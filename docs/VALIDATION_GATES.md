# Validation Gates

**Last Updated:** March 27, 2026 (ablation RMSE added)
**Owner:** Lena (queries) + Henrik (review)
**Measurement cadence:** Every session with Henrik audit — re-run measurement scripts, update Current Status column

This document defines three hard pass/fail gates for the Ludi-Bot model. No sprint item that depends on model accuracy should be marked complete without these gates passing. Gates are not aspirational — they are enforced.

**Gate pass = model is production-calibrated for that metric.**
**Gate fail = calibration work takes priority over new features.**

---

## Gate 1 — RMSE Gate

**Pass criteria:** PTS RMSE < 7.0 | AST RMSE < 2.5 | REB RMSE < 3.5

**Measurement script:** `scripts/run_backtest_suite.py` → `test_01_rmse_by_stat()`

Direct query (fastest):
```sql
SELECT
    stat_category,
    COUNT(*) as n,
    ROUND(SQRT(AVG((projection - actual_result) * (projection - actual_result))), 2) as rmse,
    ROUND(AVG(ABS(projection - actual_result)), 2) as mae,
    ROUND(AVG(projection - actual_result), 2) as mean_err
FROM bet_recommendations
WHERE outcome IN ('WIN', 'LOSS')
  AND stat_category IN ('PTS', 'AST', 'REB')
  AND projection IS NOT NULL
  AND actual_result IS NOT NULL
GROUP BY stat_category
ORDER BY stat_category;
```

**Current Status (production bets — measured 2026-03-26, N=PTS:3192 / AST:2593 / REB:1513):**

| Stat | RMSE | MAE | Mean Error | Status |
|------|------|-----|------------|--------|
| PTS | 7.93 | 6.00 | +0.08 | ❌ FAIL (target < 7.0) |
| AST | 2.61 | 1.95 | +0.25 | ⚠️ WARNING (target < 2.5) |
| REB | 3.25 | 2.41 | -0.15 | ✅ PASS (target < 3.5) |

**Gate 1 verdict: ❌ FAIL — PTS exceeds target**

**Ablation baseline (all projections — run_modifier_ablation.py, 2026-03-27, N=1,623, Mar 24–27):**

| Stat | Model RMSE | Without Pace | Without Ref | Naive |
|------|-----------|-------------|------------|-------|
| PTS | 7.44 | 7.23 (-2.8%) | 7.20 (-3.3%) | — |
| AST | 3.09 | 3.01 (-2.7%) | 3.02 (-2.3%) | — |
| REB | 3.50 | 3.37 (-3.8%) | 3.39 (-3.2%) | — |
| Overall | 3.33 | 3.23 (-3.0%) | 3.23 (-3.1%) | 3.32 (≈same) |

Ablation findings (Mar 27):
- Pace (+) and Ref (+) modifiers are genuinely HELPFUL (~3% RMSE improvement each)
- Fatigue, Empirical, Blowout, Scheme all NEUTRAL (stored as 1.0 in player_projections)
- Empirical NEUTRAL is a new blocker: `empirical_mod` is not being written from Module C output to projection_logger → TD-023
- Baseline vs naive RMSE nearly identical (3.3251 vs 3.3248) — modifiers net-neutral overall; pace+ref gains offset by NEUTRAL placeholders

Notes:
- Mean errors near zero = no directional bias. Problem is variance, not systematic drift.
- AST at 2.61 is in the warning band — watch for regression.
- RMSE measured on production bets (true_edge ≥ 5% only) — selection bias exists. True RMSE on full distribution may differ.
- Active mitigation: stat-level Kelly gate (Sprint 4-A) sizes down on high-variance stats.

---

## Gate 2 — Hit Rate Gate

**Pass criteria:** Overall WR > 52% AND 10%+ edge WR > 55%

**Measurement script:** `scripts/calibrate_claude_outputs.py` with `by_grade` breakdown

Direct query:
```sql
-- Overall
SELECT COUNT(*) as n,
       ROUND(100.0 * SUM(CASE WHEN outcome='WIN' THEN 1 ELSE 0 END) / COUNT(*), 1) as wr_pct
FROM bet_recommendations WHERE outcome IN ('WIN','LOSS');

-- 10%+ edge
SELECT COUNT(*) as n,
       ROUND(100.0 * SUM(CASE WHEN outcome='WIN' THEN 1 ELSE 0 END) / COUNT(*), 1) as wr_pct
FROM bet_recommendations WHERE outcome IN ('WIN','LOSS') AND true_edge >= 10.0;

-- By grade
SELECT curation_grade, COUNT(*) as n,
       ROUND(100.0 * SUM(CASE WHEN outcome='WIN' THEN 1 ELSE 0 END) / COUNT(*), 1) as wr_pct
FROM bet_recommendations
WHERE outcome IN ('WIN','LOSS') AND curation_grade IS NOT NULL
GROUP BY curation_grade ORDER BY wr_pct DESC;
```

**Current Status (measured 2026-03-26):**

| Segment | N | WR | Target | Status |
|---------|---|----|--------|--------|
| Overall | 16,559 | 52.6% | > 52% | ✅ PASS |
| 10%+ edge | 13,937 | 51.2% | > 55% | ❌ FAIL |
| STRONG grade | 181 | 52.5% | > 55% | ⚠️ INSUFFICIENT SIGNAL |
| LEAN grade | 1,647 | 50.9% | — | monitoring |
| FADE grade | 160 | 47.5% | — | correct direction |

**Gate 2 verdict: ⚠️ PARTIAL — overall PASS, 10%+ edge FAIL**

Notes:
- 10%+ edge tier underperforming overall rate is the inverted-edge signal confirmed in Mar 23 backtest. Higher model confidence does not predict more wins in volume stats.
- STRONG grade at 52.5% (N=181): Wilson 95% CI lower bound ≈ 45.1% — not statistically distinguishable from 50% at this sample size.
- Grade hierarchy correct direction (STRONG > LEAN > FADE) — FADE 47.5% is below breakeven.
- Active mitigation: Three-Lens curation prompt (Sprint Session 2, v2.0-three-lens) adds CONTRARIAN lens with calibration signal guard for high-edge volume stats.

---

## Gate 3 — CLV Gate

**Pass criteria:** Positive CLV on > 50% of bets with CLV data

**Measurement script:** Direct query only (no dedicated script yet):
```sql
SELECT
    COUNT(*) as total_with_clv,
    SUM(CASE WHEN clv_cents > 0 THEN 1 ELSE 0 END) as positive_clv_count,
    ROUND(100.0 * AVG(CASE WHEN clv_cents > 0 THEN 1.0 ELSE 0.0 END), 1) as positive_clv_pct,
    ROUND(AVG(clv_cents), 1) as avg_clv_cents
FROM bet_recommendations
WHERE clv_cents IS NOT NULL;
```

**Current Status (measured 2026-03-26, N=5,315):**

| Metric | Value | Target | Status |
|--------|-------|--------|--------|
| Positive CLV % | 51.9% | > 50% | ⚠️ INSUFFICIENT DATA |
| Avg CLV (clean) | -3.5 cents | > 0 | ❌ FAIL |
| Data window | Feb 27 – Mar 26 | 30+ days | ⚠️ CONTAMINATED |

**Gate 3 verdict: ⚠️ INSUFFICIENT DATA — capture mechanism was broken**

Notes:
- CLV capture bug (Issue #37 regions mismatch) affected Feb 27 – Mar 21 (~75% of current window). Fix shipped Mar 21 (`004b3c3`). Effective clean data = ~5 days.
- 17 known artifact rows with `ABS(clv_cents) >= 200` (worst: -1,523 cents from Claxton bug). These pull the average negative.
- Gate 3 cannot be fairly evaluated until a clean 30-day post-fix window accumulates (target: ~April 20, 2026).
- Positive CLV % at 51.9% is directionally correct — re-evaluate when N from clean captures reaches 1,000+.

---

## Gate Summary

| Gate | Metric | Status | Next Action |
|------|--------|--------|-------------|
| 1 — RMSE | PTS 7.93 (target <7.0) | ❌ FAIL | Sprint 5: simulation variance reduction |
| 2 — Hit Rate | Overall 52.6% / 10%+ edge 51.2% | ⚠️ PARTIAL | v2.0-three-lens CONTRARIAN lens monitoring |
| 3 — CLV | Insufficient clean data | ⚠️ PENDING | Re-evaluate ~April 20 (post-fix 30-day window) |

**Overall model status: CALIBRATION IN PROGRESS**
Gates 1 and 2 show active issues. Gate 3 is pending data quality remediation. Production pipeline continues with mitigations (Kelly gate, Three-Lens curation) while calibration improves.

---

## Process

**Updating this document:**
1. Run the direct queries above against `ludi.db`
2. Update the Current Status tables with new values and date
3. Update the Gate Summary table
4. Commit with message: `docs(gates): update validation gate measurements YYYY-MM-DD`

**Gate pass conditions:**
- Gate 1: ALL three stats pass (PTS < 7.0, AST < 2.5, REB < 3.5)
- Gate 2: BOTH conditions pass (overall > 52% AND 10%+ edge > 55%)
- Gate 3: positive CLV % > 50% on N ≥ 1,000 clean captures with avg CLV > 0

**Sprint gate enforcement:**
- Any sprint item listed as "BLOCKED on calibration" must cite which gate is failing.
- Sprint items that modify the simulation (Module C) require Gate 1 re-measurement after deploy.
- Sprint items that modify curation (curate_plays.py) require Gate 2 re-measurement after 14 days.
