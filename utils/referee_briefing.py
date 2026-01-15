#!/usr/bin/env python3
"""
LUDI INFORMATIO | REFEREE BRIEFING UTILITY
Generates "Whistle Watch" reports for daily morning briefs

Usage:
    from utils.referee_briefing import generate_whistle_watch
    report = generate_whistle_watch(games)
"""

from datetime import datetime
from typing import Dict, List


def generate_whistle_watch(zebras, games: List[Dict]) -> str:
    """
    Generate the "Whistle Watch" section for morning briefs.
    
    Args:
        zebras: LudiRefEngine instance (Module G)
        games: List of game dicts from Module A
        
    Returns:
        Formatted markdown string with referee intelligence
    """
    
    if not games:
        return "\n🦓 REFEREE INTELLIGENCE\n═══════════════════════════════════════\n   No games scheduled today.\n"
    
    lines = []
    lines.append("\n🦓 REFEREE INTELLIGENCE")
    lines.append("═══════════════════════════════════════\n")
    
    for game in games:
        home_team = game.get('home', 'N/A')
        away_team = game.get('away', 'N/A')
        
        # Get referee crew data from Module G
        home_abbr = zebras._resolve_team_abbr(home_team)
        ref_data = zebras.get_game_impact(home_abbr)
        
        # Extract crew and impact
        crew = ref_data.get('crew', [])
        pace_impact = ref_data.get('pace_impact', 1.0)
        whistle_impact = ref_data.get('whistle_impact', 1.0)
        confidence = ref_data.get('confidence', 0.0)
        
        # Format time
        start_time = game.get('start_time')
        if start_time and hasattr(start_time, 'strftime'):
            time_str = start_time.strftime('%I:%M %p ET')
        else:
            time_str = "TBD"
        
        # Game header
        lines.append(f"🏀 {away_team} @ {home_team} | {time_str}")
        
        # Crew
        if crew:
            crew_chief = crew[0] if crew else "Unknown"
            crew_str = f"{crew_chief} (C)"
            if len(crew) > 1:
                crew_str += f", {', '.join(crew[1:])}"
            lines.append(f"   Crew: {crew_str}")
        else:
            lines.append(f"   Crew: Not yet assigned")
        
        # Impact metrics
        pace_label = _get_pace_label(pace_impact)
        whistle_label = _get_whistle_label(whistle_impact)
        
        lines.append(f"   📊 Impact: Pace {pace_impact}x {pace_label} | Whistle {whistle_impact}x {whistle_label}")
        
        # Confidence
        conf_icon = "✅" if confidence >= 0.67 else "⚠️"
        conf_pct = int(confidence * 100)
        lines.append(f"   {conf_icon} Confidence: {conf_pct}% ({'All refs tracked' if confidence == 1.0 else f'{int(confidence * len(crew))}/{len(crew)} known'})")
        
        # Insight
        insight = _generate_insight(pace_impact, whistle_impact, confidence)
        lines.append(f"   💡 Insight: {insight}")
        lines.append("")  # Blank line between games
    
    return "\n".join(lines)


def _get_pace_label(pace_impact: float) -> str:
    """Return a label for pace impact."""
    if pace_impact >= 1.02:
        return "(FAST)"
    elif pace_impact <= 0.98:
        return "(SLOW)"
    else:
        return ""


def _get_whistle_label(whistle_impact: float) -> str:
    """Return a label for whistle impact."""
    if whistle_impact >= 1.03:
        return "(STRICT)"
    elif whistle_impact <= 0.97:
        return "(LENIENT)"
    else:
        return ""


def _generate_insight(pace: float, whistle: float, confidence: float) -> str:
    """
    Generate a one-line insight about the crew's expected impact.
    
    Args:
        pace: Pace impact multiplier
        whistle: Whistle impact multiplier
        confidence: Data confidence (0.0-1.0)
    """
    
    if confidence < 0.5:
        return "Low confidence - too many unknown refs"
    
    # High whistle + High pace = OVER potential
    if whistle >= 1.02 and pace >= 1.01:
        return "Heavy whistle + fast pace suggests OVER potential"
    
    # Low whistle + Slow pace = UNDER potential
    if whistle <= 0.98 and pace <= 0.99:
        return "Low whistle + slow pace favors UNDER"
    
    # Heavy whistle = More FTA
    if whistle >= 1.03:
        return "Strict crew - expect high FTA and fouls"
    
    # Lenient whistle
    if whistle <= 0.97:
        return "Lenient crew - less FTA, more flow"
    
    # Fast pace
    if pace >= 1.02:
        return "Fast-paced crew - high possessions"
    
    # Slow pace
    if pace <= 0.98:
        return "Slow-paced crew - grind-it-out game"
    
    # Neutral
    return "Neutral crew, no significant edge"


def generate_compact_whistle_watch(zebras, games: List[Dict]) -> str:
    """
    Generate a compact version for Telegram (character limit friendly).
    
    Args:
        zebras: LudiRefEngine instance
        games: List of game dicts
        
    Returns:
        Compact formatted string
    """
    
    if not games:
        return "🦓 No referee assignments yet\n"
    
    lines = ["🦓 REFEREE WATCH\n"]
    
    for game in games:
        home = game.get('home', 'N/A')
        away = game.get('away', 'N/A')
        
        home_abbr = zebras._resolve_team_abbr(home)
        ref_data = zebras.get_game_impact(home_abbr)
        
        crew = ref_data.get('crew', [])
        pace = ref_data.get('pace_impact', 1.0)
        whistle = ref_data.get('whistle_impact', 1.0)
        
        crew_chief = crew[0] if crew else "TBD"
        
        # Compact line
        lines.append(f"{away}@{home}: {crew_chief} | P:{pace:.2f}x W:{whistle:.2f}x")
    
    return "\n".join(lines)


if __name__ == "__main__":
    # Test the utility
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    from module_g import LudiRefEngine
    
    zebras = LudiRefEngine()
    zebras.build_ref_database()
    
    # Mock game data
    test_games = [
        {
            'home': 'Orlando',
            'away': 'Detroit',
            'start_time': datetime.now()
        },
        {
            'home': 'Miami',
            'away': 'Boston',
            'start_time': datetime.now()
        }
    ]
    
    print(generate_whistle_watch(zebras, test_games))
    print("\n" + "="*50 + "\n")
    print(generate_compact_whistle_watch(zebras, test_games))
