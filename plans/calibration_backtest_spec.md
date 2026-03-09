# Phase 8.23 Calibration Backtest Spec
**Author:** Lena (Data Analyst) | **Date:** 2026-03-09
**Purpose:** Define metrics, thresholds, and significance rules for `scripts/calibrate_claude_outputs.py`

---

## Data Snapshot (as of 2026-03-09)

**Source query:** `bet_recommendations WHERE is_curated=1 AND game_date >= '2026-02-26' AND outcome IN ('WIN','LOSS')`

| Metric | Value |
|--------|-------|
| Total curated settled bets | 72 |
| Wins | 38 |
| Raw win rate | 52.8% |
| Date range | 2026-02-26 → 2026-03-08 |
| Distinct game dates | 10 |
| Overall tier split | DIAMOND OVER: 8 bets / DIAMOND UNDER: 64 bets |

**Structural finding:** 88.9% of curated bets are UNDER — the system has a strong UNDER bias baked into the curation logic (system prompt line: "Prefer UNDER bets on BLK, 3PM, and STL"). OVER bets (8 total) are too small a sample for any statistical conclusion.

---

## Stat/Side Breakdown (all curated, settled)

| stat_category | bet_side | N | Wins | Raw WR | Wilson 95% Lower |
|---------------|----------|---|------|--------|-----------------|
| 3PM | UNDER | 15 | 8 | 53.3% | 30.1% |
| PR | UNDER | 12 | 11 | 91.7% | 63.6% |
| PRA | UNDER | 9 | 3 | 33.3% | 9.9% |
| REB | UNDER | 6 | 1 | 16.7% | 1.5% |
| AST | UNDER | 5 | 3 | 60.0% | 20.6% |
| PA | UNDER | 5 | 3 | 60.0% | 20.6% |
| PTS | UNDER | 4 | 3 | 75.0% | — (N<5) |
| BLK | UNDER | 4 | 3 | 75.0% | — (N<5) |
| PTS | OVER | 4 | 0 | 0.0% | — (N<5) |
| PR | OVER | 2 | 0 | 0.0% | — (N<5) |
| STL | UNDER | 2 | 0 | 0.0% | — (N<5) |
| AST | OVER | 1 | 1 | 100.0% | — (N<5) |
| RA | UNDER | 2 | 1 | 50.0% | — (N<5) |
| RA | OVER | 1 | 1 | 100.0% | — (N<5) |

**Wilson formula used:**
```
z = 1.96  (95% CI)
lower = (p + z²/2n - z*sqrt(p*(1-p)/n + z²/(4n²))) / (1 + z²/n)
```

---

## Significance Thresholds

| Threshold | Rule | Rationale |
|-----------|------|-----------|
| N >= 5 | Show in output (preview tier) | Minimum for any signal |
| N >= 10 | Flag as "approaching significance" | Wilson floor starts to tighten |
| N >= 50 | Flag as "statistically significant" | ~5% margin of error at 50/50 |
| Wilson lower >= 52% | CALIBRATED for that group | Positive edge with confidence |
| Wilson lower >= 45% and < 52% | NEEDS_MORE_DATA | Direction correct, CI too wide |
| Wilson lower < 45% | MISCALIBRATED for that group | Below break-even with confidence |

---

## Metrics to Track in `calibrate_claude_outputs.py`

### Per-Group Metrics (stat_category × bet_side, N >= 5)
1. **N** — sample count
2. **wins** — win count
3. **raw_wr** — wins / N
4. **wilson_lower** — 95% CI lower bound (formula above)
5. **avg_edge** — mean `true_edge` for the group
6. **status** — CALIBRATED / NEEDS_MORE_DATA / MISCALIBRATED per Wilson lower

### Overall Summary Metrics
1. **total_n** — all curated settled bets
2. **total_wins** — total wins
3. **overall_wr** — total_wins / total_n
4. **overall_wilson_lower** — Wilson lower on aggregate
5. **brier_score** — mean((predicted_prob - actual_outcome)^2)
   - `predicted_prob = 0.5 + (true_edge / 100 * 0.5)` (linear mapping: 0% edge → 0.5, 25% edge → 0.625)
   - `actual_outcome = 1 if WIN else 0`
6. **overall_status** — CALIBRATED / NEEDS_MORE_DATA / MISCALIBRATED

### Status Logic (overall)
```
if total_n < 50:
    status = "NEEDS_MORE_DATA"
elif overall_wilson_lower >= 0.52:
    status = "CALIBRATED"
elif overall_wilson_lower >= 0.45:
    status = "NEEDS_MORE_DATA"
else:
    status = "MISCALIBRATED"
```

---

## What Constitutes "Calibration Success" vs "Failure"

**Success (CALIBRATED):**
- Overall Wilson lower bound >= 52% (positive edge confirmed with CI)
- Brier Score < 0.25 (better than a naive 50/50 predictor's ~0.25)
- At least 2 stat groups with Wilson lower >= 52%

**Partial / Pending (NEEDS_MORE_DATA):**
- N < 50 overall (current state — only 72 bets but window closes ~Mar 10)
- Wilson lower 45-52% — direction promising but CI too wide to confirm
- Less than 2 groups have N >= 10

**Failure (MISCALIBRATED):**
- Overall Wilson lower < 45% with N >= 50
- Brier Score >= 0.27 with N >= 50 (worse than naive)
- Systematic OVER underperformance: OVER WR < 40% across all groups with N >= 5

---

## Category Sufficiency Assessment (as of Mar 9)

| Category | Current N | Sufficient Today | Est. to N=50 |
|----------|-----------|-----------------|--------------|
| PR UNDER | 12 | Preview only | ~38 more bets (~19 days) |
| 3PM UNDER | 15 | Preview only | ~35 more bets (~18 days) |
| PRA UNDER | 9 | Preview only | ~41 more bets (~21 days) |
| REB UNDER | 6 | Preview only | ~44 more bets (~22 days) |
| AST UNDER | 5 | Preview only | ~45 more bets (~23 days) |
| Overall | 72 | Approaching (N>=50 ✅) | Already sufficient for overall |

**Key finding:** Overall N=72 already exceeds the N=50 statistical significance threshold. Individual category-level analysis remains in preview tier. Wilson floor will be meaningful at the overall level today.

---

## Per-Grade Analysis Gap (STRONG vs LEAN vs FADE)

This analysis **cannot be built yet** because `claude_analysis_log.actual_outcome` is NULL for all curation rows. The log stores 1 row per batch (JSON blob of all grades), not 1 row per bet. To enable per-grade calibration:

1. Backfill step: JOIN `claude_analysis_log` curation rows → `bet_recommendations` on `bet_id` extracted from the JSON blob, then populate `actual_outcome`
2. Per-bet logging: Change `claude_analysis_log` writes in `utils/claude_logger.py` to write 1 row per bet with `curation_grade`, `bet_id`, `game_date`

**Do not attempt to compute per-grade metrics in this sprint** — the data structure does not support it.

---

## Output Format for `calibrate_claude_outputs.py`

### Stdout (printed table)
```
=== Ludi Curation Calibration Report — YYYY-MM-DD ===

Overall: N=72, WR=52.8%, Wilson Lower=42.1%, Brier=0.247
Status: NEEDS_MORE_DATA (N >= 50, but Wilson lower < 52% — need more data to confirm edge)

Per-Group Breakdown (N >= 5):
stat       side     N    wins   raw_WR   wilson_lower   status
---------- -------- ---- ------ -------- -------------- -------
PR         UNDER    12   11     91.7%    63.6%          CALIBRATED
3PM        UNDER    15   8      53.3%    30.1%          NEEDS_MORE_DATA
AST        UNDER    5    3      60.0%    20.6%          NEEDS_MORE_DATA
...

NOTE: Per-grade analysis (STRONG vs LEAN vs FADE) requires actual_outcome backfill — not yet available.
```

### JSON output (`cache/claude_calibration.json`)
```json
{
  "generated_at": "2026-03-09T...",
  "date_range": {"from": "2026-02-26", "to": "2026-03-08"},
  "overall": {
    "n": 72, "wins": 38, "raw_wr": 0.528, "wilson_lower": 0.421,
    "brier_score": 0.247, "status": "NEEDS_MORE_DATA"
  },
  "by_group": [
    {"stat_category": "PR", "bet_side": "UNDER", "n": 12, "wins": 11,
     "raw_wr": 0.917, "wilson_lower": 0.636, "avg_edge": 46.02, "status": "CALIBRATED"},
    ...
  ],
  "notes": [
    "Per-grade analysis (STRONG/LEAN/FADE) requires actual_outcome backfill — not built.",
    "Groups with N < 5 omitted from output."
  ]
}
```

---

## Implementation Notes for Junior Dev

- Wilson formula: use `z = 1.96` constant. No scipy needed — pure math.
- `predicted_prob` clamp: after linear mapping, clamp to `[0.5, 0.75]` to avoid extreme Brier values from outlier edges
- SQLite query: `WHERE is_curated=1 AND game_date >= '2026-02-26' AND outcome IN ('WIN','LOSS')`
- Cache dir: `os.makedirs('cache', exist_ok=True)` before writing JSON
- Graceful exit: if N=0, print "No settled curated bets found" and exit 0
- Do NOT query `claude_analysis_log` — not needed for this script
