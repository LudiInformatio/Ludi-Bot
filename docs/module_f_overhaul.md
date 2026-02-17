# Phase 7.9.5 — Module F (Alchemist) Overhaul + Combo Props

## Context

Deep audit of Module F (624 lines) and its data flow through `main.py` revealed **9 bugs**, including 2 critical data pipeline breaks that silently disable major features. Additionally, combo prop markets (PA, PRA, PR) are partially scaffolded but not wired end-to-end — user wants these activated.

**This follows the Module C (commit `93635dc`) and Module E (commit `d00afd0`) overhauls.**

**Key Findings:**

| Bug | Severity | Impact |
|-----|----------|--------|
| F1: Spread sign always positive | P0 | Blowout tax applied to wrong team — every game |
| F2: `ref_impact` vs `ref_data` key mismatch | P0 | Referee notes NEVER generated |
| F3: 3 stat keys missing from normalization | P1 | STL/BLK/TOV props: no sim hit rates, heuristic fallback only |
| F4: Gold combo keys don't match stat_key format | P1 | 3 of 4 gold combos (`STL_UNDER`, `BLK_UNDER`, `TOV_UNDER`) never fire |
| F5: `_map_stat` missing `turnovers` + uses wrong keys | P1 | TOV projection always returns 0 |
| F6: Display dict `ev` field stores edge, not EV | P2 | Sorting/dedup uses edge (acceptable but mislabeled) |
| F7: `avg_edge` in daily summary always 0 | P2 | Daily summary metric broken |
| F8: Dead correlation check (`units >= 1.2`) | P2 | SGP tag never fires (max units = 1.0 since V5.2) |
| F9: Bare `except: pass` in briefing | P3 | Errors invisible |

**Additionally:** Combo props (PA, PRA, PR) are partially supported — Module F already has a `pra` stdev (10.4), and `sync_historical_odds.py` already fetches `player_points_rebounds_assists`. But the full pipeline is not wired.

**Goal:** Fix all 9 bugs + enable PA/PRA/PR/RA combo props end-to-end.

---

## All Issues (Prioritized)

### Tier 1 — CRITICAL (data pipeline breaks)

| ID | Issue | Location | Evidence |
|----|-------|----------|----------|
| **F1** | `abs(spread)` strips sign — `game_is_favorite` always False | `main.py:318` → `module_f.py:78` | `spread < 0` can never be True when spread is abs() |
| **F2** | main.py stores `ref_data` (dict), Module F reads `ref_impact` (scalar) | `main.py:319` → `module_f.py:270` | `game.get('ref_impact', 1.0)` always returns 1.0 fallback |

### Tier 2 — HIGH (features silently disabled)

| ID | Issue | Location | Evidence |
|----|-------|----------|----------|
| **F3** | Stat key normalization missing `steals`→`stl`, `blocks`→`blk`, `turnovers`→`tov` | `main.py:290` | Only maps 5 of 8 stat types; 3 flow through as raw API names |
| **F4** | Gold combos use `STL_UNDER` but stat_key is `steals` (post F3 fix: `stl`) | `module_f.py:496-503` | `f"{stat_key}_{bet_direction}".upper()` = `STEALS_UNDER` ≠ `STL_UNDER` |
| **F5** | `_map_stat` missing `turnovers` key, has `steals`/`blocks` (wrong format post-fix) | `module_f.py:454-466` | After F3 fix, keys become `stl`/`blk`/`tov` but `_map_stat` has `steals`/`blocks` |

### Tier 3 — MEDIUM (mislabeled / dead code)

| ID | Issue | Location | Evidence |
|----|-------|----------|----------|
| **F6** | Display dict `"ev": edge` — labeled EV but stores edge | `module_f.py:369` | Misleading; sorting by "ev" actually sorts by edge |
| **F7** | `avg_edge` uses `p.get('true_edge', 0)` — not in display dict | `module_f.py:408` | Always 0 because `true_edge` key doesn't exist in `all_props` items |
| **F8** | Correlation check `units >= 1.2` — impossible since V5.2 max is 1.0u | `module_f.py:376` | Dead code, SGP tag never fires |
| **F9** | Bare `except: pass` hides tag parsing errors | `module_f.py:618` | Silent failure |

### New Feature — Combo Props (PA, PRA, PR, RA)

| ID | What | Location | Status |
|----|------|----------|--------|
| **CP1** | Add combo markets to API config | `config.py:139` | `TOA_MARKETS` only has single stats |
| **CP2** | Map combo API keys to internal keys | `main.py:290` | Missing `points_assists`→`pa`, etc. |
| **CP3** | Calculate combo hit rates from sim distributions | `module_c.py:329-350` | No combo logic in `calculate_hit_rates()` |
| **CP4** | Map combo projections in Module F | `module_f.py:454-466` | `_map_stat` needs to sum component projections |
| **CP5** | Add combo stdevs for fallback | `module_f.py:534-543` | Only `pra` exists (10.4), missing `pa`/`pr` |
| **CP6** | Handle combo settlement | `settle_bets.py` | Must sum component stats from game logs |

---

## Implementation Plan

### Step 1: Fix Spread Sign (F1)

**Why:** `main.py:318` wraps spread in `abs()`, stripping the sign. Module F line 78 checks `spread < 0` to identify favorites — always False. Result: blowout tax is applied to the wrong team in every game.

**File: `main.py:318`**
```python
# Before:
'spread': abs(spread) if spread != 'N/A' else 0,

# After — preserve sign (negative = home favorite):
'spread': float(spread) if spread != 'N/A' else 0,
```

**Also fix `module_f.py:99`** — `calculate_blowout_tax` receives `abs(spread)`, which is correct (it expects magnitude). Verify that `abs(spread)` is applied INSIDE Module F (line 99), not in main.py. Currently line 99 already does `spread=abs(spread)` — so this is safe.

**Validation:** Print `game_is_favorite` for a known favorite (e.g., BOS -7.5) — should be True.

---

### Step 2: Fix Referee Key Mismatch (F2)

**Why:** `main.py:319` stores referee data as `ref_data` (a dict with `pace_impact`, `whistle_impact`, `crew`). Module F line 270 reads `game.get('ref_impact', 1.0)` — a scalar key that doesn't exist. Referee notes are never generated.

**File: `module_f.py:270`**
```python
# Before:
if abs(game.get('ref_impact', 1.0) - 1.0) > 0.04:
    ref_val = game.get('ref_impact')

# After — extract pace_impact from ref_data dict:
ref_data = game.get('ref_data', {})
ref_pace = ref_data.get('pace_impact', 1.0) if isinstance(ref_data, dict) else 1.0
if abs(ref_pace - 1.0) > 0.04:
    ref_note = f"Refs Boost Overs ({ref_pace}x)" if ref_pace > 1.0 else f"Refs Drag Unders ({ref_pace}x)"
    note_elements.append(ref_note)
```

**Also fix bet_logger `referee_impact` field** at line 352:
```python
# Before:
'referee_impact': game.get('ref_impact', 1.0),

# After:
'referee_impact': ref_data.get('pace_impact', 1.0) if isinstance(game.get('ref_data', {}), dict) else 1.0,
```

**Validation:** Run pipeline with a game that has ref assignments — should see referee note in output.

---

### Step 3: Complete Stat Key Normalization (F3 + F5)

**Why:** `main.py:290` only maps 5 of 8 stat types. The 3 missing (`steals`, `blocks`, `turnovers`) flow through as raw API names. This breaks Module C's `calculate_hit_rates()` (expects `stl`/`blk`/`tov`) AND Module F's `_map_stat()`.

**File: `main.py:290`**
```python
# Before:
mk = {'points': 'pts', 'rebounds': 'reb', 'assists': 'ast', 'threes': '3pm', 'offensive_rebounds': 'oreb'}.get(k, k)

# After — add all 3 missing mappings:
mk = {
    'points': 'pts', 'rebounds': 'reb', 'assists': 'ast',
    'threes': '3pm', 'offensive_rebounds': 'oreb',
    'steals': 'stl', 'blocks': 'blk', 'turnovers': 'tov'
}.get(k, k)
```

**File: `module_f.py:454-466` — update `_map_stat` to match normalized keys:**
```python
# Before:
m = {
    'pts': 'proj_pts', 'reb': 'proj_reb', 'ast': 'proj_ast',
    '3pm': 'proj_3pm', 'oreb': 'proj_oreb',
    'steals': 'proj_stl', 'blocks': 'proj_blk',
    'defensive_rebounds': 'proj_dreb'
}

# After — use normalized short keys consistently:
m = {
    'pts': 'proj_pts', 'reb': 'proj_reb', 'ast': 'proj_ast',
    '3pm': 'proj_3pm', 'oreb': 'proj_oreb', 'dreb': 'proj_dreb',
    'stl': 'proj_stl', 'blk': 'proj_blk', 'tov': 'proj_tov'
}
```

**Also fix bare `except: continue` at `main.py:298`:**
```python
# Before:
except: continue

# After:
except Exception as e:
    print(f"   >>> [main] Prop format error for {k}: {e}")
    continue
```

**Validation:** Run pipeline — STL/BLK/TOV props should now get simulation-based hit rates instead of heuristic fallback.

---

### Step 4: Fix Gold Combo Key Matching (F4)

**Why:** Gold combos use uppercase short keys (`STL_UNDER`, `BLK_UNDER`, `TOV_UNDER`, `3PM_UNDER`). The `stat_dir` is built from `stat_key` which — after Step 3 — will be `stl`, `blk`, `tov`, `3pm`. So `f"{stat_key}_{bet_direction}".upper()` = `STL_UNDER` which now matches correctly.

**Verify after Step 3** that the combo keys match. If stat_key still arrives as `steals`/`blocks`/`turnovers` for some code path, the gold combos will still fail.

**File: `module_f.py:496-503` — no code change needed IF Step 3 is done correctly.** But add a safety normalization:
```python
# Before line 502:
stat_dir = f"{stat_key}_{bet_direction}".upper()

# After — normalize stat_key to short form before building combo:
STAT_SHORT = {'steals': 'stl', 'blocks': 'blk', 'turnovers': 'tov', 'defensive_rebounds': 'dreb'}
norm_key = STAT_SHORT.get(stat_key.lower(), stat_key.lower())
stat_dir = f"{norm_key}_{bet_direction}".upper()
```

**Validation:** Process a BLK UNDER bet — should get +1 tier upgrade from gold combo.

---

### Step 5: Fix Display Dict + Daily Summary (F6 + F7 + F8 + F9)

**F6 — `"ev": edge` mislabel (line 369):**
```python
# Before:
"ev": edge,  # V2.1: Now using devigged edge (not inflated ev)

# After — rename for clarity:
"edge": edge,  # True devigged edge percentage
```
Then update all downstream references to `p['ev']` → `p['edge']` (sort on line 397, dedup on line 391, display on line 609, grouped sort on line 427, summary on line 409, filter on line 602).

**F7 — `avg_edge` always 0 (line 408):**
```python
# Before:
'avg_edge': sum(p.get('true_edge', 0) for p in all_props) / len(all_props) if all_props else 0,

# After — use the correct key:
'avg_edge': sum(p.get('edge', 0) for p in all_props) / len(all_props) if all_props else 0,
```

**F8 — Dead correlation check (line 376):**
```python
# Before:
if len([x for x in player_props if x['units'] >= 1.2]) >= 2:

# After — lower threshold to match V5.2 max (1.0u), require DIAMOND tier:
if len([x for x in player_props if x['units'] >= 0.75]) >= 2:
```

**F9 — Bare except (line 618):**
```python
# Before:
except: pass

# After:
except Exception as e:
    print(f"   >>> [Module F] Tag parse error: {e}")
```

**Validation:** Check daily summary has non-zero `avg_edge`. Verify sort order unchanged.

---

### Step 6: Wire BDL Prop Parsing + Combo Props (PRA, PA, PR, RA)

**Why:** User wants combo props (PRA, PA, PR, RA). The-Odds-API Feb quota is exhausted (burned by Ludi Lite). BDL (GOAT tier, $39.99/mo, 600 req/min) already returns all combo markets with real sportsbook odds — and `module_a.py:577` already fetches BDL props but stores them raw without parsing. BDL should be the primary prop fallback over Tank01.

**BDL `player_props` response format** (from docs.balldontlie.io):
```json
{
  "prop_type": "points_rebounds_assists",
  "line_value": "35.5",
  "player_id": 123,
  "vendor": "draftkings",
  "market": { "type": "over_under", "over_odds": -111, "under_odds": -115 }
}
```

**BDL combo markets:** `points_rebounds_assists`, `points_assists`, `points_rebounds`, `rebounds_assists`

#### 6a: Parse BDL props into pipeline format

**File: `module_a.py` — new `_parse_bdl_props()` + update `fetch_props_balldontlie()`**

Convert raw BDL prop objects into the same `{line, odds_over, odds_under, book_over, book_under}` format that The-Odds-API props use. Key challenge: BDL returns `player_id` not player names — use `player_canonical_ids` table or BDL's player lookup.

```python
def _parse_bdl_props(self, game_id, raw_props):
    """Parse BDL player_props into standard pipeline format."""
    BDL_VENDOR_MAP = {
        'draftkings': 'DraftKings', 'fanduel': 'FanDuel',
        'betmgm': 'BetMGM', 'caesars': 'Caesars',
        'bet365': 'bet365',
    }
    for prop in raw_props:
        if prop.get('market', {}).get('type') != 'over_under':
            continue  # Skip milestone/binary markets (DD, TD)
        player_name = self._resolve_bdl_player_name(prop.get('player_id'))
        if not player_name:
            continue
        prop_type = prop.get('prop_type', '')
        line = float(prop.get('line_value', 0))
        vendor = BDL_VENDOR_MAP.get(prop.get('vendor', ''), prop.get('vendor', ''))
        over_odds = prop.get('market', {}).get('over_odds', -110)
        under_odds = prop.get('market', {}).get('under_odds', -110)

        if player_name not in self.games[game_id]['props']:
            self.games[game_id]['props'][player_name] = {}
        # Only add if TOA didn't already provide this prop
        if prop_type not in self.games[game_id]['props'][player_name]:
            self.games[game_id]['props'][player_name][prop_type] = {
                'line': line,
                'odds_over': over_odds, 'book_over': vendor,
                'odds_under': under_odds, 'book_under': vendor,
            }
```

Then in `fetch_props_balldontlie()` after line 581:
```python
self.games[game_id]['bdl_props'] = props  # Keep raw backup
self._parse_bdl_props(game_id, props)     # Parse into pipeline format
```

**Player name resolution:** Add `_resolve_bdl_player_name()` using `player_canonical_ids` table or BDL's player endpoint (with cache).

**BDL fallback mode:** When `_using_bdl_fallback` is True, `_parse_bdl_props` is the PRIMARY prop source.

#### 6b: Map combo + missing stat keys in main.py

**File: `main.py:290` — extend the mapping (builds on Step 3):**
```python
mk = {
    'points': 'pts', 'rebounds': 'reb', 'assists': 'ast',
    'threes': '3pm', 'offensive_rebounds': 'oreb',
    'steals': 'stl', 'blocks': 'blk', 'turnovers': 'tov',
    # Combo props (from BDL or TOA)
    'points_rebounds_assists': 'pra',
    'points_assists': 'pa',
    'points_rebounds': 'pr',
    'rebounds_assists': 'ra',
}.get(k, k)
```

#### 6c: Calculate combo hit rates from sim distributions

**File: `module_c.py` — extend `calculate_hit_rates()` (~line 330):**
```python
combo_map = {
    'pra': ['PTS', 'REB', 'AST'],
    'pa': ['PTS', 'AST'],
    'pr': ['PTS', 'REB'],
    'ra': ['REB', 'AST'],
}
# After single-stat lookup, add:
combo_keys = combo_map.get(prop_key.lower())
if combo_keys and all(ck in distributions for ck in combo_keys):
    combo_dist = sum(distributions[ck] for ck in combo_keys)
    hit_rates[prop_key] = round(np.mean(combo_dist > float(line)), 4)
```

#### 6d: Map combo projections + stdevs in Module F

**File: `module_f.py` — extend `_map_stat()` (from Step 3):**
```python
COMBOS = {
    'pra': ('proj_pts', 'proj_reb', 'proj_ast'),
    'pa': ('proj_pts', 'proj_ast'),
    'pr': ('proj_pts', 'proj_reb'),
    'ra': ('proj_reb', 'proj_ast'),
}
if k in COMBOS:
    return sum(p.get(c, 0) for c in COMBOS[k])
```

**Add stdevs:** `'pa': 9.2, 'pr': 9.5, 'ra': 5.3`

#### 6e: Handle combo settlement (RA only — PRA/PA/PR already exist)

**File: `settle_bets.py` — add RA:**
```python
'RA': ['reb', 'ast'],  # Add to existing COMBO_STATS dict
```

**Validation:** Run `fetch_props_balldontlie()` for a test game — verify parsed BDL props appear in `self.games[g_id]['props']` with combo keys. Trace through main.py -> Module C -> Module F to confirm combo projections and hit rates.

---

## Files Modified

| File | Changes | Risk |
|------|---------|------|
| `main.py` | Fix spread sign (F1), complete stat key normalization (F3), add combo mappings, fix bare except | MEDIUM |
| `module_f.py` | Fix ref key (F2), update `_map_stat` (F5 + combos), fix gold combos (F4), fix display dict (F6-F9), add combo stdevs | MEDIUM |
| `module_a.py` | Parse BDL props into pipeline format, player name resolution | MEDIUM |
| `module_c.py` | Add combo hit rate calculation | LOW — append-only |
| `settle_bets.py` | Add RA combo settlement | LOW — append-only |

---

## Verification Plan

### After Each Step

| Step | Verification |
|------|-------------|
| 1 (spread sign) | `python -c "print(float(-7.5) < 0)"` -> True; check Module F for a known favorite |
| 2 (ref key) | Run pipeline with ref data — should see "Refs Boost/Drag" in notes |
| 3 (stat keys) | Check `sim_hit_rates` dict contains `stl`, `blk`, `tov` keys |
| 4 (gold combos) | Process BLK UNDER bet — should get +1 tier upgrade |
| 5 (display dict) | Verify `avg_edge` in daily summary is non-zero |
| 6 (BDL + combos) | BDL props parsed; PRA line -> projection, hit rate, and edge |

### Full Validation

```bash
source .venv/bin/activate

# 1. Smoke test
python -c "from module_f import LudiReporter; r = LudiReporter(); print('Module F loaded OK')"

# 2. Verify _map_stat handles all keys including combos
python -c "
from module_f import LudiReporter
r = LudiReporter()
p = {'proj_pts': 25, 'proj_reb': 8, 'proj_ast': 6, 'proj_stl': 1.5, 'proj_blk': 1.2, 'proj_tov': 3.0, 'proj_3pm': 2.5, 'proj_oreb': 1.0, 'proj_dreb': 5.0}
for k in ['pts','reb','ast','3pm','stl','blk','tov','oreb','pra','pa','pr','ra']:
    print(f'{k}: {r._map_stat(p, k)}')
"
# Expected: pts=25, reb=8, ast=6, stl=1.5, blk=1.2, tov=3.0, pra=39, pa=31, pr=33, ra=14

# 3. Verify combo hit rates in Module C
python -c "
import numpy as np
from module_c import LudiOracle
o = LudiOracle()
dists = {'PTS': np.random.normal(25, 6, 5000), 'REB': np.random.normal(8, 3, 5000), 'AST': np.random.normal(6, 2, 5000)}
sim = {'_distributions': dists}
lines = {'pra': 35, 'pa': 28, 'pr': 30, 'ra': 12}
rates = o.calculate_hit_rates(sim, lines)
for k in ['pra','pa','pr','ra']:
    print(f'{k} hit rate: {rates.get(k, \"MISSING\")}')
"

# 4. BDL prop parser exists
python -c "from module_a import Gatekeeper; g = Gatekeeper(); print('BDL parser:', hasattr(g, '_parse_bdl_props'))"

# 5. Integration test
python test_pipeline.py
```

### Rollback Strategy

Steps are independently revertible:
- Step 1 alone = fixes the worst bug (wrong team gets blowout tax)
- Steps 1-3 = all data pipeline breaks fixed
- Steps 1-5 = all bugs fixed
- Step 6 = additive (BDL parsing + combos; can be reverted without affecting single-stat flow)

---

## Expected Impact

| Metric | Current | After Fix (est.) | Confidence |
|--------|---------|------------------|------------|
| STL/BLK/TOV hit rate source | Heuristic fallback | Simulation-based | High — normalization chain fixed |
| Gold combo tier upgrades | 1 of 4 fires (3PM only) | 4 of 4 fire | High — key matching fixed |
| Blowout tax accuracy | Wrong team taxed | Correct team taxed | High — sign preserved |
| Referee notes | Never generated | Generated when ref crew assigned | High — key mismatch fixed |
| Daily summary avg_edge | Always 0 | Real average edge | High — key reference fixed |
| Combo props (PRA/PA/PR/RA) | Not available | Full pipeline via BDL | High — BDL returns all 4 combos |
| Prop data resilience | TOA only (quota-dependent) | BDL fallback wired | High — BDL is GOAT tier, 600 req/min |

**Combined with Module C + E fixes:** All three overhauls together target the full pipeline — Module C fixes simulation inputs, Module E fixes modifier stacking, Module F fixes edge calculation and reporting. Expected combined effect: OVER WR 50-53%, Overall WR 56-59%, plus 4 new combo prop markets (PRA, PA, PR, RA) and resilient BDL prop fallback.
