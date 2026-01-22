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
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Any

# Import project modules
from utils.telegram_notifier import send_alert


class SystemHealthMonitor:
    def __init__(self):
        self.db_path = 'ludi.db'
        self.alerts = []
        self.metrics = {}
        
    def check_data_integrity(self) -> Dict[str, Any]:
        """Check if critical tables updated in last 24h"""
        results = {}
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Check tables with their last update timestamps
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
                    cursor.execute(f"""
                        SELECT COUNT(*) as record_count,
                               MAX(created_at) as last_created,
                               MAX(updated_at) as last_updated
                        FROM {table}
                        WHERE created_at >= ? OR updated_at >= ?
                    """, (cutoff_time.isoformat(), cutoff_time.isoformat()))
                    
                    row = cursor.fetchone()
                    if row and row[0] > 0:
                        results[display_name] = {
                            'status': '✅ OK',
                            'records_24h': row[0],
                            'last_update': row[1] or row[2]
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
            
            cursor.execute("""
                SELECT 
                    AVG(proj_value - line_over) as avg_deviation,
                    COUNT(*) as total_bets,
                    AVG(edge_pct) as avg_edge,
                    STDDEV(edge_pct) as edge_stddev
                FROM bet_recommendations
                WHERE created_at >= ?
                AND edge_pct IS NOT NULL
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
                    'avg_edge': round(avg_edge, 2),
                    'edge_stddev': round(row[3] or 0, 2)
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
    
    def check_api_health(self) -> Dict[str, Any]:
        """Check API quotas and connectivity"""
        results = {}
        
        try:
            # Check API usage log if it exists
            if os.path.exists('api_usage_log.json'):
                with open('api_usage_log.json', 'r') as f:
                    api_data = json.load(f)
                
                # Check latest entry
                if api_data.get('entries'):
                    latest = api_data['entries'][-1]
                    
                    # Calculate quota usage
                    odds_usage = latest.get('the_odds_api', {}).get('requests_today', 0)
                    tank_usage = latest.get('tank01', {}).get('requests_today', 0)
                    
                    odds_quota = 20000 if api_data.get('the_odds_api', {}).get('tier') == 'paid' else 500
                    tank_quota = 1000 if api_data.get('tank01', {}).get('tier') == 'paid' else 1000
                    
                    odds_pct = (odds_usage / odds_quota) * 100
                    tank_pct = (tank_usage / tank_quota) * 100
                    
                    if odds_pct > 80:
                        self.alerts.append(f"⚠️ The-Odds-API: {odds_pct:.1f}% quota used")
                        odds_status = '⚠️ HIGH'
                    elif odds_pct > 60:
                        odds_status = '🟡 MONITOR'
                    else:
                        odds_status = '✅ OK'
                    
                    if tank_pct > 80:
                        self.alerts.append(f"⚠️ Tank01: {tank_pct:.1f}% quota used")
                        tank_status = '⚠️ HIGH'
                    elif tank_pct > 60:
                        tank_status = '🟡 MONITOR'
                    else:
                        tank_status = '✅ OK'
                    
                    results = {
                        'the_odds_api': {
                            'status': odds_status,
                            'usage': f"{odds_usage}/{odds_quota} ({odds_pct:.1f}%)"
                        },
                        'tank01': {
                            'status': tank_status,
                            'usage': f"{tank_usage}/{tank_quota} ({tank_pct:.1f}%)"
                        }
                    }
                else:
                    results = {'status': '📊 NO DATA', 'message': 'No API usage entries found'}
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