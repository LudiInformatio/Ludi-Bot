# Ludi-Bot Methodology

This document describes the betting methodology, edge calculation, line shopping, and CLV tracking systems used by Ludi-Bot.

---

## Edge Calculation Overview

### The Core Formula

```python
# 1. Devig bookmaker odds
fair_prob = devig_multiplicative(over_odds, under_odds)

# 2. Calculate true edge
true_edge = (model_prob - fair_prob) / fair_prob * 100

# 3. Filter by threshold
if true_edge >= 5.0:  # 5% minimum edge (sharp market standard)
    # 4. Calculate EV
    win_prob = model_prob  # V4.6: clamp removed — raw simulation probability used directly
    ev = ((win_prob * decimal_odds) - 1) * 100  # Uses actual best-available NC Legal book odds

    # 5. Kelly sizing
    # V5.2: Tier-based sizing (replaced ev/8 fractional Kelly)
    units = TIER_UNITS[confidence_tier]
    # DIAMOND: 1.25u | BLUE CHIP: 1.00u | CORE ASSET: 0.65u | THE STEAL: 0.35u
```

---

## Devigging (Module F)

**What it does**: Removes bookmaker vig (overround) to calculate TRUE edge instead of raw edge.

**Why it matters**: Without devigging, edge calculations are understated by 3-5%. A bet that looks like 2.8% edge might actually be 7.6% true edge.

**Implementation**: Uses `utils/devig.py` with multiplicative method

```python
from utils.devig import devig_multiplicative
fair_over, fair_under = devig_multiplicative(-110, -110)
true_edge = (model_prob - fair_over) / fair_over * 100
```

**Example:**
```
Player Over 28.5 @ -108

Devigging:
- Raw implied: 51.95%
- Devigged fair prob: 50.8% (removes 1.15% vig)

Model says: 62% (from 5,000 Poisson simulations)

Edge calculation:
- Raw edge: 62% - 51.95% = 10.05% (understated!)
- TRUE edge: (62% - 50.8%) / 50.8% = 22.0% (real value revealed)
```

---

## Line Shopping Strategy

### Two-Tier Approach

**Core Principle:** Find the best odds available at NC Legal books (where user can actually bet), then validate model sharpness against sharp book closing lines.

**Why This Approach:**
- **Tier 1 (Betting):** NC Legal books (FanDuel, DK, BetMGM, Caesars, bet365, HRB) are the ONLY books accessible in North Carolina
- **Tier 2 (Validation):** Sharp books (Pinnacle, Bovada, BetOnline) used for CLV measurement to prove model finds real value

### Line Shopping Algorithm (Module A)

**Step 1: Establish Main Line**
- NC Legal books set the main line (e.g., 27.5 for Points)
- Only ONE line per player/market to enable fair comparison

**Step 2: Filter Alt Lines**
- Ignore alt lines (26.5, 28.5, etc.)
- Only compare same line across all books
- Ensures apples-to-apples edge calculations

**Step 3: Select Best NC Legal Odds**
- Compare all NC Legal books at main line
- Choose HIGHEST decimal odds (best return for bettor)
- Example: FD -108 (1.926) beats DK -115 (1.870)

**Step 4: Track Sharp Books (CLV Validation)**
- Log Pinnacle/Bovada closing line separately
- NOT for betting, but for post-bet CLV measurement
- Measure if you beat sharp market (most efficient pricing)

### Example

```
Player Points Line: 28.5

NC LEGAL BOOKS (Can Bet):
FanDuel:    28.5 @ -108  (1.926 decimal) <-- BEST
DraftKings: 28.5 @ -115  (1.870 decimal)
BetMGM:     28.5 @ -110  (1.909 decimal)
Caesars:    28.5 @ -112  (1.893 decimal)

SHARP BOOKS (CLV Benchmark):
Pinnacle:   28.5 @ -105  (1.952 decimal)

DECISION:
- Bet: FanDuel -108 (best NC Legal available)
- Line shopping edge: 18 cents vs DraftKings
- CLV Target: Beat Pinnacle's closing line
```

---

## CLV (Closing Line Value) Tracking

### Why CLV Matters

**CLV > Win Rate** because:
- Win rate is noisy (luck variance, blowouts, etc.)
- CLV is signal (you consistently found value the market adjusts to)
- Professional bettors beat closing line 55-60% of the time
- CLV > 0 over 30+ days = model is SHARP

### CLV Calculation

```python
# Formula: (opening_decimal - closing_decimal) * 100 = CLV in cents
clv_cents = (your_decimal_odds - sharp_closing_decimal) * 100

# Example:
# Your bet: FD -108 (1.926 decimal)
# Pinnacle closing: -120 (1.833 decimal)
# CLV: (1.926 - 1.833) * 100 = +9.3 cents
```

### Implementation

**Database Schema:**
```sql
ALTER TABLE bet_recommendations ADD COLUMN closing_odds_over INTEGER;
ALTER TABLE bet_recommendations ADD COLUMN closing_odds_under INTEGER;
ALTER TABLE bet_recommendations ADD COLUMN clv_cents INTEGER;
ALTER TABLE bet_recommendations ADD COLUMN closing_time TEXT;
```

**Capture Process:**
- Script runs 5 minutes before tipoff
- Fetches sharp book closing line from The-Odds-API
- Stores in database for CLV calculation

---

## Poisson Simulation (Module C)

### Configuration
- **10,000 iterations** per player (optimal balance of speed vs accuracy)
- **Two-stage simulation**:
  1. Volume simulation (FGA, FG3A, FTA using Poisson distributions)
  2. Outcome simulation (apply shooting percentages)

### Modifiers Applied
```
final_projection = base_stat * pace_factor * referee_factor * fatigue_tax * defense_rating
```

---

## Unit Sizing (Kelly Criterion)

### Conservative Approach
- Use 12.5% fractional Kelly (industry standard is 25-50%)
- Formula: `units = ev / 8`
- Capped at 1.5u maximum (prevents ruin)
- Floor at 0.25u minimum

### Bet Tiers
| Tier | Edge | Units |
|------|------|-------|
| DIAMOND | 15%+ | 1.25u |
| BLUE CHIP | 10-15% | 1.00u |
| CORE ASSET | 7-10% | 0.65u |
| THE STEAL | 5-7% | 0.35u |

> **Note (V5.2):** The system moved from fractional Kelly (`ev/8`) to tier-based flat sizing in V5.2. Tier assignment is based on `true_edge` (devigged probability edge), not on EV. The Kelly criterion is retained as a reference model in methodology documentation but is not used for production sizing.

---

## Validation Requirements

**Must-Achieve Metrics Before Dashboard Development:**
- RMSE per stat: PTS < 7.0 | AST < 2.5 | REB < 3.5 (see `docs/VALIDATION_GATES.md` for current measurements)
- Hit rate > 52% overall
- Hit rate > 55% on 10%+ edge bets
- Positive CLV (Closing Line Value) on >50% of bets

**If metrics fail**: Extend calibration phase, DO NOT proceed to dashboard.

---

## Best Practices

### Do:
- Compare all NC Legal books at main line
- Use devigging for true edge (multiplicative method)
- Filter by >= 5% edge minimum
- Track sharp closing lines for CLV validation
- Size bets with conservative Kelly (12.5% fractional)
- Report daily CLV (not just win rate)

### Don't:
- Use consensus average odds (line shopping beats averaging)
- Bet on alt lines (creates apples-to-oranges comparisons)
- Skip devigging (edge is understated by 3-5%)
- Bet sharp books (Bovada/Pinnacle not accessible in NC)
- Use aggressive Kelly sizing (1.5u max prevents ruin)
- Trust win rate alone (CLV is the signal)

---

## EV Sanity Flags

| EV Range | Flag | Action |
|----------|------|--------|
| 5-15% | Normal | Standard bet |
| 15-25% | EXCEPTIONAL | Verify line is correct |
| 25%+ | VERIFY LINE | Likely stale/error |

---

## Future Enhancements

### PBP Stats Expansion
1. **WOWY Impact**: Use `get_player_on_off_impact` to replace usage vacuum heuristics
2. **Clutch/Leverage**: Use `get_team_leverage_summary` for "Clutch Killers"
3. **Lineup Analysis**: Use `get_game_stats(Type="Lineup")` to fade/target bench units
4. **Shot Distance**: Use shot location data to refine archetypes

### Additional Signals (Week 6+)
1. **Strength of Schedule (SOS)**: Adjust L10 averages based on opponent defensive rating
2. **Depth Chart Authority**: Model "Starter Returns" impact on bench usage
3. **Shooting Luck Deviation**: Identify unsustainable efficiency variance for regression plays
