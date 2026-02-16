#!/usr/bin/env python3
"""
Model Performance Analysis Script

Purpose: Analyze betting model performance across multiple dimensions to identify
         profitable patterns and calibration opportunities.

Usage:
    python scripts/analyze_model_performance.py [--output markdown|console]

Output:
    - Six comprehensive analysis tables
    - Summary statistics and actionable recommendations
    - Optional markdown report file

Author: Ludi Informatio
Date: February 2, 2026
"""

import os
import sys
import sqlite3
import argparse
from datetime import datetime
from collections import defaultdict

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


class ModelPerformanceAnalyzer:
    def __init__(self, db_path='ludi.db'):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row

        # Data containers
        self.settled_bets = []
        self.results = {}

    def load_settled_bets(self):
        """Load all settled bets from database."""
        query = '''
            SELECT
                id,
                player_name,
                stat_category,
                line,
                bet_side as direction,
                projection,
                true_edge as edge_pct,
                units,
                outcome as result,
                profit_loss,
                position,
                archetype,
                game_date,
                bookmaker,
                odds_over,
                odds_under,
                actual_result
            FROM bet_recommendations
            WHERE outcome IS NOT NULL
            ORDER BY game_date DESC
        '''

        cursor = self.conn.cursor()
        cursor.execute(query)
        self.settled_bets = [dict(row) for row in cursor.fetchall()]

        print(f"✅ Loaded {len(self.settled_bets)} settled bets")
        print(f"   Date range: {self.settled_bets[-1]['game_date']} to {self.settled_bets[0]['game_date']}")
        print()

    def analyze_stat_category_performance(self):
        """Table 1: Overall performance by stat category."""
        stats = defaultdict(lambda: {
            'bets': 0, 'wins': 0, 'losses': 0,
            'units_wagered': 0.0, 'profit': 0.0
        })

        for bet in self.settled_bets:
            stat = bet['stat_category']
            stats[stat]['bets'] += 1
            stats[stat]['units_wagered'] += bet['units'] or 0
            stats[stat]['profit'] += bet['profit_loss'] or 0

            if bet['result'] == 'WIN':
                stats[stat]['wins'] += 1
            elif bet['result'] == 'LOSS':
                stats[stat]['losses'] += 1

        # Build result table
        table = []
        for stat in sorted(stats.keys()):
            s = stats[stat]
            win_pct = (s['wins'] / s['bets'] * 100) if s['bets'] > 0 else 0
            roi = (s['profit'] / s['units_wagered'] * 100) if s['units_wagered'] > 0 else 0

            table.append({
                'Stat': stat,
                'Bets': s['bets'],
                'Wins': s['wins'],
                'Losses': s['losses'],
                'Win%': f"{win_pct:.1f}%",
                'Units': f"{s['units_wagered']:.1f}",
                'Profit': f"{s['profit']:+.1f}",
                'ROI%': f"{roi:+.1f}%"
            })

        self.results['stat_category'] = table

    def analyze_over_under_by_stat(self):
        """Table 2: OVER vs UNDER performance by stat category."""
        stats = defaultdict(lambda: defaultdict(lambda: {
            'bets': 0, 'wins': 0, 'profit': 0.0
        }))

        for bet in self.settled_bets:
            stat = bet['stat_category']
            direction = bet['direction']

            stats[stat][direction]['bets'] += 1
            stats[stat][direction]['profit'] += bet['profit_loss'] or 0

            if bet['result'] == 'WIN':
                stats[stat][direction]['wins'] += 1

        # Build result table
        table = []
        for stat in sorted(stats.keys()):
            for direction in ['OVER', 'UNDER']:
                if direction not in stats[stat]:
                    continue

                s = stats[stat][direction]
                win_pct = (s['wins'] / s['bets'] * 100) if s['bets'] > 0 else 0

                # Recommendation logic
                if win_pct >= 55 and s['profit'] > 50:
                    recommendation = "EXCELLENT"
                elif win_pct >= 52 and s['profit'] > 0:
                    recommendation = "KEEP"
                elif win_pct < 48 or s['profit'] < -50:
                    recommendation = "FILTER OUT"
                else:
                    recommendation = "MONITOR"

                table.append({
                    'Stat': stat,
                    'Direction': direction,
                    'Bets': s['bets'],
                    'Win%': f"{win_pct:.1f}%",
                    'Profit': f"{s['profit']:+.1f}",
                    'Recommendation': recommendation
                })

        # Sort by profit descending
        table.sort(key=lambda x: float(x['Profit']), reverse=True)

        self.results['over_under'] = table

    def analyze_position_performance(self):
        """Table 3: Performance by player position."""
        positions = defaultdict(lambda: defaultdict(lambda: {
            'bets': 0, 'wins': 0, 'profit': 0.0
        }))

        for bet in self.settled_bets:
            pos = bet['position'] or 'UNK'
            stat = bet['stat_category']

            positions[pos]['_total']['bets'] += 1
            positions[pos]['_total']['profit'] += bet['profit_loss'] or 0
            positions[pos][stat]['bets'] += 1
            positions[pos][stat]['profit'] += bet['profit_loss'] or 0

            if bet['result'] == 'WIN':
                positions[pos]['_total']['wins'] += 1
                positions[pos][stat]['wins'] += 1

        # Build result table
        table = []
        for pos in sorted(positions.keys(), key=lambda x: (x == 'UNK', x)):
            total = positions[pos]['_total']
            win_pct = (total['wins'] / total['bets'] * 100) if total['bets'] > 0 else 0

            # Find best and worst stats
            stat_performance = []
            for stat in positions[pos]:
                if stat == '_total':
                    continue
                s = positions[pos][stat]
                if s['bets'] >= 20:  # Minimum sample size
                    stat_performance.append((stat, s['profit']))

            stat_performance.sort(key=lambda x: x[1], reverse=True)

            best_stat = stat_performance[0][0] if stat_performance else 'N/A'
            worst_stat = stat_performance[-1][0] if stat_performance else 'N/A'

            table.append({
                'Position': pos,
                'Bets': total['bets'],
                'Win%': f"{win_pct:.1f}%",
                'Profit': f"{total['profit']:+.1f}",
                'Best Stat': best_stat,
                'Worst Stat': worst_stat
            })

        # Sort by profit descending
        table.sort(key=lambda x: float(x['Profit']), reverse=True)

        self.results['position'] = table

    def analyze_archetype_performance(self):
        """Table 4: Performance by player archetype."""
        archetypes = defaultdict(lambda: {
            'bets': 0, 'wins': 0, 'units_wagered': 0.0, 'profit': 0.0
        })

        for bet in self.settled_bets:
            arch = bet['archetype'] or 'UNKNOWN'

            archetypes[arch]['bets'] += 1
            archetypes[arch]['units_wagered'] += bet['units'] or 0
            archetypes[arch]['profit'] += bet['profit_loss'] or 0

            if bet['result'] == 'WIN':
                archetypes[arch]['wins'] += 1

        # Build result table
        table = []
        for arch in sorted(archetypes.keys()):
            a = archetypes[arch]
            win_pct = (a['wins'] / a['bets'] * 100) if a['bets'] > 0 else 0
            units_per_bet = (a['units_wagered'] / a['bets']) if a['bets'] > 0 else 0

            table.append({
                'Archetype': arch,
                'Bets': a['bets'],
                'Win%': f"{win_pct:.1f}%",
                'Profit': f"{a['profit']:+.1f}",
                'Units/Bet': f"{units_per_bet:.2f}"
            })

        # Sort by profit descending
        table.sort(key=lambda x: float(x['Profit']), reverse=True)

        self.results['archetype'] = table

    def analyze_edge_bucket_performance(self):
        """Table 5: Performance by edge bucket (calibration check)."""
        buckets = {
            '5-10%': {'range': (5, 10), 'bets': 0, 'wins': 0},
            '10-15%': {'range': (10, 15), 'bets': 0, 'wins': 0},
            '15-20%': {'range': (15, 20), 'bets': 0, 'wins': 0},
            '20-25%': {'range': (20, 25), 'bets': 0, 'wins': 0},
            '25%+': {'range': (25, 999), 'bets': 0, 'wins': 0}
        }

        for bet in self.settled_bets:
            edge = bet['edge_pct'] or 0

            # Find appropriate bucket
            for bucket_name, bucket_data in buckets.items():
                min_edge, max_edge = bucket_data['range']
                if min_edge <= edge < max_edge:
                    bucket_data['bets'] += 1
                    if bet['result'] == 'WIN':
                        bucket_data['wins'] += 1
                    break

        # Build result table
        table = []
        for bucket_name in ['5-10%', '10-15%', '15-20%', '20-25%', '25%+']:
            b = buckets[bucket_name]
            actual_win_pct = (b['wins'] / b['bets'] * 100) if b['bets'] > 0 else 0

            # Expected win % is roughly 52.4% (break-even at -110) + (edge * 0.5)
            # This is a simplified model
            min_edge, max_edge = b['range']
            mid_edge = (min_edge + max_edge) / 2 if max_edge < 999 else min_edge + 5
            expected_win_pct = 52.4 + (mid_edge * 0.4)  # Rough approximation

            calibration_diff = actual_win_pct - expected_win_pct

            if abs(calibration_diff) <= 2:
                calibration_status = "EXCELLENT"
            elif abs(calibration_diff) <= 5:
                calibration_status = "GOOD"
            elif calibration_diff > 0:
                calibration_status = "UNDERBET"
            else:
                calibration_status = "OVERCONFIDENT"

            table.append({
                'Edge Range': bucket_name,
                'Bets': b['bets'],
                'Win%': f"{actual_win_pct:.1f}%",
                'Expected Win%': f"{expected_win_pct:.1f}%",
                'Calibration': f"{calibration_diff:+.1f}%",
                'Status': calibration_status
            })

        self.results['edge_bucket'] = table

    def generate_summary_recommendations(self):
        """Table 6: Summary and actionable recommendations."""
        summary = {
            'profitable': [],
            'leaks': [],
            'calibration_notes': [],
            'archetype_notes': []
        }

        # Find most profitable combos
        over_under_table = self.results['over_under']
        for row in over_under_table[:5]:  # Top 5
            if float(row['Profit']) > 50:
                summary['profitable'].append(
                    f"{row['Stat']} {row['Direction']}: {row['Profit']} units "
                    f"({row['Win%']}, {row['Bets']} bets)"
                )

        # Find worst leaks
        for row in reversed(over_under_table[-5:]):  # Bottom 5
            if float(row['Profit']) < -50:
                summary['leaks'].append(
                    f"{row['Stat']} {row['Direction']}: {row['Profit']} units "
                    f"({row['Win%']}, {row['Bets']} bets)"
                )

        # Archetype insights
        archetype_table = self.results['archetype']
        for row in archetype_table[:3]:  # Top 3 archetypes
            if float(row['Profit']) > 30:
                summary['archetype_notes'].append(
                    f"{row['Archetype']}: {row['Profit']} units ({row['Win%']}, {row['Bets']} bets)"
                )

        # Calibration insights
        edge_table = self.results['edge_bucket']
        for row in edge_table:
            if row['Status'] in ['OVERCONFIDENT', 'UNDERBET']:
                summary['calibration_notes'].append(
                    f"{row['Edge Range']}: {row['Status']} by {row['Calibration']}"
                )

        self.results['summary'] = summary

    def print_results(self, output_format='console'):
        """Print all analysis results."""
        print("\n" + "=" * 100)
        print("MODEL PERFORMANCE ANALYSIS")
        print("=" * 100)
        print(f"Analysis Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Total Settled Bets: {len(self.settled_bets)}")
        print(f"Date Range: {self.settled_bets[-1]['game_date']} to {self.settled_bets[0]['game_date']}")
        print("=" * 100)

        # Table 1: Stat Category Performance
        print("\n" + "=" * 100)
        print("TABLE 1: STAT CATEGORY PERFORMANCE")
        print("=" * 100)
        self._print_table(self.results['stat_category'])

        # Table 2: OVER vs UNDER
        print("\n" + "=" * 100)
        print("TABLE 2: OVER vs UNDER BY STAT")
        print("=" * 100)
        self._print_table(self.results['over_under'][:20])  # Show top 20

        # Table 3: Position Performance
        print("\n" + "=" * 100)
        print("TABLE 3: POSITION PERFORMANCE")
        print("=" * 100)
        self._print_table(self.results['position'])

        # Table 4: Archetype Performance
        print("\n" + "=" * 100)
        print("TABLE 4: ARCHETYPE PERFORMANCE")
        print("=" * 100)
        self._print_table(self.results['archetype'][:15])  # Show top 15

        # Table 5: Edge Bucket Analysis
        print("\n" + "=" * 100)
        print("TABLE 5: EDGE BUCKET ANALYSIS (Calibration Check)")
        print("=" * 100)
        self._print_table(self.results['edge_bucket'])

        # Table 6: Summary & Recommendations
        print("\n" + "=" * 100)
        print("TABLE 6: SUMMARY & RECOMMENDATIONS")
        print("=" * 100)
        self._print_summary()

        print("\n" + "=" * 100)
        print("ANALYSIS COMPLETE")
        print("=" * 100)

    def _print_table(self, table):
        """Print a table in console format."""
        if not table:
            print("  No data available")
            return

        # Get column widths
        headers = list(table[0].keys())
        col_widths = {}
        for header in headers:
            col_widths[header] = max(
                len(header),
                max(len(str(row[header])) for row in table)
            )

        # Print header
        header_row = "  " + " | ".join(h.ljust(col_widths[h]) for h in headers)
        print(header_row)
        print("  " + "-" * (len(header_row) - 2))

        # Print rows
        for row in table:
            row_str = "  " + " | ".join(str(row[h]).ljust(col_widths[h]) for h in headers)
            print(row_str)

    def _print_summary(self):
        """Print summary recommendations."""
        summary = self.results['summary']

        print("\n  PROFITABLE PATTERNS:")
        for item in summary['profitable']:
            print(f"    ✅ {item}")

        if not summary['profitable']:
            print("    ⚠️  No highly profitable patterns found (>50 units)")

        print("\n  LEAKS TO FIX:")
        for item in summary['leaks']:
            print(f"    ❌ {item}")

        if not summary['leaks']:
            print("    ✅ No major leaks detected (<-50 units)")

        print("\n  TOP ARCHETYPES:")
        for item in summary['archetype_notes']:
            print(f"    💎 {item}")

        print("\n  CALIBRATION NOTES:")
        for item in summary['calibration_notes']:
            print(f"    ⚠️  {item}")

        if not summary['calibration_notes']:
            print("    ✅ Model is well-calibrated across all edge buckets")

    def save_markdown_report(self, output_path='reports/performance_analysis_feb2.md'):
        """Save results as markdown file."""
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        with open(output_path, 'w') as f:
            f.write(f"# Model Performance Analysis\n\n")
            f.write(f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  \n")
            f.write(f"**Total Settled Bets:** {len(self.settled_bets)}  \n")
            f.write(f"**Date Range:** {self.settled_bets[-1]['game_date']} to {self.settled_bets[0]['game_date']}  \n\n")

            f.write("---\n\n")

            # Write all tables
            self._write_markdown_table(f, "Table 1: Stat Category Performance", self.results['stat_category'])
            self._write_markdown_table(f, "Table 2: OVER vs UNDER by Stat (Top 20)", self.results['over_under'][:20])
            self._write_markdown_table(f, "Table 3: Position Performance", self.results['position'])
            self._write_markdown_table(f, "Table 4: Archetype Performance (Top 15)", self.results['archetype'][:15])
            self._write_markdown_table(f, "Table 5: Edge Bucket Analysis", self.results['edge_bucket'])

            # Write summary
            f.write("## Table 6: Summary & Recommendations\n\n")

            summary = self.results['summary']

            f.write("### Profitable Patterns\n\n")
            for item in summary['profitable']:
                f.write(f"- ✅ {item}\n")

            f.write("\n### Leaks to Fix\n\n")
            for item in summary['leaks']:
                f.write(f"- ❌ {item}\n")

            f.write("\n### Top Archetypes\n\n")
            for item in summary['archetype_notes']:
                f.write(f"- 💎 {item}\n")

            f.write("\n### Calibration Notes\n\n")
            for item in summary['calibration_notes']:
                f.write(f"- ⚠️ {item}\n")

            if not summary['calibration_notes']:
                f.write("- ✅ Model is well-calibrated across all edge buckets\n")

        print(f"\n📄 Markdown report saved to: {output_path}")

    def _write_markdown_table(self, f, title, table):
        """Write a table in markdown format."""
        f.write(f"## {title}\n\n")

        if not table:
            f.write("*No data available*\n\n")
            return

        headers = list(table[0].keys())

        # Header row
        f.write("| " + " | ".join(headers) + " |\n")
        f.write("|" + "|".join(["-" * (len(h) + 2) for h in headers]) + "|\n")

        # Data rows
        for row in table:
            f.write("| " + " | ".join(str(row[h]) for h in headers) + " |\n")

        f.write("\n")

    def run(self, output_format='console'):
        """Execute full analysis pipeline."""
        print("\n" + "=" * 100)
        print("STARTING MODEL PERFORMANCE ANALYSIS")
        print("=" * 100)

        # Load data
        self.load_settled_bets()

        # Run analyses
        print("Running analyses...")
        self.analyze_stat_category_performance()
        self.analyze_over_under_by_stat()
        self.analyze_position_performance()
        self.analyze_archetype_performance()
        self.analyze_edge_bucket_performance()
        self.generate_summary_recommendations()
        print("✅ All analyses complete\n")

        # Output results
        self.print_results(output_format)

        if output_format == 'markdown':
            self.save_markdown_report()

        self.conn.close()


def main():
    parser = argparse.ArgumentParser(description='Analyze model betting performance')
    parser.add_argument(
        '--output',
        choices=['console', 'markdown'],
        default='console',
        help='Output format (default: console)'
    )

    args = parser.parse_args()

    analyzer = ModelPerformanceAnalyzer()
    analyzer.run(output_format=args.output)


if __name__ == '__main__':
    main()
