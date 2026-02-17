# Archetype Backtest Report - 60-Day

**Generated:** 2026-02-16 18:29:08
**Test Period:** 2025-12-18 to 2026-02-16
**Games Processed:** 11478
**Games Skipped:** 135 (insufficient history)

## RMSE Results (Root Mean Squared Error)

| Stat | RMSE | Status |
|------|------|--------|
| PTS  | 6.02 | ✅ PASS |
| REB  | 2.53 | ✅ PASS |
| AST  | 1.81 | ✅ PASS |
| 3PM  | 1.25 | ✅ PASS |
| BLK  | 0.73 | ✅ PASS |
| STL  | 0.96 | ⚠️ NEEDS TUNING |
| TOV  | 1.17 | ✅ PASS |

## Interpretation

- **RMSE** measures average prediction error in the same units as the stat
- Lower RMSE = better model accuracy
- Industry standard: PTS < 7.0, REB < 3.5, AST < 2.5

## Notes

- This backtest uses historical game logs with running averages (5+ game minimum)
- Module E calibration applied (matchup modifiers, fatigue, blowout tax)
- Game context (spread, total) pulled from database where available
