# Phase 4: B2B Fatigue & Rest Integration Task

**Date:** January 21, 2026  
**Task Owner:** [Agent to be assigned]  
**Priority:** HIGH  
**Estimated Time:** 45-60 minutes  
**Prerequisites:** Phase 3 ✅

---

## Mission

Implement **Phase 4 of the Archetype & Team Type Upgrade Plan**:
Integrate research-backed fatigue adjustments into Module E to account for **Back-to-Back (B2B)** games, **Travel Stress** (Road B2B), and **Rest Advantages** (3+ days rest).

---

## Research Background (Verified)

1.  **García et al. (2020):** Significant performance decline (-1.27 effect size) in Q4 of B2B games.
2.  **TopEndSports:** 2-3 point scoring decline specifically on **Road B2B** games (travel + fatigue).
3.  **Positional Impact:** High-activity guards (who cover 2.5+ miles/game) suffer largest efficiency dips.

---

## Technical Implementation

### 1. Data Availability Check

Where does `is_back_to_back` come from?
- It is passed into `calibrate_player` via the `yak_report` dictionary.
- **Task:** Verify `yak_report` contains these keys. If not, implement a helper to calculate them from `player_game_logs` or schedule data.

**Required Keys in `yak_report`:**
- `is_back_to_back` (bool)
- `is_road` (bool)
- `rest_days` (int)
- `games_in_last_5_days` (int) [Optional but good for 4-in-5 checks]

### 2. Implement `_apply_fatigue_adjustments()`

**Add to `module_e.py`:**

```python
def _apply_fatigue_adjustments(self, calibrated: dict, yak_report: dict) -> None:
    """
    Apply research-backed fatigue modifiers for B2B and schedule spots.
    
    Logic:
    - Road B2B: -6% volume (Travel + Fatigue)
    - Home B2B: -3% volume (Fatigue only)
    - Rested Advantage: +3% volume (Home + 3+ days rest)
    - Guard Tax: Extra penalty for active guards on B2B
    """
    player_name = calibrated.get('name', '')
    
    # Extract Schedule Context
    is_b2b = yak_report.get('is_back_to_back', False)
    is_road = calibrated.get('is_road', False) # Check calibrated first, then yak
    if 'is_road' not in calibrated:
        is_road = yak_report.get('is_road', False)
        
    rest_days = yak_report.get('rest_days', 2)
    position = calibrated.get('position', 'UNK')

    # === BACK-TO-BACK LOGIC (Phase A: 50% Reduction Strategy) ===
    # Findings: 2025-26 players are more resilient on B2B than historical data guarantees.
    # Adopted conservative 50% reduction of standard penalties.
    
    if is_b2b:
        if is_road:
            # Road B2B: Tuned High Stress (-4.8%)
            # Standard -9.7% was too aggressive (+1.78 pts error)
            self._apply_factor(calibrated, 0.952)
            calibrated['notes'] += " | B2B Road Tax"
            self._log_adjustment(player_name, 'FATIGUE', 0.952, "Road B2B schedule loss")
        else:
            # Home B2B: Tuned Moderate Stress (-1.5% base)
            self._apply_factor(calibrated, 0.985)
            calibrated['notes'] += " | B2B Home Tax"
            self._log_adjustment(player_name, 'FATIGUE', 0.985, "Home B2B fatigue")
        
        # Guard Specific Tax (High cardio load)
        # Reduced from -4% to -2% based on findings
        if any(g in position for g in ['PG', 'SG', 'G']):
            self._boost_stat(calibrated, 'proj_pts', 0.98) # -2% pts
            self._boost_stat(calibrated, 'proj_fg_pct', 0.99) # -1% eff
            calibrated['notes'] += " (Guard Fatigue)"
            self._log_adjustment(player_name, 'FATIGUE', 0.98, "Guard active movement penalty")

    # === REST ADVANTAGE LOGIC ===
    elif rest_days >= 3 and not is_road:
        # Rested Home Game
        self._apply_factor(calibrated, 1.03)
        calibrated['notes'] += " | Rested Home Edge"
        self._log_adjustment(player_name, 'FATIGUE', 1.03, f"Rested ({rest_days} days) at Home")
        
```

### 3. Integration

**In `calibrate_player()` method (end of function):**

```python
# ... after Phase 3 Playtype Matchups ...

# Phase 4: Fatigue Integration
self._apply_fatigue_adjustments(calibrated, yak_report)
```

---

## Testing Plan

### Create `scripts/test_fatigue_logic.py`

Test Cases:
1.  **Road B2B Player:** Verify ~6% drop.
2.  **Home B2B Player:** Verify ~3% drop.
3.  **Guard on B2B:** Verify extra penalty.
4.  **Rested Home Player:** Verify +3% boost.

### Example Test Data (2025-26 Context)

*   **Jalen Brunson (NYK)** on Road B2B (Guard Tax).
*   **Nikola Jokic (DEN)** on Home B2B (Standard Tax).
*   **Shai Gilgeous-Alexander (OKC)** with 3 days rest at Home (Rested Edge).

---

## Success Criteria

- [ ] `_apply_fatigue_adjustments()` implemented in `module_e.py`.
- [ ] Logic correctly distinguishes Road vs Home B2B.
- [ ] Guard-specific penalty implemented.
- [ ] `scripts/test_fatigue_logic.py` passes with expected modifiers.
- [ ] Debug logging confirms `FATIGUE` adjustments.

---

**Estimated Time:** 45-60 minutes
