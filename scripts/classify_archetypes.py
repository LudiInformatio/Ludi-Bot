#!/usr/bin/env python3
"""
Phase 8.4: Weekly Archetype Classification + Team Scheme Resolution
======================================================================
Classifies active NBA players into 19 primary archetypes via Claude Haiku.
Resolves team offensive/defensive scheme conflicts via Claude Haiku.
Wired into weekly_validation.yml + data_sync.yml.

CLI args:
  --dry-run: print proposed changes, zero DB writes
  --limit N: process only N players (for testing)
  --window-days: default 21
  --min-games: default 3
"""

import argparse
import sqlite3
import sys
import os
from datetime import datetime, timedelta
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.claude_client import get_claude_analysis, HAIKU_MODEL

VALID_ARCHETYPES = {
    'HELIOCENTRIC_MAESTRO', 'SLASHING_CREATOR', 'JUMBO_FACILITATOR', 'SNIPER_ELITE',
    'TWO_LEVEL_SCORER', 'ISO_ASSASSIN', 'WARRIOR_BIG', 'STRETCH_BIG', 'ROLL_MAN',
    'HUB_BIG', 'ENERGY_BIG', 'RIM_GUARDIAN', 'PERIMETER_HAWK', 'SWITCHABLE_ANCHOR',
    'HUSTLE_DISRUPTOR', 'CUTTER_SPECIALIST', 'CONNECTOR', 'FACILITATOR', 'GENERALIST'
}

VALID_DEFENSE = {'PAINT_PACK', 'PERIMETER', 'BLITZ', 'FUNNEL', 'NEUTRAL'}
VALID_OFFENSE = {'MOTION', 'ISO_HEAVY', 'HALF_COURT', 'PACE_PUSH', 'BALANCED'}

SYSTEM_PROMPT_ARCHETYPE = """You are an NBA player archetype classifier. Output EXACTLY ONE archetype from the valid list.
No explanation. No extra text. Just the archetype name.

VALID ARCHETYPES (pick exactly one):
HELIOCENTRIC_MAESTRO, SLASHING_CREATOR, JUMBO_FACILITATOR, SNIPER_ELITE,
TWO_LEVEL_SCORER, ISO_ASSASSIN, WARRIOR_BIG, STRETCH_BIG, ROLL_MAN, HUB_BIG,
ENERGY_BIG, RIM_GUARDIAN, PERIMETER_HAWK, SWITCHABLE_ANCHOR, HUSTLE_DISRUPTOR,
CUTTER_SPECIALIST, CONNECTOR, FACILITATOR, GENERALIST

CLASSIFICATION RULES:
- HELIOCENTRIC_MAESTRO: primary creator, high USG, spreads to multiple playtypes (P&R + ISO + transition)
- ISO_ASSASSIN: isolation-dominant (>20% ISO freq), low pass rate, elite self-creation
- SLASHING_CREATOR: drive-first, high FTA/FGA ratio, P&R handler or handoff heavy
- JUMBO_FACILITATOR: big-man playmaker (Jokic/Sabonis type), top P&R handler, high AST, large frame
- SNIPER_ELITE: 35%+ SPOT_UP freq, high 3PA, low at-rim freq, high percentile catch-and-shoot
- TWO_LEVEL_SCORER: efficient mid-range + rim, high shot quality, no single dominant playtype
- WARRIOR_BIG: physical bruiser big, transition + putback heavy, draws fouls
- STRETCH_BIG: big man with 30%+ SPOT_UP or OFF_SCREEN, high corner-3 freq
- ROLL_MAN: 30%+ PR_ROLL_MAN freq, lives at rim, high at-rim freq
- HUB_BIG: passing-first big (Draymond type), high AST, low shot volume
- ENERGY_BIG: hustle role, high OREB + PUTBACK freq, consistent minutes, low USG
- RIM_GUARDIAN: 70%+ at-rim shot freq, top BLK rate, minimal perimeter shooting
- PERIMETER_HAWK: wing defender, high STL, opportunistic SPOT_UP scorer
- SWITCHABLE_ANCHOR: versatile defender, moderate BLK+STL, covers multiple positions
- HUSTLE_DISRUPTOR: chaos agent, high deflections, multiple secondary playtype presence
- CUTTER_SPECIALIST: 25%+ CUT freq, off-ball movement, high score_freq_pct on cuts
- CONNECTOR: secondary ball-handler, moderate AST, TRANSITION secondary role
- FACILITATOR: pure passer, high AST/USG ratio, HANDOFF or P&R handler secondary
- GENERALIST: plays multiple ways without clear dominant pattern (use as last resort)
"""

SYSTEM_PROMPT_SCHEME = """You are an NBA team scheme classifier. Output EXACTLY ONE label. No explanation.

VALID DEFENSIVE: PAINT_PACK, PERIMETER, BLITZ, FUNNEL, NEUTRAL
VALID OFFENSIVE: MOTION, ISO_HEAVY, HALF_COURT, PACE_PUSH, BALANCED

DEFENSIVE:
- PAINT_PACK: drops in coverage, allows 3s, elite paint protection
- PERIMETER: switch-heavy, fights over screens
- BLITZ: ball movement allowed, zone elements, high cs_3pa allowed
- FUNNEL: channels drives to help, limits 3PA
- NEUTRAL: no dominant pattern

OFFENSIVE:
- MOTION: high AST/FGM (>0.675), ball movement
- ISO_HEAVY: low AST/FGM (<0.600), isolation dominant
- HALF_COURT: slow pace (<99)
- PACE_PUSH: fast pace (>101) or high PPG (>120)
- BALANCED: no dominant pattern
"""


def get_db_connection(db_path='ludi.db'):
    return sqlite3.connect(db_path)


def get_active_players(conn, window_days=21, min_games=3):
    """Query active players with sufficient game sample."""
    cutoff_date = (datetime.now() - timedelta(days=window_days)).strftime('%Y-%m-%d')
    
    query = """
        SELECT DISTINCT p.player_id, p.name, p.position, p.team, p.archetype as current_archetype
        FROM players p
        JOIN player_game_logs pgl ON p.player_id = pgl.player_id
        WHERE pgl.game_date >= ?
          AND p.status = 'ACTIVE'
        GROUP BY p.player_id, p.name, p.position, p.team, p.archetype
        HAVING COUNT(DISTINCT pgl.game_id) >= ?
        ORDER BY p.name
    """
    
    cur = conn.cursor()
    cur.execute(query, (cutoff_date, min_games))
    return cur.fetchall()


def get_player_synergy(conn, player_name):
    """Get all synergy playtypes for a Player, ordered by freq_pct DESC."""
    query = """
        SELECT playtype, freq_pct, ppp, score_freq_pct, percentile
        FROM player_synergy_playtypes
        WHERE player_name = ?
        ORDER BY freq_pct DESC
    """
    cur = conn.cursor()
    cur.execute(query, (player_name,))
    rows = cur.fetchall()
    # Filter out rows with None freq_pct
    return [r for r in rows if r[1] is not None]


def get_player_shot_quality(conn, player_id):
    """Get shot quality data for a player."""
    query = """
        SELECT at_rim_freq, corner_3_freq, shot_quality_avg
        FROM player_shot_quality
        WHERE player_id = ?
    """
    cur = conn.cursor()
    cur.execute(query, (player_id,))
    row = cur.fetchone()
    if row:
        return {'at_rim_freq': row[0], 'corner_3_freq': row[1], 'shot_quality_avg': row[2]}
    return None


def get_player_l10(conn, player_id, window_days=21):
    """Get L10 (or window average) stats for a player."""
    cutoff_date = (datetime.now() - timedelta(days=window_days)).strftime('%Y-%m-%d')
    
    query = """
        SELECT 
            AVG(pts) as pts, AVG(ast) as ast, AVG(reb) as reb,
            AVG(stl) as stl, AVG(blk) as blk,
            AVG(fga) as fga, AVG(fg3a) as fg3a, AVG(fta) as fta,
            AVG(minutes) as minutes
        FROM player_game_logs
        WHERE player_id = ? AND game_date >= ?
    """
    cur = conn.cursor()
    cur.execute(query, (player_id, cutoff_date))
    row = cur.fetchone()
    if row and row[0] is not None:
        return {
            'pts': row[0], 'ast': row[1], 'reb': row[2], 'stl': row[3], 'blk': row[4],
            'fga': row[5], 'fg3a': row[6], 'fta': row[7], 'minutes': row[8]
        }
    return None


def build_archetype_prompt(name, position, team, synergy_data, shot_data, l10_data, current_archetype):
    """Build the user prompt for archetype classification."""
    synergy_block = ""
    if synergy_data:
        for row in synergy_data:
            ppp_val = row[2] if row[2] is not None else 0.0
            score_val = row[3] if row[3] is not None else 0.0
            pct_val = row[4] if row[4] is not None else 0
            synergy_block += f"  {row[0]}: {row[1]:.1f}% | {ppp_val:.2f} PPP | {score_val:.0f}% score | {pct_val}th pct\n"
    else:
        synergy_block = "  No Synergy data available\n"
    
    shot_block = ""
    if shot_data:
        shot_block = f"Shot profile: at-rim {shot_data['at_rim_freq']:.1f}% | corner-3 {shot_data['corner_3_freq']:.1f}% | quality {shot_data['shot_quality_avg']:.3f}\n"
    else:
        shot_block = "No shot quality data\n"
    
    l10_block = ""
    if l10_data:
        l10_block = f"""L10 box: PTS {l10_data['pts']:.1f} | AST {l10_data['ast']:.1f} | REB {l10_data['reb']:.1f} | STL {l10_data['stl']:.1f} | BLK {l10_data['blk']:.1f}
          FGA {l10_data['fga']:.1f} | 3PA {l10_data['fg3a']:.1f} | FTA {l10_data['fta']:.1f} | MIN {l10_data['minutes']:.0f}"""
    else:
        l10_block = "No L10 box data"
    
    return f"""Player: {name} | {position} | {team}

Synergy usage profile (all playtypes, high freq first):
{synergy_block}{shot_block}
{l10_block}
Current DB archetype: {current_archetype or 'NULL'}"""


def validate_archetype(result, synergy_data, shot_data):
    """
    Two-gate validation:
    Gate 1 — Schema: result must be in VALID_ARCHETYPES
    Gate 2 — Synergy sanity: check thresholds based on claimed archetype
    """
    result_upper = result.strip().upper()
    
    # Gate 1: Schema validation
    if result_upper not in VALID_ARCHETYPES:
        return False, f"GATE1: {result_upper} not in VALID_ARCHETYPES"
    
    # Gate 2: Synergy sanity checks
    synergy_dict = {row[0]: row[1] for row in synergy_data} if synergy_data else {}
    
    if result_upper == 'ISO_ASSASSIN':
        iso_freq = synergy_dict.get('ISO', 0)
        if iso_freq < 15.0:
            return False, f"GATE2: ISO_ASSASSIN but ISO freq={iso_freq:.1f}% < 15%"
    
    elif result_upper == 'SNIPER_ELITE':
        spot_up_freq = synergy_dict.get('SPOT_UP', 0)
        if spot_up_freq < 25.0:
            return False, f"GATE2: SNIPER_ELITE but SPOT_UP freq={spot_up_freq:.1f}% < 25%"
    
    elif result_upper == 'RIM_GUARDIAN':
        if shot_data and shot_data.get('at_rim_freq', 0) < 50.0:
            return False, f"GATE2: RIM_GUARDIAN but at_rim_freq={shot_data['at_rim_freq']:.1f}% < 50%"
    
    elif result_upper == 'ROLL_MAN':
        roll_freq = synergy_dict.get('PR_ROLL_MAN', 0)
        if roll_freq < 20.0:
            return False, f"GATE2: ROLL_MAN but PR_ROLL_MAN freq={roll_freq:.1f}% < 20%"
    
    elif result_upper == 'CUTTER_SPECIALIST':
        cut_freq = synergy_dict.get('CUT', 0)
        if cut_freq < 20.0:
            return False, f"GATE2: CUTTER_SPECIALIST but CUT freq={cut_freq:.1f}% < 20%"
    
    return True, "PASS"


def run_team_scheme_subprocess():
    """Run update_team_scheme_cache.py as subprocess for deterministic baseline."""
    import subprocess
    result = subprocess.run(
        [sys.executable, 'scripts/update_team_scheme_cache.py'],
        check=False,
        capture_output=True,
        text=True
    )
    if result.returncode != 0:
        print(f"[WARN] update_team_scheme_cache.py failed: {result.stderr[:200]}")
    else:
        print(f"[INFO] Team scheme cache updated")


def get_team_scheme_conflicts(conn):
    """Query teams with season vs d14 style conflicts."""
    query = """
        SELECT team_abbr, scheme_type, season_style, d14_style, active_style
        FROM team_scheme_cache
        WHERE season_style != d14_style
    """
    cur = conn.cursor()
    cur.execute(query)
    return cur.fetchall()


def get_14d_offense_stats(conn, team_abbr, cutoff_date):
    """Get 14d offensive stats for a team."""
    query = """
        SELECT 
            AVG(g.pts) as pts,
            AVG(g.pace) as pace,
            SUM(pgl.fgm) as fgm,
            SUM(pgl.ast) as ast
        FROM player_game_logs pgl
        JOIN games g ON pgl.game_id = g.game_id
        WHERE pgl.team_abbreviation = ? AND pgl.game_date >= ?
    """
    cur = conn.cursor()
    cur.execute(query, (team_abbr, cutoff_date))
    row = cur.fetchone()
    if row and row[0] is not None:
        return {'pts': row[0], 'pace': row[1] or 100, 'fgm': row[2] or 1, 'ast': row[3] or 0}
    return None


def get_14d_defense_stats(conn, team_abbr, cutoff_date):
    """Get 14d defensive stats for a team."""
    query = """
        SELECT 
            SUM(pgt.drives_fga) as drives,
            AVG(CASE WHEN pgt.drives_fga > 0 THEN CAST(pgt.drives_fgm AS REAL) / pgt.drives_fga ELSE 0 END) as drive_fg_pct,
            AVG(pgt.avg_defender_dist) as defender_dist,
            SUM(pgt.catch_shoot_3pa) as cs_3pa
        FROM player_game_tracking pgt
        JOIN games g ON pgt.nba_game_id = g.game_id
        WHERE pgt.team_abbr = ? AND g.date >= ?
    """
    cur = conn.cursor()
    cur.execute(query, (team_abbr, cutoff_date))
    row = cur.fetchone()
    if row and row[0] is not None:
        return {'drives': row[0], 'drive_fg_pct': row[1] or 0, 'defender_dist': row[2] or 0, 'cs_3pa': row[3] or 0}
    return None


def get_injured_starters(conn, team_abbr):
    """Get injured starters for a team."""
    query = """
        SELECT p.name, pi.days_out
        FROM player_injuries pi
        JOIN players p ON pi.player_name = p.name
        WHERE p.team = ? AND pi.days_out > 3
        ORDER BY pi.days_out DESC
        LIMIT 3
    """
    cur = conn.cursor()
    cur.execute(query, (team_abbr,))
    return cur.fetchall()


def build_scheme_prompt(team_abbr, scheme_type, season_style, d14_style, active_style, stats, injury_note):
    """Build the user prompt for scheme classification."""
    stat_block = ""
    if scheme_type == 'OFFENSE':
        stat_block = f"14d: PPG {stats.get('pts', 0):.1f} | Pace {stats.get('pace', 100):.1f} | AST/FGM {stats.get('ast', 0) / max(stats.get('fgm', 1), 1):.3f}"
    else:
        stat_block = f"14d: Drives {stats.get('drives', 0):.0f} | Drive FG% {stats.get('drive_fg_pct', 0):.1f} | Avg Defender Dist {stats.get('defender_dist', 0):.1f}ft | Cs_3PA {stats.get('cs_3pa', 0):.0f}"
    
    return f"""Team: {team_abbr} | Classifying: {scheme_type}
Season label: {season_style} vs Last 14d: {d14_style} | Current active: {active_style}
{stat_block}
Key starters out: {injury_note or 'None'}
Based on the 14d trend, output the most accurate {scheme_type} scheme label."""


def main():
    parser = argparse.ArgumentParser(description="Classify player archetypes and resolve team scheme conflicts")
    parser.add_argument("--dry-run", action="store_true", help="Print proposed changes, zero DB writes")
    parser.add_argument("--limit", type=int, default=None, help="Process only N players (for testing)")
    parser.add_argument("--window-days", type=int, default=21, help="Window for active players (default: 21)")
    parser.add_argument("--min-games", type=int, default=3, help="Minimum games for active players (default: 3)")
    parser.add_argument("--db-path", default="ludi.db", help="Path to SQLite database")
    args = parser.parse_args()
    
    conn = get_db_connection(args.db_path)
    
    # ===================== PART A: PLAYER ARCHETYPES =====================
    print(f"\n=== PHASE 8.4 CLASSIFICATION STARTED ===")
    print(f"Window: {args.window_days}d | Min games: {args.min_games}")
    
    players = get_active_players(conn, args.window_days, args.min_games)
    if args.limit:
        players = players[:args.limit]
    
    print(f"Active players to process: {len(players)}")
    
    processed = 0
    changed = 0
    unchanged = 0
    skipped = 0
    total_tokens = 0
    archetype_changes = []
    generalist_count = 0
    
    for player_id, name, position, team, current_archetype in players:
        processed += 1
        
        synergy_data = get_player_synergy(conn, name)
        shot_data = get_player_shot_quality(conn, player_id)
        l10_data = get_player_l10(conn, player_id, args.window_days)
        
        prompt = build_archetype_prompt(name, position, team, synergy_data, shot_data, l10_data, current_archetype)
        
        result = get_claude_analysis(
            prompt,
            SYSTEM_PROMPT_ARCHETYPE,
            HAIKU_MODEL,
            temperature=0.1,
            max_tokens=20
        )
        
        if not result:
            print(f"[SKIP] {name}: Claude call failed")
            skipped += 1
            continue
        
        result = result.strip()
        
        valid, reason = validate_archetype(result, synergy_data, shot_data)
        
        if not valid:
            print(f"[SKIP {reason}] {name}: {result}")
            skipped += 1
            continue
        
        if result == 'GENERALIST':
            generalist_count += 1
        
        if result == current_archetype:
            unchanged += 1
            print(f"[UNCHANGED] {name}: {result}")
        else:
            changed += 1
            archetype_changes.append((name, current_archetype or 'NULL', result))
            print(f"[CHANGE] {name}: {current_archetype or 'NULL'} -> {result}")
            
            if not args.dry_run:
                cur = conn.cursor()
                cur.execute(
                    "UPDATE players SET archetype = ?, updated_at = datetime('now') WHERE player_id = ?",
                    (result, player_id)
                )
    
    if not args.dry_run and changed > 0:
        conn.commit()
    
    # ===================== PART B: TEAM SCHEME CONFLICTS =====================
    print(f"\n=== TEAM SCHEME RESOLUTION ===")
    
    run_team_scheme_subprocess()
    
    conflicts = get_team_scheme_conflicts(conn)
    n_conflicts = len(conflicts)
    n_resolved = 0
    
    cutoff_date = (datetime.now() - timedelta(days=14)).strftime('%Y-%m-%d')
    
    before_neutral = 0
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM team_scheme_cache WHERE scheme_type='DEFENSE' AND active_style='NEUTRAL'")
    before_neutral = cur.fetchone()[0]
    
    for team_abbr, scheme_type, season_style, d14_style, active_style in conflicts:
        if scheme_type == 'OFFENSE':
            stats = get_14d_offense_stats(conn, team_abbr, cutoff_date)
        else:
            stats = get_14d_defense_stats(conn, team_abbr, cutoff_date)
        
        injuries = get_injured_starters(conn, team_abbr)
        injury_note = ', '.join([f"{n}({d}d)" for n, d in injuries]) if injuries else None
        
        prompt = build_scheme_prompt(team_abbr, scheme_type, season_style, d14_style, active_style, stats or {}, injury_note)
        
        result = get_claude_analysis(
            prompt,
            SYSTEM_PROMPT_SCHEME,
            HAIKU_MODEL,
            temperature=0.1,
            max_tokens=20
        )
        
        if not result:
            print(f"[SKIP] {team_abbr} {scheme_type}: Claude call failed")
            continue
        
        result = result.strip().upper()
        
        if scheme_type == 'OFFENSE':
            valid_set = VALID_OFFENSE
        else:
            valid_set = VALID_DEFENSE
        
        if result not in valid_set:
            print(f"[SKIP] {team_abbr} {scheme_type}: invalid scheme {result}")
            continue
        
        print(f"[RESOLVE] {team_abbr} {scheme_type}: {active_style} -> {result}")
        n_resolved += 1
        
        if not args.dry_run:
            cur.execute(
                "UPDATE team_scheme_cache SET active_style = ?, updated_at = datetime('now') WHERE team_abbr = ? AND scheme_type = ?",
                (result, team_abbr, scheme_type)
            )
    
    if not args.dry_run and n_resolved > 0:
        conn.commit()
    
    after_neutral = 0
    cur.execute("SELECT COUNT(*) FROM team_scheme_cache WHERE scheme_type='DEFENSE' AND active_style='NEUTRAL'")
    after_neutral = cur.fetchone()[0]
    
    conn.close()
    
    # ===================== SUMMARY =====================
    generalist_pct = (generalist_count / processed * 100) if processed > 0 else 0
    
    print(f"\n=== PHASE 8.4 CLASSIFICATION SUMMARY ===")
    print(f"Players: {processed} processed | {changed} changed | {unchanged} unchanged | {skipped} skipped")
    print(f"GENERALIST: {generalist_pct:.1f}% of active players (target <25%)")
    
    if archetype_changes:
        print(f"Top archetype changes:")
        for name, old, new in archetype_changes[:5]:
            print(f"  {name}: {old} -> {new}")
    
    print(f"Team schemes: {n_conflicts} conflicts found | {n_resolved} resolved")
    print(f"Team NEUTRAL count: {before_neutral} -> {after_neutral} (of 30 defensive slots)")
    
    # Store summary for verification
    summary = {
        'processed': processed,
        'changed': changed,
        'unchanged': unchanged,
        'skipped': skipped,
        'generalist_pct': generalist_pct,
        'n_conflicts': n_conflicts,
        'n_resolved': n_resolved,
        'neutral_before': before_neutral,
        'neutral_after': after_neutral
    }
    
    return summary


if __name__ == "__main__":
    main()
