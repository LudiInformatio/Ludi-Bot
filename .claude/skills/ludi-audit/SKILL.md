---
name: ludi-audit
description: >
  Henrik's 11-point Ludi-specific gotcha checklist. Runs AFTER /simplify.
  Catches silent pipeline failures, data quality issues, and technical debt
  patterns that are unique to the Ludi-Bot codebase and would not be caught
  by a generic code review. Invoke with: "/ludi-audit review [file(s)]".
agent: henrik
context: fork
user-invocable: true
---

# Ludi Audit

**Last Updated:** March 4, 2026
**Owner:** Henrik (Code Auditor)

## Overview

This skill is an 11-point checklist of known Ludi-specific failure patterns — bugs and gotchas
that have caused real production issues in this codebase. It is NOT a generic code quality
review (that is `/simplify`'s job). Every check maps to a documented real failure.

Run this skill on any changed Python file or set of files before returning APPROVED.

## When to Use

- Use for: any `.py` file change — scripts, modules, utils, bots
- Use for: any change that touches `bet_recommendations`, `games`, or `canonical_*` tables
- Use for: any ROADMAP.md header edit (ROADMAP contract check only)
- Don't use for: docs-only changes, `.yml` workflow edits, `.md` files (except ROADMAP.md)
- Run AFTER: `/simplify` (which handles generic code quality)

---

## Workflow

Work through all 11 checks in order. For each check, scan the diff/file for the pattern.
If the pattern is absent from the changed code, mark ✅ pass. If found, flag with severity.

---

### P0 — Pipeline Breakers (any P0 failure = REVIEW_REQUIRED)

**Check 1 — BDL Abbreviation Normalization**

Scan for string literals: `'GS'`, `'NO'`, `'NY'`, `'PHO'`, `'SA'` used as team abbreviations.

- FAIL if: any new script defines a local dict with BDL short-form abbrevs (e.g., `{'GS': 'Golden State', ...}`)
- FAIL if: any hardcoded BDL abbrev used in a SQL `WHERE team = 'GS'` or similar
- PASS if: code calls `normalize_bdl_abbr(abbr)` from `utils/mappings.py`

*Root cause: BDL uses GS/NO/NY/PHO/SA; the rest of the pipeline uses GSW/NOP/NYK/PHX/SAS.
Hardcoded dicts break on every team that has a non-obvious mapping.*

---

**Check 2 — canonical_games for Pattern-B JOINs**

Scan for: `JOIN games` followed by `ON` with both a date condition AND a team condition.

- FAIL if: `JOIN games g ON g.date = ... AND (g.home_team = ... OR g.away_team = ...)`
- PASS if: `JOIN canonical_games cg ON cg.canonical_game_id = ...`

*Root cause: the `games` table stores 3 row formats per game (NBA official ID / shortened ID /
date-team ID). A Pattern-B JOIN matches all 3 rows and inflates counts by 3×.
canonical_games (902 rows) is the deduplicated single-row-per-game source.*

---

**Check 3 — No DB Connections Inside Simulation Loops**

Scan for: `sqlite3.connect()` inside any method named `run_simulation_batch()`,
`run_simulation()`, `simulate_player()`, or inside any `for player in players:` loop.

- FAIL if: DB connection opened inside a per-player or per-iteration loop
- PASS if: all data is pre-loaded at `__init__()` into dicts; zero DB calls during simulation

*Root cause: Module C runs 10,000 iterations per player. Opening a DB connection inside the
loop adds ~0.1s per player × 30 players = 3+ minutes of silent latency per game.*

---

**Check 4 — bet_recommendations Schema Sync**

If the diff adds or removes a column from `bet_recommendations`:

- FAIL if: column exists in `database.py` CREATE TABLE but NOT in `utils/bet_logger.py` CREATE TABLE (or vice versa)
- PASS if: both files are updated in the same commit

*Root cause: `database.py` and `utils/bet_logger.py` both define the `bet_recommendations`
CREATE TABLE independently. Adding a column to one without the other causes silent NULL
values or INSERT failures depending on which file ran first.*

---

**Check 5 — Tank01 Composite ID Contamination**

Scan for: any INSERT or UPDATE to `player_canonical_ids` where `canonical_id` has 8+ digits
and does NOT start with `1` (valid NBA IDs are 6-7 digits starting with 1 or 2).

- FAIL if: `canonical_id` is a Tank01 composite ID (e.g., `38017656`, `94184479027`, `942541715989`)
- FAIL if: `players.player_id` matches a Tank01 composite format instead of NBA ID
- PASS if: `canonical_id` is a valid NBA ID (e.g., `1630590`, `1641842`, `203915`)

*Root cause: Tank01 API generates composite IDs (8-11 digits) that differ from real NBA IDs
(6-7 digits, prefix 1-2). If a dirty ID enters `player_canonical_ids.canonical_id`, all
downstream JOINs (game_logs → players → canonical) silently produce 0 rows for that player.
The player becomes invisible to the pipeline — no bets generated, no injury resolution, no
archetype assignment. Diagnosed Mar 4, 2026: Pippen Jr. (MEM) and 3 others had dirty IDs
as canonical values, producing 0 module flow for active starters.*

---

### P1 — Data Quality (any P1 failure = APPROVED_WITH_NOTES, must fix before next pipeline run)

**Check 6 — Player Name Resolution Before Claude Prompts**

Scan for: any player name sourced from Odds API (raw string) passed directly into a DB
query or Claude prompt without name resolution.

- WARN if: `player_name` (or similar) used in a SQL `WHERE name = ...` without first calling
  `resolve_canonical_name(conn, player_name)` from `utils/player_id_resolver.py`
- PASS if: `resolve_canonical_name()` is called before any DB lookup or prompt injection

*Root cause: Odds API returns non-accented names ("Nikola Jokic"). The DB stores accented
canonical names ("Nikola Jokić"). Direct lookup returns 0 rows — injury shows as "none on
record" even when player is OUT.*

---

**Check 7 — No AI Training Data for Roster/Trade Info**

Scan for: hardcoded player-team dicts in any new or modified file.

- FAIL if: `{'LeBron James': 'LAL', 'Steph Curry': 'GSW', ...}` style assignments
- FAIL if: any comment like `# current as of Jan 2026` near a hardcoded roster
- PASS if: roster data sourced from `players` table, `player_canonical_ids`, Tank01, or BDL

*Root cause: AI training data is always stale. Trades, injuries, two-way contracts, and
call-ups change weekly. Hardcoded rosters cause wrong team assignments in sim context.*

---

**Check 8 — canonical_teams for ID Mappings**

Scan for: new `ESPN_TEAM_IDS = {...}` or `BDL_TEAM_IDS = {...}` style dicts in new code.

- WARN if: any new script defines its own team ID lookup dict
- PASS if: code calls `_load_espn_team_ids(conn)` or queries `canonical_teams` table

*Root cause: `canonical_teams` (30 rows) is the single source of truth for all
BDL/Tank01/ESPN team ID mappings. Local dicts go stale and diverge silently.*

---

### P2 — Technical Debt (P2 findings = APPROVED_WITH_NOTES, schedule for cleanup)

**Check 9 — team_totals Endpoint**

Scan for: `markets=team_totals` in any bulk odds API call.

- WARN if: `team_totals` passed to `/v4/sports/basketball_nba/odds` (bulk endpoint)
- PASS if: fetched via per-event `/events/{event_id}/odds?markets=team_totals`

*Root cause: Odds API bulk endpoint returns 422 for team_totals and silently drops the
entire slate. Must be fetched per-event at 1 credit/game.*

---

**Check 10 — Python 3.11 f-string Backslash Rule**

Scan for: backslash characters (`\"`, `\'`, `\n`) inside `{...}` expression blocks within f-strings.

- WARN if: `f"...{some_dict[\"key\"]}..."` — backslash inside braces
- PASS if: value extracted to a variable first: `val = some_dict["key"]; f"...{val}..."`

*Root cause: Python 3.11 raises SyntaxError for backslash escapes inside f-string expression
blocks. Fixed in 3.12, but this project runs 3.11.*

---

**Check 11 — Silent Exception Swallowing**

Scan for: bare `except` or `except Exception:` followed by `continue` or `pass` with no logging.

- WARN if: `except Exception: continue` or `except: pass` with no `logger.warning()` or `logger.error()`
- PASS if: `except Exception as e: logger.warning(f"[context] {e}"); continue`

*Root cause: Silent failures make pipeline bugs invisible. A player that fails silently
produces 0 bets with no alert — looks like a quiet day, not a bug.*

---

### New Data Script Gate (if a new `scripts/*.py` that writes to DB is in the diff)

Before marking APPROVED, verify:
- The script has been run with `--dry-run` against the live `ludi.db` (not just compiled)
- All SQL column names match the actual table schema (`PRAGMA table_info(table_name)`)
- No `no such column` errors in the dry-run output

*Root cause: `compute_empirical_modifiers.py` shipped with 3 column name mismatches
(`season`/`min`/`is_starter` vs actual `season_id`/`minutes`/`started`). Passed code
review but failed on first production run. 3 consecutive nightly failures before detection.*

---

### ROADMAP Contract (only if ROADMAP.md is in the diff)

If `ROADMAP.md` was modified, verify the header block:

- `**Active Work:**` first ` + ` segment contains a backtick-wrapped filename or class name
- `**Completed:**` has exactly 3 ` + ` segments (PM bot reads `parts[-3:]`)
- `### Current Sprint` section contains a `**Next Actions:**` block with `- [ ]` bullets

FAIL the ROADMAP contract if any condition is violated — the PM bot will generate generic output.

---

## Tech Debt Logging

After completing the 11 checks, if ANY P1 or P2 finding represents a NEW pattern not already in `docs/TECH_DEBT.md`:
1. Append a new `TD-XXX` entry to `docs/TECH_DEBT.md` with severity, location, description, impact, and recommended fix
2. Note the new entry in your audit output under the relevant check

This ensures every audit finding that isn't immediately fixed gets tracked for future cleanup.

---

## Output Format

Return exactly this format. No preamble. Start directly with `## Ludi Audit`.

```
## Ludi Audit — [filename(s) reviewed]

P0 — Pipeline Breakers
✅/🚨 BDL Abbreviation — [pass or finding]
✅/🚨 canonical_games JOIN — [pass or finding]
✅/🚨 DB in sim loop — [pass or finding]
✅/🚨 bet_recommendations sync — [pass or finding]
✅/🚨 Tank01 composite ID — [pass or finding]

P1 — Data Quality
✅/⚠️ Player name resolution — [pass or finding]
✅/⚠️ No AI roster data — [pass or finding]
✅/⚠️ canonical_teams IDs — [pass or finding]

P2 — Technical Debt
✅/⚠️ team_totals endpoint — [pass or finding]
✅/⚠️ Python 3.11 f-strings — [pass or finding]
✅/⚠️ Silent exceptions — [pass or finding]

ROADMAP contract: ✅ N/A | ✅ pass | 🚨 [finding]

Verdict: APPROVED | APPROVED_WITH_NOTES | REVIEW_REQUIRED
[One sentence summary of the most important finding, or "All checks pass."]
```

**Verdict rules:**

- `APPROVED` — all P0 and P1 checks pass (P2 warnings allowed)
- `APPROVED_WITH_NOTES` — P1 warnings present, or P2 findings that need cleanup scheduling
- `REVIEW_REQUIRED` — any P0 failure, or ROADMAP contract violation

## References

- `best-practices/ai/SKILLS_GUIDE.md` — skill anatomy + refinement protocol
- `best-practices/coding/README.md` — general coding patterns
- `best-practices/data/CANONICAL_NAME_RESOLUTION.md` — accent handling (Check 5)
- `best-practices/ops-hub/KNOWN_FIXES.md` — production failure log (source of these checks)
- `docs/TECH_DEBT.md` — Technical debt register (append findings here)
- `AGENTS.md` — Definition of Done (Henrik sign-off required before merge)
