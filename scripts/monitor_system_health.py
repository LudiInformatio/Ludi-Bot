#!/usr/bin/env python3
"""
Production System Health Monitor

Monitors system health, data integrity, and model performance.
Sends alerts to Telegram if issues detected.

Usage:
    python scripts/monitor_system_health.py [--production-mode]
"""

import sqlite3
import argparse
import json
import os
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Any

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import project modules
from utils.telegram_notifier import send_alert


class SystemHealthMonitor:
    def __init__(self):
        self.db_path = 'ludi.db'
        self.alerts = []
        self.metrics = {}

        # Mapping of tables to their actual timestamp columns
        # Many tables use 'synced_at' instead of 'created_at'/'updated_at'
        self.timestamp_columns = {
            'player_synergy_playtypes': 'synced_at',
            'player_game_tracking': 'synced_at',
            'player_shot_quality': 'synced_at',
            'team_lineups': 'created_at',
            'referee_profiles': 'last_updated',
            'games': 'date'  # Use game date as freshness indicator
        }

    def check_data_integrity(self) -> Dict[str, Any]:
        """Check if critical tables updated in last 24h"""
        results = {}

        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Check tables with their specific timestamp columns
            tables_to_check = [
                ('player_synergy_playtypes', 'Synergy Playtypes'),
                ('player_game_tracking', 'Tracking Stats'),
                ('player_shot_quality', 'Shot Quality'),
                ('team_lineups', 'WOWY Lineups'),
                ('referee_profiles', 'Referee Data'),
                ('games', 'Game Data')
            ]

            cutoff_time = datetime.now() - timedelta(hours=24)

            for table, display_name in tables_to_check:
                try:
                    # Get the correct timestamp column for this table
                    timestamp_col = self.timestamp_columns.get(table, 'created_at')

                    # Query using the correct timestamp column
                    cursor.execute(f"""
                        SELECT COUNT(*) as record_count,
                               MAX({timestamp_col}) as last_activity
                        FROM {table}
                        WHERE {timestamp_col} >= ?
                    """, (cutoff_time.isoformat(),))

                    row = cursor.fetchone()
                    if row and row[0] > 0:
                        results[display_name] = {
                            'status': '✅ OK',
                            'records_24h': row[0],
                            'last_update': row[1]
                        }
                    else:
                        # Check if table exists and has recent data at all
                        cursor.execute(f"SELECT COUNT(*) FROM {table}")
                        total_count = cursor.fetchone()[0]

                        if total_count == 0:
                            results[display_name] = {
                                'status': '🚨 EMPTY',
                                'records_24h': 0,
                                'total_records': 0
                            }
                            self.alerts.append(f"🚨 {display_name}: Table is empty")
                        else:
                            results[display_name] = {
                                'status': '⚠️ STALE',
                                'records_24h': 0,
                                'total_records': total_count
                            }
                            self.alerts.append(f"⚠️ {display_name}: No updates in 24h")

                except sqlite3.OperationalError as e:
                    results[display_name] = {
                        'status': '❌ ERROR',
                        'error': str(e)
                    }
                    self.alerts.append(f"❌ {display_name}: {str(e)}")

            conn.close()

        except Exception as e:
            self.alerts.append(f"🚨 Database connection failed: {str(e)}")
            results['database'] = {'status': '❌ FAILED', 'error': str(e)}

        return results
    
    def check_model_drift(self) -> Dict[str, Any]:
        """Check if model projections are drifting from market lines"""
        results = {}

        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Get recent bet recommendations from last 24h
            yesterday = (datetime.now() - timedelta(days=1)).isoformat()

            # Fixed column names: 'projection' and 'line' (not 'proj_value' and 'line_over')
            # Note: SQLite doesn't have STDDEV, so we calculate manually
            cursor.execute("""
                SELECT
                    AVG(projection - line) as avg_deviation,
                    COUNT(*) as total_bets,
                    AVG(true_edge) as avg_edge
                FROM bet_recommendations
                WHERE created_at >= ?
                AND true_edge IS NOT NULL
            """, (yesterday,))

            row = cursor.fetchone()
            if row and row[1] > 0:
                avg_dev = row[0] or 0.0
                total_bets = row[1]
                avg_edge = row[2] or 0.0

                # Check for concerning drift
                if abs(avg_dev) > 3.0:
                    self.alerts.append(f"⚠️ MODEL DRIFT: Avg deviation {avg_dev:.1f} pts exceeds ±3.0 threshold")
                    status = '⚠️ DRIFT'
                elif abs(avg_dev) > 2.0:
                    status = '🟡 MONITOR'
                else:
                    status = '✅ STABLE'

                results = {
                    'status': status,
                    'avg_deviation': round(avg_dev, 2),
                    'total_bets': total_bets,
                    'avg_edge': round(avg_edge, 2)
                }
            else:
                results = {
                    'status': '📊 NO DATA',
                    'message': 'No bet recommendations in last 24h'
                }

            conn.close()

        except Exception as e:
            self.alerts.append(f"🚨 Model drift check failed: {str(e)}")
            results = {'status': '❌ ERROR', 'error': str(e)}

        return results
    
    def check_module_output(self) -> Dict[str, Any]:
        """Check if modules are producing expected output volumes"""
        results = {}
        
        try:
            # Check today's log file for module activity
            log_file = f"logs/production/pipeline_{datetime.now().strftime('%Y%m%d')}.log"
            if os.path.exists(log_file):
                with open(log_file, 'r') as f:
                    log_content = f.read()
                
                # Count key outputs from each module
                module_checks = {
                    'Module A (Gatekeeper)': ['🎯 GAME SLATE', '📊 LINE SHOPPING'],
                    'Module B (Engine)': ['📈 HISTORICAL ANALYSIS'],
                    'Module C (Oracle)': ['🎲 MONTE CARLO'],
                    'Module D (Yak)': ['🏥 INJURY INTEL'],
                    'Module E (Calibrator)': ['⚙️ CALIBRATION'],
                    'Module F (Alchemist)': ['💎 DIAMOND', '🔷 BLUE CHIP', '💙 CORE', '🎯 STEAL'],
                    'Module G (Zebras)': ['🦓 ZEBRA INTEL'],
                    'Module H (Historian)': ['📚 HISTORIAN'],
                    'Module X (Scenario)': ['🔀 SCENARIO']
                }
                
                for module, markers in module_checks:
                    count = sum(log_content.count(marker) for marker in markers)
                    if count > 0:
                        results[module] = {'status': '✅ ACTIVE', 'outputs': count}
                    else:
                        results[module] = {'status': '⚠️ QUIET', 'outputs': 0}
                        self.alerts.append(f"⚠️ {module}: No output detected")
            else:
                results['log_file'] = {
                    'status': '📄 MISSING',
                    'file': log_file
                }
                self.alerts.append(f"📄 Today's log file not found: {log_file}")
        
        except Exception as e:
            self.alerts.append(f"🚨 Module output check failed: {str(e)}")
            results = {'status': '❌ ERROR', 'error': str(e)}
        
        return results
    
    def check_pf_coverage(self) -> Dict[str, Any]:
        """Check personal fouls data coverage in player_game_logs"""
        results = {}

        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Check PF coverage for recent games (last 7 days)
            cursor.execute("""
                SELECT
                    COUNT(*) as total_logs,
                    SUM(CASE WHEN pf > 0 THEN 1 ELSE 0 END) as with_pf,
                    MIN(game_date) as earliest,
                    MAX(game_date) as latest
                FROM player_game_logs
                WHERE game_date >= date('now', '-7 days')
            """)

            recent = cursor.fetchone()

            # Check full season coverage
            cursor.execute("""
                SELECT
                    COUNT(*) as total_logs,
                    SUM(CASE WHEN pf > 0 THEN 1 ELSE 0 END) as with_pf
                FROM player_game_logs
            """)

            full_season = cursor.fetchone()
            conn.close()

            if recent and recent[0] > 0:
                recent_pct = (recent[1] / recent[0]) * 100 if recent[0] > 0 else 0
                full_pct = (full_season[1] / full_season[0]) * 100 if full_season[0] > 0 else 0

                # Alert if coverage drops below 70%
                if recent_pct < 70:
                    self.alerts.append(f"⚠️ PF Coverage (7-day): {recent_pct:.1f}% - Below 70% threshold")
                    status = '⚠️ LOW'
                elif recent_pct < 80:
                    status = '🟡 MONITOR'
                else:
                    status = '✅ OK'

                results = {
                    'status': status,
                    'recent_7d': {
                        'coverage': f"{recent_pct:.1f}%",
                        'with_pf': recent[1],
                        'total': recent[0],
                        'date_range': f"{recent[2]} to {recent[3]}"
                    },
                    'full_season': {
                        'coverage': f"{full_pct:.1f}%",
                        'with_pf': full_season[1],
                        'total': full_season[0]
                    }
                }
            else:
                results = {
                    'status': '📊 NO DATA',
                    'message': 'No recent game logs found'
                }

        except Exception as e:
            self.alerts.append(f"🚨 PF coverage check failed: {str(e)}")
            results = {'status': '❌ ERROR', 'error': str(e)}

        return results

    def check_wowy_coverage(self) -> Dict[str, Any]:
        """Check WOWY data coverage across teams and players"""
        results = {}

        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Check player_season_wowy coverage
            cursor.execute("""
                SELECT
                    COUNT(*) as total_players,
                    COUNT(DISTINCT team_abbr) as teams,
                    SUM(CASE WHEN on_off_diff IS NOT NULL THEN 1 ELSE 0 END) as with_data,
                    MAX(synced_at) as last_sync
                FROM player_season_wowy
            """)

            wowy_data = cursor.fetchone()

            # Check lineup_season_totals (fallback data)
            cursor.execute("""
                SELECT
                    COUNT(*) as total_lineups,
                    COUNT(DISTINCT team_abbreviation) as teams,
                    MAX(total_possessions) as max_poss
                FROM lineup_season_totals
            """)

            lineup_data = cursor.fetchone()
            conn.close()

            if wowy_data and wowy_data[0] > 0:
                coverage_pct = (wowy_data[2] / wowy_data[0]) * 100 if wowy_data[0] > 0 else 0

                if wowy_data[1] < 30:
                    self.alerts.append(f"⚠️ WOWY: Only {wowy_data[1]}/30 teams covered")
                    status = '⚠️ INCOMPLETE'
                elif coverage_pct < 90:
                    status = '🟡 PARTIAL'
                else:
                    status = '✅ OK'

                results = {
                    'status': status,
                    'player_wowy': {
                        'players': wowy_data[0],
                        'teams': f"{wowy_data[1]}/30",
                        'with_data': wowy_data[2],
                        'coverage': f"{coverage_pct:.1f}%",
                        'last_sync': wowy_data[3]
                    },
                    'lineup_fallback': {
                        'lineups': lineup_data[0] if lineup_data else 0,
                        'teams': f"{lineup_data[1]}/30" if lineup_data else "0/30",
                        'max_possessions': lineup_data[2] if lineup_data else 0
                    }
                }
            else:
                results = {
                    'status': '📊 NO DATA',
                    'message': 'No WOWY data found',
                    'lineup_fallback': {
                        'lineups': lineup_data[0] if lineup_data else 0,
                        'teams': f"{lineup_data[1]}/30" if lineup_data else "0/30"
                    }
                }

        except Exception as e:
            self.alerts.append(f"🚨 WOWY coverage check failed: {str(e)}")
            results = {'status': '❌ ERROR', 'error': str(e)}

        return results

    def check_api_health(self) -> Dict[str, Any]:
        """Check API quotas and connectivity"""
        results = {}

        try:
            # Check API usage log if it exists
            if os.path.exists('api_usage_log.json'):
                with open('api_usage_log.json', 'r') as f:
                    api_data = json.load(f)

                # Handle actual log format: list of individual API calls
                # Note: The log file is a flat list, not the expected aggregated format
                if isinstance(api_data, list) and len(api_data) > 0:
                    # Find most recent entries for each API
                    odds_entries = [e for e in api_data if e.get('api') == 'odds_api']
                    tank_entries = [e for e in api_data if e.get('api') == 'tank01']

                    if odds_entries:
                        latest_odds = odds_entries[-1]
                        rate_info = latest_odds.get('rate_limit_info', {})
                        odds_used = int(rate_info.get('requests_used', 0))
                        odds_remaining = int(rate_info.get('requests_remaining', 0))
                        odds_quota = odds_used + odds_remaining

                        odds_pct = (odds_used / odds_quota * 100) if odds_quota > 0 else 0

                        if odds_pct > 80:
                            self.alerts.append(f"⚠️ The-Odds-API: {odds_pct:.1f}% quota used")
                            odds_status = '⚠️ HIGH'
                        elif odds_pct > 60:
                            odds_status = '🟡 MONITOR'
                        else:
                            odds_status = '✅ OK'

                        results['the_odds_api'] = {
                            'status': odds_status,
                            'usage': f"{odds_used}/{odds_quota} ({odds_pct:.1f}%)",
                            'last_check': latest_odds.get('timestamp', 'Unknown')
                        }

                    if tank_entries:
                        latest_tank = tank_entries[-1]
                        rate_info = latest_tank.get('rate_limit_info', {})
                        tank_remaining = int(rate_info.get('requests_remaining', 0))
                        tank_limit = int(rate_info.get('requests_limit', 1000))
                        tank_used = tank_limit - tank_remaining

                        tank_pct = (tank_used / tank_limit * 100) if tank_limit > 0 else 0

                        if tank_pct > 80:
                            self.alerts.append(f"⚠️ Tank01: {tank_pct:.1f}% quota used")
                            tank_status = '⚠️ HIGH'
                        elif tank_pct > 60:
                            tank_status = '🟡 MONITOR'
                        else:
                            tank_status = '✅ OK'

                        results['tank01'] = {
                            'status': tank_status,
                            'usage': f"{tank_used}/{tank_limit} ({tank_pct:.1f}%)",
                            'last_check': latest_tank.get('timestamp', 'Unknown')
                        }

                    if not odds_entries and not tank_entries:
                        results = {'status': '📊 NO DATA', 'message': 'No API entries found in log'}
                else:
                    results = {'status': '📊 NO DATA', 'message': 'API log is empty or malformed'}
            else:
                results = {'status': '📄 NO LOG', 'message': 'API usage log not found'}

        except Exception as e:
            self.alerts.append(f"🚨 API health check failed: {str(e)}")
            results = {'status': '❌ ERROR', 'error': str(e)}

        return results
    
    def generate_health_report(self) -> Dict[str, Any]:
        """Generate comprehensive health report"""
        print("🏥 RUNNING SYSTEM HEALTH MONITOR")
        print("=" * 50)
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'checks': {}
        }
        
        # Run all checks
        print("🔍 Checking data integrity...")
        report['checks']['data_integrity'] = self.check_data_integrity()
        
        print("📈 Checking model drift...")
        report['checks']['model_drift'] = self.check_model_drift()
        
        print("🧩 Checking module outputs...")
        report['checks']['module_output'] = self.check_module_output()
        
        print("🌐 Checking API health...")
        report['checks']['api_health'] = self.check_api_health()

        print("🏀 Checking PF data coverage...")
        report['checks']['pf_coverage'] = self.check_pf_coverage()

        print("📊 Checking WOWY data coverage...")
        report['checks']['wowy_coverage'] = self.check_wowy_coverage()

        # Summary
        report['summary'] = {
            'total_alerts': len(self.alerts),
            'critical_alerts': len([a for a in self.alerts if a.startswith('🚨')]),
            'warning_alerts': len([a for a in self.alerts if a.startswith('⚠️')]),
            'alerts': self.alerts
        }
        
        return report
    
    def send_alerts_if_needed(self, production_mode: bool = False):
        """Send alerts to Telegram if any detected"""
        if self.alerts:
            if production_mode:
                # In production mode, send all alerts
                alert_message = f"🚨 **SYSTEM HEALTH ALERT**\n\n" + "\n".join(self.alerts)
                send_alert("Production System Alert", alert_message)
            else:
                # In test mode, just print them
                print("\n🚨 ALERTS DETECTED:")
                for alert in self.alerts:
                    print(f"  {alert}")
        else:
            print("✅ No system issues detected")


def main():
    parser = argparse.ArgumentParser(description='System Health Monitor')
    parser.add_argument('--production-mode', action='store_true', 
                       help='Run in production mode (sends Telegram alerts)')
    
    args = parser.parse_args()
    
    monitor = SystemHealthMonitor()
    report = monitor.generate_health_report()
    
    # Save report
    os.makedirs('logs/health', exist_ok=True)
    report_file = f"logs/health/health_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"\n📋 Health report saved to: {report_file}")
    
    # Print summary
    summary = report['summary']
    print(f"\n📊 SUMMARY:")
    print(f"   Total Alerts: {summary['total_alerts']}")
    print(f"   Critical: {summary['critical_alerts']}")
    print(f"   Warnings: {summary['warning_alerts']}")
    
    # Send alerts if needed
    monitor.send_alerts_if_needed(args.production_mode)
    
    return 0 if summary['critical_alerts'] == 0 else 1


if __name__ == "__main__":
    exit(main())