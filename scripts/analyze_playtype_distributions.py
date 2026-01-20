#!/usr/bin/env python3
"""
Playtype Distribution Analysis Script
Week 1 of Archetype Synergy Upgrade

Analyzes tracking data to calculate percentile distributions
for setting strict playtype thresholds.

Usage:
    python scripts/analyze_playtype_distributions.py
"""

import sqlite3
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta

# Database path
DB_PATH = Path(__file__).parent.parent / 'ludi.db'

def get_tracking_stats(conn):
    """Get player averages from tracking data (L60 days)."""
    query = """
    SELECT 
        player_name,
        -- Drives
        AVG(drives_fga) as avg_drives,
        AVG(drives_pts) as avg_drives_pts,
        AVG(drives_pass_pct) as avg_drives_pass_pct,
        -- Catch & Shoot
        AVG(catch_shoot_fga) as avg_cs_fga,
        AVG(catch_shoot_fgm) as avg_cs_fgm,
        AVG(CAST(catch_shoot_fgm AS FLOAT) / NULLIF(catch_shoot_fga, 0)) as cs_pct,
        AVG(catch_shoot_3pa) as avg_cs_3pa,
        AVG(catch_shoot_3pm) as avg_cs_3pm,
        -- Pull Up
        AVG(pull_up_fga) as avg_pu_fga,
        AVG(pull_up_fgm) as avg_pu_fgm,
        AVG(CAST(pull_up_fgm AS FLOAT) / NULLIF(pull_up_fga, 0)) as pu_pct,
        AVG(pull_up_3pa) as avg_pu_3pa,
        -- Speed & Distance
        AVG(avg_speed_off) as avg_speed,
        AVG(dist_miles_off) as avg_distance,
        -- Defense/Contest
        AVG(wide_open_fga) as avg_wide_open,
        AVG(open_fga) as avg_open,
        AVG(tight_fga) as avg_tight,
        AVG(contested_fga) as avg_contested,
        AVG(avg_defender_dist) as avg_def_dist,
        -- Game count
        COUNT(*) as games
    FROM player_game_tracking
    WHERE game_date >= date('now', '-60 days')
    GROUP BY player_name
    HAVING games >= 10
    """
    return pd.read_sql(query, conn)


def get_shot_quality_stats(conn):
    """Get shot quality profile data."""
    query = """
    SELECT 
        player_name,
        at_rim_freq as rim_freq,
        corner_3_freq,
        arc_3_freq,
        short_mid_freq,
        long_mid_freq,
        shot_quality_avg as expected_efg,
        points_added
    FROM player_shot_quality
    WHERE season = '2025-26'
    """
    return pd.read_sql(query, conn)


def get_season_stats(conn):
    """Get base season stats from players table."""
    query = """
    SELECT 
        p.name as player_name,
        p.usg_pct,
        p.base_ppg,
        p.archetype as primary_archetype
    FROM players p
    WHERE p.is_active = 1
    """
    return pd.read_sql(query, conn)


def calculate_percentiles(df, column, percentiles=[0.25, 0.50, 0.75, 0.90]):
    """Calculate percentiles for a column."""
    valid_data = df[column].dropna()
    if len(valid_data) == 0:
        return {f'p{int(p*100)}': None for p in percentiles}
    
    result = {}
    for p in percentiles:
        result[f'p{int(p*100)}'] = valid_data.quantile(p)
    result['mean'] = valid_data.mean()
    result['min'] = valid_data.min()
    result['max'] = valid_data.max()
    result['count'] = len(valid_data)
    return result


def print_distribution_report(df, metrics):
    """Print formatted distribution report for each metric."""
    print("=" * 100)
    print("PLAYTYPE THRESHOLD ANALYSIS - DISTRIBUTION REPORT")
    print("=" * 100)
    print(f"\nTotal Players (10+ games): {len(df)}")
    print(f"Analysis Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print()
    
    results = {}
    for metric_name, column in metrics.items():
        if column not in df.columns:
            print(f"\n⚠️  {metric_name}: Column '{column}' not found")
            continue
            
        stats = calculate_percentiles(df, column)
        results[metric_name] = stats
        
        print(f"\n{'─' * 60}")
        print(f"📊 {metric_name}")
        print(f"{'─' * 60}")
        print(f"   Count:  {stats['count']}")
        print(f"   Mean:   {stats['mean']:.3f}")
        print(f"   Min:    {stats['min']:.3f}")
        print(f"   P25:    {stats['p25']:.3f}")
        print(f"   P50:    {stats['p50']:.3f} (Median)")
        print(f"   P75:    {stats['p75']:.3f} (Top 25%)")
        print(f"   P90:    {stats['p90']:.3f} (Elite)")
        print(f"   Max:    {stats['max']:.3f}")
    
    return results


def analyze_playtype_candidates(df_tracking, df_shot_quality, df_season):
    """Identify candidate players for each playtype."""
    
    # Merge dataframes
    df = df_tracking.copy()
    
    if not df_shot_quality.empty:
        df = df.merge(df_shot_quality, on='player_name', how='left')
    
    if not df_season.empty:
        df = df.merge(df_season, on='player_name', how='left')
    
    print("\n" + "=" * 100)
    print("PLAYTYPE CANDIDATE ANALYSIS")
    print("=" * 100)
    
    # ISO_SCORER candidates (drives > 8, pull_up_fga > 5)
    iso_mask = (df['avg_drives'].fillna(0) > 6) & (df['avg_pu_fga'].fillna(0) > 3)
    iso_candidates = df[iso_mask].sort_values('avg_drives', ascending=False)
    print(f"\n🏀 ISO_SCORER Candidates (drives > 6, pull_up > 3): {len(iso_candidates)} players")
    if len(iso_candidates) > 0:
        print(iso_candidates[['player_name', 'avg_drives', 'avg_pu_fga', 'games']].head(15).to_string(index=False))
    
    # SPOT_UP candidates (catch_shoot_fga > 4, cs_pct > 0.38)
    spot_mask = (df['avg_cs_fga'].fillna(0) > 3) & (df['cs_pct'].fillna(0) > 0.36)
    spot_candidates = df[spot_mask].sort_values('avg_cs_fga', ascending=False)
    print(f"\n🎯 SPOT_UP Candidates (catch_shoot > 3, cs% > 36%): {len(spot_candidates)} players")
    if len(spot_candidates) > 0:
        print(spot_candidates[['player_name', 'avg_cs_fga', 'cs_pct', 'avg_cs_3pa', 'games']].head(15).to_string(index=False))
    
    # P&R_HANDLER candidates (drives > 5, more pull_up than catch_shoot)
    pnr_mask = (df['avg_drives'].fillna(0) > 4) & (df['avg_pu_fga'].fillna(0) > df['avg_cs_fga'].fillna(0))
    pnr_candidates = df[pnr_mask].sort_values('avg_drives', ascending=False)
    print(f"\n🏃 P&R_HANDLER Candidates (drives > 4, pull_up > catch_shoot): {len(pnr_candidates)} players")
    if len(pnr_candidates) > 0:
        print(pnr_candidates[['player_name', 'avg_drives', 'avg_pu_fga', 'avg_cs_fga', 'games']].head(15).to_string(index=False))
    
    # P&R_ROLL_MAN candidates (more catch_shoot than pull_up, low drives)
    roll_mask = (df['avg_cs_fga'].fillna(0) > df['avg_pu_fga'].fillna(0)) & (df['avg_drives'].fillna(0) < 4)
    if 'rim_freq' in df.columns:
        roll_mask = roll_mask & (df['rim_freq'].fillna(0) > 0.30)
    roll_candidates = df[roll_mask].sort_values('avg_cs_fga', ascending=False)
    print(f"\n💥 P&R_ROLL_MAN Candidates (catch > pull, low drives, rim focus): {len(roll_candidates)} players")
    if len(roll_candidates) > 0:
        cols = ['player_name', 'avg_cs_fga', 'avg_pu_fga', 'avg_drives', 'games']
        if 'rim_freq' in df.columns:
            cols.insert(4, 'rim_freq')
        print(roll_candidates[[c for c in cols if c in roll_candidates.columns]].head(15).to_string(index=False))
    
    # TRANSITION candidates (high speed, high distance)
    trans_mask = (df['avg_speed'].fillna(0) > 4.2) & (df['avg_distance'].fillna(0) > 2.0)
    trans_candidates = df[trans_mask].sort_values('avg_speed', ascending=False)
    print(f"\n⚡ TRANSITION Candidates (speed > 4.2, distance > 2.0): {len(trans_candidates)} players")
    if len(trans_candidates) > 0:
        print(trans_candidates[['player_name', 'avg_speed', 'avg_distance', 'games']].head(15).to_string(index=False))
    
    # Summary stats
    print("\n" + "=" * 100)
    print("SUMMARY")
    print("=" * 100)
    print(f"Total players analyzed: {len(df)}")
    print(f"ISO_SCORER candidates: {len(iso_candidates)} ({len(iso_candidates)/len(df)*100:.1f}%)")
    print(f"SPOT_UP candidates: {len(spot_candidates)} ({len(spot_candidates)/len(df)*100:.1f}%)")
    print(f"P&R_HANDLER candidates: {len(pnr_candidates)} ({len(pnr_candidates)/len(df)*100:.1f}%)")
    print(f"P&R_ROLL_MAN candidates: {len(roll_candidates)} ({len(roll_candidates)/len(df)*100:.1f}%)")
    print(f"TRANSITION candidates: {len(trans_candidates)} ({len(trans_candidates)/len(df)*100:.1f}%)")
    
    return df


def main():
    print("\n" + "🏀" * 40)
    print("   ARCHETYPE SYNERGY UPGRADE - WEEK 1 ANALYSIS")
    print("🏀" * 40 + "\n")
    
    conn = sqlite3.connect(DB_PATH)
    
    try:
        # Get data
        print("📥 Loading tracking data...")
        df_tracking = get_tracking_stats(conn)
        print(f"   Loaded {len(df_tracking)} players with 10+ games")
        
        print("📥 Loading shot quality data...")
        df_shot_quality = get_shot_quality_stats(conn)
        print(f"   Loaded {len(df_shot_quality)} player profiles")
        
        print("📥 Loading season stats...")
        df_season = get_season_stats(conn)
        print(f"   Loaded {len(df_season)} active players")
        
        # Define metrics to analyze
        tracking_metrics = {
            'DRIVES (per game)': 'avg_drives',
            'DRIVES POINTS (per game)': 'avg_drives_pts',
            'DRIVES PASS % (per game)': 'avg_drives_pass_pct',
            'CATCH & SHOOT FGA (per game)': 'avg_cs_fga',
            'CATCH & SHOOT % (per game)': 'cs_pct',
            'CATCH & SHOOT 3PA (per game)': 'avg_cs_3pa',
            'PULL UP FGA (per game)': 'avg_pu_fga',
            'PULL UP % (per game)': 'pu_pct',
            'PULL UP 3PA (per game)': 'avg_pu_3pa',
            'SPEED (mph)': 'avg_speed',
            'DISTANCE (miles/game)': 'avg_distance',
            'WIDE OPEN FGA (per game)': 'avg_wide_open',
            'OPEN FGA (per game)': 'avg_open',
            'TIGHT FGA (per game)': 'avg_tight',
            'CONTESTED FGA (per game)': 'avg_contested',
        }
        
        # Print distribution report
        print_distribution_report(df_tracking, tracking_metrics)
        
        # Analyze candidates
        analyze_playtype_candidates(df_tracking, df_shot_quality, df_season)
        
    finally:
        conn.close()
    
    print("\n✅ Analysis complete!")
    print("   Next: Review distributions and adjust thresholds in config/playtype_thresholds.json")


if __name__ == '__main__':
    main()
