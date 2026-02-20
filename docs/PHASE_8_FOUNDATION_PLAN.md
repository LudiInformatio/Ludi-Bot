# Phase 8 Foundation Plan: Shared Claude Infrastructure + Injury Intelligence

**Status:** ✅ COMPLETE — All steps shipped (Phases 8.0-A through 8.0-D)
**Completed:** February 2026
**Priority:** ~~CRITICAL~~ ARCHIVED — no longer blocking
**Related:** See `ROADMAP.md` Phase 8 | Design doc: `.claude/plans/curried-growing-toucan.md`
**Last Revised:** February 19, 2026 7:39 PM EST

---

## Executive Summary

Phase 8.0 consists of two sequential concerns:

1. **Pre-Work (Step 0):** Shared Claude infrastructure — auth wrapper + prompt library. Zero API cost. Blocking everything that follows.
2. **Injury Intelligence (Steps 1–5):** Persistent, intraday-safe injury tracking. Standalone sync script. Module D is NOT touched.

**Part B (Rotation Intelligence) has been moved to `docs/PHASE_8_9_ROTATION_PLAN.md`** — it is Phase 8.9 scope, not a blocker for Phase 8.0.

---

## SMA Audit Findings (Feb 17, 2026 — Pre-Implementation)

| Check | Severity | Result |
|-------|----------|--------|
| Temporal integrity | Critical | ✅ CLEAN |
| Feature coverage | High | ✅ CLEAN |
| Entity resolution | Medium | ⚠️ 55 players with no canonical ID match |

**Live DB State Corrections vs Old Plan:**
| Item | Old Plan Said | Actual |
|------|---------------|--------|
| GENERALIST % | 31.4% — BLOCKING | **20.0% — TARGET ACHIEVED** ✅ |
| `player_injuries` table | needs creating | Does not exist (confirmed) |
| `current_injury_status` on `players` | needs adding | Does not exist (confirmed) |
| NBA.com CDN injury endpoint | "option" | **CONFIRMED BROKEN Feb 2026** (403/empty) |

---

## Pre-Work: Shared Claude Infrastructure (Step 0 — BLOCKING)

**Purpose:** Foundation for all Phase 8 Claude calls. Nothing else starts without this.

### Auth Architecture (No Separate API Key)

Auth priority (OAuth-first):
```python
# utils/claude_client.py
def _get_claude_auth_token() -> str:
    # Priority 1: GitHub Actions secret
    if os.getenv('CLAUDE_CODE_OAUTH_TOKEN'):
        return os.getenv('CLAUDE_CODE_OAUTH_TOKEN')
    # Priority 2: Local Claude Code config
    config_path = os.path.expanduser('~/.claude/config.json')
    if os.path.exists(config_path):
        try:
            data = json.load(open(config_path))
            if data.get('oauthToken'):
                return data['oauthToken']
        except Exception:
            pass
    # Priority 3: Explicit API key (future fallback)
    return os.getenv('ANTHROPIC_API_KEY', '')
```

### Files to Create / Modify

| File | Action | What |
|------|--------|------|
| `utils/claude_client.py` | CREATE | OAuth-first auth, `HAIKU_MODEL`/`SONNET_MODEL` constants, `get_claude_analysis()`, token tracking, graceful degradation |
| `utils/claude_prompts.py` | CREATE | `ROSTER_RULES`, `GAME_NOTES_TEMPLATE`, `SPOTLIGHT_TEMPLATE` |
| `config.py` | MODIFY | Add `CLAUDE_AUTH_TOKEN = _get_claude_auth_token()` |
| `.env.template` | MODIFY | Add `CLAUDE_CODE_OAUTH_TOKEN=your-token-here  # From Max plan` |

### Model Constants

```python
# utils/claude_client.py
HAIKU_MODEL = "claude-haiku-4-5-20251001"   # Sanity gates, classification
SONNET_MODEL = "claude-sonnet-4-6"           # Narratives, curation

# Temperature guide:
# 0.1 — math-adjacent (sanity gates, Top 5 curation)
# 0.2 — player spotlights, game notes
# 0.3 — freestyle/narrative only
```

### Acceptance Test

```bash
python -c "from utils.claude_client import HAIKU_MODEL, SONNET_MODEL; print('OK', HAIKU_MODEL, SONNET_MODEL)"
python -c "from utils.claude_prompts import ROSTER_RULES, GAME_NOTES_TEMPLATE; print('prompts OK')"
python -c "from config import CLAUDE_AUTH_TOKEN; print('auth token present:', bool(CLAUDE_AUTH_TOKEN))"
```

---

## Part A: Injury Intelligence System (Steps 1–5)

### Problem Statement

**Current State:**
- Injuries are in-memory only (`yak_cache.json`, 15-min TTL)
- No persistence, no history, no audit trail
- Long-term injured players (30+ days) silently disappear from pipeline
- BDL `return_date` and `description` (rich metadata) are fetched but discarded
- No distinction between injury vs data gap
- No intraday snapshots — status can change multiple times on game day

**What changes on game day:**
- GTD players resolve to OUT or ACTIVE
- Late scratches appear after lineup lock (~6:30 PM)
- Injury updates can flip a bet from valid to void

---

### Step 1 — Database Schema

**File:** `database.py`

#### New Table: `player_injuries` (Intraday-Safe Design)

```sql
CREATE TABLE IF NOT EXISTS player_injuries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    player_name TEXT NOT NULL,
    team_abbreviation TEXT,
    status TEXT NOT NULL,          -- OUT, DOUBTFUL, QUESTIONABLE, PROBABLE, ACTIVE
    injury_type TEXT,              -- "Ankle sprain", "Knee soreness", etc.
    return_date TEXT,              -- YYYY-MM-DD or NULL
    days_out INTEGER,              -- Calculated: onset_date → return_date or today
    onset_date TEXT,               -- When injury first appeared in our records
    description TEXT,              -- Full BDL narrative (50-200 words)
    source TEXT,                   -- 'BDL', 'Tank01'
    snapshot_time TEXT DEFAULT CURRENT_TIMESTAMP,  -- When THIS record was captured
    is_game_day_report BOOLEAN DEFAULT 0,          -- TRUE if captured <8h before any game
    resolved_at TEXT               -- When player returned to ACTIVE (NULL = still out)
);

-- Fast "current status" lookup
CREATE INDEX IF NOT EXISTS idx_injuries_player_latest
    ON player_injuries(player_name, snapshot_time DESC);
-- Game-day snapshots
CREATE INDEX IF NOT EXISTS idx_injuries_game_day
    ON player_injuries(snapshot_time, is_game_day_report);
-- Active injuries
CREATE INDEX IF NOT EXISTS idx_injuries_active
    ON player_injuries(status, resolved_at);
```

**Why intraday-safe:** Multiple rows per player per day are normal and intentional. Each sync creates a new row only when status changes (not on every run). `snapshot_time` allows full audit trail.

#### Additions to `players` Table

```sql
ALTER TABLE players ADD COLUMN current_injury_status TEXT DEFAULT 'ACTIVE';
ALTER TABLE players ADD COLUMN injury_updated_at TEXT;
ALTER TABLE players ADD COLUMN injury_return_date TEXT;
ALTER TABLE players ADD COLUMN days_out_current INTEGER DEFAULT 0;
```

#### Also Fix: 55-Player Canonical ID Gap

During schema work, query and repair the 55 players missing from `player_canonical_ids`:

```sql
-- Identify gap
SELECT p.name FROM players p
LEFT JOIN player_canonical_ids c ON p.name = c.player_name
WHERE c.player_name IS NULL;
```

Then upsert via Tank01/BDL ID lookup for each unmatched player.

**Acceptance Test:**
```bash
python database.py
sqlite3 ludi.db "SELECT COUNT(*) FROM player_injuries;"
sqlite3 ludi.db "SELECT COUNT(*) FROM players WHERE current_injury_status IS NOT NULL;"
# Canonical gap check
sqlite3 ludi.db "SELECT COUNT(*) FROM players p LEFT JOIN player_canonical_ids c ON p.name = c.player_name WHERE c.player_name IS NULL;"
```

---

### Step 2 — Standalone Sync Script

**File:** `scripts/sync_injuries.py`

**Design principle:** Module D stays exactly as-is (in-memory cache, 15-min TTL). Injury persistence is a completely separate, standalone concern.

**What it does:**
1. Call BDL API → get active injuries (primary source: structured fields, return_date, description)
2. For each team playing today, call `tank01_client.get_team_roster()` → extract embedded injury fields (Tank01 fallback)
3. Status-change detection: only insert new `player_injuries` row when status changes vs last snapshot
4. Always update `players.current_injury_status` + `players.injury_updated_at`
5. Calculate `days_out` from `onset_date` to today (or `return_date` if known)
6. Set `is_game_day_report=1` when run within 8 hours of any scheduled game tipoff

**What it does NOT do:**
- Does NOT modify `module_d.py`
- Does NOT add helper methods to any existing module
- Does NOT call any AI/Claude
- Does NOT use NBA.com CDN injury endpoint (confirmed broken Feb 2026)

**Status-change detection logic:**
```python
# Only insert new record if status CHANGED since last snapshot
last = db.query("""
    SELECT status FROM player_injuries
    WHERE player_name = ? ORDER BY snapshot_time DESC LIMIT 1
""", name)

if not last or last['status'] != new_status:
    db.insert('player_injuries', new_record)  # Status changed → log it

# Always update players fast-lookup columns regardless
db.execute("""
    UPDATE players SET
        current_injury_status = ?,
        injury_updated_at = CURRENT_TIMESTAMP,
        injury_return_date = ?,
        days_out_current = ?
    WHERE name = ?
""", new_status, return_date, days_out, player_name)
```

**Acceptance Test:**
```bash
python scripts/sync_injuries.py --dry-run
python scripts/sync_injuries.py
sqlite3 ludi.db "SELECT player_name, status, description FROM player_injuries WHERE resolved_at IS NULL LIMIT 5;"
sqlite3 ludi.db "SELECT name, current_injury_status FROM players WHERE current_injury_status != 'ACTIVE' LIMIT 10;"
```

---

### Step 3 — Three-Tier Active Roster

**File:** `main.py` (lines 80-96, `get_active_roster()` filter)

**Tier logic:**
- **Tier 1:** Active (game logs last 30 days, ≥3 games) — existing behavior, unchanged
- **Tier 2:** Recently returned (`player_injuries.resolved_at` last 7 days) — add to simulation with flagged context ("WELCOME BACK" tag)
- **Tier 3:** Long-term out (`days_out > 14`) — log reason, skip simulation, include in injury intel for Telegram

**Backward compatibility:** If `player_injuries` table is empty, falls back to Tier 1 only. No crash.

```python
# Tier 2 query example
recently_returned = db.query("""
    SELECT DISTINCT p.name, p.team, p.position, p.archetype
    FROM players p
    JOIN player_injuries i ON p.name = i.player_name
    WHERE i.resolved_at >= date('now', '-7 days')
      AND i.resolved_at IS NOT NULL
""")
```

**Acceptance Test:**
```bash
python main.py --dry-run 2>&1 | grep -E "Tier|INJURY|recently.returned|long.term"
```

---

### Step 4 — Smart Vacuum Enhancement

**File:** `module_x_scenario.py`

**Goal:** Replace the current usage vacuum (which uses API averages and keyword-based long-term detection) with full S.A.V.A.G.E. infrastructure.

| Signal | Old Approach | New Approach | Advantage |
|--------|-------------|--------------|-----------|
| Base stats | API averages | `player_game_logs` L10 | Hot streaks, recent form |
| Absorbed detection | Long-term injury keywords | `player_injuries.days_out` | Exact days, not guessing |
| Beneficiary selection | Position-only | Position + `player_wowy_stats` on/off delta | Measured impact |
| Pace modifier | Game total from API | `games.pace` from DB | Our own calculated pace |
| Archetype fit | Not applied | `archetype` + scheme matrix | Full matchup modifier |
| Trade deadline | Manual overrides | Roster history query | Dynamic |

**Classification logic (using our DB):**
```python
def _classify_vacuum_smart(out_player_name: str, team_abbr: str) -> dict:
    # Exact days_out from DB (not keyword matching)
    inj = db.query("""
        SELECT days_out, status FROM player_injuries
        WHERE player_name = ? AND resolved_at IS NULL
        ORDER BY snapshot_time DESC LIMIT 1
    """, out_player_name)

    if not inj:
        return {'status': 'skip', 'scale': 0.0, 'reason': 'Not in injury table'}

    days_out = inj['days_out'] or 0

    if days_out > 14:
        return {'status': 'absorbed', 'scale': 0.0, 'reason': f'{days_out} days — team adjusted'}
    elif days_out <= 3:
        return {'status': 'active', 'scale': 1.0, 'reason': f'Recent absence ({days_out}d)'}
    else:
        # Partial: scale 0.3–1.0 based on days
        scale = round(1.0 - ((days_out - 3) / 11 * 0.7), 2)
        return {'status': 'partial', 'scale': scale, 'reason': f'{days_out}d out — {int(scale*100)}% weight'}
```

**Constraint:** Output format unchanged — Module F reads the same vacuum dict structure.

**Acceptance Test:**
```bash
python -c "
from module_x_scenario import ScenarioBuilder
sb = ScenarioBuilder()
result = sb.build_vacuum_scenarios_for_game('LAL', 'DEN')
for k, v in result.items():
    print(f'{k}: scale={v.get(\"vacuum_scale\",0):.1f}, beneficiary={v.get(\"primary_beneficiary\",\"none\")}')
"
```

---

### Step 5 — Workflow Wiring

**Files modified:**
- `.github/workflows/data_sync.yml` — add injury sync step (after `sync_bdl_game_logs`)
- `.github/workflows/daily_briefing.yml` — add pre-brief injury refresh
- `.github/workflows/capture_closing_lines.yml` — add pre-tipoff injury refresh (most critical)

**Intraday sync schedule:**
| Time | Workflow | is_game_day_report | Purpose |
|------|---------|-------------------|---------|
| 5 AM EST | `data_sync.yml` | 0 | Overnight refresh |
| 11 AM EST | `daily_briefing.yml` | 1 | Pre-morning-brief |
| 5:30 PM EST | `capture_closing_lines.yml` | 1 | Pre-tipoff (critical) |

**`data_sync.yml` snippet:**
```yaml
- name: Sync Injuries (Overnight)
  run: |
    source .venv/bin/activate
    python scripts/sync_injuries.py
  env:
    IS_GAME_DAY_REPORT: "false"
```

**Acceptance Test:**
```bash
python scripts/sync_injuries.py  # direct run verifies it works
sqlite3 ludi.db "SELECT status, COUNT(*) FROM player_injuries WHERE resolved_at IS NULL GROUP BY status;"
```

---

## Critical Files Summary

| Step | File | Action |
|------|------|--------|
| 0 | `utils/claude_client.py` | CREATE — OAuth-first auth, model constants, graceful degradation |
| 0 | `utils/claude_prompts.py` | CREATE — ROSTER_RULES, game notes template, spotlight template |
| 0 | `config.py` | MODIFY — add `CLAUDE_AUTH_TOKEN` |
| 0 | `.env.template` | MODIFY — add `CLAUDE_CODE_OAUTH_TOKEN` |
| 1 | `database.py` | MODIFY — add `player_injuries` (intraday-safe) + 4 `players` columns |
| 2 | `scripts/sync_injuries.py` | CREATE — standalone BDL+Tank01, status-change detection |
| 3 | `main.py` | MODIFY — three-tier roster (lines 80-96) |
| 4 | `module_x_scenario.py` | MODIFY — smart vacuum using DB |
| 5 | `.github/workflows/data_sync.yml` | MODIFY — add injury sync step |
| 5 | `.github/workflows/daily_briefing.yml` | MODIFY — add pre-brief refresh |
| 5 | `.github/workflows/capture_closing_lines.yml` | MODIFY — add pre-tipoff refresh |

**NOT touched:** `module_d.py` (in-memory cache stays as-is)

---

## Acceptance Criteria

### Pre-Work (Step 0) ✅
- [x] `from utils.claude_client import HAIKU_MODEL, SONNET_MODEL` works
- [x] `from utils.claude_prompts import ROSTER_RULES, GAME_NOTES_TEMPLATE` works
- [x] `from config import CLAUDE_AUTH_TOKEN; bool(CLAUDE_AUTH_TOKEN)` is True locally and in Actions

### Injury Intelligence (Steps 1–5) ✅
- [x] `player_injuries` table exists with correct schema (`snapshot_time`, `is_game_day_report` columns present)
- [x] `players` table has `current_injury_status`, `injury_updated_at`, `injury_return_date`, `days_out_current` columns
- [x] 55-player canonical ID gap resolved (entity resolution audit shows 0 unmatched)
- [x] `sync_injuries.py --dry-run` completes without error
- [x] `sync_injuries.py` populates `player_injuries` with 10+ rows
- [x] Status-change detection works: re-running sync doesn't insert duplicates for same status
- [x] `players.current_injury_status` synced for all known injured players
- [x] Long-term injured players (days_out > 14) appear in Tier 3, NOT in simulation
- [x] Recently returned players (resolved_at last 7 days) appear in Tier 2 simulation
- [x] Smart vacuum correctly classifies: active (<4 days out), partial (4–14 days), absorbed (>14 days)
- [x] BDL `description` stored in DB (not discarded)
- [x] Phase 8.5 ready: `player_injuries.description` available for Claude sanity gate context

### SMA Audit Post-Implementation
```bash
python scripts/audit_temporal_integrity.py --db ludi.db   # must be clean
python scripts/audit_feature_coverage.py --db ludi.db     # must be clean
python scripts/audit_entity_resolution.py --db ludi.db    # 0 canonical gaps (was 55)
```

---

## Dependencies

**Required:**
- BallDontLie API (GOAT tier) — primary injury data with `return_date` + `description`
- Tank01 API (PAID) — injury fallback via team roster embedded fields
- `CLAUDE_CODE_OAUTH_TOKEN` — GitHub Actions secret (already exists ✅)

**Confirmed broken — do NOT use:**
- NBA.com CDN `injury-report_{date}.json` → 403 Forbidden as of Feb 2026
- NBA.com `ak-static.cms.nba.com` injury endpoint → empty/denied

---

## Phase 8.5+ Integration (Next)

Once Pre-Work and Steps 1–5 are complete:
- **Phase 8.5 (Step 6):** `scripts/curate_plays.py` — Haiku sanity gate reads `player_injuries.description` to flag contradictions. Sonnet Top 5 reasons about correlation + diversification.
- **Phase 8.2 (Step 7):** Game notes cards read `player_injuries.days_out` for injury impact section. Format: structured S.A.V.A.G.E. cards (not wall-of-text paragraphs).
- **Phase 8.3 (Step 8):** Player spotlights read `player_injuries` to flag minutes limits.

All Claude calls receive deterministic DB data — Claude reasons, never calculates.

---

## Residual Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| OAuth token behavior in Python SDK may differ from API key | HIGH | Test in Step 0 acceptance; fallback to requesting API key from Max plan dashboard |
| BDL `return_date` field NULL for some injuries | MEDIUM | NULL is fine; `days_out` calculated from `onset_date` → today |
| 55 canonical ID gap causes sync failures | MEDIUM | Fix in Step 1 before any sync runs |
| Smart vacuum needs `player_wowy_stats` populated | MEDIUM | Falls back to `player_game_logs` L10 if WOWY table sparse |
| Game notes token cost higher on 15-game nights | LOW | Add per-game token limit; truncate low-priority games |

---

**For rotation intelligence (Phase 8.9), see:** `docs/PHASE_8_9_ROTATION_PLAN.md` (to be created)
**For questions or updates, see:** `ROADMAP.md` Phase 8
