# Module F (Alchemist) Overhaul — Agent Prompt

## Role

You are a Python simulation engineer working on the Ludi-Bot NBA analytics platform. Your job is to execute the Module F (Alchemist) overhaul plan exactly as specified.

## Context

- **Project:** `/Users/flyprice/Desktop/Ludi Informatio/Projects/Ludi-Bot`
- **Plan file:** `docs/module_f_overhaul.md` — **READ THIS FIRST.** It contains 6 implementation steps, verification plan, and expected impact. Execute it step-by-step in order.
- **Primary files to modify:** `module_f.py` (624 lines), `main.py`, `module_a.py`, `module_c.py`, `settle_bets.py`
- **Supporting context:** `CLAUDE.md`, `ROADMAP.md`, `docs/ARCHITECTURE.md`
- **Database:** `ludi.db` (SQLite — do NOT delete or restructure tables)
- **Virtual env:** `.venv/bin/python`

## Critical Rules

1. Read the plan file completely before writing any code
2. Read each file before editing — understand existing patterns
3. Do NOT use AI knowledge for NBA data — all facts come from `ludi.db`
4. Activate venv before running any Python: `source .venv/bin/activate`
5. Back up before major changes: `cp ludi.db ludi.db.backup_pre_module_f_fix`
6. Follow conventional commits: `feat(module-f):` prefix
7. Do NOT push to remote — local commits only
8. `scipy` is NOT installed — do not import it

## Critical Interaction Warnings

1. **Module C was overhauled** (commit `93635dc`). Module C now calculates `_distributions` for all stats including STL, BLK, TOV. After Step 3 normalizes stat keys, these distributions will be accessible via `calculate_hit_rates()`.

2. **Module E was overhauled** (commit `d00afd0`). Module E now applies a global ±25% modifier cap. The `proj_stl`, `proj_blk`, `proj_tov` keys in calibrated output are guaranteed present.

3. **BDL over Tank01 for props.** User explicitly wants BDL as the primary prop fallback (GOAT tier, 600 req/min, returns combo markets). Tank01 does NOT return combo props.

4. **The-Odds-API Feb quota is exhausted.** Do NOT add combo markets to `TOA_MARKETS` in config.py — it will waste credits when quota refreshes in March. Combo props come from BDL only.

## Execution Order

1. Read the plan at `docs/module_f_overhaul.md`
2. Execute Steps 1-6 in sequence (each step depends on prior ones being stable)
3. Run verification after each step as specified in the plan
4. Run full validation after all steps complete

### Step Summary (details in plan file)

| Step | Issue ID | What |
|------|----------|------|
| 1 | F1 | Fix spread sign — remove `abs()` from `main.py:318` |
| 2 | F2 | Fix ref key mismatch — `module_f.py:270` read `ref_data` dict not `ref_impact` scalar |
| 3 | F3+F5 | Complete stat key normalization — add `steals/blocks/turnovers` to `main.py:290`, update `_map_stat` in `module_f.py` |
| 4 | F4 | Fix gold combo key matching — add safety normalization at `module_f.py:502` |
| 5 | F6-F9 | Fix display dict (`ev`->`edge`), daily summary avg_edge, dead SGP check, bare except |
| 6 | CP1-CP6 | Wire BDL prop parsing + combo props (PRA, PA, PR, RA) end-to-end |

## Key Line References (verified Feb 16)

| Location | Line(s) | What's There |
|----------|---------|-------------|
| Spread abs() BUG | `main.py:318` | `abs(spread)` strips sign |
| ref_data stored | `main.py:319` | `'ref_data': ref_data` (dict) |
| Stat normalization | `main.py:290` | Missing steals/blocks/turnovers |
| Bare except | `main.py:298` | `except: continue` |
| game_is_favorite | `module_f.py:78` | `spread < 0` — always False |
| blowout_tax abs() | `module_f.py:99` | `abs(spread)` — correct (expects magnitude) |
| ref_impact read BUG | `module_f.py:270` | `game.get('ref_impact', 1.0)` — key doesn't exist |
| referee_impact log | `module_f.py:352` | `game.get('ref_impact', 1.0)` — same bug |
| ev mislabel | `module_f.py:369` | `"ev": edge` |
| SGP dead check | `module_f.py:376` | `units >= 1.2` — max is 1.0 |
| avg_edge broken | `module_f.py:408` | `p.get('true_edge', 0)` — key doesn't exist |
| _map_stat | `module_f.py:454-466` | Has `steals`/`blocks` (wrong post-fix) |
| Gold combos | `module_f.py:496-503` | `STL_UNDER` etc. |
| Stdev table | `module_f.py:534-543` | Only `pra` (10.4), missing pa/pr/ra |
| Bare except | `module_f.py:618` | `except: pass` |
| BDL prop fetch | `module_a.py:542-586` | Fetches raw, stores at `bdl_props`, never parsed |
| Hit rate calc | `module_c.py:329-350` | Single stats only, no combos |
| Combo settlement | `settle_bets.py` | Has PRA/PA/PR, missing RA |

## Testing Protocol

### After Each Step

Run the verification specified in the plan. Key checks:

- **Step 1:** `python -c "print(float(-7.5) < 0)"` should be True
- **Step 2:** Grep for `ref_impact` — should NOT appear in module_f.py (replaced by `ref_data`)
- **Step 3:** Smoke test Module F, verify `_map_stat` returns values for `stl`, `blk`, `tov`
- **Step 5:** Verify `avg_edge` key references use `edge` not `true_edge` or `ev`
- **Step 6:** `hasattr(Gatekeeper(), '_parse_bdl_props')` should be True

### After ALL Steps Complete

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

## Reporting

When complete, provide a summary in this exact format:

```markdown
## Module F Overhaul — Completion Report

### Step Status

| Step | Issue | Status | Files Changed | Notes |
|------|-------|--------|---------------|-------|
| 1 | F1: Spread sign | DONE/BLOCKED | main.py:318 | ... |
| 2 | F2: Ref key | DONE/BLOCKED | module_f.py:270,352 | ... |
| 3 | F3+F5: Stat keys | DONE/BLOCKED | main.py:290 + module_f.py:454 | ... |
| 4 | F4: Gold combos | DONE/BLOCKED | module_f.py:502 | ... |
| 5 | F6-F9: Display/cleanup | DONE/BLOCKED | module_f.py (multiple) | ... |
| 6 | CP1-CP6: BDL + combos | DONE/BLOCKED | module_a/c/f + settle_bets | ... |

### Test Results

- Smoke test: PASS/FAIL
- _map_stat all keys: PASS/FAIL
- Combo hit rates: PASS/FAIL
- BDL parser exists: PASS/FAIL
- Integration test: PASS/FAIL
- New issues discovered: (list any)

### Deviations from Plan

(List any changes made that differ from the plan, with rationale)
```

## Rollback

Each step is independently revertible:
1. `git diff` to see what changed
2. `git checkout -- <file>` to revert that specific file
3. Continue with the next step

Steps are ordered so partial completion still improves the system:
- Step 1 alone = fixes the worst bug (wrong team gets blowout tax)
- Steps 1-3 = all data pipeline breaks fixed
- Steps 1-5 = all 9 bugs fixed
- Step 6 = additive (BDL parsing + combos; can be reverted without affecting single-stat flow)
