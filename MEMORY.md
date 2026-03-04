# MEMORY.md — Ludi-Bot Knowledge Base

### CLV Tracking Start Date (Feb 27, 2026)
- `prop_line_snapshots` started collecting data 2026-02-27. Zero CLV coverage before that date.
- `bet_recommendations.clv_cents` backfilled Feb 27–Mar 1 via `backfill_historical_odds.py` (~200 credits).
- Closing lines populate nightly via `db_backup.yml` → `capture_closing_lines.py --game-date yesterday`.
- JOIN key: `(game_date, player_name, LOWER(stat_category))` — stat_category fixed to lowercase in module_b.py (Mar 4).
- Phase 8.23 CLV analysis: use `game_date >= '2026-02-27'` as floor. Filter `ABS(clv_cents) < 200` for clean mean (extreme outliers = thin market pricing gaps, not errors).
- `ODDS_API_KEY_BACKFILL` is reserved for April historical season backfill only — never use for current-season CLV.

---

## Full Project Audit

### Post-Audit Best Practices (Feb 21, 2026)
- 3 critical patterns integrated: Schema Constraint Validation, Module-Level Constants, Parameter Propagation Debugging
