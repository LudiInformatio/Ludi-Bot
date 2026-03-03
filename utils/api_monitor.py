"""
LUDI INFORMATIO | API MONITORING UTILITY
========================================
Tracks API usage, logs requests, and sends alerts when approaching quota limits.

Features:
- Logs all API requests to api_usage_log.json
- Parses rate limit headers from The-Odds-API and Tank01
- Console warnings when >80% quota consumed
- Telegram notifications for quota alerts and errors
- Cost tracking and projections

Usage:
    monitor = APIMonitor()
    monitor.log_request('odds_api', 'fetch_slate', response.headers)
    monitor.check_quota_threshold('odds_api')
"""

import json
import os
from datetime import datetime
from typing import Dict, Optional
import requests

class APIMonitor:
    def __init__(self, log_file='api_usage_log.json'):
        """Initialize API monitoring with persistent log file."""
        self.log_file = log_file
        self.session_logs = []

        # Load existing logs or create new file
        if os.path.exists(log_file):
            try:
                with open(log_file, 'r') as f:
                    self.logs = json.load(f)
            except Exception as e:
                print(f"[TAG] Context: {e}")
                self.logs = []
        else:
            self.logs = []

        # Telegram config (loaded from environment)
        self.telegram_enabled = self._check_telegram_config()

    def _check_telegram_config(self) -> bool:
        """Check if Telegram credentials are configured."""
        try:
            import config
            if hasattr(config, 'TELEGRAM_TOKEN') and hasattr(config, 'TELEGRAM_CHAT_ID'):
                self.telegram_token = config.TELEGRAM_TOKEN
                self.telegram_chat_id = config.TELEGRAM_CHAT_ID
                if self.telegram_token and self.telegram_chat_id:
                    return True
        except Exception as e:
            print(f"[TAG] Context: {e}")
            pass
        return False

    def log_request(self, api_name: str, endpoint: str, response_headers: Dict):
        """
        Log an API request with rate limit information.

        Args:
            api_name: 'odds_api' or 'tank01'
            endpoint: e.g., 'fetch_slate', 'fetch_props', 'injury_list'
            response_headers: HTTP response headers dict
        """
        timestamp = datetime.now().isoformat()

        # Parse rate limit headers based on API
        if api_name == 'odds_api':
            rate_info = self._parse_odds_api_headers(response_headers)
        elif api_name == 'tank01':
            rate_info = self._parse_tank01_headers(response_headers)
        else:
            rate_info = {'error': 'Unknown API'}

        log_entry = {
            'timestamp': timestamp,
            'api': api_name,
            'endpoint': endpoint,
            'rate_limit_info': rate_info
        }

        # Add to logs
        self.logs.append(log_entry)
        self.session_logs.append(log_entry)

        # Persist to file
        self._save_logs()

        # Console output
        if 'requests_remaining' in rate_info:
            print(f"      📊 {api_name.upper()}: {rate_info['requests_remaining']} credits remaining")

    def _parse_odds_api_headers(self, headers: Dict) -> Dict:
        """Parse The-Odds-API rate limit headers."""
        return {
            'requests_remaining': headers.get('x-requests-remaining', 'N/A'),
            'requests_used': headers.get('x-requests-used', 'N/A'),
            'request_cost': headers.get('x-requests-last', 'N/A')
        }

    def _parse_tank01_headers(self, headers: Dict) -> Dict:
        """
        Parse Tank01/RapidAPI rate limit headers.
        Note: RapidAPI headers may vary, common ones are:
        - x-ratelimit-requests-remaining
        - x-ratelimit-requests-limit
        """
        return {
            'requests_remaining': headers.get('x-ratelimit-requests-remaining',
                                             headers.get('x-ratelimit-remaining', 'N/A')),
            'requests_limit': headers.get('x-ratelimit-requests-limit',
                                         headers.get('x-ratelimit-limit', 'N/A'))
        }

    def check_quota_threshold(self, api_name: str, threshold: float = 0.8):
        """
        Check if API quota is approaching limit and alert if needed.

        Args:
            api_name: 'odds_api' or 'tank01'
            threshold: Alert threshold (default 0.8 = 80%)
        """
        # Get most recent log for this API
        recent_logs = [log for log in self.logs if log['api'] == api_name]
        if not recent_logs:
            return

        latest_log = recent_logs[-1]
        rate_info = latest_log['rate_limit_info']

        # Calculate usage percentage
        if api_name == 'odds_api':
            remaining = rate_info.get('requests_remaining', 'N/A')
            if remaining != 'N/A' and remaining != 'Unknown':
                try:
                    remaining_int = int(remaining)
                    # Assume 20K limit for paid tier (from config)
                    total_limit = 20000
                    used_pct = 1.0 - (remaining_int / total_limit)

                    if used_pct >= threshold:
                        msg = f"⚠️ WARNING: {api_name.upper()} quota at {used_pct*100:.1f}% ({remaining_int} remaining)"
                        print(f"\n{msg}\n")
                        self._send_telegram_alert(msg)
                except ValueError:
                    pass

        elif api_name == 'tank01':
            remaining = rate_info.get('requests_remaining', 'N/A')
            limit = rate_info.get('requests_limit', 'N/A')

            if remaining != 'N/A' and limit != 'N/A':
                try:
                    remaining_int = int(remaining)
                    limit_int = int(limit)
                    used_pct = 1.0 - (remaining_int / limit_int)

                    if used_pct >= threshold:
                        msg = f"⚠️ WARNING: {api_name.upper()} quota at {used_pct*100:.1f}% ({remaining_int}/{limit_int} remaining)"
                        print(f"\n{msg}\n")
                        self._send_telegram_alert(msg)
                except ValueError:
                    pass

    def log_failed_request(self, api_name: str, endpoint: str, error_msg: str):
        """
        Log a failed API request.

        Args:
            api_name: 'odds_api' or 'tank01'
            endpoint: e.g., 'box_score', 'injury_list'
            error_msg: Error message
        """
        timestamp = datetime.now().isoformat()

        log_entry = {
            'timestamp': timestamp,
            'api': api_name,
            'endpoint': endpoint,
            'status': 'FAILED',
            'error': error_msg
        }

        self.logs.append(log_entry)
        self._save_logs()

        # Send Telegram alert for failures
        alert_msg = f"❌ API Error\nAPI: {api_name}\nEndpoint: {endpoint}\nError: {error_msg[:200]}"
        self._send_telegram_alert(alert_msg)

    def _send_telegram_alert(self, message: str):
        """Send alert via Solomon (PM bot) Telegram channel."""
        try:
            from utils.telegram_notifier import send_solomon_message
            send_solomon_message(f"🤖 *Ludi API Monitor*\n\n{message}")
        except Exception as e:
            print(f"      ⚠️ Solomon alert failed: {e}")

    def log_claude_usage(self, model: str, input_tokens: int, output_tokens: int, task: str = ""):
        """Log Claude API token usage to api_usage_log.json."""
        timestamp = datetime.now().isoformat()

        haiku_cost_input = 0.00025
        haiku_cost_output = 0.00125
        sonnet_cost_input = 0.003
        sonnet_cost_output = 0.015

        if "haiku" in model.lower():
            estimated_cost = (input_tokens / 1000) * haiku_cost_input + (output_tokens / 1000) * haiku_cost_output
            model_short = "haiku"
        else:
            estimated_cost = (input_tokens / 1000) * sonnet_cost_input + (output_tokens / 1000) * sonnet_cost_output
            model_short = "sonnet"

        log_entry = {
            'timestamp': timestamp,
            'api': 'claude',
            'task': task,
            'model': model,
            'input_tokens': input_tokens,
            'output_tokens': output_tokens,
            'total_tokens': input_tokens + output_tokens,
            'estimated_cost_usd': round(estimated_cost, 6)
        }

        self.logs.append(log_entry)
        self._save_logs()

        print(f"[Claude] {task} | {model_short} | {input_tokens}in/{output_tokens}out tokens")

    def _save_logs(self):
        """Persist logs to JSON file."""
        try:
            with open(self.log_file, 'w') as f:
                json.dump(self.logs, f, indent=2)
        except Exception as e:
            print(f"      ⚠️ Failed to save logs: {e}")

    def get_usage_summary(self, days: int = 7) -> Dict:
        """
        Get usage summary for the past N days.

        Args:
            days: Number of days to summarize (default 7)

        Returns:
            Dictionary with usage statistics
        """
        from datetime import timedelta

        cutoff = datetime.now() - timedelta(days=days)
        recent_logs = [
            log for log in self.logs
            if datetime.fromisoformat(log['timestamp']) > cutoff
        ]

        # Count requests by API and endpoint
        summary = {
            'total_requests': len(recent_logs),
            'by_api': {},
            'by_endpoint': {},
            'failures': []
        }

        for log in recent_logs:
            api = log['api']
            endpoint = log.get('endpoint', 'unknown')

            # Count by API
            summary['by_api'][api] = summary['by_api'].get(api, 0) + 1

            # Count by endpoint
            key = f"{api}:{endpoint}"
            summary['by_endpoint'][key] = summary['by_endpoint'].get(key, 0) + 1

            # Track failures
            if log.get('status') == 'FAILED':
                summary['failures'].append(log)

        return summary

    def print_usage_report(self, days: int = 7):
        """Print a formatted usage report."""
        summary = self.get_usage_summary(days)

        print("\n" + "="*50)
        print(f"   API USAGE REPORT (Last {days} Days)")
        print("="*50)
        print(f"Total Requests: {summary['total_requests']}")
        print("\nBy API:")
        for api, count in summary['by_api'].items():
            print(f"  - {api}: {count} requests")

        print("\nBy Endpoint:")
        for endpoint, count in sorted(summary['by_endpoint'].items(), key=lambda x: -x[1]):
            print(f"  - {endpoint}: {count} requests")

        if summary['failures']:
            print(f"\n⚠️ Failures: {len(summary['failures'])}")
            for failure in summary['failures'][-5:]:  # Show last 5 failures
                print(f"  - {failure['api']}:{failure['endpoint']} - {failure['error'][:50]}")

        print("="*50 + "\n")


# Singleton instance for global use
_monitor_instance = None

def get_monitor() -> APIMonitor:
    """Get or create the global API monitor instance."""
    global _monitor_instance
    if _monitor_instance is None:
        _monitor_instance = APIMonitor()
    return _monitor_instance
