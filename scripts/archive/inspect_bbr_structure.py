#!/usr/bin/env python3
"""
Inspect Basketball-Reference page structure to find correct selectors.
"""

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import time

# Test URLs
urls = {
    "Referee Roster": "https://www.basketball-reference.com/referees/2026_register.html",
    "Recent Box Scores": "https://www.basketball-reference.com/boxscores/",
}

def inspect_page(url, name):
    print("\n" + "=" * 60)
    print(f"INSPECTING: {name}")
    print("=" * 60)

    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)

    try:
        driver.get(url)
        time.sleep(2)  # Let page load

        print(f"\n✅ Loaded: {driver.title}\n")

        # Get page source (first 2000 chars to check structure)
        source = driver.page_source

        # Look for referee-related content
        if "Officials:" in source:
            print("✅ Found 'Officials:' in page")
            # Find the line with Officials
            for line in source.split('\n'):
                if 'Officials:' in line:
                    print(f"   Line: {line[:200]}")  # First 200 chars
                    break

        # Check for common table IDs
        table_ids = ['stats', 'referees', 'officials', 'per_game', 'all_stats']
        for table_id in table_ids:
            if f'id="{table_id}"' in source or f"id='{table_id}'" in source:
                print(f"✅ Found table with ID: {table_id}")

        # Look for scorebox
        if 'scorebox' in source:
            print("✅ Found 'scorebox' div (box score games)")

    except Exception as e:
        print(f"❌ Error: {e}")

    driver.quit()

if __name__ == "__main__":
    for name, url in urls.items():
        inspect_page(url, name)

    print("\n" + "=" * 60)
    print("INSPECTION COMPLETE")
    print("=" * 60)
