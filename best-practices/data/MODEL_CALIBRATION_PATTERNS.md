# Model Calibration Patterns for Sports Analytics

**Created:** March 8, 2026
**Purpose:** Reusable patterns for calibrating projection models using offline ML — learned constants baked into deterministic pipelines
**Source:** Phase 9 research sprint (30+ academic papers, domain-specific sports betting studies)
**Core principle:** ML learns constants OFFLINE; math stays deterministic at runtime. Zero LLM in the simulation loop.

---

## Why Calibration > Accuracy

**The single most important finding from our research:**

> Calibration-optimized models generated **69.86% higher returns** than accuracy-optimized models (+34.69% ROI vs -35.17% ROI).
> — ML in Sports Betting, 2024

**What this means:** It's more profitable to have a model that says "I'm 60% confident" and is RIGHT about being 60% confident, than a model that's "accurate" on average but overconfident on individual predictions.

**Practical implication:** Brier Score should be the PRIMARY backtest metric, not hit rate or RMSE alone.

---

## Pattern 1: Brier Score as Primary Metric

**What:** `BS = mean((predicted_prob - actual_outcome)^2)` where outcome is 0 or 1.

**Decomposition:**
- **Reliability** (calibration): Do 60% predictions actually hit 60%?
- **Resolution** (sharpness): Does the model distinguish easy from hard predictions?
- **Uncertainty** (irreducible): Base rate of the outcome

**Implementation:**
```python
from sklearn.metrics import brier_score_loss
import numpy as np

# predicted_prob = model's probability of OVER hitting
# actual = 1 if OVER hit, 0 if UNDER hit
bs = brier_score_loss(actual, predicted_prob)

# Calibration curve (reliability diagram)
from sklearn.calibration import calibration_curve
prob_true, prob_pred = calibration_curve(actual, predicted_prob, n_bins=10)
# Plot prob_pred (x) vs prob_true (y) — perfect = 45-degree line
```

**Interpretation:**
- BS < 0.20 = well-calibrated
- BS 0.20-0.25 = acceptable, room for improvement
- BS > 0.25 = poorly calibrated — model needs recalibration before trusting edges

**When to run:** Weekly (Tuesday backtest cycle), or after any modifier change.

---

## Pattern 2: Isotonic Regression for Edge Calibration

**What:** Non-parametric, monotonic mapping from model probability to actual win probability per stat category.

**Why isotonic:** It guarantees monotonicity (higher model prob → higher calibrated prob) while being completely non-parametric (no assumption about curve shape). This is critical for edge calibration — a model that says 65% should never map to LOWER actual win rate than one that says 55%.

**Implementation:**
```python
from sklearn.isotonic import IsotonicRegression

# Per stat category (PTS, REB, AST, etc.)
for stat in ['PTS', 'REB', 'AST', 'BLK', 'STL', '3PM']:
    mask = df['stat_category'] == stat
    iso = IsotonicRegression(out_of_bounds='clip')
    iso.fit(df.loc[mask, 'model_prob'], df.loc[mask, 'actual_win'])

    # Save as lookup table
    calibration[stat] = {
        'x': iso.X_thresholds_.tolist(),
        'y': iso.y_thresholds_.tolist()
    }
```

**Integration pattern:**
```python
# In Module F, replace static deflator:
# OLD: calibrated_edge = edge * 0.81  (static 19% deflation for PTS)
# NEW: calibrated_prob = np.interp(model_prob, iso_x, iso_y)
```

**Minimum sample:** 200 bets per stat category. Below that, fall back to existing static deflators.

**Retraining cadence:** Monthly, or when Brier Score degrades > 0.03 from baseline.

---

## Pattern 3: Per-Stat Variance Learning

**What:** Replace uniform simulation variance with stat-specific coefficients of variation.

**Why:** A player averaging 25 PTS has std ~7 (CV=0.28). A player averaging 1.5 BLK has std ~1.2 (CV=0.80). Using the same variance parameter for both creates artificial precision on PTS and artificial uncertainty on BLK.

**Implementation:**
```python
# From player_game_logs, compute per-stat coefficient of variation
for stat in ['pts', 'reb', 'ast', 'blk', 'stl', 'fg3m']:
    player_stats = df.groupby('player_name')[stat].agg(['mean', 'std'])
    # Filter: only players with >= 10 games and mean > 0
    valid = player_stats[(player_stats['mean'] > 0) & (player_stats.index.map(game_count) >= 10)]
    cv = (valid['std'] / valid['mean']).median()
    variance_coefficients[stat] = round(cv, 3)
```

**Expected output:** `{"pts": 0.28, "reb": 0.35, "ast": 0.40, "blk": 0.55, "stl": 0.60, "fg3m": 0.50}`

**Clamping:** [0.15, 0.70] — prevents pathological values from rare stats.

---

## Pattern 4: Bayesian Season Blending

**What:** Replace hardcoded "15-game threshold" for season-vs-recent blending with a Beta-Binomial conjugate prior that naturally adapts.

**Why the 15-game threshold is arbitrary:** 15 games works for PTS (high variance, needs samples), but for AST (lower variance, pattern emerges faster), the optimal threshold is ~8. A Bayesian prior handles this automatically.

**Implementation:**
```python
# Bayesian shrinkage toward season average
alpha_prior = season_mean * strength  # strength = how much to trust prior
beta_prior = (1 - season_mean) * strength
alpha_posterior = alpha_prior + recent_hits
beta_posterior = beta_prior + recent_misses

blended_estimate = alpha_posterior / (alpha_posterior + beta_posterior)
confidence = 1.0 / (1.0 + (alpha_posterior + beta_posterior) ** -0.5)
```

**Key insight:** `strength` parameter controls how quickly the model trusts recent data over season average. Learn `strength` per stat from settlement residuals.

---

## Pattern 5: Residual Analysis

**What:** Compute `(actual_result - projection)` grouped by every available dimension.

**Standard dimensions:**
- `stat_category` (PTS, REB, AST, BLK, STL, 3PM, TOV)
- `archetype` (15 offensive archetypes)
- `defensive_scheme` (PAINT_PACK, BLITZ, PERIMETER, NEUTRAL)
- `home_away`
- `rest_days` (B2B vs 1 day vs 2+ days)
- `bet_side` (OVER vs UNDER)
- `edge_bucket` (5-8%, 8-12%, 12-16%, 16%+)

**What to look for:**
- Mean residual > ±1.0 pts → systematic bias (model consistently over/under-projects)
- Residual std >> baseline → model unreliable for this dimension
- One dimension dominates → that's where calibration effort should focus

**Example finding:** "PTS OVER: mean residual +0.92 (underprojected). Model says 22.5, actuals average 23.4. Correction: inflate PTS projections by ~0.9 or recalibrate PTS-specific isotonic curve."

---

## Pattern 6: Edge Monotonicity Test

**What:** Group bets by edge bucket and check: do higher-edge bets actually hit at higher rates?

**Why this matters:** If DIAMOND (15%+ edge) hits at 51.4% but BLUE_CHIP (10-15%) hits at 57.9%, the edge calculation has an inversion at the top tier. This means the model is LESS reliable when it's MOST confident — the opposite of what a calibrated model should do.

**Implementation:**
```python
edge_buckets = [(5, 8), (8, 12), (12, 16), (16, 100)]
for low, high in edge_buckets:
    mask = (df['true_edge'] >= low) & (df['true_edge'] < high)
    wr = df.loc[mask, 'win'].mean()
    n = mask.sum()
    p_value = binom_test(int(wr * n), n, 0.5)
    # Report: edge_range, win_rate, n, p_value, significant (p < 0.05)
```

**Expected result for calibrated model:** Monotonically increasing win rate: 5-8% edge → ~52% WR, 8-12% → ~55%, 12-16% → ~58%, 16%+ → ~60%+.

**If inverted:** The edge formula (Module F) needs recalibration — likely the devigging is asymmetric or the stat-specific deflators are wrong.

---

## Pattern 7: Binomial Significance Guard

**What:** Never trust a hit rate without checking if it's statistically distinguishable from coin-flip.

**Implementation:**
```python
from scipy.stats import binom_test

# Only report finding if:
# 1. N >= 50 (sufficient sample)
# 2. p < 0.05 (statistically significant)
p_value = binom_test(wins, total, 0.5)
significant = (total >= 50) and (p_value < 0.05)
```

**Why N=50:** At 55% true win rate, you need ~50 bets for 80% power to detect the effect. Below that, you're reporting noise.

**Apply to:** Every win rate reported in backtest, every pattern Lena discovers, every edge bucket analysis.

---

## Anti-Patterns (What NOT to Do)

| Anti-Pattern | Why It's Wrong | Correct Approach |
|-------------|---------------|-----------------|
| Using hit rate alone to evaluate model | Luck variance swamps signal at N < 200 | Brier Score + calibration curve + hit rate together |
| Training on all data, testing on all data | Overfitting guaranteed | Temporal split: train on pre-freeze data, test on post-freeze |
| Calibrating then testing on same data | Circular validation | Hold out 20% of bets for testing, never touch during calibration |
| Static constants updated by "feel" | Drift undetected, no accountability | Learn from data → bake into JSON → validate with residual analysis |
| CLV as primary metric for props | Prop markets lack sharp liquidity | CLV is supplementary; WR + calibration are primary |

---

## References

- ML in Sports Betting 2024 — Calibration vs accuracy ROI study
- SportQA (NAACL 2024) — LLM sports reasoning benchmark
- sklearn isotonic regression docs — `sklearn.isotonic.IsotonicRegression`
- scipy binomial test — `scipy.stats.binom_test`
- Platt Scaling (1999) — Probabilistic outputs for SVMs (alternative to isotonic)

---

*Created March 8, 2026 — reusable patterns for any sports projection model*
