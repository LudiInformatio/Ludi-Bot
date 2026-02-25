#!/usr/bin/env python3
"""
Build normalized profile tables for classification and backtesting.

Creates/refreshes:
- player_offensive_playtype_profile
- team_offensive_playtype_profile
- player_defense_proxy_profile
- player_type_profiles  ← unified per-player type layer (Feb 25, 2026)
"""

import sqlite3


DB_PATH = "ludi.db"
SEASON = "2025-26"

# NBA Synergy raw names → our internal module_e tag names
SYNERGY_TO_TAG = {
    'ISO': 'ISO_SCORER',
    'TRANSITION': 'TRANSITION',
    'PR_BALL_HANDLER': 'P&R_HANDLER',
    'PR_ROLL_MAN': 'P&R_ROLL_MAN',
    'POST_UP': 'POST_UP',
    'SPOT_UP': 'SPOT_UP',
    'CUT': 'OFF_BALL_CUTTER',
    'PUTBACK': 'PUTBACK',
    'HANDOFF': 'HANDOFF',
    'OFF_SCREEN': 'OFF_SCREEN',
    'OFFSCREEN': 'OFF_SCREEN',
}

# Position → which internal synergy tags are "natural" for that position.
# A mismatch (e.g., C with P&R_HANDLER as #1) gets flagged for transparency
# but does NOT suppress the player — Jokić IS a legitimate P&R orchestrator.
POSITION_ELIGIBLE = {
    'G':   {'ISO_SCORER', 'P&R_HANDLER', 'SPOT_UP', 'TRANSITION', 'HANDOFF', 'OFF_SCREEN'},
    'G-F': {'ISO_SCORER', 'P&R_HANDLER', 'SPOT_UP', 'OFF_BALL_CUTTER', 'TRANSITION', 'HANDOFF', 'OFF_SCREEN'},
    'F':   {'ISO_SCORER', 'P&R_HANDLER', 'P&R_ROLL_MAN', 'SPOT_UP', 'OFF_BALL_CUTTER', 'TRANSITION', 'HANDOFF', 'OFF_SCREEN'},
    'F-C': {'P&R_ROLL_MAN', 'SPOT_UP', 'OFF_BALL_CUTTER', 'TRANSITION', 'PUTBACK', 'POST_UP', 'OFF_SCREEN'},
    'C':   {'P&R_ROLL_MAN', 'OFF_BALL_CUTTER', 'PUTBACK', 'POST_UP', 'SPOT_UP', 'TRANSITION'},
}

# Archetype → its expected primary synergy tag (from module_e archetype_synergy_map)
# Used to check whether a player's synergy data aligns with their archetype label.
ARCHETYPE_PRIMARY_TAG = {
    'HELIOCENTRIC_MAESTRO': 'P&R_HANDLER',
    'SLASHING_CREATOR':     'TRANSITION',
    'ISO_ASSASSIN':         'ISO_SCORER',
    'JUMBO_FACILITATOR':    'P&R_HANDLER',
    'SNIPER_ELITE':         'SPOT_UP',
    'TWO_LEVEL_SCORER':     'ISO_SCORER',
    'WARRIOR_BIG':          'P&R_ROLL_MAN',
    'STRETCH_BIG':          'SPOT_UP',
    'ROLL_MAN':             'P&R_ROLL_MAN',
    'HUB_BIG':              'P&R_HANDLER',
    'CUTTER_SPECIALIST':    'OFF_BALL_CUTTER',
    'ENERGY_BIG':           'P&R_ROLL_MAN',
    'CONNECTOR':            'P&R_HANDLER',
    'FACILITATOR':          'P&R_HANDLER',
    'GENERALIST':           None,  # No strong synergy signal — use top Synergy type directly
}


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


def build_player_type_profiles(conn: sqlite3.Connection) -> None:
    """
    Build player_type_profiles — unified per-player type layer.

    For each active player, stores:
      - archetype (our 15-type system) + defensive_tag
      - Top 3 NBA Synergy playtypes by frequency (raw names + translated tags)
      - Position-synergy match flag (transparent mismatch detection)
      - Archetype-synergy alignment check

    Design philosophy:
      - Use our archetype when it fits (HUB_BIG for Jokić)
      - NBA Synergy types are the descriptors (POST_UP, PR_BALL_HANDLER, ISO)
      - If archetype is GENERALIST or doesn't fit, the Synergy #1 type IS the label
      - Mismatches (e.g. C with PR_BALL_HANDLER #1) are flagged, not suppressed
    """
    cur = conn.cursor()

    # Fetch all active players. LEFT JOIN to player_canonical_ids so the name used
    # for synergy lookups is the canonical full_name (accent-correct: Jokić, Nurkić).
    # Falls back to players.name when no canonical entry exists.
    cur.execute(
        """
        SELECT
            COALESCE(pc.full_name, p.name)  AS canonical_name,
            p.name                           AS raw_name,
            COALESCE(pc.team, p.team)        AS team,
            -- Prefer players.position when real; canonical_ids.position as fallback.
            -- players table has G/F/C/SG/SF/PF data for 75%+ of roster.
            -- canonical_ids.position is mostly UNK (only ~50 entries populated).
            -- Filter out team abbr data corruption in players.position (e.g. 'ATL', 'LAC').
            CASE
                WHEN p.position NOT IN ('UNK','IND','') AND LENGTH(p.position) <= 3
                  AND p.position NOT GLOB '[A-Z][A-Z][A-Z]'  -- exclude 3-letter team abbrs
                THEN p.position
                WHEN pc.position IS NOT NULL AND pc.position != 'UNK'
                THEN pc.position
                ELSE 'UNK'
            END AS position,
            p.archetype,
            p.defensive_tag
        FROM players p
        LEFT JOIN player_canonical_ids pc
          ON LOWER(REPLACE(REPLACE(p.name, '.', ''), "'", '')) =
             LOWER(REPLACE(REPLACE(pc.normalized_name, '.', ''), "'", ''))
        WHERE UPPER(p.status) = 'ACTIVE'
          AND p.name IS NOT NULL
        """
    )
    players = cur.fetchall()

    # Fetch all synergy data for this season (top 3 per player, min 75 poss).
    # player_synergy_playtypes.player_name uses canonical names from NBA Synergy.
    cur.execute(
        f"""
        SELECT player_name, playtype, freq_pct, ppp,
               ROW_NUMBER() OVER (
                   PARTITION BY player_name
                   ORDER BY COALESCE(freq_pct, 0) DESC
               ) AS rn
        FROM player_synergy_playtypes
        WHERE season = '{SEASON}'
          AND (COALESCE(poss_per_game, 0) * COALESCE(games_played, 0)) >= 75
        """
    )
    # Build synergy lookup: {player_name: [(playtype, freq, ppp), ...]} top 3
    synergy_by_player: dict = {}
    for row in cur.fetchall():
        pname, ptype, freq, ppp_val, rn = row
        if rn <= 3:
            synergy_by_player.setdefault(pname, []).append((ptype, freq or 0.0, ppp_val or 0.0))

    rows_upserted = 0
    for canonical_name, raw_name, team, position, archetype, defensive_tag in players:
        # Use canonical name for lookups; fall back to raw name for synergy match
        player_name = canonical_name
        # Normalize position to our 5-bucket system for eligibility check
        pos_bucket = 'G'
        if position in ('C',):
            pos_bucket = 'C'
        elif position in ('PF', 'F-C'):
            pos_bucket = 'F-C'
        elif position in ('SF', 'PF', 'F'):
            pos_bucket = 'F'
        elif position in ('SG', 'PG', 'G'):
            pos_bucket = 'G'
        elif position in ('G-F', 'SF'):
            pos_bucket = 'G-F'

        eligible_tags = POSITION_ELIGIBLE.get(pos_bucket, set())

        # Pull top 3 synergy types — try canonical name first, then raw name
        syn = synergy_by_player.get(player_name) or synergy_by_player.get(raw_name, [])
        syn_types = [s[0] for s in syn]       # raw NBA names
        syn_freqs = [s[1] for s in syn]
        syn_ppps  = [s[2] for s in syn]

        def _get(lst, i, default=None):
            return lst[i] if i < len(lst) else default

        st1, sf1, sp1 = _get(syn_types, 0), _get(syn_freqs, 0, 0.0), _get(syn_ppps, 0, 0.0)
        st2, sf2, sp2 = _get(syn_types, 1), _get(syn_freqs, 1, 0.0), _get(syn_ppps, 1, 0.0)
        st3, sf3, sp3 = _get(syn_types, 2), _get(syn_freqs, 2, 0.0), _get(syn_ppps, 2, 0.0)

        # Translate to internal tags
        tag1 = SYNERGY_TO_TAG.get(st1) if st1 else None
        tag2 = SYNERGY_TO_TAG.get(st2) if st2 else None
        tag3 = SYNERGY_TO_TAG.get(st3) if st3 else None

        # Position-synergy match: primary synergy tag position-appropriate?
        pos_match = 1
        if tag1 and tag1 not in eligible_tags:
            pos_match = 0  # e.g. Jokić (C) with P&R_HANDLER as #1 → 0

        # Archetype alignment: does archetype's expected tag appear in top 3?
        arch_primary_tag = ARCHETYPE_PRIMARY_TAG.get(archetype)
        top3_tags = {t for t in [tag1, tag2, tag3] if t}
        arch_in_top3 = 1 if arch_primary_tag and arch_primary_tag in top3_tags else 0

        cur.execute(
            """
            INSERT INTO player_type_profiles
                (player_name, team, position, archetype, defensive_tag,
                 synergy_type_1, synergy_freq_1, synergy_ppp_1,
                 synergy_type_2, synergy_freq_2, synergy_ppp_2,
                 synergy_type_3, synergy_freq_3, synergy_ppp_3,
                 synergy_tag_1, synergy_tag_2, synergy_tag_3,
                 position_synergy_match, archetype_primary_tag, archetype_in_top3,
                 season, updated_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?, datetime('now'))
            ON CONFLICT(player_name, season) DO UPDATE SET
                team=excluded.team,
                position=excluded.position,
                archetype=excluded.archetype,
                defensive_tag=excluded.defensive_tag,
                synergy_type_1=excluded.synergy_type_1, synergy_freq_1=excluded.synergy_freq_1, synergy_ppp_1=excluded.synergy_ppp_1,
                synergy_type_2=excluded.synergy_type_2, synergy_freq_2=excluded.synergy_freq_2, synergy_ppp_2=excluded.synergy_ppp_2,
                synergy_type_3=excluded.synergy_type_3, synergy_freq_3=excluded.synergy_freq_3, synergy_ppp_3=excluded.synergy_ppp_3,
                synergy_tag_1=excluded.synergy_tag_1, synergy_tag_2=excluded.synergy_tag_2, synergy_tag_3=excluded.synergy_tag_3,
                position_synergy_match=excluded.position_synergy_match,
                archetype_primary_tag=excluded.archetype_primary_tag,
                archetype_in_top3=excluded.archetype_in_top3,
                updated_at=datetime('now')
            """,
            (player_name, team, position, archetype, defensive_tag,
             st1, sf1, sp1, st2, sf2, sp2, st3, sf3, sp3,
             tag1, tag2, tag3,
             pos_match, arch_primary_tag, arch_in_top3,
             SEASON)
        )
        rows_upserted += 1

    conn.commit()
    print(f"  player_type_profiles: {rows_upserted} players upserted")

    # Quick diagnostic — flag notable mismatches
    cur.execute(
        """
        SELECT player_name, team, position, archetype, synergy_tag_1,
               position_synergy_match, archetype_in_top3
        FROM player_type_profiles
        WHERE (position_synergy_match = 0 OR archetype_in_top3 = 0)
          AND archetype NOT IN ('GENERALIST', 'ENERGY_BIG')
          AND synergy_tag_1 IS NOT NULL
          AND season = ?
        ORDER BY player_name
        LIMIT 20
        """,
        (SEASON,)
    )
    mismatches = cur.fetchall()
    if mismatches:
        print(f"\n  [Type Profile] {len(mismatches)} notable archetype/position mismatches:")
        print(f"  {'Player':<25} {'Pos':<5} {'Archetype':<22} {'Syn#1':<16} {'PosFit':<7} {'ArchFit'}")
        for row in mismatches:
            pname, tm, pos, arch, stag1, pos_m, arch_m = row
            print(f"  {pname:<25} {(pos or '?'):<5} {(arch or 'None'):<22} {(stag1 or 'None'):<16} {'✓' if pos_m else '✗':<7} {'✓' if arch_m else '✗'}")


def main():
    conn = _connect()
    build_player_offensive_profile(conn)
    build_team_offensive_profile(conn)
    build_player_defense_proxy_profile(conn)
    build_player_type_profiles(conn)
    conn.close()
    print("\nBuilt all classification profile tables.")


if __name__ == "__main__":
    main()
