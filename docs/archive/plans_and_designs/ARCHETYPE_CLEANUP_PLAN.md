# Archetype Cleanup & Audit Plan

**Date:** February 17, 2026
**Context:** Post Phase 7.9.5 verification found 5 remaining issues + need full classification audit
**Predecessor:** `docs/ARCHETYPE_OVERHAUL_PLAN.md` (6-phase overhaul, mostly complete)

---

## Issues to Fix (5 items)

### Issue 1: 29 NULL Archetypes (CRITICAL)

**Problem:** 29 players in the `players` table have `archetype = NULL`. These players receive no archetype-based modifiers in Module E and no tier bonus in Module F.

**Fix:** Run reclassification on these 29 players. They should all get a valid archetype (even GENERALIST is better than NULL).

**How:**
```sql
-- Find them:
SELECT player_name, position, team_abbreviation FROM players WHERE archetype IS NULL OR archetype = '';
```
Then call Module E's `_assign_unified_archetype()` for each, ensuring the player packet has their season averages from `player_game_logs`.

**Acceptance:** 0 NULL archetypes remaining.

---

### Issue 2: GENERALIST at 26.9% (Target <25%)

**Problem:** 149/554 players = 26.9%. Target is <25% (<126 players). The catch-all at L1569-1580 uses `pts > 8.0 or ast > 2.5 or reb > 4.0` — some players just below these thresholds are falling through.

**Fix options (pick one or combine):**
- **Option A:** Lower catch-all thresholds slightly: `pts > 6.0 or ast > 2.0 or reb > 3.5`
- **Option B:** Add a minutes-based fallback: any player averaging >15 min/game gets CONNECTOR or ENERGY_BIG based on position
- **Option C:** Keep current thresholds but fix the 29 NULLs first (Issue 1) — if many NULLs become non-GENERALIST, that may bring us under 25%

**Recommended approach:** Fix Issue 1 first, then re-check the count. Only lower thresholds if still >25%.

**Acceptance:** GENERALIST < 25% of active roster (~503 players).

---

### Issue 3: Defensive Synergy Table Missing from Live DB (HIGH)

**Problem:** `player_defensive_synergy` schema is defined in `database.py` (L704, L720-722) but the table was never created in `ludi.db`. Module E queries it at L543-556 and L1921 — these always return empty, making `iso_def`/`spot_def` percentiles always 0.0. This limits PERIMETER_HAWK and SWITCHABLE_ANCHOR classification.

**Fix (3 steps):**

**Step 3a:** Create the table in ludi.db:
```python
import sqlite3
conn = sqlite3.connect('ludi.db')
conn.execute("""
    CREATE TABLE IF NOT EXISTS player_defensive_synergy (
        player_name TEXT,
        playtype TEXT,
        percentile REAL,
        ppp_allowed REAL,
        freq_pct REAL,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (player_name, playtype)
    )
""")
conn.commit()
conn.close()
```

**Step 3b:** Verify schema matches what Module E expects — check the SELECT at L548-551:
```python
SELECT playtype, percentile, ppp_allowed FROM player_defensive_synergy WHERE player_name = ?
```
Schema must have: `player_name`, `playtype`, `percentile`, `ppp_allowed`.

**Step 3c:** Note that populating this table requires Ghost Protocol scraping (NBA.com Synergy defensive data). The table should exist even if empty — Module E handles empty results gracefully. Populating it is a separate task (Ghost Protocol sync on Sunday).

**Acceptance:** Table exists in ludi.db. Module E queries don't error. Table population is a future task.

---

### Issue 4: HUSTLE_DISRUPTOR/PERIMETER_HAWK Threshold Gap (LOW)

**Problem:** Small gap between HUSTLE_DISRUPTOR (stl > 1.15) and PERIMETER_HAWK (stl >= 1.2). Players with stl 1.16-1.19 without Synergy data land on HUSTLE_DISRUPTOR, which may be fine. With defensive Synergy data (Issue 3), more players could qualify for PERIMETER_HAWK via the `iso_def >= 75` path.

**Fix:** No code change needed. Once Issue 3 is resolved and defensive Synergy data is populated, the `iso_def >= 75 and spot_def >= 70` path will activate, naturally promoting qualifying players. Monitor after data is populated.

**Acceptance:** Acknowledge as a known limitation until defensive Synergy data is live.

---

### Issue 5: `defensive_tag` Not Persisted to DB (MEDIUM)

**Problem:** Module E writes `calibrated['defensive_tag'] = 'WEAK_LINK'` (or None) at L932-935, but Module E is stateless — it never writes to the DB itself. The `defensive_tag` column was added to the `players` table, but nothing persists the value from calibration.

**Fix:** In `scripts/reclassify_player_archetypes.py` (or wherever batch reclassification runs), after calling `_assign_unified_archetype()`, also UPDATE the `defensive_tag` column:
```python
cursor.execute(
    "UPDATE players SET defensive_tag = ? WHERE player_name = ?",
    (calibrated.get('defensive_tag'), player_name)
)
```
Also check if `main.py` or `bet_logger.py` persists it during live pipeline runs.

**Acceptance:** `defensive_tag` column populated for WEAK_LINK players after reclassification.

---

## Full Classification Audit (NEW)

### Audit Goal
Verify that team defensive schemes and player archetypes are correct by spot-checking against real NBA data.

### Audit Part A: Team Defensive Schemes (30 teams)

**Current static mapping** is in `module_e.py` L80-130. The `TeamDefensiveClassifier` overlays dynamic classifications at init (L531-541).

**Audit steps:**
1. Run the dynamic classifier and print its output for all 30 teams
2. Compare against the static mapping — flag any disagreements
3. For each disagreement, check which is correct using recent team defensive stats:
   - DefRtg (lower = better)
   - Opp 3PA rate (high = PERIMETER/BLITZ)
   - Opp paint points (high = FUNNEL, low = PAINT_PACK)
   - FTA allowed (high = HACKERS)
4. Update the static mapping if the dynamic classifier is right
5. Print final scheme distribution (should have 5-7 teams per scheme, not 15+ NEUTRAL)

**Key teams to verify:**
- DET at "PAINT_PACK" — they've been rebuilding, is this still accurate?
- BKN at "BLITZ" — new roster, verify
- DEN at "FUNNEL" — Jokic system, might be more NEUTRAL
- Teams missing from static mapping that get NEUTRAL by default

### Audit Part B: Player Archetype Spot Checks (Top 50 players by minutes)

For the top 50 players by minutes played:
1. Query their current archetype from DB
2. Cross-reference with their actual stats (pts, reb, ast, stl, blk, 3pm, usage)
3. Flag any obvious misclassifications:
   - A primary ball handler classified as CUTTER_SPECIALIST
   - A stretch big who shoots 3s classified as ENERGY_BIG
   - A defensive anchor classified as GENERALIST
   - Any star player (>25 min, >15 pts) classified as GENERALIST

**Output:** A markdown table with columns:
`| Player | Team | Pos | Current Archetype | Suggested | Stats (pts/reb/ast/stl/blk/3pm) | Flag |`

Only include rows where there's a potential misclassification or notable finding.

### Audit Part C: Archetype Population Health

Generate a summary report:
1. Distribution of all archetypes (count + %)
2. Distribution by position (do guards get guard-appropriate archetypes?)
3. Any archetype with 0 or 1 players (broken threshold?)
4. Any archetype with >80 players (too loose?)
5. Defensive archetype breakdown: RIM_GUARDIAN, PERIMETER_HAWK, SWITCHABLE_ANCHOR, HUSTLE_DISRUPTOR counts by position
6. Compare the Module F `positive_archetypes` set against actual DB values — confirm all 9 types have >0 players

### Audit Part D: Team Offensive Schemes

Check `utils/team_offensive_classifier.py`:
1. Run the classifier for all 30 teams
2. Print the distribution (should NOT be >50% BALANCED)
3. Verify star-team combos make sense:
   - LAL should reflect LeBron/AD system
   - BOS should reflect Tatum/Brown system
   - DEN should reflect Jokic system

---

## Execution Order

1. **Issue 1** (NULL archetypes) — quick fix, may help Issue 2
2. **Issue 3** (create defensive Synergy table) — unblocks future data
3. **Issue 5** (persist defensive_tag) — wiring fix
4. **Issue 2** (GENERALIST count) — re-check after Issue 1, lower thresholds if needed
5. **Audit Parts A-D** — full classification audit
6. **Issue 4** (threshold gap) — monitor only, no code change

## Files to Modify

| File | Changes |
|------|---------|
| `scripts/reclassify_player_archetypes.py` | Fix NULL archetypes, persist defensive_tag |
| `module_e.py` | Lower catch-all thresholds IF needed after Issue 1 |
| `database.py` | Verify defensive Synergy schema (should be fine) |
| `ludi.db` | CREATE TABLE player_defensive_synergy, reclassify NULLs |
| `utils/team_offensive_classifier.py` | Audit only (no changes unless broken) |

## Verification

After all fixes + audit:
- `SELECT COUNT(*) FROM players WHERE archetype IS NULL` → 0
- `SELECT archetype, COUNT(*) FROM players GROUP BY archetype` → GENERALIST < 25%
- `SELECT name FROM sqlite_master WHERE name = 'player_defensive_synergy'` → exists
- `SELECT COUNT(*) FROM players WHERE defensive_tag IS NOT NULL` → > 0
- Audit report saved to `reports/archetype_audit_YYYYMMDD.md`
