# Ghost Protocol Status & Implementation Guide

**Last Updated:** January 17, 2026
**Topic:** NBA.com Data Scraping (WOWY / Lineups)

## Critical Architecture Decision
**Ghost Protocol (Playwright)** is the **ONLY** validated method for scraping `stats.nba.com`. All other methods (requests, standard selenium, hidden headless) are blocked by the WAF.

## Required Configuration
To successfully bypass detection, the browser instance MUST be initialized with:
1.  **`headless=False`** (The browser window must be visible)
2.  **`--disable-http2`** (Forces HTTP/1.1, critical for avoiding TLS fingerprinting blocks)

## Reference Implementations
*   **Production Pattern:** `scripts/sync_browser_backfill.py` (Use this structure for iterating dates and handling DB upserts).
*   **Config Reference:** `scripts/test_wowy_hybrid.py` (Contains the exact Playwright `launch` args that work).

## Current Status (WOWY Backfill)
*   **Script Created:** `scripts/sync_wowy_backfill.py`
    *   Implements the `DATA_MANIFEST` pattern.
    *   Target URLs: 5-Man Lineups & Player On/Off Stats.
*   **Database:**
    *   Table `team_lineups` created.
    *   Table `player_on_off_stats` created.
*   **Action Items:**
    *   Execute `python scripts/sync_wowy_backfill.py --days 60` to populate the database.
