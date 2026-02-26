"""
LUDI INFORMATIO | TIME UTILITIES
---------------------------------
All datetime operations must use EST (US/Eastern).
This ensures consistency between local (CLT, NC) and GitHub Actions (UTC).
"""

from datetime import datetime, timedelta
import pytz

# Eastern Standard Time
EST = pytz.timezone('US/Eastern')


def get_est_now() -> datetime:
    """Get current datetime in EST."""
    return datetime.now(EST)


def get_est_today() -> str:
    """Get today's date string in EST (YYYY-MM-DD)."""
    return get_est_now().strftime('%Y-%m-%d')


def get_est_yesterday() -> str:
    """Get yesterday's date string in EST (YYYY-MM-DD)."""
    return (get_est_now() - timedelta(days=1)).strftime('%Y-%m-%d')


def format_est_date(fmt: str = '%Y-%m-%d') -> str:
    """Get current date/time in EST with custom format."""
    return get_est_now().strftime(fmt)


def parse_game_date(date_str: str) -> datetime:
    """Parse a game date string to EST datetime."""
    dt = datetime.strptime(date_str, '%Y-%m-%d')
    return EST.localize(dt)


def get_time_context() -> dict:
    """Return current time-awareness mode for NBA game-day analysis (Ludi-Lite pattern).

    Modes drive Claude prompt confidence framing:
      EARLY_LOOK  (before noon ET)  — designations still evolving
      AFTERNOON   (noon–5 PM ET)    — watch for GTD updates
      PRE_GAME    (5–7 PM ET)       — lineups largely confirmed; evening lock window
      LOCK_TIME   (after 7 PM ET)   — games in progress; data is final

    Future: wire into Telegram bot + web app for real-time confidence display.
    """
    now = get_est_now()
    h = now.hour

    if h < 12:
        return {
            "mode": "EARLY_LOOK",
            "confidence": "LOW",
            "note": "Injury designations still evolving — verify closer to tipoff"
        }
    elif h < 17:
        return {
            "mode": "AFTERNOON",
            "confidence": "MEDIUM",
            "note": "Watch for GTD updates through 5 PM ET"
        }
    elif h < 19:
        return {
            "mode": "PRE_GAME",
            "confidence": "HIGH",
            "note": "Lineups largely confirmed — evening lock window"
        }
    else:
        return {
            "mode": "LOCK_TIME",
            "confidence": "HIGHEST",
            "note": "Games in progress — treat all data as final"
        }


def format_time_context_note(ctx: dict = None) -> str:
    """Return a single formatted string for template injection."""
    if ctx is None:
        ctx = get_time_context()
    return f"{ctx['mode']} ({ctx['confidence']}) | {ctx['note']}"


def get_est_tomorrow() -> str:
    """Get tomorrow's date string in EST (YYYY-MM-DD)."""
    return (get_est_now() + timedelta(days=1)).strftime('%Y-%m-%d')


def get_smart_target_date() -> str:
    """Return the most useful date for forward-looking queries.

    Before 9 PM EST: today's date (current slate)
    At/after 9 PM EST: tomorrow's date (early research window)

    Mirrors module_a.py Gatekeeper 9 PM cutoff pattern (module_a.py:99-106).
    """
    now = get_est_now()
    if now.hour >= 21:
        return (now + timedelta(days=1)).strftime('%Y-%m-%d')
    return now.strftime('%Y-%m-%d')
