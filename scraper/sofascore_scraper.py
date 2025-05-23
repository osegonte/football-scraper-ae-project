"""
SofaScore Scraper (Updated)
=================
Updated script to scrape detailed player statistics from SofaScore football matches.
This version handles modern SofaScore website and also includes API fallback.
"""

import argparse
import time
import os
import sys
import requests
from datetime import datetime
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException, WebDriverException

# Configure logging
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def create_driver():
    """
    Creates and configures a Chrome WebDriver for scraping.
    
    Returns:
        WebDriver: Configured Chrome WebDriver instance
    """
    try:
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36")
        
        # Try to find ChromeDriver in common locations
        driver_path = None
        common_locations = [
            './chromedriver',
            './chromedriver.exe',
            '/usr/local/bin/chromedriver',
            '/usr/bin/chromedriver'
        ]
        
        for location in common_locations:
            if os.path.exists(location):
                driver_path = location
                break
        
        if driver_path:
            service = Service(executable_path=driver_path)
            return webdriver.Chrome(service=service, options=chrome_options)
        else:
            # Let Selenium find ChromeDriver automatically
            return webdriver.Chrome(options=chrome_options)
            
    except WebDriverException as e:
        logger.error(f"Error creating WebDriver: {e}")
        logger.error("Make sure Chrome and ChromeDriver are installed and compatible")
        sys.exit(1)

def get_match_data_from_api(match_url):
    """
    Gets match data directly from SofaScore API instead of scraping.
    
    Args:
        match_url (str): SofaScore match URL
        
    Returns:
        pd.DataFrame: DataFrame containing player statistics
    """
    try:
        # Extract event ID from URL
        event_slug = match_url.rstrip('/').split('/')[-1]
        logger.info(f"Extracted event slug: {event_slug}")
        
        # Make request to get the numeric event ID
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        # Try to get event details
        event_url = f"https://api.sofascore.com/api/v1/event/{event_slug}"
        logger.info(f"Requesting event details from: {event_url}")
        event_response = requests.get(event_url, headers=headers)
        
        if event_response.status_code != 200:
            logger.error(f"Failed to get event details. Status code: {event_response.status_code}")
            return pd.DataFrame()
            
        event_data = event_response.json()
        
        # The API response structure might be event or event.id
        if 'event' in event_data:
            event_id = event_data['event']['id']
        else:
            event_id = event_data['id']
            
        logger.info(f"Found event ID: {event_id}")
        
        # Get player statistics
        player_stats_url = f"https://api.sofascore.com/api/v1/event/{event_id}/player-statistics"
        logger.info(f"Requesting player statistics from: {player_stats_url}")
        player_stats_response = requests.get(player_stats_url, headers=headers)
        
        if player_stats_response.status_code != 200:
            logger.error(f"Failed to get player statistics. Status code: {player_stats_response.status_code}")
            # Try lineups as fallback
            logger.info("Trying lineups as fallback...")
            lineups_url = f"https://api.sofascore.com/api/v1/event/{event_id}/lineups"
            lineups_response = requests.get(lineups_url, headers=headers)
            
            if lineups_response.status_code != 200:
                logger.error(f"Failed to get lineups. Status code: {lineups_response.status_code}")
                return pd.DataFrame()
                
            # Process lineups data instead
            return process_lineups_data(lineups_response.json(), event_data)
            
        stats_data = player_stats_response.json()
        
        # Process player statistics
        return process_player_stats(stats_data, event_data)
        
    except Exception as e:
        logger.error(f"Error fetching data from API: {e}")
        return pd.DataFrame()

def process_player_stats(stats_data, event_data):
    """
    Process player statistics from API response.
    
    Args:
        stats_data (dict): Player statistics data
        event_data (dict): Event data
        
    Returns:
        pd.DataFrame: DataFrame containing player statistics
    """
    try:
        all_players = []
        
        # Extract event details
        if 'event' in event_data:
            event = event_data['event']
        else:
            event = event_data
            
        # Format date
        try:
            match_date = datetime.fromtimestamp(event['startTimestamp']).strftime('%Y%m%d')
        except (KeyError, ValueError):
            match_date = datetime.now().strftime('%Y%m%d')
            
        # Extract score
        try:
            score = f"{event['homeScore']['current']}-{event['awayScore']['current']}"
        except (KeyError, TypeError):
            score = "0-0"
            
        # Process home team
        try:
            home_team = event['homeTeam']['name']
            home_players = stats_data['statistics']['home']
            
            for player in home_players:
                player_data = {
                    'Player': player['player']['name'],
                    'Player_ID': str(player['player']['id']),
                    'Team': home_team,
                    'Home/Away': '1',
                    'Date': match_date,
                    'Score': score
                }
                
                # Add statistics
                for stat_name, stat_value in player['statistics'].items():
                    player_data[stat_name] = stat_value
                    
                all_players.append(player_data)
        except (KeyError, TypeError) as e:
            logger.warning(f"Error processing home team data: {e}")
            
        # Process away team
        try:
            away_team = event['awayTeam']['name']
            away_players = stats_data['statistics']['away']
            
            for player in away_players:
                player_data = {
                    'Player': player['player']['name'],
                    'Player_ID': str(player['player']['id']),
                    'Team': away_team,
                    'Home/Away': '0',
                    'Date': match_date,
                    'Score': score
                }
                
                # Add statistics
                for stat_name, stat_value in player['statistics'].items():
                    player_data[stat_name] = stat_value
                    
                all_players.append(player_data)
        except (KeyError, TypeError) as e:
            logger.warning(f"Error processing away team data: {e}")
            
        return pd.DataFrame(all_players)
        
    except Exception as e:
        logger.error(f"Error processing player statistics: {e}")
        return pd.DataFrame()

def process_lineups_data(lineups_data, event_data):
    """
    Process lineups data from API response.
    
    Args:
        lineups_data (dict): Lineups data
        event_data (dict): Event data
        
    Returns:
        pd.DataFrame: DataFrame containing player statistics
    """
    try:
        all_players = []
        
        # Extract event details
        if 'event' in event_data:
            event = event_data['event']
        else:
            event = event_data
            
        # Format date
        try:
            match_date = datetime.fromtimestamp(event['startTimestamp']).strftime('%Y%m%d')
        except (KeyError, ValueError):
            match_date = datetime.now().strftime('%Y%m%d')
            
        # Extract score
        try:
            score = f"{event['homeScore']['current']}-{event['awayScore']['current']}"
        except (KeyError, TypeError):
            score = "0-0"
        
        # Process each lineup
        for lineup in lineups_data.get('lineups', []):
            try:
                team_name = lineup['team']['name']
                is_home = lineup.get('home', False)
                
                # Process players
                for player in lineup.get('players', []):
                    player_data = {
                        'Player': player['player']['name'],
                        'Player_ID': str(player['player']['id']),
                        'Team': team_name,
                        'Home/Away': '1' if is_home else '0',
                        'Date': match_date,
                        'Score': score,
                        'Position': player.get('position', ''),
                        'ShirtNumber': player.get('shirtNumber', ''),
                        'Minutes played': player.get('minutesPlayed', 0)
                    }
                    
                    # Add any additional stats
                    for stat_name, stat_value in player.get('statistics', {}).items():
                        player_data[stat_name] = stat_value
                        
                    all_players.append(player_data)
            except (KeyError, TypeError) as e:
                logger.warning(f"Error processing lineup data: {e}")
                
        return pd.DataFrame(all_players)
        
    except Exception as e:
        logger.error(f"Error processing lineups data: {e}")
        return pd.DataFrame()

def scrape_table_data(driver):
    """
    Extracts table data from the current view.
    
    Args:
        driver (WebDriver): Selenium WebDriver instance
        
    Returns:
        pd.DataFrame: DataFrame containing table data
    """
    try:
        # Wait for table to be visible after tab change
        table = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.XPATH, "//table[contains(@class, 'Table')]"))
        )
        
        # Extract headers
        headers = []
        try:
            header_elements = table.find_elements(By.XPATH, ".//thead/tr/th")[1:]
            headers = [header.text for header in header_elements]
            if headers and headers[0]:
                headers[0] = "Player"
            else:
                # Alternative approach if header texts are empty
                headers = ["Player"] + [f"Column_{i}" for i in range(1, len(header_elements))]
        except Exception as e:
            logger.warning(f"Error extracting table headers: {e}")
            headers = ["Player"] + [f"Column_{i}" for i in range(10)]  # Default headers
        
        # Extract rows
        rows = []
        try:
            for row in table.find_elements(By.XPATH, ".//tbody/tr"):
                cols = row.find_elements(By.TAG_NAME, "td")[1:]
                row_data = []
                for col in cols:
                    try:
                        # First try accessible_name
                        value = col.accessible_name
                        if not value:
                            # Fallback to text
                            value = col.text
                        row_data.append(value)
                    except:
                        row_data.append("")
                
                if row_data and len(row_data) > 0:
                    rows.append(row_data)
        except Exception as e:
            logger.warning(f"Error extracting table rows: {e}")
            
        # Create DataFrame
        if rows and headers and len(headers) == len(rows[0]):
            return pd.DataFrame(rows, columns=headers)
        elif rows:
            # Handle mismatched headers by using default column names
            logger.warning(f"Mismatch between headers ({len(headers)}) and row data ({len(rows[0])})")
            columns = [f"Column_{i}" for i in range(len(rows[0]))]
            columns[0] = "Player"  # Ensure first column is named "Player"
            return pd.DataFrame(rows, columns=columns)
        else:
            logger.warning("No rows found in table")
            return pd.DataFrame()
            
    except Exception as e:
        logger.error(f"Error scraping table data: {e}")
        return pd.DataFrame()

def collect_player_data(driver, table):
    """
    Collects player data from the stats table.
    
    Args:
        driver (WebDriver): Selenium WebDriver instance
        table: The table element
        
    Returns:
        list: List of player data rows
    """
    data = []
    
    try:
        rows = table.find_elements(By.XPATH, ".//tr")
        logger.info(f"Found {len(rows)} player rows in table")
        
        for row in rows:
            cells = row.find_elements(By.TAG_NAME, "td")
            if len(cells) > 1:
                try:
                    # Try multiple selectors for player name
                    player_name = None
                    try:
                        player_name = cells[1].find_element(By.CSS_SELECTOR, 'span.Text.giHhMn').text
                    except NoSuchElementException:
                        try:
                            player_name = cells[1].find_element(By.CSS_SELECTOR, 'span[class*="Text"]').text
                        except NoSuchElementException:
                            try:
                                player_name = cells[1].find_element(By.TAG_NAME, 'span').text
                            except NoSuchElementException:
                                player_name = cells[1].text
                    
                    # Get player ID from URL or generate unique ID
                    player_id = None
                    try:
                        player_id = cells[1].find_element(By.TAG_NAME, 'a').get_attribute('href').split('/')[-1]
                    except (NoSuchElementException, IndexError, AttributeError):
                        player_id = f"unknown_{int(time.time())}_{len(data)}"
                    
                    # Get team name
                    player_team = None
                    try:
                        player_team = cells[0].find_element(By.XPATH, './/img').get_attribute('alt')
                    except NoSuchElementException:
                        try:
                            player_team = cells[0].text.strip()
                        except:
                            player_team = "Unknown Team"
                            
                    data.append([player_name, player_id, player_team])
                except Exception as e:
                    logger.warning(f"Error processing player row: {e}")
    except Exception as e:
        logger.error(f"Error collecting player data: {e}")
    
    return data

def click_and_scrape(driver):
    """
    Clicks player tabs and scrapes data into a DataFrame.
    
    Args:
        driver (WebDriver): Selenium WebDriver instance
        
    Returns:
        pd.DataFrame: DataFrame containing player statistics
    """
    logger.info("Starting to scrape player data...")
    
    try:
        # Updated tab selectors for the player tab
        tab_selectors = [
            "//div[contains(@class, 'Tab') and contains(text(), 'PLAYER')]",
            "//div[contains(@class, 'Tab') and contains(text(), 'Player')]",
            "//div[contains(@class, 'Tab') and .//*[contains(text(), 'PLAYER')]]",
            "//div[contains(@class, 'Tab') and .//*[contains(text(), 'LINEUP')]]",
            "//div[contains(@class, 'Tab') and .//*[contains(text(), 'Lineup')]]",
            "//div[contains(@class, 'Tab') and .//*[contains(text(), 'LINE-UP')]]",
            "//div[contains(@class, 'Tab') and .//*[contains(text(), 'Lineups')]]",
            "//div[contains(@class, 'Tab') and .//*[contains(text(), 'LINEUPS')]]",
            # Add button selectors
            "//button[contains(@data-tabid, 'player')]",
            "//button[contains(@data-tabid, 'lineup')]",
            "//a[contains(@data-tabid, 'player')]",
            "//a[contains(@data-tabid, 'lineup')]"
        ]
        
        player_tab = None
        for selector in tab_selectors:
            try:
                elements = driver.find_elements(By.XPATH, selector)
                if elements:
                    player_tab = elements[0]
                    logger.info(f"Found player tab using selector: {selector}")
                    break
            except Exception as e:
                continue
        
        # Find the player statistics table
        table = None
        table_selectors = [
            "table.Table.fEUhaC", 
            "table[class*='Table']", 
            "//table[contains(@class, 'Table')]"
        ]
        
        for selector in table_selectors:
            try:
                if selector.startswith("//"):
                    # XPATH selector
                    table = WebDriverWait(driver, 15).until(
                        EC.presence_of_element_located((By.XPATH, selector))
                    )
                else:
                    # CSS selector
                    table = WebDriverWait(driver, 15).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                    )
                logger.info(f"Found player table using selector: {selector}")
                break
            except TimeoutException:
                continue
                
        if not table and player_tab:
            try:
                # Click the player tab if found and table not yet found
                logger.info("Clicking player tab...")
                driver.execute_script("arguments[0].click();", player_tab)
                time.sleep(2)  # Wait for content to load
                
                # Try to find table again after clicking
                for selector in table_selectors:
                    try:
                        if selector.startswith("//"):
                            # XPATH selector
                            table = WebDriverWait(driver, 15).until(
                                EC.presence_of_element_located((By.XPATH, selector))
                            )
                        else:
                            # CSS selector
                            table = WebDriverWait(driver, 15).until(
                                EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                            )
                        logger.info(f"Found player table after clicking, using selector: {selector}")
                        break
                    except TimeoutException:
                        continue
            except Exception as e:
                logger.error(f"Error clicking player tab: {e}")
                
        if not table:
            logger.error("Could not find player statistics table")
            
            # Debug info
            logger.info(f"Current page title: {driver.title}")
            logger.info(f"Current URL: {driver.current_url}")
            
            # Save page source for debugging
            try:
                with open("debug_page_source.html", "w", encoding="utf-8") as f:
                    f.write(driver.page_source)
                logger.info("Saved page source to debug_page_source.html")
            except Exception as e:
                logger.error(f"Failed to save page source: {e}")
                
            return pd.DataFrame()
            
        # Collect basic player data
        data = collect_player_data(driver, table)
        
        if not data:
            logger.error("No player data found in the table")
            return pd.DataFrame()
            
        logger.info(f"Collected basic data for {len(data)} players")
        all_dataframes = pd.DataFrame(data, columns=['Player', 'Player_ID', 'Team'])
        
        # Define the stat groups to scrape
        button_groups = {
            'General': ['summaryGroup', 'summary'],
            'Attacking': ['attackGroup', 'attack'],
            'Defending': ['defenceGroup', 'defence'],
            'Passing': ['passingGroup', 'passing'],
            'Duels': ['duelsGroup', 'duels'],
            'Goalkeeping': ['goalkeeperGroup', 'goalkeeper']
        }

        for name, tab_ids in button_groups.items():
            logger.info(f"Trying to click {name} tab...")
            
            # Try all possible tab IDs
            button = None
            for tab_id in tab_ids:
                try:
                    # Try by data-tabid attribute
                    button = WebDriverWait(driver, 5).until(
                        EC.element_to_be_clickable((By.XPATH, f"//button[@data-tabid='{tab_id}']"))
                    )
                    break
                except TimeoutException:
                    # Try by text content
                    try:
                        button = WebDriverWait(driver, 3).until(
                            EC.element_to_be_clickable((By.XPATH, f"//button[contains(., '{name}')]"))
                        )
                        break
                    except TimeoutException:
                        continue
            
            if button:
                try:
                    # Click the button and wait for the table to update
                    driver.execute_script("arguments[0].click();", button)
                    time.sleep(1)  # Wait for table to update
                    
                    # Extract data from the table
                    table_data = scrape_table_data(driver)
                    if not table_data.empty:
                        # Ensure the "Player" column exists for merging
                        if "Player" not in table_data.columns:
                            if len(table_data.columns) > 0:
                                table_data = table_data.rename(columns={table_data.columns[0]: "Player"})
                        
                        # Handle "Notes" column if it exists
                        if "Notes" in table_data.columns:
                            table_data = table_data.rename(columns={"Notes": f"Notes {name}"})
                        
                        # Merge with main dataframe
                        all_dataframes = pd.merge(all_dataframes, table_data, on='Player', how='outer', suffixes=('', '_dup'))
                        logger.info(f"Successfully scraped {name} data")
                    else:
                        logger.warning(f"No data found in {name} tab")
                except Exception as e:
                    logger.error(f"Error scraping {name} tab: {e}")
            else:
                logger.warning(f"Could not find {name} tab button")

        # Add match metadata
        return finalize_game_metadata(driver, all_dataframes)
    except Exception as e:
        logger.error(f"Error in click_and_scrape: {e}")
        return pd.DataFrame()

def finalize_game_metadata(driver, df):
    """
    Adds match metadata like home/away team, date, and score.
    
    Args:
        driver (WebDriver): Selenium WebDriver instance
        df (pd.DataFrame): DataFrame containing player statistics
        
    Returns:
        pd.DataFrame: DataFrame with added metadata
    """
    if df.empty:
        return df
        
    logger.info("Adding match metadata...")
    
    try:
        # Get away team
        away_team = "Unknown"
        away_team_selectors = [
            'div[data-testid="right_team"] img',
            '//div[contains(@class, "right_team") or contains(@data-testid, "right_team")]//img',
            '//div[contains(@class, "away") or contains(@data-testid, "away")]//img'
        ]
        
        for selector in away_team_selectors:
            try:
                if selector.startswith("//"):
                    # XPATH selector
                    element = driver.find_element(By.XPATH, selector)
                else:
                    # CSS selector
                    element = driver.find_element(By.CSS_SELECTOR, selector)
                
                away_team = element.get_attribute("alt").strip()
                if away_team:
                    break
            except NoSuchElementException:
                continue
        
        logger.info(f"Away team: {away_team}")

        # Get home team
        home_team = "Unknown"
        home_team_selectors = [
            'div[data-testid="left_team"] img',
            '//div[contains(@class, "left_team") or contains(@data-testid, "left_team")]//img',
            '//div[contains(@class, "home") or contains(@data-testid, "home")]//img'
        ]
        
        for selector in home_team_selectors:
            try:
                if selector.startswith("//"):
                    # XPATH selector
                    element = driver.find_element(By.XPATH, selector)
                else:
                    # CSS selector
                    element = driver.find_element(By.CSS_SELECTOR, selector)
                
                home_team = element.get_attribute("alt").strip()
                if home_team:
                    break
            except NoSuchElementException:
                continue
        
        logger.info(f"Home team: {home_team}")

        # Assign home/away status
        df['Home/Away'] = df['Team'].apply(
            lambda x: '1' if x == home_team else ('0' if x == away_team else 'unknown')
        )

        # Get match date
        match_date = datetime.now().strftime("%Y-%m-%d")  # Default to today
        date_found = False
        
        date_selectors = [
            "div.d_flex.ai_center.br_lg.bg-c_surface\.s2.py_xs.px_sm.mb_xs.h_\[26px\]",
            "//div[contains(@class, 'date')]",
            "//span[contains(@class, 'date')]"
        ]
        
        for selector in date_selectors:
            try:
                if selector.startswith("//"):
                    # XPATH selector
                    element = driver.find_element(By.XPATH, selector)
                else:
                    # CSS selector
                    element = driver.find_element(By.CSS_SELECTOR, selector)
                
                date_text = element.text
                
                # Extract date part (assuming format like "DD/MM/YY")
                date_parts = date_text.split()
                for part in date_parts:
                    if '/' in part and len(part) >= 6:  # Likely a date
                        date_str = part.replace("/", "")
                        try:
                            # Try multiple date formats
                            for fmt in ["%d%m%y", "%d%m%Y"]:
                                try:
                                    parsed_date = datetime.strptime(date_str, fmt)
                                    match_date = parsed_date.strftime("%Y-%m-%d")
                                    date_found = True
                                    break
                                except ValueError:
                                    continue
                            
                            if date_found:
                                break
                        except Exception as e:
                            logger.warning(f"Error parsing date '{date_str}': {e}")
                
                if date_found:
                    break
            except NoSuchElementException:
                continue
        
        logger.info(f"Match date: {match_date}")
        df['Date'] = match_date

        # Get score
        score = "0-0"  # Default score
        score_selectors = [
            "//span[contains(@class, 'Text jVxayx')]/ancestor::div[contains(@class, 'Box iCtkKe')]",
            "//div[contains(@class, 'score') or contains(@data-testid, 'score')]",
            "//div[contains(@class, 'result') or contains(@data-testid, 'result')]"
        ]
        
        for selector in score_selectors:
            try:
                element = driver.find_element(By.XPATH, selector)
                score_text = element.text.strip()
                
                if '-' in score_text:
                    # Extract the score part if there's additional text
                    for part in score_text.split():
                        if '-' in part and len(part) >= 3:
                            score = part
                            break
                    else:
                        score = score_text
                    break
            except NoSuchElementException:
                continue
        
        logger.info(f"Match score: {score}")
        df['Score'] = score

        # Fill NaN values
        df = df.fillna('0')
        
    except Exception as e:
        logger.error(f"Error extracting metadata: {e}")

    return df

def single_game_scraper(url):
    """
    Scrapes a single game's player statistics.
    
    Args:
        url (str): URL of the SofaScore match
        
    Returns:
        pd.DataFrame: DataFrame containing player statistics
    """
    logger.info(f"Starting to scrape match: {url}")
    
    # First try API approach
    logger.info("Attempting to get data from API...")
    api_data = get_match_data_from_api(url)
    
    if not api_data.empty:
        logger.info(f"Successfully retrieved data from API for {len(api_data)} players")
        return api_data
    
    logger.info("API approach failed, falling back to browser scraping...")
    
    driver = None
    
    try:
        driver = create_driver()
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                logger.info(f"Loading URL (attempt {retry_count+1}/{max_retries})")
                driver.get(url)
                time.sleep(3)  # Wait for page to load
                
                # Accept cookies if present
                try:
                    cookie_button = WebDriverWait(driver, 5).until(
                        EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Accept') or contains(., 'OK') or contains(., 'Got it')]"))
                    )
                    cookie_button.click()
                    logger.info("Accepted cookies")
                    time.sleep(1)
                except:
                    # No cookie banner or already accepted
                    pass
                
                result_df = click_and_scrape(driver)
                if not result_df.empty:
                    logger.info(f"Successfully scraped data for {len(result_df)} players using browser approach")
                    return result_df
                else:
                    logger.warning(f"No data found after scraping attempt {retry_count+1}")
                
                retry_count += 1
                if retry_count < max_retries:
                    wait_time = 2 * retry_count
                    logger.info(f"Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                
            except Exception as e:
                logger.error(f"Error during scraping (attempt {retry_count+1}/{max_retries}): {e}")
                retry_count += 1
                if retry_count < max_retries:
                    wait_time = 2 * retry_count
                    logger.info(f"Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
        
        logger.error(f"Failed to scrape match after {max_retries} attempts")
        return pd.DataFrame()
        
    except Exception as e:
        logger.error(f"Unhandled error: {e}")
        return pd.DataFrame()
    finally:
        if driver:
            driver.quit()

def main():
    parser = argparse.ArgumentParser(description="Scrape player statistics from SofaScore football matches.")
    parser.add_argument('--url', help='SofaScore match URL', required=True)
    parser.add_argument('--output', help='Output CSV filename', default="scraped_game.csv")
    parser.add_argument('--verbose', action='store_true', help='Enable verbose logging')
    args = parser.parse_args()
    
    # Set logging level based on verbose flag
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    
    logger.info(f"Starting scraper for URL: {args.url}")
    logger.info(f"Output will be saved to: {args.output}")
    
    start_time = time.time()
    df = single_game_scraper(args.url)
    duration = time.time() - start_time
    
    if not df.empty:
        df.to_csv(args.output, index=False)
        logger.info(f"Successfully scraped data for {len(df)} players in {duration:.2f} seconds")
        logger.info(f"Data saved to {args.output}")
    else:
        logger.error(f"Failed to scrape data after {duration:.2f} seconds")

if __name__ == "__main__":
    main()
