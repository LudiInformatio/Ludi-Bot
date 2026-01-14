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
