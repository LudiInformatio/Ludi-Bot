#!/usr/bin/env python3
"""
14-Day Trend Analysis Script
Compares recent 14-day window (Feb 2-12, 2026) vs full season baseline
to identify performance drift, scheme changes, and calibration issues.

Author: Ludi Informatio
Created: 2026-02-15
"""

import sqlite3
import argparse
from datetime import datetime, timedelta
from collections import defaultdict
from pathlib import Path

# Analysis windows
SEASON_START = '2025-10-20'
TREND_WINDOW_START = '2026-02-02'  # Last 14 days
TREND_WINDOW_END = '2026-02-12'

# Database path
DB_PATH = '/Users/flyprice/Desktop/Ludi Informatio/Projects/Ludi-Bot/ludi.db'

# Reports directory
REPORTS_DIR = Path('/Users/flyprice/Desktop/Ludi Informatio/Projects/Ludi-Bot/reports')
REPORTS_DIR.mkdir(exist_ok=True)


def _resolve_window_end(db_path: str, end_date: str = None) -> str:
    if end_date:
        return end_date
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT MAX(date) FROM games")
        row = cursor.fetchone()
        conn.close()
        if row and row[0]:
            return row[0]
    except Exception:
        pass
    return '2026-02-12'


def get_db_connection():
    """Create database connection."""
    return sqlite3.connect(DB_PATH)


def analyze_player_drift():
    """
    Section 1: Player Performance Drift
    Compare 14-day avg vs season avg for key stats.
    """
    print("\n" + "="*80)
    print("SECTION 1: PLAYER PERFORMANCE DRIFT")
    print("="*80)

    conn = get_db_connection()
    cursor = conn.cursor()

    # Stats to analyze (actual column names in player_game_logs)
    stats = ['pts', 'ast', 'reb', 'fg3m', 'blk', 'stl', 'tov']

    results = []

    for stat in stats:
        # Season average
        cursor.execute(f"""
            SELECT player_name, AVG({stat}) as season_avg, COUNT(*) as games
            FROM player_game_logs
            WHERE game_date >= ? AND game_date <= ?
            AND minutes > 0
            GROUP BY player_name
            HAVING games >= 20
        """, (SEASON_START, TREND_WINDOW_END))
        season_data = {row[0]: row[1] for row in cursor.fetchall()}

        # 14-day average
        cursor.execute(f"""
            SELECT player_name, AVG({stat}) as trend_avg, COUNT(*) as games
            FROM player_game_logs
            WHERE game_date >= ? AND game_date <= ?
            AND minutes > 0
            GROUP BY player_name
            HAVING games >= 5
        """, (TREND_WINDOW_START, TREND_WINDOW_END))

        for row in cursor.fetchall():
            player, trend_avg, games = row
            if player in season_data and season_data[player] > 0:
                season_avg = season_data[player]
                pct_change = ((trend_avg - season_avg) / season_avg) * 100

                if abs(pct_change) >= 15:  # 15% threshold
                    results.append({
                        'player': player,
                        'stat': stat.upper(),
                        'season_avg': round(season_avg, 2),
                        'recent_avg': round(trend_avg, 2),
                        'pct_change': round(pct_change, 1),
                        'recent_games': games
                    })

    conn.close()

    # Sort by absolute change
    results.sort(key=lambda x: abs(x['pct_change']), reverse=True)

    # Generate report
    report_lines = []
    report_lines.append("# Player Performance Drift Analysis")
    report_lines.append(f"\n**Analysis Date:** {datetime.now().strftime('%Y-%m-%d')}")
    report_lines.append(f"**Season Baseline:** {SEASON_START} to {TREND_WINDOW_END}")
    report_lines.append(f"**Recent Window:** {TREND_WINDOW_START} to {TREND_WINDOW_END} (14 days)")
    report_lines.append(f"\n**Threshold:** ≥15% change\n")

    report_lines.append("\n## Top 30 Performance Movers\n")
    report_lines.append("| Player | Stat | Season Avg | Recent Avg | Change % | Games |")
    report_lines.append("|--------|------|------------|------------|----------|-------|")

    for item in results[:30]:
        direction = "📈" if item['pct_change'] > 0 else "📉"
        report_lines.append(
            f"| {item['player']} | {item['stat']} | {item['season_avg']} | "
            f"{item['recent_avg']} | {direction} {item['pct_change']}% | {item['recent_games']} |"
        )

    # Save report
    report_path = REPORTS_DIR / f"player_drift_{datetime.now().strftime('%Y-%m-%d')}.md"
    with open(report_path, 'w') as f:
        f.write('\n'.join(report_lines))

    print(f"\n✅ Found {len(results)} players with ≥15% drift")
    print(f"📄 Report saved: {report_path}")

    return results


def analyze_scheme_effectiveness():
    """
    Section 2: Team Scheme Effectiveness
    Compare defensive/offensive scheme performance in windows.
    """
    print("\n" + "="*80)
    print("SECTION 2: TEAM SCHEME EFFECTIVENESS")
    print("="*80)

    conn = get_db_connection()
    cursor = conn.cursor()

    # Extract defensive scheme from tags
    results = []

    for window_name, start_date, end_date in [
        ("Season", SEASON_START, TREND_WINDOW_END),
        ("14-Day", TREND_WINDOW_START, TREND_WINDOW_END)
    ]:
        cursor.execute("""
            SELECT tags, outcome
            FROM bet_recommendations
            WHERE created_at >= ? AND created_at <= ?
            AND outcome IN ('WIN', 'LOSS')
        """, (start_date + ' 00:00:00', end_date + ' 23:59:59'))

        scheme_stats = defaultdict(lambda: {'wins': 0, 'losses': 0})

        for tags_json, outcome in cursor.fetchall():
            if not tags_json:
                continue

            # Parse tags (JSON array)
            import json
            try:
                tags = json.loads(tags_json)
            except (json.JSONDecodeError, TypeError):
                continue

            # Find defensive scheme tag
            scheme = None
            for tag in tags:
                if tag.startswith('vs_'):
                    scheme = tag[3:]  # Remove 'vs_' prefix
                    break

            if scheme:
                if outcome == 'WIN':
                    scheme_stats[scheme]['wins'] += 1
                else:
                    scheme_stats[scheme]['losses'] += 1

        # Calculate hit rates
        for scheme, stats in scheme_stats.items():
            total = stats['wins'] + stats['losses']
            if total >= 10:  # Minimum sample size
                hit_rate = (stats['wins'] / total) * 100
                results.append({
                    'window': window_name,
                    'scheme': scheme.upper(),
                    'wins': stats['wins'],
                    'losses': stats['losses'],
                    'total': total,
                    'hit_rate': round(hit_rate, 1)
                })

    conn.close()

    # Generate comparison report
    report_lines = []
    report_lines.append("# Defensive Scheme Performance Analysis")
    report_lines.append(f"\n**Analysis Date:** {datetime.now().strftime('%Y-%m-%d')}")
    report_lines.append(f"**Minimum Sample:** 10 bets per scheme\n")

    # Group by scheme for comparison
    scheme_comparison = defaultdict(dict)
    for item in results:
        scheme_comparison[item['scheme']][item['window']] = item

    report_lines.append("\n## Season vs 14-Day Performance\n")
    report_lines.append("| Scheme | Season WR | Season Bets | 14-Day WR | 14-Day Bets | Trend |")
    report_lines.append("|--------|-----------|-------------|-----------|-------------|-------|")

    for scheme in sorted(scheme_comparison.keys()):
        season_data = scheme_comparison[scheme].get('Season', {})
        trend_data = scheme_comparison[scheme].get('14-Day', {})

        if season_data and trend_data:
            season_wr = season_data['hit_rate']
            trend_wr = trend_data['hit_rate']
            diff = trend_wr - season_wr

            if diff > 5:
                trend_icon = "📈 HEATING UP"
            elif diff < -5:
                trend_icon = "📉 COOLING OFF"
            else:
                trend_icon = "➡️ STABLE"

            report_lines.append(
                f"| {scheme} | {season_wr}% | {season_data['total']} | "
                f"{trend_wr}% | {trend_data['total']} | {trend_icon} ({diff:+.1f}%) |"
            )

    # Save report
    report_path = REPORTS_DIR / f"scheme_trends_{datetime.now().strftime('%Y-%m-%d')}.md"
    with open(report_path, 'w') as f:
        f.write('\n'.join(report_lines))

    print(f"\n✅ Analyzed {len(scheme_comparison)} defensive schemes")
    print(f"📄 Report saved: {report_path}")

    return results


def analyze_archetype_trends():
    """
    Section 3: Archetype Performance Changes
    Compare archetype × stat hit rates in windows.
    """
    print("\n" + "="*80)
    print("SECTION 3: ARCHETYPE PERFORMANCE TRENDS")
    print("="*80)

    conn = get_db_connection()
    cursor = conn.cursor()

    results = []

    for window_name, start_date, end_date in [
        ("Season", SEASON_START, TREND_WINDOW_END),
        ("14-Day", TREND_WINDOW_START, TREND_WINDOW_END)
    ]:
        cursor.execute("""
            SELECT tags, stat_category, outcome
            FROM bet_recommendations
            WHERE created_at >= ? AND created_at <= ?
            AND outcome IN ('WIN', 'LOSS')
        """, (start_date + ' 00:00:00', end_date + ' 23:59:59'))

        archetype_stats = defaultdict(lambda: {'wins': 0, 'losses': 0})

        for tags_json, stat_category, outcome in cursor.fetchall():
            if not tags_json:
                continue

            # Parse tags
            import json
            try:
                tags = json.loads(tags_json)
            except (json.JSONDecodeError, TypeError):
                continue

            # Find archetype tag
            archetypes = [
                'STRETCH_BIG', 'SLASHING_CREATOR', 'SNIPER_ELITE', 'ROLL_MAN',
                'HELIOCENTRIC_MAESTRO', 'GENERALIST', 'TWO_LEVEL_SCORER', 'HUB_BIG'
            ]

            archetype = None
            for tag in tags:
                if tag in archetypes:
                    archetype = tag
                    break

            if archetype and stat_category:
                key = f"{archetype}_{stat_category}"
                if outcome == 'WIN':
                    archetype_stats[key]['wins'] += 1
                else:
                    archetype_stats[key]['losses'] += 1

        # Calculate hit rates
        for key, stats in archetype_stats.items():
            total = stats['wins'] + stats['losses']
            if total >= 5:  # Lower threshold for archetype combos
                hit_rate = (stats['wins'] / total) * 100
                archetype, stat_category = key.rsplit('_', 1)
                results.append({
                    'window': window_name,
                    'archetype': archetype,
                    'stat_category': stat_category,
                    'wins': stats['wins'],
                    'losses': stats['losses'],
                    'total': total,
                    'hit_rate': round(hit_rate, 1)
                })

    conn.close()

    # Generate report
    report_lines = []
    report_lines.append("# Archetype Performance Trends")
    report_lines.append(f"\n**Analysis Date:** {datetime.now().strftime('%Y-%m-%d')}")
    report_lines.append(f"**Minimum Sample:** 5 bets per archetype-stat combo\n")

    # Group by archetype-stat_category for comparison
    combo_comparison = defaultdict(dict)
    for item in results:
        key = f"{item['archetype']}_{item['stat_category']}"
        combo_comparison[key][item['window']] = item

    report_lines.append("\n## Top Trending Archetype-Stat Combos\n")
    report_lines.append("| Archetype | Stat | Season WR | 14-Day WR | Change | Trend |")
    report_lines.append("|-----------|------|-----------|-----------|--------|-------|")

    # Calculate trends
    trends = []
    for key, data in combo_comparison.items():
        if 'Season' in data and '14-Day' in data:
            season_wr = data['Season']['hit_rate']
            trend_wr = data['14-Day']['hit_rate']
            diff = trend_wr - season_wr

            trends.append({
                'key': key,
                'archetype': data['Season']['archetype'],
                'stat_category': data['Season']['stat_category'],
                'season_wr': season_wr,
                'trend_wr': trend_wr,
                'diff': diff,
                'season_bets': data['Season']['total'],
                'trend_bets': data['14-Day']['total']
            })

    # Sort by absolute change
    trends.sort(key=lambda x: abs(x['diff']), reverse=True)

    for item in trends[:20]:
        if item['diff'] > 10:
            trend_icon = "🔥 HOT"
        elif item['diff'] < -10:
            trend_icon = "❄️ COLD"
        else:
            trend_icon = "➡️"

        report_lines.append(
            f"| {item['archetype']} | {item['stat_category']} | {item['season_wr']}% | "
            f"{item['trend_wr']}% | {item['diff']:+.1f}% | {trend_icon} |"
        )

    # Save report
    report_path = REPORTS_DIR / f"archetype_trends_{datetime.now().strftime('%Y-%m-%d')}.md"
    with open(report_path, 'w') as f:
        f.write('\n'.join(report_lines))

    print(f"\n✅ Analyzed {len(combo_comparison)} archetype-stat combos")
    print(f"📄 Report saved: {report_path}")

    return results


def analyze_edge_calibration():
    """
    Section 4: Edge Calibration Drift
    Compare edge bucket performance in windows.
    """
    print("\n" + "="*80)
    print("SECTION 4: EDGE CALIBRATION DRIFT")
    print("="*80)

    conn = get_db_connection()
    cursor = conn.cursor()

    edge_buckets = [
        (5, 10, "5-10%"),
        (10, 15, "10-15%"),
        (15, 20, "15-20%"),
        (20, 25, "20-25%"),
        (25, 100, "25%+")
    ]

    results = []

    for window_name, start_date, end_date in [
        ("Season", SEASON_START, TREND_WINDOW_END),
        ("14-Day", TREND_WINDOW_START, TREND_WINDOW_END)
    ]:
        for min_edge, max_edge, bucket_name in edge_buckets:
            cursor.execute("""
                SELECT COUNT(*) as total,
                       SUM(CASE WHEN outcome = 'WIN' THEN 1 ELSE 0 END) as wins
                FROM bet_recommendations
                WHERE created_at >= ? AND created_at <= ?
                AND outcome IN ('WIN', 'LOSS')
                AND true_edge >= ? AND true_edge < ?
            """, (start_date + ' 00:00:00', end_date + ' 23:59:59', min_edge, max_edge))

            row = cursor.fetchone()
            total, wins = row[0], row[1] or 0

            if total > 0:
                hit_rate = (wins / total) * 100
                results.append({
                    'window': window_name,
                    'bucket': bucket_name,
                    'min_edge': min_edge,
                    'wins': wins,
                    'losses': total - wins,
                    'total': total,
                    'hit_rate': round(hit_rate, 1)
                })

    conn.close()

    # Generate report
    report_lines = []
    report_lines.append("# Edge Calibration Analysis")
    report_lines.append(f"\n**Analysis Date:** {datetime.now().strftime('%Y-%m-%d')}\n")

    report_lines.append("\n## Edge Bucket Performance Comparison\n")
    report_lines.append("| Edge Bucket | Season WR | Season Bets | 14-Day WR | 14-Day Bets | Status |")
    report_lines.append("|-------------|-----------|-------------|-----------|-------------|--------|")

    # Expected win rates by edge
    expected_wr = {
        "5-10%": 55,
        "10-15%": 60,
        "15-20%": 65,
        "20-25%": 70,
        "25%+": 74
    }

    for bucket_name in ["5-10%", "10-15%", "15-20%", "20-25%", "25%+"]:
        season_data = next((r for r in results if r['window'] == 'Season' and r['bucket'] == bucket_name), None)
        trend_data = next((r for r in results if r['window'] == '14-Day' and r['bucket'] == bucket_name), None)

        if season_data:
            season_wr = season_data['hit_rate']
            season_bets = season_data['total']

            trend_wr = trend_data['hit_rate'] if trend_data else 0
            trend_bets = trend_data['total'] if trend_data else 0

            expected = expected_wr[bucket_name]

            # Status determination
            if season_wr >= expected:
                status = "✅ CALIBRATED"
            elif season_wr >= expected - 5:
                status = "⚠️ CLOSE"
            else:
                status = "🚨 BROKEN"

            report_lines.append(
                f"| {bucket_name} | {season_wr}% | {season_bets} | "
                f"{trend_wr}% | {trend_bets} | {status} |"
            )

    report_lines.append("\n## Critical Issue: 25%+ Edge Bucket")
    report_lines.append("\n**Expected:** 74% win rate")
    high_edge_season = next((r for r in results if r['window'] == 'Season' and r['bucket'] == '25%+'), None)
    if high_edge_season:
        report_lines.append(f"**Actual (Season):** {high_edge_season['hit_rate']}%")
        report_lines.append(f"**Sample Size:** {high_edge_season['total']} bets")

        if high_edge_season['hit_rate'] < 55:
            report_lines.append("\n**Status:** 🚨 CRITICAL - Edge calculation likely broken above 20%")
        else:
            report_lines.append("\n**Status:** ⚠️ Needs investigation")

    # Save report
    report_path = REPORTS_DIR / f"edge_calibration_{datetime.now().strftime('%Y-%m-%d')}.md"
    with open(report_path, 'w') as f:
        f.write('\n'.join(report_lines))

    print(f"\n✅ Edge calibration analysis complete")
    print(f"📄 Report saved: {report_path}")

    return results


def analyze_stat_trends():
    """
    Section 5: Stat Category Performance Changes
    Compare per-stat OVER vs UNDER performance.
    """
    print("\n" + "="*80)
    print("SECTION 5: STAT CATEGORY TRENDS")
    print("="*80)

    conn = get_db_connection()
    cursor = conn.cursor()

    results = []

    for window_name, start_date, end_date in [
        ("Season", SEASON_START, TREND_WINDOW_END),
        ("14-Day", TREND_WINDOW_START, TREND_WINDOW_END)
    ]:
        cursor.execute("""
            SELECT stat_category, bet_side, outcome
            FROM bet_recommendations
            WHERE created_at >= ? AND created_at <= ?
            AND outcome IN ('WIN', 'LOSS')
        """, (start_date + ' 00:00:00', end_date + ' 23:59:59'))

        stat_stats = defaultdict(lambda: defaultdict(lambda: {'wins': 0, 'losses': 0}))

        for stat_category, bet_side, outcome in cursor.fetchall():
            if stat_category and bet_side:
                if outcome == 'WIN':
                    stat_stats[stat_category][bet_side]['wins'] += 1
                else:
                    stat_stats[stat_category][bet_side]['losses'] += 1

        # Calculate hit rates
        for stat_category, sides in stat_stats.items():
            for bet_side, stats in sides.items():
                total = stats['wins'] + stats['losses']
                if total >= 10:  # Minimum sample
                    hit_rate = (stats['wins'] / total) * 100
                    results.append({
                        'window': window_name,
                        'stat_category': stat_category,
                        'side': bet_side,
                        'wins': stats['wins'],
                        'losses': stats['losses'],
                        'total': total,
                        'hit_rate': round(hit_rate, 1)
                    })

    conn.close()

    # Generate report
    report_lines = []
    report_lines.append("# Stat Category Performance Trends")
    report_lines.append(f"\n**Analysis Date:** {datetime.now().strftime('%Y-%m-%d')}")
    report_lines.append(f"**Minimum Sample:** 10 bets per stat-side\n")

    # Group by stat_category-side for comparison
    stat_comparison = defaultdict(dict)
    for item in results:
        key = f"{item['stat_category']}_{item['side']}"
        stat_comparison[key][item['window']] = item

    report_lines.append("\n## Season vs 14-Day Performance by Stat & Direction\n")
    report_lines.append("| Stat | Side | Season WR | Season Bets | 14-Day WR | 14-Day Bets | Trend |")
    report_lines.append("|------|------|-----------|-------------|-----------|-------------|-------|")

    trends = []
    for key, data in stat_comparison.items():
        if 'Season' in data and '14-Day' in data:
            season_wr = data['Season']['hit_rate']
            trend_wr = data['14-Day']['hit_rate']
            diff = trend_wr - season_wr

            trends.append({
                'key': key,
                'stat_category': data['Season']['stat_category'],
                'side': data['Season']['side'],
                'season_wr': season_wr,
                'trend_wr': trend_wr,
                'diff': diff,
                'season_bets': data['Season']['total'],
                'trend_bets': data['14-Day']['total']
            })

    # Sort by absolute change
    trends.sort(key=lambda x: abs(x['diff']), reverse=True)

    for item in trends[:30]:
        if item['diff'] > 10:
            trend_icon = "📈 IMPROVING"
        elif item['diff'] < -10:
            trend_icon = "📉 DECLINING"
        else:
            trend_icon = "➡️"

        report_lines.append(
            f"| {item['stat_category']} | {item['side']} | {item['season_wr']}% | {item['season_bets']} | "
            f"{item['trend_wr']}% | {item['trend_bets']} | {trend_icon} ({item['diff']:+.1f}%) |"
        )

    # Add summary analysis
    report_lines.append("\n## Key Findings\n")

    # Overall OVER vs UNDER
    season_over = sum(r['wins'] for r in results if r['window'] == 'Season' and r['side'] == 'OVER')
    season_over_total = sum(r['total'] for r in results if r['window'] == 'Season' and r['side'] == 'OVER')
    season_under = sum(r['wins'] for r in results if r['window'] == 'Season' and r['side'] == 'UNDER')
    season_under_total = sum(r['total'] for r in results if r['window'] == 'Season' and r['side'] == 'UNDER')

    over_wr = (season_over / season_over_total * 100) if season_over_total > 0 else 0
    under_wr = (season_under / season_under_total * 100) if season_under_total > 0 else 0

    report_lines.append(f"**Season OVER Bets:** {over_wr:.1f}% WR ({season_over}/{season_over_total})")
    report_lines.append(f"**Season UNDER Bets:** {under_wr:.1f}% WR ({season_under}/{season_under_total})")

    if abs(over_wr - under_wr) > 5:
        if over_wr > under_wr:
            report_lines.append("\n⚠️ **Imbalance detected:** OVER bets significantly outperforming UNDER bets")
        else:
            report_lines.append("\n⚠️ **Imbalance detected:** UNDER bets significantly outperforming OVER bets")
            report_lines.append("**Implication:** Model may be systematically over-projecting player stats")

    # Save report
    report_path = REPORTS_DIR / f"stat_trends_{datetime.now().strftime('%Y-%m-%d')}.md"
    with open(report_path, 'w') as f:
        f.write('\n'.join(report_lines))

    print(f"\n✅ Analyzed {len(stat_comparison)} stat-direction combos")
    print(f"📄 Report saved: {report_path}")

    return results


def main():
    """Run all trend analyses."""
    parser = argparse.ArgumentParser(description="14-day trend analysis")
    parser.add_argument("--db-path", default=DB_PATH)
    parser.add_argument("--season-start", default=SEASON_START)
    parser.add_argument("--trend-start", default=None)
    parser.add_argument("--trend-end", default=None)
    args = parser.parse_args()

    global DB_PATH, SEASON_START, TREND_WINDOW_START, TREND_WINDOW_END
    DB_PATH = args.db_path
    SEASON_START = args.season_start
    TREND_WINDOW_END = _resolve_window_end(DB_PATH, args.trend_end)

    if args.trend_start:
        TREND_WINDOW_START = args.trend_start
    else:
        end_dt = datetime.strptime(TREND_WINDOW_END, "%Y-%m-%d")
        TREND_WINDOW_START = (end_dt - timedelta(days=13)).strftime("%Y-%m-%d")

    print("\n" + "="*80)
    print("14-DAY TREND ANALYSIS")
    print("="*80)
    print(f"Season Baseline: {SEASON_START} to {TREND_WINDOW_END}")
    print(f"Recent Window: {TREND_WINDOW_START} to {TREND_WINDOW_END}")
    print("="*80)

    # Run all sections
    player_drift = analyze_player_drift()
    scheme_trends = analyze_scheme_effectiveness()
    archetype_trends = analyze_archetype_trends()
    edge_calibration = analyze_edge_calibration()
    stat_trends = analyze_stat_trends()

    # Summary
    print("\n" + "="*80)
    print("ANALYSIS COMPLETE")
    print("="*80)
    print(f"\n📊 Reports generated in: {REPORTS_DIR}/")
    print("\n📁 Files created:")
    print(f"   - player_drift_{datetime.now().strftime('%Y-%m-%d')}.md")
    print(f"   - scheme_trends_{datetime.now().strftime('%Y-%m-%d')}.md")
    print(f"   - archetype_trends_{datetime.now().strftime('%Y-%m-%d')}.md")
    print(f"   - edge_calibration_{datetime.now().strftime('%Y-%m-%d')}.md")
    print(f"   - stat_trends_{datetime.now().strftime('%Y-%m-%d')}.md")
    print("\n✅ All analyses complete")


if __name__ == '__main__':
    main()
