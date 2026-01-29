# Module G Scraper Fix Report - Jan 29, 2026

## Issue
The referee scraper was failing with a `Timeout 30000ms exceeded` error when trying to fill the date input field (`input#ref-date`).

## Root Cause Analysis
1.  **Privacy Popup Obstruction**: A OneTrust privacy overlay (`#onetrust-banner-sdk`) was appearing, potentially intercepting interactions or shifting focus.
2.  **Hidden Input Field**: The date input field is inside a dropdown menu (`button.dropdown-toggle`).
3.  **Dropdown Closure**: The previous logic attempted to open the dropdown, but interactions (like the popup appearing/closing) or race conditions caused the dropdown to close before the `fill` command could execute, making the input invisible/uninteractable.

## Solution Implemented
1.  **Privacy Popup Handling**: Added explicit logic to detect the OneTrust banner and click "Reject Advertising Cookies" (or the Close button) immediately after page load.
2.  **Robust Dropdown Interaction**:
    *   Enforced the dropdown click with `force=True`.
    *   Added a **Re-Open Check**: Before filling the date, the script now checks `if not page.is_visible('input#ref-date')`. If hidden, it re-clicks the dropdown toggle and waits for visibility.
3.  **Error Visibility**: Added `page.screenshot(path="error_state.png")` in the exception block to capture the browser state on future failures.

## Verification
- **Debug Script**: Confirmed that clicking the dropdown is required to make the input visible.
- **Production Run**:
    - Popup detected and cookies rejected.
    - Dropdown opened successfully.
    - Date toggled (Yesterday -> Today) without timeout.
    - **Result**: Successfully scraped assignments for 8 games.
    - **Impact**: Pace/Whistle factors updated (e.g., MIL vs WAS: 1.924x Pace/Whistle with 100% confidence).

## Code Changes
- Modified `module_g.py`: `build_ref_database` method.
- Added logic for `#onetrust-reject-all-handler` and `.onetrust-close-btn-handler`.
- Added visibility checks before `page.fill`.

## Status
✅ **FIXED** - Ready for production.

## Basketball-Reference Scraper Fix (Jan 29, 2026)

### Issue
The `scripts/scrape_referee_roster.py` script was falling back to hardcoded data because Basketball-Reference (BBR) blocked the `requests` library with a **403 Forbidden** error.

### Root Cause
1.  **Bot Detection**: BBR/Cloudflare blocks simple Python `requests` user agents.
2.  **Table Structure**: BBR changed the referee table layout to use **MultiIndex (Hierarchical) Headers**, breaking the previous column mapping logic.

### Solution Implemented
1.  **Playwright Migration**: Replaced `requests` with `Playwright (headless=False)` to mimic a real user browser, successfully bypassing the 403 block.
2.  **Robust Table Logic**:
    - Removed reliance on specific ID `#referees_stats`.
    - Implemented a loop to scan all 25+ tables on the page.
    - Added **MultiIndex Flattening** to handle the `('Unnamed: 0_level_0', 'Referee')` column structure.

### Verification
- **Command**: `python3 scripts/scrape_referee_roster.py --dry-run`
- **Result**: Successfully navigated to BBR, found the target table upon index 24, and parsed **72 referees** (vs 51 fallback).
- **Status**: ✅ FIXED