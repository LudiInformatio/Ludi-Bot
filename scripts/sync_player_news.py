#!/usr/bin/env python3
"""
Sync Tank01 news → player_news_cache table.

Tank01 endpoint: GET /getNBANews?recentNews=true
USAGE RULE: Fetch ONCE per day — do NOT call per-player. Response is already
league-wide; local filtering is free after a single API call.

Actual response structure (confirmed Feb 20, 2026):
  body = [
    {
      "title":     "Williams will be rested Friday against the Cavaliers.",
      "link":      "https://ak-static.cms.nba.com/referee/injury/...",
      "image":     "https://a.espncdn.com/i/headshots/nba/players/full/4066218.png",
      "playerIDs": ["28698616399"]   # Tank01 composite IDs
    },
    ...
  ]

NOTE: No playerName, teamAbv, body/content, or publishedAt in the response.
      Player name resolved via player_canonical_ids if available.

Run: daily, inside data_sync.yml
"""
import sys
import sqlite3
from datetime import date

sys.path.insert(0, '.')
import config
from utils.tank01_client import get_client as get_tank01_client


def sync_player_news() -> int:
    today = date.today().strftime('%Y-%m-%d')
    client = get_tank01_client()

    news_items = client.get_top_news()
    if not news_items:
        print("[sync_player_news] No news returned from Tank01")
        return 0

    conn = sqlite3.connect(config.DB_PATH)
    cursor = conn.cursor()
    count = 0

    for item in news_items:
        if not isinstance(item, dict):
            continue
        try:
            # Actual Tank01 recentNews fields: title, link, image, playerIDs
            headline    = item.get('title', '') or ''
            content     = item.get('link', '') or ''  # link = the source URL
            published_at = today  # recentNews has no publishedAt field
            team_abv    = ''

            # playerIDs = Tank01 composite IDs (e.g. "28698616399")
            # Store raw ID as player_name for now — resolved by module_d at query time
            player_ids  = item.get('playerIDs', [])
            player_name = player_ids[0] if player_ids else ''  # raw Tank01 ID

            if not headline:
                continue  # skip empty records

            # Deduplicate: same headline on same fetch date = same article
            existing = cursor.execute(
                "SELECT id FROM player_news_cache WHERE headline = ? AND fetched_date = ?",
                (headline, today)
            ).fetchone()

            if not existing:
                cursor.execute("""
                    INSERT INTO player_news_cache
                        (player_name, team_abv, headline, content, published_at, fetched_date)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (player_name, team_abv, headline, content, published_at, today))
                count += 1
        except Exception as e:
            print(f"[sync_player_news] Error on item: {e}")

    conn.commit()
    conn.close()
    print(f"[sync_player_news] Inserted {count} new items (checked {len(news_items)} total)")
    return count


if __name__ == "__main__":
    sync_player_news()
