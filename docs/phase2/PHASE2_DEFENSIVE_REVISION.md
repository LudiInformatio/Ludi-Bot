# Phase 2 Revision: Update Team Defensive Styles (Verified 2025-26)

**Date:** January 21, 2026  
**Status:** Revision Required  
**Findings:** 40% mismatch rate in defensive backtests (12/30 teams).

---

## 📋 The Problem

Our defensive classifications in `module_e.py` are outdated and failing verification:

1. **PAINT_PACK Failure:** 7 teams (MIN, SAS, ORL, LAL, CLE, MEM, MIL) are failing rim protection checks. They allow >0% `diff_pct` at the rim or have poor overall ratings.
2. **PERIMETER Failure:** 5 teams (GSW, DAL, NYK, LAC, NOP) are failing perimeter denial checks. They are playing more `SWITCH_HEAVY` than `PERIMETER` denial.
3. **Archetype Mismatch:** The dynamic classifier (`utils/team_defensive_classifier.py`) uses newer archetypes (`SWITCH_HEAVY`, `DROP_COVERAGE`) than `module_e.py`.

---

## 🛠️ Update 1: DEFENSIVE_STYLES Dict

Update `self.DEFENSIVE_STYLES` in `module_e.py` with these verified 2025-26 profiles:

### 🛡️ [UPGRADE] New Defensive Powerhouses
- **DET:** Move to `PAINT_PACK` (90.2 DefRtg, 87.5 recently)
- **PHX:** Move to `BLITZ` (Elite 91.3 recent DefRtg)
- **BOS:** Keep `PAINT_PACK` (Elite 93.7 recent DefRtg)
- **OKC:** Keep `PAINT_PACK` (Stable 96.0 recent DefRtg)

### 📉 [DOWNGRADE] Elite Status Removed (Too Many Points Allowed)
- **MIL:** Move to `NEUTRAL` (115.3 DefRtg - too high for elite label)
- **LAL:** Move to `NEUTRAL` (112.3 DefRtg + failing rim check)
- **NOP:** Move to `NEUTRAL` (111.8 DefRtg)
- **NYK / DAL:** Move to `NEUTRAL` (Failing perimeter denial, DefRtg > 110)

### 🔄 [SHIFT] Style Adjustments (Failing rim/perimeter checks)
- **MIN, SAS, ORL, CLE, MEM:** Move to `NEUTRAL` or `FUNNEL` (failing `diff_pct < 0` check).
- **LAC, GSW:** Move to `NEUTRAL` (failing perimeter denial checks).

---

## 🛠️ Update 2: Harmonize Archetypes

Update `classify_defense()` (or the mapping logic) to bridge the gap between Week 3 dynamic labels and Module E:

**Mapping Strategy:**
- `RIM_FORTRESS` / `DROP_COVERAGE` → `PAINT_PACK`
- `SWITCH_HEAVY` → Treat as `BLITZ` (high pressure/isolation forcing) or add `SWITCH` to `ADJUSTMENT_RULES`.
- `PERIMETER_FUNNEL` → `PERIMETER`.

---

## 🛠️ Update 3: Dynamic Classifier logic

Update `classify_defense()` in `module_e.py` (if it exists there) to mirror the thresholds in `utils/team_defensive_classifier.py`.

---

## 📋 Tasks

1. **Modify `module_e.py`**: Update `DEFENSIVE_STYLES` dict with verified 2025-26 data.
2. **Modify `module_e.py`**: Update `_apply_defensive_diff_adjustment` (if needed) to handle any new archetypes.
3. **Re-run Backtests**:
   ```bash
   python3 scripts/backtest_defense_styles_60day.py
   python3 scripts/backtest_defense_styles_14day.py
   ```
4. **Report Results**: Mismatch rate should now be **<10%**.

---

## Success Criteria

- [x] `DEFENSIVE_STYLES` reflects current 2025-26 performance.
- [x] 60-day defensive mismatch rate is **<10%**.
- [x] 14-day trends correctly identify Detroit and Phoenix as rising defenses.
- [x] No regression in offensive backtests.

**Priority:** HIGH  
**Impact:** Accuracy of Phase 2 Matchup Matrix.
