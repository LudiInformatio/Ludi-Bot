---
name: backtest
description: >
  Run validation suite to check model accuracy against historical data.
  Verifies fatigue modifiers, playtype matchups, and archetype performance.
  Trigger phrases: "backtest", "run validation", "model accuracy", "/backtest".
---

# Backtest Validation

Runs the validation suite to verify model accuracy against historical results.

## What This Does

Runs two backtest scripts:
1. **Fatigue Test** — 21-day B2B game fatigue modifier validation
2. **Playtype Trends** — 14-day archetype vs defense matchup validation

---

## Execution Steps

### Step 1 — Run Fatigue Backtest

```bash
source .venv/bin/activate
python scripts/backtest_fatigue_21day.py --verbose
```

### Step 2 — Run Playtype Trends Backtest

```bash
source .venv/bin/activate
python scripts/backtest_playtype_trends_14day.py --verbose
```

### Step 3 — Check Results

Review output for:
- Mean error vs targets
- Hit rate vs thresholds
- Modifier drift indicators

---

## Success Criteria

| Metric | Target | Warning | Fail |
|--------|--------|---------|------|
| Mean Error | ±1.0 pts | ±1.0-1.5 pts | >±1.5 pts |
| Hit Rate | >52% | 50-52% | <50% |
| Modifier Drift | ±1.0 pts | ±1.0-1.5 pts | >±1.5 pts |

---

## Output Format

```
## Backtest Results — [date]

### Fatigue Test (21-day)
- Mean Error: [X.X] pts — [PASS/WARNING/FAIL]
- Hit Rate: [X]% — [PASS/WARNING/FAIL]
- Status: [PASS/FAIL]

### Playtype Trends (14-day)
- Mean Error: [X.X] pts — [PASS/WARNING/FAIL]
- Hit Rate: [X]% — [PASS/WARNING/FAIL]
- Status: [PASS/FAIL]

### Overall Status
[PASS/FAIL] — [summary]
```

---

## Post-Backtest Actions

- **PASS**: Report to Solomon "✅ /backtest: All tests passed"
- **WARNING**: Report "⚠️ /backtest: Warnings — [specific metrics]"
- **FAIL**: Report "🔴 /backtest: FAILED — [specific metrics needing attention]"

---

## When to Run

- After any model/calibration changes
- Weekly (Tuesdays via `weekly_validation.yml`)
- Before deploying to production
