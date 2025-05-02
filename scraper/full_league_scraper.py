"""
Full League Scraper
===================
Scrapes all games from a given SofaScore country/league/season and date range.
Depends on: sofascore_scraper.py
"""

import argparse
import time
from datetime import datetime

import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import StaleElementReferenceException

from sofascore_scraper import single_game_scraper


def create_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    return webdriver.Chrome(options=chrome_options)


driver = create_driver()


def scraping_caller_for_rounds(rounds_matrix, league, season):
    combined_league_data = pd.DataFrame()
    for i, game_urls in enumerate(rounds_matrix):
        round_data = pd.DataFrame()
        for url in game_urls:
            try:
                game_data = single_game_scraper(url)
                if game_data is None or game_data.empty:
                    continue
                round_data = pd.concat([round_data, game_data], ignore_index=True)
            except Exception as e:
                print(f"Error scraping {url}: {e}")
        combined_league_data = pd.concat([combined_league_data, round_data], ignore_index=True)
        print(f"Finished round {i + 1} with {len(round_data)} games.")

    filename = f"{league}_{season.replace('/', '-')}.xlsx"
    combined_league_data.to_excel(filename, index=False)
    print(f" Saved all data to {filename}")


def navigate_games_within_dates(season, initial_date, final_date, league):
    rounds_matrix = []
    current_round = []

    initial = datetime.strptime(initial_date, "%d/%m/%y")
    final = datetime.strptime(final_date, "%d/%m/%y")

    while True:
        game_dates = WebDriverWait(driver, 20).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "bdi.Text.kcRyBI"))
        )
        time.sleep(2)

        for i in range(len(game_dates) - 1, -1, -1):
            try:
                game_dates = WebDriverWait(driver, 10).until(
                    EC.presence_of_all_elements_located((By.CSS_SELECTOR, "bdi.Text.kcRyBI"))
                )
                game_date = game_dates[i].text.strip()

                if ":" in game_date:
                    continue

                game_date_dt = datetime.strptime(game_date, "%d/%m/%y")
                if initial <= game_date_dt <= final:
                    anchor = game_dates[i].find_element(By.XPATH, "./ancestor::a")
                    url = anchor.get_attribute("href")
                    if url:
                        current_round.append(url)

                elif game_date_dt < initial:
                    if current_round:
                        rounds_matrix.append(current_round)
                    scraping_caller_for_rounds(rounds_matrix, league, season)
                    return

            except StaleElementReferenceException:
                break

        try:
            prev_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "button.Button.iCnTrv"))
            )
            span = prev_button.find_element(By.CSS_SELECTOR, "span.Text.eIDPIm").text
            if "PREVIOUS" in span.upper():
                if current_round:
                    rounds_matrix.append(current_round)
                    current_round = []
                driver.execute_script("arguments[0].click();", prev_button)
                time.sleep(2)
            else:
                if current_round:
                    rounds_matrix.append(current_round)
                    scraping_caller_for_rounds(rounds_matrix, league, season)
                return
        except Exception as e:
            print(f"Error with previous button: {e}")
            if current_round:
                rounds_matrix.append(current_round)
            scraping_caller_for_rounds(rounds_matrix, league, season)
            return


def search_season_and_dates(season, initial_date, final_date, league):
    seasons_tab = WebDriverWait(driver, 20).until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, "button.DropdownButton.bWGdIv"))
    )
    seasons_tab.click()

    items = WebDriverWait(driver, 10).until(
        EC.presence_of_all_elements_located((By.XPATH, "//li[contains(@class, 'DropdownItem')]"))
    )

    for item in items:
        if item.text == season:
            item.click()
            break

    try:
        by_date_tab = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "div.Box.bkrWzf.Tab.cbSGUp.secondary[data-tabid='date']"))
        )
        driver.execute_script("arguments[0].click();", by_date_tab)
        time.sleep(2)
    except Exception as e:
        print(f"Could not find 'by date' tab: {e}")

    navigate_games_within_dates(season, initial_date, final_date, league)


def search_country_and_league(country_name, league_name, season, initial_date, final_date):
    """
    Navigates the SofaScore website to locate the desired country and league, then triggers scraping.
    """
    url = "https://www.sofascore.com/football"
    try:
        driver.get(url)
    except Exception as e:
        raise RuntimeError(f" Failed to load SofaScore football page: {e}")

    try:
        # Expand all countries
        show_more_buttons = WebDriverWait(driver, 20).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "button.button--variant_clear"))
        )
        for i, button in enumerate(show_more_buttons):
            try:
                driver.execute_script("arguments[0].scrollIntoView();", button)
                WebDriverWait(driver, 10).until(EC.element_to_be_clickable(button)).click()
                time.sleep(0.2)
            except Exception as e:
                print(f" Could not click 'Show more' button #{i}: {e}")

        # Step 1: Find country
        country_elements = WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "span.Text.bImuxH"))
        )

        country_found = False
        for country in country_elements:
            country_text = country.text.strip().split('==')[0].strip()
            if country_name.lower() == country_text.lower():
                print(f" Country found: {country_text}")
                country.click()
                time.sleep(2)
                country_found = True
                break

        if not country_found:
            raise ValueError(f" Country '{country_name}' not found on SofaScore.")

        # Step 2: Find league inside selected country
        league_elements = WebDriverWait(driver, 15).until(
            EC.presence_of_all_elements_located(
                (By.XPATH, "//div[contains(@class, 'Box') and contains(@class, 'eCIOYr')]")
            )
        )

        league_found = False
        for league_box in league_elements:
            league_text = league_box.find_element(By.CLASS_NAME, 'Text.ilzzfl').text.strip()
            print(f"Checking league: {league_text}")
            if league_name.lower() == league_text.lower():
                league_box.click()
                time.sleep(2)
                league_found = True
                break

        if not league_found:
            raise ValueError(f" League '{league_name}' not found in country '{country_name}'.")

        clean_league_code = league_name.replace(" ", "")
        search_season_and_dates(season, initial_date, final_date, clean_league_code)

    except Exception as e:
        raise RuntimeError(f"🔥 Unexpected error in country/league navigation: {e}")


def main():
    parser = argparse.ArgumentParser(description="Scrape football match data from SofaScore.")
    parser.add_argument('--country', type=str, required=True, help="Country name, e.g. 'Italy'")
    parser.add_argument('--league', type=str, required=True, help="League name, e.g. 'Serie A'")
    parser.add_argument('--season', type=str, required=True, help="Season format: '23/24'")
    parser.add_argument('--initial_date', type=str, required=True, help="Start date in DD/MM/YY")
    parser.add_argument('--final_date', type=str, required=True, help="End date in DD/MM/YY")
    args = parser.parse_args()

    search_country_and_league(
        country_name=args.country,
        league_name=args.league,
        season=args.season,
        initial_date=args.initial_date,
        final_date=args.final_date
    )

    driver.quit()


if __name__ == "__main__":
    main()
