#!/usr/bin/env python3
"""
Phase 8.4: Weekly Archetype Classification + Team Scheme Resolution
======================================================================
Hybrid off/def role system (Feb 22 2026):
  players.archetype    = offensive role (15 archetypes, Claude Haiku)
  players.defensive_tag = defensive role (5 labels, deterministic thresholds)

Classifies active NBA players into 15 offensive archetypes via Claude Haiku.
Assigns defensive_tag via _assign_defensive_tag() — no Claude API needed.
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

# Load .env so ANTHROPIC_API_KEY is available before claude_client checks os.getenv()
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from utils.claude_client import get_claude_analysis, HAIKU_MODEL
from utils.claude_prompts import ARCHETYPE_SYSTEM_PROMPT as SYSTEM_PROMPT_ARCHETYPE

# Offensive role archetypes only — what offensive role does this player fill?
# Defensive role is tracked separately in players.defensive_tag (see _assign_defensive_tag).
# PERIMETER_HAWK, RIM_GUARDIAN, SWITCHABLE_ANCHOR, HUSTLE_DISRUPTOR removed from here;
# they now live in defensive_tag so every player has BOTH an offensive AND defensive role.
VALID_ARCHETYPES = {
    'HELIOCENTRIC_MAESTRO', 'SLASHING_CREATOR', 'JUMBO_FACILITATOR', 'SNIPER_ELITE',
    'TWO_LEVEL_SCORER', 'ISO_ASSASSIN', 'WARRIOR_BIG', 'STRETCH_BIG', 'ROLL_MAN',
    'HUB_BIG', 'ENERGY_BIG', 'CUTTER_SPECIALIST', 'CONNECTOR', 'FACILITATOR', 'GENERALIST'
}

# Defensive role values — written to players.defensive_tag by _assign_defensive_tag()
VALID_DEFENSIVE_TAGS = {
    'PERIMETER_HAWK', 'RIM_GUARDIAN', 'SWITCHABLE_ANCHOR', 'HUSTLE_DISRUPTOR',
    'WEAK_LINK', None
}

VALID_DEFENSE = {'PAINT_PACK', 'PERIMETER', 'BLITZ', 'FUNNEL', 'NEUTRAL'}
VALID_OFFENSE = {'MOTION', 'ISO_HEAVY', 'HALF_COURT', 'PACE_PUSH', 'BALANCED'}

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
            AVG(minutes) as minutes, AVG(oreb) as oreb
        FROM player_game_logs
        WHERE player_id = ? AND game_date >= ?
    """
    cur = conn.cursor()
    cur.execute(query, (player_id, cutoff_date))
    row = cur.fetchone()
    if row and row[0] is not None:
        return {
            'pts': row[0], 'ast': row[1], 'reb': row[2], 'stl': row[3], 'blk': row[4],
            'fga': row[5], 'fg3a': row[6], 'fta': row[7], 'minutes': row[8],
            'oreb': row[9] or 0.0,
        }
    return None


def get_player_season_advanced(conn, player_name: str) -> dict | None:
    """Season-level advanced stats from player_season_averages_bdl.
    100% coverage (535 players). Single row query per player.
    Returns: usg_pct, ast_pct, ast_to, off_rating, def_rating — the key discriminators
    that resolve HELIOCENTRIC vs SLASHING vs ISO close calls."""
    import json
    row = conn.execute(
        """SELECT stats_json FROM player_season_averages_bdl
           WHERE player_name = ? AND category = 'general' AND stat_type = 'advanced'
           LIMIT 1""",
        (player_name,)
    ).fetchone()
    if not row or not row[0]:
        return None
    try:
        data = json.loads(row[0])
        stats = data.get('stats', data)
        return {k: stats.get(k) for k in
                ('usg_pct', 'ast_pct', 'ast_to', 'off_rating', 'def_rating')}
    except Exception:
        return None


def _format_example(name, position, team, synergy_data, l10_data, season_data, target_archetype):
    """Format one DB-pulled player into a few-shot example line."""
    synergy_line = ""
    if synergy_data:
        parts = [f"{r[0]}: {r[1]:.1f}%" for r in synergy_data[:3]]
        synergy_line = "Synergy: " + " | ".join(parts)

    season_line = ""
    if season_data:
        parts = []
        if season_data.get('usg_pct') is not None:  parts.append(f"USG {season_data['usg_pct']:.1%}")
        if season_data.get('ast_pct') is not None:  parts.append(f"AST% {season_data['ast_pct']:.1%}")
        if season_data.get('ast_to') is not None:   parts.append(f"A/TO {season_data['ast_to']:.2f}")
        if season_data.get('off_rating') is not None: parts.append(f"OFF {season_data['off_rating']:.0f}")
        if parts:
            season_line = "Season: " + " | ".join(parts)

    l21_line = ""
    if l10_data:
        fga = max(l10_data.get('fga', 1) or 1, 1)
        l21_line = (f"L21: PTS {l10_data['pts']:.1f} | AST {l10_data['ast']:.1f} | STL {l10_data['stl']:.1f} | "
                    f"Ratios: FTA/FGA {l10_data.get('fta',0)/fga:.2f} | "
                    f"3PA/FGA {l10_data.get('fg3a',0)/fga:.2f}")

    lines = [f"Player: {name} | {position} | {team}"]
    if synergy_line: lines.append(synergy_line)
    if season_line:  lines.append(season_line)
    if l21_line:     lines.append(l21_line)
    lines.append(f"Output: {target_archetype}")
    return "\n".join(lines)


def build_archetype_system_prompt(conn) -> str:
    """Build ARCHETYPE_SYSTEM_PROMPT with DB-verified few-shot examples.

    Queries ludi.db for 3 canonical OFFENSIVE archetype representatives:
      1. HELIOCENTRIC_MAESTRO — highest-scoring confirmed HELI player with P&R synergy
      2. SLASHING_CREATOR    — highest FTA/FGA confirmed SLASHING player with drive synergy
      3. CONNECTOR           — highest-AST role player (replaces PERIMETER_HAWK — now in defensive_tag)

    Built ONCE per weekly run before the player loop — same string passed to all
    535 calls so Anthropic prompt caching still fires (identical system prompt).
    Never uses AI training data for team/player assignments: always from ludi.db.
    """
    from utils.claude_prompts import ARCHETYPE_SYSTEM_PROMPT

    examples = []

    # ── Example 1: HELIOCENTRIC_MAESTRO ──────────────────────────────────
    row = conn.execute("""
        SELECT p.player_id, p.name, p.position, p.team
        FROM players p
        WHERE p.archetype = 'HELIOCENTRIC_MAESTRO' AND p.status = 'ACTIVE'
          AND EXISTS (SELECT 1 FROM player_synergy_playtypes WHERE player_name = p.name)
          AND EXISTS (SELECT 1 FROM player_season_averages_bdl
                      WHERE player_name = p.name AND category='general' AND stat_type='advanced')
          AND p.player_id IN (
              SELECT DISTINCT player_id FROM player_game_logs
              WHERE game_date >= date('now','-21 days'))
        ORDER BY (SELECT AVG(pts) FROM player_game_logs
                  WHERE player_id = p.player_id AND game_date >= date('now','-21 days')) DESC
        LIMIT 1
    """).fetchone()
    if row:
        pid, name, pos, team = row
        syn = get_player_synergy(conn, name)
        l10 = get_player_l10(conn, pid, 21)
        sea = get_player_season_advanced(conn, name)
        examples.append(_format_example(name, pos, team, syn, l10, sea, 'HELIOCENTRIC_MAESTRO'))

    # ── Example 2: SLASHING_CREATOR ──────────────────────────────────────
    row = conn.execute("""
        SELECT p.player_id, p.name, p.position, p.team
        FROM players p
        JOIN player_game_logs pgl ON p.player_id = pgl.player_id
        WHERE p.archetype = 'SLASHING_CREATOR' AND p.status = 'ACTIVE'
          AND pgl.game_date >= date('now','-21 days')
          AND pgl.fga > 0
          AND EXISTS (SELECT 1 FROM player_synergy_playtypes WHERE player_name = p.name)
        GROUP BY p.player_id
        HAVING COUNT(DISTINCT pgl.game_id) >= 5
        ORDER BY AVG(pgl.fta) / MAX(AVG(pgl.fga), 1) DESC
        LIMIT 1
    """).fetchone()
    if row:
        pid, name, pos, team = row
        syn = get_player_synergy(conn, name)
        l10 = get_player_l10(conn, pid, 21)
        sea = get_player_season_advanced(conn, name)
        examples.append(_format_example(name, pos, team, syn, l10, sea, 'SLASHING_CREATOR'))

    # ── Example 3: CONNECTOR ──────────────────────────────────────────────
    # PERIMETER_HAWK removed (now lives in defensive_tag, not archetype).
    # CONNECTOR replaces it as the 3rd example — secondary ball-handler archetype.
    row = conn.execute("""
        SELECT p.player_id, p.name, p.position, p.team
        FROM players p
        JOIN player_game_logs pgl ON p.player_id = pgl.player_id
        WHERE p.archetype = 'CONNECTOR' AND p.status = 'ACTIVE'
          AND pgl.game_date >= date('now','-21 days')
          AND EXISTS (SELECT 1 FROM player_synergy_playtypes WHERE player_name = p.name)
        GROUP BY p.player_id
        HAVING COUNT(DISTINCT pgl.game_id) >= 5
        ORDER BY AVG(pgl.ast) DESC
        LIMIT 1
    """).fetchone()
    if row:
        pid, name, pos, team = row
        syn = get_player_synergy(conn, name)
        l10 = get_player_l10(conn, pid, 21)
        sea = get_player_season_advanced(conn, name)
        examples.append(_format_example(name, pos, team, syn, l10, sea, 'CONNECTOR'))

    examples_block = "\n\n".join(examples) if examples else "(no canonical examples available this run)"
    return ARCHETYPE_SYSTEM_PROMPT.format(examples_block=examples_block)


def build_archetype_prompt(name, position, team, synergy_data, shot_data, l10_data, current_archetype, season_data=None):
    """Build the user prompt for archetype classification.

    Prompt budget: ~15-20 lines per player (BERT Pattern 4 token discipline).
    Synergy capped at top 6 — rows 7-11 are noise at <5% freq.
    Season block injects key discriminators: USG%, AST%, A/TO, OFF/DEF ratings.
    Ratios block (FTA/FGA, 3PA/FGA, AST/FGA) derived from L21 — no extra DB query.
    at_rim_freq / corner_3_freq stored as fractions (0.0-1.0) → displayed as %.
    """
    synergy_block = ""
    if synergy_data:
        # Cap at top 6 playtypes (BERT Pattern 4: token budget discipline)
        for row in synergy_data[:6]:
            ppp_val = row[2] if row[2] is not None else 0.0
            score_val = row[3] if row[3] is not None else 0.0
            synergy_block += f"  {row[0]}: {row[1]:.1f}% | {ppp_val:.2f} PPP | {score_val:.0f}% score\n"
    else:
        synergy_block = "  No Synergy data available\n"

    shot_block = ""
    if shot_data:
        # at_rim_freq / corner_3_freq are fractions (0.0-1.0) — multiply by 100 for display
        at_rim_pct = (shot_data['at_rim_freq'] or 0) * 100
        corner3_pct = (shot_data['corner_3_freq'] or 0) * 100
        shot_block = f"Shot profile: at-rim {at_rim_pct:.0f}% | corner-3 {corner3_pct:.0f}% | quality {shot_data['shot_quality_avg']:.3f}\n"
    else:
        shot_block = "No shot quality data\n"

    # Computed ratios from L21 (no extra query, directly maps to Gate 2 thresholds)
    ratio_line = ""
    if l10_data:
        fga = max(l10_data.get('fga', 1) or 1, 1)
        ratio_line = (f"Ratios: FTA/FGA {l10_data.get('fta', 0)/fga:.2f} | "
                      f"3PA/FGA {l10_data.get('fg3a', 0)/fga:.2f} | "
                      f"AST/FGA {l10_data.get('ast', 0)/fga:.2f}")

    # Season-level advanced stats (1 compact line — key discriminators)
    season_line = ""
    if season_data:
        parts = []
        if season_data.get('usg_pct') is not None:    parts.append(f"USG {season_data['usg_pct']:.1%}")
        if season_data.get('ast_pct') is not None:    parts.append(f"AST% {season_data['ast_pct']:.1%}")
        if season_data.get('ast_to') is not None:     parts.append(f"A/TO {season_data['ast_to']:.2f}")
        if season_data.get('off_rating') is not None: parts.append(f"OFF {season_data['off_rating']:.0f}")
        if season_data.get('def_rating') is not None: parts.append(f"DEF {season_data['def_rating']:.0f}")
        if parts:
            season_line = "Season: " + " | ".join(parts)

    l10_block = ""
    if l10_data:
        l10_block = (f"L21: PTS {l10_data['pts']:.1f} | AST {l10_data['ast']:.1f} | "
                     f"REB {l10_data['reb']:.1f} | STL {l10_data['stl']:.1f} | "
                     f"BLK {l10_data['blk']:.1f} | FGA {l10_data['fga']:.1f} | MIN {l10_data['minutes']:.0f}")
    else:
        l10_block = "No L21 box data"

    return f"""Player: {name} | {position} | {team}

Synergy (top 6 playtypes, high freq first):
{synergy_block}{shot_block}
{season_line}
{l10_block}
{ratio_line}
Current DB archetype: {current_archetype or 'NULL'}"""


def validate_archetype(result, synergy_data, shot_data, l10_data=None, position=None):
    """
    Two-gate validation:
    Gate 1 — Schema: result must be in VALID_ARCHETYPES
    Gate 2 — Data sanity: thresholds using synergy, shot quality, L21 box stats, and position

    position: 'G', 'F', 'C', 'UNK', or None — used for position-aware archetype constraints.
    A center (C) classified as HELIOCENTRIC_MAESTRO must have P&R_BALL_HANDLER ≥ 10%;
    otherwise they are a scoring big (JUMBO_FACILITATOR or TWO_LEVEL_SCORER), not an orchestrator.

    l10_data keys: pts, ast, reb, stl, blk, fga, fg3a, fta, minutes, oreb
    synergy_dict keys: ISO, PR_BALL_HANDLER, PR_ROLL_MAN, SPOT_UP, POST_UP,
                       PUTBACK, CUT, TRANSITION, HANDOFF, OFF_SCREEN, MISC
    shot_data keys: at_rim_freq, corner_3_freq, shot_quality_avg
    """
    result_upper = result.strip().upper()

    # Gate 1: Schema validation
    if result_upper not in VALID_ARCHETYPES:
        return False, f"GATE1: {result_upper} not in VALID_ARCHETYPES"

    # Gate 2: Data sanity checks
    synergy_dict = {row[0]: row[1] for row in synergy_data} if synergy_data else {}
    # Helper aliases
    pts    = (l10_data or {}).get('pts', 0) or 0
    ast    = (l10_data or {}).get('ast', 0) or 0
    stl    = (l10_data or {}).get('stl', 0) or 0
    blk    = (l10_data or {}).get('blk', 0) or 0
    fga    = (l10_data or {}).get('fga', 1) or 1   # avoid div/0
    fg3a   = (l10_data or {}).get('fg3a', 0) or 0
    fta    = (l10_data or {}).get('fta', 0) or 0
    mins   = (l10_data or {}).get('minutes', 0) or 0
    oreb   = (l10_data or {}).get('oreb', 0) or 0
    fta_ratio = fta / fga
    has_synergy = bool(synergy_dict)

    if result_upper == 'HELIOCENTRIC_MAESTRO':
        # Primary creator: needs real scoring volume + ball-in-hand creation
        if l10_data and pts < 18.0:
            return False, f"GATE2: HELIOCENTRIC_MAESTRO but pts={pts:.1f} < 18"
        if has_synergy:
            iso_freq = synergy_dict.get('ISO', 0) or 0
            prh_freq = synergy_dict.get('PR_BALL_HANDLER', 0) or 0
            if iso_freq < 8 and prh_freq < 15:
                return False, (f"GATE2: HELIOCENTRIC_MAESTRO but ISO={iso_freq:.0f}% "
                               f"and P&R={prh_freq:.0f}% both low")
            # Position-aware: Centers require P&R_BALL_HANDLER ≥ 10% to be heliocentric.
            # A C with high scoring but POST_UP/PR_ROLL_MAN playtypes is a scoring big
            # (JUMBO_FACILITATOR or TWO_LEVEL_SCORER), not a guard-style orchestrator.
            # Jokic qualifies (P&R_BH ~25%). Embiid (P&R_BH=0%) does not.
            pos_norm = (position or '').upper()
            if pos_norm == 'C' and prh_freq < 10:
                return False, (f"GATE2: HELIOCENTRIC_MAESTRO but position=C and "
                               f"P&R_BH={prh_freq:.0f}% < 10% (scoring big, not orchestrator)")

    elif result_upper == 'ISO_ASSASSIN':
        # Isolation specialist: ISO ≥ 15% required
        iso_freq = synergy_dict.get('ISO', 0) or 0
        if has_synergy and iso_freq < 15.0:
            return False, f"GATE2: ISO_ASSASSIN but ISO freq={iso_freq:.1f}% < 15%"

    elif result_upper == 'SLASHING_CREATOR':
        # Drive-first: draws fouls at high rate + rim or ball-handler synergy
        if l10_data and fta_ratio < 0.28:
            return False, f"GATE2: SLASHING_CREATOR but FTA/FGA={fta_ratio:.2f} < 0.28"
        if has_synergy:
            # at_rim_freq is stored as fraction (0.0-1.0); threshold 0.25 = 25%
            at_rim = shot_data['at_rim_freq'] if shot_data else None
            prh = synergy_dict.get('PR_BALL_HANDLER', 0) or 0
            handoff = synergy_dict.get('HANDOFF', 0) or 0
            rim_ok = (at_rim is not None and at_rim >= 0.25) or (prh + handoff) >= 10
            if not rim_ok:
                rim_pct = f"{at_rim*100:.0f}%" if at_rim is not None else "N/A"
                return False, (f"GATE2: SLASHING_CREATOR but at_rim={rim_pct}<25% and "
                               f"PR_BALL_HANDLER+HANDOFF={prh+handoff:.0f}% < 10%")

    elif result_upper == 'JUMBO_FACILITATOR':
        # Big-man playmaker (Jokic/Sabonis/Embiid type): strong AST + big-man creation
        # Threshold: 4.0 AST (Embiid 4.3 qualifies; guards who sneak in will fail synergy check)
        if l10_data and ast < 4.0:
            return False, f"GATE2: JUMBO_FACILITATOR but AST={ast:.1f} < 4.0"
        if has_synergy:
            prh_freq = synergy_dict.get('PR_BALL_HANDLER', 0) or 0
            post_freq = synergy_dict.get('POST_UP', 0) or 0
            iso_freq  = synergy_dict.get('ISO', 0) or 0
            pos_norm  = (position or '').upper()
            # C players: qualify via POST_UP ≥ 15% OR PR_BH ≥ 10% (Embiid: POST=21%, ISO=12%)
            # Non-C: must have P&R_BALL_HANDLER presence (guard/forward playmaker)
            if pos_norm == 'C':
                if prh_freq < 10 and post_freq < 15 and iso_freq < 8:
                    return False, (f"GATE2: JUMBO_FACILITATOR (C) but P&R_BH={prh_freq:.0f}% "
                                   f"POST_UP={post_freq:.0f}% ISO={iso_freq:.0f}% all low")
            else:
                if prh_freq < 15 and post_freq < 10 and iso_freq < 8:
                    return False, (f"GATE2: JUMBO_FACILITATOR but P&R={prh_freq:.0f}% "
                                   f"POST_UP={post_freq:.0f}% ISO={iso_freq:.0f}% all low")

    elif result_upper == 'SNIPER_ELITE':
        # Catch-and-shoot specialist: SPOT_UP ≥ 25%
        spot_up_freq = synergy_dict.get('SPOT_UP', 0) or 0
        if has_synergy and spot_up_freq < 25.0:
            return False, f"GATE2: SNIPER_ELITE but SPOT_UP freq={spot_up_freq:.1f}% < 25%"

    elif result_upper == 'TWO_LEVEL_SCORER':
        # Multi-zone scorer: scores at rim AND from perimeter
        if l10_data and pts < 12.0:
            return False, f"GATE2: TWO_LEVEL_SCORER but pts={pts:.1f} < 12"
        if l10_data and fg3a < 1.0:
            return False, f"GATE2: TWO_LEVEL_SCORER but fg3a={fg3a:.1f} < 1.0 (no perimeter)"
        # at_rim_freq stored as fraction (0.0-1.0); threshold 0.20 = 20%
        if shot_data and shot_data.get('at_rim_freq', 1.0) < 0.20:
            return False, (f"GATE2: TWO_LEVEL_SCORER but at_rim_freq="
                           f"{shot_data['at_rim_freq']*100:.0f}% < 20% (no rim presence)")

    elif result_upper == 'WARRIOR_BIG':
        # Physical bruiser: transition+putback synergy OR fouls drawn + offensive boards
        if has_synergy:
            putback = synergy_dict.get('PUTBACK', 0) or 0
            trans   = synergy_dict.get('TRANSITION', 0) or 0
            if (putback + trans) < 20:
                # Fallback: physical big who draws fouls and crashes boards
                if l10_data and not (fta_ratio >= 0.35 and oreb >= 1.5):
                    return False, (f"GATE2: WARRIOR_BIG but PUTBACK+TRANSITION="
                                   f"{putback+trans:.0f}% and FTA/FGA={fta_ratio:.2f}, "
                                   f"OREB={oreb:.1f} both below threshold")

    elif result_upper == 'STRETCH_BIG':
        # Big who shoots from perimeter: SPOT_UP or corner-3 or high fg3a rate
        # corner_3_freq stored as fraction (0.0-1.0); threshold 0.20 = 20%
        spot_up = synergy_dict.get('SPOT_UP', 0) or 0
        corner3 = (shot_data['corner_3_freq'] if shot_data else 0) or 0
        if has_synergy and spot_up < 20 and corner3 < 0.20 and fg3a < 2.5:
            return False, (f"GATE2: STRETCH_BIG but SPOT_UP={spot_up:.0f}%, "
                           f"corner3={corner3*100:.0f}%, fg3a={fg3a:.1f} all low")

    elif result_upper == 'ROLL_MAN':
        # P&R roll specialist: PR_ROLL_MAN ≥ 20%
        roll_freq = synergy_dict.get('PR_ROLL_MAN', 0) or 0
        if has_synergy and roll_freq < 20.0:
            return False, f"GATE2: ROLL_MAN but PR_ROLL_MAN freq={roll_freq:.1f}% < 20%"

    elif result_upper == 'HUB_BIG':
        # Passing-first big: moderate AST (Draymond 3.5-5), low shot volume
        if l10_data and ast < 3.5:
            return False, f"GATE2: HUB_BIG but AST={ast:.1f} < 3.5"
        if l10_data and fga > 9.0:
            return False, f"GATE2: HUB_BIG but FGA={fga:.1f} > 9 (too much shot volume)"

    elif result_upper == 'ENERGY_BIG':
        # Hustle role: offensive board presence + limited shot creation
        if l10_data and fga > 9.0:
            return False, f"GATE2: ENERGY_BIG but FGA={fga:.1f} > 9 (too much shot volume)"
        if l10_data and mins < 12.0:
            return False, f"GATE2: ENERGY_BIG but MIN={mins:.0f} < 12 (insufficient role)"
        putback = synergy_dict.get('PUTBACK', 0) or 0
        # OREB ≥ 1.5 threshold (uses DB oreb data, independent of synergy coverage)
        if has_synergy and putback < 10 and oreb < 1.5:
            return False, (f"GATE2: ENERGY_BIG but PUTBACK={putback:.0f}% "
                           f"and OREB={oreb:.1f} both low")

    # NOTE: PERIMETER_HAWK, RIM_GUARDIAN, SWITCHABLE_ANCHOR, HUSTLE_DISRUPTOR are no longer
    # valid offensive archetypes — they live in players.defensive_tag. Gate 1 rejects
    # them before reaching here, so no Gate 2 branches are needed.

    elif result_upper == 'CUTTER_SPECIALIST':
        # Off-ball cutter: CUT ≥ 20%
        cut_freq = synergy_dict.get('CUT', 0) or 0
        if has_synergy and cut_freq < 20.0:
            return False, f"GATE2: CUTTER_SPECIALIST but CUT freq={cut_freq:.1f}% < 20%"

    elif result_upper == 'CONNECTOR':
        # Secondary ball-handler pushing pace: some playmaking + transition role
        # 2.5 AST floor (not a pure point guard, but moves the ball)
        if l10_data and ast < 2.5:
            return False, f"GATE2: CONNECTOR but AST={ast:.1f} < 2.5"
        trans = synergy_dict.get('TRANSITION', 0) or 0
        # Threshold lowered 8% → 5%: primary guards with P&R_BH ≥ 25% often have
        # low TRANSITION% (run half-court sets) but are clearly connectors (e.g. Jalen Green 54% P&R)
        if has_synergy and trans < 5:
            return False, f"GATE2: CONNECTOR but TRANSITION={trans:.0f}% < 5%"

    elif result_upper == 'FACILITATOR':
        # Pure passer: meaningful AST + active in ball-movement playtypes
        # 4.5 AST — lower than JUMBO_FACILITATOR (5) since these are role passers, not stars
        if l10_data and ast < 4.5:
            return False, f"GATE2: FACILITATOR but AST={ast:.1f} < 4.5"
        if has_synergy:
            handoff = synergy_dict.get('HANDOFF', 0) or 0
            prh     = synergy_dict.get('PR_BALL_HANDLER', 0) or 0
            if handoff < 8 and prh < 12:
                return False, (f"GATE2: FACILITATOR but HANDOFF={handoff:.0f}% "
                               f"and P&R={prh:.0f}% both low")

    # GENERALIST: no Gate 2 — valid fallback for any player

    return True, "PASS"


def _gate2_fallback(rejected_arch: str, synergy_data, shot_data, l10_data,
                    position: str | None = None) -> str | None:
    """
    Deterministic fallback: after Gate 2 rejects Claude's proposal, try the natural
    alternative offensive archetype before defaulting to GENERALIST.
    No Claude call — pure heuristic based on synergy + box stats + position.

    Returns a valid offensive archetype string, or None (caller uses GENERALIST).
    NOTE: PERIMETER_HAWK, RIM_GUARDIAN, SWITCHABLE_ANCHOR, HUSTLE_DISRUPTOR are NOT
    valid offensive archetypes — never return them here. Defensive identity is handled
    separately by _assign_defensive_tag().

    Position-aware chains:
      C  + HELIOCENTRIC rejected (no P&R_BH) → JUMBO_FACILITATOR → TWO_LEVEL_SCORER
      G/F + HELIOCENTRIC rejected (pts<18)   → CONNECTOR (high AST + P&R_BH)
      PERIMETER_HAWK (Claude suggested)      → offensive label based on synergy/pts
      SLASHING_CREATOR + FTA/FGA < 0.28     → TWO_LEVEL_SCORER
      JUMBO_FACILITATOR + AST < 4.0         → HELIOCENTRIC_MAESTRO (scoring big)
    """
    synergy_dict = {r[0]: r[1] for r in synergy_data} if synergy_data else {}
    spot_up  = synergy_dict.get('SPOT_UP', 0) or 0
    trans    = synergy_dict.get('TRANSITION', 0) or 0
    prh      = synergy_dict.get('PR_BALL_HANDLER', 0) or 0
    post_up  = synergy_dict.get('POST_UP', 0) or 0
    iso      = synergy_dict.get('ISO', 0) or 0
    roll     = synergy_dict.get('PR_ROLL_MAN', 0) or 0

    pts   = (l10_data or {}).get('pts', 0) or 0
    ast   = (l10_data or {}).get('ast', 0) or 0
    stl   = (l10_data or {}).get('stl', 0) or 0
    fga   = max((l10_data or {}).get('fga', 1) or 1, 1)
    fta   = (l10_data or {}).get('fta', 0) or 0
    fg3a  = (l10_data or {}).get('fg3a', 0) or 0
    at_rim = (shot_data or {}).get('at_rim_freq', None)  # fraction 0.0-1.0

    pos_norm  = (position or '').upper()
    is_center = pos_norm == 'C'

    if rejected_arch == 'HELIOCENTRIC_MAESTRO':
        if is_center:
            # C rejected from HELIOCENTRIC — typically no P&R_BH (POST_UP/ROLL/ISO big scorer).
            # Route to big-man archetypes: JUMBO_FACILITATOR first, then TWO_LEVEL_SCORER.
            if ast >= 4.0 and (prh >= 8 or post_up >= 10 or iso >= 8):
                return 'JUMBO_FACILITATOR'
            if pts >= 14:
                return 'TWO_LEVEL_SCORER'
        else:
            # G/F rejected (typically pts < 18). Route to CONNECTOR if real playmaking exists.
            if ast >= 5 and (trans >= 5 or prh >= 20):
                return 'CONNECTOR'
            if ast >= 3.5 and prh >= 25:
                return 'CONNECTOR'

    elif rejected_arch in ('PERIMETER_HAWK', 'SWITCHABLE_ANCHOR', 'HUSTLE_DISRUPTOR', 'RIM_GUARDIAN'):
        # Claude suggested a defensive archetype — Gate 1 already rejects these as offensive
        # archetypes. Route to the correct offensive label based on stats/synergy.
        # (Defensive identity will be assigned separately by _assign_defensive_tag().)
        if pts >= 17:
            if prh >= 20 and ast >= 5:
                return 'HELIOCENTRIC_MAESTRO'
            if fg3a >= 3.0 or spot_up >= 20:
                return 'TWO_LEVEL_SCORER'
            return 'TWO_LEVEL_SCORER'       # Default for high-scoring wing/big
        if spot_up >= 25:
            return 'SNIPER_ELITE'           # Catch-and-shoot specialist
        if prh >= 20:
            return 'CONNECTOR'              # Secondary ball-handler
        if rejected_arch == 'RIM_GUARDIAN':
            # Centers with rim presence but not qualifying as RIM_GUARDIAN offensively
            if roll >= 20:
                return 'ROLL_MAN'
            return 'ENERGY_BIG'             # Default for rim-anchored bigs

    elif rejected_arch == 'SLASHING_CREATOR':
        # Failed FTA/FGA threshold — check for multi-zone scoring pattern instead.
        if pts >= 12 and fg3a >= 1.0:
            rim_ok = (at_rim is not None and at_rim >= 0.20) or (prh >= 10)
            if rim_ok:
                return 'TWO_LEVEL_SCORER'

    elif rejected_arch == 'JUMBO_FACILITATOR':
        # Failed AST or synergy threshold.
        # C: don't route back to HELIOCENTRIC (position blocked) — use TWO_LEVEL_SCORER instead.
        # G/F: if high-scoring with creation plays, HELIOCENTRIC may fit.
        if is_center:
            if pts >= 12 and (post_up >= 10 or roll >= 15 or iso >= 8):
                return 'TWO_LEVEL_SCORER'
            if roll >= 20:
                return 'ROLL_MAN'
        else:
            if pts >= 18 and (iso >= 8 or prh >= 8):
                return 'HELIOCENTRIC_MAESTRO'

    elif rejected_arch == 'SNIPER_ELITE':
        # Failed SPOT_UP threshold — if ball-handling present, reclassify as CONNECTOR
        if ast >= 2.5 and prh >= 10:
            return 'CONNECTOR'
        # Otherwise fall through to GENERALIST

    elif rejected_arch == 'CONNECTOR':
        # Failed AST/TRANSITION — if SPOT_UP dominant, reclassify as SNIPER_ELITE
        if spot_up >= 25:
            return 'SNIPER_ELITE'

    elif rejected_arch in ('WARRIOR_BIG', 'ENERGY_BIG'):
        # Failed rim/putback thresholds but center with roll presence → ROLL_MAN
        if is_center and roll >= 15 and (at_rim is None or at_rim >= 0.30):
            return 'ROLL_MAN'

    return None  # No clean fallback — caller uses GENERALIST


def _assign_defensive_tag(synergy_data, shot_data, l10_data) -> str | None:
    """
    Deterministic defensive role assignment — no Claude needed.
    Runs after offensive archetype is finalized. Writes to players.defensive_tag.

    Defensive role hierarchy (checked in order, first match wins):
      PERIMETER_HAWK   — elite perimeter defender: STL ≥ 0.9 + perimeter offensive role
      RIM_GUARDIAN     — elite rim protector: at_rim ≥ 50% + BLK ≥ 1.0
      SWITCHABLE_ANCHOR — versatile two-way defender: STL+BLK ≥ 1.2 (not pure rim/perimeter)
      HUSTLE_DISRUPTOR  — chaos/energy defender: STL+BLK ≥ 1.0 + 3+ synergy playtypes
      WEAK_LINK        — poor defender (existing logic preserved)
      None             — average/unknown defender

    Thresholds are data-driven from 2025-26 season distribution.
    at_rim_freq is stored as fraction (0.0-1.0) in player_shot_quality.
    """
    stl  = (l10_data or {}).get('stl', 0) or 0
    blk  = (l10_data or {}).get('blk', 0) or 0
    synergy_dict = {r[0]: r[1] for r in synergy_data} if synergy_data else {}
    has_synergy  = bool(synergy_dict)
    spot_up      = synergy_dict.get('SPOT_UP', 0) or 0
    at_rim       = (shot_data or {}).get('at_rim_freq', None)  # fraction 0.0-1.0
    n_playtypes  = len(synergy_data) if synergy_data else 0

    # PERIMETER_HAWK: elite perimeter defender who also contributes on perimeter offensively.
    # Requires STL ≥ 0.9 + either SPOT_UP presence in synergy OR no synergy data (can't disprove).
    if stl >= 0.9:
        if not has_synergy or spot_up > 0:
            return 'PERIMETER_HAWK'

    # RIM_GUARDIAN: interior anchor who challenges shots at the rim.
    # at_rim_freq ≥ 0.50 means ≥50% of shot attempts come at the rim (rim-dominant offensively too).
    if at_rim is not None and at_rim >= 0.50 and blk >= 1.0:
        return 'RIM_GUARDIAN'

    # SWITCHABLE_ANCHOR: versatile defender who neither specializes at rim nor perimeter.
    # Must clear combined STL+BLK ≥ 1.2 but not qualify as a pure specialist above.
    if (stl + blk) >= 1.2:
        return 'SWITCHABLE_ANCHOR'

    # HUSTLE_DISRUPTOR: high-activity defender across multiple fronts.
    # Lower combined threshold (1.0) but requires multi-playtype presence (chaos agent).
    if (stl + blk) >= 1.0 and n_playtypes >= 3:
        return 'HUSTLE_DISRUPTOR'

    # WEAK_LINK: existing WEAK_LINK logic is applied upstream in module_e — preserve NULL here.
    # classify_archetypes.py does NOT assign WEAK_LINK (that's Module E's domain).
    # Return None = average/unknown defender.
    return None


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
    parser.add_argument("--compare", action="store_true", help="Side-by-side: Gate2(current DB label) vs Claude+Gate2 proposal")
    parser.add_argument("--limit", type=int, default=None, help="Process only N players (for testing)")
    parser.add_argument("--window-days", type=int, default=21, help="Window for active players (default: 21)")
    parser.add_argument("--min-games", type=int, default=3, help="Minimum games for active players (default: 3)")
    parser.add_argument("--db-path", default="ludi.db", help="Path to SQLite database")
    args = parser.parse_args()
    
    conn = get_db_connection(args.db_path)

    # Build system prompt ONCE from live DB data (DB-verified examples, not training memory).
    # Identical string passed to all ~535 calls → Anthropic prompt caching fires after player 1.
    system_prompt = build_archetype_system_prompt(conn)

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
        season_data = get_player_season_advanced(conn, name)

        # ── Gate 2 audit on current DB label (no Claude needed) ──────────────
        # Always run this so --compare mode and the Claude-unavailable fallback
        # both have current_gate2_pass / current_gate2_reason available.
        if current_archetype:
            curr_valid, curr_reason = validate_archetype(
                current_archetype, synergy_data, shot_data, l10_data, position=position
            )
            current_gate2 = "PASS" if curr_valid else f"FAIL({curr_reason})"
        else:
            curr_valid, curr_reason = False, "no current archetype"
            current_gate2 = "NULL"

        # ── Gate 1: Claude Haiku classification ───────────────────────────────
        prompt = build_archetype_prompt(
            name, position, team, synergy_data, shot_data, l10_data,
            current_archetype, season_data=season_data
        )

        result = get_claude_analysis(
            prompt,
            system_prompt,     # built once from DB — DB-verified examples, not training memory
            HAIKU_MODEL,
            temperature=0.0,   # deterministic — classification must be consistent across weekly batch
            max_tokens=20
        )

        claude_unavailable = not result
        if claude_unavailable:
            # Fallback: validate current DB label with Gate 2 and use it if it passes,
            # otherwise downgrade to GENERALIST. This keeps the script functional even
            # when the Anthropic API is unreachable.
            fallback = current_archetype if (current_archetype and curr_valid) else 'GENERALIST'
            print(f"[FALLBACK→{fallback}] {name}: Claude unavailable | Gate2(current): {current_gate2}")
            result = fallback
        else:
            result = result.strip()
            # BERT Pattern 8: log parse failures so we can tune the prompt over time
            if result.upper() not in VALID_ARCHETYPES:
                print(f"[PARSE FAIL] {name}: Claude returned '{result}' (not in VALID_ARCHETYPES) → will fall to GENERALIST")

        # ── Gate 2: validate Claude's (or fallback) proposal ─────────────────
        valid, reason = validate_archetype(result, synergy_data, shot_data, l10_data, position=position)

        if not valid:
            # Gate 2 rejected — try deterministic fallback before defaulting to GENERALIST.
            # _gate2_fallback() uses position + synergy + box stats to route to the next
            # most appropriate archetype (e.g. C+HELIOCENTRIC → JUMBO_FACILITATOR,
            # PERIMETER_HAWK+low_STL → SNIPER_ELITE, HELIOCENTRIC+pts<18 → CONNECTOR).
            fallback_arch = _gate2_fallback(result, synergy_data, shot_data, l10_data, position=position)
            if fallback_arch:
                fb_valid, fb_reason = validate_archetype(fallback_arch, synergy_data, shot_data, l10_data, position=position)
                if fb_valid:
                    if args.compare or not claude_unavailable:
                        print(f"[GATE2 FALLBACK] {name}: {result}({reason}) → {fallback_arch}")
                    result = fallback_arch
                    valid = True
                else:
                    if args.compare or not claude_unavailable:
                        print(f"[GATE2 REJECT→GENERALIST] {name}: {result} | {reason} | fallback {fallback_arch} also failed: {fb_reason}")
                    result = 'GENERALIST'
                    valid = True
            else:
                if args.compare or not claude_unavailable:
                    print(f"[GATE2 REJECT→GENERALIST] {name}: {result} | {reason}")
                result = 'GENERALIST'
                valid = True  # GENERALIST always passes

        # ── Compare mode: side-by-side output ────────────────────────────────
        if args.compare:
            claude_label = "N/A(fallback)" if claude_unavailable else result
            action = "NO CHANGE" if result == current_archetype else f"→{result}"
            print(
                f"[COMPARE] {name:<28} | "
                f"DB:{current_archetype or 'NULL'}({current_gate2}) | "
                f"Claude:{claude_label} | "
                f"Action:{action}"
            )

        if result == 'GENERALIST':
            generalist_count += 1

        # ── Defensive tag: always recompute (hybrid off/def system) ──────────
        # Runs for every player regardless of whether offensive archetype changed.
        # defensive_tag is independent of archetype — a GENERALIST can be PERIMETER_HAWK.
        def_tag = _assign_defensive_tag(synergy_data, shot_data, l10_data)

        if result == current_archetype:
            unchanged += 1
            if not args.compare:
                print(f"[UNCHANGED] {name}: {result} | def_tag={def_tag or 'NULL'}")
        else:
            changed += 1
            archetype_changes.append((name, current_archetype or 'NULL', result))
            if not args.compare:
                print(f"[CHANGE] {name}: {current_archetype or 'NULL'} -> {result} | def_tag={def_tag or 'NULL'}")

            if not args.dry_run:
                cur = conn.cursor()
                cur.execute(
                    "UPDATE players SET archetype = ?, updated_at = datetime('now') WHERE player_id = ?",
                    (result, player_id)
                )

        # Always write defensive_tag (even for unchanged offensive archetype)
        if not args.dry_run:
            cur = conn.cursor()
            cur.execute(
                "UPDATE players SET defensive_tag = ? WHERE player_id = ?",
                (def_tag, player_id)
            )
    
    # ── Post-process cleanup: reset stale / invalid archetypes ───────────────
    # Players injured/inactive during this run (< min_games threshold) may retain
    # stale archetypes from before system migrations:
    #   - Defensive archetypes (PERIMETER_HAWK etc.) → removed from VALID_ARCHETYPES Feb 22 2026
    #   - TWO_WAY_WING → mid-session approach rolled back Feb 22 2026
    # Since Gate 1 rejects all of these, this sweep is safe and idempotent.
    stale_players = conn.execute(
        "SELECT player_id, name, archetype FROM players WHERE archetype IN "
        "('PERIMETER_HAWK','RIM_GUARDIAN','SWITCHABLE_ANCHOR','HUSTLE_DISRUPTOR','TWO_WAY_WING')"
    ).fetchall()
    if stale_players:
        print(f"\n[CLEANUP] {len(stale_players)} players skipped this run still have "
              f"legacy defensive archetypes → attempting 60d classification, then transferring defensive_tag")
        _VALID_DEF_TAGS = {'PERIMETER_HAWK', 'RIM_GUARDIAN', 'SWITCHABLE_ANCHOR', 'HUSTLE_DISRUPTOR'}
        for pid, pname, parch in stale_players:
            # Step 1: Attempt offensive classification with 60-day window data.
            # These players have synergy + season data but < min_games in the normal window.
            # Many (e.g. Jalen Williams) have full offensive profiles — don't default to GENERALIST.
            position_row = conn.execute(
                "SELECT position FROM players WHERE player_id = ?", (pid,)
            ).fetchone()
            position_60d = (position_row[0] if position_row else None)
            synergy_60d = get_player_synergy(conn, pname)
            shot_60d    = get_player_shot_quality(conn, pid)
            l10_60d     = get_player_l10(conn, pid, window_days=60)   # extended window

            # Use _gate2_fallback() to deterministically find the best offensive label.
            # Doesn't require Claude — uses synergy + box stats only.
            # If the primary fallback fails Gate 2 (e.g. HELIOCENTRIC_MAESTRO pts<18 by slim margin),
            # try a secondary fallback using the rejected arch as the new starting point —
            # this lets the chain resolve: PERIMETER_HAWK→HELIOCENTRIC(fail)→CONNECTOR/TWO_LEVEL_SCORER.
            off_arch = _gate2_fallback(parch, synergy_60d, shot_60d, l10_60d, position=position_60d)
            fb_valid = False
            if off_arch:
                fb_valid, _ = validate_archetype(off_arch, synergy_60d, shot_60d, l10_60d,
                                                 position=position_60d)
                if not fb_valid:
                    # Primary fallback failed — try one more hop (e.g. HELIOCENTRIC → CONNECTOR)
                    off_arch2 = _gate2_fallback(off_arch, synergy_60d, shot_60d, l10_60d,
                                                position=position_60d)
                    if off_arch2:
                        fb2_valid, _ = validate_archetype(off_arch2, synergy_60d, shot_60d,
                                                          l10_60d, position=position_60d)
                        if fb2_valid:
                            off_arch = off_arch2
                            fb_valid = True
                    if not fb_valid:
                        off_arch = None  # both hops failed — fall to GENERALIST

            final_arch = off_arch or 'GENERALIST'

            # Step 2: Preserve defensive identity in defensive_tag.
            transferred_tag = parch if parch in _VALID_DEF_TAGS else None
            print(f"  {pname}: {parch} → {final_arch} | defensive_tag={transferred_tag or 'NULL'} "
                  f"(60d games: {l10_60d.get('games', 0) if l10_60d else 0})")
            archetype_changes.append((pname, parch, final_arch))
            changed += 1
            if not args.dry_run:
                cur = conn.cursor()
                # Only overwrite defensive_tag if current value is NULL or WEAK_LINK
                # (WEAK_LINK from _assign_defensive_tag on sparse data is less reliable
                # than the historical classification stored in the old archetype column).
                cur.execute(
                    """UPDATE players
                       SET archetype = ?,
                           defensive_tag = CASE
                             WHEN defensive_tag IS NULL OR defensive_tag = 'WEAK_LINK'
                             THEN ?
                             ELSE defensive_tag
                           END,
                           updated_at = datetime('now')
                       WHERE player_id = ?""",
                    (final_arch, transferred_tag, pid)
                )

    if not args.dry_run and (changed > 0 or stale_players):
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
    print(f"Hybrid off/def system: archetype=offensive role | defensive_tag=defensive role")
    
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
