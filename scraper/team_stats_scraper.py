"""
Team Stats Scraper
=================
This script scrapes team-level statistics from SofaScore football matches.
It focuses on collecting team data for the last 7 matches.
"""

import argparse
import time
from datetime import datetime
import pandas as pd
import uuid
import pytz
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# Initialize WebDriver
def create_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    return webdriver.Chrome(options=chrome_options)

def scrape_team_match_stats(url, driver=None):
    """
    Scrapes team-level match statistics from a SofaScore match page.
    
    Args:
        url (str): URL of the SofaScore match
        driver (WebDriver, optional): Selenium WebDriver instance
        
    Returns:
        dict: Dictionary containing team match statistics
    """
    close_driver = False
    if driver is None:
        driver = create_driver()
        close_driver = True
    
    try:
        driver.get(url)
        time.sleep(2)
        
        # Get match date
        date_element = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.d_flex.ai_center.br_lg.bg-c_surface\\.s2.py_xs.px_sm.mb_xs.h_\\[26px\\]"))
        )
        date_str = date_element.text.split(' ')[0].replace('/', '')
        match_date = datetime.strptime(date_str, "%d%m%y").strftime("%Y%m%d")
        
        # Get team names
        home_team = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'div[data-testid="left_team"] img'))
        ).get_attribute("alt").strip()
        
        away_team = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'div[data-testid="right_team"] img'))
        ).get_attribute("alt").strip()
        
        # Get score
        score_element = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//span[contains(@class, 'Text jVxayx')]/ancestor::div[contains(@class, 'Box iCtkKe')]"))
        )
        score_text = score_element.text
        score_parts = score_text.split('-')
        home_goals = int(score_parts[0].strip())
        away_goals = int(score_parts[1].strip())
        
        # Click on Statistics tab to get detailed stats
        tabs = WebDriverWait(driver, 15).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.Box.bkrWzf.Tab.cbSGUp.secondary"))
        )
        stats_tab = next((tab for tab in tabs if "STATISTICS" in tab.text), None)
        if stats_tab:
            stats_tab.click()
            time.sleep(1)
        
        # Extract statistics
        stats_dict = extract_team_stats(driver)
        
        # Get league info
        try:
            tournament_info = driver.find_element(By.CSS_SELECTOR, "span.Text.jzTRIw")
            league_name = tournament_info.text.strip()
            # Extract league ID from URL or another attribute if available
            league_id = league_name.lower().replace(' ', '_')
        except NoSuchElementException:
            league_name = "Unknown"
            league_id = "unknown"
        
        # Create unique match_id
        match_id_home = f"{match_date}_{home_team}_{away_team}"
        match_id_away = f"{match_date}_{away_team}_{home_team}"
        
        # Create records for both home and away teams
        home_record = {
            'match_id': match_id_home,
            'date': match_date,
            'team': home_team,
            'opponent': away_team,
            'gf': home_goals,
            'ga': away_goals,
            'sh': stats_dict.get('home_shots', 0),
            'sot': stats_dict.get('home_shots_on_target', 0),
            'dist': stats_dict.get('home_distance_covered', 0),
            'fk': stats_dict.get('home_free_kicks', 0),
            'pk': stats_dict.get('home_penalty_goals', 0),
            'pkatt': stats_dict.get('home_penalty_attempts', 0),
            'league_id': league_id,
            'league_name': league_name,
            'scrape_date': datetime.now(pytz.UTC).isoformat()
        }
        
        away_record = {
            'match_id': match_id_away,
            'date': match_date,
            'team': away_team,
            'opponent': home_team,
            'gf': away_goals,
            'ga': home_goals,
            'sh': stats_dict.get('away_shots', 0),
            'sot': stats_dict.get('away_shots_on_target', 0),
            'dist': stats_dict.get('away_distance_covered', 0),
            'fk': stats_dict.get('away_free_kicks', 0),
            'pk': stats_dict.get('away_penalty_goals', 0),
            'pkatt': stats_dict.get('away_penalty_attempts', 0),
            'league_id': league_id,
            'league_name': league_name,
            'scrape_date': datetime.now(pytz.UTC).isoformat()
        }
        
        return [home_record, away_record]
        
    except Exception as e:
        print(f"Error scraping match {url}: {e}")
        return []
    finally:
        if close_driver:
            driver.quit()

def extract_team_stats(driver):
    """
    Extracts team statistics from the statistics page.
    
    Args:
        driver (WebDriver): Selenium WebDriver instance
        
    Returns:
        dict: Dictionary containing team statistics
    """
    stats = {}
    
    try:
        # Wait for statistics table to load
        stats_table = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.sc-fqkvVR.sc-dcJsrY.dJzBEI.chmHlz"))
        )
        
        # Extract all statistic rows
        stat_rows = stats_table.find_elements(By.CSS_SELECTOR, "div.sc-fqkvVR.sc-dcJsrY.dNrDGK.chmHlz")
        
        for row in stat_rows:
            try:
                # Get the statistic name and values
                stat_elements = row.find_elements(By.CSS_SELECTOR, "div")
                if len(stat_elements) >= 3:
                    stat_name = stat_elements[1].text.strip().lower().replace(' ', '_')
                    home_value = clean_stat_value(stat_elements[0].text.strip())
                    away_value = clean_stat_value(stat_elements[2].text.strip())
                    
                    stats[f'home_{stat_name}'] = home_value
                    stats[f'away_{stat_name}'] = away_value
            except Exception as e:
                print(f"Error extracting stat row: {e}")
        
        # Look specifically for shots, shots on target, distance, free kicks, penalties
        map_specific_stats(stats)
        
    except Exception as e:
        print(f"Error extracting team stats: {e}")
    
    return stats

def clean_stat_value(value):
    """
    Cleans and converts statistic values to appropriate types.
    
    Args:
        value (str): Statistic value as string
        
    Returns:
        int or float: Converted statistic value
    """
    try:
        # Handle percentage values
        if '%' in value:
            return float(value.replace('%', ''))
        
        # Handle distance values (e.g., "10.5 km")
        if 'km' in value:
            return float(value.replace('km', '').strip())
        
        # Handle values with slash (e.g., "5/10")
        if '/' in value:
            parts = value.split('/')
            return int(parts[0].strip())
        
        # Try to convert to int or float
        try:
            return int(value)
        except ValueError:
            try:
                return float(value)
            except ValueError:
                return value
    except:
        return value

def map_specific_stats(stats_dict):
    """
    Maps SofaScore statistic names to required output names.
    
    Args:
        stats_dict (dict): Dictionary of statistics
        
    Returns:
        None: Modifies the stats_dict in place
    """
    # Mapping for shots
    if 'home_total_shots' in stats_dict:
        stats_dict['home_shots'] = stats_dict['home_total_shots']
        stats_dict['away_shots'] = stats_dict['away_total_shots']
    
    # Mapping for shots on target
    if 'home_shots_on_goal' in stats_dict:
        stats_dict['home_shots_on_target'] = stats_dict['home_shots_on_goal']
        stats_dict['away_shots_on_target'] = stats_dict['away_shots_on_goal']
    
    # For penalties, usually need to check for specific stats
    # These may need to be adjusted based on how SofaScore displays these stats
    if 'home_penalties' in stats_dict:
        penalty_str_home = stats_dict.get('home_penalties', '0/0')
        penalty_str_away = stats_dict.get('away_penalties', '0/0')
        
        if isinstance(penalty_str_home, str) and '/' in penalty_str_home:
            parts = penalty_str_home.split('/')
            stats_dict['home_penalty_goals'] = int(parts[0].strip())
            stats_dict['home_penalty_attempts'] = int(parts[1].strip())
        else:
            stats_dict['home_penalty_goals'] = 0
            stats_dict['home_penalty_attempts'] = 0
            
        if isinstance(penalty_str_away, str) and '/' in penalty_str_away:
            parts = penalty_str_away.split('/')
            stats_dict['away_penalty_goals'] = int(parts[0].strip())
            stats_dict['away_penalty_attempts'] = int(parts[1].strip())
        else:
            stats_dict['away_penalty_goals'] = 0
            stats_dict['away_penalty_attempts'] = 0
    else:
        # Default values if not found
        stats_dict['home_penalty_goals'] = 0
        stats_dict['home_penalty_attempts'] = 0
        stats_dict['away_penalty_goals'] = 0
        stats_dict['away_penalty_attempts'] = 0
        
    # Free kicks may need similar parsing
    if 'home_free_kicks' not in stats_dict:
        stats_dict['home_free_kicks'] = 0
        stats_dict['away_free_kicks'] = 0

def get_team_last_matches(team_name, num_matches=7):
    """
    Gets the last N matches for a specific team.
    
    Args:
        team_name (str): Name of the team
        num_matches (int): Number of recent matches to fetch
        
    Returns:
        list: List of match data dictionaries
    """
    driver = create_driver()
    team_matches = []
    
    try:
        # Search for the team on SofaScore
        driver.get("https://www.sofascore.com/")
        time.sleep(2)
        
        # Find search box and input team name
        search_box = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input.Input.ezmCXj"))
        )
        search_box.send_keys(team_name)
        time.sleep(1)
        
        # Click on the first search result (should be the team)
        first_result = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "a.SearchResultItem.fjVBon"))
        )
        first_result.click()
        time.sleep(2)
        
        # Find and click on the "Matches" tab
        tabs = WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.Box.bkrWzf.Tab.cbSGUp"))
        )
        matches_tab = next((tab for tab in tabs if "MATCHES" in tab.text), None)
        if matches_tab:
            matches_tab.click()
            time.sleep(1)
        
        # Find the finished matches section
        finished_section = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//div[contains(text(), 'Finished')]"))
        )
        match_links = finished_section.find_elements(By.XPATH, "following-sibling::div//a")
        
        # Get the most recent matches
        match_urls = []
        for i, link in enumerate(match_links):
            if i >= num_matches:
                break
            match_urls.append(link.get_attribute('href'))
        
        # Scrape each match
        for url in match_urls:
            match_data = scrape_team_match_stats(url, driver)
            if match_data:
                team_matches.extend(match_data)
    
    except Exception as e:
        print(f"Error getting matches for {team_name}: {e}")
    
    finally:
        driver.quit()
    
    # Filter to include only matches for the requested team
    return [match for match in team_matches if match['team'] == team_name]

def main():
    parser = argparse.ArgumentParser(description="Scrape team statistics from SofaScore.")
    parser.add_argument('--team', type=str, help='Team name to scrape data for')
    parser.add_argument('--matches', type=int, default=7, help='Number of recent matches to scrape')
    parser.add_argument('--output', type=str, default='team_stats.csv', help='Output CSV filename')
    args = parser.parse_args()
    
    if args.team:
        matches_data = get_team_last_matches(args.team, args.matches)
        if matches_data:
            df = pd.DataFrame(matches_data)
            df.to_csv(args.output, index=False)
            print(f"Scraped data for {len(matches_data)} matches saved to {args.output}")
        else:
            print(f"No match data found for {args.team}")
    else:
        print("Please provide a team name using the --team argument")

if __name__ == "__main__":
    main()