# ARCHIVED: 2026-03-03 — Endpoint discovery tool — keep for API debugging reference
"""
SportsDataIO Discovery Lab — Endpoint Discovery Tester
Tests all confirmed endpoints and probes locked paths to document tier access.

Usage:
    python scripts/test_sportsdata_endpoints.py             # Quick status table
    python scripts/test_sportsdata_endpoints.py --save      # Save raw JSON to cache/sportsdata/discovery/
    python scripts/test_sportsdata_endpoints.py --verbose   # Show sample data from each endpoint
    python scripts/test_sportsdata_endpoints.py --save --verbose

Cost: ~10 API calls (respects 1s rate limit, skips cache so fresh results)
"""

import os
import sys
import json
import time
import argparse
import requests
from datetime import datetime, timedelta

# Ensure project root is in path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config

DISCOVERY_DIR = "cache/sportsdata/discovery"
BASE_FANTASY  = "https://api.sportsdata.io/api/nba/fantasy/json"
BASE_SCORES   = "https://api.sportsdata.io/v3/nba/scores/json"
BASE_STATS    = "https://api.sportsdata.io/v3/nba/stats/json"
BASE_ODDS     = "https://api.sportsdata.io/v3/nba/odds/json"


def _get_session() -> requests.Session:
    """Build authenticated session using Fantasy API key."""
    s = requests.Session()
    key = config.SPORTSDATA_API_KEY
    if not key:
        print("❌  SPORTSDATA_API_KEY not set in .env — cannot run tests")
        sys.exit(1)
    s.headers.update({
        "Ocp-Apim-Subscription-Key": key,
        "Accept": "application/json",
    })
    return s


def _test_endpoint(session, url: str, label: str, save: bool, verbose: bool) -> dict:
    """
    Hit one endpoint and return a result dict.
    Enforces 1s sleep between calls to respect 100/day quota.
    """
    time.sleep(1.0)
    result = {
        "label": label,
        "url": url,
        "status": None,
        "record_count": None,
        "sample": None,
        "error": None,
    }
    try:
        resp = session.get(url, timeout=15)
        result["status"] = resp.status_code

        if resp.status_code == 200:
            try:
                data = resp.json()
                if isinstance(data, list):
                    result["record_count"] = len(data)
                    result["sample"] = data[0] if data else {}
                elif isinstance(data, dict):
                    result["record_count"] = 1
                    result["sample"] = data
            except Exception as e:
                result["error"] = f"JSON parse error: {e}"

            # Save raw response if requested
            if save:
                os.makedirs(DISCOVERY_DIR, exist_ok=True)
                safe_label = label.replace("/", "_").replace(" ", "_").replace("{", "").replace("}", "")
                path = os.path.join(DISCOVERY_DIR, f"{safe_label}.json")
                try:
                    with open(path, "w") as f:
                        json.dump(resp.json(), f, indent=2)
                except Exception:
                    pass

        else:
            # Try to read error body
            try:
                result["error"] = resp.text[:200]
            except Exception:
                pass

    except requests.exceptions.Timeout:
        result["status"] = "TIMEOUT"
        result["error"] = "Request timed out after 15s"
    except Exception as e:
        result["status"] = "ERROR"
        result["error"] = str(e)

    return result


def _print_result(r: dict, verbose: bool):
    """Print a single result row."""
    status = r["status"]
    label  = r["label"]
    count  = r["record_count"]
    err    = r["error"] or ""

    if status == 200:
        count_str = f"{count} records" if count is not None else "?"
        print(f"  ✅  {label:<55} {count_str}")
        if verbose and r["sample"]:
            sample_keys = list(r["sample"].keys())[:8]
            print(f"       Sample keys: {sample_keys}")
    elif status in (401, 403):
        print(f"  🔒  {label:<55} HTTP {status} — Needs paid tier")
    elif status == 404:
        print(f"  ❌  {label:<55} HTTP 404 — Wrong API path or not available")
    else:
        print(f"  ⚠️  {label:<55} HTTP {status}  {err[:60]}")


def main():
    parser = argparse.ArgumentParser(description="SportsDataIO endpoint discovery tester")
    parser.add_argument("--save", action="store_true", help="Save raw JSON to cache/sportsdata/discovery/")
    parser.add_argument("--verbose", action="store_true", help="Show sample field names from each endpoint")
    args = parser.parse_args()

    session = _get_session()

    # Build sample dates for parameterized endpoints
    today = datetime.now()
    yesterday = today - timedelta(days=1)
    last_season_date = "2025-JAN-15"   # Reliable 2024-25 game date (mid-season)
    today_str = today.strftime("%Y-%b-%d").upper()
    yesterday_str = yesterday.strftime("%Y-%b-%d").upper()

    print("\n" + "=" * 70)
    print("  SPORTSDATA.IO ENDPOINT DISCOVERY REPORT")
    print(f"  Run time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Key tier: {config.SPORTSDATA_TIER.upper()}")
    print("=" * 70)

    # --------------------------------------------------------
    # CONFIRMED WORKING (Fantasy API path)
    # --------------------------------------------------------
    print("\n📦  FANTASY API PATH (free tier — confirmed working Feb 22, 2026)")
    print("-" * 70)

    fantasy_endpoints = [
        (f"{BASE_FANTASY}/teams",                                          "teams"),
        (f"{BASE_FANTASY}/Players",                                        "Players (live injuries + rosters)"),
        (f"{BASE_FANTASY}/PlayerSeasonStats/2025",                         "PlayerSeasonStats/2025 (2024-25)"),
        (f"{BASE_FANTASY}/Standings/2025",                                 "Standings/2025 (2024-25)"),
        (f"{BASE_FANTASY}/PlayerGameStatsByDate/{last_season_date}",       f"PlayerGameStatsByDate/{last_season_date}"),
        (f"{BASE_FANTASY}/PlayerGameProjectionStatsByDate/{today_str}",    f"PlayerGameProjectionStatsByDate/{today_str}"),
        (f"{BASE_FANTASY}/DfsSlatesByDate/{today_str}",                    f"DfsSlatesByDate/{today_str}"),
        (f"{BASE_FANTASY}/CurrentSeason",                                  "CurrentSeason"),
    ]

    results_fantasy = []
    for url, label in fantasy_endpoints:
        r = _test_endpoint(session, url, label, args.save, args.verbose)
        _print_result(r, args.verbose)
        results_fantasy.append(r)

    # --------------------------------------------------------
    # PAID TIER PROBES (should return 401/403/404)
    # --------------------------------------------------------
    print("\n🔐  PAID TIER PROBES (documenting what's locked)")
    print("-" * 70)

    paid_probes = [
        (f"{BASE_FANTASY}/PlayerSeasonStats/2026",                          "PlayerSeasonStats/2026 (current — paid Fantasy)"),
        (f"{BASE_FANTASY}/Standings/2026",                                  "Standings/2026 (current — paid Fantasy)"),
        (f"{BASE_SCORES}/GamesByDate/{today_str}",                          "GamesByDate (Scores API)"),
        (f"{BASE_SCORES}/Referees",                                         "Referees (Scores API)"),
        (f"{BASE_SCORES}/ProjectedPlayerGameStatsByDate/{today_str}",       "Projected lineups (Scores API)"),
        (f"{BASE_STATS}/PlayerGameStatsByDate/{today_str}",                 "PlayerGameStats/current (Stats API)"),
        (f"{BASE_ODDS}/PlayerPropsByDate/{today_str}",                      "PlayerProps (Odds API)"),
    ]

    results_paid = []
    for url, label in paid_probes:
        r = _test_endpoint(session, url, label, args.save, args.verbose)
        _print_result(r, args.verbose)
        results_paid.append(r)

    # --------------------------------------------------------
    # SUMMARY
    # --------------------------------------------------------
    print("\n" + "=" * 70)
    working = sum(1 for r in results_fantasy if r["status"] == 200)
    locked  = sum(1 for r in results_paid if r["status"] in (401, 403))
    not_found = sum(1 for r in results_paid if r["status"] == 404)
    errors  = sum(1 for r in (results_fantasy + results_paid) if r["status"] not in (200, 401, 403, 404))

    print(f"  ✅  Working endpoints:  {working}/{len(fantasy_endpoints)}")
    print(f"  🔒  Locked (paid tier): {locked}")
    print(f"  ❌  Not found (404):    {not_found}")
    if errors:
        print(f"  ⚠️  Errors:             {errors}")

    # Show injury summary if Players returned 200
    players_result = next((r for r in results_fantasy if "Players" in r["label"]), None)
    if players_result and players_result["status"] == 200 and players_result["record_count"]:
        print(f"\n  ℹ️  Players endpoint: {players_result['record_count']} total players")
        if args.save:
            saved_path = os.path.join(DISCOVERY_DIR, "Players_live_injuries_rosters_.json")
            if os.path.exists(saved_path):
                try:
                    with open(saved_path) as f:
                        players = json.load(f)
                    injured = [p for p in players if p.get("InjuryStatus") and p["InjuryStatus"] not in ("", None)]
                    suspended = [p for p in players if p.get("Status") == "Suspended"]
                    print(f"       Injured players: {len(injured)}")
                    print(f"       Suspended players: {len(suspended)}")
                    if suspended and args.verbose:
                        for p in suspended:
                            name = f"{p.get('FirstName','')} {p.get('LastName','')}".strip()
                            team = p.get("Team", "?")
                            notes = p.get("InjuryNotes", "")[:80]
                            print(f"         🚫 {name} ({team}): {notes}")
                except Exception:
                    pass

    if args.save:
        print(f"\n  💾  Raw JSON saved to: {DISCOVERY_DIR}/")

    print("=" * 70 + "\n")

    # Exit with error code if no working endpoints (helps CI detect problems)
    if working == 0:
        print("❌  No working endpoints found. Check SPORTSDATA_API_KEY in .env")
        sys.exit(1)


if __name__ == "__main__":
    main()
