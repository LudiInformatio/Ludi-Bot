#!/usr/bin/env python
"""
3-Game Validation Test - Phase 4
Tests full pipeline with 3 games to measure realistic costs
Expected cost: ~96 credits (~$0.14)
"""

import json
import os
from datetime import datetime
from module_a import Gatekeeper

def test_3_game_pipeline():
    """Test full pipeline with 3 games"""
    print("\n" + "="*60)
    print("PHASE 4: 3-GAME VALIDATION TEST")
    print("="*60)
    print("Expected cost: ~96 credits (~$0.14)")
    print("  - Slate fetch: 6 credits")
    print("  - Props (3 games × 30): 90 credits")
    print("="*60 + "\n")

    # Track initial state
    initial_credits = None
    if os.path.exists('api_usage_log.json'):
        with open('api_usage_log.json', 'r') as f:
            logs = json.load(f)
            if logs:
                initial_credits = int(logs[-1]['rate_limit_info']['requests_remaining'])
                print(f"[START] Initial credits: {initial_credits:,}\n")

    # Initialize Gatekeeper
    print("[1] Initializing Gatekeeper...")
    gk = Gatekeeper()
    print("    ✅ Gatekeeper initialized\n")

    # Fetch slate
    print("[2] Fetching live slate...")
    try:
        gk.fetch_live_slate()
        print("    ✅ Slate fetch completed\n")
    except Exception as e:
        print(f"    ❌ Error during slate fetch: {e}\n")
        return False

    # Fetch props for 3 games
    print("[3] Fetching props for 3 games...")
    try:
        gk.fetch_comprehensive_props(limit_games=3)
        print("    ✅ Props fetch completed\n")
    except Exception as e:
        print(f"    ❌ Error during props fetch: {e}\n")
        return False

    # Analyze results
    print("[4] Analyzing API Usage...")
    if os.path.exists('api_usage_log.json'):
        with open('api_usage_log.json', 'r') as f:
            logs = json.load(f)

        # Count API calls by endpoint
        endpoint_counts = {}
        total_credits = 0

        for log in logs:
            endpoint = log.get('endpoint')
            rate_info = log.get('rate_limit_info', {})

            if endpoint not in endpoint_counts:
                endpoint_counts[endpoint] = {'count': 0, 'credits': 0}

            endpoint_counts[endpoint]['count'] += 1

            # Track credits used
            if 'request_cost' in rate_info:
                try:
                    credits = int(rate_info['request_cost'])
                    endpoint_counts[endpoint]['credits'] += credits
                    total_credits += credits
                except:
                    pass

        # Display breakdown
        print(f"    Total log entries: {len(logs)}")
        print(f"\n    Breakdown by endpoint:")
        for endpoint, stats in endpoint_counts.items():
            print(f"      - {endpoint}: {stats['count']} calls, {stats['credits']} credits")

        # Get final credits
        final_credits = int(logs[-1]['rate_limit_info']['requests_remaining'])
        credits_used = initial_credits - final_credits if initial_credits else total_credits

        print(f"\n[5] Cost Analysis:")
        print(f"    - Credits used (this session): {credits_used}")
        print(f"    - Remaining credits: {final_credits:,}")

        # Calculate cost
        cost_per_credit = 30.0 / 20000  # $30 for 20K credits = $0.0015/credit
        session_cost = credits_used * cost_per_credit

        print(f"    - Session cost: ${session_cost:.4f}")

        # Calculate cost per game
        cost_per_game = session_cost / 3 if session_cost > 0 else 0
        print(f"    - Cost per game: ${cost_per_game:.4f}")

        # Budget check
        budget_target = 0.10
        print(f"\n[6] Budget Validation:")
        if cost_per_game < budget_target:
            print(f"    ✅ UNDER BUDGET (${cost_per_game:.4f} < ${budget_target:.2f})")
        else:
            print(f"    ⚠️  OVER BUDGET (${cost_per_game:.4f} > ${budget_target:.2f})")

        # Monthly projection
        games_per_day = 12
        avg_games_analyzed = 3  # Conservative estimate
        daily_cost = cost_per_game * avg_games_analyzed
        monthly_cost = daily_cost * 30

        print(f"\n[7] Monthly Projections:")
        print(f"    - Daily cost (3 games): ${daily_cost:.2f}")
        print(f"    - Monthly cost: ${monthly_cost:.2f}")
        print(f"    - Paid tier cost: $30.00")
        if monthly_cost < 30:
            headroom = 30 - monthly_cost
            print(f"    - Headroom: ${headroom:.2f} (✅ Comfortable)")
        else:
            print(f"    - ⚠️  Projected usage exceeds tier limit")

    else:
        print("    ❌ Log file not found")
        return False

    print("\n" + "="*60)
    print("PHASE 4: COMPLETE ✅")
    print("="*60)
    return True

if __name__ == "__main__":
    success = test_3_game_pipeline()

    if success:
        print("\n✅ Ready to proceed to Phase 5 (Review & Validate)")
    else:
        print("\n❌ Fix issues before proceeding")
