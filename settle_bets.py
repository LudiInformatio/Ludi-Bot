#!/usr/bin/env python
"""
settle_bets.py - The "Ghost Book" Settlement Engine

Purpose:
1. Fetch pending bets from ludi.db
2. Fetch box scores from Tank01 (Yesterday's games)
3. Grade bets (WIN/LOSS/PUSH)
4. Calculate Profit/Loss
5. Update Database

Usage:
python3 settle_bets.py --date 2026-01-12
"""

import argparse
import requests
import json
import time
from datetime import datetime, timedelta
from utils.bet_logger import get_bet_logger
import config

class BetSettler:
    def __init__(self):
        print("\n" + "="*60)
        print("🏛️  LUDI GHOST BOOK: SETTLEMENT ENGINE")
        print("="*60)
        
        self.logger = get_bet_logger()
        self.TANK_KEY = getattr(config, 'TANK01_KEY', '')
        self.TANK_HOST = "tank01-fantasy-stats.p.rapidapi.com"

    def fetch_box_scores(self, game_date):
        """Fetch all player stats for a specific date using Tank01."""
        # Endpoint: getNBADailyPlayerStats
        # Tank01 expects gameDate as YYYYMMDD
        clean_date = game_date.replace('-', '')
        url = f"https://{self.TANK_HOST}/getNBADailyPlayerStats"
        params = {'gameDate': clean_date}
        headers = {"X-RapidAPI-Key": self.TANK_KEY, "X-RapidAPI-Host": self.TANK_HOST}
        
        print(f"   📡 Fetching Box Scores for {game_date}...", end=" ")
        
        try:
            r = requests.get(url, headers=headers, params=params)
            data = r.json()
            
            if r.status_code != 200:
                print(f"❌ Failed (Status {r.status_code})")
                return {}
                
            stats_map = {}
            # Tank01 response structure: {'body': [player1, player2...]}
            players = data.get('body', [])
            
            if not players:
                print("⚠️  No stats found (Empty Body).")
                return {}

            print(f"✅ Success. Found {len(players)} players.")
            
            for p in players:
                name = p.get('longName', '')
                clean_name = self._normalize_name(name)
                
                # Extract stats (Tank01 keys)
                try:
                    stats = {
                        'PTS': float(p.get('pts', 0) or 0),
                        'REB': float(p.get('reb', 0) or 0),
                        'AST': float(p.get('ast', 0) or 0),
                        '3PM': float(p.get('fg3PtMade', 0) or 0),
                        'STL': float(p.get('stl', 0) or 0),
                        'BLK': float(p.get('blk', 0) or 0),
                        'TOV': float(p.get('TOV', 0) or 0),
                        # PRA = PTS + REB + AST
                        'PRA': float(p.get('pts', 0) or 0) + float(p.get('reb', 0) or 0) + float(p.get('ast', 0) or 0)
                    }
                    stats_map[clean_name] = stats
                except ValueError:
                    continue
                
            return stats_map
            
        except Exception as e:
            print(f"❌ Error: {e}")
            return {}

    def _normalize_name(self, name):
        return name.lower().replace('.', '').replace(' ', '').strip()

    def settle(self, target_date):
        # 1. Get Pending Bets
        bets = self.logger.get_pending_bets(game_date=target_date)
        if not bets:
            print(f"   ℹ️  No pending bets found for {target_date}.")
            return

        print(f"   📋 Found {len(bets)} pending bets.")

        # 2. Get Actuals
        box_scores = self.fetch_box_scores(target_date)
        if not box_scores:
            print("   ❌ No stats available yet. Try again later.")
            return

        # 3. Grade Bets
        wins = 0
        losses = 0
        pushes = 0
        pnl = 0.0

        print("\n   📝 Grading Ticket...")
        for bet in bets:
            player = bet['player_name']
            clean_player = self._normalize_name(player)
            stat_cat = bet['stat_category']
            line = bet['line']
            side = bet['bet_side']
            units = bet['units'] or 1.0
            
            # Find Actual
            actual_stats = box_scores.get(clean_player)
            
            # Handle DNP / Missing Data
            if not actual_stats:
                # Check if game happened? For now assume DNP = Void
                print(f"      ⚪ {player}: No stats found (DNP?) -> Voiding")
                self.logger.update_outcome(bet['id'], 'PUSH', 0.0, 0.0)
                pushes += 1
                continue

            actual_val = actual_stats.get(stat_cat)
            if actual_val is None:
                # Stat category missing (e.g. 'Fantasy Points' not mapped)
                print(f"      ⚠️  {player}: Stat {stat_cat} not found -> Voiding")
                self.logger.update_outcome(bet['id'], 'PUSH', 0.0, 0.0)
                pushes += 1
                continue
            
            # Determine Outcome
            outcome = 'PUSH'
            profit = 0.0
            
            if side == 'OVER':
                if actual_val > line: outcome = 'WIN'
                elif actual_val < line: outcome = 'LOSS'
            elif side == 'UNDER':
                if actual_val < line: outcome = 'WIN'
                elif actual_val > line: outcome = 'LOSS'
            
            # Calculate PnL (Using exact odds if available)
            odds = bet.get('odds_over') if side == 'OVER' else bet.get('odds_under')
            
            # Default to -110 if odds missing
            if not odds: odds = -110
            
            multiplier = 1.0
            if odds > 0:
                multiplier = 1 + (odds / 100)
            else:
                multiplier = 1 + (100 / abs(odds))
            
            if outcome == 'WIN':
                profit = units * (multiplier - 1)
                wins += 1
                print(f"      ✅ {player} {side} {line} {stat_cat} | Actual: {actual_val} | +{profit:.2f}u")
            elif outcome == 'LOSS':
                profit = -units
                losses += 1
                print(f"      ❌ {player} {side} {line} {stat_cat} | Actual: {actual_val} | {profit:.2f}u")
            else:
                pushes += 1
                print(f"      ⚪ {player} {side} {line} {stat_cat} | Actual: {actual_val} | Void")

            # Update DB
            self.logger.update_outcome(bet['id'], outcome, actual_val, profit)
            pnl += profit

        # 4. Summary
        print("\n" + "-"*30)
        print(f"   💰 DAILY P&L: {pnl:+.2f} Units")
        print(f"   🏆 Record: {wins}-{losses}-{pushes}")
        print("-" * 30 + "\n")
        
        # Update Daily Summary Table
        self.logger.calculate_daily_summary(target_date)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    # Default to yesterday
    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    parser.add_argument("--date", type=str, default=yesterday, help="Date to settle (YYYY-MM-DD)")
    args = parser.parse_args()
    
    settler = BetSettler()
    settler.settle(args.date)