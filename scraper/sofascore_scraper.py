"""
SofaScore Scraper
=================
This script scrapes detailed player statistics from SofaScore football matches.
"""

import argparse
import time
import os
import sys
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
                
        if not table:
            logger.error("Could not find player statistics table")
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
            "div.d_flex.ai_center.br_lg.bg-c_surface\\.s2.py_xs.px_sm.mb_xs.h_\\[26px\\]",
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
                
                # Try to find the player tab
                logger.info("Looking for PLAYER tab...")
                player_tab = None
                
                # Try multiple selectors for player tab
                tab_selectors = [
                    "//div[contains(@class, 'Tab') and contains(text(), 'PLAYER')]",
                    "//div[contains(@class, 'Tab') and contains(text(), 'Player')]",
                    "//div[contains(@class, 'Tab') and .//*[contains(text(), 'PLAYER')]]",
                    "//div[contains(@class, 'Box') and contains(@class, 'Tab') and contains(text(), 'PLAYER')]"
                ]
                
                for selector in tab_selectors:
                    try:
                        elements = driver.find_elements(By.XPATH, selector)
                        if elements:
                            player_tab = elements[0]
                            break
                    except:
                        continue
                
                if not player_tab:
                    # Try to find all tabs and then filter by text
                    try:
                        elements = WebDriverWait(driver, 20).until(
                            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.Box.bkrWzf.Tab.cbSGUp.secondary, div[class*='Tab']"))
                        )
                        
                        for e in elements:
                            if 'PLAYER' in e.text.upper():
                                player_tab = e
                                break
                    except:
                        pass
                
                if player_tab:
                    logger.info("Found PLAYER tab, clicking...")
                    driver.execute_script("arguments[0].click();", player_tab)
                    time.sleep(2)  # Wait for content to load
                    
                    result_df = click_and_scrape(driver)
                    if not result_df.empty:
                        logger.info(f"Successfully scraped data for {len(result_df)} players")
                        return result_df
                    else:
                        logger.warning(f"No data found after clicking player tab")
                else:
                    logger.warning(f"No PLAYER tab found")
                
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