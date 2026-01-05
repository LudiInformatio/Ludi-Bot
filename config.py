# LUDI INFORMATIO | SYSTEM CONFIGURATION
# ----------------------------------------
# SECURE VERSION - Loads sensitive keys from .env file
# Updated: January 4, 2026

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# ====================================================
# 1. ODDS & LINES PROVIDERS
# ====================================================

# PRIMARY FOR GAME LINES (Spreads, Totals, Moneyline)
# Source: https://the-odds-api.com/
ODDS_API_KEY = os.getenv('ODDS_API_KEY')

# PRIMARY FOR PLAYER PROPS (Source 1)
# Source: https://sportsgameodds.com/
SGO_API_KEY = os.getenv('SGO_API_KEY')

# ====================================================
# 2. DATA & STATS PROVIDERS
# ====================================================

# LIVE STATS & ROSTERS (Tank01)
# Source: https://rapidapi.com/tank01/api/tank01-fantasy-stats
TANK01_KEY = os.getenv('TANK01_KEY')

# ====================================================
# 3. NEWS & SCOUTING (The Yak)
# ====================================================

# GOOGLE CUSTOM SEARCH (Contextual News)
GOOGLE_SEARCH_KEY = os.getenv('GOOGLE_SEARCH_KEY')
GOOGLE_SEARCH_CX = os.getenv('GOOGLE_SEARCH_CX')

# ====================================================
# 4. ALERTS & REPORTING
# ====================================================

# TELEGRAM BOT (Morning Briefing)
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

# ====================================================
# 5. GLOBAL SETTINGS (Non-Sensitive)
# ====================================================
CURRENT_SEASON = "2025-2026"
REFRESH_HOURS = 6
BRAND_HEADER = "ludi informatio"

# Feature Flags
ENABLE_TELEGRAM_ALERTS = True
RUN_SEASON_INIT = False

# ====================================================
# 6. DFS & PROP SETTINGS (THE UNLOCK)
# ====================================================

# The-Odds-API: Region for DFS is distinct from 'us'
TOA_DFS_REGION = 'us_dfs'  # Targets PrizePicks, Underdog, etc.
TOA_MARKETS = 'player_points,player_rebounds,player_assists'

# SportsGameOdds: Specific Bookmaker IDs to filter noise
# These string IDs force the API to return only DFS data
SGO_DFS_BOOKS = "prizepicks,underdog,dabble"

# Set to True to catch "Demons/Goblins" (Alt lines)
SGO_INCLUDE_ALTS = True

# ====================================================
# 7. VALIDATION (Startup Check)
# ====================================================

def validate_config():
    """Verify all required API keys are loaded"""
    required_keys = {
        'ODDS_API_KEY': ODDS_API_KEY,
        'TANK01_KEY': TANK01_KEY,
        'GOOGLE_SEARCH_KEY': GOOGLE_SEARCH_KEY,
        'TELEGRAM_TOKEN': TELEGRAM_TOKEN
    }

    missing = [key for key, value in required_keys.items() if not value]

    if missing:
        raise ValueError(f"Missing required API keys in .env file: {', '.join(missing)}")

    print("✅ All API keys loaded successfully from .env")

# Run validation on import (can be disabled for testing)
if __name__ != "__main__":
    validate_config()
