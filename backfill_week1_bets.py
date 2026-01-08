# LUDI INFORMATIO | BACKFILL SCRIPT
# ----------------------------------------
# Purpose: Parse Week 1 test results from daily_briefing.txt and insert into bet_tracking system
# Cost: $0 (no API calls, manual parsing)

import re
from datetime import datetime
from utils.bet_logger import get_bet_logger

# Week 1 test game context (from WEEK1_DAY7_COMPLETION_REPORT.md)
WEEK1_GAMES = {
    'CHI_DET': {
        'game_id': 'CHI_DET_20260107',
        'game_date': '2026-01-07',
        'matchup': 'CHI @ DET',
        'home_team': 'DET',
        'away_team': 'CHI',
        'spread': -7.5,  # DET favored
        'total': 221.5,
        'referee_impact': 1.003
    },
    'WAS_PHI': {
        'game_id': 'WAS_PHI_20260107',
        'game_date': '2026-01-07',
        'matchup': 'WAS @ PHI',
        'home_team': 'PHI',
        'away_team': 'WAS',
        'spread': -12.5,  # PHI favored
        'total': 234.5,
        'referee_impact': 1.0
    },
    'TOR_CHA': {
        'game_id': 'TOR_CHA_20260107',
        'game_date': '2026-01-07',
        'matchup': 'TOR @ CHA',
        'home_team': 'CHA',
        'away_team': 'TOR',
        'spread': -2.5,  # CHA favored
        'total': 213.5,
        'referee_impact': 1.0
    }
}

# Team-to-game mapping
TEAM_TO_GAME = {
    'DET': 'CHI_DET',
    'CHI': 'CHI_DET',
    'PHI': 'WAS_PHI',
    'WAS': 'WAS_PHI',
    'CHA': 'TOR_CHA',
    'TOR': 'TOR_CHA'
}

def parse_daily_briefing(file_path='daily_briefing.txt'):
    """
    Parse daily_briefing.txt and extract bet recommendations.

    Returns:
        List of bet dictionaries
    """
    with open(file_path, 'r') as f:
        content = f.read()

    bets = []

    # Regex patterns
    # Pattern 1: 🏀 Duncan Robinson (DET) | OVER 17.5 PTS
    bet_pattern = r'🏀 (.+?) \((\w+)\) \| (OVER|UNDER) ([\d.]+) (\w+)'

    # Pattern 2: Sharp Proj: 10.52 | EV: +43.25% | 1.5u
    proj_pattern = r'Sharp Proj: ([\d.]+) \| EV: \+([\d.]+)% \| ([\d.]+)u'

    # Find all bet lines
    lines = content.split('\n')
    i = 0
    while i < len(lines):
        line = lines[i]

        # Match bet line
        bet_match = re.search(bet_pattern, line)
        if bet_match:
            player_name = bet_match.group(1)
            team = bet_match.group(2)
            bet_side = bet_match.group(3)
            line_value = float(bet_match.group(4))
            stat_category = bet_match.group(5)

            # Look for projection line (should be next line)
            if i + 1 < len(lines):
                proj_line = lines[i + 1]
                proj_match = re.search(proj_pattern, proj_line)

                if proj_match:
                    projection = float(proj_match.group(1))
                    ev = float(proj_match.group(2))
                    units = float(proj_match.group(3))

                    # Get game context
                    game_key = TEAM_TO_GAME.get(team)
                    if not game_key:
                        print(f"⚠️  Unknown team: {team}, skipping bet")
                        i += 2
                        continue

                    game_context = WEEK1_GAMES[game_key]

                    # Determine opponent
                    opponent = game_context['away_team'] if team == game_context['home_team'] else game_context['home_team']

                    # Build bet record
                    bet = {
                        'run_date': '2026-01-07',
                        'game_id': game_context['game_id'],
                        'game_date': game_context['game_date'],
                        'matchup': game_context['matchup'],
                        'home_team': game_context['home_team'],
                        'away_team': game_context['away_team'],
                        'spread': game_context['spread'],
                        'total': game_context['total'],
                        'player_name': player_name,
                        'team': team,
                        'opponent': opponent,
                        'stat_category': stat_category,
                        'bet_side': bet_side,
                        'line': line_value,
                        'odds_over': -110,  # Assume standard juice
                        'odds_under': -110,
                        'projection': projection,
                        'fair_prob': 0.512,  # Approximate (devigged -110/-110)
                        'model_prob': None,  # Not available from briefing
                        'true_edge': None,  # Not available, but EV is
                        'ev': ev,
                        'units': units,
                        'confidence_tier': 'DIAMOND',
                        'note': '[🔥 CORRELATED SGP]',  # All Week 1 bets had this tag
                        'referee_impact': game_context['referee_impact'],
                        'blowout_modifier': None,  # Not available from briefing
                        'run_type': 'test',
                        'bookmaker': 'consensus'
                    }

                    bets.append(bet)
                    print(f"✅ Parsed: {player_name} ({team}) {bet_side} {line_value} {stat_category}")

            i += 2  # Skip next line (projection line)
        else:
            i += 1

    return bets


def main():
    print("="*60)
    print("WEEK 1 BACKFILL SCRIPT")
    print("="*60)

    print("\n📄 Parsing daily_briefing.txt...")
    bets = parse_daily_briefing()

    if not bets:
        print("❌ No bets found in daily_briefing.txt")
        return

    print(f"\n✅ Parsed {len(bets)} bets")

    # Validate bet count
    if len(bets) != 5:
        print(f"⚠️  Warning: Expected 5 bets, found {len(bets)}")

    # Insert into database
    print("\n📊 Inserting into bet_recommendations table...")
    logger = get_bet_logger()

    bet_ids = []
    for bet in bets:
        try:
            bet_id = logger.log_recommendation(bet)
            bet_ids.append(bet_id)
            print(f"✅ Inserted bet #{bet_id}: {bet['player_name']} ({bet['team']}) {bet['bet_side']} {bet['line']} {bet['stat_category']}")
        except Exception as e:
            print(f"❌ Failed to insert bet: {e}")

    # Calculate summary
    total_units = sum(b['units'] for b in bets)
    print(f"\n📊 Summary:")
    print(f"   Bets: {len(bets)}")
    print(f"   Total Units: {total_units:.1f}u")
    print(f"   API Cost: $0.1125 (Week 1 test)")
    print(f"   Players: {len(set(b['player_name'] for b in bets))}")

    # Insert daily summary
    print("\n📊 Creating daily summary...")
    summary_data = {
        'run_date': '2026-01-07',
        'total_bets': len(bets),
        'total_units': total_units,
        'pending': len(bets),
        'avg_edge': None,  # Not available from briefing
        'avg_ev': sum(b['ev'] for b in bets) / len(bets),
        'api_cost': 0.1125,
        'api_credits_used': 75,
        'games_analyzed': 3,
        'players_simulated': 19,
        'runtime_seconds': 45.0
    }
    logger.calculate_daily_summary('2026-01-07', summary_data)
    print("✅ Daily summary created")

    print("\n" + "="*60)
    print("✅ BACKFILL COMPLETE")
    print("="*60)

    print("\n🔍 Verification queries:")
    print("   sqlite3 ludi.db \"SELECT COUNT(*) FROM bet_recommendations WHERE run_type='test';\"")
    print("   sqlite3 ludi.db \"SELECT player_name, stat_category, line FROM bet_recommendations WHERE run_date='2026-01-07';\"")
    print("   sqlite3 ludi.db \"SELECT * FROM bet_daily_summaries WHERE run_date='2026-01-07';\"")


if __name__ == "__main__":
    main()
