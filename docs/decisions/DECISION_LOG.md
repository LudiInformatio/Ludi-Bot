# Decision Log (ADR — Architecture Decision Records)
**Last Updated:** March 8, 2026

This log captures significant decisions that affect the architecture, data model, ops, or product direction of Ludi-Bot. See `docs/decisions/ADR_TEMPLATE.md` for format.

---

## Skills 2.0 Hybrid Architecture
- **Date:** 2026-03-06
- **Domain:** architecture
- **Authorized by:** Owner
- **Context:** OpenClaw (open-source local runtime) was evaluated as the AI employee execution layer. Claude Code Skills 2.0 subagents (`.claude/agents/*.md`) were assessed as an alternative.
- **Decision:** Skills 2.0 hybrid — Claude Code subagents for interactive work, external stack (Telegram bots, GH Actions, launchd) for scheduled/always-on.
- **Rationale:** $0 incremental cost (uses Claude subscription), native Claude Code integration, faster to ship. OpenClaw added infrastructure overhead with no benefit given existing GH Actions automation.
- **Alternatives considered:** OpenClaw runtime, custom Python agent orchestration
- **Review date:** September 2026 (before 2026-27 season)

---

## Canonical Games Table for Pattern-B JOINs
- **Date:** 2026-02-28
- **Domain:** data
- **Authorized by:** Lena → Owner
- **Context:** The `games` table stores 3 duplicate game_id formats per game (NBA official / shortened / date-team), causing 3× row inflation on JOIN queries using `(date, home_team, away_team)` patterns.
- **Decision:** `canonical_games` table (902 rows) is the single source of truth for game identity. Use `canonical_game_id` (format: `{date}_{home}_{away}`) for all Pattern-B JOINs.
- **Rationale:** Eliminates 3× inflation without rewriting the `games` table. `sync_canonical_games(conn)` importable from `database.py`.
- **Alternatives considered:** Deduplicating `games` table, using DISTINCT in all queries

---

## bet_recommendations UNIQUE INDEX (Dedup Fix)
- **Date:** 2026-03-04
- **Domain:** data
- **Authorized by:** Owner
- **Context:** `bet_recommendations` had 17,202 duplicate rows out of 26,495 (65%). P&L unit totals were inflated 2–10× as a result.
- **Decision:** Added UNIQUE INDEX on `(game_date, player_name, stat_category, direction)`. All inserts use `INSERT OR IGNORE`.
- **Rationale:** Prevents future duplication at the DB layer without requiring application-level dedup logic.
- **Alternatives considered:** Application-level dedup on insert, periodic cleanup script

---

## CLV Supplementary-Only for Prop Markets
- **Date:** 2026-03-07
- **Domain:** product
- **Authorized by:** Lena → Owner
- **Context:** CLV (Closing Line Value) is the gold standard for model validation in game markets (Pinnacle closes sharp). Prop markets were being treated the same way.
- **Decision:** CLV is supplementary-only for player prop markets. Win rate + calibration (Brier Score) are primary metrics.
- **Rationale:** Prop markets lack sufficient sharp liquidity — the closing line is not an efficient price signal. Unabated research confirms this. CLV still tracked but not used as primary model validation metric.
- **Alternatives considered:** Using CLV as primary metric (same as game markets)
- **Review date:** June 2026 (reassess if Pinnacle expands prop coverage)

---

## DST Cron Update Approach (March 2026)
- **Date:** 2026-03-08
- **Domain:** ops
- **Authorized by:** Owner
- **Context:** US clocks moved to EDT (UTC-4) on March 8, 2026. All 17 GitHub Actions workflows use UTC cron schedules originally set for EST (UTC-5).
- **Decision:** Decrement UTC hour by 1 in all 17 `data_sync.yml` and related workflow cron expressions. Exclude launchd plists (macOS handles DST natively).
- **Rationale:** Direct 1-hour decrement is simpler than using timezone-aware cron libraries. launchd uses wall-clock time, not UTC.
- **Alternatives considered:** Using `TZ=America/New_York` in cron (not supported by GH Actions), dynamic UTC offset at runtime
