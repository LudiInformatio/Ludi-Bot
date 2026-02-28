#!/usr/bin/env python3
"""
LUDI INFORMATIO | REFEREE DAILY LEARNING ENGINE
Phase 2: Incremental Learning System for Module G

Purpose:
    - Runs post-game (2 AM EST recommended)
    - Scrapes yesterday's box scores for foul totals
    - Credits/debits crew members based on deviation from expectation
    - Updates referee_daily_stats table with rolling trends
    - Graduates unknown refs to "Tracked" after N games

Usage:
    python scripts/learn_daily_trends.py [--date YYYY-MM-DD] [--dry-run]
"""

import sys
import os
import argparse
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import DB_PATH


# ═══════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════

# League average fouls per game (both teams combined) - 2025-26 season
# Verified from 806 samples: 18.74 per team × 2 = 37.48 total
# Per-ref average: 37.5 / 3 = 12.5
LEAGUE_AVG_FOULS = 37.5
PER_REF_AVG_FOULS = 12.5  # Verified per-ref average

# Minimum games before a ref "graduates" from unknown to tracked
MIN_GAMES_FOR_GRADUATION = 5

# Recency window for rolling stats
RECENCY_WINDOW = 10  # Last N games

# Learning rate: How much each game's deviation moves the average
LEARNING_RATE = 0.15  # 15% weight to new data

# ── Style classification thresholds (calibrated Feb 2026 against real data) ──
# 2025-26 data shows a bimodal distribution with a gap from 13.2 → 16.2:
#   STRICT cluster: 16.25–20.22 f/g (12 refs — Foster, Brothers, Capers, etc.)
#   NEUTRAL cluster: 12.07–13.18 f/g (34 refs)
#   Gap (no refs exist): 13.19–16.24
# LENIENT captures the genuine bottom-quartile of NEUTRAL:
#   Jonathan Sterling (12.07), Evan Scott (12.12), James Williams (12.16),
#   Justin Van Duyne (12.21), Curtis Blair (12.25) — all have pace_impact ~0.97
STRICT_THRESHOLD = 16.0    # Gap starts at 13.19; cluster starts at 16.25 (16.0 is safe)
LENIENT_THRESHOLD = 12.3   # Bottom quartile: 5 refs below 12.30 are genuinely lighter crews

# Season start date for games_worked calculation
SEASON_START = '2025-10-01'

# Rolling window for trend stats (last N games per ref, not calendar days)
# Game-count is robust against All-Star break / scheduling gaps that make calendar windows unreliable.
# Active refs work ~3-4 games/week → 10 games ≈ 2.5 weeks of regular-season play.
ROLLING_WINDOW_GAMES = 10  # last 10 games per referee


# ═══════════════════════════════════════════════════════════════════════════
# DATABASE OPERATIONS
# ═══════════════════════════════════════════════════════════════════════════

def get_yesterdays_games(conn: sqlite3.Connection, target_date: str) -> List[Dict]:
    """
    Fetch games from a specific date with their foul totals and referee crews.
    
    Args:
        conn: SQLite connection
        target_date: Date string in YYYY-MM-DD format
        
    Returns:
        List of game dicts with referee_crew and total fouls
    """
    c = conn.cursor()
    
    # Query games table for the target date
    # Note: games table uses game_id format like '20260114_MIA@DET'
    #       but player_game_logs uses nba_game_id format like '0022500001'
    c.execute('''
        SELECT game_id, home_team, away_team, referee_crew,
               home_score, away_score, pace, nba_game_id
        FROM games
        WHERE DATE(date) = ?
    ''', (target_date,))
    
    games = []
    for row in c.fetchall():
        games.append({
            'game_id': row[0],
            'home_team': row[1],
            'away_team': row[2],
            'referee_crew': row[3],  # Comma-separated string
            'home_score': row[4],
            'away_score': row[5],
            'pace': row[6],
            'nba_game_id': row[7]  # For joining with player_game_logs
        })
    
    return games


def get_game_fouls_from_logs(conn: sqlite3.Connection, game_id: str) -> Optional[int]:
    """
    Calculate total fouls for a game by summing PF from player_game_logs.
    
    Args:
        conn: SQLite connection
        game_id: The game ID to look up
        
    Returns:
        Total fouls called in the game, or None if not found
    """
    c = conn.cursor()
    
    # Sum personal fouls from both teams
    c.execute('''
        SELECT SUM(pf) FROM player_game_logs
        WHERE game_id = ?
    ''', (game_id,))
    
    result = c.fetchone()
    return result[0] if result and result[0] else None


def get_referee_profile(conn: sqlite3.Connection, ref_name: str) -> Optional[Dict]:
    """
    Get current referee profile from database.
    
    Args:
        conn: SQLite connection
        ref_name: Referee name
        
    Returns:
        Dict with referee profile or None
    """
    c = conn.cursor()
    
    c.execute('''
        SELECT referee_id, referee_name, avg_fouls_per_game, 
               avg_pace_impact, style, seasons_active
        FROM referee_profiles
        WHERE LOWER(referee_name) = LOWER(?)
    ''', (ref_name.strip(),))
    
    row = c.fetchone()
    if row:
        return {
            'referee_id': row[0],
            'referee_name': row[1],
            'avg_fouls_per_game': row[2],
            'avg_pace_impact': row[3],
            'style': row[4],
            'seasons_active': row[5]
        }
    return None


def update_referee_stats(conn: sqlite3.Connection, ref_name: str, 
                         game_fouls: float, deviation: float, 
                         dry_run: bool = False) -> bool:
    """
    Update a referee's rolling stats based on game performance.
    
    Uses exponential moving average for smooth updates.
    
    Args:
        conn: SQLite connection
        ref_name: Referee name
        game_fouls: Actual fouls in the game
        deviation: Fouls vs expected (positive = stricter)
        dry_run: If True, don't actually update
        
    Returns:
        True if update succeeded
    """
    profile = get_referee_profile(conn, ref_name)
    
    if not profile:
        print(f"      ⚠️  Unknown ref: {ref_name} (will add with estimate)")
        # Add new ref with this game as baseline
        if not dry_run:
            _add_new_referee(conn, ref_name, game_fouls)
        return True
    
    # Calculate new average using exponential moving average
    old_avg = profile['avg_fouls_per_game']
    new_avg = (1 - LEARNING_RATE) * old_avg + LEARNING_RATE * game_fouls
    
    # Determine style based on per-ref average (calibrated to real 2025-26 cluster data)
    if new_avg >= STRICT_THRESHOLD:
        new_style = 'STRICT'
    elif new_avg <= LENIENT_THRESHOLD:
        new_style = 'LENIENT'
    else:
        new_style = 'NEUTRAL'
    
    # Calculate pace impact (per-ref average is 12.5)
    new_pace_impact = round(new_avg / PER_REF_AVG_FOULS, 3)
    
    if dry_run:
        print(f"      📊 {ref_name}: {old_avg:.1f} → {new_avg:.1f} ({new_style})")
        return True
    
    # Update the database
    c = conn.cursor()
    c.execute('''
        UPDATE referee_profiles
        SET avg_fouls_per_game = ?,
            avg_pace_impact = ?,
            style = ?,
            last_updated = CURRENT_TIMESTAMP
        WHERE referee_id = ?
    ''', (round(new_avg, 2), new_pace_impact, new_style, profile['referee_id']))
    
    # Also update daily stats table
    c.execute('''
        INSERT INTO referee_daily_stats (
            referee_id, last5_fouls_avg, last5_pace_impact, sync_date
        ) VALUES (?, ?, ?, ?)
        ON CONFLICT(referee_id, sync_date) DO UPDATE SET
            last5_fouls_avg = excluded.last5_fouls_avg,
            last5_pace_impact = excluded.last5_pace_impact
    ''', (profile['referee_id'], round(new_avg, 2), new_pace_impact, 
          datetime.now().strftime('%Y-%m-%d')))
    
    conn.commit()
    return True


def _add_new_referee(conn: sqlite3.Connection, ref_name: str, first_game_fouls: float):
    """
    Add a newly discovered referee to the database.
    
    Args:
        conn: SQLite connection
        ref_name: Referee name
        first_game_fouls: Fouls from their first tracked game
    """
    # Use league average as baseline, weighted with first observation
    estimated_fouls = (PER_REF_AVG_FOULS + first_game_fouls) / 2
    pace_impact = round(estimated_fouls / PER_REF_AVG_FOULS, 3)
    
    if estimated_fouls >= STRICT_THRESHOLD:
        style = 'STRICT'
    elif estimated_fouls <= LENIENT_THRESHOLD:
        style = 'LENIENT'
    else:
        style = 'NEUTRAL'
    
    c = conn.cursor()
    c.execute('''
        INSERT INTO referee_profiles (
            referee_name, avg_fouls_per_game, avg_pace_impact,
            avg_technical_rate, style, seasons_active, data_source
        ) VALUES (?, ?, ?, 0.0, ?, 1, 'incremental-learning')
    ''', (ref_name.strip(), round(estimated_fouls, 2), pace_impact, style))
    
    conn.commit()
    print(f"      🎓 NEW REF ADDED: {ref_name} ({estimated_fouls:.1f} f/g, {style})")


def update_rolling_and_season_stats(conn: sqlite3.Connection,
                                    rolling_games_n: int = ROLLING_WINDOW_GAMES,
                                    dry_run: bool = False) -> None:
    """
    Compute and persist two complementary referee stats from game data:

    1. rolling_21d_fouls / rolling_21d_games  (column names kept for schema compat)
       Average fouls per ref over the last N GAMES (not calendar days).
       Game-count window is robust against All-Star breaks and scheduling gaps
       that cause calendar windows to return misleadingly small samples.
       Default: 10 games ≈ 2.5 weeks of regular-season play for active refs.

    2. games_worked
       Total games in games.referee_crew since SEASON_START (2025-10-01).
       Used as a confidence weight: refs with < 10 games get a weaker prior.

    Called once per night from main() after the per-game EMA loop completes.
    Operates on the parsed crew strings in games.referee_crew — no scraping needed.
    """
    c = conn.cursor()

    # ── Step 1: Fetch ALL season games with fouls (sorted by date DESC) ────────
    # We sort descending so that for each ref we can take the most recent N games.
    c.execute('''
        SELECT g.date, g.game_id, g.referee_crew, SUM(pgl.pf) AS total_fouls
        FROM games g
        JOIN player_game_logs pgl ON pgl.game_id = g.game_id
        WHERE DATE(g.date) >= ?
          AND g.referee_crew IS NOT NULL AND g.referee_crew != ''
        GROUP BY g.game_id
        HAVING total_fouls > 0
        ORDER BY g.date DESC
    ''', (SEASON_START,))
    all_season_games = c.fetchall()

    # ── Step 2: Build per-ref game history (date-ordered, most recent first) ───
    ref_game_history = {}   # ref_name -> [(game_date, fouls_per_ref), ...]
    ref_season_count = {}   # ref_name -> int (total season appearances)

    for game_date, _gid, crew_str, total_fouls in all_season_games:
        refs = [r.strip() for r in crew_str.split(',') if r.strip()]
        fouls_per_ref = total_fouls / 3.0
        for ref in refs:
            # History list is already in DESC order (most recent first)
            ref_game_history.setdefault(ref, []).append((game_date, fouls_per_ref))
            ref_season_count[ref] = ref_season_count.get(ref, 0) + 1

    if not ref_game_history:
        print(f"   [ROLLING] No game data found for rolling/season stats")
        return

    # ── Step 3: Compute last-N-games rolling average per ref ──────────────────
    ref_rolling = {}   # ref_name -> (rolling_avg_fouls, games_in_window)
    for ref_name, history in ref_game_history.items():
        # history is already most-recent-first; take first N entries
        window = history[:rolling_games_n]
        if window:
            fouls_values = [f for _, f in window]
            ref_rolling[ref_name] = (
                round(sum(fouls_values) / len(fouls_values), 2),
                len(fouls_values)
            )

    # ── Step 4: Batch update referee_profiles ─────────────────────────────────
    updated = 0
    for ref_name in ref_game_history:
        rolling_avg, rolling_count = ref_rolling.get(ref_name, (None, 0))
        season_count = ref_season_count.get(ref_name, 0)

        if not dry_run:
            c.execute('''
                UPDATE referee_profiles
                SET rolling_21d_fouls = CASE WHEN ? IS NOT NULL THEN ? ELSE rolling_21d_fouls END,
                    rolling_21d_games = ?,
                    games_worked = ?
                WHERE referee_name = ?
            ''', (rolling_avg, rolling_avg, rolling_count, season_count, ref_name))
            if c.rowcount > 0:
                updated += 1
        else:
            season_str = f"{season_count}g season"
            rolling_str = f"{rolling_avg:.1f} f/g × {rolling_count}g (last {rolling_games_n})" if rolling_avg else "no window data"
            print(f"      📊 {ref_name}: {rolling_str} | {season_str}")

    if not dry_run:
        conn.commit()

    total_season_games = len(all_season_games)
    print(f"   [ROLLING] ✅ last-{rolling_games_n}-games window + season stats updated for {updated} refs "
          f"({total_season_games} total season games processed)")


# ═══════════════════════════════════════════════════════════════════════════
# MAIN LEARNING LOGIC
# ═══════════════════════════════════════════════════════════════════════════

def process_game(conn: sqlite3.Connection, game: Dict, dry_run: bool = False) -> Dict:
    """
    Process a single game's referee data.
    
    Args:
        conn: SQLite connection
        game: Game dict with referee_crew
        dry_run: If True, don't update database
        
    Returns:
        Dict with processing results
    """
    result = {
        'game_id': game['game_id'],
        'matchup': f"{game['away_team']} @ {game['home_team']}",
        'refs_processed': 0,
        'deviation': 0.0,
        'skipped': False
    }
    
    # Get actual fouls from game logs
    # IMPORTANT: player_game_logs stores game_id in Tank01 format (YYYYMMDD_AWAY@HOME)
    # The games.nba_game_id field is NBA API format (0022500XXX) and incompatible
    lookup_id = game['game_id']  # Always use Tank01 format for player_game_logs queries
    total_fouls = get_game_fouls_from_logs(conn, lookup_id)
    
    if not total_fouls:
        result['skipped'] = True
        result['skip_reason'] = 'No foul data in logs'
        return result
    
    # Parse referee crew
    crew_str = game.get('referee_crew', '')
    if not crew_str:
        result['skipped'] = True
        result['skip_reason'] = 'No referee crew data'
        return result
    
    crew = [ref.strip() for ref in crew_str.split(',') if ref.strip()]
    if not crew:
        result['skipped'] = True
        result['skip_reason'] = 'Empty referee crew'
        return result
    
    # Calculate deviation from expected
    # Each ref gets 1/3 of the game's foul total as their "contribution"
    fouls_per_ref = total_fouls / len(crew)
    deviation = total_fouls - LEAGUE_AVG_FOULS
    deviation_per_ref = deviation / len(crew)
    
    result['total_fouls'] = total_fouls
    result['deviation'] = deviation
    result['crew'] = crew
    
    print(f"   🏀 {result['matchup']}: {total_fouls} fouls ({deviation:+.1f} vs avg)")
    
    # Update each referee's stats
    for ref_name in crew:
        update_referee_stats(conn, ref_name, fouls_per_ref, deviation_per_ref, dry_run)
        result['refs_processed'] += 1
    
    return result


def run_daily_learning(target_date: str = None, dry_run: bool = False):
    """
    Main entry point for daily learning process.
    
    Args:
        target_date: Date to process (defaults to yesterday)
        dry_run: If True, simulate but don't update database
    """
    if not target_date:
        yesterday = datetime.now() - timedelta(days=1)
        target_date = yesterday.strftime('%Y-%m-%d')
    
    print("\n" + "=" * 60)
    print("LUDI INFORMATIO | REFEREE LEARNING ENGINE")
    print(f"Processing Date: {target_date}")
    print(f"Mode: {'DRY RUN (No DB Updates)' if dry_run else 'LIVE'}")
    print("=" * 60)
    
    conn = sqlite3.connect(DB_PATH)
    
    try:
        # Fetch yesterday's games
        games = get_yesterdays_games(conn, target_date)
        
        if not games:
            print(f"\n   ⚠️  No games found for {target_date}")
            print("   Hint: Ensure games table has data for this date")
            return
        
        print(f"\n   📅 Found {len(games)} games to process\n")
        
        # Process each game (with error handling per game)
        results = []
        for game in games:
            try:
                result = process_game(conn, game, dry_run)
                results.append(result)
            except Exception as e:
                print(f"   ❌ Error processing {game.get('game_id', 'unknown')}: {e}")
                results.append({
                    'game_id': game.get('game_id', 'unknown'),
                    'matchup': f"{game.get('away_team', '?')} @ {game.get('home_team', '?')}",
                    'refs_processed': 0,
                    'deviation': 0.0,
                    'skipped': True,
                    'skip_reason': f'Error: {e}'
                })
        
        # Summary
        print("\n" + "=" * 60)
        print("LEARNING SUMMARY")
        print("=" * 60)
        
        processed = [r for r in results if not r['skipped']]
        skipped = [r for r in results if r['skipped']]
        
        total_refs = sum(r['refs_processed'] for r in processed)
        avg_deviation = sum(r['deviation'] for r in processed) / len(processed) if processed else 0
        
        print(f"   Games Processed: {len(processed)}")
        print(f"   Games Skipped: {len(skipped)}")
        print(f"   Referees Updated: {total_refs}")
        print(f"   Avg Deviation: {avg_deviation:+.1f} fouls vs league avg")
        
        if skipped:
            print("\n   Skipped Games:")
            for r in skipped:
                print(f"      - {r['matchup']}: {r.get('skip_reason', 'Unknown')}")
        
        if not dry_run:
            print("\n   ✅ Database updated successfully")
        else:
            print("\n   🔍 DRY RUN complete (no changes made)")

        # ── Rolling window + season stats (runs after per-game EMA loop) ──────
        print(f"\n   📊 Updating {ROLLING_WINDOW_DAYS}-day rolling window + season stats...")
        try:
            update_rolling_and_season_stats(conn, rolling_days=ROLLING_WINDOW_DAYS,
                                            dry_run=dry_run)
        except Exception as e:
            print(f"   ⚠️  Rolling window update failed (non-critical): {e}")

    finally:
        conn.close()


# ═══════════════════════════════════════════════════════════════════════════
# CLI INTERFACE
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='Referee Daily Learning Engine - Updates referee stats based on game results'
    )
    parser.add_argument(
        '--date', '-d',
        type=str,
        default=None,
        help='Date to process (YYYY-MM-DD format, defaults to yesterday)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Simulate processing without updating database'
    )
    
    args = parser.parse_args()
    
    run_daily_learning(target_date=args.date, dry_run=args.dry_run)
