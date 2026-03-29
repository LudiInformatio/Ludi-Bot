import logging
import re
import sqlite3
import time
from collections import defaultdict
from typing import Any

logger = logging.getLogger(__name__)

from database import DB_PATH
from utils.claude_client import get_claude_analysis, HAIKU_MODEL, SONNET_MODEL
from utils.claude_prompts import (
    ASK_LUDI_INTENT_SYSTEM,
    ASK_LUDI_INTENT_PROMPT,
    ASK_LUDI_NARRATIVE_SYSTEM,
    ROSTER_RULES,
)
from utils.time_utils import get_est_now, format_time_context_note, get_smart_target_date
from bots import ask_ludi_db


RATE_LIMIT_WINDOW = 60
RATE_LIMIT_MAX = 10

_user_rate_limits: dict[int, list[float]] = defaultdict(list)


def check_rate_limit(user_id: int) -> bool:
    """Check if user is within rate limit. Returns True if allowed, False if rate limited."""
    now = time.time()
    user_requests = _user_rate_limits[user_id]
    user_requests[:] = [t for t in user_requests if now - t < RATE_LIMIT_WINDOW]
    if len(user_requests) >= RATE_LIMIT_MAX:
        return False
    user_requests.append(now)
    return True


def classify_intent(user_message: str) -> str:
    """Classify user intent using Haiku model."""
    prompt = ASK_LUDI_INTENT_PROMPT.format(user_message=user_message)
    result = get_claude_analysis(
        prompt=prompt,
        system_prompt=ASK_LUDI_INTENT_SYSTEM,
        model=HAIKU_MODEL,
        temperature=0.0,
        max_tokens=200,
        call_type="ask_ludi_intent",
    )
    if result:
        result = result.strip().lower()
        valid_intents = ["injuries", "standings", "schedule", "recap", "edges", "trends", "free_text"]
        for intent in valid_intents:
            if intent in result:
                return intent
    return "free_text"


def _format_timestamp_est(ts_str: str | None) -> str | None:
    """Convert ISO timestamp string to readable EST time like '5:18 PM'."""
    if not ts_str:
        return None
    try:
        import pytz
        from datetime import datetime
        EST = pytz.timezone('US/Eastern')
        # Handle both 'YYYY-MM-DD HH:MM:SS' and ISO format
        for fmt in ('%Y-%m-%dT%H:%M:%S.%f', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%d %H:%M:%S.%f', '%Y-%m-%d %H:%M:%S'):
            try:
                dt = datetime.strptime(ts_str, fmt)
                dt_est = dt.replace(tzinfo=pytz.utc).astimezone(EST)
                return dt_est.strftime('%-I:%M %p EST')
            except ValueError:
                continue
        return None
    except Exception as e:
        print(f"[WARNING] _format_timestamp_est failed: {e}")
        return None


def get_data_for_intent(intent: str, user_message: str = "") -> tuple[str, dict]:
    """Fetch data from database based on classified intent.

    Returns (formatted_data_str, freshness_meta_dict) tuple.
    Meta is used by generate_narrative() for time-aware framing.
    """
    meta = ask_ludi_db.get_freshness_meta()

    if intent == "injuries":
        injuries = ask_ludi_db.get_injuries()
        return format_injuries(injuries, meta), meta
    elif intent == "edges":
        edges = ask_ludi_db.get_edges()
        return format_edges(edges, meta), meta
    elif intent == "trends":
        player_match = re.search(r"(?:about|for|on)\s+([A-Za-z]+(?:\s+[A-Za-z]+)*)", user_message, re.IGNORECASE)
        player_name = player_match.group(1) if player_match else None
        trends = ask_ludi_db.get_trends(player_name)
        return format_trends(trends, player_name), meta
    elif intent == "schedule":
        schedule = ask_ludi_db.get_schedule()
        return format_schedule(schedule, meta), meta
    elif intent == "recap":
        recap = ask_ludi_db.get_recap()
        return format_recap(recap), meta
    elif intent == "standings":
        standings = ask_ludi_db.get_standings()
        return format_standings(standings, meta), meta
    else:
        return ask_ludi_db.free_text_query(user_message), meta


def format_injuries(injuries: list[dict[str, Any]], meta: dict | None = None) -> str:
    """Format injuries data for display with freshness footer."""
    if not injuries:
        return "No active injuries on record."
    lines = []
    for inj in injuries[:15]:
        days = f"{inj['days_out']}d" if inj.get('days_out') else "?"
        lines.append(f"• {inj['player_name']} ({inj['team_abbreviation']}) — {inj['status']} ({days})")
    result = "**Current Injuries:**\n" + "\n".join(lines)
    # Freshness footer
    if meta:
        ts = _format_timestamp_est(meta.get('injuries'))
        if ts:
            result += f"\n_Injury data as of {ts}_"
    return result


def format_edges(edges: list[dict[str, Any]], meta: dict | None = None) -> str:
    """Format betting edges for display. Time-aware: 3 states based on hour."""
    now = get_est_now()

    # State 1: Before pipeline runs (before 11 AM)
    if not edges and now.hour < 11:
        return "Today's edges will be available after the **10 AM pipeline run**. Check back after 11 AM."

    # State 2: Normal daytime or evening with no edges
    if not edges:
        return "No positive EV plays found for today's slate."

    lines = []

    # State 3: After 9 PM — show today's final edges + tomorrow note
    if now.hour >= 21:
        lines.append("**Today's Edges (final):**")
        for edge in edges[:10]:
            pct = f"{edge['true_edge']:.1f}%"
            proj = f"{edge['projection']:.1f}" if edge.get('projection') is not None else 'N/A'
            line = f"• {edge['player_name']} {edge['bet_side']} {edge['line']} {edge['stat_category']} @ {edge['matchup']}\n  Edge: {pct} | Proj: {proj}"
            lines.append(line)
        # Tomorrow note — slate context will have tomorrow's games if available
        target = get_smart_target_date()
        lines.append(f"\n_Tomorrow's slate ({target}) loading. Ask 'What games are on tomorrow?' for early matchup preview._")
    else:
        # Normal daytime view
        for edge in edges[:10]:
            pct = f"{edge['true_edge']:.1f}%"
            proj = f"{edge['projection']:.1f}" if edge.get('projection') is not None else 'N/A'
            line = f"• {edge['player_name']} {edge['bet_side']} {edge['line']} {edge['stat_category']} @ {edge['matchup']}\n  Edge: {pct} | Proj: {proj}"
            lines.append(line)

    result = "**Today's Top Edges:**\n" + "\n".join(lines) if lines[0] != "**Today's Edges (final):**" else "\n".join(lines)

    # Freshness footer
    if meta:
        ts = _format_timestamp_est(meta.get('edges'))
        if ts:
            result += f"\n_Pipeline run: {ts}_"
    return result


def format_trends(trends: list[dict[str, Any]], player_name: str | None = None) -> str:
    """Format trends data for display."""
    if not trends:
        return "No recent trend data available."
    if player_name:
        lines = [f"**Recent Games for {player_name}:**"]
        for t in trends[:5]:
            pts = t.get('pts', 0) or 0
            reb = t.get('reb', 0) or 0
            ast = t.get('ast', 0) or 0
            date = t.get('game_date', '')[:10]
            lines.append(f"• {date}: {pts} PTS, {reb} REB, {ast} AST")
    else:
        lines = ["**Recent League Trends:**"]
        for t in trends[:10]:
            pts = t.get('pts', 0) or 0
            lines.append(f"• {t['player_name']}: {pts} pts")
    return "\n".join(lines)


def format_schedule(schedule: list[dict[str, Any]], meta: dict | None = None) -> str:
    """Format schedule data for display with smart date context."""
    target_date = meta.get('target_date') if meta else get_smart_target_date()

    if not schedule:
        # Check nba_calendar for expected count before saying "no games"
        expected = ask_ludi_db.get_expected_game_count(target_date)
        if expected > 0:
            return f"**{target_date}:** {expected} games expected — matchups available after 3 AM sync."
        return f"No games scheduled for {target_date}."

    label = "Today" if target_date == ask_ludi_db.get_est_today() else target_date
    lines = [f"**{label}'s Schedule:**"]
    for game in schedule:
        lines.append(f"• {game['away_team']} @ {game['home_team']}")
    return "\n".join(lines)


def format_recap(recap: list[dict[str, Any]]) -> str:
    """Format recap data for display."""
    if not recap:
        return "No game results from yesterday."
    lines = ["**Yesterday's Results:**"]
    for game in recap:
        away = game.get('away_team', '')
        home = game.get('home_team', '')
        away_score = game.get('away_score', 0) or 0
        home_score = game.get('home_score', 0) or 0
        lines.append(f"• {away} {away_score} @ {home} {home_score}")
    return "\n".join(lines)


def format_standings(standings: list[dict[str, Any]], meta: dict | None = None) -> str:
    """Format standings data for display with freshness footer."""
    if not standings:
        return "No standings data available."
    lines = ["**Current Standings:**"]
    for s in standings[:10]:
        record = f"{s['wins']}-{s['losses']}"
        lines.append(f"• {s['team_abbrev']}: {record} ({s['win_pct']:.1%})")
    result = "\n".join(lines)
    # Freshness footer (standings update daily)
    if meta:
        ts = _format_timestamp_est(meta.get('standings'))
        if ts:
            result += f"\n_Standings as of {ts}_"
    return result


def format_fallback_data(intent: str) -> str:
    """Provide graceful degradation when data fetch fails."""
    fallback_messages = {
        "injuries": "I couldn't fetch the latest injuries. Try again shortly.",
        "edges": "I couldn't fetch today's edges. The pipeline may not have run yet.",
        "trends": "I couldn't fetch trend data. Please try again.",
        "schedule": "I couldn't fetch the schedule. Please try again.",
        "recap": "I couldn't fetch yesterday's results. Please try again.",
        "standings": "I couldn't fetch the standings. Please try again.",
        "free_text": "I'm having trouble accessing the database. Please try again.",
    }
    return fallback_messages.get(intent, "Something went wrong. Please try again.")


async def generate_narrative(
    user_message: str,
    data: str,
    slate_context: str = "",
    meta: dict | None = None,
) -> str:
    """Generate natural language narrative using Sonnet model.

    Injects slate context (BERT Pattern 2: text_a=reference, text_b=answer data)
    and time context so Sonnet can frame confidence appropriately.
    """
    time_ctx = format_time_context_note()

    prompt = f"""=== TONIGHT'S SLATE (reference context) ===
{slate_context}

=== QUERY DATA (answer from this) ===
{data}

=== TIME CONTEXT ===
{time_ctx}

=== USER QUESTION ===
{user_message}"""

    try:
        result = get_claude_analysis(
            prompt=prompt,
            system_prompt=f"{ROSTER_RULES}\n\n{ASK_LUDI_NARRATIVE_SYSTEM}",
            model=SONNET_MODEL,
            temperature=0.3,
            max_tokens=600,
            call_type="ask_ludi_narrative",
        )
        if result:
            return result.strip()
    except Exception as e:
        print(f"[WARNING] generate_narrative Sonnet call failed: {e}")
    return data


async def handle_message(update, context) -> None:
    """Handle incoming messages from users."""
    if not update.message or not update.message.text:
        return

    user_id = update.effective_user.id
    user_message = update.message.text.strip()
    _req_start = time.time()  # for interaction logging

    if not check_rate_limit(user_id):
        await update.message.reply_text(
            "Rate limit exceeded. Please wait 60 seconds before sending another message."
        )
        return

    intent = classify_intent(user_message)

    try:
        data, meta = get_data_for_intent(intent, user_message)
        # Fetch slate context once per message (cached — negligible overhead)
        slate_context = ask_ludi_db.build_slate_context()

        if intent == "free_text" and "?" not in user_message:
            response = data
        else:
            response = await generate_narrative(user_message, data, slate_context, meta)
    except Exception:
        response = format_fallback_data(intent)

    MAX_TG = 4096
    if len(response) <= MAX_TG:
        await update.message.reply_text(response)
    else:
        for i in range(0, len(response), MAX_TG):
            await update.message.reply_text(response[i:i + MAX_TG])

    # Log interaction for training data — fire-and-forget, never blocks the response
    try:
        _resp_ms = int((time.time() - _req_start) * 1000)
        with sqlite3.connect(DB_PATH) as _log_conn:
            _log_conn.execute(
                "INSERT INTO ask_ludi_interactions "
                "(query_text, intent, response_text, response_time_ms, session_id) "
                "VALUES (?, ?, ?, ?, ?)",
                (user_message, intent, response[:2000], _resp_ms, str(user_id))
            )
    except Exception as _e:
        logger.warning(f"[ask_ludi] interaction log failed: {_e}")
