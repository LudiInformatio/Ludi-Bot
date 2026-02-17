#!/usr/bin/env python3
"""
Build normalized profile tables for classification and backtesting.

Creates/refreshes:
- player_offensive_playtype_profile
- team_offensive_playtype_profile
- player_defense_proxy_profile
"""

import sqlite3


DB_PATH = "ludi.db"
SEASON = "2025-26"


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.execute("PRAGMA busy_timeout=30000;")
    return conn


def build_player_offensive_profile(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()
    cur.execute("DROP TABLE IF EXISTS player_offensive_playtype_profile")
    cur.execute(
        f"""
        CREATE TABLE player_offensive_playtype_profile AS
        WITH ranked AS (
            SELECT
                player_name,
                team_abbr,
                playtype,
                freq_pct,
                ppp,
                percentile,
                (COALESCE(poss_per_game, 0) * COALESCE(games_played, 0)) AS total_poss,
                ROW_NUMBER() OVER (
                    PARTITION BY player_name
                    ORDER BY COALESCE(freq_pct, 0) DESC
                ) AS rn
            FROM player_synergy_playtypes
            WHERE season = '{SEASON}'
              AND (COALESCE(poss_per_game, 0) * COALESCE(games_played, 0)) >= 75
        )
        SELECT
            p1.player_name,
            p1.team_abbr,
            p1.playtype AS dominant_playtype,
            p1.freq_pct AS dominant_freq_pct,
            p1.ppp AS dominant_ppp,
            p1.percentile AS dominant_percentile,
            p1.total_poss AS dominant_total_poss,
            p2.playtype AS secondary_playtype,
            p2.freq_pct AS secondary_freq_pct,
            p2.ppp AS secondary_ppp,
            p2.percentile AS secondary_percentile
        FROM ranked p1
        LEFT JOIN ranked p2
          ON p1.player_name = p2.player_name
         AND p2.rn = 2
        WHERE p1.rn = 1
        """
    )
    cur.execute("CREATE INDEX IF NOT EXISTS idx_off_profile_player ON player_offensive_playtype_profile(player_name)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_off_profile_team ON player_offensive_playtype_profile(team_abbr)")
    conn.commit()


def build_team_offensive_profile(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()
    cur.execute("DROP TABLE IF EXISTS team_offensive_playtype_profile")
    cur.execute(
        f"""
        CREATE TABLE team_offensive_playtype_profile AS
        WITH weighted AS (
            SELECT
                team_abbr,
                playtype,
                SUM(COALESCE(freq_pct, 0) * (COALESCE(poss_per_game, 0) * COALESCE(games_played, 0))) AS weighted_freq,
                SUM(COALESCE(poss_per_game, 0) * COALESCE(games_played, 0)) AS total_poss
            FROM player_synergy_playtypes
            WHERE season = '{SEASON}'
              AND team_abbr IS NOT NULL
              AND team_abbr != ''
              AND (COALESCE(poss_per_game, 0) * COALESCE(games_played, 0)) >= 75
            GROUP BY team_abbr, playtype
        ),
        scored AS (
            SELECT
                team_abbr,
                playtype,
                CASE WHEN total_poss > 0 THEN weighted_freq / total_poss ELSE 0 END AS team_freq_pct,
                total_poss,
                ROW_NUMBER() OVER (
                    PARTITION BY team_abbr
                    ORDER BY CASE WHEN total_poss > 0 THEN weighted_freq / total_poss ELSE 0 END DESC
                ) AS rn
            FROM weighted
        )
        SELECT
            s1.team_abbr,
            s1.playtype AS dominant_playtype,
            s1.team_freq_pct AS dominant_freq_pct,
            s2.playtype AS secondary_playtype,
            s2.team_freq_pct AS secondary_freq_pct
        FROM scored s1
        LEFT JOIN scored s2
          ON s1.team_abbr = s2.team_abbr
         AND s2.rn = 2
        WHERE s1.rn = 1
        """
    )
    cur.execute("CREATE INDEX IF NOT EXISTS idx_team_off_profile_team ON team_offensive_playtype_profile(team_abbr)")
    conn.commit()


def build_player_defense_proxy_profile(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()
    cur.execute("DROP TABLE IF EXISTS player_defense_proxy_profile")
    cur.execute(
        f"""
        CREATE TABLE player_defense_proxy_profile AS
        SELECT
            d.player_name,
            d.team_abbr,
            d.position,
            AVG(COALESCE(d.diff_pct, 0)) AS def_diff_pct,
            AVG(COALESCE(d.freq_pct, 0)) AS def_freq_pct,
            AVG(COALESCE(d.dfga, 0)) AS def_dfga,
            AVG(COALESCE(d.dfg_pct, 0)) AS def_dfg_pct,
            AVG(COALESCE(s.dist_miles_def, 0)) AS def_distance_miles,
            AVG(COALESCE(s.avg_speed_def, 0)) AS def_speed,
            AVG(COALESCE(h.box_outs, 0)) AS hustle_box_outs,
            AVG(COALESCE(h.contested_shots, 0)) AS hustle_contested_shots
        FROM player_defense d
        LEFT JOIN player_speed s
          ON s.player_name = d.player_name
         AND s.season = d.season
        LEFT JOIN player_game_hustle h
          ON h.player_name = d.player_name
         AND h.game_date >= date('now', '-30 days')
        WHERE d.season = '{SEASON}'
        GROUP BY d.player_name, d.team_abbr, d.position
        """
    )
    cur.execute("CREATE INDEX IF NOT EXISTS idx_def_proxy_player ON player_defense_proxy_profile(player_name)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_def_proxy_team ON player_defense_proxy_profile(team_abbr)")
    conn.commit()


def main():
    conn = _connect()
    build_player_offensive_profile(conn)
    build_team_offensive_profile(conn)
    build_player_defense_proxy_profile(conn)
    conn.close()
    print("Built classification profile tables.")


if __name__ == "__main__":
    main()
