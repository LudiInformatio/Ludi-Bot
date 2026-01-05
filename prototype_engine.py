import numpy as np
import pandas as pd
from scipy.stats import poisson

# --- CONFIGURATION (The knobs we turn) ---
SIM_ITERATIONS = 2500
RANDOM_SEED = 42  # For reproducibility during testing

class SavageEngine:
    def __init__(self):
        np.random.seed(RANDOM_SEED)

    def usage_vacuum(self, roster, player_out=None):
        """
        Adjusts usage rates when a player is OUT.
        The 'Vacuum' sucks up the missing usage and redistributes it
        proportionally to the remaining active players.
        """
        if player_out and player_out in roster:
            print(f"⚠️  ALERT: {player_out} is OUT. Engaging Usage Vacuum...")
            missing_usage = roster[player_out]['usg_pct']
            del roster[player_out]
            
            # Calculate total remaining usage weight
            total_remaining_weight = sum(p['usg_pct'] for p in roster.values())
            
            # Redistribute
            for player in roster:
                # Share of the vacuum this player absorbs
                share = roster[player]['usg_pct'] / total_remaining_weight
                boost = missing_usage * share
                roster[player]['usg_pct'] += boost
                print(f"   -> {player} absorbs {boost*100:.1f}% USG (New: {roster[player]['usg_pct']*100:.1f}%)")
        return roster

    def simulate_game(self, player_stats, defense_rating, pace_factor=1.0):
        """
        Runs Monte Carlo simulation using Poisson distribution.
        
        Formula:
        Projected_Pts = (Base_Pts * Usage_Adj * Def_Adj * Pace_Adj)
        Game_Score = Poisson(Projected_Pts)
        """
        results = []
        
        # Calculate Lambda (Expected Value) for the Poisson distribution
        # In a real model, this would be more complex (TS%, FGA, etc.)
        # Here we use a simplified PPG projection adjusted by our factors.
        
        base_ppg = player_stats['base_ppg']
        
        # Adjust for Usage (Simplified: 1.0 is neutral. Higher USG% = Higher Multiplier)
        # Assuming 'base_ppg' was achieved at 'base_usg', we scale by current_usg / base_usg
        usage_multiplier = player_stats['usg_pct'] / player_stats['base_usg']
        
        # Adjust for Defense (Simplified: 110 is league avg. Higher is worse defense -> more points)
        defense_multiplier = defense_rating / 110.0
        
        # Final Expected Value (Lambda)
        expected_points = base_ppg * usage_multiplier * defense_multiplier * pace_factor
        
        # The S.A.V.A.G.E. Simulation (2500 runs)
        # We simulate the game 2500 times
        simulated_outcomes = np.random.poisson(expected_points, SIM_ITERATIONS)
        
        return {
            'player': player_stats['name'],
            'mean': np.mean(simulated_outcomes),
            'median': np.median(simulated_outcomes),
            'floor': np.percentile(simulated_outcomes, 10), # 10th percentile (Safe floor)
            'ceiling': np.percentile(simulated_outcomes, 90), # 90th percentile (Ceiling game)
            'prob_20_plus': np.mean(simulated_outcomes >= 20) * 100,
            'prob_30_plus': np.mean(simulated_outcomes >= 30) * 100
        }

# --- THE LAB (Running the Test) ---

def run_test_scenario():
    engine = SavageEngine()
    
    print("\n--- 🧪 SCENARIO: Milwaukee Bucks vs Indiana Pacers (High Pace) ---")
    print(f"System: {SIM_ITERATIONS} Simulations | Distribution: Poisson")
    print("Season: 2025-26 (Current Roster)")
    
    # 1. Define the Roster (REAL 2025-26 Stats)
    # Source: StatMuse, RotoWire, Basketball-Reference (Jan 2026)
    # NOTE: Dame tore his Achilles in 2024-25 playoffs, now with Portland
    bucks_roster = {
        'Giannis': {'name': 'Giannis Antetokounmpo', 'base_ppg': 28.9, 'usg_pct': 0.349, 'base_usg': 0.349},
        'KPJ':     {'name': 'Kevin Porter Jr.',     'base_ppg': 18.8, 'usg_pct': 0.260, 'base_usg': 0.260},  # New lead guard
        'Kuzma':   {'name': 'Kyle Kuzma',           'base_ppg': 13.1, 'usg_pct': 0.225, 'base_usg': 0.225},  # New forward
        'Turner':  {'name': 'Myles Turner',         'base_ppg': 12.6, 'usg_pct': 0.171, 'base_usg': 0.171},  # New center
        'Bobby':   {'name': 'Bobby Portis',         'base_ppg': 13.3, 'usg_pct': 0.233, 'base_usg': 0.233},  # 6th man
    }
    
    # Game Context
    pacers_def_rating = 118.0  # Bad defense (Good for scoring)
    game_pace = 1.05           # Very fast pace (Pacers play fast)
    
    # --- TEST 1: Everyone Healthy ---
    print("\n[TEST 1] Standard Rotation (Everyone Healthy)")
    # Deep copy to avoid modifying the original for Test 2
    roster_healthy = {k: v.copy() for k, v in bucks_roster.items()} 
    
    kpj_stats = roster_healthy['KPJ']
    res = engine.simulate_game(kpj_stats, pacers_def_rating, game_pace)
    print(f"Kevin Porter Jr. Projection:")
    print(f"  Mean: {res['mean']:.1f} pts")
    print(f"  Range (10-90%): {res['floor']:.0f} - {res['ceiling']:.0f} pts")
    print(f"  Prob 20+: {res['prob_20_plus']:.1f}%")
    print(f"  Prob 30+: {res['prob_30_plus']:.1f}%")
    
    # --- TEST 2: Giannis is OUT (Usage Vacuum) ---
    print("\n" + "="*50)
    print("[TEST 2] 🚑 SCENARIO UPDATE: Giannis Antetokounmpo is OUT")
    print("Engaging Ludi 'Usage Vacuum' protocols...")
    print("="*50)
    
    # Apply Vacuum Logic
    roster_injured = {k: v.copy() for k, v in bucks_roster.items()}
    roster_injured = engine.usage_vacuum(roster_injured, player_out='Giannis')
    
    kpj_stats_vaced = roster_injured['KPJ']
    res_vaced = engine.simulate_game(kpj_stats_vaced, pacers_def_rating, game_pace)
    
    print(f"\nKevin Porter Jr. Projection (Without Giannis):")
    print(f"  Mean: {res_vaced['mean']:.1f} pts  (Change: +{res_vaced['mean'] - res['mean']:.1f})")
    print(f"  Range (10-90%): {res_vaced['floor']:.0f} - {res_vaced['ceiling']:.0f} pts")
    print(f"  Prob 20+: {res_vaced['prob_20_plus']:.1f}%  (Change: +{res_vaced['prob_20_plus'] - res['prob_20_plus']:.1f}%)")
    print(f"  Prob 30+: {res_vaced['prob_30_plus']:.1f}%  (Change: +{res_vaced['prob_30_plus'] - res['prob_30_plus']:.1f}%)")

if __name__ == "__main__":
    run_test_scenario()
