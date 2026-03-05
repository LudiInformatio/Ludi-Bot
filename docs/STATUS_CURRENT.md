# Current System Status

**Last Updated:** March 4, 2026
**Phase:** Phase 8 — AI-Enhanced Pipeline

## Active Sprint
- Curation Engine v2 (`curate_plays.py`, `utils/game_dossier.py`) — full-slate STRONG/LEAN/FADE grading + shared Perplexity cache + employee onboarding prep
- Ask Ludi Bot (`bots/ask_ludi.py`) — v1 live, 7 intents, data freshness layer shipped (ghost guard, slate context, ESPN fallback)
- Phase 8.23 Feedback Loop — `claude_analysis_log` collecting, Wilson calibration at ~Mar 10

## Last 3 Major Completions
- Curation v2: 3-layer decision tree (math → dossier → Claude), shared cache, BERT Pattern 2, full-slate grading ✅
- CLV Hardening: `game_date` logger fix, closing lines wired nightly via `db_backup.yml`, Feb 27–Mar 1 backfill ✅
- `bet_recommendations` dedup: 17,202 dupes removed, UNIQUE INDEX `idx_bet_recs_no_dupes`, INSERT OR IGNORE ✅

## Database State (Mar 4, 2026)
- `player_canonical_ids`: 638 players, 99.79% clean canonical IDs post full remediation
- `player_game_logs`: ~18,400 rows, 99.2% plus_minus coverage
- `bet_recommendations`: 9,293 rows (post-dedup), UNIQUE INDEX active
- `prop_line_snapshots`: CLV data starts 2026-02-27

## Full Documentation
- Full sprint history: `docs/STATUS_HISTORY.md`
- Current tasks + priorities: `ROADMAP.md`
- System design + schema: `docs/ARCHITECTURE.md`
- Jan 2026 phase archive: `docs/archive/phase_reports/PHASES_1_4_AND_INFRA_SUMMARY.md`
