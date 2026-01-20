import sqlite3
import datetime
from utils.bet_logger import get_bet_logger
from utils.telegram_notifier import send_message
from utils.player_id_resolver import PlayerIDResolver

# =========================================================
# LUDI LENS v2.0 | THE SETTLEMENT LEDGER
# ---------------------------------------------------------
# Purpose: Grades 'Pending' bets against actual Game Logs
# Run Time: 5:00 AM EST (Daily)
# =========================================================

class BetSettler:
    def __init__(self, db_path='ludi.db'):
        self.db_path = db_path
        self.logger = get_bet_logger(db_path=db_path)
        self.conn = sqlite3.connect(db_path)
        self.resolver = PlayerIDResolver(db_path=db_path)

    def run_settlement(self, target_date=None):
        """
        Main Routine: Fetches pending bets, finds matching game logs, updates outcomes.
        """
        print("\n" + "="*60)
        print("🏛️  THE LEDGER: BET SETTLEMENT PROTOCOL")
        print("="*60)
        
        # 1. Get Pending Bets
        pending_bets = self.logger.get_pending_bets(target_date)
        if not pending_bets:
            print("✅ No pending bets found.")
            return

        print(f"📊 Processing {len(pending_bets)} pending bets...")
        
        settled_count = 0
        daily_pl = {} # Track P&L per date
        
        for bet in pending_bets:
            bet_id = bet['id']
            player_name = bet['player_name']
            game_date = bet['game_date']
            stat_cat = bet['stat_category']
            line = bet['line']
            side = bet['bet_side']
            odds_over = bet['odds_over']
            odds_under = bet['odds_under']

            # Initialize daily tracker
            if game_date not in daily_pl:
                daily_pl[game_date] = {'wins': 0, 'losses': 0, 'units': 0.0}

            # 2. Find Actual Result in Game Logs
            actual_val = self._lookup_game_log(player_name, game_date, stat_cat)
            
            if actual_val is None:
                print(f"   ⚠️  MISSING LOG: {player_name} ({game_date}) - Skipping")
                continue
            
            # 3. Determine Outcome
            outcome, profit = self._grade_bet(side, line, actual_val, bet['units'], odds_over, odds_under)
            
            # 4. Update Database
            clv = 0.0 
            self.logger.update_outcome(bet_id, outcome, actual_val, profit_loss=profit, clv=clv)
            
            # Update Tracker
            if outcome == 'WIN': daily_pl[game_date]['wins'] += 1
            if outcome == 'LOSS': daily_pl[game_date]['losses'] += 1
            daily_pl[game_date]['units'] += profit
            
            # Visual Log
            emoji = "✅" if outcome == "WIN" else "❌" if outcome == "LOSS" else "↔️"
            print(f"   {emoji} {player_name:<20} {stat_cat:<4} | Line: {line} | Actual: {actual_val} | {outcome}")
            
            settled_count += 1

        print("-" * 60)
        print(f"✅ SETTLEMENT COMPLETE: {settled_count}/{len(pending_bets)} bets graded.")
        
        # Update Daily Summary & Send Telegram
        for d, stats in daily_pl.items():
            self.logger.calculate_daily_summary(d)
            print(f"   📅 Daily Summary Updated: {d}")
            
            # Send Telegram Report for the specific date
            if stats['wins'] + stats['losses'] > 0:
                header = f"💰 **LUDI SETTLEMENT | {d}**"
                body = (
                    f"✅ Wins: {stats['wins']}\n"
                    f"❌ Losses: {stats['losses']}\n"
                    f"📈 Profit: {stats['units']:+.2f} Units"
                )
                try:
                    send_message(f"{header}\n\n{body}")
                    print(f"   🚀 Sent Telegram Recap for {d}")
                except Exception as e:
                    print(f"   ⚠️ Failed to send Telegram: {e}")

    def _lookup_game_log(self, player_name, game_date, stat_cat):
        """
        Queries player_game_logs for the actual stat value.
        Mapping needed: 'PTS' -> 'pts', 'REB' -> 'reb', '3PM' -> 'fg3m'
        """
        stat_map = {
            'PTS': 'pts',
            'REB': 'reb',
            'AST': 'ast',
            '3PM': 'fg3m',
            'BLK': 'blk',
            'BLOCKS': 'blk',
            'STL': 'stl',
            'STEALS': 'stl',
            'TOV': 'tov',
            'TURNOVERS': 'tov',
            'PRA': 'pra', # Derived
            'PR': 'pr',   # Derived
            'PA': 'pa'    # Derived
        }
        
        db_col = stat_map.get(stat_cat)
        if not db_col and stat_cat not in ['PRA', 'PR', 'PA']:
            print(f"   ❌ Unknown stat category: {stat_cat}")
            return None
            
        c = self.conn.cursor()

        # ---------------------------------------------------------
        # 🛡️ ROBUST LOOKUP: Resolve Name -> Canonical ID
        # ---------------------------------------------------------
        canonical_id = None
        try:
            canonical_id = self.resolver.resolve_to_canonical_id(player_name)
        except ValueError:
            pass # Name not found in canonical map, will fallback to string match

        def fetch_stats_by_id(pid):
            if stat_cat in ['PRA', 'PR', 'PA']:
                c.execute('''
                    SELECT pts, reb, ast FROM player_game_logs 
                    WHERE player_id = ? AND game_date = ?
                ''', (pid, game_date))
                row = c.fetchone()
                if not row: return None
                p, r, a = row
                if stat_cat == 'PRA': return p + r + a
                if stat_cat == 'PR': return p + r
                if stat_cat == 'PA': return p + a
            else:
                c.execute(f"SELECT {db_col} FROM player_game_logs WHERE player_id = ? AND game_date = ?", (pid, game_date))
                row = c.fetchone()
                return row[0] if row else None

        def fetch_stats_by_name(pname):
            if stat_cat in ['PRA', 'PR', 'PA']:
                c.execute('''
                    SELECT pts, reb, ast FROM player_game_logs 
                    WHERE player_name = ? AND game_date = ?
                ''', (pname, game_date))
                row = c.fetchone()
                if not row: return None
                p, r, a = row
                if stat_cat == 'PRA': return p + r + a
                if stat_cat == 'PR': return p + r
                if stat_cat == 'PA': return p + a
            else:
                c.execute(f"SELECT {db_col} FROM player_game_logs WHERE player_name = ? AND game_date = ?", (pname, game_date))
                row = c.fetchone()
                return row[0] if row else None

        # Strategy 1: Canonical ID Match (Highest Fidelity)
        if canonical_id:
            val = fetch_stats_by_id(canonical_id)
            if val is not None:
                return val
            # If ID found but no logs, it might be a data gap, but we double check name just in case

        # Strategy 2: Strict Name Match (Legacy Fallback)
        val = fetch_stats_by_name(player_name)
        if val is not None:
            return val
            
        return None

    def _grade_bet(self, side, line, actual, units, odds_over, odds_under):
        """
        Returns (outcome, profit_loss)
        Profit calculation assumes standard -110 unless specific odds provided.
        """
        # Default odds if missing
        price = odds_over if side == 'OVER' else odds_under
        if not price: price = -110
            
        # 1. Determine Win/Loss
        outcome = 'PUSH'
        if side == 'OVER':
            if actual > line: outcome = 'WIN'
            elif actual < line: outcome = 'LOSS'
        elif side == 'UNDER':
            if actual < line: outcome = 'WIN'
            elif actual > line: outcome = 'LOSS'
            
        # 2. Calculate Profit
        profit = 0.0
        if outcome == 'WIN':
            # Convert American Odds to Decimal Multiplier
            if price > 0:
                multiplier = price / 100.0
            else:
                multiplier = 100.0 / abs(price)
            profit = units * multiplier
        elif outcome == 'LOSS':
            profit = -units
            
        return outcome, round(profit, 2)

import config

if __name__ == "__main__":
    config.validate_config()
    settler = BetSettler()
    settler.run_settlement()
