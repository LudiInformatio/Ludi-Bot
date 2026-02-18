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
            actual_val, minutes_played = self._lookup_game_log(player_name, game_date, stat_cat)

            # V5.2: Auto-void DNPs (0 minutes = player was inactive/benched)
            if actual_val is not None and minutes_played is not None and minutes_played == 0:
                clv_cents_void = bet.get('clv_cents') or 0.0
                self.logger.update_outcome(bet_id, 'PUSH', -998, profit_loss=0.0, clv=clv_cents_void)
                print(f"   ↔️  VOID-DNP (0 min): {player_name} ({game_date})")
                settled_count += 1
                continue

            if actual_val is None:
                # Auto-void: check if team played and player was DNP
                void_reason = self._diagnose_missing_log(bet.get('team', ''), game_date, player_name)
                if void_reason:
                    clv_cents_void = bet.get('clv_cents') or 0.0
                    self.logger.update_outcome(bet_id, 'PUSH',
                        -999 if void_reason == 'NO_GAME' else -998,
                        profit_loss=0.0, clv=clv_cents_void)
                    print(f"   ↔️  VOID-{void_reason}: {player_name} ({game_date})")
                    settled_count += 1
                else:
                    print(f"   ⚠️  MISSING LOG: {player_name} ({game_date}) - Skipping")
                continue
            
            # 3. Determine Outcome
            outcome, profit = self._grade_bet(side, line, actual_val, bet['units'], odds_over, odds_under)
            
            # 4. Update Database — copy clv_cents to clv if available
            clv_cents = bet.get('clv_cents')
            clv = float(clv_cents) if clv_cents is not None and clv_cents != 0 else 0.0
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
        Returns: (stat_value, minutes_played) tuple. Both None if no log found.
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
            'PRA': 'pra',
            'PR': 'pr',
            'PA': 'pa',
            'RA': 'ra'
        }

        db_col = stat_map.get(stat_cat)
        if not db_col and stat_cat not in ['PRA', 'PR', 'PA', 'RA']:
            print(f"   ❌ Unknown stat category: {stat_cat}")
            return None, None

        c = self.conn.cursor()

        canonical_id = None
        try:
            canonical_id = self.resolver.resolve_to_canonical_id(player_name)
        except ValueError:
            pass

        def fetch_stats_by_id(pid):
            if stat_cat in ['PRA', 'PR', 'PA', 'RA']:
                c.execute('''
                    SELECT pts, reb, ast, minutes FROM player_game_logs
                    WHERE player_id = ? AND game_date = ?
                ''', (pid, game_date))
                row = c.fetchone()
                if not row: return None, None
                p, r, a, mins = row
                if stat_cat == 'PRA':
                    val = p + r + a
                elif stat_cat == 'PR':
                    val = p + r
                elif stat_cat == 'PA':
                    val = p + a
                else:  # RA
                    val = r + a
                return val, mins
            else:
                c.execute(f"SELECT {db_col}, minutes FROM player_game_logs WHERE player_id = ? AND game_date = ?", (pid, game_date))
                row = c.fetchone()
                return (row[0], row[1]) if row else (None, None)

        def fetch_stats_by_name(pname):
            if stat_cat in ['PRA', 'PR', 'PA', 'RA']:
                c.execute('''
                    SELECT pts, reb, ast, minutes FROM player_game_logs
                    WHERE player_name = ? AND game_date = ?
                ''', (pname, game_date))
                row = c.fetchone()
                if not row: return None, None
                p, r, a, mins = row
                if stat_cat == 'PRA':
                    val = p + r + a
                elif stat_cat == 'PR':
                    val = p + r
                elif stat_cat == 'PA':
                    val = p + a
                else:  # RA
                    val = r + a
                return val, mins
            else:
                c.execute(f"SELECT {db_col}, minutes FROM player_game_logs WHERE player_name = ? AND game_date = ?", (pname, game_date))
                row = c.fetchone()
                return (row[0], row[1]) if row else (None, None)

        # Strategy 1: Canonical ID Match (Highest Fidelity)
        if canonical_id:
            val, mins = fetch_stats_by_id(canonical_id)
            if val is not None:
                return val, mins

        # Strategy 2: Strict Name Match (Legacy Fallback)
        val, mins = fetch_stats_by_name(player_name)
        if val is not None:
            return val, mins

        return None, None

    def _diagnose_missing_log(self, team, game_date, player_name):
        """
        When a game log is missing, determine WHY so we can auto-void.
        Returns: 'NO_GAME' if team didn't play, 'DNP' if team played but
        player has no log (sat out), or None if we can't determine.
        """
        c = self.conn.cursor()

        # Check if the team had a game on this date
        c.execute(
            "SELECT COUNT(*) FROM games WHERE date = ? AND (home_team = ? OR away_team = ?)",
            (game_date, team, team)
        )
        team_had_game = c.fetchone()[0] > 0

        if not team_had_game:
            return 'NO_GAME'

        # Team played but no game log for this player → DNP (0 minutes, inactive, etc.)
        return 'DNP'

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
