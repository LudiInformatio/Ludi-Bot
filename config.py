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
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ludi.db")

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

# SPORTSDATA.IO (Box score enrichment: started, DK/FD fantasy pts, home/away, doubles)
# Source: https://discoverylab.sportsdata.io/
# Pricing: Free (100 calls/day) — Fantasy API path
SPORTSDATA_API_KEY = os.getenv('SPORTSDATA_API_KEY')
SPORTSDATA_TIER = os.getenv('SPORTSDATA_TIER', 'free')
USE_SPORTSDATA = bool(SPORTSDATA_API_KEY)

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

# TELEGRAM BOT 2 — Solomon (PM briefs, session debriefs, settlement summaries)
TELEGRAM_TOKEN_SOLOMON = os.getenv('TELEGRAM_TOKEN_SOLOMON')
TELEGRAM_CHAT_ID_SOLOMON = os.getenv('TELEGRAM_CHAT_ID_SOLOMON')

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

# ====================================================
# MODIFIER FLAGS (Subtractive Optimization)
# ====================================================
# All 38 flags default True — no behavior change at ship.
# Set individual flags to False to isolate modifier contributions.
# Override via env: MODIFIER_FLAGS_JSON='{"pace": false, "referee": false}'

MODIFIER_FLAGS = {
    # Module C
    'pace': True,
    'referee': True,
    'fatigue': True,
    'team_defense': True,
    'shot_quality': True,
    'drives_boost': True,
    'return_ramp': True,
    'season_blend': True,
    'conditional_baseline': True,
    'empirical_role': True,
    # Module E
    'matchup_scheme': True,
    'secondary_playtype': True,
    'dvp_modulator': True,
    'synergy_efficiency': True,
    'game_total': True,
    'team_totals': True,
    'scoring_env': True,
    'pbp_shot_quality': True,
    'ft_touch': True,
    'shot_creation': True,
    'shot_difficulty': True,
    'opponent_context': True,
    'fatigue_e': True,
    'clutch_boost': True,
    'speed_fatigue': True,
    'touches_context': True,
    'leverage_context': True,
    'ppp_efficiency': True,
    'defensive_diff': True,
    'drives_ast': True,
    'weak_link_boost': True,
    'westbrook_rule': True,
    # Module F
    'blowout_tax': True,
    'wowy_edge_penalty': True,
    'edge_dampening': True,
    'stat_calibration': True,
    'rmse_sizing': True,
    'combo_correlation': True,
    'stat_kelly_gate': True,
    'steam_move': True,        # T5d: flag STEAM_MOVE when Pinnacle line moves >= threshold
    'sniper_b2b_exempt': True, # SNIPER_ELITE players bypass B2B fatigue penalty
    # Module X
    'vegas_guardrail': True,
    # main.py get_active_roster()
    'recency_weighting': True,
}

# Env override: allows per-flag toggling without code changes
_FLAG_OVERRIDES = json.loads(os.getenv('MODIFIER_FLAGS_JSON', '{}'))
MODIFIER_FLAGS = {**MODIFIER_FLAGS, **_FLAG_OVERRIDES}

# ====================================================
# RECENCY WEIGHTING (Projection Accuracy Sprint 1, Phase 2)
# ====================================================
# Exponential decay weights for get_active_roster() L25 game window.
# Half-life = 7 games (most-recent game = index 0, weight ~0.1029).
# Pre-normalized so sum(RECENCY_WEIGHTS_L25) ≈ 1.0.
# When n < 25, slice w[:n] and re-normalize: w / sum(w).
# N-gate: use flat average when player has < RECENCY_MIN_GAMES_FOR_WEIGHTING games
# (weighting HURTS on small samples: +8.64% RMSE for N=3-7, Lena-verified N=969).
RECENCY_WEIGHTS_L25 = [
    0.102935, 0.093231, 0.084441, 0.076480, 0.069270,
    0.062740, 0.056825, 0.051468, 0.046615, 0.042221,
    0.038240, 0.034635, 0.031370, 0.028412, 0.025734,
    0.023308, 0.021110, 0.019120, 0.017318, 0.015685,
    0.014206, 0.012867, 0.011654, 0.010555, 0.009560
]
RECENCY_MIN_GAMES_FOR_WEIGHTING = 15

# Run validation ONLY when executed directly, not on import
if __name__ == "__main__":
    validate_config()
