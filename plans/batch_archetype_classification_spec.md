# Batch Archetype Classification — Implementation Spec

**Status:** APPROVED (Lena sign-off below)
**Date:** 2026-03-10
**Author:** Henrik (Code Auditor) + Lena (Data Analyst)
**Implements:** Batch-by-team refactor of `scripts/classify_archetypes.py`
**Junior dev:** implement per this spec. Henrik will audit the diff before merge.

---

## Part 1 — Lena's Data Analysis

### Archetype Baseline (protect these numbers)

| Archetype | Count | % of Active |
|-----------|-------|-------------|
| GENERALIST | 143 | 29.1% |
| SNIPER_ELITE | 115 | 23.4% |
| CONNECTOR | 63 | 12.8% |
| ENERGY_BIG | 34 | 6.9% |
| CUTTER_SPECIALIST | 29 | 5.9% |
| TWO_LEVEL_SCORER | 21 | 4.3% |
| STRETCH_BIG | 21 | 4.3% |
| ROLL_MAN | 20 | 4.1% |
| HELIOCENTRIC_MAESTRO | 16 | 3.3% |
| SLASHING_CREATOR | 12 | 2.4% |
| Other (WARRIOR_BIG, ISO, etc.) | 18 | 3.6% |

**Total active: 492. NULL archetype: 0.**

### Bench Player Composition

- Active players with recent logs (last 30 days): 456
- Bench players (avg < 20 min/game): 220 = **48% of active roster**
- Bench archetype distribution: GENERALIST (85), SNIPER_ELITE (46), ENERGY_BIG (23), CUTTER_SPECIALIST (21), CONNECTOR (15)

**Key finding:** Nearly half of all active players are bench players. GENERALIST already dominates bench classifications (85/220 = 38.6%). This is the number to protect — batch anchoring risk is that this number drifts significantly higher.

### Archetype Instability / Highest-Risk Players

High-variance bench players (avg < 22 min, minute range > 15 in last 30 days) — these players are most at risk from batch degradation because their stat profiles are the least distinct:

| Player | Team | Current Archetype | Avg Min | Min Range |
|--------|------|-------------------|---------|-----------|
| Rayan Rupert | MEM | SNIPER_ELITE | 21.2 | 36.0 |
| AJ Johnson | DAL | CUTTER_SPECIALIST | 10.2 | 34.0 |
| Paul Reed | DET | ENERGY_BIG | 16.0 | 33.0 |
| Ron Harper Jr. | BOS | SNIPER_ELITE | 12.3 | 29.0 |
| Jaxson Hayes | LAL | ROLL_MAN | 18.5 | 29.0 |
| Justin Edwards | PHI | SNIPER_ELITE | 14.7 | 28.0 |
| Alex Caruso | OKC | SNIPER_ELITE | 16.7 | 28.0 |
| Andre Drummond | PHI | ENERGY_BIG | 18.2 | 27.0 |

These players have volatile minutes and sparse stat lines. In a batch context they are likely to be anchored toward the dominant star's archetype or fall back to GENERALIST.

### GENERALIST Rate by Team (degradation risk by team)

Teams with already-high GENERALIST rates — if batch classification is implemented, these teams are most susceptible to further inflation:

| Team | Gen Count | Total | Gen% |
|------|-----------|-------|------|
| TOR | 9 | 16 | 56.3% |
| DET | 8 | 16 | 50.0% |
| SAS | 7 | 16 | 43.8% |
| MIN | 7 | 16 | 43.8% |
| HOU | 7 | 17 | 41.2% |
| LAL | 7 | 18 | 38.9% |

These are primarily rebuilding teams with high bench rotation. Their GENERALIST rates are already elevated and would be the first to show degradation.

### Prompt Engineering Patterns (from `best-practices/ai/PROMPT_ENGINEERING_PATTERNS.md`)

Patterns applicable to batch classification:

**Pattern 1 — Label space first:** Output schema must be defined at the top of the system prompt before any player data. For batch mode, the schema changes: instead of a single string, it becomes a JSON object keyed by player name. Must be in system prompt (not user prompt) for Anthropic caching to fire.

**Pattern 3 — Few-shot examples (≤5):** The 3 existing canonical examples (HELIOCENTRIC, SLASHING_CREATOR, CONNECTOR) in `build_archetype_system_prompt()` are sufficient. Do NOT add more examples per player — BERT research shows 3-5 examples is optimal. Adding team-level few-shot would exceed token budget.

**Pattern 4 — Token budget discipline:** A 15-player batch prompt is 15× the per-player token budget. At ~200 tokens per player input + ~150 tokens for the system prompt overhead, a 15-player batch = ~3,150 tokens input + ~150 output tokens = well within Haiku's 200K context but costs more per batch than per-player. Calculate: 500 per-player calls at $0.25/1M input = $0.125 vs 30 batch calls at ~$0.047/batch = $1.41. Batch is MORE expensive. However, Anthropic prompt caching (identical system prompt) reduces the effective cost.

**Pattern 11 — Many-Shot ICL (NOT recommended here):** The 9,293 settled bets are for curation, not archetype classification. Do not inject ICL examples for archetype. Keep the existing 3 canonical examples.

**Pattern 12 — Response prefilling:** Prefilling with `{"` guarantees JSON output compliance. Apply to batch output schema.

### Lena's Recommendation

**Risk assessment:** Batch-by-team is HIGH RISK for bench players with minimal recent logs. The core mechanism that makes the current system work — individual per-player Gate 2 validation with `_gate2_fallback()` — is preserved in the batch design ONLY if the individual fallback loop runs per-player after receiving batch output. This is non-negotiable.

**Accuracy guard — GENERALIST inflation threshold:**
- Current baseline: 29.1% overall GENERALIST rate (143/492)
- Bench player GENERALIST rate: 38.6% (85/220)
- Alert threshold: if post-batch GENERALIST rate exceeds **35% of active players**, flag as degradation
- Hard block threshold: if GENERALIST rate exceeds **40%**, do NOT commit results — retry with per-player fallback
- The summary output already logs `generalist_pct` — add these thresholds to the summary block

**Lena sign-off:** APPROVED with mandatory accuracy guards described above. The skip-if-recent logic (7-day window) and per-player Gate 2 fallback are required for sign-off. Do not ship without both.

---

## Part 2 — Henrik's Implementation Spec

### What Changes

`scripts/classify_archetypes.py` — Part A (player loop) only. Part B (team scheme resolution) is unchanged.

**Current:** ~500 sequential Claude calls, one per player, in `for player_id, name, position, team, current_archetype in players:` loop.

**Target:** 30 batch calls, one per team, each with ~15 players. Falls back to per-player call for any player whose batch result fails Gate 2 and `_gate2_fallback()` returns None.

**Estimated reduction:** 500 calls → 30 batch calls + N individual fallback calls. Expected N < 20 (GENERALIST fallbacks don't need a retry — they pass immediately). Real savings: ~460 Claude calls per weekly run.

---

### Spec: New Function `build_team_batch_prompt(players_data)`

**Purpose:** Build a single user prompt for all players on one team.

**Input:** `players_data` — list of dicts, each containing:
```
{
  "player_id": str,
  "name": str,
  "position": str,
  "team": str,
  "current_archetype": str | None,
  "synergy_data": list,
  "shot_data": dict | None,
  "l10_data": dict | None,
  "season_data": dict | None
}
```

**Output format:** JSON keyed by player name:
```json
{
  "Shai Gilgeous-Alexander": "HELIOCENTRIC_MAESTRO",
  "Jalen Williams": "TWO_LEVEL_SCORER",
  "Alex Caruso": "SNIPER_ELITE",
  ...
}
```

**Prompt structure (following BERT Pattern 1 — label space first):**

```
OUTPUT: Return a JSON object with exactly one key per player.
Valid values: HELIOCENTRIC_MAESTRO, SLASHING_CREATOR, JUMBO_FACILITATOR, SNIPER_ELITE,
TWO_LEVEL_SCORER, ISO_ASSASSIN, WARRIOR_BIG, STRETCH_BIG, ROLL_MAN, HUB_BIG,
ENERGY_BIG, CUTTER_SPECIALIST, CONNECTOR, FACILITATOR, GENERALIST
No other values. No explanation. JSON only.

PLAYERS TO CLASSIFY:
{"player": "Alex Caruso", "position": "G", "team": "OKC"}
L21: PTS 7.2 | AST 2.1 | REB 2.8 | STL 1.1 | BLK 0.2 | FGA 4.1 | MIN 17
Synergy: SPOT_UP: 31.2% | TRANSITION: 18.4% | CUT: 12.1%
Shot: at-rim 28% | corner-3 22% | quality 0.431
Season: USG 11.2% | AST% 8.1% | A/TO 1.42 | OFF 118
Current DB archetype: SNIPER_ELITE

{"player": "Shai Gilgeous-Alexander", ...}
...
```

**Token budget calculation:**
- System prompt (shared, cached): ~600 tokens
- Per-player data block: ~120 tokens
- 15 players: ~1,800 tokens input
- Output: 15 players × 4 tokens avg = ~60 tokens
- Total per batch: ~1,860 tokens. Within budget.

---

### Spec: Skip-If-Recently-Classified Logic

**Add to `get_active_players()` return value:** Include `updated_at` column.

**Apply filter before batching:** Only include a player in the batch if their `updated_at` is older than 7 days. Players updated within 7 days skip the Claude call entirely — their current DB archetype is retained as-is.

**Query change in `get_active_players()`:**
```sql
SELECT player_id, name, position, team, current_archetype, updated_at
FROM (...)
ORDER BY name
```

**In the batch assembly loop:**
```python
if updated_at and (datetime.now() - datetime.fromisoformat(updated_at)).days < 7:
    # Skip — classified within 7 days
    skipped += 1
    continue
```

**Note on current state:** All 492 active players have `updated_at` older than 7 days (most recent is 2026-03-03, as of 2026-03-10 that's 7 days old). The skip logic will have minimal effect on first run but will significantly reduce calls on subsequent weekly runs after batch mode ships.

---

### Spec: Batch Assembly and Execution Loop

Replace the current `for player_id, name, position, team, current_archetype in players:` loop with:

**Step 1 — Group players by team:**
```python
from collections import defaultdict
teams = defaultdict(list)
for player_row in players:
    player_id, name, position, team, current_archetype, updated_at = player_row
    # Skip logic
    if updated_at and (datetime.now() - datetime.fromisoformat(updated_at)).days < 7:
        skipped += 1
        continue
    # Pre-fetch all data before batching (avoid DB calls inside loop)
    synergy = get_player_synergy(conn, name)
    shot = get_player_shot_quality(conn, player_id)
    l10 = get_player_l10(conn, player_id, args.window_days)
    season = get_player_season_advanced(conn, name)
    teams[team or 'UNKNOWN'].append({
        "player_id": player_id, "name": name, "position": position,
        "team": team, "current_archetype": current_archetype,
        "synergy_data": synergy, "shot_data": shot,
        "l10_data": l10, "season_data": season
    })
```

**Step 2 — One batch call per team:**
```python
import json
for team_name, team_players in sorted(teams.items()):
    batch_prompt = build_team_batch_prompt(team_players)
    batch_result = get_claude_analysis(
        batch_prompt,
        system_prompt,
        HAIKU_MODEL,
        temperature=0.0,
        max_tokens=400,   # 15 players × ~25 tokens output = 375 max
        call_type='archetype_batch',
    )
    # Parse JSON result
    try:
        parsed = json.loads(batch_result or '{}')
    except json.JSONDecodeError:
        parsed = {}
        print(f"[BATCH PARSE FAIL] {team_name}: non-JSON response → falling back to per-player")
    # Process each player in the batch result
    for player_data in team_players:
        name = player_data['name']
        batch_archetype = parsed.get(name)
        _process_player_result(conn, player_data, batch_archetype, args, ...)
```

---

### Spec: `_process_player_result()` (extracted from current loop)

This function handles Gate 2 validation, fallback logic, and DB write for ONE player. It is called both from the batch path AND the individual fallback path.

**Signature:**
```python
def _process_player_result(
    conn, player_data: dict, proposed_archetype: str | None,
    args, stats: dict, system_prompt: str
) -> tuple[str, bool]:  # returns (final_archetype, changed)
```

**Logic (unchanged from current loop, just extracted):**
1. If `proposed_archetype` is None or fails Gate 1 schema: call Claude individually for this player (per-player fallback)
2. Run `validate_archetype()` on proposed result
3. If Gate 2 fails: run `_gate2_fallback()`, then validate, then GENERALIST
4. Write to DB if not dry-run
5. Return final archetype and whether it changed

**Per-player fallback call:**
```python
def _fallback_single_player(player_data, system_prompt, args):
    """Individual Claude call for one player — used when batch result is missing or invalid."""
    prompt = build_archetype_prompt(
        player_data['name'], player_data['position'], player_data['team'],
        player_data['synergy_data'], player_data['shot_data'], player_data['l10_data'],
        player_data['current_archetype'], season_data=player_data['season_data']
    )
    return get_claude_analysis(
        prompt, system_prompt, HAIKU_MODEL,
        temperature=0.0, max_tokens=20, call_type='archetype',
        player_name=player_data['name']
    )
```

---

### Spec: GENERALIST Inflation Guard (Lena-required)

Add to the summary block at end of `main()`:

```python
GENERALIST_ALERT_THRESHOLD = 35.0   # % — soft alert, log warning
GENERALIST_BLOCK_THRESHOLD = 40.0   # % — hard block, do NOT commit results

if generalist_pct >= GENERALIST_BLOCK_THRESHOLD:
    print(f"[ACCURACY GUARD FAIL] GENERALIST rate {generalist_pct:.1f}% >= {GENERALIST_BLOCK_THRESHOLD}% block threshold")
    print(f"[ACCURACY GUARD FAIL] Aborting DB write — results may reflect batch degradation")
    print(f"[ACCURACY GUARD FAIL] Rerun with --per-player flag to bypass batch mode")
    if not args.dry_run:
        conn.rollback()
    sys.exit(1)
elif generalist_pct >= GENERALIST_ALERT_THRESHOLD:
    print(f"[ACCURACY GUARD WARN] GENERALIST rate {generalist_pct:.1f}% >= {GENERALIST_ALERT_THRESHOLD}% alert threshold")
    print(f"[ACCURACY GUARD WARN] Review changes before next pipeline run")
```

**Add `--per-player` CLI flag** as escape hatch:
```python
parser.add_argument("--per-player", action="store_true",
    help="Disable batch mode — run one Claude call per player (original behavior)")
```

If `--per-player` is passed, skip all batching and run original loop. This ensures the weekly_validation.yml workflow can be manually overridden if batch mode produces suspect results.

---

### Spec: System Prompt Compatibility

The existing `build_archetype_system_prompt()` function is unchanged. The same system prompt is passed to both batch calls and individual fallback calls — Anthropic caching still fires for the batch path (30 calls with identical system prompt).

**One change required:** The output schema in the system prompt must describe BOTH individual and batch output format:

```
For single-player calls: output exactly one archetype label, e.g. "SNIPER_ELITE"
For batch calls (JSON requested in user message): output a JSON object, e.g. {"Player Name": "ARCHETYPE"}
No explanation. No other text.
```

This is a backwards-compatible change — individual calls still receive a single string output.

---

### Spec: Prompt Caching Impact

Current: 500 calls with identical system prompt → caching fires after call 1 → 499 calls pay only input token cost.

Batch: 30 calls with identical system prompt → caching fires after call 1 → 29 calls pay only input token cost. Each batch call has ~3× the input tokens but 30/500 = 6% of the calls.

**Net cost change:** Approximate. Current ~500 calls at ~300 tokens avg = 150K tokens. Batch ~30 calls at ~1,860 tokens avg = 55,800 tokens. Batch is ~63% cheaper on input tokens. Output tokens similar (one label per player either way).

---

### Files to Change

| File | Change |
|------|--------|
| `scripts/classify_archetypes.py` | Main refactor — batch loop, `build_team_batch_prompt()`, `_process_player_result()`, `_fallback_single_player()`, accuracy guards, `--per-player` flag, `updated_at` in query |
| No other files | DB schema unchanged, system prompt function unchanged, Gate 2 unchanged |

---

### Ludi Audit Pre-Check

Before junior dev writes code, confirm these checks will pass:

- **P0 Check 3 (DB in sim loop):** All DB calls (synergy, shot, l10, season) must be pre-fetched BEFORE the batch loop, not inside it. The current loop already does this per-player — preserve this pattern in the batch assembly.
- **P0 Check 5 (Tank01 IDs):** No changes to player_canonical_ids — N/A.
- **P1 Check 7 (No AI roster data):** Team grouping uses `players.team` from DB — correct.
- **P2 Check 11 (Silent exceptions):** `json.JSONDecodeError` on batch parse must log with `logger.warning()`, not swallow silently.

---

## Part 3 — Task 2: Corrupted Bets Log Investigation

### Finding

`logs/bets/2026-03-04.json` is **NOT corrupted.** The file is valid JSON containing 2 bet records from OKC vs NYK. The ops-hub Issue 30 flag was incorrect.

**Verification:** `json.load()` succeeds, returns 2 records with complete schema.

### morning_brief.py reads bets from DB, not files

`morning_brief.py` reads today's curated bets via `bet_recommendations` table query filtered by `today_str`. It does NOT read from `logs/bets/*.json` at any point. The `logs/bets/` directory is written by `utils/bet_logger.py` as an archival output — it is never consumed by any downstream script in the current production pipeline.

**Confirmed by:** grep across all `.py` files — only `utils/bet_logger.py` and `send_week2_checklist.py` (a checklist doc, not a pipeline script) reference `logs/bets`.

### Recommendation

- No deletion needed — file is valid
- No date guard needed in `morning_brief.py` — it does not read log files
- Close ops-hub Issue 30 as invalid / resolved by investigation
- No junior dev work required for Task 2

---

## Implementation Order for Junior Dev

1. Add `updated_at` to `get_active_players()` return columns
2. Write `build_team_batch_prompt()` function
3. Extract `_process_player_result()` and `_fallback_single_player()` from current loop
4. Replace Part A loop with batch assembly + team loop
5. Add `--per-player` flag
6. Add GENERALIST accuracy guards to summary block
7. Update system prompt in `build_archetype_system_prompt()` to describe both output modes
8. Run with `--dry-run --limit 30` and verify batch prompt format, then `--dry-run` full run
9. Check GENERALIST rate in dry-run output — must be within 2% of current 29.1% baseline

**Do NOT run in production without dry-run validation first.**
