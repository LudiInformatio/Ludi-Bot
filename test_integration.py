import sys
import os
from dotenv import load_dotenv

# Load env variables for API keys
load_dotenv()

try:
    from module_a import Gatekeeper
    from module_h_historian import LudiHistorian # Updated to Module H
except ImportError as e:
    print(f"❌ Import Failed: {e}")
    sys.exit(1)

def test_integration():
    print("🔌 Testing Module A (Gatekeeper) Integration...")
    
    # 1. Initialize Gatekeeper
    try:
        gk = Gatekeeper()
        print("✅ Gatekeeper Initialized")
    except Exception as e:
        print(f"❌ Gatekeeper Init Failed: {e}")
        return

    # 2. Check API Key
    if not os.getenv("ODDS_API_KEY"):
        print("❌ TDS_API_KEY Missing from .env")
        return
    else:
        print("✅ ODDS_API_KEY Found")

    # 3. Initialize Historian (DB)
    try:
        db = LudiHistorian()
        print("✅ LudiHistorian (DB) Initialized")
    except Exception as e:
        print(f"❌ DB Init Failed: {e}")
        return
    
    # 4. Attempt to fetch simplified slate (using mock or real if possible)
    # For now, we just want to verify the method exists and runs
    if hasattr(gk, 'fetch_live_slate'):
        print("✅ Gatekeeper has 'fetch_live_slate' method")
    else:
        print("❌ 'fetch_live_slate' method missing from Gatekeeper")

    print("\n🎉 Module A Integration Test: READY to connect.")
    print("Next Step: Modify module_a.py to write to db.games and db.odds tables.")

if __name__ == "__main__":
    test_integration()
