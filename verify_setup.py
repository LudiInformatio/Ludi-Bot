#!/usr/bin/env python3
"""
LUDI BOT - Setup Verification Script
Checks if all dependencies and configuration are ready
"""

import sys
import os

def check_dependencies():
    """Check if all required Python packages are installed"""
    print("🔍 Checking Python dependencies...")
    
    required_packages = [
        'requests', 'dotenv', 'pandas', 'numpy', 'lxml',
        'google.genai', 'duckduckgo_search', 'bs4', 
        'unidecode', 'pytz', 'inputimeout'
    ]
    
    missing = []
    for package in required_packages:
        try:
            if package == 'dotenv':
                __import__('dotenv')
            elif package == 'bs4':
                __import__('bs4')
            elif package == 'google.genai':
                __import__('google.genai')
            else:
                __import__(package)
            print(f"  ✅ {package}")
        except ImportError:
            print(f"  ❌ {package}")
            missing.append(package)
    
    if missing:
        print(f"\n⚠️  Missing packages: {', '.join(missing)}")
        print("   Run: python3 -m pip install -r requirements.txt")
        return False
    else:
        print("\n✅ All dependencies installed!")
        return True

def check_env_file():
    """Check if .env file exists and has required keys"""
    print("\n🔍 Checking .env configuration...")
    
    if not os.path.exists('.env'):
        print("  ❌ .env file not found")
        print("   Create it from .env.template:")
        print("   cp .env.template .env")
        return False
    
    print("  ✅ .env file exists")
    
    # Check if config module loads
    try:
        import config
        
        has_odds_key = config.ODDS_API_KEY and config.ODDS_API_KEY != 'your_odds_api_key_here'
        has_tank_key = config.TANK01_KEY and config.TANK01_KEY != 'your_tank01_key_here'
        
        if has_odds_key:
            print("  ✅ ODDS_API_KEY configured")
        else:
            print("  ⚠️  ODDS_API_KEY needs to be set (currently placeholder)")
            
        if has_tank_key:
            print("  ✅ TANK01_KEY configured")
        else:
            print("  ⚠️  TANK01_KEY needs to be set (currently placeholder)")
        
        if not (has_odds_key and has_tank_key):
            print("\n⚠️  API keys need to be configured in .env file")
            print("   See SETUP_INSTRUCTIONS.md for details")
            return False
        
        return True
        
    except Exception as e:
        print(f"  ❌ Error loading config: {e}")
        return False

def check_database():
    """Check if database file exists"""
    print("\n🔍 Checking database...")
    
    if os.path.exists('ludi.db'):
        size_mb = os.path.getsize('ludi.db') / (1024 * 1024)
        print(f"  ✅ ludi.db exists ({size_mb:.1f} MB)")
        return True
    else:
        print("  ⚠️  ludi.db not found (will be created on first run)")
        return True  # Not critical

def check_modules():
    """Check if all Ludi modules can be imported"""
    print("\n🔍 Checking Ludi modules...")
    
    modules = [
        ('module_a', 'Gatekeeper'),
        ('module_b', 'print_sharp_box_score'),
        ('module_c', 'LudiOracle'),
        ('module_d', 'LudiYak'),
        ('module_e', 'LudiCalibrator'),
        ('module_f', 'LudiReporter'),
        ('module_g', 'LudiRefEngine'),
        ('module_h_historian', 'LudiHistorian'),
        ('module_x_scenario', 'ScenarioBuilder'),
    ]
    
    all_ok = True
    for module_name, class_name in modules:
        try:
            module = __import__(module_name)
            if hasattr(module, class_name) or class_name == 'print_sharp_box_score':
                print(f"  ✅ {module_name}")
            else:
                print(f"  ⚠️  {module_name} (missing {class_name})")
                all_ok = False
        except Exception as e:
            print(f"  ❌ {module_name}: {e}")
            all_ok = False
    
    return all_ok

def main():
    print("=" * 60)
    print("  LUDI BOT - SETUP VERIFICATION")
    print("=" * 60)
    
    deps_ok = check_dependencies()
    env_ok = check_env_file()
    db_ok = check_database()
    modules_ok = check_modules()
    
    print("\n" + "=" * 60)
    print("  SUMMARY")
    print("=" * 60)
    
    if deps_ok and env_ok and modules_ok:
        print("✅ System is ready to run!")
        print("\nTo start the bot, run:")
        print("  python3 main.py")
        print("  python3 main.py --games CLE SAC")
        print("\nFor help:")
        print("  python3 main.py --help")
        return 0
    else:
        print("⚠️  Setup incomplete. Please address the issues above.")
        print("\nSee SETUP_INSTRUCTIONS.md for detailed setup guide.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
