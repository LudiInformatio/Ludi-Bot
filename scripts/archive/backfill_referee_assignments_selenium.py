#!/usr/bin/env python3
"""
Backfill referee assignments using Selenium browser automation.
Scrapes Basketball-Reference for last 30 days of games.

Why Selenium: BBR blocks Python requests (403) but loads fine in browser.
Selenium uses a real Chrome browser to bypass bot detection.
"""

import sqlite3
import pandas as pd
import time
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager

DB_PATH = "ludi.db"

def setup_driver():
    """Initialize Chrome driver with options to avoid detection."""
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # Run in background
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)

    # User agent to look like real browser
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

    # Use webdriver-manager to auto-download ChromeDriver
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver

def get_games_to_backfill():
    """Get games from last 30 days that need referee data."""
    conn = sqlite3.connect(DB_PATH)
    thirty_days_ago = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')

    games = pd.read_sql_query("""
        SELECT game_id, date, home_team, away_team
        FROM games
        WHERE date >= ?
          AND (referee_crew IS NULL OR referee_crew = '')
        ORDER BY date DESC
    """, conn, params=(thirty_days_ago,))

    conn.close()
    return games

def convert_to_bbr_game_id(date_str, home_team):
    """
    Convert our date + home_team to Basketball-Reference game ID format.

    BBR Format: YYYYMMDD0TTT
    Example: 202601140LAL (Jan 14, 2026, Lakers home game)

    The '0' is a game number (usually 0 for single game that day).
    """
    # Parse date
    dt = datetime.strptime(date_str, '%Y-%m-%d')
    date_part = dt.strftime('%Y%m%d')

    # BBR uses 3-letter codes (same as ours mostly)
    # Special case: Brooklyn = BRK on BBR, we use BKN
    team_map = {
        'BKN': 'BRK',  # Brooklyn
        'PHX': 'PHO',  # Phoenix
        'CHA': 'CHO',  # Charlotte (sometimes)
    }

    bbr_team = team_map.get(home_team, home_team)

    # BBR game ID format
    game_id = f"{date_part}0{bbr_team}"
    return game_id

def scrape_game_referees_selenium(driver, date_str, home_team):
    """
    Scrape referee crew from Basketball-Reference box score using Selenium.

    Returns:
        list: Referee names, or None if failed
    """
    bbr_game_id = convert_to_bbr_game_id(date_str, home_team)
    url = f'https://www.basketball-reference.com/boxscores/{bbr_game_id}.html'

    try:
        driver.get(url)

        # Wait for page to load (up to 10 seconds)
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "content"))
        )

        # Find the "Officials:" section in the scorebox
        # BBR structure: <div class="scorebox_meta"><div>Officials: Name1, Name2, Name3</div></div>
        try:
            scorebox = driver.find_element(By.CLASS_NAME, "scorebox_meta")
            scorebox_text = scorebox.text

            # Look for "Officials:" line
            for line in scorebox_text.split('\n'):
                if 'Officials:' in line or 'Official:' in line:
                    # Extract names after colon
                    refs_part = line.split(':')[1].strip()
                    # Split by comma and clean
                    refs = [r.strip() for r in refs_part.split(',')]
                    return refs if refs else None

        except NoSuchElementException:
            # Try alternate location (sometimes in different div)
            try:
                # Look for any element containing "Officials:"
                elements = driver.find_elements(By.XPATH, "//*[contains(text(), 'Officials:')]")
                if elements:
                    text = elements[0].text
                    refs_part = text.split(':')[1].strip()
                    refs = [r.strip() for r in refs_part.split(',')]
                    return refs if refs else None
            except:
                pass

        return None

    except TimeoutException:
        print(f"    ⏱️  Timeout loading page")
        return None
    except Exception as e:
        print(f"    ❌ Error: {e}")
        return None

def main():
    print("=" * 60)
    print("BASKETBALL-REFERENCE REFEREE BACKFILL (SELENIUM)")
    print("=" * 60)
    print("\n⚙️  Setting up Chrome browser...")

    # Check if chromedriver is installed
    try:
        driver = setup_driver()
        print("✅ Chrome driver initialized\n")
    except Exception as e:
        print(f"❌ Chrome driver error: {e}")
        print("\n💡 Install ChromeDriver:")
        print("   macOS: brew install chromedriver")
        print("   Then: xattr -d com.apple.quarantine $(which chromedriver)")
        return

    # Get games to process
    games = get_games_to_backfill()
    print(f"📊 Found {len(games)} games to backfill")

    if len(games) == 0:
        print("✅ All games already have referee data!")
        driver.quit()
        return

    print(f"🎯 Target: Last 30 days ({games['date'].min()} to {games['date'].max()})\n")
    print("-" * 60)

    success_count = 0
    failed_count = 0

    for idx, game in games.iterrows():
        print(f"\n[{idx+1}/{len(games)}] {game['date']} {game['away_team']}@{game['home_team']}")

        refs = scrape_game_referees_selenium(driver, game['date'], game['home_team'])

        if refs:
            # Store to database
            conn = sqlite3.connect(DB_PATH)
            conn.execute("""
                UPDATE games
                SET referee_crew = ?
                WHERE game_id = ?
            """, (','.join(refs), game['game_id']))
            conn.commit()
            conn.close()

            success_count += 1
            print(f"    ✅ Stored: {', '.join(refs)}")
        else:
            failed_count += 1
            print(f"    ❌ Failed to scrape")

        # Rate limiting (be nice to BBR servers)
        time.sleep(3)

    driver.quit()

    print("\n" + "=" * 60)
    print("BACKFILL COMPLETE")
    print("=" * 60)
    print(f"✅ Success: {success_count}/{len(games)} games")
    print(f"❌ Failed: {failed_count}/{len(games)} games")

    if success_count > 0:
        print(f"\n📊 Database now has referee data for {success_count} additional games!")

    if failed_count > 0:
        print(f"\n⚠️  {failed_count} games failed - may be:")
        print("   - Future games (not played yet)")
        print("   - Incorrect game ID format")
        print("   - Page structure changed")

if __name__ == "__main__":
    main()
