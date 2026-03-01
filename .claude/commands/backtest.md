# Backtest Validation

Run the standard validation suite for Ludi-Bot to verify model accuracy.

## Why We Backtest
Backtesting compares our model's predictions against actual historical results. This tells us if our projections are accurate and identifies "drift" - when the model starts becoming less accurate over time.

## Validation Steps

### 1. B2B Fatigue Test (21-day window)
```bash
python scripts/backtest_fatigue_21day.py
```
**What it checks**: Does our back-to-back game fatigue modifier accurately predict performance drops?

### 2. Playtype Matchups Test
```bash
python scripts/backtest_playtype_matchups.py
```
**What it checks**: Do our archetype vs defense matchup modifiers hold up against real game data?

## Success Criteria

| Metric | Target | Fail Threshold |
|--------|--------|----------------|
| Mean Error | ±1.0 pts | >±1.5 pts |
| Hit Rate | >52% | <50% |
| Modifier Drift | ±1.0 pts | >±1.5 pts |

## How to Interpret Results

- **PASS**: Metrics within targets - model is performing well
- **WARNING**: Approaching thresholds - investigate trends
- **FAIL**: Outside thresholds - model needs recalibration

## Report Format
Summarize as:
```
Backtest Results [DATE]
- B2B Fatigue: [PASS/FAIL] (mean error: X pts)
- Playtype Matchups: [PASS/FAIL] (mean error: X pts)
- Overall Status: [PASS/FAIL]
```
