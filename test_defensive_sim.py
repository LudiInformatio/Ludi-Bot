#!/usr/bin/env python3
"""
Quick test to verify STL/BLK simulation is working
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from module_c import LudiOracle

# Create a test player with STL/BLK data
test_player = {
    'name': 'Ryan Rollins',
    'PTS': 10.0,
    'REB': 3.0,
    'AST': 5.0,
    'STL': 1.5,  # Season average
    'BLK': 0.3,  # Season average
    'FG3M': 1.5,
    'OREB': 0.5,
    'DREB': 2.5,
    'TOV': 1.5,
    'MIN': 20.0,
    'pace_factor': 1.0,
    'def_factor': 1.0
}

# Run simulation
oracle = LudiOracle()
mods = {'pace': 1.0, 'def_factor': 1.0, 'whistle': 1.0, 'def_rtg': 1.0, 'fatigue': 1.0}
vol_dist = oracle._simulate_volume(test_player, mods)
result = oracle._simulate_outcomes(test_player, vol_dist, mods)

print("Simulation Results:")
for stat in ['PTS', 'REB', 'AST', 'STL', 'BLK', 'FG3M']:
    print(f"  {stat}: {result.get(stat, 0)}")

print(f"\nDistributions available: {'_distributions' in result}")
if '_distributions' in result:
    dist = result['_distributions']
    print(f"  STL mean: {dist.get('STL', [0]).mean():.2f}")
    print(f"  BLK mean: {dist.get('BLK', [0]).mean():.2f}")