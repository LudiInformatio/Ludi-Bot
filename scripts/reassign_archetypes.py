#!/usr/bin/env python3
"""
Ludi-Bot Archetype Re-assignment Script (V2)
=============================================
Re-calculates archetypes using FULL SEASON box score data as foundation,
enhanced by synergy playtypes when available.

Archetype Philosophy:
- Box scores determine BASE archetype (available for 500+ players)
- Synergy data REFINES the archetype (available for ~370 players)
- Thresholds based on actual 2025-26 NBA data percentiles

Usage:
    python scripts/reassign_archetypes.py          # Dry run (default)
    python scripts/reassign_archetypes.py --execute  # Actually update

Created: Feb 2, 2026
"""

import sqlite3
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

DB_PATH = "ludi.db"

# ============================================================================
# ARCHETYPE DEFINITIONS (Based on 2025-26 NBA Data Percentiles)
# ============================================================================
#
# Thresholds calibrated from actual player distributions:
# - PPG: Top tier 25+, High 18+, Mid 12+
# - APG: Elite 8+, High 6+, Good 4+
# - RPG: Elite 10+, High 7+, Good 5+
# - 3PM: Sniper 3+, Shooter 2+, Some 1+
# - BPG: Elite 1.5+, Good 1+
# - SPG: Elite 1.5+, Good 1+
# ============================================================================


def get_season_averages(conn, player_name):
    """Get full season box score averages (Oct 2025 - present)."""
    c = conn.cursor()

    c.execute('''
        SELECT
            AVG(pts), AVG(reb), AVG(ast), AVG(fg3m),
            AVG(stl), AVG(blk), AVG(tov), AVG(fga),
            AVG(fta), AVG(CAST(minutes AS REAL)), COUNT(*)
        FROM player_game_logs
        WHERE player_name = ?
        AND game_date >= '2025-10-01'
    ''', (player_name,))

    row = c.fetchone()
    if not row or row[10] < 5:  # Need at least 5 games
        return None

    pts, reb, ast, tpm, stl, blk, tov, fga, fta, mins, games = row

    # Estimate usage
    if mins and mins > 0:
        est_poss = mins * 0.85
        if est_poss > 0:
            usg = (fga + 0.44 * fta + tov) / est_poss
            usg = min(0.40, max(0.10, usg))
        else:
            usg = 0.20
    else:
        usg = 0.20

    return {
        'pts': pts or 0,
        'reb': reb or 0,
        'ast': ast or 0,
        'tpm': tpm or 0,
        'stl': stl or 0,
        'blk': blk or 0,
        'tov': tov or 0,
        'usg': usg,
        'mins': mins or 0,
        'games': games
    }


def get_synergy_profile(conn, player_name):
    """Get player's synergy playtype profile."""
    c = conn.cursor()

    c.execute('''
        SELECT playtype, freq_pct, ppp
        FROM player_synergy_playtypes
        WHERE player_name = ? AND season = '2025-26'
        ORDER BY freq_pct DESC
    ''', (player_name,))

    return {row[0]: {'freq': row[1], 'ppp': row[2]} for row in c.fetchall()}


def assign_archetype(stats, synergy, position):
    """
    Assign archetype based on box scores + synergy enhancement.

    Returns: (archetype, reasoning)
    """
    if not stats:
        return 'GENERALIST', 'No stats'

    pts = stats['pts']
    reb = stats['reb']
    ast = stats['ast']
    tpm = stats['tpm']
    stl = stats['stl']
    blk = stats['blk']
    usg = stats['usg']
    mins = stats['mins']

    # Get synergy frequencies (default 0 if not available)
    iso_freq = synergy.get('ISO', {}).get('freq', 0)
    prh_freq = synergy.get('PR_BALL_HANDLER', {}).get('freq', 0)
    prr_freq = synergy.get('PR_ROLL_MAN', {}).get('freq', 0)
    spot_freq = synergy.get('SPOT_UP', {}).get('freq', 0)
    trans_freq = synergy.get('TRANSITION', {}).get('freq', 0)
    cut_freq = synergy.get('CUT', {}).get('freq', 0)
    post_freq = synergy.get('POST_UP', {}).get('freq', 0)

    # =========================================================================
    # TIER 1: STAR ENGINES (25+ PPG, high usage primary scorers)
    # =========================================================================

    # HELIOCENTRIC_MAESTRO: Ball-dominant playmakers (Luka, Jokic, Harden)
    # High scoring + high assists + P&R usage
    if pts >= 22 and ast >= 7:
        return 'HELIOCENTRIC_MAESTRO', f'Elite playmaker: {pts:.1f}ppg/{ast:.1f}apg'

    # ISO_ASSASSIN: Volume isolation scorers (SGA, Ant, KD)
    # High scoring + ISO or mid-range heavy
    if pts >= 25 and iso_freq >= 15:
        return 'ISO_ASSASSIN', f'Elite ISO: {pts:.1f}ppg, {iso_freq:.0f}% ISO'
    if pts >= 27 and usg >= 0.30:
        return 'ISO_ASSASSIN', f'Volume scorer: {pts:.1f}ppg, {usg:.0%} USG'

    # =========================================================================
    # TIER 2: PRIMARY SCORERS (18+ PPG)
    # =========================================================================

    # SNIPER_ELITE: High-volume 3PT shooters (Curry, Booker, Mitchell)
    if tpm >= 3.0:
        return 'SNIPER_ELITE', f'Elite shooter: {tpm:.1f} 3PM/game'
    if tpm >= 2.5 and spot_freq >= 20:
        return 'SNIPER_ELITE', f'Spot-up sniper: {tpm:.1f} 3PM, {spot_freq:.0f}% spot-up'

    # TWO_LEVEL_SCORER: Versatile scorers (18+ pts, some 3s, some drives)
    if pts >= 18 and tpm >= 1.5 and usg >= 0.24:
        return 'TWO_LEVEL_SCORER', f'Versatile: {pts:.1f}ppg, {tpm:.1f} 3PM'

    # SLASHING_CREATOR: Athletic drivers (Giannis, Zion style)
    if pts >= 20 and tpm < 1.0 and trans_freq >= 15:
        return 'SLASHING_CREATOR', f'Slasher: {pts:.1f}ppg, {trans_freq:.0f}% transition'
    if pts >= 22 and tpm < 1.5:
        return 'SLASHING_CREATOR', f'Paint scorer: {pts:.1f}ppg, {tpm:.1f} 3PM'

    # =========================================================================
    # TIER 3: BIG MEN (7+ RPG or specific big-man roles)
    # =========================================================================

    # HUB_BIG: Passing bigs (Jokic, Sabonis)
    if reb >= 8 and ast >= 5:
        return 'HUB_BIG', f'Playmaking big: {reb:.1f}rpg/{ast:.1f}apg'

    # WARRIOR_BIG: Two-way bigs (Embiid, AD style)
    if reb >= 7 and blk >= 1.0:
        return 'WARRIOR_BIG', f'Rim protector: {reb:.1f}rpg/{blk:.1f}bpg'
    if reb >= 8 and (stl + blk) >= 1.5:
        return 'WARRIOR_BIG', f'Two-way big: {reb:.1f}rpg, {stl+blk:.1f} stk+blk'

    # STRETCH_BIG: Shooting bigs (KAT, Lauri)
    if reb >= 6 and tpm >= 1.5:
        return 'STRETCH_BIG', f'Stretch big: {reb:.1f}rpg/{tpm:.1f} 3PM'

    # ROLL_MAN: P&R finishers (Ayton, Capela)
    if reb >= 7 and prr_freq >= 12:
        return 'ROLL_MAN', f'Roll man: {reb:.1f}rpg, {prr_freq:.0f}% P&R roll'
    if reb >= 8 and tpm < 0.5:
        return 'ROLL_MAN', f'Traditional big: {reb:.1f}rpg'

    # POST_ANCHOR: Post-up specialists
    if post_freq >= 15 and reb >= 6:
        return 'POST_ANCHOR', f'Post player: {post_freq:.0f}% post-up'

    # =========================================================================
    # TIER 4: ROLE PLAYERS & SPECIALISTS
    # =========================================================================

    # FACILITATOR: Pass-first guards (CP3, Rondo style)
    if ast >= 5 and pts < 15:
        return 'FACILITATOR', f'Playmaker: {ast:.1f}apg/{pts:.1f}ppg'
    if ast >= 6:
        return 'FACILITATOR', f'High assists: {ast:.1f}apg'

    # CUTTER_SPECIALIST: Off-ball movers (role players who cut)
    if cut_freq >= 15:
        return 'CUTTER_SPECIALIST', f'Cutter: {cut_freq:.0f}% cut plays'

    # ISLAND_DEFENDER: Defensive stoppers
    if (stl + blk) >= 2.0 and pts < 12:
        return 'ISLAND_DEFENDER', f'Defender: {stl:.1f}spg/{blk:.1f}bpg'
    if stl >= 1.5:
        return 'ISLAND_DEFENDER', f'Ball hawk: {stl:.1f}spg'

    # =========================================================================
    # TIER 5: EXPANDED ROLE PLAYER CATEGORIES
    # =========================================================================

    # 3&D WING: Shooters who defend
    if tpm >= 1.0 and (stl + blk) >= 1.0:
        return 'TWO_WAY_WING', f'3&D: {tpm:.1f} 3PM, {stl+blk:.1f} stk+blk'

    # SPOT_UP_SHOOTER: Catch-and-shoot specialists
    if spot_freq >= 30 or (tpm >= 1.5 and pts < 15):
        return 'SNIPER_ELITE', f'Spot-up: {spot_freq:.0f}% spot-up, {tpm:.1f} 3PM'

    # ENERGY_BIG: Rebounding role players
    if reb >= 5 and pts < 10:
        return 'ROLL_MAN', f'Energy big: {reb:.1f}rpg/{pts:.1f}ppg'

    # COMBO_GUARD: Scoring guards with some playmaking
    if pts >= 12 and ast >= 3:
        return 'TWO_LEVEL_SCORER', f'Combo guard: {pts:.1f}ppg/{ast:.1f}apg'

    # ATHLETIC_FINISHER: Transition/lob threats
    if trans_freq >= 20:
        return 'ATHLETIC_FINISHER', f'Transition: {trans_freq:.0f}% transition'

    # =========================================================================
    # FALLBACK: Reasonable categorization for remaining players
    # =========================================================================

    # Scorer fallback
    if pts >= 10:
        if tpm >= 1.0:
            return 'TWO_LEVEL_SCORER', f'Scoring: {pts:.1f}ppg, {tpm:.1f} 3PM'
        else:
            return 'ATHLETIC_FINISHER', f'Inside scorer: {pts:.1f}ppg'

    # Playmaker fallback
    if ast >= 3:
        return 'FACILITATOR', f'Passer: {ast:.1f}apg'

    # Rebounder fallback
    if reb >= 4:
        return 'ROLL_MAN', f'Rebounder: {reb:.1f}rpg'

    # Low-minute role player
    if mins < 15:
        return 'GENERALIST', f'Limited minutes: {mins:.1f}mpg'

    # True generalist (jack of all trades)
    return 'GENERALIST', f'Role player: {pts:.1f}/{reb:.1f}/{ast:.1f}'


def reassign_archetypes(dry_run=True):
    """Re-assign archetypes for all active players."""
    print("\n" + "=" * 60)
    print("LUDI-BOT ARCHETYPE RE-ASSIGNMENT (V2)")
    print("=" * 60)
    print(f"Mode: {'DRY RUN' if dry_run else 'EXECUTE'}")
    print("Using: Full season box scores + Synergy enhancement")

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Get all active players
    c.execute('''
        SELECT player_id, name, team, position, archetype
        FROM players
        WHERE is_active = 1
        ORDER BY base_ppg DESC NULLS LAST
    ''')
    players = c.fetchall()

    print(f"\nProcessing {len(players)} active players...")

    results = {
        'updated': 0,
        'unchanged': 0,
        'no_data': 0,
        'changes': []
    }

    archetype_counts = {}

    for player_id, name, team, position, current_arch in players:
        # Get season stats
        stats = get_season_averages(conn, name)

        if not stats:
            results['no_data'] += 1
            new_arch = current_arch or 'GENERALIST'
            archetype_counts[new_arch] = archetype_counts.get(new_arch, 0) + 1
            continue

        # Get synergy profile
        synergy = get_synergy_profile(conn, name)

        # Assign archetype
        new_arch, reason = assign_archetype(stats, synergy, position or 'UNK')

        archetype_counts[new_arch] = archetype_counts.get(new_arch, 0) + 1

        if new_arch != current_arch:
            results['updated'] += 1
            results['changes'].append({
                'name': name,
                'team': team,
                'old': current_arch,
                'new': new_arch,
                'reason': reason,
                'ppg': stats['pts'],
                'has_synergy': bool(synergy)
            })

            if not dry_run:
                c.execute('UPDATE players SET archetype = ? WHERE player_id = ?',
                         (new_arch, player_id))
        else:
            results['unchanged'] += 1

    if not dry_run:
        conn.commit()

    conn.close()

    # Print results
    print("\n" + "=" * 60)
    print("RESULTS")
    print("=" * 60)

    print(f"\nPlayers processed: {len(players)}")
    print(f"  Updated: {results['updated']}")
    print(f"  Unchanged: {results['unchanged']}")
    print(f"  No data: {results['no_data']}")

    print("\n--- ARCHETYPE DISTRIBUTION ---")
    for arch, cnt in sorted(archetype_counts.items(), key=lambda x: -x[1]):
        pct = 100 * cnt / len(players)
        bar = '█' * int(pct / 2)
        print(f"  {arch:<22} {cnt:>4} ({pct:>5.1f}%) {bar}")

    # Check GENERALIST rate
    generalist_pct = 100 * archetype_counts.get('GENERALIST', 0) / len(players)
    target_met = generalist_pct < 20
    print(f"\nGENERALIST rate: {generalist_pct:.1f}% (target: <20%) {'✅' if target_met else '❌'}")

    if results['changes']:
        print("\n--- TOP CHANGES (by PPG) ---")
        for change in sorted(results['changes'], key=lambda x: -x['ppg'])[:25]:
            syn = " [+Syn]" if change['has_synergy'] else ""
            print(f"  {change['name'][:22]:<22} ({change['team']}): {change['old'] or 'NULL':<20} -> {change['new']:<20}{syn}")
            print(f"    Reason: {change['reason']}")

    if dry_run:
        print("\n" + "=" * 60)
        print("DRY RUN - No changes made")
        print("Run with --execute to actually update database")
        print("=" * 60)

    return results


if __name__ == "__main__":
    dry_run = '--execute' not in sys.argv
    reassign_archetypes(dry_run=dry_run)
