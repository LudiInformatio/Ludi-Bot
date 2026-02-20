#!/usr/bin/env python3
"""
Sync Tank01 team standings + win/loss streaks → team_current_info table.

Tank01 endpoint: getNBATeams (1 call = all 30 teams — credit-efficient)

Note: getNBACurrentInfo only returns season metadata (season/currentDate/seasonType),
not per-team standings. The actual standings/streaks live in getNBATeams.

Actual response structure from getNBATeams:
  [
    {
      "teamAbv": "ORL",
      "wins": "29",
      "loss": "25",
      "currentStreak": {"result": "W", "length": "1"},
      "ppg": "115.4",
      "oppg": "114.9",
      "conferenceAbv": "East",
      ...
    },
    ...
  ]

Run: daily, inside data_sync.yml
"""
import sys
import sqlite3
from datetime import date

sys.path.insert(0, '.')
import config
from utils.tank01_client import get_client as get_tank01_client


def sync_team_current_info() -> int:
    client = get_tank01_client()

    # getNBATeams returns all 30 teams with wins/losses/streak in one call
    teams = client.get_teams()
    if not teams:
        print("[sync_team_current_info] No team data returned from Tank01 — skipping")
        return 0

    conn = sqlite3.connect(config.DB_PATH)
    cursor = conn.cursor()
    count = 0

    for team in teams:
        if not isinstance(team, dict):
            continue
        team_abv = team.get('teamAbv', '')
        if not team_abv:
            continue
        try:
            # Tank01 returns string ints — cast defensively
            wins   = int(team.get('wins', 0) or 0)
            losses = int(team.get('loss', 0) or 0)   # Tank01 uses "loss" (singular)

            # currentStreak = {"result": "W", "length": "3"}
            # "result" = "W" or "L"; "length" = streak count as string
            current_streak = team.get('currentStreak', {})
            win_streak  = 0
            loss_streak = 0
            if isinstance(current_streak, dict):
                streak_type = str(current_streak.get('result', '')).upper()
                streak_len  = int(current_streak.get('length', 0) or 0)
                if streak_type == 'W':
                    win_streak = streak_len
                elif streak_type == 'L':
                    loss_streak = streak_len

            cursor.execute("""
                INSERT INTO team_current_info
                    (team_abv, wins, losses, win_streak, loss_streak, fetched_at)
                VALUES (?, ?, ?, ?, ?, datetime('now'))
                ON CONFLICT(team_abv) DO UPDATE SET
                    wins        = excluded.wins,
                    losses      = excluded.losses,
                    win_streak  = excluded.win_streak,
                    loss_streak = excluded.loss_streak,
                    fetched_at  = excluded.fetched_at
            """, (team_abv, wins, losses, win_streak, loss_streak))
            count += 1
        except Exception as e:
            print(f"[sync_team_current_info] Error for {team_abv}: {e}")

    conn.commit()
    conn.close()
    print(f"[sync_team_current_info] Synced {count} teams")
    return count


if __name__ == "__main__":
    sync_team_current_info()
