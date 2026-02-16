"""
Phase 4: B2B Fatigue - 21-Day Backtest Validation

Analyzes fatigue adjustment performance using real game results from last 21 days.

Metrics:
- Mean Error (Actual - Predicted)
- RMSE
- Over/Under Projection %
- Sample Size per Scenario

Scenarios Tested:
1. Road B2B (Guard vs Non-Guard)
2. Home B2B (Guard vs Non-Guard)
3. Rested Home (3+ days rest)
4. Schedule Density (4-in-5 nights)
5. Normal Rest (Control Group)

Context:
Dec 20-Jan 16 backtest showed B2B players OUTPERFORMED by +2.7% PTS.
This 21-day test validates if trend continues.
"""

import sys
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict
import math

sys.path.append(str(Path(__file__).parent.parent))

class FatigueBacktest:
    def __init__(self, days: int = 21):
        self.days = days
        self.conn = sqlite3.connect('ludi.db')
        self.results = defaultdict(list)

    def get_player_baseline(self, player_name: str, game_date: str) -> dict:
        """Get player's season average BEFORE the game date."""
        cursor = self.conn.cursor()

        # Get season avg up to (but not including) this game
        cursor.execute("""
            SELECT
                AVG(pts) as avg_pts,
                AVG(ast) as avg_ast,
                AVG(reb) as avg_reb,
                AVG(minutes) as avg_min,
                team_abbreviation,
                COUNT(*) as games
            FROM player_game_logs
            WHERE player_name = ?
            AND game_date < ?
            AND game_date >= date('now', '-90 days')
            GROUP BY player_name
            HAVING COUNT(*) >= 5
        """, (player_name, game_date))

        row = cursor.fetchone()

        if not row or row[5] < 5:
            return None

        return {
            'baseline_pts': row[0] or 0,
            'baseline_ast': row[1] or 0,
            'baseline_reb': row[2] or 0,
            'baseline_min': row[3] or 0,
            'team': row[4],
            'games': row[5]
        }

    def get_player_position(self, player_name: str) -> str:
        """Get player position from players table."""
        cursor = self.conn.cursor()

        cursor.execute("""
            SELECT position FROM players
            WHERE name = ? AND season_id = '22025'
            AND position != 'UNK'
            ORDER BY updated_at DESC
            LIMIT 1
        """, (player_name,))

        row = cursor.fetchone()
        return row[0] if row else 'UNK'

    def determine_schedule_scenario(self, player_name: str, team: str,
                                    game_date: str) -> dict:
        """Determine schedule scenario for this game."""
        cursor = self.conn.cursor()

        game_dt = datetime.strptime(game_date, '%Y-%m-%d')

        # Get team's recent games
        cursor.execute("""
            SELECT DISTINCT game_date, matchup
            FROM player_game_logs
            WHERE team_abbreviation = ?
            AND game_date < ?
            AND game_date >= date(?, '-10 days')
            ORDER BY game_date DESC
        """, (team, game_date, game_date))

        past_games = cursor.fetchall()

        # Determine if road game (matchup contains '@')
        cursor.execute("""
            SELECT matchup FROM player_game_logs
            WHERE player_name = ? AND game_date = ?
            LIMIT 1
        """, (player_name, game_date))

        matchup_row = cursor.fetchone()
        is_road = False
        if matchup_row and matchup_row[0]:
            is_road = '@' in matchup_row[0]

        # Check for back-to-back
        is_b2b = False
        rest_days = 999

        if past_games:
            last_game_date = past_games[0][0]
            last_game_dt = datetime.strptime(last_game_date, '%Y-%m-%d')
            rest_days = (game_dt - last_game_dt).days
            is_b2b = (rest_days == 1)

        # Count games in last 5 days
        games_in_5_days = len([g for g in past_games
                               if (game_dt - datetime.strptime(g[0], '%Y-%m-%d')).days <= 5])

        return {
            'is_back_to_back': is_b2b,
            'is_road': is_road,
            'rest_days': rest_days,
            'games_in_last_5_days': games_in_5_days
        }

    def apply_fatigue_modifiers(self, baseline_pts: float, scenario: dict,
                                position: str) -> dict:
        """Apply fatigue modifiers to baseline projection."""
        predicted_pts = baseline_pts
        modifiers_applied = []

        is_b2b = scenario['is_back_to_back']
        is_road = scenario['is_road']
        rest_days = scenario['rest_days']
        games_in_5 = scenario['games_in_last_5_days']

        is_guard = position in ['G', 'PG', 'SG', 'G-F']

        # B2B Logic (V5.2 - Updated Feb 15, 2026)
        if is_b2b:
            if is_road:
                predicted_pts *= 0.952  # Road B2B (-4.8%)
                modifiers_applied.append('Road_B2B_-4.8%')
            else:
                predicted_pts *= 0.985  # Home B2B (-1.5%)
                modifiers_applied.append('Home_B2B_-1.5%')

            # Guard tax
            if is_guard:
                predicted_pts *= 0.98  # Guard tax (-2%)
                modifiers_applied.append('Guard_Tax_-2%')

        # Rested Home Edge
        elif rest_days >= 3 and not is_road:
            predicted_pts *= 1.03  # +3% boost
            modifiers_applied.append('Rested_Home_+3%')

        # Schedule Density (V5.2)
        if games_in_5 >= 3:
            predicted_pts *= 0.99  # -1% density tax
            modifiers_applied.append('Density_4in5_-1%')

        return {
            'predicted_pts': predicted_pts,
            'modifiers': modifiers_applied
        }

    def classify_scenario(self, scenario: dict, position: str) -> str:
        """Classify scenario into analysis bucket."""
        is_b2b = scenario['is_back_to_back']
        is_road = scenario['is_road']
        rest_days = scenario['rest_days']
        games_in_5 = scenario['games_in_last_5_days']
        is_guard = position in ['G', 'PG', 'SG', 'G-F']

        if is_b2b:
            if is_road:
                return 'Road_B2B_Guard' if is_guard else 'Road_B2B_NonGuard'
            else:
                return 'Home_B2B_Guard' if is_guard else 'Home_B2B_NonGuard'
        elif rest_days >= 3 and not is_road:
            return 'Rested_Home'
        elif games_in_5 >= 3:
            return 'Density_4in5'
        else:
            return 'Normal_Rest'

    def run_backtest(self):
        """Run 21-day backtest."""
        print(f"\n{'='*70}")
        print(f"  PHASE 4: B2B FATIGUE - 21-DAY BACKTEST")
        print(f"{'='*70}")
        print(f"\nAnalyzing games from last {self.days} days...")

        cursor = self.conn.cursor()

        # Get all player-games from last 21 days
        cursor.execute("""
            SELECT
                player_name,
                team_abbreviation,
                game_date,
                pts,
                ast,
                reb,
                minutes
            FROM player_game_logs
            WHERE game_date >= date('now', ?)
            AND game_date < date('now')
            AND minutes >= 10
            ORDER BY game_date DESC
        """, (f'-{self.days} days',))

        games = cursor.fetchall()

        print(f"Found {len(games)} player-games with 10+ minutes")
        print(f"\nProcessing schedule scenarios...")

        processed = 0
        skipped = 0

        for player_name, team, game_date, actual_pts, actual_ast, actual_reb, actual_min in games:
            # Get baseline
            baseline = self.get_player_baseline(player_name, game_date)
            if not baseline:
                skipped += 1
                continue

            # Get position
            position = self.get_player_position(player_name)

            # Get schedule scenario
            scenario = self.determine_schedule_scenario(player_name, team, game_date)

            # Apply fatigue modifiers
            prediction = self.apply_fatigue_modifiers(
                baseline['baseline_pts'],
                scenario,
                position
            )

            # Classify scenario
            scenario_type = self.classify_scenario(scenario, position)

            # Store result
            error = actual_pts - prediction['predicted_pts']
            self.results[scenario_type].append({
                'player': player_name,
                'team': team,
                'date': game_date,
                'position': position,
                'baseline_pts': baseline['baseline_pts'],
                'predicted_pts': prediction['predicted_pts'],
                'actual_pts': actual_pts,
                'error': error,
                'modifiers': prediction['modifiers']
            })

            processed += 1

            if processed % 500 == 0:
                print(f"  Processed {processed} games...")

        print(f"\n✅ Processed {processed} player-games")
        print(f"⚠️  Skipped {skipped} (insufficient baseline data)")

    def calculate_metrics(self, results: list) -> dict:
        """Calculate performance metrics for a scenario."""
        if not results:
            return None

        errors = [r['error'] for r in results]
        n = len(errors)

        mean_error = sum(errors) / n
        rmse = math.sqrt(sum(e**2 for e in errors) / n)

        over_proj = sum(1 for e in errors if e > 0)  # Actual > Predicted
        under_proj = sum(1 for e in errors if e < 0)  # Actual < Predicted

        over_pct = (over_proj / n) * 100
        under_pct = (under_proj / n) * 100

        return {
            'sample_size': n,
            'mean_error': mean_error,
            'rmse': rmse,
            'over_proj_pct': over_pct,
            'under_proj_pct': under_pct
        }

    def print_report(self):
        """Print comprehensive analysis report."""
        print(f"\n{'='*70}")
        print(f"  FATIGUE ADJUSTMENT PERFORMANCE REPORT")
        print(f"{'='*70}")

        # Scenario order for display
        scenario_order = [
            'Road_B2B_Guard',
            'Road_B2B_NonGuard',
            'Home_B2B_Guard',
            'Home_B2B_NonGuard',
            'Rested_Home',
            'Density_4in5',
            'Normal_Rest'
        ]

        print(f"\n{'Scenario':<25} {'N':<6} {'Mean Err':<10} {'RMSE':<8} {'Over%':<8} {'Under%':<8}")
        print(f"{'-'*70}")

        for scenario in scenario_order:
            if scenario not in self.results or not self.results[scenario]:
                continue

            metrics = self.calculate_metrics(self.results[scenario])
            if not metrics:
                continue

            print(f"{scenario:<25} {metrics['sample_size']:<6} "
                  f"{metrics['mean_error']:>+8.2f}  {metrics['rmse']:>6.2f}  "
                  f"{metrics['over_proj_pct']:>6.1f}% {metrics['under_proj_pct']:>6.1f}%")

        # Key Findings Section
        print(f"\n{'='*70}")
        print(f"  KEY FINDINGS")
        print(f"{'='*70}")

        # Analyze B2B performance
        road_b2b_guard = self.results.get('Road_B2B_Guard', [])
        home_b2b_guard = self.results.get('Home_B2B_Guard', [])
        road_b2b_big = self.results.get('Road_B2B_NonGuard', [])
        home_b2b_big = self.results.get('Home_B2B_NonGuard', [])

        if road_b2b_guard:
            metrics = self.calculate_metrics(road_b2b_guard)
            print(f"\n1. ROAD B2B GUARDS (n={metrics['sample_size']})")
            print(f"   Modifier: -4.8% B2B Road, -2% Guard Tax = -6.7% total (V5.2)")
            print(f"   Mean Error: {metrics['mean_error']:+.2f} pts")

            if metrics['mean_error'] > 1.0:
                print(f"   ⚠️  UNDER-PROJECTION: Players are OUTPERFORMING by {metrics['mean_error']:.1f} pts")
                print(f"   → Consider reducing penalty from -6.7% to ~{-6.7 + (metrics['mean_error'] / 25 * 100):.1f}%")
            elif metrics['mean_error'] < -1.0:
                print(f"   ✅ OVER-PROJECTION: Tax may be too aggressive")
            else:
                print(f"   ✅ WELL-CALIBRATED: Error within ±1.0 pts")

        if home_b2b_guard:
            metrics = self.calculate_metrics(home_b2b_guard)
            print(f"\n2. HOME B2B GUARDS (n={metrics['sample_size']})")
            print(f"   Modifier: -1.5% B2B Home, -2% Guard Tax = -3.5% total (V5.2)")
            print(f"   Mean Error: {metrics['mean_error']:+.2f} pts")

            if metrics['mean_error'] > 1.0:
                print(f"   ⚠️  UNDER-PROJECTION: Players are OUTPERFORMING by {metrics['mean_error']:.1f} pts")
            elif metrics['mean_error'] < -1.0:
                print(f"   ✅ OVER-PROJECTION: Tax may be too aggressive")
            else:
                print(f"   ✅ WELL-CALIBRATED")

        if road_b2b_big:
            metrics = self.calculate_metrics(road_b2b_big)
            print(f"\n3. ROAD B2B NON-GUARDS (n={metrics['sample_size']})")
            print(f"   Modifier: -4.8% B2B Road (V5.2)")
            print(f"   Mean Error: {metrics['mean_error']:+.2f} pts")

        if home_b2b_big:
            metrics = self.calculate_metrics(home_b2b_big)
            print(f"\n4. HOME B2B NON-GUARDS (n={metrics['sample_size']})")
            print(f"   Modifier: -1.5% B2B Home (V5.2)")
            print(f"   Mean Error: {metrics['mean_error']:+.2f} pts")

        rested = self.results.get('Rested_Home', [])
        if rested:
            metrics = self.calculate_metrics(rested)
            print(f"\n5. RESTED HOME (3+ days) (n={metrics['sample_size']})")
            print(f"   Modifier: +3% boost")
            print(f"   Mean Error: {metrics['mean_error']:+.2f} pts")

            if metrics['mean_error'] > 0.5:
                print(f"   ⚠️  Players are EXCEEDING boost by {metrics['mean_error']:.1f} pts")
            elif metrics['mean_error'] < -0.5:
                print(f"   ⚠️  Boost may be too aggressive")
            else:
                print(f"   ✅ WELL-CALIBRATED")

        # Overall Assessment
        print(f"\n{'='*70}")
        print(f"  OVERALL ASSESSMENT")
        print(f"{'='*70}")

        all_b2b = road_b2b_guard + home_b2b_guard + road_b2b_big + home_b2b_big
        normal = self.results.get('Normal_Rest', [])

        if all_b2b and normal:
            b2b_metrics = self.calculate_metrics(all_b2b)
            normal_metrics = self.calculate_metrics(normal)

            print(f"\nB2B Players (All): {b2b_metrics['mean_error']:+.2f} pts mean error (n={b2b_metrics['sample_size']})")
            print(f"Normal Rest:       {normal_metrics['mean_error']:+.2f} pts mean error (n={normal_metrics['sample_size']})")

            diff = b2b_metrics['mean_error'] - normal_metrics['mean_error']

            if diff > 2.0:
                print(f"\n⚠️  B2B PLAYERS OUTPERFORMING by {diff:.1f} pts vs Normal Rest")
                print(f"   → Fatigue penalties are TOO AGGRESSIVE")
                print(f"   → Consider reducing all B2B modifiers by ~{diff / 25 * 100:.0f}%")
            elif diff < -2.0:
                print(f"\n✅ B2B PLAYERS UNDERPERFORMING by {abs(diff):.1f} pts vs Normal Rest")
                print(f"   → Fatigue penalties are APPROPRIATE")
            else:
                print(f"\n✅ B2B vs Normal Rest difference: {diff:.1f} pts (reasonable)")

        print(f"\n{'='*70}")

    def generate_markdown_report(self):
        """Generate markdown report and save to reports/ directory."""
        from pathlib import Path

        # Create reports directory if it doesn't exist
        reports_dir = Path('reports')
        reports_dir.mkdir(exist_ok=True)

        # Generate filename with today's date
        today = datetime.now().strftime('%Y-%m-%d')
        filename = reports_dir / f'fatigue_trends_{today}.md'

        # Scenario order for display
        scenario_order = [
            'Road_B2B_Guard',
            'Road_B2B_NonGuard',
            'Home_B2B_Guard',
            'Home_B2B_NonGuard',
            'Rested_Home',
            'Density_4in5',
            'Normal_Rest'
        ]

        # Build markdown content
        content = f"""# Fatigue Adjustment Performance Report - 21-Day Backtest

**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Test Period:** Last {self.days} days (through {datetime.now().strftime('%Y-%m-%d')})
**Modifier Version:** V5.2 (Updated Feb 15, 2026)

## Modifier Values (V5.2)

| Scenario | Modifier | Total Tax |
|----------|----------|-----------|
| Road B2B (Guard) | -4.8% B2B + -2% Guard | -6.7% |
| Road B2B (Non-Guard) | -4.8% B2B | -4.8% |
| Home B2B (Guard) | -1.5% B2B + -2% Guard | -3.5% |
| Home B2B (Non-Guard) | -1.5% B2B | -1.5% |
| Rested Home (3+ days) | +3% Boost | +3.0% |
| Density (4-in-5) | -1% Density Tax | -1.0% |

## Performance Metrics by Scenario

| Scenario | N | Mean Error | RMSE | Over% | Under% |
|----------|---|------------|------|-------|--------|
"""

        # Add metrics for each scenario
        for scenario in scenario_order:
            if scenario not in self.results or not self.results[scenario]:
                continue

            metrics = self.calculate_metrics(self.results[scenario])
            if not metrics:
                continue

            content += f"| {scenario} | {metrics['sample_size']} | {metrics['mean_error']:+.2f} | {metrics['rmse']:.2f} | {metrics['over_proj_pct']:.1f}% | {metrics['under_proj_pct']:.1f}% |\n"

        # Key Findings
        content += "\n## Key Findings\n\n"

        # Road B2B Guards
        road_b2b_guard = self.results.get('Road_B2B_Guard', [])
        if road_b2b_guard:
            metrics = self.calculate_metrics(road_b2b_guard)
            content += f"### 1. Road B2B Guards (n={metrics['sample_size']})\n\n"
            content += f"- **Modifier:** -6.7% total (-4.8% B2B Road + -2% Guard Tax)\n"
            content += f"- **Mean Error:** {metrics['mean_error']:+.2f} pts\n"

            if metrics['mean_error'] > 1.0:
                content += f"- ⚠️ **UNDER-PROJECTION:** Players outperforming by {metrics['mean_error']:.1f} pts\n"
                content += f"- **Recommendation:** Consider reducing penalty to ~{-6.7 + (metrics['mean_error'] / 25 * 100):.1f}%\n\n"
            elif metrics['mean_error'] < -1.0:
                content += f"- ✅ **OVER-PROJECTION:** Tax may be too aggressive\n\n"
            else:
                content += f"- ✅ **WELL-CALIBRATED:** Error within ±1.0 pts\n\n"

        # Home B2B Guards
        home_b2b_guard = self.results.get('Home_B2B_Guard', [])
        if home_b2b_guard:
            metrics = self.calculate_metrics(home_b2b_guard)
            content += f"### 2. Home B2B Guards (n={metrics['sample_size']})\n\n"
            content += f"- **Modifier:** -3.5% total (-1.5% B2B Home + -2% Guard Tax)\n"
            content += f"- **Mean Error:** {metrics['mean_error']:+.2f} pts\n"

            if metrics['mean_error'] > 1.0:
                content += f"- ⚠️ **UNDER-PROJECTION:** Players outperforming by {metrics['mean_error']:.1f} pts\n\n"
            elif metrics['mean_error'] < -1.0:
                content += f"- ✅ **OVER-PROJECTION:** Tax may be too aggressive\n\n"
            else:
                content += f"- ✅ **WELL-CALIBRATED**\n\n"

        # Rested Home
        rested = self.results.get('Rested_Home', [])
        if rested:
            metrics = self.calculate_metrics(rested)
            content += f"### 3. Rested Home (3+ days) (n={metrics['sample_size']})\n\n"
            content += f"- **Modifier:** +3% boost\n"
            content += f"- **Mean Error:** {metrics['mean_error']:+.2f} pts\n"

            if metrics['mean_error'] > 0.5:
                content += f"- ⚠️ Players exceeding boost by {metrics['mean_error']:.1f} pts\n\n"
            elif metrics['mean_error'] < -0.5:
                content += f"- ⚠️ Boost may be too aggressive\n\n"
            else:
                content += f"- ✅ **WELL-CALIBRATED**\n\n"

        # Overall Assessment
        all_b2b = (self.results.get('Road_B2B_Guard', []) +
                   self.results.get('Home_B2B_Guard', []) +
                   self.results.get('Road_B2B_NonGuard', []) +
                   self.results.get('Home_B2B_NonGuard', []))
        normal = self.results.get('Normal_Rest', [])

        if all_b2b and normal:
            b2b_metrics = self.calculate_metrics(all_b2b)
            normal_metrics = self.calculate_metrics(normal)

            content += f"## Overall Assessment\n\n"
            content += f"- **B2B Players (All):** {b2b_metrics['mean_error']:+.2f} pts mean error (n={b2b_metrics['sample_size']})\n"
            content += f"- **Normal Rest:** {normal_metrics['mean_error']:+.2f} pts mean error (n={normal_metrics['sample_size']})\n"

            diff = b2b_metrics['mean_error'] - normal_metrics['mean_error']

            if diff > 2.0:
                content += f"\n⚠️ **B2B players outperforming by {diff:.1f} pts vs Normal Rest**\n"
                content += f"- Fatigue penalties are **TOO AGGRESSIVE**\n"
                content += f"- Consider reducing all B2B modifiers by ~{diff / 25 * 100:.0f}%\n"
            elif diff < -2.0:
                content += f"\n✅ **B2B players underperforming by {abs(diff):.1f} pts vs Normal Rest**\n"
                content += f"- Fatigue penalties are **APPROPRIATE**\n"
            else:
                content += f"\n✅ **B2B vs Normal Rest difference: {diff:.1f} pts (reasonable)**\n"

        content += "\n---\n\n*Generated by scripts/backtest_fatigue_21day.py*\n"

        # Write to file
        with open(filename, 'w') as f:
            f.write(content)

        print(f"\n📄 Report saved to: {filename}")
        return filename

    def close(self):
        self.conn.close()

if __name__ == "__main__":
    print("\n🔬 Starting 21-Day Fatigue Backtest...")
    print(f"Window: {datetime.now() - timedelta(days=21):%Y-%m-%d} to {datetime.now():%Y-%m-%d}")

    backtest = FatigueBacktest(days=21)

    try:
        backtest.run_backtest()
        backtest.print_report()
        backtest.generate_markdown_report()
    finally:
        backtest.close()

    print(f"\n✅ Backtest Complete")
