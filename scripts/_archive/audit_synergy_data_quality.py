# ARCHIVED: 2026-03-03 — One-off audit — not operational
#!/usr/bin/env python3
"""
Audit Synergy data quality and scale consistency.

Outputs:
- reports/synergy_data_quality_<date>.md
"""

import sqlite3
from datetime import datetime
from pathlib import Path
from statistics import median


DB_PATH = "ludi.db"
SEASON = "2025-26"


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.execute("PRAGMA busy_timeout=30000;")
    return conn


def _fetch_playtype_rows(conn: sqlite3.Connection):
    cur = conn.cursor()
    cur.execute(
        """
        SELECT playtype, freq_pct, percentile, poss_per_game, games_played, team_abbr
        FROM player_synergy_playtypes
        WHERE season = ?
        """,
        (SEASON,),
    )
    return cur.fetchall()


def _build_report(rows) -> str:
    now = datetime.now()
    by_playtype = {}
    null_team = 0
    null_percentile = 0
    sig_rows = 0

    for playtype, freq, percentile, poss_pg, games, team_abbr in rows:
        by_playtype.setdefault(playtype, []).append(freq if freq is not None else 0.0)
        if not team_abbr:
            null_team += 1
        if percentile is None:
            null_percentile += 1
        total_poss = (poss_pg or 0.0) * (games or 0)
        if total_poss >= 75:
            sig_rows += 1

    lines = []
    lines.append("# Synergy Data Quality Audit")
    lines.append("")
    lines.append(f"Generated: {now.strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"Season: {SEASON}")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Total rows: {len(rows)}")
    lines.append(f"- Significant rows (poss_per_game * games_played >= 75): {sig_rows}")
    lines.append(f"- Team NULL rows: {null_team}")
    lines.append(f"- Percentile NULL rows: {null_percentile}")
    lines.append("")
    lines.append("## Playtype Scale Check")
    lines.append("")
    lines.append("| Playtype | Rows | Min | Median | Max | <=1.0 | >1.0 | Mixed Scale Flag |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|---|")

    for playtype in sorted(by_playtype):
        vals = [float(v or 0.0) for v in by_playtype[playtype]]
        if not vals:
            continue
        le_one = sum(1 for v in vals if v <= 1.0)
        gt_one = sum(1 for v in vals if v > 1.0)
        mixed = "YES" if le_one > 0 and gt_one > 0 else "NO"
        lines.append(
            f"| {playtype} | {len(vals)} | {min(vals):.4f} | {median(vals):.4f} | {max(vals):.4f} | {le_one} | {gt_one} | {mixed} |"
        )

    lines.append("")
    lines.append("## Notes")
    lines.append("")
    lines.append("- Mixed-scale playtypes should be normalized to canonical 0-100 freq_pct.")
    lines.append("- Low/NULL percentile rows should be excluded from percentile-driven rules.")
    lines.append("- Team NULL rows reduce team-level style aggregation quality.")
    lines.append("")
    return "\n".join(lines)


def main():
    reports_dir = Path("reports")
    reports_dir.mkdir(exist_ok=True)
    out_path = reports_dir / f"synergy_data_quality_{datetime.now().strftime('%Y-%m-%d')}.md"

    conn = _connect()
    rows = _fetch_playtype_rows(conn)
    conn.close()

    report = _build_report(rows)
    out_path.write_text(report, encoding="utf-8")
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
