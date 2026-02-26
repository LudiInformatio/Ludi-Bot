import os
import re
import time
from collections import defaultdict
from typing import Any

from utils.claude_client import get_claude_analysis, HAIKU_MODEL, SONNET_MODEL
from utils.claude_prompts import (
    ASK_LUDI_INTENT_SYSTEM,
    ASK_LUDI_INTENT_PROMPT,
    ASK_LUDI_NARRATIVE_SYSTEM,
)
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
        temperature=0.1,
        max_tokens=200,
        call_type="ask_ludi_intent",
    )
    if result:
        result = result.strip().lower()
        valid_intents = ["injuries", "edges", "trends", "schedule", "recap", "standings", "free_text"]
        for intent in valid_intents:
            if intent in result:
                return intent
    return "free_text"


def get_data_for_intent(intent: str, user_message: str = "") -> str:
    """Fetch data from database based on classified intent."""
    if intent == "injuries":
        injuries = ask_ludi_db.get_injuries()
        return format_injuries(injuries)
    elif intent == "edges":
        edges = ask_ludi_db.get_edges()
        return format_edges(edges)
    elif intent == "trends":
        player_match = re.search(r"(?:about|for|on)\s+([A-Za-z]+(?:\s+[A-Za-z]+)*)", user_message, re.IGNORECASE)
        player_name = player_match.group(1) if player_match else None
        trends = ask_ludi_db.get_trends(player_name)
        return format_trends(trends, player_name)
    elif intent == "schedule":
        schedule = ask_ludi_db.get_schedule()
        return format_schedule(schedule)
    elif intent == "recap":
        recap = ask_ludi_db.get_recap()
        return format_recap(recap)
    elif intent == "standings":
        standings = ask_ludi_db.get_standings()
        return format_standings(standings)
    else:
        return ask_ludi_db.free_text_query(user_message)


def format_injuries(injuries: list[dict[str, Any]]) -> str:
    """Format injuries data for display."""
    if not injuries:
        return "No active injuries on record."
    lines = []
    for inj in injuries[:15]:
        days = f"{inj['days_out']}d" if inj.get('days_out') else "?"
        lines.append(f"• {inj['player_name']} ({inj['team_abbreviation']}) — {inj['status']} ({days})")
    return "**Current Injuries:**\n" + "\n".join(lines)


def format_edges(edges: list[dict[str, Any]]) -> str:
    """Format betting edges for display."""
    if not edges:
        return "No positive EV plays found for today."
    lines = []
    for edge in edges[:10]:
        pct = f"{edge['true_edge']:.1f}%"
        line = f"• {edge['player_name']} {edge['bet_side']} {edge['line']} {edge['stat_category']} @ {edge['matchup']}\n  Edge: {pct} | Proj: {edge['projection']}"
        lines.append(line)
    return "**Today's Top Edges:**\n" + "\n".join(lines)


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


def format_schedule(schedule: list[dict[str, Any]]) -> str:
    """Format schedule data for display."""
    if not schedule:
        return "No games scheduled for today."
    lines = ["**Today's Schedule:**"]
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


def format_standings(standings: list[dict[str, Any]]) -> str:
    """Format standings data for display."""
    if not standings:
        return "No standings data available."
    lines = ["**Current Standings:**"]
    for s in standings[:10]:
        record = f"{s['wins']}-{s['losses']}"
        lines.append(f"• {s['team_abbrev']}: {record} ({s['win_pct']:.1%})")
    return "\n".join(lines)


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


async def generate_narrative(user_message: str, data: str) -> str:
    """Generate natural language narrative using Sonnet model."""
    prompt = f"""User question: {user_message}

Data from database:
{data}

Provide a helpful, concise answer based on the data above."""
    result = get_claude_analysis(
        prompt=prompt,
        system_prompt=ASK_LUDI_NARRATIVE_SYSTEM,
        model=SONNET_MODEL,
        temperature=0.2,
        max_tokens=600,
        call_type="ask_ludi_narrative",
    )
    if result:
        return result.strip()
    return data


async def handle_message(update, context) -> None:
    """Handle incoming messages from users."""
    if not update.message or not update.message.text:
        return
    
    user_id = update.effective_user.id
    user_message = update.message.text.strip()
    
    if not check_rate_limit(user_id):
        await update.message.reply_text(
            "Rate limit exceeded. Please wait 60 seconds before sending another message."
        )
        return
    
    intent = classify_intent(user_message)
    
    try:
        data = get_data_for_intent(intent, user_message)
        if intent == "free_text" and "?" not in user_message:
            response = data
        else:
            response = await generate_narrative(user_message, data)
    except Exception as e:
        response = format_fallback_data(intent)
    
    await update.message.reply_text(response)
