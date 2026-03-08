# CLAUDE.md

This file provides guidance to Claude Code when working with code in this repository.
It is supplemental context only. `AGENTS.md` is the primary operating guide for Codex-style agent behavior.

## Instruction Precedence

When instructions conflict, use this order:
1. `AGENTS.md` (primary agent operating rules)
2. `ROADMAP.md` (current phase and priorities)
3. `CLAUDE.md` (supplemental project context)

**Repository**: https://github.com/LudiInformatio/Ludi-Bot.git

---

## Project Context

See @ROADMAP.md for current tasks and priorities.
See @docs/ARCHITECTURE.md for system design and module reference.
See @docs/METHODOLOGY.md for betting edge calculations.
See @docs/STATUS_CURRENT.md for current system state.
See docs/STATUS_HISTORY.md for full sprint history (not auto-loaded).
See @docs/TOOLS_GUIDE.md for task automation scripts and helpers.

---

## Critical Data Rules

**NEVER use AI training data for NBA roster/player/trade knowledge.** The AI's training data is outdated and WILL produce incorrect results (wrong teams, missed trades, phantom transactions).

Instead, ALWAYS use these sources for current-season truth:
1. **`ludi.db` database** — `players` table (current rosters), `player_game_logs` (game-by-game team assignments), `player_canonical_ids` (ID mappings)
2. **Live APIs** — Tank01 (`RosterValidator`), Ball Don't Lie (`BDLClient`), PBP Stats
3. **`player_game_logs.team_abbreviation`** — Tracks which team a player played for on each game date (historical proof of trades)

**Examples of what NOT to do:**
- Do NOT assume which players were traded based on AI memory
- Do NOT hardcode trade lists from general knowledge
- Do NOT guess player team assignments — query the database or API

**The correct process for roster/trade operations:**
1. Query our database first (`players`, `player_game_logs`)
2. If needed, fetch LIVE data from Tank01 or BDL APIs
3. Compare API data vs database to detect changes
4. Never fill gaps with AI assumptions

**Database Firewall (4-Tier) - Mandatory for all ingestion:**
To prevent ID contamination (e.g., Tank01 composite IDs like `28398804489` vs canonical `1629029`), all ingestion scripts MUST use the `LudiHistorian.resolve_player_id_for_insert(id, name)` firewall in `database.py`.
1. **Tier 1 (Exact):** Pass through if ID is already canonical (1xxxxxx or 2xxxxxx, length <= 7).
2. **Tier 2 (Alias):** Check `aliases` and `tank01_aliases` JSON columns in `player_canonical_ids`.
3. **Tier 3 (Name):** Resolve via `PlayerIDResolver` (normalized name match) + **Auto-register** the dirty ID as a new alias.
4. **Tier 4 (Fallback):** Log `logger.warning()` and return original ID (triggers manual review).

**Current NBA season is 2025-26.** Never use AI training data for current rosters, trades,
or injury status — it will be wrong. Players change teams, get injured, and return throughout
the season. The AI's knowledge cutoff predates this season's moves. Always verify against
`ludi.db` or a live API call before making any roster or injury assumption.

**This rule applies to mock scenarios and prompt examples too.** When writing or editing
example prompts, format templates, or test scenarios in `utils/claude_prompts.py` or
anywhere else — never hardcode a player's team from AI training memory. Either:
1. Query `ludi.db` first: `SELECT name, team FROM players WHERE name = '...';`
2. Use clearly generic placeholders: `[PLAYER]`, `[TEAM]`, `[BOS starter]`
3. Use `build_archetype_system_prompt(conn)` pattern — examples built from DB at runtime

**Multi-team trade paths must be accepted as-is from the database.** Players can have
offseason trades AND mid-season trades — `player_game_logs.team_abbreviation` is the
authoritative record. Example: Anfernee Simons (POR → BOS offseason, BOS → CHI mid-season
2025-26) — the database correctly shows BOS,CHI. Never question multi-team histories that
look "wrong" from training data memory. The API data is always right; training data is stale.

---

## Quick Commands

```bash
# Activate environment
source .venv/bin/activate

# Run main pipeline
.venv/bin/python main.py

# Run integration test (1 game, verbose)
.venv/bin/python main.py --limit-games 1 --verbose

# Initialize database
.venv/bin/python database.py

# Test individual modules
python -c "from module_a import Gatekeeper; gk = Gatekeeper(); print(gk.fetch_live_slate())"
python -c "from module_d import LudiYak; print(LudiYak().get_injuries())"

# Send Telegram test
python -c "from utils.telegram_notifier import send_message; send_message('Test')"

# Start Ask Ludi bot (Phase 8.13)
.venv/bin/python bots/ask_ludi.py
```

> **Note:** Paper trade any model changes before deploying to production. Back up the database before running migration scripts.

---

## Database Management

**IMPORTANT:** `ludi.db` is NOT tracked in git. Full backup/restore docs in `docs/PRODUCTION_HANDBOOK.md`.

```bash
bash scripts/backup_database.sh                                          # create backup
bash scripts/restore_database.sh archives/data/ludi.db.backup_YYYYMMDD_HHMMSS.gz  # restore
```

---

## Module Reference

See `docs/ARCHITECTURE.md` → "Module Class Names Reference" for the full table with import examples. Use exact class names only — wrong names cause ImportError.

---

## Project Identity

- **Colors**: Dark Navy #0F172A, Gold #FBBF24, Emerald #10B981
- **Voice**: Professional, Tactical, "Asset Management" (No "locks" or gambling slang)
- **Iconography**: IYKYK Elite Set (diamond, blueprint, pour, toast, counter-punch, frosty)

---

## Environment Setup

Key `.env` variables (see `.env.template` for full list):
- `ODDS_API_KEY`, `TANK01_KEY`, `BALLDONTLIE_KEY` (required)
- `TELEGRAM_TOKEN`, `TELEGRAM_CHAT_ID` (notifications)
- `GEMINI_API_KEY` (optional — Ask Ludi chatbot)
- `DEBUG_LOG`, `IS_PRODUCTION` (flags)

---

## Automation Schedule

See `docs/PRODUCTION_HANDBOOK.md` for the full workflow schedule (all times, triggers, and purposes). All workflows run on a self-hosted macOS runner.

---

## Known Gotchas

> **See also:** `best-practices/ai/COMMON_MISTAKES.md` for recurring Claude Code session mistakes, SQL schema traps, and silent failure patterns with prevention rules.

- Referee assignments require web scraping (can fail if NBA.com changes HTML)
- DuckDuckGo search in Module D can be rate-limited — use sparingly
- Module I (Aggregator) is placeholder code — not yet implemented
- Runner DB symlink: `actions-runner/.../ludi.db` → local project DB. Don't break the symlink.
- BDL abbreviation mismatches (GS→GSW, NO→NOP, NY→NYK, PHO→PHX, SA→SAS) — always use `normalize_bdl_abbr()` from `utils/mappings.py`. See `best-practices/ai/COMMON_MISTAKES.md` §2.3.
- Always use correct class names — see ARCHITECTURE.md "Module Class Names Reference" for the full table with import examples.
- Player name resolution: Odds API returns non-accented names (e.g. "Nikola Jokic") but `player_injuries` + `players` tables store canonical names with accents (e.g. "Nikola Jokić"). Always call `resolve_canonical_name(conn, player_name)` from `utils/player_id_resolver.py` before any name-based DB query in Claude prompt pipelines
- `canonical_teams` table (30 rows) is the single source of truth for BDL/Tank01/ESPN team ID mappings — do NOT hardcode `ESPN_TEAM_IDS` dicts in new scripts
- `canonical_games` table (955+ rows) is the single source of truth for game identity — use for any JOIN on `(date, home_team, away_team)` (Pattern-B) to prevent 3× row inflation. The `games` table has 3 duplicate game_id formats per game (NBA official / shortened / date-team). Call `from database import sync_canonical_games` and `sync_canonical_games(conn)` after any INSERT INTO games. Never use `JOIN games g ON g.date = ... AND (g.home_team = ... OR g.away_team = ...)` — use `canonical_games` instead.
- **Odds-API `team_totals`** — NOT supported on the bulk `/v4/sports/basketball_nba/odds` endpoint (returns 422, drops entire slate). Fetch separately via `/v4/sports/{sport}/events/{event_id}/odds?markets=team_totals`. Per-event format: `outcome['description']=team name`, `outcome['name']=Over/Under`. Cost: 1 credit/game.
- **`start_time` from JSON cache is a string** — `save_games_cache()` serializes `datetime` → string. After `load_games_cache()`, always parse with `datetime.fromisoformat(start_time)` before accessing `.tzinfo` or comparing with `datetime.now()`.
- **Tank01 `getNBADepthCharts` format change (2026-03)** — Tank01 changed response from `{"ATL": {...}}` (dict keyed by team) to `[{"teamAbv": "ATL", ...}]` (list of 30 objects). `utils/tank01_client.get_depth_charts()` normalizes both → always returns dict. Also: Tank01 depth charts use BDL-style abbreviations (NY/GS/NO/PHO/SA) — `normalize_bdl_abbr()` is applied automatically inside `get_depth_charts()`. Do NOT call it again at the call site.
- **Team Defensive Schemes** — always query `team_scheme_cache` table (`WHERE scheme_type='DEFENSE'`). Never rely on any hardcoded list in docs — schemes update mid-season.
- **ROADMAP.md Template Contract** — When any agent updates `ROADMAP.md`, preserve these patterns so `utils/pm_bot.py` parses correctly:
  - `**Active Work:**` — short phrase(s) separated by ` + `. First segment = current sprint focus (shown in break messages).
  - `**Completed:**` — keep the last 3 completions as separate ` + ` segments at the end (PM bot reads `parts[-3:]`).
  - `### Current Sprint` section — must include a `**Next Actions:**` block with `- [ ]` bullets for actionable tasks. The PM bot's pending task list comes ONLY from here; the Phase 8 table is status-tracking only and NOT parsed for tasks.
  - Never collapse all completions into one segment or remove the ` + ` delimiters — it breaks the parser.
- **`## Project Vision` in README.md is permanent** — never delete, reorder above the License section, or trim its content. Update `*Last updated:*` and the "Where it is now" / "Where it's headed" bullets periodically. This section is institutional memory, not bloat.

---

## Employee Delegation (MANDATORY)

**When the user explicitly asks an employee to do work, delegate immediately — do not do the work yourself.**

This is an explicit authorization from the owner. When the user says "have Henrik do X", "send to Lena", "have the junior dev implement", or any similar phrasing that routes a task to a named employee:

1. **Launch the appropriate agent** using the Agent tool (`subagent_type: henrik`, `lena`, `silas`, or `general-purpose` for the junior dev / Gemini)
2. **Do not read files, write code, or make edits yourself** before delegating
3. **Pass the full task context** in the agent prompt so they can work autonomously
4. **Report back** what the employee did, any issues they found, and the commit hash

**Employee roster:**
- **Henrik** (`subagent_type: henrik`) — Code Auditor & Reviewer. Plans, reviews, and approves diffs. Never writes code — delegates implementation to junior dev. Use `isolation: worktree` for safe read access during audits.
- **Silas** (`subagent_type: silas`) — Infrastructure monitor. Read-only, health checks only.
- **Lena** (`subagent_type: lena`) — Data analyst. Queries ludi.db, reviews plans, signs off on data logic. Uses `/sma` for data model audit/design — outputs specs to Solomon, not implementation.
- **Junior dev / Gemini** — General-purpose agent (`subagent_type: general-purpose`) or Bash `gemini` CLI for code writing tasks.

**"Send to Henrik" delegation pipeline (MANDATORY — applies to all "send to henrik" / "have henrik do X" commands):**
1. Henrik reviews the plan/spec and identifies what needs to be built
2. Junior dev (Gemini / general-purpose agent) writes the code or files
3. Henrik audits the junior dev output → APPROVED or REVIEW_REQUIRED
Never skip steps — Henrik never writes code himself, junior dev never ships without Henrik's audit.

**Workflow when employee sign-off triggers execution:**
Lena approves plan → automatically delegate to Henrik + junior dev to execute → report back. No need to ask the user for a second approval after an employee has signed off.

---

## Custom Skills

This project has custom skills available:
- `/session-brief` - Start-of-session orientation (ROADMAP + memory + git log — read-only)
- `/session-debrief` - End-of-session wrap-up (update docs, commit, send PM bot break)
- `/backtest` - Run validation suite and check model accuracy
- `/daily` - Daily pipeline health check
- `/sports-model` (alias: `/sma`) - Use `skills/sports-data-model-architect` for balanced audit-first data modeling + implementation support
- `/ludi-audit` - Henrik's 11-point Ludi-specific gotcha checklist (run after `/simplify` on any diff)

---

## Resources

- **Roadmap**: @ROADMAP.md (tasks & priorities)
- **Architecture**: @docs/ARCHITECTURE.md (pipeline, schema, modules)
- **Methodology**: @docs/METHODOLOGY.md (edge calc, line shopping, CLV)
- **Current State**: @docs/STATUS_CURRENT.md (active sprint + DB state)
- **Status History**: docs/STATUS_HISTORY.md (full sprint archive — not auto-loaded)
- **Production Handbook**: @docs/PRODUCTION_HANDBOOK.md
- **Best Practices**: `best-practices/` directory — key files listed below (no auto-load; open manually):
  - **API Best Practices**: `best-practices/api/API_BEST_PRACTICES.md` (comprehensive guide)
  - **API Quick Reference**: `best-practices/api/API_QUICK_REFERENCE.md` (cheatsheet)
  - **Canonical Name Resolution**: `best-practices/data/CANONICAL_NAME_RESOLUTION.md` (accent handling across APIs, two-direction transforms, injection point table)
  - **PM Bot Notes Guide**: `best-practices/ai/PM_BOT_NOTES_GUIDE.md` (how to write ROADMAP header lines so PM bot messages are specific, not generic)
  - **Common Mistakes**: `best-practices/ai/COMMON_MISTAKES.md` (recurring Claude Code mistakes — DPO-style prevention rules, schema traps, silent failure patterns)
- **Tools Guide**: @docs/TOOLS_GUIDE.md (automation scripts, helpers)
- **Research**: `docs/research/` (competitive analysis, prompt engineering)
