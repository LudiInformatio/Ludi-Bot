import sqlite3
import os
import pandas as pd
import numpy as np
from datetime import datetime

DB_PATH = "ludi.db"
REPORT_DIR = "reports"

# Per-stat RMSE targets — each stat has a different scale,
# so we need separate thresholds instead of one global RMSE.
RMSE_TARGETS = {
    "PTS": 8.0,
    "AST": 4.0,
    "REB": 5.0,
    "3PM": 2.0,
    "BLOCKS": 1.5,
    "STEALS": 1.5,
    "TURNOVERS": 2.0,
}

# Hit rate threshold for GO/NO-GO decision
HIT_RATE_TARGET = 52.0


def generate_report():
    """Main report generator. Queries ludi.db and produces both
    console output and a date-stamped markdown file."""

    today = datetime.now().strftime("%Y-%m-%d")
    output_file = os.path.join(REPORT_DIR, f"validation_report_{today}.md")
    os.makedirs(REPORT_DIR, exist_ok=True)

    conn = sqlite3.connect(DB_PATH)

    # ── Load settled bets (exclude VOIDs which have actual_result < 0) ──
    query = """
        SELECT *
        FROM bet_recommendations
        WHERE outcome IN ('WIN', 'LOSS', 'PUSH')
          AND actual_result >= 0
    """
    df = pd.read_sql_query(query, conn)

    # Total bets in table (settled + unsettled) for context
    total_all = pd.read_sql_query(
        "SELECT COUNT(*) as n FROM bet_recommendations", conn
    )["n"][0]

    conn.close()

    if df.empty:
        print("No settled bets found. Cannot generate validation report.")
        return

    # ──────────────────────────────────────────────
    # 1. CORE METRICS
    # ──────────────────────────────────────────────
    total_bets = len(df)
    wins = len(df[df["outcome"] == "WIN"])
    losses = len(df[df["outcome"] == "LOSS"])
    pushes = len(df[df["outcome"] == "PUSH"])
    hit_rate = (wins / (wins + losses)) * 100 if (wins + losses) > 0 else 0
    pnl = df["profit_loss"].sum()
    roi = (pnl / df["units"].sum()) * 100 if df["units"].sum() > 0 else 0

    # Date range of the data
    date_min = df["game_date"].min() if "game_date" in df.columns else "N/A"
    date_max = df["game_date"].max() if "game_date" in df.columns else "N/A"

    # ──────────────────────────────────────────────
    # 2. PER-STAT RMSE (not one global number)
    # ──────────────────────────────────────────────
    # Compute RMSE separately per stat category because mixing PTS errors
    # (scale ~20) with BLK errors (scale ~1) produces a meaningless number.
    stat_rmse = {}
    for cat in sorted(df["stat_category"].unique()):
        sub = df[df["stat_category"] == cat]
        errors = sub["actual_result"] - sub["projection"]
        rmse_val = np.sqrt((errors ** 2).mean())
        target = RMSE_TARGETS.get(cat, 5.0)  # fallback target
        stat_rmse[cat] = {"count": len(sub), "rmse": rmse_val, "target": target}

    # ──────────────────────────────────────────────
    # 3. BRIER SCORE (model calibration metric)
    # ──────────────────────────────────────────────
    # Brier score = mean((model_prob - outcome_binary)^2)
    # Lower is better. 0.25 = coin flip, <0.20 = decent, <0.15 = good.
    df_brier = df[df["outcome"].isin(["WIN", "LOSS"])].copy()
    df_brier["outcome_binary"] = (df_brier["outcome"] == "WIN").astype(int)
    # model_prob might be null for some rows; drop those
    df_brier = df_brier.dropna(subset=["model_prob"])
    if len(df_brier) > 0:
        brier_score = ((df_brier["model_prob"] - df_brier["outcome_binary"]) ** 2).mean()
    else:
        brier_score = None

    # ──────────────────────────────────────────────
    # 4. EDGE DISTRIBUTION
    # ──────────────────────────────────────────────
    # Bucket bets by true_edge to see how many are in each range.
    # Negative-edge bets are a known bug — they should not exist.
    edge_buckets = {
        "Negative (< 0%)": len(df[df["true_edge"] < 0]),
        "0 - 5%": len(df[(df["true_edge"] >= 0) & (df["true_edge"] < 5)]),
        "5 - 7%": len(df[(df["true_edge"] >= 5) & (df["true_edge"] < 7)]),
        "7 - 10%": len(df[(df["true_edge"] >= 7) & (df["true_edge"] < 10)]),
        "10 - 15%": len(df[(df["true_edge"] >= 10) & (df["true_edge"] < 15)]),
        "15%+": len(df[df["true_edge"] >= 15]),
    }

    # Hit rate per edge bucket (for quality analysis)
    edge_hr = {}
    for label, (lo, hi) in [
        ("Negative", (-999, 0)),
        ("0-5%", (0, 5)),
        ("5-7%", (5, 7)),
        ("7-10%", (7, 10)),
        ("10-15%", (10, 15)),
        ("15%+", (15, 999)),
    ]:
        sub = df[(df["true_edge"] >= lo) & (df["true_edge"] < hi)]
        w = len(sub[sub["outcome"] == "WIN"])
        l = len(sub[sub["outcome"] == "LOSS"])
        edge_hr[label] = (w / (w + l)) * 100 if (w + l) > 0 else 0

    # ──────────────────────────────────────────────
    # 5. TIER DISTRIBUTION (health check)
    # ──────────────────────────────────────────────
    tier_dist = df["confidence_tier"].value_counts().to_dict()
    tier_count = len(tier_dist)
    # Flag: if only 1 tier exists, the tier system is broken
    tier_broken = tier_count <= 1

    # ──────────────────────────────────────────────
    # 6. PERFORMANCE BY STAT CATEGORY (with hit rate)
    # ──────────────────────────────────────────────
    stat_perf = []
    for cat in sorted(df["stat_category"].unique()):
        sub = df[df["stat_category"] == cat]
        w = len(sub[sub["outcome"] == "WIN"])
        l = len(sub[sub["outcome"] == "LOSS"])
        hr = (w / (w + l)) * 100 if (w + l) > 0 else 0
        cat_pnl = sub["profit_loss"].sum()
        stat_perf.append({
            "Stat": cat,
            "Bets": len(sub),
            "W-L": f"{w}-{l}",
            "Hit Rate": f"{hr:.1f}%",
            "PnL": f"{cat_pnl:+.2f}u",
            "RMSE": f"{stat_rmse[cat]['rmse']:.2f}",
            "Target": f"< {stat_rmse[cat]['target']:.1f}",
            "Pass": "PASS" if stat_rmse[cat]["rmse"] < stat_rmse[cat]["target"] else "FAIL",
        })

    # ──────────────────────────────────────────────
    # 7. PERFORMANCE BY ARCHETYPE
    # ──────────────────────────────────────────────
    arch_perf = []
    if "archetype" in df.columns:
        for arch in sorted(df["archetype"].dropna().unique()):
            sub = df[df["archetype"] == arch]
            w = len(sub[sub["outcome"] == "WIN"])
            l = len(sub[sub["outcome"] == "LOSS"])
            hr = (w / (w + l)) * 100 if (w + l) > 0 else 0
            arch_pnl = sub["profit_loss"].sum()
            arch_perf.append({
                "Archetype": arch,
                "Bets": len(sub),
                "Hit Rate": f"{hr:.1f}%",
                "PnL": f"{arch_pnl:+.2f}u",
            })
        # Sort by bet count descending
        arch_perf.sort(key=lambda x: x["Bets"], reverse=True)

    # ──────────────────────────────────────────────
    # 8. GO / NO-GO DECISION
    # ──────────────────────────────────────────────
    # Check per-stat RMSE: how many stats pass their target?
    rmse_passes = sum(1 for v in stat_rmse.values() if v["rmse"] < v["target"])
    rmse_total = len(stat_rmse)

    if hit_rate >= HIT_RATE_TARGET and rmse_passes == rmse_total:
        status = "GO"
        status_emoji = "GO"
        recommendation = "All criteria met. Model is production-ready."
    elif hit_rate < 50.0:
        status = "NO-GO"
        status_emoji = "NO-GO"
        recommendation = "CRITICAL: Hit rate below breakeven. Extend calibration phase."
    elif hit_rate < HIT_RATE_TARGET:
        status = "CAUTION"
        status_emoji = "CAUTION"
        recommendation = f"Hit rate below {HIT_RATE_TARGET}% target. Review stat-level RMSE failures."
    else:
        # Hit rate OK but some RMSE targets missed
        status = "CAUTION"
        status_emoji = "CAUTION"
        failed_stats = [k for k, v in stat_rmse.items() if v["rmse"] >= v["target"]]
        recommendation = f"Hit rate OK but RMSE targets missed for: {', '.join(failed_stats)}."

    # ══════════════════════════════════════════════
    # CONSOLE OUTPUT
    # ══════════════════════════════════════════════
    sep = "=" * 64
    print(f"\n{sep}")
    print(f"  LUDI VALIDATION REPORT  |  {today}  |  {status}")
    print(f"{sep}")
    print(f"  Date Range : {date_min} to {date_max}")
    print(f"  Settled    : {total_bets:,} bets  ({wins}W / {losses}L / {pushes}P)")
    print(f"  Hit Rate   : {hit_rate:.1f}%  (target > {HIT_RATE_TARGET}%)")
    print(f"  PnL        : {pnl:+.2f}u")
    print(f"  ROI        : {roi:+.1f}%")
    if brier_score is not None:
        print(f"  Brier Score: {brier_score:.4f}  (lower is better, 0.25 = coin flip)")
    print(f"{sep}")

    # Per-stat RMSE table
    print(f"\n  {'STAT':<12} {'BETS':>6} {'RMSE':>7} {'TARGET':>8} {'RESULT':>8}")
    print(f"  {'-'*12} {'-'*6} {'-'*7} {'-'*8} {'-'*8}")
    for cat, info in sorted(stat_rmse.items(), key=lambda x: x[1]["count"], reverse=True):
        passed = "PASS" if info["rmse"] < info["target"] else "FAIL"
        print(f"  {cat:<12} {info['count']:>6} {info['rmse']:>7.2f} {'< ' + str(info['target']):>8} {passed:>8}")

    # Edge distribution table
    print(f"\n  {'EDGE BUCKET':<18} {'COUNT':>7} {'HIT RATE':>10}")
    print(f"  {'-'*18} {'-'*7} {'-'*10}")
    for (label, count), (_, hr_val) in zip(edge_buckets.items(), edge_hr.items()):
        pct = f"{count / total_bets * 100:.1f}%" if total_bets > 0 else "0%"
        print(f"  {label:<18} {count:>5} ({pct:>5})  {hr_val:>6.1f}%")

    # Tier check
    print(f"\n  TIER DISTRIBUTION:")
    for tier, count in sorted(tier_dist.items(), key=lambda x: x[1], reverse=True):
        print(f"    {tier}: {count:,} ({count/total_bets*100:.1f}%)")
    if tier_broken:
        print(f"  *** WARNING: Only {tier_count} tier(s) found. Tier system is BROKEN. ***")

    # CLV warning
    print(f"\n  CLV STATUS: UNRELIABLE (71%+ of values are 0.0 placeholder data)")
    print(f"  --> CLV metrics are NOT computed. Fix CLV capture before trusting this data.")

    # GO/NO-GO
    print(f"\n{sep}")
    print(f"  VERDICT: {status}")
    print(f"  {recommendation}")
    print(f"{sep}\n")

    # ══════════════════════════════════════════════
    # MARKDOWN FILE
    # ══════════════════════════════════════════════
    md = f"""# Ludi Informatio - Validation Report
**Date:** {today}
**Data Range:** {date_min} to {date_max}
**Status:** {status}
**Recommendation:** {recommendation}

---

## 1. Executive Summary

| Metric | Result | Target | Status |
|--------|--------|--------|--------|
| **Settled Bets** | {total_bets:,} | 50+ | {"PASS" if total_bets >= 50 else "FAIL"} |
| **Record** | {wins}W / {losses}L / {pushes}P | -- | -- |
| **Hit Rate** | {hit_rate:.1f}% | > {HIT_RATE_TARGET}% | {"PASS" if hit_rate >= HIT_RATE_TARGET else "FAIL"} |
| **PnL** | {pnl:+.2f}u | > 0 | {"PASS" if pnl > 0 else "FAIL"} |
| **ROI** | {roi:+.1f}% | > 0% | {"PASS" if roi > 0 else "FAIL"} |
| **Brier Score** | {f"{brier_score:.4f}" if brier_score is not None else "N/A"} | < 0.25 | {"PASS" if brier_score and brier_score < 0.25 else "FAIL" if brier_score else "N/A"} |

---

## 2. Per-Stat RMSE

> RMSE is split by stat category because mixing PTS errors (scale ~20) with BLK errors (scale ~1) would produce a meaningless aggregate number.

| Stat | Bets | RMSE | Target | Status |
|------|------|------|--------|--------|
"""
    for row in sorted(stat_perf, key=lambda x: x["Bets"], reverse=True):
        md += f"| {row['Stat']} | {row['Bets']} | {row['RMSE']} | {row['Target']} | {row['Pass']} |\n"

    md += f"""
---

## 3. Performance by Stat Category

| Stat | Bets | W-L | Hit Rate | PnL |
|------|------|-----|----------|-----|
"""
    for row in sorted(stat_perf, key=lambda x: x["Bets"], reverse=True):
        md += f"| {row['Stat']} | {row['Bets']} | {row['W-L']} | {row['Hit Rate']} | {row['PnL']} |\n"

    if arch_perf:
        md += f"""
---

## 4. Performance by Archetype

| Archetype | Bets | Hit Rate | PnL |
|-----------|------|----------|-----|
"""
        for row in arch_perf:
            md += f"| {row['Archetype']} | {row['Bets']} | {row['Hit Rate']} | {row['PnL']} |\n"

    md += f"""
---

## 5. Edge Distribution

> Negative-edge bets should not exist (known bug from pre-V5.2 code). The 5%+ buckets are where real value lives.

| Edge Bucket | Count | % of Total | Hit Rate |
|-------------|-------|------------|----------|
"""
    for (label, count), (_, hr_val) in zip(edge_buckets.items(), edge_hr.items()):
        pct = f"{count / total_bets * 100:.1f}%" if total_bets > 0 else "0%"
        md += f"| {label} | {count:,} | {pct} | {hr_val:.1f}% |\n"

    md += f"""
---

## 6. Tier Distribution

"""
    for tier, count in sorted(tier_dist.items(), key=lambda x: x[1], reverse=True):
        md += f"- **{tier}**: {count:,} ({count/total_bets*100:.1f}%)\n"

    if tier_broken:
        md += f"""
> **WARNING:** Only {tier_count} tier(s) found across {total_bets:,} bets. The tier classification system is **BROKEN** -- all bets are being assigned the same tier regardless of edge strength. This was a known issue in pre-V5.2 Module F. The V5.2 fix (composite tiers with edge-based + gold combos) should resolve this going forward, but historical data remains all-DIAMOND.
"""

    md += f"""
---

## 7. CLV (Closing Line Value)

> **DATA QUALITY WARNING:** CLV data is currently UNRELIABLE. Approximately 71% of CLV values are 0.0 (placeholder). CLV metrics are intentionally NOT computed in this report. Do not draw conclusions from CLV data until the forward CLV capture system (`scripts/capture_closing_lines.py`) has been running reliably for 30+ days.

---

## 8. Brier Score (Model Calibration)

"""
    if brier_score is not None:
        md += f"""- **Brier Score:** {brier_score:.4f}
- **Interpretation:** Measures how well `model_prob` predicts actual outcomes. Lower is better.
  - 0.25 = coin flip (no skill)
  - 0.20 = decent calibration
  - 0.15 = good calibration
  - < 0.10 = excellent
- **Sample:** {len(df_brier):,} bets with valid model_prob
"""
    else:
        md += "- No valid model_prob data found. Cannot compute Brier score.\n"

    md += f"""
---

## 9. GO / NO-GO Assessment

**Criteria:**

| Check | Threshold | Result | Status |
|-------|-----------|--------|--------|
| Hit Rate | > {HIT_RATE_TARGET}% | {hit_rate:.1f}% | {"PASS" if hit_rate >= HIT_RATE_TARGET else "FAIL"} |
| RMSE (per-stat) | All pass targets | {rmse_passes}/{rmse_total} pass | {"PASS" if rmse_passes == rmse_total else "FAIL"} |
| Tier System | > 1 tier | {tier_count} tier(s) | {"PASS" if not tier_broken else "FAIL (BROKEN)"} |
| Negative Edges | 0 | {edge_buckets.get("Negative (< 0%)", 0):,} | {"PASS" if edge_buckets.get("Negative (< 0%)", 0) == 0 else "FAIL"} |

**Verdict: {status}**
{recommendation}

---

*Generated by Ludi Validation Engine on {today}*
*Data: {total_bets:,} settled bets from {date_min} to {date_max}*
"""

    with open(output_file, "w") as f:
        f.write(md)

    print(f"Report saved to {output_file}")


if __name__ == "__main__":
    generate_report()
