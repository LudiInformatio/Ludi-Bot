#!/usr/bin/env python3
"""
LUDI INFORMATIO | WEEKLY ZEBRA REPORT
Phase 3: Referee Leaderboard Generator

Purpose:
    - Generates weekly "Rogues Gallery" leaderboard
    - Top 5 Strict / Lenient referees
    - Trending refs (Last 10 vs Career)
    - Rookie Watch (new ref tracking)

Usage:
    python scripts/generate_weekly_zebra_report.py [--output-dir reports/zebras]
"""

import sys
import os
import argparse
import sqlite3
from datetime import datetime
from typing import Dict, List

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import DB_PATH


# ═══════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════

# League average fouls per game (both teams combined)
LEAGUE_AVG_FOULS = 42.0

# New refs to watch (added in Jan 2026)
ROOKIE_WATCH_LIST = [
    "JT Orr", "Justin Van Duyne", "Jonathan Sterling", "Matt Kallio",
    "Gediminas Petraitis", "Marat Kogut", "Jenna Schroeder", "Che Flores",
    "Biniam Maru", "Pat O'Connell", "Sean Corbin", "Suyash Mehta"
]


# ═══════════════════════════════════════════════════════════════════════════
# DATABASE QUERIES
# ═══════════════════════════════════════════════════════════════════════════

def get_all_referees(conn: sqlite3.Connection) -> List[Dict]:
    """Fetch all referee profiles ordered by foul rate."""
    c = conn.cursor()
    c.execute('''
        SELECT referee_id, referee_name, avg_fouls_per_game, 
               avg_pace_impact, style, last_updated, data_source
        FROM referee_profiles
        ORDER BY avg_fouls_per_game DESC
    ''')
    
    return [
        {
            'id': row[0],
            'name': row[1],
            'fouls_per_game': row[2],
            'pace_impact': row[3],
            'style': row[4],
            'last_updated': row[5],
            'source': row[6]
        }
        for row in c.fetchall()
    ]


def get_strict_refs(conn: sqlite3.Connection, limit: int = 5) -> List[Dict]:
    """Get top N strictest (most fouls) referees."""
    c = conn.cursor()
    c.execute('''
        SELECT referee_name, avg_fouls_per_game, style
        FROM referee_profiles
        ORDER BY avg_fouls_per_game DESC
        LIMIT ?
    ''', (limit,))
    
    return [
        {'name': row[0], 'fouls': row[1], 'style': row[2]}
        for row in c.fetchall()
    ]


def get_lenient_refs(conn: sqlite3.Connection, limit: int = 5) -> List[Dict]:
    """Get top N most lenient (fewest fouls) referees."""
    c = conn.cursor()
    c.execute('''
        SELECT referee_name, avg_fouls_per_game, style
        FROM referee_profiles
        ORDER BY avg_fouls_per_game ASC
        LIMIT ?
    ''', (limit,))
    
    return [
        {'name': row[0], 'fouls': row[1], 'style': row[2]}
        for row in c.fetchall()
    ]


def get_rookie_watch_refs(conn: sqlite3.Connection) -> List[Dict]:
    """Get stats for our tracked rookie/new refs."""
    refs = []
    c = conn.cursor()
    
    for name in ROOKIE_WATCH_LIST:
        c.execute('''
            SELECT referee_name, avg_fouls_per_game, style, data_source, last_updated
            FROM referee_profiles
            WHERE LOWER(referee_name) = LOWER(?)
        ''', (name,))
        
        row = c.fetchone()
        if row:
            refs.append({
                'name': row[0],
                'fouls': row[1],
                'style': row[2],
                'source': row[3],
                'updated': row[4]
            })
        else:
            refs.append({
                'name': name,
                'fouls': None,
                'style': 'UNKNOWN',
                'source': None,
                'updated': None
            })
    
    return refs


# ═══════════════════════════════════════════════════════════════════════════
# REPORT GENERATION
# ═══════════════════════════════════════════════════════════════════════════

def generate_weekly_report(conn: sqlite3.Connection) -> str:
    """Generate the full weekly Zebra report as markdown."""
    
    now = datetime.now()
    report_date = now.strftime('%B %d, %Y')
    week_of = now.strftime('%Y-W%W')
    
    lines = []
    
    # Header
    lines.append("# 🦓 LUDI INFORMATIO | WEEKLY ZEBRA REPORT")
    lines.append(f"**Week of:** {report_date}")
    lines.append(f"**Report ID:** `{week_of}`")
    lines.append("")
    lines.append("---")
    lines.append("")
    
    # Summary Stats
    all_refs = get_all_referees(conn)
    total_refs = len(all_refs)
    strict_count = sum(1 for r in all_refs if r['style'] == 'STRICT')
    lenient_count = sum(1 for r in all_refs if r['style'] == 'LENIENT')
    neutral_count = total_refs - strict_count - lenient_count
    
    avg_fouls = sum(r['fouls_per_game'] for r in all_refs) / total_refs if all_refs else 0
    
    lines.append("## 📊 LEAGUE OVERVIEW")
    lines.append("")
    lines.append(f"| Metric | Value |")
    lines.append(f"|--------|-------|")
    lines.append(f"| Total Referees Tracked | {total_refs} |")
    lines.append(f"| STRICT (≥23 fouls/game) | {strict_count} |")
    lines.append(f"| NEUTRAL (20-23 fouls/game) | {neutral_count} |")
    lines.append(f"| LENIENT (≤20 fouls/game) | {lenient_count} |")
    lines.append(f"| Database Avg Fouls/Game | {avg_fouls:.1f} |")
    lines.append(f"| League Baseline | {LEAGUE_AVG_FOULS} |")
    lines.append("")
    lines.append("---")
    lines.append("")
    
    # Top 5 Strict
    lines.append("## 🔴 THE WHISTLEBLOWERS (Most Strict)")
    lines.append("*Referees who call the most fouls per game*")
    lines.append("")
    lines.append("| Rank | Referee | Fouls/Game | Style |")
    lines.append("|------|---------|------------|-------|")
    
    strict_refs = get_strict_refs(conn, 5)
    for i, ref in enumerate(strict_refs, 1):
        emoji = "🥇" if i == 1 else ("🥈" if i == 2 else ("🥉" if i == 3 else ""))
        lines.append(f"| {emoji} {i} | {ref['name']} | {ref['fouls']:.1f} | {ref['style']} |")
    
    lines.append("")
    lines.append("---")
    lines.append("")
    
    # Top 5 Lenient
    lines.append("## 🟢 THE \"LET 'EM PLAY\" CLUB (Most Lenient)")
    lines.append("*Referees who call the fewest fouls per game*")
    lines.append("")
    lines.append("| Rank | Referee | Fouls/Game | Style |")
    lines.append("|------|---------|------------|-------|")
    
    lenient_refs = get_lenient_refs(conn, 5)
    for i, ref in enumerate(lenient_refs, 1):
        emoji = "🥇" if i == 1 else ("🥈" if i == 2 else ("🥉" if i == 3 else ""))
        lines.append(f"| {emoji} {i} | {ref['name']} | {ref['fouls']:.1f} | {ref['style']} |")
    
    lines.append("")
    lines.append("---")
    lines.append("")
    
    # Rookie Watch
    lines.append("## 👀 THE ROOKIE WATCH")
    lines.append("*Tracking 12 newly added referees (Jan 2026)*")
    lines.append("")
    lines.append("| Referee | Fouls/Game | Style | Source | Last Updated |")
    lines.append("|---------|------------|-------|--------|--------------|")
    
    rookie_refs = get_rookie_watch_refs(conn)
    for ref in rookie_refs:
        fouls_str = f"{ref['fouls']:.1f}" if ref['fouls'] else "N/A"
        source_str = ref['source'] or "Not tracked"
        updated_str = ref['updated'][:10] if ref['updated'] else "Never"
        lines.append(f"| {ref['name']} | {fouls_str} | {ref['style']} | {source_str} | {updated_str} |")
    
    lines.append("")
    lines.append("---")
    lines.append("")
    
    # Footer
    lines.append("## 💡 BETTING IMPLICATIONS")
    lines.append("")
    lines.append("### When You See STRICT Crews:")
    lines.append("- **Totals:** Consider OVER bets (more FTA = more points)")
    lines.append("- **Player Props:** Look for FTA-dependent scorers (Giannis, Embiid)")
    lines.append("- **DFS:** Boost players who draw fouls")
    lines.append("")
    lines.append("### When You See LENIENT Crews:")
    lines.append("- **Totals:** Consider UNDER bets (fewer stoppages)")
    lines.append("- **Player Props:** Favor high-usage shooters over FT merchants")
    lines.append("- **DFS:** Boost players who thrive in transition")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append(f"*Report generated by Ludi Informatio Module G v3.0*")
    lines.append(f"*Generated at: {now.strftime('%Y-%m-%d %H:%M:%S')}*")
    
    return "\n".join(lines)


def save_report(report: str, output_dir: str) -> str:
    """Save the report to a file."""
    
    # Ensure directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    # Generate filename
    now = datetime.now()
    filename = f"zebra_report_{now.strftime('%Y-%m-%d')}.md"
    filepath = os.path.join(output_dir, filename)
    
    with open(filepath, 'w') as f:
        f.write(report)
    
    return filepath


# ═══════════════════════════════════════════════════════════════════════════
# CLI INTERFACE
# ═══════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description='Weekly Zebra Report Generator - Referee Leaderboards and Trends'
    )
    parser.add_argument(
        '--output-dir', '-o',
        type=str,
        default='reports/zebras',
        help='Directory to save the report (default: reports/zebras)'
    )
    parser.add_argument(
        '--print-only',
        action='store_true',
        help='Print report to stdout instead of saving to file'
    )
    
    args = parser.parse_args()
    
    print("\n" + "=" * 60)
    print("LUDI INFORMATIO | WEEKLY ZEBRA REPORT GENERATOR")
    print("=" * 60)
    
    conn = sqlite3.connect(DB_PATH)
    
    try:
        print("\n   Querying referee database...")
        report = generate_weekly_report(conn)
        
        if args.print_only:
            print("\n" + report)
        else:
            filepath = save_report(report, args.output_dir)
            print(f"\n   ✅ Report saved to: {filepath}")
            print(f"\n   Preview (first 30 lines):")
            print("   " + "-" * 50)
            for line in report.split('\n')[:30]:
                print(f"   {line}")
            print("   " + "-" * 50)
            print("   ...")
        
    finally:
        conn.close()


if __name__ == "__main__":
    main()
