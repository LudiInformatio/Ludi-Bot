# Module G Audit Prompt for External Agent

You are an expert AI auditor. Your task is to review the implementation of **Module G: Referee Intelligence** in the Ludi-Bot project.

## Context
The user has implemented a 5-phase upgrade to the referee module:
-   **Phase 1-3:** Database tables (`referee_profiles`, `referee_daily_stats`), scraper fallbacks, daily learning engine, and reporting suite.
-   **Phase 4:** "Hybrid Seeding" strategy using browser-extracted JSON from Basketball-Reference to populate 78 referees with 2025-26 season stats. Includes a `referee_player_bias` table for "Star Killer" tracking.
-   **Phase 5:** A Playwright-based "Ghost Browser" scraper (`scripts/sync_external_intelligence.py`) that pulls betting intelligence (O/U %, ATS Records) from Covers.com and OddsShark weekly.

## Your Audit Tasks

### 1. Code Quality Review
Examine the following files for correctness, edge case handling, and Python best practices:
-   `database.py` (Schema definitions for `referee_profiles`, `referee_daily_stats`, `referee_player_bias`)
-   `scripts/seed_referees.py` (JSON seeding logic)
-   `scripts/analyze_star_bias.py` (Forward learning engine)
-   `scripts/sync_external_intelligence.py` (Playwright scraper for betting data)
-   `utils/render_full_report.py` (Visual report with "Whistle Watch" footer)
-   `module_g.py` (Core referee engine)

### 2. Integration Check
Verify the data flow:
1.  `scrape_referee_roster.py` OR `seed_referees.py` → `referee_profiles` table.
2.  `sync_external_intelligence.py` → Updates `ou_percentage`, `home_ats_bias` columns.
3.  `module_g.py` reads `referee_profiles` and returns `{pace_impact, whistle_impact, crew, confidence}`.
4.  `render_full_report.py` queries `referee_profiles` and displays a "Whistle Watch" footer on visual cards.

### 3. Specific Questions to Answer
-   Are there any SQL injection vulnerabilities?
-   Is the Playwright scraper robust against site structure changes (e.g., uses `try/except`)?
-   Does the "style" classification (STRICT/LENIENT/NEUTRAL) logic match the documented thresholds?
-   Is the `referee_player_bias` table being populated correctly by `analyze_star_bias.py`?

### 4. Suggested Improvements
Provide a list of 3-5 actionable improvements for the next iteration.

## Location
The repository is at: `https://github.com/LudiInformatio/Ludi-Bot.git`
