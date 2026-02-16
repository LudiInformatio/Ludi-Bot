#!/usr/bin/env python3
"""
14-Day Trend Analysis for Secondary Playtype Matchups.
Identifies recent spikes in specific playtype-defense interactions.
Enhanced with performance metrics from bet_recommendations table.
"""
import sys
sys.path.insert(0, '.')

from module_e import LudiCalibrator
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

def generate_markdown_report(cutoff_date, recent_total, prev_total, styles,
                             recent_counts, prev_counts, scheme_stats):
    """Generate markdown report and save to reports/ directory."""
    # Create reports directory if it doesn't exist
    reports_dir = Path('reports')
    reports_dir.mkdir(exist_ok=True)

    # Generate filename with today's date
    today = datetime.now().strftime('%Y-%m-%d')
    filename = reports_dir / f'playtype_trends_{today}.md'

    # Build markdown content
    content = f"""# Playtype Trends Analysis - 14-Day Report

**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Analysis Period:** Last 14 days (since {cutoff_date})
**Sample Size:** {recent_total} recent team-games vs {prev_total} baseline games

## Defensive Style Frequency Trends

Comparing last 14 days vs previous 15-30 day baseline:

| Defense Style | Recent % | Baseline % | Trend | Difference |
|---------------|----------|------------|-------|------------|
"""

    for style in sorted(styles):
        rec_pct = (recent_counts.get(style, 0) / recent_total * 100) if recent_total else 0
        prev_pct = (prev_counts.get(style, 0) / prev_total * 100) if prev_total else 0
        diff = rec_pct - prev_pct

        trend_label = "→ Neutral"
        if diff > 5:
            trend_label = "⬆️ HOT"
        elif diff < -5:
            trend_label = "⬇️ COLD"

        content += f"| {style} | {rec_pct:.1f}% | {prev_pct:.1f}% | {trend_label} | {diff:+.1f}% |\n"

    # Matchup Implications
    content += "\n## Matchup Implications\n\n"

    hot_styles = [s for s in styles if (recent_counts.get(s,0)/recent_total*100) > (prev_counts.get(s,0)/prev_total*100) + 2]

    if hot_styles:
        for style in hot_styles:
            diff = (recent_counts.get(style,0)/recent_total*100) - (prev_counts.get(style,0)/prev_total*100)

            if style == "BLITZ":
                content += f"### 🔥 BLITZ is trending (+{diff:.1f}%)\n\n"
                content += "- Expect MORE **[ISO_SCORER]** penalties (TOV tax)\n"
                content += "- Expect MORE **[P&R_HANDLER]** blitz taxes\n\n"
            elif style == "PAINT_PACK":
                content += f"### 🔥 PAINT_PACK is trending (+{diff:.1f}%)\n\n"
                content += "- Expect MORE **[SPOT_UP]** 3PM boosts\n"
                content += "- Expect MORE **[P&R_ROLL_MAN]** scoring boosts\n\n"
            elif style == "FUNNEL":
                content += f"### 🔥 FUNNEL is trending\n\n"
                content += "- Expect MORE **[TRANSITION]** scoring boosts\n\n"
    else:
        content += "*No significant defensive style trends detected (>2% shift required)*\n\n"

    # Performance Metrics
    content += "## Performance Metrics by Defensive Scheme (Last 14 Days)\n\n"
    content += "| Defensive Scheme | Bets | Win Rate | ROI | Net Profit |\n"
    content += "|------------------|------|----------|-----|------------|\n"

    for scheme, stats in sorted(scheme_stats.items()):
        if stats['bets'] == 0:
            continue

        win_rate = (stats['wins'] / (stats['wins'] + stats['losses']) * 100) if (stats['wins'] + stats['losses']) > 0 else 0
        total_pl = stats['profit'] + stats['loss']
        roi = (total_pl / stats['bets'] * 100) if stats['bets'] > 0 else 0

        # Add status indicator
        status = "✅" if roi > 5 else ("⚠️" if roi < -5 else "➡️")

        content += f"| {status} {scheme} | {stats['bets']} | {win_rate:.1f}% | {roi:+.1f}% | {total_pl:+.2f}u |\n"

    # Key Findings
    content += "\n## Key Findings\n\n"

    # Find best and worst schemes
    valid_schemes = {k: v for k, v in scheme_stats.items() if v['bets'] >= 5}

    if valid_schemes:
        best_scheme = max(valid_schemes.items(), key=lambda x: (x[1]['profit'] + x[1]['loss']))
        worst_scheme = min(valid_schemes.items(), key=lambda x: (x[1]['profit'] + x[1]['loss']))

        best_stats = best_scheme[1]
        worst_stats = worst_scheme[1]

        best_roi = ((best_stats['profit'] + best_stats['loss']) / best_stats['bets'] * 100) if best_stats['bets'] > 0 else 0
        worst_roi = ((worst_stats['profit'] + worst_stats['loss']) / worst_stats['bets'] * 100) if worst_stats['bets'] > 0 else 0

        content += f"### Best Performing Scheme\n\n"
        content += f"- **{best_scheme[0]}**: {best_stats['bets']} bets, {best_roi:+.1f}% ROI\n"
        content += f"- Net Profit: {best_stats['profit'] + best_stats['loss']:+.2f}u\n\n"

        content += f"### Worst Performing Scheme\n\n"
        content += f"- **{worst_scheme[0]}**: {worst_stats['bets']} bets, {worst_roi:+.1f}% ROI\n"
        content += f"- Net Profit: {worst_stats['profit'] + worst_stats['loss']:+.2f}u\n\n"
    else:
        content += "*Insufficient bet data for scheme comparison (minimum 5 bets required)*\n\n"

    content += "---\n\n*Generated by scripts/backtest_playtype_trends_14day.py*\n"

    # Write to file
    with open(filename, 'w') as f:
        f.write(content)

    print(f"\n📄 Report saved to: {filename}")
    return filename

def run_14day_trends():
    print("=" * 70)
    print("PHASE 3: 14-DAY PLAYTYPE TRENDS ANALYSIS")
    print("=" * 70)
    
    calib = LudiCalibrator(debug_log=False)
    
    # 1. Get recent games (Last 14 days)
    conn = sqlite3.connect('ludi.db')
    cursor = conn.cursor()
    cutoff_date = (datetime.now() - timedelta(days=14)).strftime('%Y-%m-%d')
    days_back_30 = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
    days_back_15 = (datetime.now() - timedelta(days=15)).strftime('%Y-%m-%d')

    print(f"📅 Analyzing games since {cutoff_date}...")
    
    # Analyze Defense Frequency (Recent 14 vs Previous 15-30)
    def get_defense_counts(start_date, end_date=None):
        query = """
        SELECT DISTINCT game_date, team_abbreviation
        FROM player_game_logs 
        WHERE game_date >= ?
        """
        params = [start_date]
        if end_date:
            query += " AND game_date <= ?"
            params.append(end_date)
            
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        style_counts = {}
        for _, team in rows:
            # Check what DEFENSE this team plays (from module_e static dict)
            # Use 'team' as opponent to see what defenses players are facing
            def_style = calib.DEFENSIVE_STYLES.get(team, "NEUTRAL")
            style_counts[def_style] = style_counts.get(def_style, 0) + 1
            
        return style_counts, len(rows)

    recent_counts, recent_total = get_defense_counts(cutoff_date)
    prev_counts, prev_total = get_defense_counts(days_back_30, days_back_15)
    
    conn.close()

    print(f"📊 Sample Size: {recent_total} recent team-games vs {prev_total} baseline.")
    
    if recent_total == 0:
        print("❌ No recent data found.")
        return

    print("\n🔍 DEFENSIVE STYLE TRENDS (Last 14 Days vs Baseline)")
    print(f"{'DEFENSE STYLE':<15} | {'RECENT %':<10} | {'PREV %':<10} | {'TREND':<10}")
    print("-" * 60)
    
    styles = set(list(recent_counts.keys()) + list(prev_counts.keys()))
    
    for style in sorted(styles):
        rec_pct = (recent_counts.get(style, 0) / recent_total * 100) if recent_total else 0
        prev_pct = (prev_counts.get(style, 0) / prev_total * 100) if prev_total else 0
        diff = rec_pct - prev_pct
        
        trend_arrow = "➡️"
        if diff > 5: trend_arrow = "⬆️ HOT"
        elif diff < -5: trend_arrow = "⬇️ COLD"
        
        print(f"{style:<15} | {rec_pct:5.1f}%     | {prev_pct:5.1f}%     | {trend_arrow} ({diff:+5.1f}%)")

    print("\n🎯 MATCHUP IMPLICATIONS")
    print("-" * 60)

    # Hot styles trigger specific matchups
    hot_styles = [s for s in styles if (recent_counts.get(s,0)/recent_total*100) > (prev_counts.get(s,0)/prev_total*100) + 2]

    for style in hot_styles:
        if style == "BLITZ":
            print(f"🔥 BLITZ is trending (+{(recent_counts.get('BLITZ',0)/recent_total*100 - prev_counts.get('BLITZ',0)/prev_total*100):.1f}%).")
            print("   -> expect MORE [ISO_SCORER] penalties (TOV tax)")
            print("   -> expect MORE [P&R_HANDLER] blitz taxes")
        elif style == "PAINT_PACK":
            print(f"🔥 PAINT_PACK is trending (+{(recent_counts.get('PAINT_PACK',0)/recent_total*100 - prev_counts.get('PAINT_PACK',0)/prev_total*100):.1f}%).")
            print("   -> expect MORE [SPOT_UP] 3PM boosts")
            print("   -> expect MORE [P&R_ROLL_MAN] scoring boosts")
        elif style == "FUNNEL":
            print(f"🔥 FUNNEL is trending.")
            print("   -> expect MORE [TRANSITION] scoring boosts")

    # Performance Metrics by Defensive Scheme
    print("\n📊 PERFORMANCE METRICS BY DEFENSIVE SCHEME (Last 14 Days)")
    print("-" * 80)

    conn = sqlite3.connect('ludi.db')
    cursor = conn.cursor()

    # Get bet performance by defensive scheme tag
    cursor.execute("""
        SELECT
            tags,
            COUNT(*) as total_bets,
            SUM(CASE WHEN outcome = 'WIN' THEN 1 ELSE 0 END) as wins,
            SUM(CASE WHEN outcome = 'LOSS' THEN 1 ELSE 0 END) as losses,
            SUM(CASE WHEN outcome = 'PUSH' THEN 1 ELSE 0 END) as pushes,
            SUM(CASE WHEN outcome = 'WIN' THEN profit_loss ELSE 0 END) as total_profit,
            SUM(CASE WHEN outcome = 'LOSS' THEN profit_loss ELSE 0 END) as total_loss
        FROM bet_recommendations
        WHERE created_at >= date('now', '-14 days')
        AND outcome IN ('WIN', 'LOSS', 'PUSH')
        AND tags IS NOT NULL
        GROUP BY tags
    """)

    bet_data = cursor.fetchall()
    conn.close()

    # Parse tags and aggregate by defensive scheme
    scheme_stats = {
        'vs_BLITZ': {'bets': 0, 'wins': 0, 'losses': 0, 'pushes': 0, 'profit': 0, 'loss': 0},
        'vs_PAINT_PACK': {'bets': 0, 'wins': 0, 'losses': 0, 'pushes': 0, 'profit': 0, 'loss': 0},
        'vs_PERIMETER': {'bets': 0, 'wins': 0, 'losses': 0, 'pushes': 0, 'profit': 0, 'loss': 0},
        'vs_FUNNEL': {'bets': 0, 'wins': 0, 'losses': 0, 'pushes': 0, 'profit': 0, 'loss': 0},
        'vs_HACKERS': {'bets': 0, 'wins': 0, 'losses': 0, 'pushes': 0, 'profit': 0, 'loss': 0},
        'vs_NEUTRAL': {'bets': 0, 'wins': 0, 'losses': 0, 'pushes': 0, 'profit': 0, 'loss': 0}
    }

    for tags_str, total, wins, losses, pushes, profit, loss in bet_data:
        if not tags_str:
            continue

        # Parse JSON tags
        import json
        try:
            tags = json.loads(tags_str)
        except:
            continue

        # Find defensive scheme tag
        for tag in tags:
            if tag.startswith('vs_'):
                if tag in scheme_stats:
                    scheme_stats[tag]['bets'] += total
                    scheme_stats[tag]['wins'] += wins
                    scheme_stats[tag]['losses'] += losses
                    scheme_stats[tag]['pushes'] += pushes
                    scheme_stats[tag]['profit'] += profit or 0
                    scheme_stats[tag]['loss'] += loss or 0

    print(f"{'Scheme':<15} | {'Bets':<6} | {'Win%':<8} | {'ROI':<10} | {'Profit':<10}")
    print("-" * 80)

    for scheme, stats in sorted(scheme_stats.items()):
        if stats['bets'] == 0:
            continue

        win_rate = (stats['wins'] / (stats['wins'] + stats['losses']) * 100) if (stats['wins'] + stats['losses']) > 0 else 0
        total_pl = stats['profit'] + stats['loss']
        roi = (total_pl / stats['bets'] * 100) if stats['bets'] > 0 else 0

        print(f"{scheme:<15} | {stats['bets']:<6} | {win_rate:>6.1f}% | {roi:>+8.1f}% | {total_pl:>+9.2f}u")

    print("\n✅ Phase 3 Trend Analysis Complete")

    # Generate markdown report
    generate_markdown_report(cutoff_date, recent_total, prev_total, styles,
                            recent_counts, prev_counts, scheme_stats)

if __name__ == "__main__":
    run_14day_trends()
