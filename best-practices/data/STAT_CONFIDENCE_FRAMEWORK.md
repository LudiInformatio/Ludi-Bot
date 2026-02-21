# Stat Confidence & Edge Calibration Framework

**Created:** February 20, 2026
**Sources:** Ludi-Bot bet_recommendations (14,000+ settled bets) + DraftEdge/Unabated/Rithmm methodology research
**Purpose:** Define how we measure, report, and act on stat-category-specific confidence — separate from raw edge %

---

## The Problem We Solved

Our Monte Carlo model was reporting 35–40% edge on PTS/REB/AST. Those bets were winning at 48–52%.
Meanwhile, BLOCKS UNDER had a **negative** average edge (-2.8%) but won 66.4% of the time.

**The edge number was wrong — not the projection.**

Root cause: edge = `(model_prob - fair_prob) / fair_prob`. Both `model_prob` (from our sim) and `fair_prob` (from devigging) are imperfect, and the errors compound differently by stat. High-variance stats (PTS, PRA, REB combos) have noisy model probs. Low-line stats (BLOCKS, STEALS) have book-set lines that are systematically biased.

---

## The Stock Market Analogy

Think of stat categories like asset classes. Size accordingly.

| Tier | Asset | Stats | Why |
|------|-------|-------|-----|
| **Blue Chip** | Stable, proven dividend | BLOCKS UNDER, 3PM UNDER | Low RMSE (0.35–0.67), structural book inefficiency, iron-clad sample sizes |
| **Growth** | Emerging signal, watch carefully | STEALS UNDER, TURNOVERS UNDER | Improving trend or strong WR but small sample (n<200) |
| **Cyclical** | Works sometimes, market-efficient | AST, PTS | Medium variance; books are sharp here; need higher edge to bet |
| **Speculative** | High upside but unreliable | REB OVER, PRA | Actively degrading WR; projection RMSE > 3; model overconfident |
| **Avoid** | Structural losers | PRA OVER, PA OVER | Wilson lower bound < 30%; consistent money-losers |

---

## The Signal Quality Matrix (Updated Nightly)

Data from `cache/stat_confidence.json` (built by `scripts/build_stat_confidence.py`).

### As of Feb 20, 2026 (14,000+ settled bets)

| Stat | Side | WR% | Wilson LB | RMSE | n | Trend | Grade | Calibration Gap |
|------|------|-----|-----------|------|---|-------|-------|-----------------|
| BLOCKS | UNDER | 70.7% | **68.7%** | 0.35 | 2,187 | STABLE | **A+ IRON-CLAD** | +17.8% (underestimated) |
| TURNOVERS | UNDER | 72.2% | **65.0%** | — | 169 | SMALL_N | **B SOLID** | +9.0% |
| 3PM | UNDER | 61.4% | **58.9%** | 0.67 | 1,470 | STABLE | **B RELIABLE** | -11% |
| STEALS | UNDER | 54.8% | **52.4%** | 0.46 | 1,644 | IMPROVING | **C MODERATE** | ~0% |
| AST | UNDER | 54.3% | 51.7% | 1.24 | 1,381 | STABLE | **C MODERATE** | -13% |
| REB | UNDER | 55.3% | 52.6% | 1.87 | 1,333 | DEGRADING | **C MODERATE** | -18% |
| PTS | UNDER | 51.6% | 49.4% | 4.93 | 1,977 | DEGRADING | **D UNCERTAIN** | -19.5% |
| PTS | OVER | 47.5% | 44.4% | 4.93 | 1,024 | STABLE | **D UNCERTAIN** | -19.5% |
| REB | OVER | 39.7% | 36.7% | 1.87 | 974 | DEGRADING | **D UNCERTAIN** | -18% |
| PA | OVER | 36.9% | 26.2% | 4.80 | 65 | SMALL_N | **D UNCERTAIN** | -14% |
| PRA | OVER | 25.0% | **16.8%** | 5.51 | 80 | AVOID | **F AVOID** | -21% |

**Calibration Gap** = actual WR% minus what the model's average edge would predict. Negative means model overstates edge.

---

## Three Layers of Smarter Betting

### Layer 1: Edge Calibration (Module F) — Fix the Core Number

The raw `true_edge` is systematically wrong for high-variance stats. Apply a calibration multiplier **before** tiering.

```python
# Edge calibration factors — derived from (calibration_gap / avg_edge) analysis
EDGE_CALIBRATION = {
    'BLOCKS':     {'UNDER': 1.25, 'OVER': 1.00},   # underestimated — boost
    'TURNOVERS':  {'UNDER': 1.10, 'OVER': 1.00},   # real signal, small sample
    'STEALS':     {'UNDER': 1.00, 'OVER': 1.00},   # well-calibrated
    '3PM':        {'UNDER': 0.90, 'OVER': 0.90},   # slight overconfidence
    'AST':        {'UNDER': 0.85, 'OVER': 0.85},   # 13% overconfident
    'REB':        {'UNDER': 0.82, 'OVER': 0.80},   # 18% overconfident + degrading
    'PTS':        {'UNDER': 0.80, 'OVER': 0.78},   # 19.5% overconfident
    'PRA':        {'UNDER': 0.85, 'OVER': 0.70},   # most volatile; OVER is structural avoid
    'PA':         {'UNDER': 0.90, 'OVER': 0.70},   # PA OVER 36.9% WR (D grade)
    'PR':         {'UNDER': 0.88, 'OVER': 0.75},   # PR OVER 38.2% WR
    'RA':         {'UNDER': 0.92, 'OVER': 0.92},   # moderate, small sample
}
```

**Result:** A PTS UNDER bet with 10% raw edge becomes 8% calibrated edge, placing it in CORE ASSET (was BLUE CHIP). The tier now reflects reality.

### Layer 2: Confidence-Weighted Sizing (Module F) — RMSE Affects Units

Low projection certainty = smaller bet, even at the same tier.

```python
# RMSE grades → sizing modifier
RMSE_SIZING = {
    'BLOCKS':    0.35,   # multiplier = 1.00 (no penalty)
    'STEALS':    0.46,   # multiplier = 1.00
    '3PM':       0.67,   # multiplier = 1.00
    'AST':       1.24,   # multiplier = 0.95
    'REB':       1.87,   # multiplier = 0.90
    'PTS':       4.93,   # multiplier = 0.85
    'PA':        4.80,   # multiplier = 0.85
    'PR':        4.96,   # multiplier = 0.85
    'PRA':       5.51,   # multiplier = 0.80
}

def rmse_sizing_modifier(stat_category):
    rmse = RMSE_SIZING.get(stat_category, 2.0)
    if rmse <= 1.0:   return 1.00
    elif rmse <= 2.0: return 0.95
    elif rmse <= 4.0: return 0.90
    else:             return 0.85   # high-variance stats get 15% size cut
```

**Combined effect example:**
| Bet | Raw Edge | Calibrated | Tier | Raw Units | RMSE Adj | Final Units |
|-----|---------|-----------|------|-----------|----------|-------------|
| BLOCKS UNDER | 8% | 10% | BLUE CHIP | 0.75u | 1.00x | **0.75u** |
| PTS OVER | 10% | 7.8% | CORE ASSET | 0.50u | 0.85x | **0.43u** |
| PRA OVER | 10% | 7.0% | CORE ASSET | 0.50u | 0.80x | **0.40u** |

### Layer 3: Claude Domain Knowledge (curate_plays.py) — Informed Curation

Inject the full signal quality matrix into the Sonnet curation system prompt dynamically:

```python
def _get_system_wr_context(conn) -> str:
    """Query live calibration-adjusted WR stats — auto-updates as season progresses."""
    rows = conn.execute("""
        SELECT stat_category, bet_side,
               COUNT(*) as n,
               ROUND(100.0 * SUM(CASE WHEN outcome='WIN' THEN 1 ELSE 0 END) / COUNT(*), 1) as wr,
               SUM(CASE WHEN outcome='WIN' THEN 1 ELSE 0 END) as wins
        FROM bet_recommendations
        WHERE outcome IN ('WIN','LOSS')
        GROUP BY stat_category, bet_side
        HAVING COUNT(*) >= 50
        ORDER BY wr DESC
    """).fetchall()

    import math
    z = 1.96
    lines = ["EMPIRICAL WIN RATES (this season, calibrated confidence):"]
    for stat, side, n, wr, wins in rows:
        p = wins / n
        denom = 1 + z**2/n
        center = (p + z**2/(2*n)) / denom
        margin = z * math.sqrt(p*(1-p)/n + z**2/(4*n**2)) / denom
        lb = max(0, center - margin)

        if lb >= 0.60 and n >= 500:   grade, note = "A+", "PRIORITIZE"
        elif lb >= 0.55 and n >= 150: grade, note = "B",  "PREFER"
        elif lb >= 0.50:              grade, note = "C",  ""
        elif lb >= 0.45:              grade, note = "D",  "DEPRIORITIZE"
        else:                         grade, note = "F",  "AVOID"

        suffix = f" ← {note}" if note else ""
        lines.append(f"  {stat} {side}: {wr:.0f}% (95% floor={lb*100:.0f}%, n={n}) [{grade}]{suffix}")

    lines.append("\nNOTE: High edge% on PTS/REB/PRA is systematically overestimated by the model.")
    lines.append("BLOCKS UNDER is a structural edge — book lines are consistently too high.")
    lines.append("STEALS UNDER is improving. REB OVER is actively degrading. PRA OVER is a structural avoid.")
    return "\n".join(lines)
```

---

## Minimum Edge Thresholds by Stat (Proposed)

The current 5% floor is uniform. These are stat-specific calibrated minimums:

| Stat Category | Side | Current Min | Proposed Min | Reason |
|---------------|------|-------------|--------------|--------|
| BLOCKS | UNDER | 5% | 3% | Structural edge; even low-edge BLOCKS UNDER wins |
| 3PM | UNDER | 5% | 5% | Well-calibrated |
| STEALS | UNDER | 5% | 5% | Well-calibrated, improving |
| AST | any | 5% | 6% | 13% overconfident |
| REB | UNDER | 5% | 6% | 18% overconfident, degrading |
| PTS | UNDER | 5% | 7% | 19.5% overconfident |
| PTS | OVER | 5% | 8% | 19.5% overconfident + OVER bias |
| REB | OVER | 5% | 9% | Degrading, 39.7% WR |
| PRA | OVER | 5% | AVOID | Structural loser (25% WR) — filter entirely |
| PA | OVER | 5% | AVOID | 36.9% WR — filter |

---

## What Competitive Platforms Do

| Platform | Key Method | Relevant to Us |
|----------|-----------|----------------|
| **DraftEdge** | MSE score → Floor/Ceiling/Volatility metrics. Blue/Green/Yellow/Red tiers | Our RMSE grades → tier color |
| **Unabated** | Mean → Median conversion for low-count stats (Poisson asymmetry) | Apply to BLOCKS/STEALS sims |
| **Rithmm** | "Smart Signals" — historical outperformance patterns trigger alerts | Our BLOCKS UNDER structural edge |
| **PlayerProps.ai** | BetScore 1-100 blending edge + sample confidence + recency | Wilson LB is our BetScore proxy |
| **OddsJam** | Positive EV scan across all markets; no stat-specific calibration | We go further with stat-specific calibration |
| **Industry finding** | 20%+ edge bets → 50-55% WR (same as our data). Sweet spot is 10-15% edge | Confirms our calibration problem |

**Key industry insight** (Unabated): For low-frequency stats (BLOCKS avg ~1.2/game), convert Poisson **mean** to **median** before comparing to line. Poisson median ≈ floor(λ + 1/3 - 1/(50λ)). A player projecting 1.2 blocks has a median of 1, not 1.2. This systematically helps UNDER bets on BLOCKS.

---

## Implementation Files

| File | Change | Phase |
|------|--------|-------|
| `scripts/build_stat_confidence.py` | Nightly: computes Wilson LB, RMSE, calibration gap → `cache/stat_confidence.json` | 8.20 |
| `module_f.py` | `_apply_stat_calibration()` + `_apply_stat_sizing()` | 8.20 |
| `scripts/curate_plays.py` | `_get_system_wr_context(conn)` → injected into Sonnet system prompt | 8.20 |
| `utils/claude_prompts.py` | Add few-shot examples to GAME_NOTES_TEMPLATE + SPOTLIGHT_TEMPLATE | 8.19 |
| `ROADMAP.md` | Phase 8.20: Stat Confidence & Edge Calibration | done |

---

## Auto-Update Cadence

`build_stat_confidence.py` runs **nightly at 5 AM** in `data_sync.yml`, after bet settlement.
As sample sizes grow, grades automatically promote (D→C→B→A+). No manual updates needed.

This means by March 2026 (~2,000 more bets), TURNOVERS UNDER (n=169 today) will have a sample-validated grade rather than "SMALL_N" — and Module F will automatically apply a tighter calibration.

---

## What NOT to Do

- **Do NOT** inject raw WR% into Claude. Use Wilson lower bound — it's the conservative, statistically-defensible number.
- **Do NOT** apply RMSE penalties to BLOCKS/STEALS. Their projection error is small in absolute terms; the high relative variance is already priced in by the low line.
- **Do NOT** filter TURNOVERS/STEALS UNDER bets. The edge is real — just acknowledge small sample in sizing.
- **Do NOT** set the minimum edge for BLOCKS UNDER above 5%. The structural book inefficiency means even "below threshold" edges hit.
- **Do NOT** build stat-specific Poisson distributions yet (Phase 9 territory). The calibration multipliers are a 95% solution for 5% of the work.

---

*Authored Feb 20, 2026 — based on 14,000+ settled bets + DraftEdge/Unabated/Rithmm methodology research*
