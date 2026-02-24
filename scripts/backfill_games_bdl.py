#!/usr/bin/env python3
"""
One-time backfill: populate games table for Feb 19-20, 2026 using BDL API.
Odds API is on 401 (quota exhausted) so we use Ball Don't Lie as the source.
"""

import os
import sys
import sqlite3
import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.mappings import normalize_bdl_abbr

# ---------- ENV LOADING (Python 3.14 safe) ----------
env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '.env')
if os.path.exists(env_path):
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, _, val = line.partition('=')
                os.environ.setdefault(key.strip(), val.strip())

BDL_KEY = os.environ.get('BALLDONTLIE_KEY', '')
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'ludi.db')

DATES = ['2026-02-19', '2026-02-20']


def normalize_abbrev(abbrev: str) -> str:
    return normalize_bdl_abbr(abbrev)


def fetch_games_from_bdl(dates: list) -> list:
    url = 'https://api.balldontlie.io/v1/games'
    headers = {'Authorization': BDL_KEY}
    params = {f'dates[]': d for d in dates}  # requests handles duplicate keys via list
    # requests needs list of tuples for repeated keys
    param_list = [('dates[]', d) for d in dates] + [('per_page', 100)]

    print(f"📡 Fetching BDL games for {', '.join(dates)}...")
    resp = requests.get(url, headers=headers, params=param_list, timeout=15)

    if resp.status_code != 200:
        print(f"❌ BDL returned {resp.status_code}: {resp.text[:300]}")
        sys.exit(1)

    data = resp.json().get('data', [])
    print(f"   → {len(data)} games returned from BDL")
    return data


def build_game_rows(bdl_games: list) -> list:
    rows = []
    for g in bdl_games:
        home_abbrev = normalize_abbrev(g['home_team']['abbreviation'])
        away_abbrev = normalize_abbrev(g['visitor_team']['abbreviation'])

        # Parse date from BDL (format: "2026-02-19")
        game_date = g['date'][:10]  # trim time component if present

        game_id = f"{game_date.replace('-', '')}_{away_abbrev}@{home_abbrev}"

        home_score = g.get('home_team_score') or None
        away_score = g.get('visitor_team_score') or None

        # BDL game id stored in nba_game_id for reference
        bdl_id = str(g.get('id', ''))

        rows.append((game_id, game_date, home_abbrev, away_abbrev,
                     home_score, away_score, bdl_id))

    return rows


def upsert_games(rows: list):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    inserted = 0
    for row in rows:
        game_id, game_date, home, away, h_score, a_score, bdl_id = row
        try:
            cur.execute("""
                INSERT INTO games (game_id, date, home_team, away_team,
                                   home_score, away_score, nba_game_id)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(game_id) DO UPDATE SET
                    date          = excluded.date,
                    home_team     = excluded.home_team,
                    away_team     = excluded.away_team,
                    home_score    = excluded.home_score,
                    away_score    = excluded.away_score,
                    nba_game_id   = excluded.nba_game_id
            """, (game_id, game_date, home, away, h_score, a_score, bdl_id))
            score_str = f"{a_score}-{h_score}" if h_score is not None else "TBD"
            print(f"   ✅ {away} @ {home} ({game_date}) | {score_str} | {game_id}")
            inserted += 1
        except Exception as e:
            print(f"   ❌ DB error for {game_id}: {e}")

    conn.commit()
    conn.close()
    print(f"\n💾 {inserted}/{len(rows)} rows upserted into games table.")


def verify():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        SELECT date, away_team, home_team, away_score, home_score
        FROM games
        WHERE date >= '2026-02-19'
        ORDER BY date, home_team
    """)
    rows = cur.fetchall()
    conn.close()

    print("\n" + "="*60)
    print("VERIFICATION — games table (Feb 19+)")
    print("="*60)
    for r in rows:
        date, away, home, a_s, h_s = r
        score = f"{a_s}-{h_s}" if a_s is not None else "TBD"
        print(f"  {date}  {away:3s} @ {home:3s}  {score}")
    print(f"\nTotal rows: {len(rows)}")


if __name__ == '__main__':
    if not BDL_KEY:
        print("❌ BALLDONTLIE_KEY not found in .env")
        sys.exit(1)

    bdl_games = fetch_games_from_bdl(DATES)
    rows = build_game_rows(bdl_games)
    upsert_games(rows)
    verify()
