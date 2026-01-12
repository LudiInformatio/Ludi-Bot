#!/usr/bin/env python
"""
backtest_archetypes.py - Phase B: Archetype Matchup Validation

Tests Module E calibration logic against historical data to verify:
1. Slasher vs Hackers → More FTA in actual games?
2. Stretch Big vs Paint Pack → More 3PM in actual games?
3. Blowout Tax → Reduced minutes in blowout games?

Database: ludi.db (24,770 records through Jan 10)
Run: ./venv/bin/python backtest_archetypes.py
Full season: ./venv/bin/python backtest_archetypes.py --full-season
"""

import sqlite3
import argparse
from datetime import datetime
from module_e import LudiCalibrator

def query_historical_matchups(archetype_condition, def_style, min_games=5, days=60):
    """
    Query database for historical matchups matching archetype + defense criteria.
    
    Args:
        archetype_condition: SQL WHERE clause for archetype (e.g., "pts > 22 AND fg3m < 2")
        def_style: Defense team abbreviation (e.g., 'IND' for Hackers)
        min_games: Minimum games to include player
        days: Number of days to look back (default: 60)
    
    Returns:
        List of (player_name, avg_stat, game_count)
    """
    conn = sqlite3.connect('ludi.db')
    c = conn.cursor()
    
    # Query: Find players matching archetype playing against specific defense
    query = f"""
    SELECT 
        p.player_name,
        AVG(p.fta) as avg_fta,
        AVG(p.fg3m) as avg_3pm,
        AVG(p.minutes) as avg_min,
        AVG(p.pts) as avg_pts,
        COUNT(*) as game_count
    FROM player_game_logs p
    JOIN games g ON p.game_id = g.game_id
    WHERE (g.home_team = ? OR g.away_team = ?)
    AND p.team_abbreviation != ?  -- Playing AGAINST this team
    AND {archetype_condition}
    AND p.game_date >= date('now', '-{days} days')
    GROUP BY p.player_name
    HAVING COUNT(*) >= ?
    ORDER BY game_count DESC
    LIMIT 10
    """
    
    c.execute(query, (def_style, def_style, def_style, min_games))
    results = c.fetchall()
    conn.close()
    
    return results

def test_slasher_vs_hackers(days=60):
    """
    Test Case 1: Slasher vs Hackers Defense
    
    Hypothesis: Slashers draw more fouls vs foul-prone defenses (IND, CHA, POR)
    Expected: avg_fta vs Hackers > avg_fta vs other teams
    """
    print("\n" + "="*60)
    print("📋 TEST 1: Slasher vs Hackers")
    print("="*60)
    
    # Slasher condition: High scoring, low 3PM
    slasher_condition = "pts > 20 AND fg3m < 2.0 AND minutes > 30"
    
    # Hackers teams: IND, CHA, POR
    hackers = ['IND', 'CHA', 'POR']
    
    print("\n🔍 Criteria: Slashers (PTS > 20, 3PM < 2.0) vs Hackers (IND/CHA/POR)")
    
    for team in hackers:
        print(f"\n📊 {team} Defense:")
        results = query_historical_matchups(slasher_condition, team, min_games=2, days=days)
        
        if not results:
            print("   ⚠️  No data found")
            continue
            
        for row in results[:3]:  # Top 3 players
            player, fta, tpm, mins, pts, games = row
            print(f"   {player:<20} | FTA: {fta:.1f} | Games: {games}")
    
    print("\n✅ Visual review: Are FTA numbers elevated vs Hackers?")
    print("   (Compare to player's season average for validation)")

def test_stretch_big_vs_paint_pack(days=60):
    """
    Test Case 2: Stretch Big vs Paint Pack Defense
    
    Hypothesis: Stretch bigs shoot more 3s when paint is packed
    Expected: avg_3pm vs Paint Pack > avg_3pm vs other teams
    """
    print("\n" + "="*60)
    print("📋 TEST 2: Stretch Big vs Paint Pack")
    print("="*60)
    
    # Stretch Big condition: Good rebounding + 3PM
    stretch_condition = "reb > 6.0 AND fg3m > 1.5 AND minutes > 25"
    
    # Paint Pack teams: OKC, BOS, DET, MIN, LAL
    paint_pack = ['OKC', 'BOS', 'DET', 'MIN', 'LAL']
    
    print("\n🔍 Criteria: Stretch Bigs (REB > 6, 3PM > 1.5) vs Paint Pack")
    
    for team in paint_pack[:3]:  # Just 3 teams for brevity
        print(f"\n📊 {team} Defense:")
        results = query_historical_matchups(stretch_condition, team, min_games=2, days=days)
        
        if not results:
            print("   ⚠️  No data found")
            continue
            
        for row in results[:3]:
            player, fta, tpm, mins, pts, games = row
            print(f"   {player:<20} | 3PM: {tpm:.1f} | Games: {games}")
    
    print("\n✅ Visual review: Are 3PM numbers elevated vs Paint Pack?")

def test_blowout_tax(days=60):
    """
    Test Case 3: Blowout Tax
    
    Hypothesis: Starters play fewer minutes in blowout games
    Expected: avg_min in 15+ spread games < avg_min in close games
    """
    print("\n" + "="*60)
    print("📋 TEST 3: Blowout Tax")
    print("="*60)
    
    conn = sqlite3.connect('ludi.db')
    c = conn.cursor()
    
    # Query: Compare minutes in blowout vs close games
    query = """
    WITH game_margins AS (
        SELECT 
            g.game_id,
            ABS(g.home_score - g.away_score) as margin,
            CASE 
                WHEN ABS(g.home_score - g.away_score) > 15 THEN 'Blowout'
                ELSE 'Close'
            END AS game_type
        FROM games g
        WHERE g.date >= date('now', '-' || ? || ' days')
        AND g.home_score IS NOT NULL
    )
    SELECT 
        gm.game_type,
        AVG(p.minutes) as avg_min,
        COUNT(*) as player_games
    FROM player_game_logs p
    JOIN game_margins gm ON p.game_id = gm.game_id
    WHERE p.minutes > 30  -- Starters only
    GROUP BY gm.game_type
    """
    
    c.execute(query, (days,))
    results = c.fetchall()
    conn.close()
    
    print("\n📊 Starter Minutes (MIN > 30 baseline):")
    for row in results:
        game_type, avg_min, count = row
        print(f"   {game_type:<10} | Avg: {avg_min:.1f} min | Sample: {count} games")
    
    if len(results) == 2:
        blowout_min = results[0][1] if results[0][0] == 'Blowout' else results[1][1]
        close_min = results[1][1] if results[1][0] == 'Close' else results[0][1]
        reduction = ((close_min - blowout_min) / close_min) * 100
        
        print(f"\n✅ Reduction in blowouts: {reduction:.1f}%")
        print(f"   (Module E applies 6% reduction - does data support this?)")

def test_calibrator_accuracy():
    """
    Bonus: Test if calibrator's archetype assignments match reality
    """
    print("\n" + "="*60)
    print("📋 BONUS: Calibrator Archetype Accuracy")
    print("="*60)
    
    conn = sqlite3.connect('ludi.db')
    c = conn.cursor()
    
    # Get top scorers
    query = """
    SELECT 
        player_name,
        AVG(pts) as avg_pts,
        AVG(reb) as avg_reb,
        AVG(ast) as avg_ast,
        AVG(fg3m) as avg_3pm,
        COUNT(*) as games
    FROM player_game_logs
    WHERE game_date >= date('now', '-30 days')
    GROUP BY player_name
    HAVING COUNT(*) >= 10
    ORDER BY AVG(pts) DESC
    LIMIT 5
    """
    
    c.execute(query)
    results = c.fetchall()
    conn.close()
    
    calib = LudiCalibrator()
    
    print("\n🏀 Top 5 Scorers - Archetype Check:")
    for row in results:
        player, pts, reb, ast, tpm, games = row
        
        # Mock player for archetype test
        mock_player = {
            'base_pts': pts,
            'base_reb': reb,
            'base_ast': ast,
            'base_3pm': tpm,
            'base_usg': 0.30 if pts > 25 else 0.25,
            'base_stl': 1.0,
            'base_blk': 0.5
        }
        
        archetype = calib._assign_archetype(mock_player)
        print(f"   {player:<25} | {pts:.1f} PPG | {archetype}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Phase B: Archetype Matchup Backtest')
    parser.add_argument('--full-season', action='store_true',
                       help='Run full season backtest (120 days instead of 60)')
    args = parser.parse_args()
    
    days = 120 if args.full_season else 60
    mode = "FULL SEASON" if args.full_season else "60-DAY"
    
    print("\n" + "="*70)
    print(f"🔬 PHASE B: ARCHETYPE MATCHUP BACKTEST ({mode})")
    print("="*70)
    print(f"\nValidating Module E calibration logic against historical data")
    print(f"Database: 24,770 records through Jan 10, 2026")
    print(f"Date range: Last {days} days")
    print("="*70)
    
    try:
        test_slasher_vs_hackers(days)
        test_stretch_big_vs_paint_pack(days)
        test_blowout_tax(days)
        test_calibrator_accuracy()
        
        print("\n" + "="*70)
        print(f"📊 BACKTEST COMPLETE ({mode})")
        print("="*70)
        print("\nReview results above to validate Module E matchup logic.")
        print("If trends align with predictions, Module E logic is sound.")
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
