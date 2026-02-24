#!/usr/bin/env python3
"""
Audit Missing Canonical IDs
===========================
Builds a deduped list of missing canonical IDs from:
  - player_canonical_ids_staging (preferred)
  - Optional GitHub Actions log file
  - player_game_logs (unresolvable dirty IDs)

Cross-checks against:
  - player_canonical_ids (normalized_name match)
  - players table (normalized_name match)
  - ESPN rosters (optional) for espn_id lookup

Optional: auto-update tank01_aliases when a canonical match is found.

Usage:
  python scripts/audit_missing_canonical_ids.py --log-file /tmp/run.log --check-espn --update-aliases --out logs/missing_canonical_ids_YYYYMMDD.json
"""

import argparse
import json
import os
import re
import sqlite3
import time
import unicodedata
from datetime import datetime

import requests

DB_DEFAULT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ludi.db")

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 '
                  '(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
    'Accept': 'application/json',
}
TEAM_RATE_LIMIT = 0.4
ATHLETE_RATE_LIMIT = 0.1
TIMEOUT = 15

LOG_PATTERN = re.compile(r"No canonical ID for:\s+(?P<name>.+?)\s+\((?P<id>[^)]+)\)")


def normalize_name(name: str, strip_suffix: bool = True) -> str:
    if not name:
        return ""
    name = ''.join(' ' if ch.isspace() else ch for ch in name)
    name = unicodedata.normalize('NFKD', name)
    name = name.encode('ASCII', 'ignore').decode('ASCII')
    name = name.lower().strip()
    if strip_suffix:
        for suffix in [' jr.', ' jr', ' sr.', ' sr', ' iii', ' ii', ' iv', ' v']:
            name = name.replace(suffix, '')
    return ' '.join(name.split())


def parse_log_file(path: str):
    entries = []
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            match = LOG_PATTERN.search(line)
            if match:
                entries.append({
                    "source": "tank01",
                    "source_player_id": match.group("id").strip(),
                    "player_name": match.group("name").strip(),
                })
    return entries


def load_staging(conn):
    try:
        rows = conn.execute("""
            SELECT source, source_player_id, player_name, normalized_name,
                   first_game_date, last_game_date, seen_count
            FROM player_canonical_ids_staging
        """).fetchall()
        return [
            {
                "source": r[0],
                "source_player_id": r[1],
                "player_name": r[2],
                "normalized_name": r[3],
                "first_game_date": r[4],
                "last_game_date": r[5],
                "seen_count": r[6],
            }
            for r in rows
        ]
    except sqlite3.Error:
        return []


def load_unresolvable(conn):
    rows = conn.execute("""
        SELECT DISTINCT pgl.player_id, pgl.player_name, COUNT(*) as games
        FROM player_game_logs pgl
        WHERE LENGTH(pgl.player_id) > 8
        AND pgl.player_id NOT IN (SELECT canonical_id FROM player_canonical_ids)
        GROUP BY pgl.player_id, pgl.player_name
        ORDER BY games DESC
    """).fetchall()
    return [
        {
            "source": "unknown",
            "source_player_id": r[0],
            "player_name": r[1],
            "seen_count": r[2],
        }
        for r in rows
    ]


def _get(url: str) -> dict:
    try:
        r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        r.raise_for_status()
        return r.json()
    except Exception:
        return {}


def _load_espn_team_ids(conn) -> dict:
    try:
        rows = conn.execute(
            "SELECT standard_abbr, espn_id FROM canonical_teams WHERE espn_id IS NOT NULL"
        ).fetchall()
        if rows:
            return {row[0]: row[1] for row in rows}
    except Exception:
        pass
    return {
        'ATL': 1,  'BOS': 2,  'NOP': 3,  'CHI': 4,  'CLE': 5,
        'DAL': 6,  'DEN': 7,  'DET': 8,  'GSW': 9,  'HOU': 10,
        'IND': 11, 'LAC': 12, 'LAL': 13, 'MIA': 14, 'MIL': 15,
        'MIN': 16, 'BKN': 17, 'NYK': 18, 'ORL': 19, 'PHI': 20,
        'PHX': 21, 'POR': 22, 'SAC': 23, 'SAS': 24, 'OKC': 25,
        'UTA': 26, 'WAS': 27, 'TOR': 28, 'MEM': 29, 'CHA': 30,
    }


def fetch_espn_roster_map(conn):
    espn_team_ids = _load_espn_team_ids(conn)
    roster_map = {}
    for abbr, team_id in sorted(espn_team_ids.items()):
        url = (f"https://sports.core.api.espn.com/v2/sports/basketball/leagues/nba"
               f"/teams/{team_id}/athletes?limit=100")
        data = _get(url)
        for item in data.get("items", []):
            ref_url = item.get("$ref")
            if not ref_url:
                continue
            athlete = _get(ref_url)
            if not athlete:
                continue
            espn_id = str(athlete.get("id", "")).strip()
            display_name = athlete.get("displayName") or athlete.get("fullName", "")
            if espn_id and display_name:
                norm = normalize_name(display_name)
                roster_map[norm] = {"espn_id": espn_id, "display_name": display_name, "team": abbr}
            time.sleep(ATHLETE_RATE_LIMIT)
        time.sleep(TEAM_RATE_LIMIT)
    return roster_map


def update_tank01_alias(conn, canonical_id, source_player_id):
    row = conn.execute(
        "SELECT tank01_aliases FROM player_canonical_ids WHERE canonical_id = ?",
        (canonical_id,)
    ).fetchone()
    aliases = []
    if row and row[0]:
        try:
            aliases = json.loads(row[0]) or []
        except json.JSONDecodeError:
            aliases = []
    if source_player_id not in aliases:
        aliases.append(source_player_id)
        conn.execute(
            "UPDATE player_canonical_ids SET tank01_aliases = ?, updated_at = CURRENT_TIMESTAMP WHERE canonical_id = ?",
            (json.dumps(aliases), canonical_id)
        )
        return True
    return False


def main():
    parser = argparse.ArgumentParser(description="Audit missing canonical IDs")
    parser.add_argument("--db", default=DB_DEFAULT, help="Path to ludi.db")
    parser.add_argument("--log-file", help="Optional path to GitHub Actions log file")
    parser.add_argument("--from-staging", action="store_true", help="Include staging table entries")
    parser.add_argument("--from-unresolvable", action="store_true", help="Include unresolvable IDs from player_game_logs")
    parser.add_argument("--check-espn", action="store_true", help="Check ESPN rosters for missing names")
    parser.add_argument("--update-aliases", action="store_true", help="Update tank01_aliases when canonical match found")
    parser.add_argument("--out", help="Optional output path for JSON report")
    args = parser.parse_args()

    conn = sqlite3.connect(args.db)
    conn.row_factory = sqlite3.Row

    entries = []
    if args.from_staging:
        entries.extend(load_staging(conn))
    if args.log_file:
        entries.extend(parse_log_file(args.log_file))
    if args.from_unresolvable:
        entries.extend(load_unresolvable(conn))

    # Deduplicate
    dedup = {}
    for e in entries:
        key = (e.get("source") or "unknown", e.get("source_player_id"), e.get("player_name"))
        if key not in dedup:
            dedup[key] = e

    missing = list(dedup.values())

    # Build lookup maps
    canonical_rows = conn.execute(
        "SELECT canonical_id, normalized_name, full_name FROM player_canonical_ids"
    ).fetchall()
    canonical_map = {r["normalized_name"]: (r["canonical_id"], r["full_name"]) for r in canonical_rows}

    player_rows = conn.execute(
        "SELECT player_id, name FROM players"
    ).fetchall()
    players_map = {normalize_name(r["name"], strip_suffix=False): (r["player_id"], r["name"]) for r in player_rows}

    espn_map = fetch_espn_roster_map(conn) if args.check_espn else {}

    updated_aliases = 0
    matched_canonical = 0
    matched_players = 0
    matched_espn = 0

    report = []
    for e in missing:
        name = e.get("player_name")
        norm_basic = e.get("normalized_name") or normalize_name(name, strip_suffix=False)
        norm_suffix_stripped = normalize_name(name, strip_suffix=True)

        canonical_match = canonical_map.get(norm_suffix_stripped) or canonical_map.get(norm_basic)
        players_match = players_map.get(norm_basic) or players_map.get(norm_suffix_stripped)
        espn_match = espn_map.get(norm_suffix_stripped) or espn_map.get(norm_basic)

        if canonical_match:
            matched_canonical += 1
            if args.update_aliases and (e.get("source") == "tank01"):
                if update_tank01_alias(conn, canonical_match[0], e.get("source_player_id")):
                    updated_aliases += 1

        if players_match:
            matched_players += 1

        if espn_match:
            matched_espn += 1

        report.append({
            "source": e.get("source"),
            "source_player_id": e.get("source_player_id"),
            "player_name": name,
            "normalized_name": norm_basic,
            "canonical_match": {
                "canonical_id": canonical_match[0],
                "full_name": canonical_match[1],
            } if canonical_match else None,
            "players_match": {
                "player_id": players_match[0],
                "name": players_match[1],
            } if players_match else None,
            "espn_match": espn_match if espn_match else None,
            "seen_count": e.get("seen_count"),
            "first_game_date": e.get("first_game_date"),
            "last_game_date": e.get("last_game_date"),
        })

    if args.update_aliases:
        conn.commit()

    conn.close()

    summary = {
        "missing_total": len(report),
        "matched_canonical": matched_canonical,
        "matched_players": matched_players,
        "matched_espn": matched_espn,
        "aliases_added": updated_aliases,
        "generated_at": datetime.now().isoformat(),
    }

    output = {
        "summary": summary,
        "missing": report,
    }

    print(json.dumps(summary, indent=2))

    if args.out:
        os.makedirs(os.path.dirname(args.out), exist_ok=True)
        with open(args.out, "w") as f:
            json.dump(output, f, indent=2)
        print(f"Wrote report to {args.out}")


if __name__ == "__main__":
    main()
