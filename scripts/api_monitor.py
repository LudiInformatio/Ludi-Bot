#!/usr/bin/env python3
"""
scripts/api_monitor.py

Pre-flight quota gate for the daily simulation pipeline.
Checks live quota levels for The-Odds-API and Tank01/RapidAPI.
Raises SystemExit(1) if either quota is critically low and exit_on_fail=True.

Usage:
    python scripts/api_monitor.py --check-quotas --exit-on-fail
    python scripts/api_monitor.py --check-quotas            # monitoring mode, no exit
"""

import argparse
import json
import logging
import os
import sys
from datetime import date
from typing import Optional, Tuple

import requests

# Add project root to path so utils imports work
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [api_monitor] %(levelname)s %(message)s'
)
logger = logging.getLogger('api_monitor')

ODDS_API_CRITICAL_THRESHOLD = 3000
ODDS_API_EXHAUSTED_THRESHOLD = 0  # Fully exhausted — BDL fallback takes over, pipeline continues
TANK01_CRITICAL_THRESHOLD = 50


def _read_today_snapshot(api_name: str, log_file: str = 'api_usage_log.json') -> Optional[dict]:
    if not os.path.exists(log_file):
        return None
    try:
        with open(log_file, 'r') as f:
            logs = json.load(f)
        if not isinstance(logs, list):
            return None
        today_str = date.today().isoformat()
        entries = [
            e for e in logs
            if e.get('api') == api_name
            and e.get('timestamp', '').startswith(today_str)
            and 'rate_limit_info' in e
        ]
        if entries:
            return entries[-1]['rate_limit_info']
    except Exception as e:
        logger.warning(f"[snapshot] Could not read {log_file}: {e}")
    return None


def _fetch_odds_api_quota(api_key: str) -> Tuple[Optional[int], Optional[int]]:
    url = "https://api.the-odds-api.com/v4/sports"
    try:
        resp = requests.get(url, params={"apiKey": api_key}, timeout=10)
        remaining_raw = resp.headers.get("x-requests-remaining")
        used_raw = resp.headers.get("x-requests-used")
        if remaining_raw is None:
            logger.warning(
                f"[odds_api] x-requests-remaining header absent "
                f"(status={resp.status_code}) — key may be invalid"
            )
            return None, None
        return int(remaining_raw), int(used_raw) if used_raw else None
    except requests.exceptions.RequestException as e:
        logger.warning(f"[odds_api] Network error fetching quota: {e}")
        return None, None
    except ValueError as e:
        logger.warning(f"[odds_api] Could not parse quota headers: {e}")
        return None, None


def _fetch_tank01_quota(api_key: str) -> Tuple[Optional[int], Optional[int]]:
    url = "https://tank01-fantasy-stats.p.rapidapi.com/getNBATeams"
    headers = {
        "x-rapidapi-key": api_key,
        "x-rapidapi-host": "tank01-fantasy-stats.p.rapidapi.com",
    }
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        remaining_raw = resp.headers.get(
            "x-ratelimit-requests-remaining",
            resp.headers.get("x-ratelimit-remaining")
        )
        limit_raw = resp.headers.get(
            "x-ratelimit-requests-limit",
            resp.headers.get("x-ratelimit-limit")
        )
        if remaining_raw is None:
            logger.warning(
                f"[tank01] x-ratelimit-requests-remaining header absent "
                f"(status={resp.status_code}) — key may be invalid"
            )
            return None, None
        return int(remaining_raw), int(limit_raw) if limit_raw else None
    except requests.exceptions.RequestException as e:
        logger.warning(f"[tank01] Network error fetching quota: {e}")
        return None, None
    except ValueError as e:
        logger.warning(f"[tank01] Could not parse quota headers: {e}")
        return None, None


def check_quotas(exit_on_fail: bool = False) -> dict:
    """
    Check remaining quota for The-Odds-API and Tank01.

    Strategy: try today's snapshot first (avoids a live call), then live HTTP if needed.
    Network errors log a warning and continue — quota unknown != quota exhausted.
    Only confirmed < threshold quota triggers SystemExit when exit_on_fail=True.

    Returns dict with keys 'odds_api' and 'tank01', each containing 'remaining', 'status'.
    """
    odds_api_key = os.environ.get("ODDS_API_KEY")
    tank01_key = os.environ.get("TANK01_KEY")
    results = {}

    # --- Odds API ---
    odds_remaining = None
    snapshot = _read_today_snapshot("odds_api")
    if snapshot:
        try:
            odds_remaining = int(snapshot.get("requests_remaining", "N/A"))
            logger.info(f"[odds_api] Quota from today snapshot: {odds_remaining} remaining")
        except (ValueError, TypeError) as e:
            logger.warning(f"[odds_api] Could not parse snapshot: {e}")

    if odds_remaining is None:
        if not odds_api_key:
            logger.warning("[odds_api] ODDS_API_KEY not set — skipping live quota check")
        else:
            logger.info("[odds_api] No today snapshot — fetching live quota")
            odds_remaining, _ = _fetch_odds_api_quota(odds_api_key)

    if odds_remaining is not None:
        logger.info(f"[odds_api] {odds_remaining} credits remaining")
        if odds_remaining <= 0:
            msg = (
                f"Odds API quota exhausted ({odds_remaining} credits). "
                f"BDL/ESPN fallback active — pipeline continuing."
            )
            logger.warning(f"[odds_api] WARNING: {msg}")
            results["odds_api"] = {"remaining": odds_remaining, "status": "EXHAUSTED_FALLBACK"}
            # Do NOT raise SystemExit — Module A has BDL and ESPN fallbacks
        elif odds_remaining < ODDS_API_CRITICAL_THRESHOLD:
            msg = (
                f"Odds API quota critically low: {odds_remaining} remaining "
                f"(threshold: {ODDS_API_CRITICAL_THRESHOLD}). "
                f"Aborting to prevent mid-run exhaustion."
            )
            logger.error(f"[odds_api] CRITICAL: {msg}")
            results["odds_api"] = {"remaining": odds_remaining, "status": "CRITICAL"}
            if exit_on_fail:
                raise SystemExit(f"[T5b] {msg}")
        else:
            results["odds_api"] = {"remaining": odds_remaining, "status": "OK"}
    else:
        logger.warning(
            "[odds_api] Quota unavailable — could not confirm level. "
            "Pipeline will continue (quota unknown != quota exhausted)."
        )
        results["odds_api"] = {"remaining": None, "status": "UNKNOWN"}

    # --- Tank01 ---
    tank01_remaining = None
    snapshot = _read_today_snapshot("tank01")
    if snapshot:
        try:
            tank01_remaining = int(snapshot.get("requests_remaining", "N/A"))
            logger.info(f"[tank01] Quota from today snapshot: {tank01_remaining} remaining")
        except (ValueError, TypeError) as e:
            logger.warning(f"[tank01] Could not parse snapshot: {e}")

    if tank01_remaining is None:
        if not tank01_key:
            logger.warning("[tank01] TANK01_KEY not set — skipping live quota check")
        else:
            logger.info("[tank01] No today snapshot — fetching live quota")
            tank01_remaining, tank01_limit = _fetch_tank01_quota(tank01_key)

    if tank01_remaining is not None:
        logger.info(f"[tank01] {tank01_remaining} calls remaining today")
        if tank01_remaining < TANK01_CRITICAL_THRESHOLD:
            msg = (
                f"Tank01 quota critically low: {tank01_remaining} remaining "
                f"(threshold: {TANK01_CRITICAL_THRESHOLD}). "
                f"Pipeline aborted to prevent mid-run exhaustion."
            )
            logger.error(f"[tank01] CRITICAL: {msg}")
            results["tank01"] = {"remaining": tank01_remaining, "status": "CRITICAL"}
            if exit_on_fail:
                raise SystemExit(f"[T5b] {msg}")
        else:
            results["tank01"] = {"remaining": tank01_remaining, "status": "OK"}
    else:
        logger.warning(
            "[tank01] Quota unavailable — could not confirm level. "
            "Pipeline will continue (quota unknown != quota exhausted)."
        )
        results["tank01"] = {"remaining": None, "status": "UNKNOWN"}

    return results


def main():
    parser = argparse.ArgumentParser(
        description="Pre-flight API quota check for the daily simulation pipeline."
    )
    parser.add_argument(
        "--check-quotas",
        action="store_true",
        help="Run quota check for The-Odds-API and Tank01",
    )
    parser.add_argument(
        "--exit-on-fail",
        action="store_true",
        help="Raise SystemExit(1) if any quota is critically low (use in CI/CD gates)",
    )
    args = parser.parse_args()

    if args.check_quotas:
        results = check_quotas(exit_on_fail=args.exit_on_fail)
        critical = [api for api, r in results.items() if r["status"] == "CRITICAL"]
        if critical:
            logger.error(f"[preflight] CRITICAL quota for: {', '.join(critical)}")
            if args.exit_on_fail:
                sys.exit(1)
        else:
            logger.info("[preflight] All quota checks passed.")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
