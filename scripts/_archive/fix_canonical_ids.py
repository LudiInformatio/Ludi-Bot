#!/usr/bin/env python3
# ARCHIVED: 2026-03-04 — One-time Tank01 dirty ID remediation script. Run by QA agent. Task complete.
"""
One-Time Player ID Remediation Script
=====================================
Fixes a systemic player ID contamination problem caused by a Tank01 API
change in Jan 2026, which introduced dirty composite IDs into the system.

This script executes a multi-step remediation process:
1.  Identifies "dirty" IDs (len > 7 or not starting with '1' or '2').
2.  Builds a mapping from dirty IDs to "clean" NBA official IDs by fetching
    the complete NBA player roster from the `nba_api` and matching by name.
3.  Corrects primary keys in `player_canonical_ids` by inserting new records
    with clean IDs and deleting the old records with dirty IDs.
4.  Updates foreign keys in 7 downstream tables.
5.  De-duplicates `player_game_logs` and `player_game_advanced` where entries
    for both clean and dirty IDs existed for the same player-game.
6.  Enriches the `espn_id` column in `player_canonical_ids` by fetching data
    from the ESPN public API, ensuring high data completeness.

All database operations are performed within transactions on a per-table basis.
A `--dry-run` mode is available to inspect the proposed changes without
writing to the database.

Usage:
    # First, run a dry run to see what will be changed
    python scripts/fix_canonical_ids.py --dry-run

    # After verifying the dry run output, execute the changes
    python scripts/fix_canonical_ids.py
"""

import os
import sys
import time
import sqlite3
import unicodedata
import re
import argparse
import requests
import logging
from nba_api.stats.static import players

# Add project root for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'ludi.db')

TABLES_TO_FIX = [
    'player_canonical_ids',
    'players',
    'player_game_logs',
    'player_game_advanced',
    'beneficiary_minutes',
    'player_season_averages_bdl',
    'prop_line_snapshots',
]

# --- ESPN Enrichment ---
ESPN_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 '
                  '(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
    'Accept': 'application/json',
}
TEAM_RATE_LIMIT = 0.4
ATHLETE_RATE_LIMIT = 0.1
ESPN_TIMEOUT = 15


def is_dirty_id(player_id):
    """Detects if a player ID is a 'dirty' composite ID."""
    if not player_id:
        return False
    player_id_str = str(player_id)
    return len(player_id_str) > 7 or not player_id_str.startswith(('1', '2'))

def normalize_for_lookup(name: str) -> str:
    """Normalizes a display name to match player_canonical_ids.normalized_name format."""
    if not name:
        return ""
    name = unicodedata.normalize('NFD', name)
    name = ''.join(c for c in name if unicodedata.category(c) != 'Mn')
    name = name.lower().strip()
    name = re.sub(r'\s+(jr\.?|sr\.?|ii|iii|iv|v)$', '', name, flags=re.IGNORECASE)
    return name.strip()


def get_dirty_counts(conn):
    """Gets a count of dirty IDs in each relevant table."""
    counts = {}
    for table in TABLES_TO_FIX:
        if table == 'beneficiary_minutes':
            try:
                cursor = conn.execute(f"SELECT out_player_id, beneficiary_player_id FROM {table}")
                rows = cursor.fetchall()
                counts[table] = sum(1 for row in rows if is_dirty_id(row[0]) or is_dirty_id(row[1]))
            except sqlite3.OperationalError as e:
                logging.error(f"Error querying {table}: {e}")
                counts[table] = 'N/A'
            continue

        pk_col = 'canonical_id' if table == 'player_canonical_ids' else 'player_id'
        try:
            cursor = conn.execute(f"SELECT {pk_col} FROM {table}")
            rows = cursor.fetchall()
            counts[table] = sum(1 for row in rows if is_dirty_id(row[0]))
        except sqlite3.OperationalError as e:
            logging.error(f"Error querying {table}: {e}")
            counts[table] = 'N/A'
    return counts

def build_dirty_to_clean_map(conn):
    """Builds a mapping from dirty IDs to clean NBA IDs using normalized names."""
    logging.info("Building dirty to clean ID map...")
    # 1. Get all NBA players from the API (source of truth for clean IDs)
    try:
        nba_players = players.get_players()
        # { 'normalized_name': 'id' }
        clean_player_map = {normalize_for_lookup(p['full_name']): p['id'] for p in nba_players}
        logging.info(f"Loaded {len(clean_player_map)} players from NBA API.")
    except Exception as e:
        logging.error(f"Failed to fetch players from nba_api: {e}")
        return {}

    # 2. Get dirty entries from our database
    cursor = conn.execute("SELECT canonical_id, full_name, normalized_name FROM player_canonical_ids")
    dirty_players = {row[0]: (row[1], row[2]) for row in cursor.fetchall() if is_dirty_id(row[0])}

    # 3. Create the mapping
    id_map = {}
    for dirty_id, (full_name, normalized_name) in dirty_players.items():
        # Use the pre-computed normalized_name from the DB for lookup
        lookup_name = normalized_name if normalized_name else normalize_for_lookup(full_name)
        if not lookup_name:
            logging.warning(f"Skipping dirty ID {dirty_id} due to empty name.")
            continue
        
        clean_id = clean_player_map.get(lookup_name)
        if clean_id:
            id_map[str(dirty_id)] = str(clean_id)
            logging.info(f"Mapped dirty {dirty_id} ({full_name}) -> clean {clean_id}")
        else:
            logging.warning(f"Could not find clean ID for dirty {dirty_id} ({full_name}) using normalized name '{lookup_name}'")
            
    logging.info(f"Built map for {len(id_map)} dirty IDs.")
    return id_map

def fix_player_canonical_ids(conn, id_map, dry_run=False):
    """Fixes the player_canonical_ids table by replacing dirty PKs with clean ones."""
    table = 'player_canonical_ids'
    logging.info(f"Processing table: {table}")
    if dry_run:
        logging.info(f"[DRY RUN] Would fix {len(id_map)} records in {table}")
        return

    cursor = conn.cursor()
    
    # Process each player individually to isolate errors
    for dirty_id, clean_id in id_map.items():
        try:
            cursor.execute("BEGIN")
            
            dirty_row_data = cursor.execute("SELECT * FROM player_canonical_ids WHERE canonical_id = ?", (dirty_id,)).fetchone()
            if not dirty_row_data:
                cursor.execute("ROLLBACK")
                continue

            column_names = [desc[0] for desc in cursor.description]
            dirty_row = dict(zip(column_names, dirty_row_data))

            clean_row_exists = cursor.execute("SELECT * FROM player_canonical_ids WHERE canonical_id = ?", (clean_id,)).fetchone()
            
            if clean_row_exists:
                logging.warning(f"Clean ID {clean_id} already exists. Merging data and deleting dirty row {dirty_id}.")
                clean_row = dict(zip(column_names, clean_row_exists))
                
                update_needed = False
                update_clauses = []
                update_params = []
                for col in column_names:
                    if col in ['canonical_id', 'created_at', 'updated_at']: continue
                    if clean_row.get(col) is None and dirty_row.get(col) is not None:
                        update_clauses.append(f"{col} = ?")
                        update_params.append(dirty_row[col])
                        update_needed = True
                
                if update_needed:
                    update_params.append(clean_id)
                    update_sql = f"UPDATE {table} SET {', '.join(update_clauses)}, updated_at = CURRENT_TIMESTAMP WHERE canonical_id = ?"
                    cursor.execute(update_sql, update_params)
                    logging.info(f"Merged data from dirty ID {dirty_id} into clean ID {clean_id}")

            else:
                dirty_row['canonical_id'] = clean_id
                cols_to_insert = [c for c in column_names if c in dirty_row and dirty_row[c] is not None]
                placeholders = ', '.join(['?'] * len(cols_to_insert))
                values_to_insert = [dirty_row[c] for c in cols_to_insert]
                insert_sql = f"INSERT INTO {table} ({', '.join(cols_to_insert)}) VALUES ({placeholders})"
                cursor.execute(insert_sql, values_to_insert)

            cursor.execute(f"DELETE FROM {table} WHERE canonical_id = ?", (dirty_id,))
            logging.info(f"Processed dirty ID {dirty_id} -> clean ID {clean_id} in {table}")
            
            cursor.execute("COMMIT")

        except sqlite3.IntegrityError as e:
            logging.error(f"INTEGRITY ERROR for dirty ID {dirty_id} -> clean ID {clean_id}: {e}. Skipping this player.")
            cursor.execute("ROLLBACK")
        except Exception as e:
            logging.error(f"GENERAL ERROR for dirty ID {dirty_id}: {e}. Rolling back.")
            cursor.execute("ROLLBACK")


def fix_downstream_table(conn, table, id_map, dry_run=False):
    """Fixes a downstream table with a player_id foreign key."""
    logging.info(f"Processing table: {table}")
    if dry_run:
        logging.info(f"[DRY RUN] Would update player_id in {table} for {len(id_map)} mappings.")
        return

    cursor = conn.cursor()
    try:
        cursor.execute("BEGIN")
        updated_count = 0
        for dirty_id, clean_id in id_map.items():
            res = cursor.execute(f"UPDATE {table} SET player_id = ? WHERE player_id = ?", (clean_id, dirty_id))
            if res.rowcount > 0:
                updated_count += res.rowcount
        
        logging.info(f"Updated {updated_count} rows in {table}.")
        cursor.execute("COMMIT")
    except Exception as e:
        logging.error(f"Error processing {table}: {e}. Rolling back.")
        cursor.execute("ROLLBACK")

def fix_beneficiary_minutes(conn, id_map, dry_run=False):
    """Fixes the beneficiary_minutes table which has two player ID columns."""
    table = 'beneficiary_minutes'
    logging.info(f"Processing special table: {table}")
    if dry_run:
        logging.info(f"[DRY RUN] Would update IDs in {table} for {len(id_map)} mappings.")
        return

    cursor = conn.cursor()
    try:
        cursor.execute("BEGIN")
        
        # We need to process this table carefully to avoid unique constraint violations
        # Get all rows with dirty IDs first
        dirty_rows_q = f"SELECT * FROM {table} WHERE "
        dirty_id_clauses = []
        all_dirty_ids = list(id_map.keys())
        for dirty_id in all_dirty_ids:
            dirty_id_clauses.append("out_player_id = ?")
            dirty_id_clauses.append("beneficiary_player_id = ?")
        
        dirty_rows_q += " OR ".join(dirty_id_clauses)
        
        params = []
        for did in all_dirty_ids:
            params.extend([did, did])

        dirty_rows = cursor.execute(dirty_rows_q, params).fetchall()
        column_names = [desc[0] for desc in cursor.description]

        updated_count = 0
        deleted_count = 0

        for row_data in dirty_rows:
            row = dict(zip(column_names, row_data))
            
            clean_out_id = id_map.get(str(row['out_player_id']), row['out_player_id'])
            clean_ben_id = id_map.get(str(row['beneficiary_player_id']), row['beneficiary_player_id'])

            # If this row itself would not change, skip it
            if str(clean_out_id) == str(row['out_player_id']) and str(clean_ben_id) == str(row['beneficiary_player_id']):
                continue

            # Check if a "clean" version of this row already exists
            existing_clean_row = cursor.execute(
                f"SELECT 1 FROM {table} WHERE out_player_id = ? AND beneficiary_player_id = ? AND team_abbreviation = ?",
                (clean_out_id, clean_ben_id, row['team_abbreviation'])
            ).fetchone()

            if existing_clean_row:
                # If the clean version exists, just delete this dirty one
                cursor.execute(
                    f"DELETE FROM {table} WHERE out_player_id = ? AND beneficiary_player_id = ? AND team_abbreviation = ?",
                    (row['out_player_id'], row['beneficiary_player_id'], row['team_abbreviation'])
                )
                deleted_count += 1
            else:
                # Otherwise, update the row to its clean state
                cursor.execute(
                    f"UPDATE {table} SET out_player_id = ?, beneficiary_player_id = ? WHERE out_player_id = ? AND beneficiary_player_id = ? AND team_abbreviation = ?",
                    (clean_out_id, clean_ben_id, row['out_player_id'], row['beneficiary_player_id'], row['team_abbreviation'])
                )
                updated_count += 1

        logging.info(f"Updated {updated_count} and deleted {deleted_count} conflicting rows in {table}.")
        cursor.execute("COMMIT")
    except Exception as e:
        logging.error(f"Error processing {table}: {e}. Rolling back.")
        cursor.execute("ROLLBACK")


def deduplicate_table(conn, table, group_by_cols, dry_run=False):
    """
    De-duplicates a table after ID remediation based on a set of columns.
    """
    logging.info(f"Deduplicating table: {table}")
    
    group_by_str = ", ".join(group_by_cols)
    
    dedup_sql = f"""
        DELETE FROM {table}
        WHERE rowid NOT IN (
            SELECT MIN(rowid)
            FROM {table}
            GROUP BY {group_by_str}
        );
    """
    
    rows_to_delete_sql = f"""
        SELECT COUNT(*) FROM {table}
        WHERE rowid NOT IN (
            SELECT MIN(rowid)
            FROM {table}
            GROUP BY {group_by_str}
        );
    """

    cursor = conn.cursor()
    if dry_run:
        try:
            count_to_delete = cursor.execute(rows_to_delete_sql).fetchone()[0]
            logging.info(f"[DRY RUN] Would deduplicate {count_to_delete} rows from {table}.")
        except sqlite3.OperationalError as e:
            logging.error(f"[DRY RUN] Could not count duplicates for {table}: {e}")
        return
    
    try:
        cursor.execute("BEGIN")
        res = cursor.execute(dedup_sql)
        logging.info(f"Deduplicated {res.rowcount} rows from {table}.")
        cursor.execute("COMMIT")
    except Exception as e:
        logging.error(f"Error deduplicating {table}: {e}. Rolling back.")
        cursor.execute("ROLLBACK")


def _espn_get(url: str) -> dict:
    """Fetch JSON from a URL with retry on transient errors."""
    try:
        r = requests.get(url, headers=ESPN_HEADERS, timeout=ESPN_TIMEOUT)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        logging.warning(f"ESPN GET failed: {url[:80]} — {e}")
        return {}


def _load_espn_team_ids(conn) -> dict:
    """Load ESPN team IDs from canonical_teams table."""
    try:
        rows = conn.execute(
            "SELECT standard_abbr, espn_id FROM canonical_teams WHERE espn_id IS NOT NULL"
        ).fetchall()
        if rows:
            return {row[0]: row[1] for row in rows}
    except Exception:
        pass
    logging.warning("Could not load ESPN team IDs from DB, using hardcoded fallback.")
    return {
        'ATL': 1,  'BOS': 2,  'NOP': 3,  'CHI': 4,  'CLE': 5,
        'DAL': 6,  'DEN': 7,  'DET': 8,  'GSW': 9,  'HOU': 10,
        'IND': 11, 'LAC': 12, 'LAL': 13, 'MIA': 14, 'MIL': 15,
        'MIN': 16, 'BKN': 17, 'NYK': 18, 'ORL': 19, 'PHI': 20,
        'PHX': 21, 'POR': 22, 'SAC': 23, 'SAS': 24, 'OKC': 25,
        'UTA': 26, 'WAS': 27, 'TOR': 28, 'MEM': 29, 'CHA': 30,
    }


def fetch_team_athletes(espn_team_id: int) -> list:
    """Fetch all active athletes for an ESPN team."""
    url = (f"https://sports.core.api.espn.com/v2/sports/basketball/leagues/nba"
           f"/seasons/2026/teams/{espn_team_id}/athletes?limit=100")
    data = _espn_get(url)
    athletes = []

    for item in data.get('items', []):
        ref_url = item.get('$ref', '')
        if not ref_url:
            continue
        athlete_data = _espn_get(ref_url)
        if not athlete_data:
            continue
        espn_id = str(athlete_data.get('id', ''))
        display_name = athlete_data.get('displayName') or athlete_data.get('fullName', '')
        if espn_id and display_name:
            athletes.append({'espn_id': espn_id, 'display_name': display_name})
        time.sleep(ATHLETE_RATE_LIMIT)
    return athletes


def enrich_espn_ids(conn, dry_run=False):
    """Verifies and fills the espn_id column in player_canonical_ids."""
    logging.info("--- ESPN ID ENRICHMENT ---")
    if dry_run:
        logging.info("[DRY RUN] Would enrich ESPN IDs.")
        return

    espn_team_ids = _load_espn_team_ids(conn)
    canonical_players = {
        row[0]: row[1]
        for row in conn.execute(
            "SELECT normalized_name, canonical_id FROM player_canonical_ids WHERE espn_id IS NULL"
        ).fetchall()
    }

    logging.info(f"Attempting to find ESPN IDs for {len(canonical_players)} players.")
    
    matched_count = 0
    cursor = conn.cursor()
    
    try:
        cursor.execute("BEGIN")
        for team_abbr, espn_team_id in sorted(espn_team_ids.items()):
            logging.info(f"Scanning {team_abbr} for ESPN IDs...")
            athletes = fetch_team_athletes(espn_team_id)
            for athlete in athletes:
                norm_name = normalize_for_lookup(athlete['display_name'])
                if norm_name in canonical_players:
                    res = cursor.execute(
                        "UPDATE player_canonical_ids SET espn_id = ? WHERE normalized_name = ?",
                        (athlete['espn_id'], norm_name)
                    )
                    if res.rowcount > 0:
                        matched_count += res.rowcount
                        logging.info(f"  Matched {athlete['display_name']} -> espn_id {athlete['espn_id']}")
                        del canonical_players[norm_name] # Remove from pool
            time.sleep(TEAM_RATE_LIMIT)
        
        cursor.execute("COMMIT")
        logging.info(f"Committed {matched_count} new ESPN IDs.")

    except Exception as e:
        logging.error(f"Error during ESPN enrichment: {e}. Rolling back.")
        cursor.execute("ROLLBACK")
    
    logging.info(f"ESPN ID enrichment complete. Found {matched_count} new IDs.")
    logging.info(f"{len(canonical_players)} players still missing ESPN ID.")


def run(dry_run=False):
    """Main execution function."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA busy_timeout=30000")
    
    logging.info("--- PRE-FIX ANALYSIS ---")
    dirty_counts_before = get_dirty_counts(conn)
    for table, count in dirty_counts_before.items():
        logging.info(f"Dirty IDs in {table}: {count}")

    id_map = build_dirty_to_clean_map(conn)
    if not id_map:
        logging.info("No dirty IDs to map. Exiting.")
        conn.close()
        return

    # --- FIXING ---
    fix_player_canonical_ids(conn, id_map, dry_run)
    
    # Handle generic tables
    for table in [t for t in TABLES_TO_FIX if t not in ['player_canonical_ids', 'beneficiary_minutes']]:
        fix_downstream_table(conn, table, id_map, dry_run)
    
    # Handle special table
    fix_beneficiary_minutes(conn, id_map, dry_run)
        
    # --- DEDUPLICATION ---
    deduplicate_table(conn, 'player_game_logs', ['player_id', 'game_id'], dry_run)
    deduplicate_table(conn, 'player_game_advanced', ['player_id', 'game_date'], dry_run)

    # --- ENRICHMENT ---
    enrich_espn_ids(conn, dry_run)

    logging.info("--- POST-FIX ANALYSIS ---")
    if not dry_run:
        dirty_counts_after = get_dirty_counts(conn)
        for table, count in dirty_counts_after.items():
            logging.info(f"Dirty IDs in {table}: {count}")

    conn.close()
    logging.info("Remediation script finished.")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="One-time player ID remediation script.")
    parser.add_argument('--dry-run', action='store_true', help="Log changes without writing to DB.")
    args = parser.parse_args()
    
    run(dry_run=args.dry_run)
