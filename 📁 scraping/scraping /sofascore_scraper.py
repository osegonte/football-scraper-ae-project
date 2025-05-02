"""
SofaScore Scraper
=================
This script scrapes detailed player statistics from SofaScore football matches.
"""

import argparse
import time
from datetime import datetime
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import StaleElementReferenceException

# Initialize WebDriver
def create_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    return webdriver.Chrome(options=chrome_options)

driver = create_driver()

def click_and_scrape():
    """
    Clicks player tabs and scrapes data into a DataFrame.
    """
    table = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, "table.Table.fEUhaC")))
    data = []

    for row in table.find_elements(By.XPATH, ".//tr"):
        cells = row.find_elements(By.TAG_NAME, "td")
        if len(cells) > 1:
            try:
                player_name = cells[1].find_element(By.CSS_SELECTOR, 'span.Text.giHhMn').text
                player_id = cells[1].find_element(By.TAG_NAME, 'a').get_attribute('href').split('/')[-1]
                player_team = cells[0].find_element(By.XPATH, './/img').get_attribute('alt')
                data.append([player_name, player_id, player_team])
            except Exception as e:
                print(f"Error processing player row: {e}")

    all_dataframes = pd.DataFrame(data, columns=['Player', 'Player_ID', 'Team'])
    button_groups = {
        'General': 'summaryGroup',
        'Attacking': 'attackGroup',
        'Defending': 'defenceGroup',
        'Passing': 'passingGroup',
        'Duels': 'duelsGroup',
        'Goalkeeping': 'goalkeeperGroup'
    }

    for name, tab_id in button_groups.items():
        try:
            button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, f"//button[@data-tabid='{tab_id}']"))
            )
            button.click()
            time.sleep(0.1)
            table_data = scrape_table_data()
            table_data = table_data.rename(columns={'Notes': f'Notes {name}'})
            all_dataframes = pd.merge(all_dataframes, table_data, on='Player', how='outer', suffixes=('', '_dup'))
        except Exception as e:
            print(f"Error clicking {name} button: {e}")

    return finalize_game_metadata(all_dataframes)

def scrape_table_data():
    """
    Extracts table data from the current view.
    """
    table = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.XPATH, "//table[contains(@class, 'Table')]"))
    )
    headers = [header.text for header in table.find_elements(By.XPATH, ".//thead/tr/th")[1:]]
    headers[0] = "Player"

    rows = [
        [col.accessible_name for col in row.find_elements(By.TAG_NAME, "td")[1:]]
        for row in table.find_elements(By.XPATH, ".//tbody/tr")
    ]
    return pd.DataFrame(rows, columns=headers)

def finalize_game_metadata(df):
    """
    Adds match metadata like home/away team, date, and score.
    """
    try:
        away_team = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'div[data-testid="right_team"] img'))
        ).get_attribute("alt").strip()

        home_team = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'div[data-testid="left_team"] img'))
        ).get_attribute("alt").strip()

        df['Home/Away'] = df['Team'].apply(lambda x: '1' if x == home_team else ('0' if x == away_team else 'unknown'))

        outer_div = driver.find_element(By.CSS_SELECTOR,
                                        "div.d_flex.ai_center.br_lg.bg-c_surface\\.s2.py_xs.px_sm.mb_xs.h_\\[26px\\]")
        spans = outer_div.find_elements(By.TAG_NAME, 'span')
        date = [span.text for span in spans if ':' not in span.text][0].replace("/", "")

        df['Date'] = date
        df.fillna('0', inplace=True)

        score_element = driver.find_element(By.XPATH, "//span[contains(@class, 'Text jVxayx')]/ancestor::div[contains(@class, 'Box iCtkKe')]")
        df['Score'] = score_element.text
    except Exception as e:
        print(f"Error extracting metadata: {e}")

    return df

def single_game_scraper(url):
    """
    Scrapes a single game's player statistics.
    """
    driver.get(url)
    time.sleep(1)
    try:
        elements = WebDriverWait(driver, 20).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.Box.bkrWzf.Tab.cbSGUp.secondary"))
        )
        player_tab = next((e for e in elements if 'PLAYER' in e.text), None)
        if player_tab:
            player_tab.click()
            time.sleep(0.5)
            return click_and_scrape()
        else:
            print("No PLAYER tab found.")
            return pd.DataFrame()
    except Exception as e:
        print(f"Error scraping game: {e}")
        return pd.DataFrame()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', help='SofaScore match URL', required=True)
    args = parser.parse_args()

    df = single_game_scraper(args.url)
    df.to_csv("scraped_game.csv", index=False)
    driver.quit()

if __name__ == "__main__":
    main()
