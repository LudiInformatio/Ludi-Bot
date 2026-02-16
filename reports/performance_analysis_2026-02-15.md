# Model Performance Analysis (Enhanced V2.0)

**Date:** 2026-02-15 19:45:02  
**Total Settled Bets:** 14423 (VOIDs excluded)  
**Date Range:** 2026-01-07 to 2026-02-12  
**Sample Size Filter:** 100+ bets for segment reporting  

---

## Table 1: Stat Category Performance

| Stat | Bets | Wins | Losses | Win% | Units | Profit | ROI% |
|------|------|------|--------|------|-------|--------|------|
| 3PM | 2134 | 1173 | 961 | 55.0% | 2384.2 | -60.9 | -2.6% |
| AST | 2624 | 1389 | 1235 | 52.9% | 2784.0 | +65.8 | +2.4% |
| BLOCKS | 2520 | 1673 | 847 | 66.4% | 715.3 | +12.4 | +1.7% |
| PTS | 2766 | 1390 | 1376 | 50.3% | 3116.8 | -65.9 | -2.1% |
| REB | 2227 | 1082 | 1145 | 48.6% | 2528.4 | -191.5 | -7.6% |
| STEALS | 1983 | 1075 | 908 | 54.2% | 1101.0 | +131.9 | +12.0% |
| TURNOVERS | 169 | 122 | 47 | 72.2% | 237.9 | +104.8 | +44.1% |

## Table 2: OVER vs UNDER by Stat (Top 20)

| Stat | Direction | Bets | Win% | Profit | Recommendation |
|------|-----------|------|------|--------|----------------|
| 3PM | UNDER | 1354 | 62.3% | +181.6 | EXCELLENT |
| STEALS | UNDER | 1644 | 54.8% | +121.8 | KEEP |
| TURNOVERS | UNDER | 169 | 72.2% | +104.8 | EXCELLENT |
| BLOCKS | UNDER | 2187 | 70.7% | +90.1 | EXCELLENT |
| REB | UNDER | 1253 | 55.5% | +84.7 | EXCELLENT |
| AST | UNDER | 1277 | 54.3% | +70.2 | KEEP |
| STEALS | OVER | 339 | 51.3% | +10.2 | MONITOR |
| AST | OVER | 1347 | 51.6% | -4.4 | MONITOR |
| PTS | UNDER | 1821 | 51.0% | -8.0 | MONITOR |
| PTS | OVER | 945 | 48.8% | -57.9 | FILTER OUT |
| BLOCKS | OVER | 333 | 38.1% | -77.7 | FILTER OUT |
| 3PM | OVER | 780 | 42.3% | -242.5 | FILTER OUT |
| REB | OVER | 974 | 39.7% | -276.2 | FILTER OUT |

## Table 3: Position Performance

| Position | Bets | Win% | Profit | Best Stat | Worst Stat |
|----------|------|------|--------|-----------|------------|
| G | 3798 | 55.7% | +82.2 | BLOCKS | PTS |
| UNK | 6832 | 55.5% | -23.0 | PTS | REB |
| F | 2822 | 53.9% | -27.4 | AST | REB |
| C | 960 | 49.0% | -29.6 | PTS | REB |

## Table 4: Archetype Performance (Top 15)

| Archetype | Bets | Win% | Profit | Units/Bet |
|-----------|------|------|--------|-----------|
| ELITE_SCORER | 996 | 57.3% | +105.5 | 1.05 |
| UNKNOWN | 678 | 57.2% | +69.2 | 1.00 |
| RIM_RUNNER | 261 | 62.8% | +31.8 | 0.98 |
| TWO_WAY_WING | 791 | 53.9% | +26.3 | 0.95 |
| WARRIOR_BIG | 379 | 59.4% | +25.6 | 0.68 |
| HUB_BIG | 478 | 55.2% | +13.5 | 1.14 |
| TWO_LEVEL_SCORER | 518 | 58.7% | +12.0 | 0.67 |
| JUMBO_CREATOR | 213 | 54.0% | -2.0 | 1.10 |
| SNIPER_ELITE | 348 | 51.1% | -4.3 | 0.60 |
| SNIPER | 246 | 57.3% | -6.0 | 0.88 |
| STRETCH_BIG | 210 | 46.7% | -21.5 | 0.91 |
| JUMBO_FACILITATOR | 157 | 45.9% | -23.9 | 0.56 |
| FACILITATOR | 1369 | 54.4% | -83.5 | 0.67 |
| GENERALIST | 7502 | 53.9% | -159.8 | 0.93 |

## Table 5: Edge Bucket Analysis

| Edge Range | Bets | Win% | Expected Win% | Calibration | Brier Score | Status |
|------------|------|------|---------------|-------------|-------------|--------|
| 5-10% | 2647 | 57.9% | 53.1% | +4.9% | 0.2472 | GOOD |
| 10-15% | 1158 | 53.1% | 56.1% | -3.0% | 0.2471 | GOOD |
| 15-20% | 1580 | 56.3% | 57.1% | -0.9% | 0.2466 | EXCELLENT |
| 20-25% | 794 | 52.6% | 60.9% | -8.3% | 0.2580 | OVERCONFIDENT |
| 25%+ | 6095 | 50.0% | 73.8% | -23.8% | 0.3217 | OVERCONFIDENT |

## Table 6: Summary & Recommendations

### Profitable Patterns

- ✅ 3PM UNDER: +181.6 units (62.3%, 1354 bets)
- ✅ STEALS UNDER: +121.8 units (54.8%, 1644 bets)
- ✅ TURNOVERS UNDER: +104.8 units (72.2%, 169 bets)
- ✅ BLOCKS UNDER: +90.1 units (70.7%, 2187 bets)
- ✅ REB UNDER: +84.7 units (55.5%, 1253 bets)

### Leaks to Fix

- ❌ REB OVER: -276.2 units (39.7%, 974 bets)
- ❌ 3PM OVER: -242.5 units (42.3%, 780 bets)
- ❌ BLOCKS OVER: -77.7 units (38.1%, 333 bets)
- ❌ PTS OVER: -57.9 units (48.8%, 945 bets)

### Top Archetypes

- 💎 ELITE_SCORER: +105.5 units (57.3%, 996 bets)
- 💎 UNKNOWN: +69.2 units (57.2%, 678 bets)
- 💎 RIM_RUNNER: +31.8 units (62.8%, 261 bets)

### Calibration Notes

- ⚠️ 20-25%: OVERCONFIDENT by -8.3%
- ⚠️ 25%+: OVERCONFIDENT by -23.8%
## Table 7: Spread Bucket Analysis

| Spread Bucket | Bets | Win% | Profit |
|---------------|------|------|--------|
| Heavy Fav (<-7) | 2727 | 54.6% | -35.4 |
| Mod Fav (-7 to -3) | 2303 | 56.5% | +172.3 |
| Toss-Up (-3 to +3) | 4258 | 53.3% | -213.2 |
| Mod Dog (+3 to +7) | 2557 | 55.3% | +76.2 |
| Heavy Dog (>+7) | 2578 | 55.5% | -3.2 |

## Table 8: Total Bucket Analysis

| Total Bucket | Bets | Win% | Profit |
|--------------|------|------|--------|
| Low (<218) | 14416 | 54.8% | -7.7 |
| Normal (218-228) | 4 | 100.0% | +5.9 |
| Moderate (228-238) | 3 | 33.3% | -1.5 |

## Table 9: Home vs Away Performance

| Venue | Bets | Win% | Profit |
|-------|------|------|--------|
| Home | 7516 | 55.3% | +90.1 |
| Away | 6907 | 54.2% | -93.5 |

## Table 10: Archetype × Stat Cross-Cuts (Top 20)

| Archetype × Stat | Bets | Win% | Profit |
|------------------|------|------|--------|
| ELITE_SCORER × STEALS | 138 | 75.4% | +98.5 |
| TWO_WAY_WING × STEALS | 129 | 48.8% | +28.0 |
| UNKNOWN × 3PM | 101 | 59.4% | +22.1 |
| TWO_WAY_WING × AST | 130 | 62.3% | +22.0 |
| UNKNOWN × REB | 110 | 54.5% | +20.9 |
| ELITE_SCORER × PTS | 166 | 55.4% | +17.3 |
| UNKNOWN × BLOCKS | 119 | 68.1% | +15.6 |
| TWO_WAY_WING × BLOCKS | 135 | 60.0% | +13.9 |
| UNKNOWN × STEALS | 116 | 55.2% | +5.8 |
| UNKNOWN × PTS | 107 | 55.1% | +4.2 |
| ELITE_SCORER × 3PM | 161 | 53.4% | +3.2 |
| ELITE_SCORER × BLOCKS | 159 | 69.2% | +3.0 |
| FACILITATOR × AST | 274 | 50.0% | +2.7 |
| FACILITATOR × STEALS | 197 | 59.9% | +1.7 |
| FACILITATOR × 3PM | 168 | 59.5% | -0.1 |
| ELITE_SCORER × AST | 164 | 46.3% | -0.7 |
| GENERALIST × BLOCKS | 1291 | 67.0% | -3.4 |
| TWO_WAY_WING × REB | 131 | 57.3% | -3.8 |
| TWO_LEVEL_SCORER × PTS | 107 | 48.6% | -6.7 |
| GENERALIST × AST | 1367 | 52.3% | -7.3 |

## Dual-Pool Analysis: Morning vs Evening

| Pool | Bets | Win% | Profit |
|------|------|------|--------|
| Morning (<20:00 UTC) | 10495 | 54.8% | +78.4 |
| Evening (≥20:00 UTC) | 3928 | 54.8% | -81.7 |

**Paired Dates (Both Pools):** 14 dates  
**Dates:** 2026-01-12, 2026-01-13, 2026-01-14, 2026-02-02, 2026-02-03, 2026-02-04, 2026-02-05, 2026-02-06, 2026-02-07, 2026-02-08 ... and 4 more  

