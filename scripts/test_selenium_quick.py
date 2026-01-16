#!/usr/bin/env python3
"""
Quick test of Selenium + ChromeDriver setup.
Tests accessing Basketball-Reference referee roster page.
"""

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

def test_selenium():
    print("=" * 60)
    print("SELENIUM + CHROMEDRIVER TEST")
    print("=" * 60)

    print("\n1. Setting up Chrome driver...")
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")

    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        print("   ✅ Chrome driver initialized")
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return

    print("\n2. Testing Basketball-Reference access...")
    url = "https://www.basketball-reference.com/referees/2026_register.html"

    try:
        driver.get(url)
        print(f"   ✅ Loaded: {url}")

        # Check if page loaded
        page_title = driver.title
        print(f"   📄 Page title: {page_title}")

        # Try to find referee table
        try:
            table = driver.find_element(By.ID, "stats")
            print(f"   ✅ Found referee stats table!")

            # Count rows (approximate referee count)
            rows = table.find_elements(By.TAG_NAME, "tr")
            print(f"   📊 Found {len(rows)} table rows")

        except Exception as e:
            print(f"   ⚠️  Could not find table: {e}")

    except Exception as e:
        print(f"   ❌ Error loading page: {e}")

    driver.quit()
    print("\n" + "=" * 60)
    print("TEST COMPLETE")
    print("=" * 60)

if __name__ == "__main__":
    test_selenium()
