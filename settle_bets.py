import sqlite3
import pandas as pd
from datetime import datetime

DB_PATH = "ludi.db"

def settle_bets():
    print("==================================================")
    print("LUDI INFORMATIO: BET SETTLEMENT ENGINE")
    print("==================================================")
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # 1. Get all pending bets (outcome is NULL or 'PENDING')
    cursor.execute('''
        SELECT * FROM bet_recommendations 
        WHERE outcome IS NULL OR outcome = 'PENDING'
    ''')
    pending_bets = cursor.fetchall()
    
    if not pending_bets:
        print("✅ No pending bets to settle.")
        conn.close()
        return

    print(f"🔍 Found {len(pending_bets)} pending bets. Caching game logs...")
    
    # 2. Cache relevant game logs to minimize queries
    # Get range of dates needed
    dates = set(b['game_date'] for b in pending_bets)
    min_date = min(dates)
    max_date = max(dates)
    
    cursor.execute('''
        SELECT * FROM player_game_logs 
        WHERE game_date BETWEEN ? AND ?
    ''', (min_date, max_date))
    
    logs = cursor.fetchall()
    
    # Create lookup map: (player_name, game_date) -> stats_row
    log_map = {}
    for log in logs:
        # Normalize keys: lowercase
        key = (log['player_name'].lower(), log['game_date'])
        log_map[key] = log
        
    print(f"📊 Loaded {len(logs)} game logs for lookup.")
    
    settled_count = 0
    skipped_count = 0
    
    print("\n--- GRADING RESULTS ---")
    
    for bet in pending_bets:
        bet_id = bet['id']
        player = bet['player_name']
        date = bet['game_date']
        stat_cat = bet['stat_category'] # CORRECTED
        line = float(bet['line'])
        direction = bet['bet_side'].upper() # CORRECTED
        
        # Look for match
        key = (player.lower(), date)
        
        if key not in log_map:
            skipped_count += 1
            continue
            
        # Found the game log!
        game_log = log_map[key]
        
        # Map stat category to DB column
        db_col = None
        if stat_cat in ['PTS', 'Points', 'points']: db_col = 'pts'
        elif stat_cat in ['REB', 'Rebounds', 'rebounds']: db_col = 'reb'
        elif stat_cat in ['AST', 'Assists', 'assists']: db_col = 'ast'
        elif stat_cat in ['THREES', 'Threes', '3pm', 'FG3M', '3PM']: db_col = 'fg3m'
        elif stat_cat in ['PRA']: db_col = 'pra' 
        
        actual_val = 0.0
        
        if db_col == 'pra':
            actual_val = float(game_log['pts'] + game_log['reb'] + game_log['ast'])
        elif db_col and db_col in game_log.keys():
            actual_val = float(game_log[db_col])
        else:
            print(f"⚠️  Unknown stat category '{stat_cat}' for {player}")
            skipped_count += 1
            continue
            
        # GRADE IT
        outcome = "PUSH"
        if direction == "OVER":
            if actual_val > line: outcome = "WIN"
            elif actual_val < line: outcome = "LOSS"
        elif direction == "UNDER":
            if actual_val < line: outcome = "WIN"
            elif actual_val > line: outcome = "LOSS"
            
        # Calculate PnL (Units)
        units = bet['units']
        # Determine odds used
        odds = bet['odds_over'] if direction == 'OVER' else bet['odds_under']
        
        profit = 0.0
        
        if outcome == "WIN":
            if odds and odds != 0: # Check just in case
                if odds > 0:
                    profit = units * (odds / 100)
                else:
                    profit = units * (100 / abs(odds))
        elif outcome == "LOSS":
            profit = -units
        
        # Update DB
        cursor.execute('''
            UPDATE bet_recommendations
            SET outcome = ?,
                actual_result = ?,
                profit_loss = ?,
                settled_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (outcome, actual_val, round(profit, 3), bet_id))
        
        settled_count += 1

    conn.commit()
    conn.close()
    
    print("-" * 50)
    print(f"🏁 SETTLEMENT COMPLETE")
    print(f"✅ Settled: {settled_count}")
    print(f"⏳ Pending: {skipped_count} (Waiting for game logs)")
    print("==================================================")

if __name__ == "__main__":
    settle_bets()
