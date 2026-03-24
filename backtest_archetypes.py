#!/usr/bin/env python
"""
backtest_archetypes.py - Ludi Informatio Backtesting Suite
Includes:
1. Hypothesis Testing (Phase B)
2. Historical Replay Loop (RMSE Validation) for 15, 60, and Full Season ranges.
"""

import sqlite3
import argparse
import math
from datetime import datetime, timedelta, date
from collections import defaultdict
from module_e import LudiCalibrator

# ==========================================
# PHASE 1: HYPOTHESIS TESTING
# ==========================================

def query_historical_matchups(archetype_condition, def_style, min_games=5, days=60):
    conn = sqlite3.connect('ludi.db')
    c = conn.cursor()
    
    query = f"""
    SELECT 
        p.player_name,
        AVG(p.fta) as avg_fta,
        AVG(p.fg3m) as avg_3pm,
        AVG(p.minutes) as avg_min,
        AVG(p.pts) as avg_pts,
        COUNT(*) as game_count
    FROM player_game_logs p
    JOIN games g ON p.game_id = g.game_id
    WHERE (g.home_team = ? OR g.away_team = ?)
    AND p.team_abbreviation != ?
    AND {archetype_condition}
    AND p.game_date >= date('now', '-{days} days')
    GROUP BY p.player_name
    HAVING COUNT(*) >= ?
    ORDER BY game_count DESC
    LIMIT 10
    """
    
    c.execute(query, (def_style, def_style, def_style, min_games))
    results = c.fetchall()
    conn.close()
    return results

def test_slasher_vs_hackers(days=60):
    print("\n" + "="*60)
    print(f"📋 HYPOTHESIS TEST 1: Slasher vs Hackers (Last {days} Days)")
    print("="*60)
    slasher_condition = "pts > 20 AND fg3m < 2.0 AND minutes > 30"
    # Pull HACKERS teams from LudiCalibrator.DEFENSIVE_STYLES
    calib = LudiCalibrator()
    hackers = [team for team, style in calib.DEFENSIVE_STYLES.items() if style == 'HACKERS']
    for team in hackers:
        print(f"\n📊 {team} Defense:")
        results = query_historical_matchups(slasher_condition, team, min_games=2, days=days)
        if not results:
            print("   ⚠️  No data found")
            continue
        for row in results[:3]:
            player, fta, tpm, mins, pts, games = row
            print(f"   {player:<20} | FTA: {fta:.1f} | Games: {games}")

def test_stretch_big_vs_paint_pack(days=60):
    print("\n" + "="*60)
    print(f"📋 HYPOTHESIS TEST 2: Stretch Big vs Paint Pack (Last {days} Days)")
    print("="*60)
    stretch_condition = "reb > 6.0 AND fg3m > 1.5 AND minutes > 25"
    # Pull PAINT_PACK teams from LudiCalibrator.DEFENSIVE_STYLES
    calib = LudiCalibrator()
    paint_pack = [team for team, style in calib.DEFENSIVE_STYLES.items() if style == 'PAINT_PACK']
    for team in paint_pack[:3]:
        print(f"\n📊 {team} Defense:")
        results = query_historical_matchups(stretch_condition, team, min_games=2, days=days)
        if not results:
            print("   ⚠️  No data found")
            continue
        for row in results[:3]:
            # FIXED: Added fta to unpacking (6 columns returned)
            player, fta, tpm, mins, pts, games = row
            print(f"   {player:<20} | 3PM: {tpm:.1f} | Games: {games}")

def test_blowout_tax(days=60):
    print("\n" + "="*60)
    print(f"📋 HYPOTHESIS TEST 3: Blowout Tax (Last {days} Days)")
    print("="*60)
    conn = sqlite3.connect('ludi.db')
    c = conn.cursor()
    query = """
    WITH game_margins AS (
        SELECT 
            g.game_id,
            ABS(g.home_score - g.away_score) as margin,
            CASE 
                WHEN ABS(g.home_score - g.away_score) > 15 THEN 'Blowout'
                ELSE 'Close'
            END AS game_type
        FROM games g
        WHERE g.date >= date('now', '-' || ? || ' days')
        AND g.home_score IS NOT NULL
    )
    SELECT 
        gm.game_type,
        AVG(p.minutes) as avg_min,
        COUNT(*) as player_games
    FROM player_game_logs p
    JOIN game_margins gm ON p.game_id = gm.game_id
    WHERE p.minutes > 30
    GROUP BY gm.game_type
    """
    c.execute(query, (days,))
    results = c.fetchall()
    conn.close()
    print("\n📊 Starter Minutes (MIN > 30 baseline):")
    for row in results:
        game_type, avg_min, count = row
        print(f"   {game_type:<10} | Avg: {avg_min:.1f} min | Sample: {count} games")

# ==========================================
# PHASE 2: HISTORICAL REPLAY LOOP
# ==========================================

class BacktestEngine:
    def __init__(self, days=60):
        self.days = days
        self.calib = LudiCalibrator()
        self.conn = sqlite3.connect('ludi.db')
        self.running_stats = defaultdict(lambda: defaultdict(list))
        
        # Stats to track for running averages
        self.tracking_stats = ['pts', 'reb', 'ast', 'fg3m', 'minutes', 'fga', 'fta', 'tov', 'stl', 'blk', 'oreb']

    def fetch_logs(self):
        """Fetch all logs in chronological order, joined with game info.
           COALESCE used to handle NULL stats.
        """
        query = """
        SELECT 
            p.player_id, p.player_name, p.team_abbreviation, 
            p.game_date, p.game_id, p.matchup,
            COALESCE(p.pts, 0), COALESCE(p.reb, 0), COALESCE(p.ast, 0), 
            COALESCE(p.fg3m, 0), COALESCE(p.minutes, 0), 
            COALESCE(p.fga, 0), COALESCE(p.fta, 0), COALESCE(p.tov, 0), 
            COALESCE(p.stl, 0), COALESCE(p.blk, 0), COALESCE(p.oreb, 0),
            g.home_team, g.away_team, g.home_score, g.away_score
        FROM player_game_logs p
        LEFT JOIN games g ON p.game_id = g.game_id
        ORDER BY p.game_date ASC
        """
        c = self.conn.cursor()
        c.execute(query)
        return c.fetchall()

    def get_running_avg(self, player_id, stat):
        history = self.running_stats[player_id][stat]
        if not history:
            return 0.0
        # Ensure we don't crash on any None values if they snuck in
        clean_history = [x for x in history if x is not None]
        if not clean_history:
            return 0.0
        return sum(clean_history) / len(clean_history)

    def calculate_rmse(self, predictions, actuals):
        if not predictions:
            return 0.0
        mse = sum((p - a) ** 2 for p, a in zip(predictions, actuals)) / len(predictions)
        return math.sqrt(mse)

    def _generate_markdown_report(self, label, processed, skipped, rmse_results, start_date, end_date):
        """Generate markdown report and save to reports/ directory."""
        from pathlib import Path

        # Create reports directory if it doesn't exist
        reports_dir = Path('reports')
        reports_dir.mkdir(exist_ok=True)

        # Generate filename with today's date
        today = datetime.now().strftime('%Y-%m-%d')
        filename = reports_dir / f'backtest_archetypes_{today}.md'

        # Build markdown content
        content = f"""# Archetype Backtest Report - {label}

**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Test Period:** {start_date} to {end_date}
**Games Processed:** {processed}
**Games Skipped:** {skipped} (insufficient history)

## RMSE Results (Root Mean Squared Error)

| Stat | RMSE | Status |
|------|------|--------|
| PTS  | {rmse_results['pts']:.2f} | {'✅ PASS' if rmse_results['pts'] < 7.0 else '⚠️ NEEDS TUNING'} |
| REB  | {rmse_results['reb']:.2f} | {'✅ PASS' if rmse_results['reb'] < 3.5 else '⚠️ NEEDS TUNING'} |
| AST  | {rmse_results['ast']:.2f} | {'✅ PASS' if rmse_results['ast'] < 2.5 else '⚠️ NEEDS TUNING'} |
| 3PM  | {rmse_results['fg3m']:.2f} | {'✅ PASS' if rmse_results['fg3m'] < 1.5 else '⚠️ NEEDS TUNING'} |
| BLK  | {rmse_results['blk']:.2f} | {'✅ PASS' if rmse_results['blk'] < 0.8 else '⚠️ NEEDS TUNING'} |
| STL  | {rmse_results['stl']:.2f} | {'✅ PASS' if rmse_results['stl'] < 0.8 else '⚠️ NEEDS TUNING'} |
| TOV  | {rmse_results['tov']:.2f} | {'✅ PASS' if rmse_results['tov'] < 1.2 else '⚠️ NEEDS TUNING'} |

## Interpretation

- **RMSE** measures average prediction error in the same units as the stat
- Lower RMSE = better model accuracy
- Industry standard: PTS < 7.0, REB < 3.5, AST < 2.5

## Notes

- This backtest uses historical game logs with running averages (5+ game minimum)
- Module E calibration applied (matchup modifiers, fatigue, blowout tax)
- Game context (spread, total) pulled from database where available
"""

        # Write to file
        with open(filename, 'w') as f:
            f.write(content)

        print(f"\n📄 Markdown report generated: {filename}")

    def run(self, label="Backtest"):
        print("\n" + "="*60)
        print(f"🔄 STARTING REPLAY LOOP: {label} (Last {self.days} Days)")
        print("="*60)

        logs = self.fetch_logs()
        # Calculate start date based on self.days
        start_date_obj = datetime.now() - timedelta(days=self.days)
        start_date = start_date_obj.strftime('%Y-%m-%d')
        
        print(f"   Date Range: {start_date} to {datetime.now().strftime('%Y-%m-%d')}")
        
        results = {
            'pts': {'pred': [], 'act': []},
            'reb': {'pred': [], 'act': []},
            'ast': {'pred': [], 'act': []},
            'fg3m': {'pred': [], 'act': []},
            'blk': {'pred': [], 'act': []},
            'stl': {'pred': [], 'act': []},
            'tov': {'pred': [], 'act': []}
        }
        
        processed_count = 0
        skipped_count = 0

        # Reset running stats for each run to ensure clean state if re-instantiated
        self.running_stats = defaultdict(lambda: defaultdict(list))

        for row in logs:
            (pid, name, team, date_str, gid, matchup, 
             pts, reb, ast, fg3m, mins, 
             fga, fta, tov, stl, blk, oreb,
             home, away, h_score, a_score) = row

            # 1. Prediction Step (Before updating stats with current game)
            
            # Check if this game is within the test window
            if date_str >= start_date:
                # Need at least 5 games of history to predict
                if len(self.running_stats[pid]['pts']) >= 5:
                    
                    # Construct Player Packet (Pre-Game State)
                    base_pts = self.get_running_avg(pid, 'pts')
                    base_reb = self.get_running_avg(pid, 'reb')
                    base_ast = self.get_running_avg(pid, 'ast')
                    base_min = self.get_running_avg(pid, 'minutes')
                    base_3pm = self.get_running_avg(pid, 'fg3m')
                    base_stl = self.get_running_avg(pid, 'stl')
                    base_blk = self.get_running_avg(pid, 'blk')
                    
                    # Estimate Usage
                    avg_fga = self.get_running_avg(pid, 'fga')
                    avg_fta = self.get_running_avg(pid, 'fta')
                    avg_tov = self.get_running_avg(pid, 'tov')
                    base_usg = 0.20
                    if base_min > 0:
                        base_usg = ((avg_fga + 0.44*avg_fta + avg_tov) / base_min) / 2.1
                    
                    opponent = 'UNK'
                    if home and away:
                        opponent = away if team == home else home

                    # Pull game context from database (spread, total) if available
                    spread = 5.0
                    total = 228.0
                    if h_score is not None and a_score is not None:
                        # Calculate actual spread from final scores
                        if team == home:
                            spread = h_score - a_score
                        else:
                            spread = a_score - h_score
                        total = h_score + a_score

                    odds = {'total': total, 'spread': abs(spread)}

                    player_packet = {
                        'name': name,
                        'team': team,
                        'opponent': opponent,
                        'base_pts': base_pts,
                        'base_reb': base_reb,
                        'base_ast': base_ast,
                        'base_min': base_min,
                        'base_3pm': base_3pm,
                        'base_stl': base_stl,
                        'base_blk': base_blk,
                        'base_usg': base_usg,
                        'base_fga': avg_fga,
                        'base_fta': avg_fta,
                        'base_tov': avg_tov,
                        'base_oreb': self.get_running_avg(pid, 'oreb'),
                        'proj_pts': base_pts,
                        'proj_reb': base_reb,
                        'proj_ast': base_ast,
                        'proj_3pm': base_3pm,
                        'proj_min': base_min,
                        'proj_fga': avg_fga,
                        'proj_fta': avg_fta,
                        'proj_tov': avg_tov,
                        'proj_stl': base_stl,
                        'proj_blk': base_blk,
                        'proj_oreb': self.get_running_avg(pid, 'oreb'),
                        'odds': odds
                    }
                    
                    # Run Calibration
                    yak_report = {'status': 'Active', 'note': ''} 
                    calibrated = self.calib.calibrate_player(player_packet, yak_report)
                    
                    # Store Results for all 7 stats
                    results['pts']['pred'].append(calibrated['proj_pts'])
                    results['pts']['act'].append(pts)

                    results['reb']['pred'].append(calibrated['proj_reb'])
                    results['reb']['act'].append(reb)

                    results['ast']['pred'].append(calibrated['proj_ast'])
                    results['ast']['act'].append(ast)

                    results['fg3m']['pred'].append(calibrated.get('proj_3pm', base_3pm))
                    results['fg3m']['act'].append(fg3m)

                    results['blk']['pred'].append(calibrated.get('proj_blk', base_blk))
                    results['blk']['act'].append(blk)

                    results['stl']['pred'].append(calibrated.get('proj_stl', base_stl))
                    results['stl']['act'].append(stl)

                    results['tov']['pred'].append(calibrated.get('proj_tov', avg_tov))
                    results['tov']['act'].append(tov)

                    processed_count += 1
                else:
                    skipped_count += 1

            # 2. Update Running Stats (Post-Game)
            # Cap running window to prevent unbounded growth (look-ahead for early-season games)
            _WINDOW = 30
            for _stat, _val in [
                ('pts', pts), ('reb', reb), ('ast', ast), ('fg3m', fg3m),
                ('minutes', mins), ('fga', fga), ('fta', fta), ('tov', tov),
                ('stl', stl), ('blk', blk), ('oreb', oreb)
            ]:
                self.running_stats[pid][_stat].append(_val)
                if len(self.running_stats[pid][_stat]) > _WINDOW:
                    self.running_stats[pid][_stat].pop(0)

        print(f"\n✅ Processing Complete: {label}")
        print(f"   Games Predicted: {processed_count}")
        print(f"   Skipped (Low History): {skipped_count}")

        # Calculate RMSE for all 7 stats
        print(f"\n📊 {label} VALIDATION RESULTS (RMSE):")

        rmse_results = {}
        for stat in ['pts', 'reb', 'ast', 'fg3m', 'blk', 'stl', 'tov']:
            rmse = self.calculate_rmse(results[stat]['pred'], results[stat]['act'])
            rmse_results[stat] = rmse
            print(f"   {stat.upper()} RMSE: {rmse:.2f}")

        if rmse_results['pts'] < 7.0:
            print("   ✅ PTS Model is solid (< 7.0)")
        else:
            print("   ⚠️ PTS Model needs tuning (> 7.0)")

        # Generate markdown report
        self._generate_markdown_report(label, processed_count, skipped_count, rmse_results, start_date, datetime.now().strftime('%Y-%m-%d'))

        return rmse_results

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode', type=str, choices=['15', '60', 'season', 'all'], default='60', 
                        help='Test duration: 15, 60, season (since Oct 21), or all')
    args = parser.parse_args()
    
    # Calculate Season Duration
    season_start = datetime(2025, 10, 21)
    today = datetime.now()
    season_days = (today - season_start).days

    modes_to_run = []
    if args.mode == 'all':
        modes_to_run = [('15-Day', 15), ('60-Day', 60), ('Full Season', season_days)]
    elif args.mode == 'season':
        modes_to_run = [('Full Season', season_days)]
    elif args.mode == '15':
        modes_to_run = [('15-Day', 15)]
    else:
        modes_to_run = [('60-Day', 60)]

    print(f"Starting Backtest Suite (Mode: {args.mode})")
    
    # Run Hypothesis Tests just once (using the largest window)
    max_days = max(m[1] for m in modes_to_run)
    try:
        test_slasher_vs_hackers(max_days)
        test_stretch_big_vs_paint_pack(max_days)
        test_blowout_tax(max_days)
    except Exception as e:
        print(f"Hypothesis tests failed: {e}")

    # Run Replay Loops
    for label, days in modes_to_run:
        engine = BacktestEngine(days=days)
        engine.run(label)