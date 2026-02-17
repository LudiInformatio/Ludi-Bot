#!/usr/bin/env python3
"""
Backtest classification lift by archetype-playtype alignment and defensive scheme tags.

Outputs:
- reports/classification_lift_<date>.md
"""

import argparse
import json
import sqlite3
from collections import defaultdict
from datetime import datetime
from pathlib import Path


DB_PATH = "ludi.db"
SEASON = "2025-26"

ARCHETYPE_EXPECTED = {
    "HELIOCENTRIC_MAESTRO": {"P&R_HANDLER"},
    "ISO_ASSASSIN": {"ISO_SCORER"},
    "SLASHING_CREATOR": {"TRANSITION"},
    "JUMBO_FACILITATOR": {"P&R_HANDLER"},
    "SNIPER_ELITE": {"SPOT_UP", "OFF_SCREEN"},
    "TWO_LEVEL_SCORER": {"ISO_SCORER", "P&R_HANDLER"},
    "ATHLETIC_FINISHER": {"TRANSITION", "OFF_BALL_CUTTER"},
    "WARRIOR_BIG": {"P&R_ROLL_MAN", "PUTBACK"},
    "VULTURE_BIG": {"PUTBACK", "TRANSITION"},
    "STRETCH_BIG": {"SPOT_UP"},
    "POST_ANCHOR": {"POST_UP"},
    "ROLL_MAN": {"P&R_ROLL_MAN", "PUTBACK"},
    "CUTTER_SPECIALIST": {"OFF_BALL_CUTTER", "CUT"},
    "FACILITATOR": {"P&R_HANDLER"},
    "CONNECTOR": {"P&R_HANDLER", "HANDOFF"},
    "ENERGY_BIG": {"PUTBACK", "P&R_ROLL_MAN"},
}


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.execute("PRAGMA busy_timeout=30000;")
    conn.row_factory = sqlite3.Row
    return conn


def _fetch_top_playtype(conn: sqlite3.Connection) -> dict:
    cur = conn.cursor()
    cur.execute(
        f"""
        WITH ranked AS (
            SELECT
                player_name,
                playtype,
                freq_pct,
                ROW_NUMBER() OVER (
                    PARTITION BY player_name
                    ORDER BY COALESCE(freq_pct, 0) DESC
                ) AS rn
            FROM player_synergy_playtypes
            WHERE season = ?
              AND (COALESCE(poss_per_game, 0) * COALESCE(games_played, 0)) >= 75
        )
        SELECT player_name, playtype, freq_pct
        FROM ranked
        WHERE rn = 1
        """,
        (SEASON,),
    )
    return {r["player_name"]: (r["playtype"], float(r["freq_pct"] or 0.0)) for r in cur.fetchall()}


def _fetch_settled_bets(conn: sqlite3.Connection, days: int):
    cur = conn.cursor()
    cur.execute(
        """
        SELECT player_name, archetype, outcome, profit_loss, units, tags
        FROM bet_recommendations
        WHERE game_date >= date('now', '-' || ? || ' days')
          AND outcome IN ('WIN', 'LOSS', 'PUSH')
        """,
        (days,),
    )
    return cur.fetchall()


def _alignment_bucket(archetype: str, top_playtype: str) -> str:
    if not archetype or not top_playtype:
        return "no_synergy"
    expected = ARCHETYPE_EXPECTED.get(archetype)
    if not expected:
        return "unmapped"
    return "aligned" if top_playtype in expected else "mismatched"


def _parse_scheme_tags(tags_text: str):
    if not tags_text:
        return []
    try:
        tags = json.loads(tags_text)
        if isinstance(tags, list):
            return [t for t in tags if isinstance(t, str) and t.startswith("vs_")]
    except Exception:
        pass
    return []


def _compute_metrics(rows, top_map):
    buckets = defaultdict(lambda: {"bets": 0, "wins": 0, "losses": 0, "pushes": 0, "profit": 0.0, "units": 0.0})
    schemes = defaultdict(lambda: {"bets": 0, "wins": 0, "losses": 0, "pushes": 0, "profit": 0.0})

    for r in rows:
        player = r["player_name"]
        archetype = r["archetype"] or ""
        outcome = r["outcome"]
        profit = float(r["profit_loss"] or 0.0)
        units = float(r["units"] or 0.0)

        top_playtype = None
        if player in top_map:
            top_playtype = top_map[player][0]
        bucket = _alignment_bucket(archetype, top_playtype)

        b = buckets[bucket]
        b["bets"] += 1
        b["profit"] += profit
        b["units"] += units
        if outcome == "WIN":
            b["wins"] += 1
        elif outcome == "LOSS":
            b["losses"] += 1
        else:
            b["pushes"] += 1

        for scheme in _parse_scheme_tags(r["tags"]):
            s = schemes[scheme]
            s["bets"] += 1
            s["profit"] += profit
            if outcome == "WIN":
                s["wins"] += 1
            elif outcome == "LOSS":
                s["losses"] += 1
            else:
                s["pushes"] += 1

    return buckets, schemes


def _fmt_rate(wins: int, losses: int) -> float:
    den = wins + losses
    return (wins / den * 100.0) if den > 0 else 0.0


def _report(days: int, top_map: dict, buckets: dict, schemes: dict) -> str:
    lines = []
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines.append("# Classification Lift Backtest")
    lines.append("")
    lines.append(f"Generated: {now}")
    lines.append(f"Window: last {days} days")
    lines.append(f"Top-playtype coverage: {len(top_map)} players")
    lines.append("")

    lines.append("## Alignment Buckets")
    lines.append("")
    lines.append("| Bucket | Bets | Win Rate | ROI per Bet | Profit |")
    lines.append("|---|---:|---:|---:|---:|")

    for key in ["aligned", "mismatched", "unmapped", "no_synergy"]:
        b = buckets.get(key, {"bets": 0, "wins": 0, "losses": 0, "profit": 0.0})
        wr = _fmt_rate(b["wins"], b["losses"])
        roi = (b["profit"] / b["bets"]) if b["bets"] > 0 else 0.0
        lines.append(f"| {key} | {b['bets']} | {wr:.1f}% | {roi:+.3f}u | {b['profit']:+.2f}u |")

    lines.append("")
    aligned = buckets.get("aligned", {"wins": 0, "losses": 0, "profit": 0.0, "bets": 0})
    mismatched = buckets.get("mismatched", {"wins": 0, "losses": 0, "profit": 0.0, "bets": 0})
    delta_wr = _fmt_rate(aligned["wins"], aligned["losses"]) - _fmt_rate(mismatched["wins"], mismatched["losses"])
    delta_roi = ((aligned["profit"] / aligned["bets"]) if aligned["bets"] else 0.0) - (
        (mismatched["profit"] / mismatched["bets"]) if mismatched["bets"] else 0.0
    )
    lines.append(f"- Alignment WR delta (aligned - mismatched): {delta_wr:+.2f}%")
    lines.append(f"- Alignment ROI delta (aligned - mismatched): {delta_roi:+.3f}u")
    lines.append("")

    lines.append("## Defensive Scheme Tag Performance")
    lines.append("")
    lines.append("| Scheme | Bets | Win Rate | ROI per Bet | Profit |")
    lines.append("|---|---:|---:|---:|---:|")
    for scheme, s in sorted(schemes.items(), key=lambda kv: kv[1]["bets"], reverse=True):
        wr = _fmt_rate(s["wins"], s["losses"])
        roi = (s["profit"] / s["bets"]) if s["bets"] > 0 else 0.0
        lines.append(f"| {scheme} | {s['bets']} | {wr:.1f}% | {roi:+.3f}u | {s['profit']:+.2f}u |")

    lines.append("")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Backtest classification lift by alignment and scheme tags")
    parser.add_argument("--days", type=int, default=60, help="Lookback window in days")
    args = parser.parse_args()

    conn = _connect()
    top_map = _fetch_top_playtype(conn)
    rows = _fetch_settled_bets(conn, args.days)
    conn.close()

    buckets, schemes = _compute_metrics(rows, top_map)
    report = _report(args.days, top_map, buckets, schemes)

    reports_dir = Path("reports")
    reports_dir.mkdir(exist_ok=True)
    path = reports_dir / f"classification_lift_{datetime.now().strftime('%Y-%m-%d')}.md"
    path.write_text(report, encoding="utf-8")
    print(f"Wrote {path}")


if __name__ == "__main__":
    main()
