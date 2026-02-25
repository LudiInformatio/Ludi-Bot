#!/usr/bin/env python3
"""
Matchup Intelligence Tables Builder — Phase 8 Sprint 2

Builds three pre-computed lookup tables from historical bet + tracking data:

  1. player_archetype_vs_defense  — per (archetype, defense_type): historical WR,
     avg stat deltas vs season baseline, and bet performance. Single-row lookup
     replaces multi-sentence Claude reasoning about matchup tendencies.

  2. team_playtype_allowed  — per team: how much paint/C&S/pull-up/drive volume
     they allow, ranked 1-30. Powers "this team allows the 3rd-most paint pts"
     context in game notes at zero Claude token cost.

  3. player_archetype_roster  — per player: archetype + season stats + vs-each-
     defense performance. Groups players by team → archetype for game notes that
     say "3 SNIPER_ELITE players on BOS all averaging +12% vs PAINT_PACK D."

Run weekly via weekly_validation.yml (after classify_archetypes + scheme cache update).

Usage:
    python scripts/sync_matchup_intelligence.py
    python scripts/sync_matchup_intelligence.py --window-days 60
    python scripts/sync_matchup_intelligence.py --verbose
"""

import argparse
import sqlite3
import os
import sys
import math
from datetime import datetime, timedelta
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.mappings import normalize_bdl_abbr

DB_PATH = "ludi.db"
SEASON = "2025-26"
DEFAULT_WINDOW_DAYS = 60   # How far back to look for bet outcomes

# Archetypes we care about (canonical 15 + GENERALIST)
VALID_ARCHETYPES = {
    'GENERALIST', 'SNIPER_ELITE', 'CONNECTOR', 'ENERGY_BIG', 'CUTTER_SPECIALIST',
    'STRETCH_BIG', 'HELIOCENTRIC_MAESTRO', 'ROLL_MAN', 'TWO_LEVEL_SCORER', 'WARRIOR_BIG',
    'SLASHING_CREATOR', 'JUMBO_FACILITATOR', 'ISO_ASSASSIN', 'FACILITATOR', 'HUB_BIG',
}
VALID_DEF_STYLES = {'PAINT_PACK', 'PERIMETER', 'FUNNEL', 'BLITZ', 'NEUTRAL'}


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.execute("PRAGMA busy_timeout=30000;")
    conn.row_factory = sqlite3.Row
    return conn


# ── Table 1: player_archetype_vs_defense ─────────────────────────────────────

def build_player_archetype_vs_defense(conn: sqlite3.Connection, window_days: int = 60, verbose: bool = False) -> None:
    """
    For each (archetype, defense_type) pair, compute:
    - Historical bet win rate and net units
    - Avg points/reb/ast for games played in that matchup
    - Delta vs that archetype's season baseline

    Refresh: weekly. Source: bet_recommendations + player_game_logs + team_scheme_cache.
    """
    cur = conn.cursor()

    # Ensure table exists
    cur.execute("""
        CREATE TABLE IF NOT EXISTS player_archetype_vs_defense (
            archetype       TEXT NOT NULL,
            defense_type    TEXT NOT NULL,
            season          TEXT NOT NULL DEFAULT '2025-26',
            -- Bet performance
            bets            INTEGER DEFAULT 0,
            wins            INTEGER DEFAULT 0,
            losses          INTEGER DEFAULT 0,
            win_rate        REAL DEFAULT 0.0,
            avg_edge        REAL DEFAULT 0.0,
            net_units       REAL DEFAULT 0.0,
            -- Game stats in this matchup (from player_game_logs)
            games           INTEGER DEFAULT 0,
            avg_pts         REAL DEFAULT 0.0,
            avg_reb         REAL DEFAULT 0.0,
            avg_ast         REAL DEFAULT 0.0,
            avg_blk         REAL DEFAULT 0.0,
            avg_stl         REAL DEFAULT 0.0,
            avg_3pm         REAL DEFAULT 0.0,
            -- Delta vs season baseline for this archetype
            pts_vs_baseline REAL DEFAULT 0.0,
            reb_vs_baseline REAL DEFAULT 0.0,
            ast_vs_baseline REAL DEFAULT 0.0,
            updated_at      TEXT DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (archetype, defense_type, season)
        )
    """)

    window_start = (datetime.now() - timedelta(days=window_days)).strftime('%Y-%m-%d')

    # Step 1: Bet performance per (archetype, opponent_def_style)
    cur.execute("""
        SELECT b.archetype, t.active_style as def_style,
            COUNT(*) as bets,
            SUM(CASE WHEN b.outcome='WIN' THEN 1 ELSE 0 END) as wins,
            SUM(CASE WHEN b.outcome='LOSS' THEN 1 ELSE 0 END) as losses,
            ROUND(AVG(b.true_edge), 2) as avg_edge,
            ROUND(SUM(CASE WHEN b.outcome='WIN' THEN b.units WHEN b.outcome='LOSS' THEN -b.units ELSE 0 END), 2) as net_u
        FROM bet_recommendations b
        JOIN team_scheme_cache t ON b.opponent = t.team_abbr AND t.scheme_type = 'DEFENSE'
        WHERE b.game_date >= ?
          AND b.outcome IN ('WIN','LOSS','PUSH','VOID')
          AND b.archetype IN ({})
          AND t.active_style IN ({})
        GROUP BY b.archetype, t.active_style
        HAVING COUNT(*) >= 10
    """.format(
        ','.join(['?' for _ in VALID_ARCHETYPES]),
        ','.join(['?' for _ in VALID_DEF_STYLES])
    ), [window_start] + list(VALID_ARCHETYPES) + list(VALID_DEF_STYLES))
    bet_perf = {(r['archetype'], r['def_style']): dict(r) for r in cur.fetchall()}

    # opponent_expr: parse opponent team from matchup column.
    # player_game_logs has no opponent column — matchup format: "TEAM @ OPP" or "TEAM vs. OPP"
    # In both cases, the opponent is the text AFTER "@ " or "vs. "
    _opp_expr = """TRIM(CASE
        WHEN gl.matchup LIKE '% @ %' THEN SUBSTR(gl.matchup, INSTR(gl.matchup, ' @ ') + 3)
        WHEN gl.matchup LIKE '% vs. %' THEN SUBSTR(gl.matchup, INSTR(gl.matchup, ' vs. ') + 5)
        ELSE NULL END)"""

    # Step 2: Season baseline stats per archetype (avg across all games in window)
    cur.execute("""
        SELECT p.archetype,
            ROUND(AVG(gl.pts), 2) as avg_pts,
            ROUND(AVG(gl.reb), 2) as avg_reb,
            ROUND(AVG(gl.ast), 2) as avg_ast
        FROM players p
        JOIN player_game_logs gl ON gl.player_name = p.name
        WHERE gl.game_date >= ?
          AND p.archetype IN ({})
          AND gl.minutes >= 10
        GROUP BY p.archetype
    """.format(','.join(['?' for _ in VALID_ARCHETYPES])),
    [window_start] + list(VALID_ARCHETYPES))
    baselines = {r['archetype']: dict(r) for r in cur.fetchall()}

    # Step 3: Avg game stats by archetype vs each defense type.
    # Use games table to resolve opponent cleanly (no matchup string parsing).
    # games.home_team/away_team + player's team_abbreviation → opponent team.
    _arch_ph = ','.join(['?' for _ in VALID_ARCHETYPES])
    _def_ph  = ','.join(['?' for _ in VALID_DEF_STYLES])
    cur.execute(f"""
        SELECT p.archetype, sc.active_style as def_style,
            COUNT(*) as games,
            ROUND(AVG(gl.pts), 2) as avg_pts,
            ROUND(AVG(gl.reb), 2) as avg_reb,
            ROUND(AVG(gl.ast), 2) as avg_ast,
            ROUND(AVG(gl.blk), 3) as avg_blk,
            ROUND(AVG(gl.stl), 3) as avg_stl,
            ROUND(AVG(COALESCE(gl.fg3m, 0)), 2) as avg_3pm
        FROM players p
        JOIN player_game_logs gl ON gl.player_name = p.name
        JOIN games g ON g.date = gl.game_date
          AND (g.home_team = gl.team_abbreviation OR g.away_team = gl.team_abbreviation)
        JOIN team_scheme_cache sc
          ON CASE WHEN g.home_team = gl.team_abbreviation THEN g.away_team
                  ELSE g.home_team END = sc.team_abbr
          AND sc.scheme_type = 'DEFENSE'
        WHERE gl.game_date >= ?
          AND p.archetype IN ({_arch_ph})
          AND sc.active_style IN ({_def_ph})
          AND gl.minutes >= 10
        GROUP BY p.archetype, sc.active_style
        HAVING COUNT(*) >= 5
    """, [window_start] + list(VALID_ARCHETYPES) + list(VALID_DEF_STYLES))
    game_stats = {(r['archetype'], r['def_style']): dict(r) for r in cur.fetchall()}

    # Step 4: Upsert all (archetype, def_style) combinations
    rows_written = 0
    for archetype in VALID_ARCHETYPES:
        baseline = baselines.get(archetype, {})
        for def_style in VALID_DEF_STYLES:
            bp = bet_perf.get((archetype, def_style), {})
            gs = game_stats.get((archetype, def_style), {})
            if not bp and not gs:
                continue  # No data for this pair — skip

            bets = bp.get('bets', 0)
            wins = bp.get('wins', 0)
            losses = bp.get('losses', 0)
            wr = round(wins / (wins + losses), 4) if (wins + losses) > 0 else 0.0

            gs_pts = gs.get('avg_pts', 0) or 0.0
            gs_reb = gs.get('avg_reb', 0) or 0.0
            gs_ast = gs.get('avg_ast', 0) or 0.0

            bl_pts = baseline.get('avg_pts', 0) or 0.0
            bl_reb = baseline.get('avg_reb', 0) or 0.0
            bl_ast = baseline.get('avg_ast', 0) or 0.0

            cur.execute("""
                INSERT INTO player_archetype_vs_defense
                    (archetype, defense_type, season, bets, wins, losses, win_rate,
                     avg_edge, net_units, games, avg_pts, avg_reb, avg_ast, avg_blk,
                     avg_stl, avg_3pm, pts_vs_baseline, reb_vs_baseline, ast_vs_baseline, updated_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?, datetime('now'))
                ON CONFLICT(archetype, defense_type, season) DO UPDATE SET
                    bets=excluded.bets, wins=excluded.wins, losses=excluded.losses,
                    win_rate=excluded.win_rate, avg_edge=excluded.avg_edge,
                    net_units=excluded.net_units, games=excluded.games,
                    avg_pts=excluded.avg_pts, avg_reb=excluded.avg_reb,
                    avg_ast=excluded.avg_ast, avg_blk=excluded.avg_blk,
                    avg_stl=excluded.avg_stl, avg_3pm=excluded.avg_3pm,
                    pts_vs_baseline=excluded.pts_vs_baseline,
                    reb_vs_baseline=excluded.reb_vs_baseline,
                    ast_vs_baseline=excluded.ast_vs_baseline,
                    updated_at=datetime('now')
            """, (archetype, def_style, SEASON, bets, wins, losses, wr,
                  bp.get('avg_edge', 0) or 0,
                  bp.get('net_u', 0) or 0,
                  gs.get('games', 0) or 0,
                  gs_pts, gs_reb, gs_ast,
                  gs.get('avg_blk', 0) or 0,
                  gs.get('avg_stl', 0) or 0,
                  gs.get('avg_3pm', 0) or 0,
                  round(gs_pts - bl_pts, 2) if bl_pts else 0.0,
                  round(gs_reb - bl_reb, 2) if bl_reb else 0.0,
                  round(gs_ast - bl_ast, 2) if bl_ast else 0.0,
            ))
            rows_written += 1

    conn.commit()
    print(f"  player_archetype_vs_defense: {rows_written} rows upserted")

    if verbose:
        cur.execute("""
            SELECT archetype, defense_type, bets, ROUND(win_rate*100,1) as wr_pct, net_units,
                   games, avg_pts, pts_vs_baseline
            FROM player_archetype_vs_defense
            WHERE season=? AND bets >= 30
            ORDER BY win_rate DESC LIMIT 15
        """, (SEASON,))
        rows = cur.fetchall()
        if rows:
            print(f"\n  Top matchups (≥30 bets):")
            print(f"  {'Archetype':<22} {'vs':<12} {'Bets':>5} {'WR%':>6} {'Net U':>7} {'G':>4} {'AvgPTS':>7} {'Δ':>6}")
            for r in rows:
                print(f"  {r['archetype']:<22} {r['defense_type']:<12} {r['bets']:>5} "
                      f"{r['wr_pct']:>6} {r['net_units']:>7.1f} {r['games']:>4} "
                      f"{r['avg_pts']:>7.1f} {r['pts_vs_baseline']:>+6.1f}")


# ── Table 2: team_playtype_allowed ─────────────────────────────────────────────

def build_team_playtype_allowed(conn: sqlite3.Connection, window_days: int = 60, verbose: bool = False) -> None:
    """
    For each team: how many paint pts, C&S 3PA, pull-up FGA, and drives do they
    allow per game? Rank all 30 teams 1=best defense, 30=worst for each category.

    Source: player_game_tracking (tracking stats for players vs each opponent team),
    player_game_logs (paint/non-paint points proxy from shot charts).
    """
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS team_playtype_allowed (
            team_abbr           TEXT NOT NULL,
            -- Tracking-based: from player_game_tracking WHERE player's team != defending team
            cs_3pa_allowed_pg   REAL DEFAULT 0.0,   -- Catch & shoot 3PA per game
            cs_3pm_allowed_pg   REAL DEFAULT 0.0,   -- C&S 3PM per game
            drives_fga_allowed_pg REAL DEFAULT 0.0, -- Drive FGA per game allowed
            pullup_fga_allowed_pg REAL DEFAULT 0.0, -- Pull-up FGA per game allowed
            avg_off_speed_pg    REAL DEFAULT 0.0,   -- Avg offensive player speed vs this D
            avg_def_dist_pg     REAL DEFAULT 0.0,   -- Avg defender distance (how tight they play)
            -- Rankings (1=best defense for that category, 30=worst)
            cs_3pa_rank         INTEGER DEFAULT 15,
            drives_rank         INTEGER DEFAULT 15,
            pullup_rank         INTEGER DEFAULT 15,
            -- Defensive quality from team_scheme_cache
            def_style           TEXT,
            def_quality         TEXT,
            games_sample        INTEGER DEFAULT 0,
            season              TEXT NOT NULL DEFAULT '2025-26',
            updated_at          TEXT DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (team_abbr, season)
        )
    """)

    window_start = (datetime.now() - timedelta(days=window_days)).strftime('%Y-%m-%d')

    # Query tracking stats per DEFENDING team.
    # Use games table join on tracking.team_abbr for clean opponent resolution —
    # avoids brittle matchup string parsing in player_game_logs.
    # canonical_id route: tracking.nba_player_id → player_canonical_ids.nba_api_id (future)
    cur.execute("""
        SELECT
            CASE WHEN g.home_team = t.team_abbr THEN g.away_team
                 ELSE g.home_team END as defending_team,
            COUNT(DISTINCT t.game_date) as games,
            ROUND(AVG(t.catch_shoot_3pa), 3) as cs_3pa,
            ROUND(AVG(t.catch_shoot_3pm), 3) as cs_3pm,
            ROUND(AVG(t.drives_fga), 3) as drives_fga,
            ROUND(AVG(t.pull_up_fga), 3) as pullup_fga,
            ROUND(AVG(t.avg_speed_off), 3) as avg_speed,
            ROUND(AVG(t.avg_defender_dist), 3) as avg_dist
        FROM player_game_tracking t
        JOIN games g ON g.date = t.game_date
          AND (g.home_team = t.team_abbr OR g.away_team = t.team_abbr)
        WHERE t.game_date >= ?
          AND t.drives_fga IS NOT NULL
        GROUP BY 1
        HAVING COUNT(DISTINCT t.game_date) >= 5
    """, (window_start,))
    team_tracking = {r['defending_team']: dict(r) for r in cur.fetchall()}

    if not team_tracking:
        print("  team_playtype_allowed: No tracking data found — skipping")
        return

    # Clear stale rows so normalized team names replace any BDL-abbreviation leftovers
    cur.execute("DELETE FROM team_playtype_allowed WHERE season=?", (SEASON,))

    # Load current def quality from team_scheme_cache
    cur.execute("SELECT team_abbr, active_style, def_quality_14d FROM team_scheme_cache WHERE scheme_type='DEFENSE'")
    def_quality = {r['team_abbr']: (r['active_style'], r['def_quality_14d']) for r in cur.fetchall()}

    # Compute league-wide ranks for each stat (1=best defense = lowest value allowed)
    all_teams = list(team_tracking.keys())
    cs_sorted = sorted(all_teams, key=lambda t: team_tracking[t].get('cs_3pa', 99))
    drives_sorted = sorted(all_teams, key=lambda t: team_tracking[t].get('drives_fga', 99))
    pullup_sorted = sorted(all_teams, key=lambda t: team_tracking[t].get('pullup_fga', 99))

    cs_rank = {t: i + 1 for i, t in enumerate(cs_sorted)}
    drives_rank = {t: i + 1 for i, t in enumerate(drives_sorted)}
    pullup_rank = {t: i + 1 for i, t in enumerate(pullup_sorted)}

    rows_written = 0
    for team_raw, stats in team_tracking.items():
        team = normalize_bdl_abbr(team_raw)  # GS→GSW, NY→NYK, PHO→PHX, SA→SAS, NO→NOP
        style, quality = def_quality.get(team, ('NEUTRAL', None))
        cur.execute("""
            INSERT INTO team_playtype_allowed
                (team_abbr, cs_3pa_allowed_pg, cs_3pm_allowed_pg, drives_fga_allowed_pg,
                 pullup_fga_allowed_pg, avg_off_speed_pg, avg_def_dist_pg,
                 cs_3pa_rank, drives_rank, pullup_rank,
                 def_style, def_quality, games_sample, season, updated_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?, ?, datetime('now'))
            ON CONFLICT(team_abbr, season) DO UPDATE SET
                cs_3pa_allowed_pg=excluded.cs_3pa_allowed_pg,
                cs_3pm_allowed_pg=excluded.cs_3pm_allowed_pg,
                drives_fga_allowed_pg=excluded.drives_fga_allowed_pg,
                pullup_fga_allowed_pg=excluded.pullup_fga_allowed_pg,
                avg_off_speed_pg=excluded.avg_off_speed_pg,
                avg_def_dist_pg=excluded.avg_def_dist_pg,
                cs_3pa_rank=excluded.cs_3pa_rank,
                drives_rank=excluded.drives_rank,
                pullup_rank=excluded.pullup_rank,
                def_style=excluded.def_style,
                def_quality=excluded.def_quality,
                games_sample=excluded.games_sample,
                updated_at=datetime('now')
        """, (team,
              stats.get('cs_3pa', 0), stats.get('cs_3pm', 0), stats.get('drives_fga', 0),
              stats.get('pullup_fga', 0), stats.get('avg_speed', 0), stats.get('avg_dist', 0),
              cs_rank.get(team, 15), drives_rank.get(team, 15), pullup_rank.get(team, 15),
              style, quality, stats.get('games', 0), SEASON))
        rows_written += 1

    conn.commit()
    print(f"  team_playtype_allowed: {rows_written} teams upserted")

    if verbose:
        cur.execute("""
            SELECT team_abbr, ROUND(cs_3pa_allowed_pg,2) as cs, cs_3pa_rank,
                   ROUND(drives_fga_allowed_pg,2) as drives, drives_rank, def_style, def_quality
            FROM team_playtype_allowed WHERE season=?
            ORDER BY cs_3pa_rank
        """, (SEASON,))
        rows = cur.fetchall()
        print(f"\n  {'Team':<6} {'C&S 3PA':>8} {'Rnk':>4} {'Drives':>7} {'Rnk':>4} {'Style':<12} {'Quality'}")
        for r in rows:
            print(f"  {r['team_abbr']:<6} {r['cs']:>8} {r['cs_3pa_rank']:>4} "
                  f"{r['drives']:>7} {r['drives_rank']:>4} {(r['def_style'] or 'N/A'):<12} {r['def_quality'] or ''}")


# ── Table 3: player_archetype_roster ──────────────────────────────────────────

def build_player_archetype_roster(conn: sqlite3.Connection, window_days: int = 60, verbose: bool = False) -> None:
    """
    Per active player: snapshot of archetype, defensive_tag, season averages,
    and performance vs each defense type (pts_vs_paint_pack, etc.).

    Groups by team → archetype for game notes queries:
    "BOS has 3 SNIPER_ELITE averaging 12% better vs PAINT_PACK"
    """
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS player_archetype_roster (
            player_name         TEXT NOT NULL,
            team                TEXT,
            position            TEXT,
            archetype           TEXT,
            defensive_tag       TEXT,
            synergy_type_1      TEXT,   -- Primary NBA Synergy type
            synergy_freq_1      REAL,
            -- Season averages (window_days)
            avg_pts             REAL DEFAULT 0.0,
            avg_reb             REAL DEFAULT 0.0,
            avg_ast             REAL DEFAULT 0.0,
            avg_3pm             REAL DEFAULT 0.0,
            avg_blk             REAL DEFAULT 0.0,
            avg_stl             REAL DEFAULT 0.0,
            avg_min             REAL DEFAULT 0.0,
            games_played        INTEGER DEFAULT 0,
            -- vs each defense type (pts delta vs season avg)
            pts_vs_paint_pack   REAL DEFAULT 0.0,
            pts_vs_perimeter    REAL DEFAULT 0.0,
            pts_vs_funnel       REAL DEFAULT 0.0,
            pts_vs_blitz        REAL DEFAULT 0.0,
            pts_vs_neutral      REAL DEFAULT 0.0,
            -- Bet performance
            bet_win_rate        REAL DEFAULT 0.0,
            bet_count           INTEGER DEFAULT 0,
            bet_net_units       REAL DEFAULT 0.0,
            -- Metadata
            synergy_dominance   TEXT,   -- DOMINANT/PRIMARY/MIXED/BALANCED
            effective_label     TEXT,   -- e.g. "HUB_BIG · POST_UP (23%)"
            season              TEXT NOT NULL DEFAULT '2025-26',
            updated_at          TEXT DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (player_name, season)
        )
    """)

    window_start = (datetime.now() - timedelta(days=window_days)).strftime('%Y-%m-%d')

    # Season averages per player
    cur.execute("""
        SELECT gl.player_name, gl.team_abbreviation as team,
            COUNT(*) as games,
            ROUND(AVG(gl.pts), 2) as avg_pts,
            ROUND(AVG(gl.reb), 2) as avg_reb,
            ROUND(AVG(gl.ast), 2) as avg_ast,
            ROUND(AVG(COALESCE(gl.fg3m, 0)), 2) as avg_3pm,
            ROUND(AVG(gl.blk), 3) as avg_blk,
            ROUND(AVG(gl.stl), 3) as avg_stl,
            ROUND(AVG(gl.minutes), 1) as avg_min
        FROM player_game_logs gl
        WHERE gl.game_date >= ? AND gl.minutes >= 10
        GROUP BY gl.player_name, gl.team_abbreviation
        HAVING COUNT(*) >= 5
    """, (window_start,))
    season_avgs = {r['player_name']: dict(r) for r in cur.fetchall()}

    # Pts per defense type per player — games table join for clean opponent resolution
    cur.execute("""
        SELECT gl.player_name, sc.active_style as def_style,
            ROUND(AVG(gl.pts), 2) as avg_pts, COUNT(*) as games
        FROM player_game_logs gl
        JOIN games g ON g.date = gl.game_date
          AND (g.home_team = gl.team_abbreviation OR g.away_team = gl.team_abbreviation)
        JOIN team_scheme_cache sc
          ON CASE WHEN g.home_team = gl.team_abbreviation THEN g.away_team
                  ELSE g.home_team END = sc.team_abbr
          AND sc.scheme_type = 'DEFENSE'
        WHERE gl.game_date >= ? AND gl.minutes >= 10
        GROUP BY gl.player_name, sc.active_style
        HAVING COUNT(*) >= 3
    """, (window_start,))
    pts_by_def = defaultdict(dict)
    for r in cur.fetchall():
        pts_by_def[r['player_name']][r['def_style']] = r['avg_pts']

    # Bet performance per player
    cur.execute("""
        SELECT player_name,
            COUNT(*) as bets,
            ROUND(100.0*SUM(CASE WHEN outcome='WIN' THEN 1 ELSE 0 END)/
                  NULLIF(SUM(CASE WHEN outcome IN('WIN','LOSS') THEN 1 ELSE 0 END),0), 3) as wr,
            ROUND(SUM(CASE WHEN outcome='WIN' THEN units WHEN outcome='LOSS' THEN -units ELSE 0 END), 2) as net_u
        FROM bet_recommendations
        WHERE game_date >= ? AND outcome IN ('WIN','LOSS','PUSH','VOID')
        GROUP BY player_name HAVING COUNT(*) >= 5
    """, (window_start,))
    bet_perf = {r['player_name']: dict(r) for r in cur.fetchall()}

    # Player type profiles for archetype + defensive_tag + synergy data
    cur.execute("""
        SELECT player_name, team, position, archetype, defensive_tag,
               synergy_type_1, synergy_freq_1, synergy_dominance, effective_label
        FROM player_type_profiles WHERE season = ?
    """, (SEASON,))
    type_profiles = {r['player_name']: dict(r) for r in cur.fetchall()}

    rows_written = 0
    for player_name, sa in season_avgs.items():
        profile = type_profiles.get(player_name, {})
        bp = bet_perf.get(player_name, {})
        pts_defs = pts_by_def.get(player_name, {})

        baseline_pts = sa.get('avg_pts', 0) or 0.0

        def _pts_delta(def_style):
            if def_style not in pts_defs:
                return 0.0
            return round(pts_defs[def_style] - baseline_pts, 2)

        cur.execute("""
            INSERT INTO player_archetype_roster
                (player_name, team, position, archetype, defensive_tag,
                 synergy_type_1, synergy_freq_1,
                 avg_pts, avg_reb, avg_ast, avg_3pm, avg_blk, avg_stl, avg_min,
                 games_played,
                 pts_vs_paint_pack, pts_vs_perimeter, pts_vs_funnel, pts_vs_blitz, pts_vs_neutral,
                 bet_win_rate, bet_count, bet_net_units,
                 synergy_dominance, effective_label, season, updated_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,datetime('now'))
            ON CONFLICT(player_name, season) DO UPDATE SET
                team=excluded.team, position=excluded.position,
                archetype=excluded.archetype, defensive_tag=excluded.defensive_tag,
                synergy_type_1=excluded.synergy_type_1, synergy_freq_1=excluded.synergy_freq_1,
                avg_pts=excluded.avg_pts, avg_reb=excluded.avg_reb, avg_ast=excluded.avg_ast,
                avg_3pm=excluded.avg_3pm, avg_blk=excluded.avg_blk, avg_stl=excluded.avg_stl,
                avg_min=excluded.avg_min, games_played=excluded.games_played,
                pts_vs_paint_pack=excluded.pts_vs_paint_pack,
                pts_vs_perimeter=excluded.pts_vs_perimeter,
                pts_vs_funnel=excluded.pts_vs_funnel,
                pts_vs_blitz=excluded.pts_vs_blitz,
                pts_vs_neutral=excluded.pts_vs_neutral,
                bet_win_rate=excluded.bet_win_rate,
                bet_count=excluded.bet_count,
                bet_net_units=excluded.bet_net_units,
                synergy_dominance=excluded.synergy_dominance,
                effective_label=excluded.effective_label,
                updated_at=datetime('now')
        """, (
            player_name,
            profile.get('team') or sa.get('team'),
            profile.get('position'),
            profile.get('archetype'),
            profile.get('defensive_tag'),
            profile.get('synergy_type_1'),
            profile.get('synergy_freq_1'),
            sa.get('avg_pts', 0), sa.get('avg_reb', 0), sa.get('avg_ast', 0),
            sa.get('avg_3pm', 0), sa.get('avg_blk', 0), sa.get('avg_stl', 0), sa.get('avg_min', 0),
            sa.get('games', 0),
            _pts_delta('PAINT_PACK'), _pts_delta('PERIMETER'),
            _pts_delta('FUNNEL'), _pts_delta('BLITZ'), _pts_delta('NEUTRAL'),
            (bp.get('wr') or 0.0) / 100.0,
            bp.get('bets', 0),
            bp.get('net_u', 0) or 0.0,
            profile.get('synergy_dominance'),
            profile.get('effective_label'),
            SEASON,
        ))
        rows_written += 1

    conn.commit()
    print(f"  player_archetype_roster: {rows_written} players upserted")

    if verbose:
        cur.execute("""
            SELECT player_name, team, archetype, synergy_type_1,
                   ROUND(avg_pts,1) as pts,
                   ROUND(pts_vs_paint_pack,1) as vs_paint,
                   ROUND(pts_vs_blitz,1) as vs_blitz,
                   ROUND(bet_win_rate*100,1) as wr_pct, bet_count
            FROM player_archetype_roster
            WHERE season=? AND archetype='ROLL_MAN' AND bet_count >= 10
            ORDER BY wr_pct DESC LIMIT 10
        """, (SEASON,))
        rows = cur.fetchall()
        if rows:
            print(f"\n  ROLL_MAN bet performance (sample):")
            for r in rows:
                print(f"  {r['player_name']:<22} {(r['team'] or '?'):<5} "
                      f"Pts: {r['pts']:>5} | vs PAINT: {r['vs_paint']:>+5} | "
                      f"vs BLITZ: {r['vs_blitz']:>+5} | WR: {r['wr_pct']:>5}% ({r['bet_count']}b)")


# ── Table 4: defensive_tag_vs_offense ────────────────────────────────────────

def build_defensive_tag_vs_offense(conn: sqlite3.Connection, window_days: int = 60, verbose: bool = False) -> None:
    """
    Per (defensive_tag, opponent_offense_type): how do tagged defenders perform
    on DEFENSIVE stats (BLK, STL, DREB) vs different opponent offense styles?

    Insight examples:
      RIM_GUARDIAN vs ISO_HEAVY offense → more BLK (ISO players attack the rim)
      PERIMETER_HAWK vs MOTION offense → more STL (high ball movement = turnovers)
      SWITCHABLE_ANCHOR vs PACE_PUSH → more DREB (transition misses, long rebounds)

    Feeds game notes: "Jarrett Allen (RIM_GUARDIAN) vs MEM (FUNNEL, MOTION offense):
    RIM_GUARDIAN players avg 1.8 BLK vs MOTION teams (+0.4 above baseline)."
    """
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS defensive_tag_vs_offense (
            defensive_tag       TEXT NOT NULL,
            offense_type        TEXT NOT NULL,  -- MOTION/ISO_HEAVY/PACE_PUSH/HALF_COURT
            season              TEXT NOT NULL DEFAULT '2025-26',
            -- Game defensive stats in this matchup
            games               INTEGER DEFAULT 0,
            avg_blk             REAL DEFAULT 0.0,
            avg_stl             REAL DEFAULT 0.0,
            avg_dreb            REAL DEFAULT 0.0,
            avg_pf              REAL DEFAULT 0.0,
            -- Delta vs season baseline for this defensive tag
            blk_vs_baseline     REAL DEFAULT 0.0,
            stl_vs_baseline     REAL DEFAULT 0.0,
            dreb_vs_baseline    REAL DEFAULT 0.0,
            -- Bet performance on BLK/STL props for tagged players
            blk_bets            INTEGER DEFAULT 0,
            blk_win_rate        REAL DEFAULT 0.0,
            stl_bets            INTEGER DEFAULT 0,
            stl_win_rate        REAL DEFAULT 0.0,
            updated_at          TEXT DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (defensive_tag, offense_type, season)
        )
    """)

    VALID_DEF_TAGS = {'RIM_GUARDIAN', 'PERIMETER_HAWK', 'SWITCHABLE_ANCHOR', 'HUSTLE_DISRUPTOR', 'WEAK_LINK'}
    VALID_OFF_TYPES = {'MOTION', 'ISO_HEAVY', 'PACE_PUSH', 'HALF_COURT', 'BALANCED'}

    window_start = (datetime.now() - timedelta(days=window_days)).strftime('%Y-%m-%d')

    # Season baseline per defensive tag (avg defensive stats regardless of opponent)
    cur.execute("""
        SELECT p.defensive_tag,
            ROUND(AVG(gl.blk), 3) as avg_blk,
            ROUND(AVG(gl.stl), 3) as avg_stl,
            ROUND(AVG(COALESCE(gl.dreb, gl.reb * 0.75)), 2) as avg_dreb
        FROM players p
        JOIN player_game_logs gl ON gl.player_name = p.name
        WHERE gl.game_date >= ?
          AND p.defensive_tag IN ({})
          AND gl.minutes >= 10
        GROUP BY p.defensive_tag
    """.format(','.join(['?' for _ in VALID_DEF_TAGS])),
    [window_start] + list(VALID_DEF_TAGS))
    def_baselines = {r['defensive_tag']: dict(r) for r in cur.fetchall()}

    # Avg defensive stats by (defensive_tag, opponent_offense_type)
    # Opponent offense type from team_scheme_cache for the player's OPPONENT team
    _arch_ph = ','.join(['?' for _ in VALID_DEF_TAGS])
    _off_ph  = ','.join(['?' for _ in VALID_OFF_TYPES])
    cur.execute(f"""
        SELECT p.defensive_tag, sc.active_style as off_type,
            COUNT(*) as games,
            ROUND(AVG(gl.blk), 3) as avg_blk,
            ROUND(AVG(gl.stl), 3) as avg_stl,
            ROUND(AVG(COALESCE(gl.dreb, gl.reb * 0.75)), 2) as avg_dreb,
            ROUND(AVG(gl.pf), 2) as avg_pf
        FROM players p
        JOIN player_game_logs gl ON gl.player_name = p.name
        JOIN games g ON g.date = gl.game_date
          AND (g.home_team = gl.team_abbreviation OR g.away_team = gl.team_abbreviation)
        JOIN team_scheme_cache sc
          ON CASE WHEN g.home_team = gl.team_abbreviation THEN g.away_team
                  ELSE g.home_team END = sc.team_abbr
          AND sc.scheme_type = 'OFFENSE'
        WHERE gl.game_date >= ?
          AND p.defensive_tag IN ({_arch_ph})
          AND sc.active_style IN ({_off_ph})
          AND gl.minutes >= 10
        GROUP BY p.defensive_tag, sc.active_style
        HAVING COUNT(*) >= 5
    """, [window_start] + list(VALID_DEF_TAGS) + list(VALID_OFF_TYPES))
    matchup_stats = {(r['defensive_tag'], r['off_type']): dict(r) for r in cur.fetchall()}

    # BLK/STL bet performance per (defensive_tag, opponent_offense_type)
    cur.execute(f"""
        SELECT p.defensive_tag, sc.active_style as off_type,
            b.stat_category,
            COUNT(*) as bets,
            ROUND(100.0*SUM(CASE WHEN b.outcome='WIN' THEN 1 ELSE 0 END)/
                  NULLIF(SUM(CASE WHEN b.outcome IN('WIN','LOSS') THEN 1 ELSE 0 END),0), 3) as wr
        FROM bet_recommendations b
        JOIN players p ON b.player_name = p.name
        JOIN team_scheme_cache sc ON b.opponent = sc.team_abbr AND sc.scheme_type = 'OFFENSE'
        WHERE b.game_date >= ?
          AND b.outcome IN ('WIN','LOSS','PUSH','VOID')
          AND b.stat_category IN ('BLK','STL')
          AND p.defensive_tag IN ({_arch_ph})
          AND sc.active_style IN ({_off_ph})
        GROUP BY p.defensive_tag, sc.active_style, b.stat_category
        HAVING COUNT(*) >= 5
    """, [window_start] + list(VALID_DEF_TAGS) + list(VALID_OFF_TYPES))
    bet_stats = {}
    for r in cur.fetchall():
        key = (r['defensive_tag'], r['off_type'])
        bet_stats.setdefault(key, {})[r['stat_category']] = (r['bets'], r['wr'] or 0.0)

    rows_written = 0
    for def_tag in VALID_DEF_TAGS:
        baseline = def_baselines.get(def_tag, {})
        for off_type in VALID_OFF_TYPES:
            ms = matchup_stats.get((def_tag, off_type), {})
            bs = bet_stats.get((def_tag, off_type), {})
            if not ms:
                continue

            bl = baseline.get('avg_blk', 0) or 0.0
            bs_stl = baseline.get('avg_stl', 0) or 0.0
            bd = baseline.get('avg_dreb', 0) or 0.0

            blk_bets, blk_wr = bs.get('BLK', (0, 0.0))
            stl_bets, stl_wr = bs.get('STL', (0, 0.0))

            cur.execute("""
                INSERT INTO defensive_tag_vs_offense
                    (defensive_tag, offense_type, season, games,
                     avg_blk, avg_stl, avg_dreb, avg_pf,
                     blk_vs_baseline, stl_vs_baseline, dreb_vs_baseline,
                     blk_bets, blk_win_rate, stl_bets, stl_win_rate, updated_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?, datetime('now'))
                ON CONFLICT(defensive_tag, offense_type, season) DO UPDATE SET
                    games=excluded.games, avg_blk=excluded.avg_blk,
                    avg_stl=excluded.avg_stl, avg_dreb=excluded.avg_dreb,
                    avg_pf=excluded.avg_pf,
                    blk_vs_baseline=excluded.blk_vs_baseline,
                    stl_vs_baseline=excluded.stl_vs_baseline,
                    dreb_vs_baseline=excluded.dreb_vs_baseline,
                    blk_bets=excluded.blk_bets, blk_win_rate=excluded.blk_win_rate,
                    stl_bets=excluded.stl_bets, stl_win_rate=excluded.stl_win_rate,
                    updated_at=datetime('now')
            """, (
                def_tag, off_type, SEASON,
                ms.get('games', 0),
                ms.get('avg_blk', 0) or 0.0,
                ms.get('avg_stl', 0) or 0.0,
                ms.get('avg_dreb', 0) or 0.0,
                ms.get('avg_pf', 0) or 0.0,
                round((ms.get('avg_blk', 0) or 0.0) - bl, 3),
                round((ms.get('avg_stl', 0) or 0.0) - bs_stl, 3),
                round((ms.get('avg_dreb', 0) or 0.0) - bd, 2),
                blk_bets, blk_wr / 100.0,
                stl_bets, stl_wr / 100.0,
            ))
            rows_written += 1

    conn.commit()
    print(f"  defensive_tag_vs_offense: {rows_written} rows upserted")

    if verbose and rows_written > 0:
        cur.execute("""
            SELECT defensive_tag, offense_type, games,
                   ROUND(avg_blk,3) as blk, ROUND(blk_vs_baseline,3) as blk_d,
                   ROUND(avg_stl,3) as stl, ROUND(stl_vs_baseline,3) as stl_d,
                   blk_bets, ROUND(blk_win_rate*100,1) as blk_wr
            FROM defensive_tag_vs_offense
            WHERE season=? AND games >= 10
            ORDER BY blk_vs_baseline DESC LIMIT 15
        """, (SEASON,))
        rows = cur.fetchall()
        if rows:
            print(f"\n  Defensive tag × offense type (BLK signal, ≥10 games):")
            print(f"  {'Def Tag':<20} {'vs':<12} {'G':>4} {'BLK':>6} {'Δ':>6} {'STL':>6} {'Δ':>6} {'BLK WR'}")
            for r in rows:
                print(f"  {r['defensive_tag']:<20} {r['offense_type']:<12} {r['games']:>4} "
                      f"{r['blk']:>6} {r['blk_d']:>+6} {r['stl']:>6} {r['stl_d']:>+6} "
                      f"{r['blk_wr'] if r['blk_bets'] >= 5 else 'n/a':>6}")


# ── Token-efficient context helper ────────────────────────────────────────────

def get_matchup_context_row(conn: sqlite3.Connection, archetype: str, defense_type: str,
                             opponent_team: str = None) -> str:
    """
    Returns a 2-line pre-computed matchup context string for Claude prompts.
    Replaces multi-sentence matchup reasoning with a single DB lookup.

    Example output:
    "ROLL_MAN vs PAINT_PACK: 69.9% WR (n=247), avg +1.2 pts above baseline.
     LAL allows 2.25 drives/g (20th), 2.54 C&S 3PA (15th), PAINT_PACK [AVERAGE]."
    """
    cur = conn.cursor()

    # Archetype vs defense performance
    cur.execute("""
        SELECT bets, ROUND(win_rate*100,1) as wr_pct, net_units,
               ROUND(pts_vs_baseline,1) as pts_delta, games
        FROM player_archetype_vs_defense
        WHERE archetype=? AND defense_type=? AND season=?
    """, (archetype, defense_type, SEASON))
    arch_row = cur.fetchone()

    arch_str = "No historical data for this matchup."
    if arch_row and arch_row['bets'] >= 5:
        arch_str = (f"{archetype} vs {defense_type}: {arch_row['wr_pct']}% WR "
                    f"(n={arch_row['bets']}), pts {arch_row['pts_delta']:+.1f} vs baseline.")

    # Opponent team playtype data
    team_str = ""
    if opponent_team:
        cur.execute("""
            SELECT ROUND(cs_3pa_allowed_pg,2) as cs, cs_3pa_rank,
                   ROUND(drives_fga_allowed_pg,2) as drives, drives_rank,
                   def_style, def_quality
            FROM team_playtype_allowed WHERE team_abbr=? AND season=?
        """, (opponent_team, SEASON))
        t = cur.fetchone()
        if t:
            team_str = (f"{opponent_team} allows {t['drives']:.2f} drives/g "
                        f"(#{t['drives_rank']}), {t['cs']:.2f} C&S 3PA/g "
                        f"(#{t['cs_3pa_rank']}), {t['def_style'] or 'NEUTRAL'} "
                        f"[{t['def_quality'] or 'AVERAGE'}].")

    return f"{arch_str}\n{team_str}".strip()


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Build matchup intelligence tables")
    parser.add_argument('--window-days', type=int, default=DEFAULT_WINDOW_DAYS,
                        help=f'Days of historical data to use (default: {DEFAULT_WINDOW_DAYS})')
    parser.add_argument('--verbose', action='store_true', help='Print sample output after each table')
    args = parser.parse_args()

    print(f"\n{'='*60}")
    print(f"MATCHUP INTELLIGENCE BUILDER — {args.window_days}-day window")
    print(f"{'='*60}")

    conn = _connect()

    build_player_archetype_vs_defense(conn, window_days=args.window_days, verbose=args.verbose)
    build_team_playtype_allowed(conn, window_days=args.window_days, verbose=args.verbose)
    build_player_archetype_roster(conn, window_days=args.window_days, verbose=args.verbose)
    build_defensive_tag_vs_offense(conn, window_days=args.window_days, verbose=args.verbose)

    # Quick validation
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    for tbl in ['player_archetype_vs_defense', 'team_playtype_allowed',
                'player_archetype_roster', 'defensive_tag_vs_offense']:
        cur.execute(f"SELECT COUNT(*) as n FROM {tbl}")
        r = cur.fetchone()
        print(f"  [{tbl}] {r['n']} rows total")

    # Sample context query
    if args.verbose:
        sample = get_matchup_context_row(conn, 'ROLL_MAN', 'PAINT_PACK', 'BOS')
        print(f"\nSample get_matchup_context_row(ROLL_MAN, PAINT_PACK, BOS):")
        print(f"  {sample}")

    conn.close()
    print(f"\n✅ Matchup intelligence tables updated.")


if __name__ == "__main__":
    main()
