#!/usr/bin/env python3
"""
Sync team DVP (Defender vs Position) rankings by offensive archetype.
Computes how well each team defends specific offensive archetypes.
"""

import argparse
import sqlite3
import os
import sys
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'ludi.db')
DEFAULT_SEASON = '2025-26'

BDL_TO_STANDARD = {
    'GS': 'GSW',
    'SA': 'SAS',
    'NO': 'NOP',
    'NY': 'NYK',
    'PHO': 'PHX',
}


def normalize_team(team):
    """Normalize BDL abbreviations to standard format."""
    return BDL_TO_STANDARD.get(team, team)


def create_table(conn):
    """Create team_dvp_by_archetype table if not exists."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS team_dvp_by_archetype (
            opponent_team TEXT NOT NULL,
            archetype TEXT NOT NULL,
            season TEXT NOT NULL DEFAULT '2025-26',
            games INTEGER,
            avg_pts REAL,
            avg_reb REAL,
            avg_ast REAL,
            avg_fg3m REAL,
            avg_fga REAL,
            avg_minutes REAL,
            avg_pts_per100 REAL,
            pts_vs_baseline REAL,
            reb_vs_baseline REAL,
            ast_vs_baseline REAL,
            rank_pts INTEGER,
            data_confidence TEXT,  -- HIGH (30+ games) / MEDIUM (15-29) / LOW (<15)
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (opponent_team, archetype, season)
        )
    """)
    # Index for fast Phase 8.25 queries: WHERE archetype = ? ORDER BY rank_pts
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_dvp_archetype
        ON team_dvp_by_archetype (archetype, rank_pts)
    """)
    conn.commit()


def compute_dvp(conn, season, min_games, archetype_filter=None):
    """Compute DVP statistics by archetype."""
    
    # Filter conditions
    where_clauses = [
        "pgl.game_date >= '2025-10-01'",
        "pgl.minutes >= 15",
        "p.archetype IS NOT NULL",
        "p.archetype != ''",
        "p.archetype != 'GENERALIST'"
    ]
    
    if archetype_filter:
        where_clauses.append(f"p.archetype = '{archetype_filter}'")
    
    where_sql = " AND ".join(where_clauses)
    
    # Get baseline stats per archetype (league-wide averages)
    baseline_query = f"""
        SELECT 
            p.archetype,
            AVG(pgl.pts) as league_avg_pts,
            AVG(pgl.reb) as league_avg_reb,
            AVG(pgl.ast) as league_avg_ast
        FROM player_game_logs pgl
        JOIN players p ON p.name = pgl.player_name
        WHERE {where_clauses[0]} AND {where_clauses[1]} AND {where_clauses[2]} AND {where_clauses[3]} AND {where_clauses[4]}
        GROUP BY p.archetype
    """
    baseline = {}
    for row in conn.execute(baseline_query):
        baseline[row['archetype']] = {
            'pts': row['league_avg_pts'],
            'reb': row['league_avg_reb'],
            'ast': row['league_avg_ast']
        }
    
    # Build main query with opponent team determination
    # If player team = home_team, opponent = away_team, else opponent = home_team
    # Group by raw opponent team (from games table), normalize after aggregation
    query = f"""
        SELECT 
            p.archetype,
            CASE 
                WHEN pgl.team_abbreviation = g.home_team THEN g.away_team
                ELSE g.home_team
            END as opponent_team_raw,
            COUNT(*) as games,
            AVG(pgl.pts) as avg_pts,
            AVG(pgl.reb) as avg_reb,
            AVG(pgl.ast) as avg_ast,
            AVG(pgl.fg3m) as avg_fg3m,
            AVG(pgl.fga) as avg_fga,
            AVG(pgl.minutes) as avg_minutes
        FROM player_game_logs pgl
        JOIN players p ON p.name = pgl.player_name
        JOIN games g ON g.game_id = pgl.game_id
        WHERE {where_sql}
        GROUP BY opponent_team_raw, p.archetype
        HAVING games >= {min_games}
    """
    
    # First pass: collect raw results with normalization
    raw_results = []
    for row in conn.execute(query):
        archetype = row['archetype']
        bl = baseline.get(archetype, {})
        
        avg_minutes = row['avg_minutes'] or 0
        avg_pts = row['avg_pts'] or 0
        
        if avg_minutes > 0:
            avg_pts_per100 = avg_pts * (48 / avg_minutes)
        else:
            avg_pts_per100 = 0
        
        pts_vs_baseline = avg_pts - (bl.get('pts') or 0)
        reb_vs_baseline = row['avg_reb'] - (bl.get('reb') or 0)
        ast_vs_baseline = row['avg_ast'] - (bl.get('ast') or 0)
        
        raw_results.append({
            'opponent_team_raw': row['opponent_team_raw'],
            'opponent_team': normalize_team(row['opponent_team_raw']),
            'archetype': archetype,
            'season': season,
            'games': row['games'],
            'avg_pts': avg_pts,
            'avg_reb': row['avg_reb'],
            'avg_ast': row['avg_ast'],
            'avg_fg3m': row['avg_fg3m'],
            'avg_fga': row['avg_fga'],
            'avg_minutes': avg_minutes,
            'avg_pts_per100': avg_pts_per100,
            'pts_vs_baseline': pts_vs_baseline,
            'reb_vs_baseline': reb_vs_baseline,
            'ast_vs_baseline': ast_vs_baseline,
        })
    
    # Second pass: aggregate normalized results (merge rows with same normalized team)
    aggregated = {}
    for r in raw_results:
        key = (r['opponent_team'], r['archetype'])
        if key not in aggregated:
            aggregated[key] = {
                'opponent_team': r['opponent_team'],
                'archetype': r['archetype'],
                'season': r['season'],
                'games': 0,
                'avg_pts_sum': 0,
                'avg_reb_sum': 0,
                'avg_ast_sum': 0,
                'avg_fg3m_sum': 0,
                'avg_fga_sum': 0,
                'avg_minutes_sum': 0,
            }
        aggregated[key]['games'] += r['games']
        aggregated[key]['avg_pts_sum'] += r['avg_pts'] * r['games']
        aggregated[key]['avg_reb_sum'] += r['avg_reb'] * r['games']
        aggregated[key]['avg_ast_sum'] += r['avg_ast'] * r['games']
        aggregated[key]['avg_fg3m_sum'] += r['avg_fg3m'] * r['games']
        aggregated[key]['avg_fga_sum'] += r['avg_fga'] * r['games']
        aggregated[key]['avg_minutes_sum'] += r['avg_minutes'] * r['games']
    
    # Compute weighted averages
    results = []
    for key, agg in aggregated.items():
        games = agg['games']
        if games > 0:
            avg_pts = agg['avg_pts_sum'] / games
            avg_reb = agg['avg_reb_sum'] / games
            avg_ast = agg['avg_ast_sum'] / games
            avg_fg3m = agg['avg_fg3m_sum'] / games
            avg_fga = agg['avg_fga_sum'] / games
            avg_minutes = agg['avg_minutes_sum'] / games
            avg_pts_per100 = avg_pts * (48 / avg_minutes) if avg_minutes > 0 else 0
            
            bl = baseline.get(agg['archetype'], {})
            pts_vs_baseline = avg_pts - (bl.get('pts') or 0)
            reb_vs_baseline = avg_reb - (bl.get('reb') or 0)
            ast_vs_baseline = avg_ast - (bl.get('ast') or 0)
            
            results.append({
                'opponent_team': agg['opponent_team'],
                'archetype': agg['archetype'],
                'season': agg['season'],
                'games': games,
                'avg_pts': round(avg_pts, 2),
                'avg_reb': round(avg_reb, 2),
                'avg_ast': round(avg_ast, 2),
                'avg_fg3m': round(avg_fg3m, 2),
                'avg_fga': round(avg_fga, 2),
                'avg_minutes': round(avg_minutes, 2),
                'avg_pts_per100': round(avg_pts_per100, 2),
                'pts_vs_baseline': round(pts_vs_baseline, 2),
                'reb_vs_baseline': round(reb_vs_baseline, 2),
                'ast_vs_baseline': round(ast_vs_baseline, 2),
            })
    
    # Add rank_pts per archetype (1 = lowest pts allowed = best defense)
    for archetype in set(r['archetype'] for r in results):
        archetype_results = [r for r in results if r['archetype'] == archetype]
        archetype_results.sort(key=lambda x: x['avg_pts'])
        
        for rank, r in enumerate(archetype_results, 1):
            r['rank_pts'] = rank
    
    return results


def check_sample_coverage(conn, min_games):
    """Check if archetypes have sufficient team coverage."""
    query = """
        SELECT 
            p.archetype,
            COUNT(DISTINCT 
                CASE 
                    WHEN pgl.team_abbreviation = g.home_team THEN g.away_team
                    ELSE g.home_team
                END
            ) as team_count
        FROM player_game_logs pgl
        JOIN players p ON p.name = pgl.player_name
        JOIN games g ON g.game_id = pgl.game_id
        WHERE pgl.game_date >= '2025-10-01'
            AND pgl.minutes >= 15
            AND p.archetype IS NOT NULL
            AND p.archetype != ''
            AND p.archetype != 'GENERALIST'
        GROUP BY p.archetype
        HAVING COUNT(*) >= ?
    """
    
    print("\n--- Sample Coverage Check ---")
    coverage_warning = False
    for row in conn.execute(query, (min_games,)):
        if row['team_count'] < 5:
            print(f"  WARNING: {row['archetype']} has only {row['team_count']} teams with >= {min_games} games")
            coverage_warning = True
    
    if not coverage_warning:
        print("  All archetypes have >= 5 teams with sufficient sample")


def print_summary(results, archetype_filter=None):
    """Print summary table of top matchup edges per archetype."""
    archetypes = sorted(set(r['archetype'] for r in results))
    
    print("\n" + "=" * 80)
    print("TEAM DVP BY ARCHETYPE - SUMMARY")
    print("=" * 80)
    
    for archetype in archetypes:
        archetype_results = [r for r in results if r['archetype'] == archetype]
        if not archetype_results:
            continue
        
        archetype_results.sort(key=lambda x: x['pts_vs_baseline'])  # lowest = best defense
        
        print(f"\n{archetype} (top 5 matchups - hardest to score on):")
        print("-" * 70)
        print(f"{'Team':<6} {'Games':<6} {'AvgPts':<8} {'Per100':<8} {'vsBaseline':<12} {'Rank'}")
        print("-" * 70)
        
        for r in archetype_results[:5]:
            print(f"{r['opponent_team']:<6} {r['games']:<6} {r['avg_pts']:<8.2f} {r['avg_pts_per100']:<8.2f} {r['pts_vs_baseline']:+.2f}{'':>6} {r['rank_pts']}")
    
    print("\n" + "=" * 80)
    print(f"Total rows inserted: {len(results)}")
    print("=" * 80)


def main():
    parser = argparse.ArgumentParser(description='Sync team DVP by archetype')
    parser.add_argument('--season', default=DEFAULT_SEASON, help='Season to process')
    parser.add_argument('--min-games', type=int, default=10, help='Minimum games threshold')
    parser.add_argument('--archetype', help='Filter to specific archetype')
    parser.add_argument('--dry-run', action='store_true', help='Show results without saving')
    args = parser.parse_args()
    
    if not os.path.exists(DB_PATH):
        print(f"ERROR: Database not found at {DB_PATH}")
        sys.exit(1)
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    
    create_table(conn)
    
    check_sample_coverage(conn, args.min_games)
    
    print(f"\nComputing DVP for season {args.season}...")
    if args.archetype:
        print(f"Filtering to archetype: {args.archetype}")
    
    results = compute_dvp(conn, args.season, args.min_games, args.archetype)
    
    if args.dry_run:
        print(f"\n[DRY RUN] Would insert {len(results)} rows")
        conn.close()
        return
    
    # Clear existing data for this season/archetype filter and re-insert
    if args.archetype:
        conn.execute(
            "DELETE FROM team_dvp_by_archetype WHERE season = ? AND archetype = ?",
            (args.season, args.archetype)
        )
    else:
        conn.execute(
            "DELETE FROM team_dvp_by_archetype WHERE season = ?",
            (args.season,)
        )
    
    # Insert results
    for r in results:
        # Derive confidence tier from sample size (per DVP_AND_SCHEME_METHODOLOGY.md)
        games = r['games']
        confidence = 'HIGH' if games >= 30 else ('MEDIUM' if games >= 15 else 'LOW')

        conn.execute("""
            INSERT INTO team_dvp_by_archetype (
                opponent_team, archetype, season, games,
                avg_pts, avg_reb, avg_ast, avg_fg3m, avg_fga, avg_minutes,
                avg_pts_per100, pts_vs_baseline, reb_vs_baseline, ast_vs_baseline,
                rank_pts, data_confidence, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            r['opponent_team'], r['archetype'], r['season'], r['games'],
            r['avg_pts'], r['avg_reb'], r['avg_ast'], r['avg_fg3m'], r['avg_fga'],
            r['avg_minutes'], r['avg_pts_per100'], r['pts_vs_baseline'],
            r['reb_vs_baseline'], r['ast_vs_baseline'], r['rank_pts'],
            confidence, datetime.now().isoformat()
        ))
    
    conn.commit()
    
    print_summary(results, args.archetype)
    
    conn.close()
    print("\nDone.")


if __name__ == '__main__':
    main()
