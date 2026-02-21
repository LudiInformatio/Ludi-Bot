# LUDI INFORMATIO | SYSTEM CONFIGURATION
# ----------------------------------------
# SECURE VERSION - Loads sensitive keys from .env file
# Updated: January 4, 2026

import os
import json
import functools
from dotenv import load_dotenv

# Load environment variables from .env file ONLY if not in production/CI
# This prevents local .env files from overriding injected secrets in Docker/CI
if not os.getenv('IS_SELF_HOSTED'):
    load_dotenv()
else:
    print("🔒 Running in Self-Hosted Mode: Skipping .env load (relying on injected secrets)")

# ====================================================
# 0. DATABASE CONFIGURATION
# ====================================================
DB_PATH = "ludi.db"

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
TANK01_HOST = "tank01-fantasy-stats.p.rapidapi.com"

# ====================================================
# 2b. NEW PAID APIs (Placeholders - Add keys to .env)
# ====================================================

# API-SPORTS (Historical Data + Livescores)
# Source: https://api-sports.io/documentation/nba/v2
# Pricing: $25/mo for Pro tier
APISPORTS_KEY = os.getenv('APISPORTS_KEY')
APISPORTS_HOST = "v2.nba.api-sports.io"

# BALLDONTLIE (Props Validation + Injuries + Play-by-Play)
# Source: https://docs.balldontlie.io
# Pricing: GOAT tier $39.99/mo (600 req/min)
BALLDONTLIE_KEY = os.getenv('BALLDONTLIE_KEY')
BALLDONTLIE_HOST = "api.balldontlie.io"

# GEMINI AI (Ask Ludi Chatbot - Week 7)
# Source: https://ai.google.dev/
# Pricing: Pay-as-you-go (~$5-10/mo estimated)
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

# PERPLEXITY API (Research queries)
# Source: https://docs.perplexity.ai/
PERPLEXITY_API_KEY = os.getenv('PERPLEXITY_API_KEY')

# --- Claude API (Phase 8 AI Integration) ---
def _get_claude_auth_token() -> str:
    """Returns Claude auth token. Priority: OAuth env → local config → API key."""
    if os.getenv('CLAUDE_CODE_OAUTH_TOKEN'):
        return os.getenv('CLAUDE_CODE_OAUTH_TOKEN')
    config_path = os.path.expanduser('~/.claude/config.json')
    if os.path.exists(config_path):
        try:
            import json as _json
            data = _json.load(open(config_path))
            if data.get('oauthToken'):
                return data['oauthToken']
        except Exception:
            pass
    return os.getenv('ANTHROPIC_API_KEY', '')

CLAUDE_AUTH_TOKEN = _get_claude_auth_token()

# ====================================================
# 3. NEWS & SCOUTING (The Yak)
# ====================================================

# GOOGLE CUSTOM SEARCH (Contextual News)
GOOGLE_SEARCH_KEY = os.getenv('GOOGLE_SEARCH_KEY')
GOOGLE_SEARCH_CX = os.getenv('GOOGLE_SEARCH_CX')

# ====================================================
# 4. ALERTS & REPORTING
# ====================================================

# TELEGRAM BOT (Morning Briefing — betting product only)
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

# SLACK (Ops/Work Notes — pipeline alerts, diagnostics, GitHub links)
# Workspace: vibestarters.slack.com | Channel: C0AGBQXRXB3
# Get webhook URL from app settings (A0AD1RWU6TG) → Incoming Webhooks
SLACK_WEBHOOK_URL = os.getenv('SLACK_WEBHOOK_URL', '')

# ====================================================
# 5. GLOBAL SETTINGS (Non-Sensitive)
# ====================================================
CURRENT_SEASON = "2025-2026"
REFRESH_HOURS = 6
BRAND_HEADER = "ludi informatio"

# Feature Flags
ENABLE_TELEGRAM_ALERTS = True
RUN_SEASON_INIT = False
DEBUG_LOG = False  # Set to True for verbose calibration logs

# Phase 7.4: Production flag (controls Telegram sends, debug behavior)
IS_PRODUCTION = os.getenv('IS_PRODUCTION', 'false').lower() == 'true'

# ====================================================
# 5c. SIMULATION SETTINGS (MODULE C)
# ====================================================
# Phase 8.9: Rotation/minutes projection feature flag (True by default)
USE_MINUTES_PROJECTION = os.getenv('USE_MINUTES_PROJECTION', 'true').lower() == 'true'

# Phase 8.18: Team totals scoring modifier feature flag
USE_TEAM_TOTALS_MODIFIER = True

# Phase 8 / Module A: Use Tank01 consensus prop lines as 3rd fallback + line validator.
# When True: (1) single-vendor BDL lines are validated against Tank01 before being
# accepted, and (2) players with zero BDL coverage get a Tank01-only entry at -110/-110.
# Set to False to disable entirely (reverts to pre-Tank01 BDL-only behavior).
USE_TANK01_PROP_FALLBACK = True
# Controls Tank01 consensus cross-check on BDL single-vendor lines.
# Independent of full fallback — allows validation-only or fallback-only modes.
USE_TANK01_LINE_VALIDATION = True

SIM_COUNT = 10000
SIM_VARIANCE = 0.35
SIM_POISSON_THRESHOLD = 3.0
LEAGUE_AVG_TOTAL = 224.5
LEAGUE_AVG_FG_PCT = 0.465
LEAGUE_AVG_TS_PCT = 60.4
FATIGUE_B2B_TAX = 0.965
FATIGUE_RUST_TAX = 0.985
LEAGUE_AVG_PPP = 1.05
MAX_MODIFIER = 1.25
MIN_MODIFIER = 0.75
GAME_TOTAL_LOW_FACTOR = 0.97
SHOT_CREATION_PULLUP_TAX = 0.97

# ====================================================
# 5b. API TIER CONFIGURATION
# ====================================================

# Tier detection (free vs paid)
ODDS_API_TIER = os.getenv('ODDS_API_TIER', 'free')
TANK01_TIER = os.getenv('TANK01_TIER', 'free')
BALLDONTLIE_TIER = os.getenv('BALLDONTLIE_TIER', os.getenv('BDL_TIER', 'goat'))
BDL_TIER = BALLDONTLIE_TIER  # Alias for convenience

# Tier limits (requests/month for odds_api, requests/day for tank01)
TIER_LIMITS = {
    'odds_api': {
        'free': 500,      # per month
        'paid': 20000     # per month
    },
    'tank01': {
        'free': 1000,     # per month
        'paid': 1000      # per DAY (30,000/month)
    },
    'balldontlie': {
        'free': 5,        # per minute
        'allstar': 60,    # per minute
        'goat': 600       # per minute
    }
}

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
    # Required for core functionality
    required_keys = {
        'ODDS_API_KEY': ODDS_API_KEY,
        'TANK01_KEY': TANK01_KEY,
    }
    
    # Optional keys (new paid APIs - warn if missing but don't fail)
    optional_keys = {
        'APISPORTS_KEY': APISPORTS_KEY,
        'BALLDONTLIE_KEY': BALLDONTLIE_KEY,
        'GEMINI_API_KEY': GEMINI_API_KEY,
        'GOOGLE_SEARCH_KEY': GOOGLE_SEARCH_KEY,
        'TELEGRAM_TOKEN': TELEGRAM_TOKEN,
        'PERPLEXITY_API_KEY': PERPLEXITY_API_KEY,
    }

    missing_required = [key for key, value in required_keys.items() if not value]
    missing_optional = [key for key, value in optional_keys.items() if not value]

    if missing_required:
        raise ValueError(f"Missing REQUIRED API keys in .env file: {', '.join(missing_required)}")

    print("✅ Core API keys loaded (ODDS_API_KEY, TANK01_KEY)")

    # Tier validation (use global to modify module-level variables)
    global ODDS_API_TIER, TANK01_TIER, BALLDONTLIE_TIER

    if ODDS_API_TIER not in ['free', 'paid']:
        print(f"⚠️  Invalid ODDS_API_TIER: {ODDS_API_TIER}, defaulting to 'free'")
        ODDS_API_TIER = 'free'

    if TANK01_TIER not in ['free', 'paid']:
        print(f"⚠️  Invalid TANK01_TIER: {TANK01_TIER}, defaulting to 'free'")
        TANK01_TIER = 'free'

    if BALLDONTLIE_TIER not in ['free', 'allstar', 'goat']:
        print(f"⚠️  Invalid BALLDONTLIE_TIER: {BALLDONTLIE_TIER}, defaulting to 'goat'")
        BALLDONTLIE_TIER = 'goat'

    # Display tier info
    print(f"✅ The-Odds-API tier: {ODDS_API_TIER.upper()} "
          f"(limit: {TIER_LIMITS['odds_api'][ODDS_API_TIER]:,} requests/month)")
    print(f"✅ Tank01 tier: {TANK01_TIER.upper()} "
          f"(limit: {TIER_LIMITS['tank01'][TANK01_TIER]:,} requests/{'day' if TANK01_TIER == 'paid' else 'month'})")
    print(f"✅ BallDontLie tier: {BALLDONTLIE_TIER.upper()} "
          f"(limit: {TIER_LIMITS['balldontlie'][BALLDONTLIE_TIER]:,} requests/minute)")

    if missing_optional:
        print(f"⚠️  Optional keys not set: {', '.join(missing_optional)}")
    else:
        print("✅ All optional API keys loaded")

# ====================================================
# SCORING ENVIRONMENT (Phase 8.14)
# ====================================================
SCORING_ENV_PATH = 'cache/scoring_environment.json'
SCORING_ENV_OVER_THRESHOLD = 0.48
SCORING_ENV_DAMPENER = 0.97

@functools.lru_cache(maxsize=1)
def get_scoring_environment():
    try:
        with open(SCORING_ENV_PATH) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {}

# Run validation ONLY when executed directly, not on import
if __name__ == "__main__":
    validate_config()
