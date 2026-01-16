#!/usr/bin/env python3
"""
Test Basketball-Reference accessibility by opening in browser.
This bypasses Python's requests library and uses your actual browser,
which may have better success avoiding 403 blocks.
"""

import webbrowser
import time

def test_bbr_urls():
    """Open Basketball-Reference URLs in browser for manual testing."""

    urls_to_test = [
        ("Referee Roster 2026", "https://www.basketball-reference.com/referees/2026_register.html"),
        ("Recent Games (Box Scores)", "https://www.basketball-reference.com/boxscores/"),
        ("Sample Box Score (Jan 14)", "https://www.basketball-reference.com/boxscores/202601140LAL.html"),
    ]

    print("=" * 60)
    print("BASKETBALL-REFERENCE BROWSER TEST")
    print("=" * 60)
    print("\nThis will open 3 URLs in your default browser.")
    print("Check if each page loads successfully.\n")

    for name, url in urls_to_test:
        print(f"Opening: {name}")
        print(f"URL: {url}")
        webbrowser.open(url)
        print("✅ Opened in browser\n")
        time.sleep(2)  # Brief delay between opens

    print("=" * 60)
    print("MANUAL VERIFICATION CHECKLIST:")
    print("=" * 60)
    print("\n1. Referee Roster 2026:")
    print("   - Does the page load?")
    print("   - Can you see a table with referee names?")
    print("   - Are there foul statistics (PF/G column)?")
    print("\n2. Recent Games:")
    print("   - Does the page load?")
    print("   - Can you see today's/recent game results?")
    print("\n3. Sample Box Score:")
    print("   - Does the page load?")
    print("   - Can you see 'Officials:' section with referee names?")
    print("   - Can you see total fouls in the box score?")
    print("\n" + "=" * 60)
    print("If pages load in browser but fail via Python requests,")
    print("we'll need Selenium browser automation for scraping.")
    print("=" * 60)

if __name__ == "__main__":
    test_bbr_urls()
