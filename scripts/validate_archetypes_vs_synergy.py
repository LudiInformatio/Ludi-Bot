#!/usr/bin/env python3
"""
Archetype vs Synergy Validation Script
Validates player archetype assignments against NBA Synergy playtype data.

Usage:
    python scripts/validate_archetypes_vs_synergy.py

Output:
    reports/archetype_validation_2026-02-15.md
"""

import sqlite3
import os
from datetime import datetime
from collections import defaultdict
from typing import Dict, List, Tuple

# Archetype-to-Synergy expected mappings
ARCHETYPE_MAPPINGS = {
    'SNIPER_ELITE': {'expected': ['SPOT_UP'], 'threshold': 25.0},
    'ISO_ASSASSIN': {'expected': ['ISO'], 'threshold': 20.0},
    'HELIOCENTRIC_MAESTRO': {'expected': ['P&R_HANDLER'], 'threshold': 20.0},
    'ROLL_MAN': {'expected': ['P&R_ROLL_MAN'], 'threshold': 15.0},
    'CUTTER_SPECIALIST': {'expected': ['OFF_BALL_CUTTER'], 'threshold': 15.0},
    'ATHLETIC_FINISHER': {'expected': ['TRANSITION'], 'threshold': 15.0},
    'FACILITATOR': {'expected': ['P&R_HANDLER'], 'threshold': 15.0},
    'STRETCH_BIG': {'expected': ['SPOT_UP', 'P&R_ROLL_MAN'], 'threshold': 15.0},
    'RIM_RUNNER': {'expected': ['P&R_ROLL_MAN', 'PUTBACK'], 'threshold': 15.0},
    'TWO_WAY_WING': {'expected': ['SPOT_UP', 'TRANSITION'], 'threshold': 12.0},
    'ELITE_SCORER': {'expected': ['ISO', 'P&R_HANDLER'], 'threshold': 15.0},
    'GENERALIST': {'expected': [], 'threshold': 0.0},  # No specific expectation
}

# Minimum possessions for significance (Synergy best practice)
MIN_TOTAL_POSS = 75


def get_db_connection():
    """Connect to the database."""
    db_path = os.path.join(os.path.dirname(__file__), '..', 'ludi.db')
    return sqlite3.connect(db_path)


def get_player_archetypes_and_synergy(conn) -> Dict[str, Dict]:
    """
    Get all active players with their archetypes and top Synergy playtypes.

    Returns:
        Dict mapping player_name -> {archetype, synergy_data}
    """
    query = """
    SELECT
        p.name,
        p.archetype,
        ps.playtype,
        ps.freq_pct,
        ps.percentile,
        ps.poss_per_game,
        ps.games_played,
        (ps.poss_per_game * ps.games_played) as total_poss
    FROM players p
    LEFT JOIN player_synergy_playtypes ps ON p.name = ps.player_name
    WHERE p.is_active = 1
    ORDER BY p.name, ps.freq_pct DESC
    """

    cursor = conn.cursor()
    cursor.execute(query)
    rows = cursor.fetchall()

    # Group by player
    players = defaultdict(lambda: {'archetype': None, 'synergy': []})

    for row in rows:
        name, archetype, playtype, freq_pct, percentile, ppg, games, total_poss = row

        if archetype:
            players[name]['archetype'] = archetype

        if playtype and total_poss and total_poss >= MIN_TOTAL_POSS:
            players[name]['synergy'].append({
                'playtype': playtype,
                'freq_pct': freq_pct,
                'percentile': percentile,
                'poss_per_game': ppg,
                'games_played': games,
                'total_poss': total_poss
            })

    return dict(players)


def validate_archetype(archetype: str, synergy_data: List[Dict]) -> Tuple[bool, str, List[Dict]]:
    """
    Validate if archetype matches Synergy data.

    Returns:
        (is_valid, reason, top_playtypes)
    """
    if not synergy_data:
        return False, "NO_SYNERGY_DATA", []

    if archetype not in ARCHETYPE_MAPPINGS:
        return True, "UNMAPPED_ARCHETYPE", synergy_data[:3]

    mapping = ARCHETYPE_MAPPINGS[archetype]
    expected_playtypes = mapping['expected']
    threshold = mapping['threshold']

    # GENERALIST has no expectations
    if not expected_playtypes:
        return True, "GENERALIST_PASS", synergy_data[:3]

    # Check if top playtype matches expectations
    top_playtype = synergy_data[0]

    if top_playtype['playtype'] in expected_playtypes and top_playtype['freq_pct'] >= threshold:
        return True, "ALIGNED", synergy_data[:3]

    # Check if any expected playtype meets threshold
    for syn in synergy_data:
        if syn['playtype'] in expected_playtypes and syn['freq_pct'] >= threshold:
            return True, "ALIGNED_SECONDARY", synergy_data[:3]

    # Mismatch: top playtype doesn't match expectation
    top_type = top_playtype['playtype']
    top_freq = top_playtype['freq_pct']
    return False, f"MISMATCH: Top={top_type}({top_freq:.1f}%) Expected={expected_playtypes}", synergy_data[:3]


def get_bet_performance(conn, player_name: str, days: int = 14) -> Dict:
    """Get recent bet performance for a player."""
    query = """
    SELECT
        COUNT(*) as total_bets,
        SUM(CASE WHEN outcome = 'WIN' THEN 1 ELSE 0 END) as wins,
        SUM(CASE WHEN outcome = 'LOSS' THEN 1 ELSE 0 END) as losses,
        AVG(true_edge) as avg_edge,
        AVG(CASE WHEN outcome IN ('WIN', 'LOSS') THEN
            CASE WHEN outcome = 'WIN' THEN units ELSE -units END
        END) as avg_profit
    FROM bet_recommendations
    WHERE player_name = ?
    AND game_date >= date('now', '-' || ? || ' days')
    AND outcome IN ('WIN', 'LOSS', 'PUSH')
    """

    cursor = conn.cursor()
    cursor.execute(query, (player_name, days))
    row = cursor.fetchone()

    if row and row[0] > 0:
        total, wins, losses, avg_edge, avg_profit = row
        return {
            'total_bets': total,
            'wins': wins,
            'losses': losses,
            'win_rate': (wins / (wins + losses) * 100) if (wins + losses) > 0 else 0,
            'avg_edge': avg_edge or 0,
            'avg_profit': avg_profit or 0
        }

    return None


def analyze_performance_by_alignment(conn, players: Dict) -> Dict:
    """Compare performance between aligned and mismatched archetypes."""
    aligned_stats = {'total_bets': 0, 'wins': 0, 'losses': 0, 'total_profit': 0}
    mismatched_stats = {'total_bets': 0, 'wins': 0, 'losses': 0, 'total_profit': 0}

    for name, data in players.items():
        if not data['archetype'] or not data['synergy']:
            continue

        is_valid, reason, _ = validate_archetype(data['archetype'], data['synergy'])
        perf = get_bet_performance(conn, name, days=14)

        if not perf or perf['total_bets'] < 3:  # Minimum sample size
            continue

        target = aligned_stats if is_valid else mismatched_stats
        target['total_bets'] += perf['total_bets']
        target['wins'] += perf['wins']
        target['losses'] += perf['losses']
        target['total_profit'] += perf['avg_profit'] * perf['total_bets']

    return {
        'aligned': aligned_stats,
        'mismatched': mismatched_stats
    }


def generate_report(players: Dict, performance: Dict, output_path: str):
    """Generate markdown validation report."""

    # Categorize players
    aligned = []
    mismatched = []
    no_data = []

    for name, data in players.items():
        if not data['archetype']:
            continue

        if not data['synergy']:
            no_data.append(name)
            continue

        is_valid, reason, top_playtypes = validate_archetype(data['archetype'], data['synergy'])

        record = {
            'name': name,
            'archetype': data['archetype'],
            'reason': reason,
            'top_playtypes': top_playtypes
        }

        if is_valid:
            aligned.append(record)
        else:
            mismatched.append(record)

    # Calculate stats
    total_players = len(players)
    players_with_archetypes = sum(1 for d in players.values() if d['archetype'])
    players_with_synergy = sum(1 for d in players.values() if d['synergy'])
    coverage_pct = (players_with_synergy / players_with_archetypes * 100) if players_with_archetypes > 0 else 0

    # Performance stats
    aligned_perf = performance['aligned']
    mismatched_perf = performance['mismatched']

    aligned_wr = (aligned_perf['wins'] / (aligned_perf['wins'] + aligned_perf['losses']) * 100) if (aligned_perf['wins'] + aligned_perf['losses']) > 0 else 0
    mismatched_wr = (mismatched_perf['wins'] / (mismatched_perf['wins'] + mismatched_perf['losses']) * 100) if (mismatched_perf['wins'] + mismatched_perf['losses']) > 0 else 0

    aligned_roi = (aligned_perf['total_profit'] / aligned_perf['total_bets']) if aligned_perf['total_bets'] > 0 else 0
    mismatched_roi = (mismatched_perf['total_profit'] / mismatched_perf['total_bets']) if mismatched_perf['total_bets'] > 0 else 0

    # Write report
    with open(output_path, 'w') as f:
        f.write(f"# Archetype vs Synergy Validation Report\n\n")
        f.write(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

        f.write("## Executive Summary\n\n")
        f.write(f"- **Total Active Players:** {total_players}\n")
        f.write(f"- **Players with Archetypes:** {players_with_archetypes}\n")
        f.write(f"- **Players with Synergy Data:** {players_with_synergy}\n")
        f.write(f"- **Synergy Coverage:** {coverage_pct:.1f}%\n")
        f.write(f"- **Aligned Archetypes:** {len(aligned)} ({len(aligned)/players_with_archetypes*100:.1f}%)\n")
        f.write(f"- **Mismatched Archetypes:** {len(mismatched)} ({len(mismatched)/players_with_archetypes*100:.1f}%)\n")
        f.write(f"- **No Synergy Data:** {len(no_data)} ({len(no_data)/players_with_archetypes*100:.1f}%)\n\n")

        f.write("## Performance Comparison (14-Day)\n\n")
        f.write("| Metric | Aligned Archetypes | Mismatched Archetypes | Delta |\n")
        f.write("|--------|-------------------|----------------------|-------|\n")
        f.write(f"| Total Bets | {aligned_perf['total_bets']} | {mismatched_perf['total_bets']} | - |\n")
        f.write(f"| Win Rate | {aligned_wr:.1f}% | {mismatched_wr:.1f}% | {aligned_wr - mismatched_wr:+.1f}% |\n")
        f.write(f"| ROI per Bet | {aligned_roi:+.2f}u | {mismatched_roi:+.2f}u | {aligned_roi - mismatched_roi:+.2f}u |\n")
        f.write(f"| Total Profit | {aligned_perf['total_profit']:+.1f}u | {mismatched_perf['total_profit']:+.1f}u | {aligned_perf['total_profit'] - mismatched_perf['total_profit']:+.1f}u |\n\n")

        if len(mismatched) > 0:
            f.write("## Mismatched Archetypes (Needs Review)\n\n")
            f.write("| Player | Assigned Archetype | Mismatch Reason | Top Playtype | Freq % | Percentile |\n")
            f.write("|--------|-------------------|----------------|--------------|--------|------------|\n")

            for record in sorted(mismatched, key=lambda x: x['top_playtypes'][0]['freq_pct'] if x['top_playtypes'] else 0, reverse=True):
                top = record['top_playtypes'][0] if record['top_playtypes'] else None
                if top:
                    f.write(f"| {record['name']} | {record['archetype']} | {record['reason']} | {top['playtype']} | {top['freq_pct']:.1f}% | {top['percentile']:.0f}% |\n")
            f.write("\n")

        f.write("## Recommended Reclassifications\n\n")
        f.write("| Player | Current Archetype | Recommended Archetype | Primary Playtype | Freq % |\n")
        f.write("|--------|------------------|----------------------|------------------|--------|\n")

        for record in mismatched:
            if not record['top_playtypes']:
                continue

            top = record['top_playtypes'][0]
            playtype = top['playtype']
            freq = top['freq_pct']

            # Suggest new archetype based on top playtype
            suggested = None
            if playtype == 'ISO' and freq >= 20:
                suggested = 'ISO_ASSASSIN'
            elif playtype == 'SPOT_UP' and freq >= 25:
                suggested = 'SNIPER_ELITE'
            elif playtype == 'P&R_HANDLER' and freq >= 20:
                suggested = 'HELIOCENTRIC_MAESTRO'
            elif playtype == 'P&R_ROLL_MAN' and freq >= 15:
                suggested = 'ROLL_MAN'
            elif playtype == 'OFF_BALL_CUTTER' and freq >= 15:
                suggested = 'CUTTER_SPECIALIST'
            elif playtype == 'TRANSITION' and freq >= 15:
                suggested = 'ATHLETIC_FINISHER'

            if suggested and suggested != record['archetype']:
                f.write(f"| {record['name']} | {record['archetype']} | {suggested} | {playtype} | {freq:.1f}% |\n")

        f.write("\n")

        f.write("## Secondary Playtype Analysis\n\n")
        f.write("Players with multiple significant playtypes (freq >= 15%):\n\n")
        f.write("| Player | Archetype | Primary Playtype | Secondary Playtype(s) |\n")
        f.write("|--------|-----------|-----------------|----------------------|\n")

        for name, data in sorted(players.items()):
            if not data['archetype'] or len(data['synergy']) < 2:
                continue

            significant = [s for s in data['synergy'] if s['freq_pct'] >= 15.0]
            if len(significant) >= 2:
                primary = f"{significant[0]['playtype']} ({significant[0]['freq_pct']:.1f}%)"
                secondary = ", ".join([f"{s['playtype']} ({s['freq_pct']:.1f}%)" for s in significant[1:]])
                f.write(f"| {name} | {data['archetype']} | {primary} | {secondary} |\n")

        f.write("\n")

        f.write("## Synergy Data Quality\n\n")
        f.write(f"**Coverage Gaps:** {len(no_data)} players with archetypes but no Synergy data\n\n")

        if no_data:
            f.write("Players missing Synergy data:\n")
            for name in sorted(no_data):
                archetype = players[name]['archetype']
                f.write(f"- {name} ({archetype})\n")
            f.write("\n")

        f.write("## Validation Criteria\n\n")
        f.write("| Archetype | Expected Playtype(s) | Threshold |\n")
        f.write("|-----------|---------------------|----------|\n")
        for archetype, mapping in sorted(ARCHETYPE_MAPPINGS.items()):
            expected = ", ".join(mapping['expected']) if mapping['expected'] else "N/A"
            threshold = f"{mapping['threshold']:.0f}%" if mapping['threshold'] > 0 else "N/A"
            f.write(f"| {archetype} | {expected} | {threshold} |\n")
        f.write("\n")

        f.write("**Minimum Total Possessions:** 75 (Synergy best practice)\n\n")

        f.write("## Methodology\n\n")
        f.write("1. **Data Source:** `player_synergy_playtypes` table (2,740 records, 405 players)\n")
        f.write("2. **Filtering:** Only playtypes with ≥75 total possessions considered significant\n")
        f.write("3. **Validation:** Each archetype validated against expected Synergy playtype(s)\n")
        f.write("4. **Performance:** 14-day bet performance compared between aligned/mismatched\n")
        f.write("5. **Recommendations:** Reclassifications based on dominant playtype frequency\n\n")


def main():
    """Main execution."""
    print("🔍 Archetype vs Synergy Validation Script")
    print("=" * 60)

    # Connect to database
    conn = get_db_connection()
    print(f"✓ Connected to database")

    # Get player data
    print(f"⏳ Fetching player archetypes and Synergy data...")
    players = get_player_archetypes_and_synergy(conn)
    print(f"✓ Loaded {len(players)} active players")

    # Analyze performance
    print(f"⏳ Analyzing bet performance by archetype alignment...")
    performance = analyze_performance_by_alignment(conn, players)
    print(f"✓ Performance analysis complete")

    # Generate report
    output_path = os.path.join(
        os.path.dirname(__file__),
        '..',
        'reports',
        f'archetype_validation_{datetime.now().strftime("%Y-%m-%d")}.md'
    )

    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    print(f"⏳ Generating validation report...")
    generate_report(players, performance, output_path)
    print(f"✓ Report saved to: {output_path}")

    # Print summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    players_with_archetypes = sum(1 for d in players.values() if d['archetype'])
    players_with_synergy = sum(1 for d in players.values() if d['synergy'])

    aligned = sum(1 for name, data in players.items()
                  if data['archetype'] and data['synergy']
                  and validate_archetype(data['archetype'], data['synergy'])[0])

    mismatched = sum(1 for name, data in players.items()
                     if data['archetype'] and data['synergy']
                     and not validate_archetype(data['archetype'], data['synergy'])[0])

    no_data = sum(1 for d in players.values() if d['archetype'] and not d['synergy'])

    print(f"Total Players: {len(players)}")
    print(f"With Archetypes: {players_with_archetypes}")
    print(f"With Synergy Data: {players_with_synergy} ({players_with_synergy/players_with_archetypes*100:.1f}%)")
    print(f"\nValidation Results:")
    print(f"  ✓ Aligned: {aligned} ({aligned/players_with_archetypes*100:.1f}%)")
    print(f"  ✗ Mismatched: {mismatched} ({mismatched/players_with_archetypes*100:.1f}%)")
    print(f"  ? No Data: {no_data} ({no_data/players_with_archetypes*100:.1f}%)")

    # Performance summary
    aligned_perf = performance['aligned']
    mismatched_perf = performance['mismatched']

    if aligned_perf['total_bets'] > 0 and mismatched_perf['total_bets'] > 0:
        aligned_wr = aligned_perf['wins'] / (aligned_perf['wins'] + aligned_perf['losses']) * 100
        mismatched_wr = mismatched_perf['wins'] / (mismatched_perf['wins'] + mismatched_perf['losses']) * 100

        print(f"\n14-Day Performance:")
        print(f"  Aligned: {aligned_wr:.1f}% WR ({aligned_perf['total_bets']} bets)")
        print(f"  Mismatched: {mismatched_wr:.1f}% WR ({mismatched_perf['total_bets']} bets)")
        print(f"  Delta: {aligned_wr - mismatched_wr:+.1f}%")

    print("\n" + "=" * 60)
    print(f"✓ Validation complete. See full report at:\n  {output_path}")

    conn.close()


if __name__ == '__main__':
    main()
