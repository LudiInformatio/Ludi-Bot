#!/usr/bin/env python3
"""
validate_team_classifiers.py
===========================
Week 3 Validation Script

Goal: Verify automated team classification for both Offensive and Defensive schemes.
"""

import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.team_offensive_classifier import TeamOffensiveClassifier
from utils.team_defensive_classifier import TeamDefensiveClassifier

def validate_classifiers():
    print("=== TEAM CLASSIFIER VALIDATION ===")
    
    # 1. Offensive Validation
    print("\n[1] OFFENSIVE CLASSIFIER")
    try:
        off_classifier = TeamOffensiveClassifier()
        off_results = off_classifier.batch_classify_all_teams()
        
        # Count types
        off_counts = {}
        for team, cls in off_results.items():
            off_counts[cls] = off_counts.get(cls, 0) + 1
            
        print(f"Total Teams Classified: {len(off_results)}")
        print("Distribution:")
        for cls, count in off_counts.items():
            print(f"  {cls}: {count} ({count/30:.1%})")
            
        # Sample Check
        print("\nSample Teams:")
        samples = ['BOS', 'GSW', 'DEN', 'LAL', 'OKC']
        for team in samples:
            if team in off_results:
                summary = off_classifier.get_classification_summary(team)
                print(f"  {team}: {summary['classification']} (Conf: {summary['confidence']})")
                
    except Exception as e:
        print(f"❌ OFFENSIVE CLASSIFIER FAILED: {e}")

    # 2. Defensive Validation
    print("\n[2] DEFENSIVE CLASSIFIER")
    try:
        def_classifier = TeamDefensiveClassifier()
        def_results = def_classifier.batch_classify_all_teams()
        
        # Count types
        def_counts = {}
        for team, cls in def_results.items():
            def_counts[cls] = def_counts.get(cls, 0) + 1
            
        print(f"Total Teams Classified: {len(def_results)}")
        print("Distribution:")
        for cls, count in def_counts.items():
            print(f"  {cls}: {count} ({count/30:.1%})")
            
        # Sample Check
        print("\nSample Teams:")
        samples = ['BOS', 'MIN', 'OKC', 'MIA', 'SAS']
        for team in samples:
            if team in def_results:
                summary = def_classifier.get_classification_summary(team)
                print(f"  {team}: {summary['classification']} (Conf: {summary['confidence']})")

    except Exception as e:
        print(f"❌ DEFENSIVE CLASSIFIER FAILED: {e}")

if __name__ == "__main__":
    validate_classifiers()
