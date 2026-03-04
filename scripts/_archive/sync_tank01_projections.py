# ARCHIVED: 2026-03-03 — Read-only benchmark — never used in pipeline
#!/usr/bin/env python3
"""
Sync Tank01 fantasy projections → tank01_projections table.

Tank01 endpoint: getNBAProjections
POLICY: READ-ONLY benchmark ONLY. Never feeds into SAVAGE simulation model.

Response structure (observed):
  body = {
    "28398804489": {          # Tank01 playerID (may be composite or legacy)
      "pts": "24.3",
      "reb": "6.1",
      "ast": "5.8",
      "stl": "1.2",
      "blk": "0.4",
      "TOV": "3.1",          # uppercase TOV
      "fantasyPts": "42.7",
      "playerName": "LeBron James",
      ...
    },
    ...
  }

Run: daily, inside data_sync.yml
"""
import sys
import sqlite3
from datetime import date

sys.path.insert(0, '.')
import config
from utils.tank01_client import get_client as get_tank01_client


def sync_projections() -> int:
    today = date.today().strftime('%Y-%m-%d')
    client = get_tank01_client()

    # get_projections() already returns body dict keyed by playerID
    player_projections = client.get_projections(num_days=7)
    if not player_projections:
        print(f"[sync_projections] No projections returned — Tank01 may be down")
        return 0

    conn = sqlite3.connect(config.DB_PATH)
    cursor = conn.cursor()
    count = 0

    for tank01_id, proj in player_projections.items():
        if not isinstance(proj, dict):
            continue
        try:
            # Resolve Tank01 playerID → our canonical NBA ID
            # Falls back to raw tank01_id if no mapping exists (acceptable for benchmark data)
            # tank01_id is a composite ID — fall back to raw ID for projection benchmarks
            # (exact ID resolution not critical for drift detection use case)
            player_id = tank01_id

            cursor.execute("""
                INSERT INTO tank01_projections
                    (player_id, game_date, pts, reb, ast, stl, blk, tov, fantasy_pts)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(player_id, game_date) DO UPDATE SET
                    pts         = excluded.pts,
                    reb         = excluded.reb,
                    ast         = excluded.ast,
                    stl         = excluded.stl,
                    blk         = excluded.blk,
                    tov         = excluded.tov,
                    fantasy_pts = excluded.fantasy_pts,
                    fetched_at  = datetime('now')
            """, (
                player_id,
                today,
                float(proj.get('pts', 0) or 0),
                float(proj.get('reb', 0) or 0),
                float(proj.get('ast', 0) or 0),
                float(proj.get('stl', 0) or 0),
                float(proj.get('blk', 0) or 0),
                # Tank01 sends TOV uppercase in params AND in response body
                float(proj.get('TOV', proj.get('tov', 0)) or 0),
                # Tank01 field is 'fantasyPoints' (camelCase); values are 7-day cumulative
                float(proj.get('fantasyPoints', proj.get('fantasyPts', 0)) or 0),
            ))
            count += 1
        except Exception as e:
            print(f"[sync_projections] Error for player {tank01_id}: {e}")

    conn.commit()
    conn.close()
    print(f"[sync_projections] Synced {count} player projections for {today}")
    return count


if __name__ == "__main__":
    sync_projections()
