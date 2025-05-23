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
import traceback
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException

# Initialize WebDriver
def create_driver():
    """
    Creates and configures a Chrome WebDriver for scraping.
    
    Returns:
        WebDriver: Configured Chrome WebDriver instance
    """
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36")
    return webdriver.Chrome(options=chrome_options)

def scrape_team_match_stats(url, driver=None):
    """
    Scrapes team-level match statistics from a SofaScore match page.
    
    Args:
        url (str): URL of the SofaScore match
        driver (WebDriver, optional): Selenium WebDriver instance
        
    Returns:
        list: List of dictionaries containing home and away team match statistics
    """
    close_driver = False
    if driver is None:
        driver = create_driver()
        close_driver = True
    
    try:
        driver.get(url)
        time.sleep(3)  # Increased wait time
        
        # Get match date - with multiple approaches
        try:
            date_element = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div.d_flex.ai_center.br_lg.bg-c_surface\\.s2.py_xs.px_sm.mb_xs.h_\\[26px\\]"))
            )
            date_str = date_element.text.split(' ')[0].replace('/', '')
        except (TimeoutException, NoSuchElementException, IndexError):
            try:
                # Try alternative approach
                date_str = driver.find_element(By.XPATH, "//div[contains(@class, 'date') or contains(@data-testid, 'date')]").text.split(' ')[0].replace('/', '')
            except:
                # Default to today's date if all approaches fail
                date_str = datetime.now().strftime("%d%m%y")
        
        # Standardize date format
        try:
            # Try to parse with different possible formats
            format_attempts = ["%d%m%y", "%d%m%Y", "%Y%m%d"]
            match_date = None
            
            for fmt in format_attempts:
                try:
                    match_date = datetime.strptime(date_str, fmt).strftime("%Y%m%d")
                    break
                except ValueError:
                    continue
                    
            if not match_date:
                # Default format if all attempts fail
                match_date = datetime.now().strftime("%Y%m%d")
        except Exception as e:
            print(f"Error parsing date {date_str}: {e}")
            match_date = datetime.now().strftime("%Y%m%d")
        
        # Get team names - with fallbacks
        try:
            home_team = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'div[data-testid="left_team"] img'))
            ).get_attribute("alt").strip()
        except (TimeoutException, NoSuchElementException):
            try:
                home_team = driver.find_element(By.XPATH, "//div[contains(@class, 'left_team') or contains(@data-testid, 'left_team')]//img").get_attribute("alt").strip()
            except:
                try:
                    # Try just getting text
                    home_team = driver.find_element(By.XPATH, "//div[contains(@class, 'left_team') or contains(@data-testid, 'left_team')]").text.strip()
                except:
                    home_team = "Unknown Home Team"
        
        try:
            away_team = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'div[data-testid="right_team"] img'))
            ).get_attribute("alt").strip()
        except (TimeoutException, NoSuchElementException):
            try:
                away_team = driver.find_element(By.XPATH, "//div[contains(@class, 'right_team') or contains(@data-testid, 'right_team')]//img").get_attribute("alt").strip()
            except:
                try:
                    # Try just getting text
                    away_team = driver.find_element(By.XPATH, "//div[contains(@class, 'right_team') or contains(@data-testid, 'right_team')]").text.strip()
                except:
                    away_team = "Unknown Away Team"
        
        # Get score - with fallbacks
        try:
            score_element = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//span[contains(@class, 'Text jVxayx')]/ancestor::div[contains(@class, 'Box iCtkKe')]"))
            )
            score_text = score_element.text
        except (TimeoutException, NoSuchElementException):
            try:
                # Try alternative selector
                score_text = driver.find_element(By.XPATH, "//div[contains(@class, 'score') or contains(@data-testid, 'score')]").text
            except:
                score_text = "0-0"  # Default score
        
        # Parse score safely
        try:
            score_parts = score_text.split('-')
            if len(score_parts) == 2:
                home_goals = int(score_parts[0].strip())
                away_goals = int(score_parts[1].strip())
            else:
                home_goals = 0
                away_goals = 0
        except (ValueError, IndexError):
            home_goals = 0
            away_goals = 0
            
        # Click on Statistics tab - with retry logic
        attempts = 0
        while attempts < 3:
            try:
                # Try to find the Statistics tab
                tabs = WebDriverWait(driver, 15).until(
                    EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.Box.bkrWzf.Tab.cbSGUp.secondary, div[class*='Tab']"))
                )
                
                # Try to find Statistics tab (case-insensitive)
                stats_tab = None
                for tab in tabs:
                    if "STATISTICS" in tab.text.upper():
                        stats_tab = tab
                        break
                
                if stats_tab:
                    stats_tab.click()
                    time.sleep(2)  # Wait for statistics to load
                    break
                else:
                    attempts += 1
                    time.sleep(1)
            except Exception as e:
                print(f"Attempt {attempts+1}/3: Error finding statistics tab: {e}")
                attempts += 1
                time.sleep(1)
        
        # Extract statistics - with validation
        stats_dict = extract_team_stats(driver)
        
        # Validate extracted statistics
        for key, value in list(stats_dict.items()):
            # Convert strings to numeric values when possible
            if isinstance(value, str):
                try:
                    if '.' in value:
                        stats_dict[key] = float(value)
                    else:
                        stats_dict[key] = int(value)
                except ValueError:
                    # Keep as string if conversion fails
                    pass
            
            # Set default values for missing or invalid statistics
            if key.endswith('_shots') and (not key in stats_dict or stats_dict[key] is None):
                stats_dict[key] = 0
            if key.endswith('_shots_on_target') and (not key in stats_dict or stats_dict[key] is None):
                stats_dict[key] = 0
        
        # Get league info - with fallbacks
        try:
            tournament_info = driver.find_element(By.CSS_SELECTOR, "span.Text.jzTRIw")
            league_name = tournament_info.text.strip()
        except NoSuchElementException:
            try:
                # Try alternative selector
                league_name = driver.find_element(By.XPATH, "//span[contains(@class, 'tournament') or contains(@class, 'league')]").text.strip()
            except:
                league_name = "Unknown League"
        
        # Extract league ID from URL or league name
        try:
            league_id = url.split('/tournament/')[1].split('/')[0]
        except (IndexError, ValueError):
            # Fallback to normalized league name
            league_id = league_name.lower().replace(' ', '_')
        
        # Create unique match_id
        match_id_home = f"{match_date}_{home_team}_{away_team}"
        match_id_away = f"{match_date}_{away_team}_{home_team}"
        
        # Get current time in UTC
        scrape_timestamp = datetime.now(pytz.UTC).isoformat()
        
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
            'scrape_date': scrape_timestamp
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
            'scrape_date': scrape_timestamp
        }
        
        return [home_record, away_record]
        
    except Exception as e:
        print(f"Error scraping match {url}: {e}")
        traceback.print_exc()  # Print full stack trace for debugging
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
        # Try multiple approaches to find statistics table
        stats_table = None
        selectors = [
            "div.sc-fqkvVR.sc-dcJsrY.dJzBEI.chmHlz",
            "div[class*='statistics']",
            "//div[contains(text(), 'Statistics')]/../.."
        ]
        
        for selector in selectors:
            try:
                if selector.startswith("//"):
                    # XPATH selector
                    stats_table = WebDriverWait(driver, 5).until(
                        EC.presence_of_element_located((By.XPATH, selector))
                    )
                else:
                    # CSS selector
                    stats_table = WebDriverWait(driver, 5).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                    )
                break
            except (TimeoutException, NoSuchElementException):
                continue
        
        if not stats_table:
            print("Could not find statistics table")
            return stats
        
        # Try multiple approaches to find statistic rows
        stat_rows = []
        row_selectors = [
            "div.sc-fqkvVR.sc-dcJsrY.dNrDGK.chmHlz",
            "div[class*='statistic-row']",
            "//div[contains(@class, 'statistic')]"
        ]
        
        for selector in row_selectors:
            try:
                if selector.startswith("//"):
                    # XPATH selector
                    stat_rows = stats_table.find_elements(By.XPATH, selector)
                else:
                    # CSS selector
                    stat_rows = stats_table.find_elements(By.CSS_SELECTOR, selector)
                
                if stat_rows:
                    break
            except NoSuchElementException:
                continue
        
        if not stat_rows:
            print("Could not find statistic rows")
            return stats
        
        # Extract statistics from rows
        for row in stat_rows:
            try:
                # Get the statistic name and values from div elements
                stat_elements = row.find_elements(By.CSS_SELECTOR, "div")
                
                if len(stat_elements) >= 3:
                    stat_name = stat_elements[1].text.strip().lower().replace(' ', '_')
                    home_value = clean_stat_value(stat_elements[0].text.strip())
                    away_value = clean_stat_value(stat_elements[2].text.strip())
                    
                    stats[f'home_{stat_name}'] = home_value
                    stats[f'away_{stat_name}'] = away_value
            except NoSuchElementException as e:
                print(f"Element not found in stat row: {e}")
            except StaleElementReferenceException:
                print("Element became stale, the page likely changed during processing")
                continue
            except Exception as e:
                print(f"Unexpected error extracting stat row: {e}")
                traceback.print_exc()
        
        # Map specific stats to required output format
        map_specific_stats(stats)
        
    except Exception as e:
        print(f"Error extracting team stats: {e}")
        traceback.print_exc()
    
    return stats

def clean_stat_value(value):
    """
    Cleans and converts statistic values to appropriate types.
    
    Args:
        value (str): Statistic value as string
        
    Returns:
        int, float or str: Converted statistic value
    """
    try:
        # Handle empty or None values
        if not value or value == '-':
            return 0
            
        # Handle percentage values
        if '%' in value:
            return float(value.replace('%', ''))
        
        # Handle distance values (e.g., "10.5 km")
        if isinstance(value, str) and 'km' in value:
            return float(value.replace('km', '').strip())
        
        # Handle values with slash (e.g., "5/10")
        if isinstance(value, str) and '/' in value:
            parts = value.split('/')
            if len(parts) == 2:
                try:
                    return int(parts[0].strip())
                except ValueError:
                    return 0
        
        # Try to convert to int or float
        if isinstance(value, str):
            try:
                if value.isdigit():
                    return int(value)
                elif value.replace('.', '', 1).isdigit():
                    return float(value)
                else:
                    return value
            except ValueError:
                return value
        else:
            return value
    except Exception as e:
        print(f"Error cleaning value '{value}': {e}")
        return 0

def map_specific_stats(stats_dict):
    """
    Maps SofaScore statistic names to required output names.
    
    Args:
        stats_dict (dict): Dictionary of statistics
        
    Returns:
        None: Modifies the stats_dict in place
    """
    # Mapping for shots
    shot_keys = ['total_shots', 'shots', 'shot_attempts']
    for key in shot_keys:
        if f'home_{key}' in stats_dict:
            stats_dict['home_shots'] = stats_dict[f'home_{key}']
            stats_dict['away_shots'] = stats_dict[f'away_{key}']
            break
    
    # Default if no shot stats found
    if 'home_shots' not in stats_dict:
        stats_dict['home_shots'] = 0
        stats_dict['away_shots'] = 0
    
    # Mapping for shots on target
    sot_keys = ['shots_on_goal', 'shots_on_target', 'accurate_shots']
    for key in sot_keys:
        if f'home_{key}' in stats_dict:
            stats_dict['home_shots_on_target'] = stats_dict[f'home_{key}']
            stats_dict['away_shots_on_target'] = stats_dict[f'away_{key}']
            break
    
    # Default if no shots on target found
    if 'home_shots_on_target' not in stats_dict:
        stats_dict['home_shots_on_target'] = 0
        stats_dict['away_shots_on_target'] = 0
    
    # For penalties, check for specific stats
    penalty_keys = ['penalties', 'penalty_kicks', 'penalty']
    
    for key in penalty_keys:
        if f'home_{key}' in stats_dict:
            penalty_str_home = stats_dict.get(f'home_{key}', '0/0')
            penalty_str_away = stats_dict.get(f'away_{key}', '0/0')
            
            # Process home penalties
            if isinstance(penalty_str_home, str) and '/' in penalty_str_home:
                parts = penalty_str_home.split('/')
                stats_dict['home_penalty_goals'] = int(parts[0].strip()) if parts[0].strip().isdigit() else 0
                stats_dict['home_penalty_attempts'] = int(parts[1].strip()) if parts[1].strip().isdigit() else 0
            else:
                stats_dict['home_penalty_goals'] = 0
                stats_dict['home_penalty_attempts'] = 0
                
            # Process away penalties
            if isinstance(penalty_str_away, str) and '/' in penalty_str_away:
                parts = penalty_str_away.split('/')
                stats_dict['away_penalty_goals'] = int(parts[0].strip()) if parts[0].strip().isdigit() else 0
                stats_dict['away_penalty_attempts'] = int(parts[1].strip()) if parts[1].strip().isdigit() else 0
            else:
                stats_dict['away_penalty_goals'] = 0
                stats_dict['away_penalty_attempts'] = 0
                
            break
    
    # Default values if no penalties found
    if 'home_penalty_goals' not in stats_dict:
        stats_dict['home_penalty_goals'] = 0
        stats_dict['home_penalty_attempts'] = 0
        stats_dict['away_penalty_goals'] = 0
        stats_dict['away_penalty_attempts'] = 0
    
    # Free kicks mapping
    fk_keys = ['free_kicks', 'free_kick', 'freekicks']
    for key in fk_keys:
        if f'home_{key}' in stats_dict:
            stats_dict['home_free_kicks'] = stats_dict[f'home_{key}']
            stats_dict['away_free_kicks'] = stats_dict[f'away_{key}']
            break
    
    # Default if no free kicks found
    if 'home_free_kicks' not in stats_dict:
        stats_dict['home_free_kicks'] = 0
        stats_dict['away_free_kicks'] = 0
        
    # Distance covered mapping
    distance_keys = ['distance_covered', 'distance', 'distance_run']
    for key in distance_keys:
        if f'home_{key}' in stats_dict:
            stats_dict['home_distance_covered'] = stats_dict[f'home_{key}']
            stats_dict['away_distance_covered'] = stats_dict[f'away_{key}']
            break
    
    # Default if no distance covered found
    if 'home_distance_covered' not in stats_dict:
        stats_dict['home_distance_covered'] = 0
        stats_dict['away_distance_covered'] = 0

def get_team_matches_api(team_name, num_matches=7):
    """
    Gets the last N matches for a specific team using SofaScore's API.
    
    Args:
        team_name (str): Name of the team
        num_matches (int): Number of recent matches to fetch
        
    Returns:
        list: List of match data dictionaries
    """
    import requests
    from datetime import datetime, timedelta
    import time
    import json
    
    # Create a session with browser-like headers
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'application/json',
        'Accept-Language': 'en-US,en;q=0.9',
        'Referer': 'https://www.sofascore.com/'
    })
    
    # Step 1: Search for the team ID
    search_url = f"https://api.sofascore.com/api/v1/search/teams/{team_name}"
    try:
        response = session.get(search_url)
        search_data = response.json()
        
        # Extract team ID from search results
        team_id = None
        if 'results' in search_data and search_data['results']:
            # Look for exact or close match
            for result in search_data['results']:
                if result['name'].lower() == team_name.lower() or team_name.lower() in result['name'].lower():
                    team_id = result['id']
                    break
        
        if not team_id:
            print(f"Could not find team ID for {team_name}")
            return []
            
        print(f"Found team ID {team_id} for {team_name}")
        
        # Step 2: Get team's last matches
        team_url = f"https://api.sofascore.com/api/v1/team/{team_id}/events/last/{num_matches}"
        response = session.get(team_url)
        events_data = response.json()
        
        if 'events' not in events_data:
            print(f"No match data found for {team_name}")
            return []
        
        # Process match data
        matches = []
        for event in events_data['events']:
            # Check if it's a finished match
            if event['status']['type'] != 'finished':
                continue
                
            # Get team and opponent info
            home_team = event['homeTeam']['name']
            away_team = event['awayTeam']['name']
            is_home = home_team == team_name
            opponent = away_team if is_home else home_team
            
            # Get score
            home_score = event['homeScore']['current']
            away_score = event['awayScore']['current']
            
            # Get date
            match_timestamp = event['startTimestamp']
            match_date = datetime.fromtimestamp(match_timestamp).strftime('%Y%m%d')
            
            # Create match ID
            match_id = f"{match_date}_{home_team}_{away_team}"
            
            # Get tournament/league info
            league_name = event['tournament']['name']
            league_id = str(event['tournament']['id'])
            
            # Create record for this team
            team_record = {
                'match_id': match_id,
                'date': match_date,
                'team': team_name,
                'opponent': opponent,
                'gf': home_score if is_home else away_score,
                'ga': away_score if is_home else home_score,
                'home/away': '1' if is_home else '0',
                'league_id': league_id,
                'league_name': league_name,
                'scrape_date': datetime.now().isoformat()
            }
            
            # Get detailed stats if available
            try:
                stats_url = f"https://api.sofascore.com/api/v1/event/{event['id']}/statistics"
                response = session.get(stats_url)
                stats_data = response.json()
                
                if 'statistics' in stats_data:
                    # Process home/away team statistics
                    home_stats = stats_data['statistics'][0]['groups']
                    away_stats = stats_data['statistics'][1]['groups']
                    
                    # Find the relevant stats for our team
                    team_stats = home_stats if is_home else away_stats
                    
                    # Extract and add the stats we need
                    for group in team_stats:
                        for stat in group['statisticsItems']:
                            # Map common stat names to our format
                            if stat['name'] == 'Total shots':
                                team_record['sh'] = stat['home' if is_home else 'away']
                            elif stat['name'] == 'Shots on target':
                                team_record['sot'] = stat['home' if is_home else 'away']
                            elif stat['name'] == 'Distance covered':
                                # Convert distance to km if needed
                                dist_value = stat['home' if is_home else 'away']
                                if isinstance(dist_value, str) and 'km' in dist_value:
                                    team_record['dist'] = float(dist_value.replace('km', '').strip())
                                else:
                                    team_record['dist'] = dist_value
            except Exception as e:
                print(f"Error getting detailed stats: {e}")
            
            # Set default values for any missing fields
            team_record.setdefault('sh', 0)
            team_record.setdefault('sot', 0)
            team_record.setdefault('dist', 0)
            team_record.setdefault('fk', 0)
            team_record.setdefault('pk', 0)
            team_record.setdefault('pkatt', 0)
            
            matches.append(team_record)
            
        print(f"Found {len(matches)} matches for {team_name}")
        return matches
        
    except Exception as e:
        print(f"Error getting matches for {team_name}: {e}")
        import traceback
        traceback.print_exc()
        return []
    
def get_team_last_matches(team_name, num_matches=7):
    """
    Gets the last N matches for a specific team, trying API first,
    then falling back to browser if needed.
    """
    # Try API approach first
    matches = get_team_matches_api(team_name, num_matches)
    
    # If API failed, fall back to browser approach
    if not matches:
        print(f"API approach failed for {team_name}, trying browser fallback...")
        matches = get_team_last_matches_browser(team_name, num_matches)
    
    return matches

def main():
    parser = argparse.ArgumentParser(description="Scrape team statistics from SofaScore.")
    parser.add_argument('--team', type=str, help='Team name to scrape data for')
    parser.add_argument('--matches', type=int, default=7, help='Number of recent matches to scrape')
    parser.add_argument('--output', type=str, default='team_stats.csv', help='Output CSV filename')
    args = parser.parse_args()
    
    if args.team:
        print(f"Scraping data for: {args.team}")
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