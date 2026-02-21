#!/usr/bin/env python
"""
Single API Call Test - Phase 3
Tests one API call to verify monitoring and paid tier integration
Cost: ~6 credits (~$0.01)
"""

import json
import os
from module_a import Gatekeeper

def test_single_slate_fetch():
    """Test single slate fetch with monitoring"""
    print("\n" + "="*60)
    print("PHASE 3: SINGLE API CALL TEST")
    print("="*60)
    print("Expected cost: ~6 credits (~$0.01)")
    print("="*60 + "\n")

    # Initialize Gatekeeper
    print("[1] Initializing Gatekeeper...")
    gk = Gatekeeper()
    print("    ✅ Gatekeeper initialized\n")

    # Make single API call
    print("[2] Fetching live slate (ONE API call)...")
    try:
        gk.fetch_live_slate()
        print("\n    ✅ Slate fetch completed\n")
    except Exception as e:
        print(f"\n    ❌ Error during fetch: {e}\n")
        return False

    # Verify monitoring logs created
    print("[3] Verifying monitoring logs...")
    if os.path.exists('api_usage_log.json'):
        with open('api_usage_log.json', 'r') as f:
            logs = json.load(f)

        print(f"    ✅ Log file created with {len(logs)} entries")

        # Display latest log entry
        if logs:
            latest = logs[-1]
            print("\n[4] Latest Log Entry:")
            print(f"    - API: {latest.get('api')}")
            print(f"    - Endpoint: {latest.get('endpoint')}")
            print(f"    - Timestamp: {latest.get('timestamp')}")

            rate_info = latest.get('rate_limit_info', {})
            if rate_info:
                print(f"    - Rate Limit Info:")
                for key, value in rate_info.items():
                    print(f"      • {key}: {value}")

                # Calculate cost
                requests_used = rate_info.get('requests_used', 'N/A')
                print(f"\n[5] Cost Analysis:")
                print(f"    - Credits used: {requests_used}")
                if requests_used != 'N/A':
                    try:
                        cost = int(requests_used) * 0.0015  # $30/20000 = $0.0015 per credit
                        print(f"    - Estimated cost: ${cost:.4f}")
                    except (ValueError, TypeError):
                        pass
            else:
                print("    ⚠️  No rate limit info found in headers")
    else:
        print("    ❌ Log file not created")
        return False

    print("\n" + "="*60)
    print("PHASE 3: COMPLETE ✅")
    print("="*60)
    return True

if __name__ == "__main__":
    success = test_single_slate_fetch()

    if success:
        print("\n✅ Ready to proceed to Phase 4 (3-game test)")
        print("   Estimated Phase 4 cost: ~96 credits (~$0.14)")
    else:
        print("\n❌ Fix issues before proceeding to Phase 4")
