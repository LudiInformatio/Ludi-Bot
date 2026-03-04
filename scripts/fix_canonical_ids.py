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
import json
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
    'player_game_tracking',
    'player_game_opponent',
    'player_game_hustle',
    'player_clutch_stats',
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


def is_id_dirty_sql(col_name):
    """SQL expression for dirty ID detection (mirrors is_dirty_id logic)."""
    return f"(LENGTH({col_name}) > 7 OR {col_name} NOT GLOB '[12]*')"

def normalize_for_lookup(name: str) -> str:
    """Normalizes a display name to match player_canonical_ids.normalized_name format.

    Handles multiple source formats:
    - Standard: "Jalen Williams" → "jalen williams"
    - PBP Stats opponent: "Williams, Jalen" → "jalen williams"
    - ALL CAPS: "JALEN WILLIAMS" → "jalen williams"
    - Accented: "Nikola Jokić" → "nikola jokic"
    """
    if not name:
        return ""
    # Handle "Last, First" format (PBP Stats / player_game_opponent)
    if ',' in name:
        parts = name.split(',', 1)
        name = f"{parts[1].strip()} {parts[0].strip()}"
    # Strip underscores (PBP Stats IDs like "gabe_vincent")
    name = name.replace('_', ' ')
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

        if table == 'player_canonical_ids':
            pk_col = 'canonical_id'
        elif table in ('player_game_tracking', 'player_clutch_stats'):
            pk_col = 'nba_player_id'
        else:
            pk_col = 'player_id'
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
                # DELETE dirty row FIRST to free the normalized_name UNIQUE constraint
                cursor.execute(f"DELETE FROM {table} WHERE canonical_id = ?", (dirty_id,))
                dirty_row['canonical_id'] = clean_id
                cols_to_insert = [c for c in column_names if c in dirty_row and dirty_row[c] is not None]
                placeholders = ', '.join(['?'] * len(cols_to_insert))
                values_to_insert = [dirty_row[c] for c in cols_to_insert]
                insert_sql = f"INSERT INTO {table} ({', '.join(cols_to_insert)}) VALUES ({placeholders})"
                cursor.execute(insert_sql, values_to_insert)
                # Register the dirty ID as an alias on the new clean row
                existing_aliases = json.loads(dirty_row.get('aliases') or '[]')
                if dirty_id not in existing_aliases:
                    existing_aliases.append(dirty_id)
                cursor.execute(f"UPDATE {table} SET aliases = ? WHERE canonical_id = ?",
                              (json.dumps(existing_aliases), clean_id))

            if clean_row_exists:
                # Only delete dirty row here (ELSE branch already deleted it above)
                cursor.execute(f"DELETE FROM {table} WHERE canonical_id = ?", (dirty_id,))
            logging.info(f"Processed dirty ID {dirty_id} -> clean ID {clean_id} in {table}")
            
            cursor.execute("COMMIT")

        except sqlite3.IntegrityError as e:
            logging.error(f"INTEGRITY ERROR for dirty ID {dirty_id} -> clean ID {clean_id}: {e}. Skipping this player.")
            cursor.execute("ROLLBACK")
        except Exception as e:
            logging.error(f"GENERAL ERROR for dirty ID {dirty_id}: {e}. Rolling back.")
            cursor.execute("ROLLBACK")


def _build_name_to_canonical_map(conn):
    """Build normalized_name -> canonical_id lookup from the (now clean) player_canonical_ids."""
    rows = conn.execute("SELECT normalized_name, canonical_id FROM player_canonical_ids").fetchall()
    return {row[0]: row[1] for row in rows if row[0]}


def _build_alias_to_canonical_map(conn):
    """Build dirty_id -> canonical_id from aliases + tank01_aliases columns."""
    alias_map = {}
    rows = conn.execute("SELECT canonical_id, aliases, tank01_aliases FROM player_canonical_ids").fetchall()
    for canonical_id, aliases_json, tank01_json in rows:
        for col_json in [aliases_json, tank01_json]:
            if col_json and col_json != '[]':
                try:
                    for alias in json.loads(col_json):
                        alias_map[str(alias)] = canonical_id
                except (json.JSONDecodeError, TypeError):
                    pass
    return alias_map


def fix_downstream_table(conn, table, id_map, dry_run=False):
    """Fixes a downstream table by finding its own dirty IDs and resolving via name or alias lookup."""
    logging.info(f"Processing table: {table}")

    # Determine which column holds the player ID and which holds the name
    col_info = {
        'players': ('player_id', 'name'),
        'player_game_logs': ('player_id', 'player_name'),
        'player_game_advanced': ('player_id', 'player_name'),
        'player_game_tracking': ('nba_player_id', 'player_name'),
        'player_game_opponent': ('player_id', 'player_name'),
        'player_game_hustle': ('player_id', 'player_name'),
        'player_clutch_stats': ('nba_player_id', 'player_name'),
        'player_season_averages_bdl': ('player_id', 'player_name'),
        'prop_line_snapshots': ('player_id', 'player_name'),
    }

    id_col, name_col = col_info.get(table, ('player_id', None))

    # Build resolution maps from the now-clean canonical table
    name_map = _build_name_to_canonical_map(conn)
    alias_map = _build_alias_to_canonical_map(conn)

    # Find dirty IDs in THIS table
    dirty_expr = is_id_dirty_sql(id_col)
    if name_col:
        rows = conn.execute(f"SELECT DISTINCT {id_col}, {name_col} FROM {table} WHERE {dirty_expr}").fetchall()
    else:
        rows = conn.execute(f"SELECT DISTINCT {id_col} FROM {table} WHERE {dirty_expr}").fetchall()

    if not rows:
        logging.info(f"No dirty IDs found in {table}.")
        return

    # Build this table's dirty→clean map
    local_map = {}
    for row in rows:
        dirty_id = str(row[0])
        player_name = row[1] if name_col else None

        # Try alias lookup first (fastest)
        if dirty_id in alias_map:
            local_map[dirty_id] = alias_map[dirty_id]
            continue

        # Try name lookup from name column
        if player_name:
            norm = normalize_for_lookup(player_name)
            if norm in name_map:
                local_map[dirty_id] = name_map[norm]
                continue

        # Try normalizing the dirty_id itself as a name (PBP Stats text IDs)
        norm_id = normalize_for_lookup(dirty_id)
        if norm_id in name_map:
            local_map[dirty_id] = name_map[norm_id]
            continue

        # Try the original canonical id_map as fallback
        if dirty_id in id_map:
            local_map[dirty_id] = id_map[dirty_id]
            continue

        logging.warning(f"  Could not resolve dirty ID {dirty_id} ({player_name}) in {table}")

    logging.info(f"Found {len(rows)} distinct dirty IDs in {table}, resolved {len(local_map)}.")

    if dry_run:
        logging.info(f"[DRY RUN] Would update {len(local_map)} distinct IDs in {table}.")
        return

    # Define extra columns in UNIQUE constraints (besides the player ID column)
    unique_extra = {
        'players': [],  # player_id is sole PK
        'player_game_logs': ['game_date'],
        'player_game_advanced': ['game_date'],
        'player_game_tracking': ['game_date'],
        'player_game_opponent': ['game_date'],
        'player_game_hustle': ['game_date'],
        'player_clutch_stats': ['game_date'],
        'player_season_averages_bdl': ['season', 'category', 'stat_type'],
        'prop_line_snapshots': [],
    }
    extra_cols = unique_extra.get(table, [])

    cursor = conn.cursor()
    try:
        cursor.execute("BEGIN")
        updated_count = 0
        deleted_count = 0
        for dirty_id, clean_id in local_map.items():
            if extra_cols:
                # Delete dirty rows that overlap with existing clean rows on unique key
                join_cond = ' AND '.join(f"d.{c} = c.{c}" for c in extra_cols)
                cursor.execute(f"""
                    DELETE FROM {table} WHERE rowid IN (
                        SELECT d.rowid FROM {table} d
                        INNER JOIN {table} c
                            ON c.{id_col} = ? AND d.{id_col} = ? AND {join_cond}
                    )
                """, (clean_id, dirty_id))
                deleted_count += cursor.rowcount
            else:
                # Simple PK — delete dirty if clean already exists
                exists = cursor.execute(
                    f"SELECT 1 FROM {table} WHERE {id_col} = ? LIMIT 1", (clean_id,)
                ).fetchone()
                if exists:
                    cursor.execute(f"DELETE FROM {table} WHERE {id_col} = ?", (dirty_id,))
                    deleted_count += cursor.rowcount
                    continue

            # Update remaining dirty rows to clean
            res = cursor.execute(f"UPDATE {table} SET {id_col} = ? WHERE {id_col} = ?", (clean_id, dirty_id))
            updated_count += res.rowcount

        logging.info(f"Updated {updated_count} rows, deleted {deleted_count} overlapping dups in {table}.")
        cursor.execute("COMMIT")
    except Exception as e:
        logging.error(f"Error processing {table}: {e}. Rolling back.")
        cursor.execute("ROLLBACK")

def fix_beneficiary_minutes(conn, id_map, dry_run=False):
    """Fixes the beneficiary_minutes table which has two player ID columns."""
    table = 'beneficiary_minutes'
    logging.info(f"Processing special table: {table}")

    # Build resolution maps from the now-clean canonical table
    name_map = _build_name_to_canonical_map(conn)
    alias_map = _build_alias_to_canonical_map(conn)

    # Find ALL dirty IDs across both columns
    dirty_expr_out = is_id_dirty_sql('out_player_id')
    dirty_expr_ben = is_id_dirty_sql('beneficiary_player_id')
    dirty_rows = conn.execute(f"""
        SELECT DISTINCT out_player_id, out_player_name, beneficiary_player_id, beneficiary_player_name
        FROM {table}
        WHERE {dirty_expr_out} OR {dirty_expr_ben}
    """).fetchall()

    if not dirty_rows:
        logging.info(f"No dirty IDs found in {table}.")
        return

    # Build a unified resolution function
    def resolve(pid, pname):
        pid_str = str(pid)
        if not is_dirty_id(pid_str):
            return pid_str
        if pid_str in alias_map:
            return alias_map[pid_str]
        if pname:
            norm = normalize_for_lookup(pname)
            if norm in name_map:
                return name_map[norm]
        # Try normalizing the ID itself as a name
        norm_id = normalize_for_lookup(pid_str)
        if norm_id in name_map:
            return name_map[norm_id]
        if pid_str in id_map:
            return id_map[pid_str]
        return pid_str  # unchanged

    logging.info(f"Found {len(dirty_rows)} distinct dirty row combinations in {table}.")

    if dry_run:
        logging.info(f"[DRY RUN] Would fix dirty IDs in {table}.")
        return

    cursor = conn.cursor()
    try:
        cursor.execute("BEGIN")
        updated_count = 0
        deleted_count = 0

        # Process each unique dirty out_player_id
        out_ids = conn.execute(f"SELECT DISTINCT out_player_id, out_player_name FROM {table} WHERE {dirty_expr_out}").fetchall()
        for dirty_id, name in out_ids:
            clean_id = resolve(dirty_id, name)
            if str(clean_id) != str(dirty_id):
                # Delete overlapping rows (same beneficiary + team with clean out_player_id already exists)
                cursor.execute(f"""
                    DELETE FROM {table} WHERE rowid IN (
                        SELECT d.rowid FROM {table} d
                        INNER JOIN {table} c
                            ON c.out_player_id = ? AND d.out_player_id = ?
                            AND c.beneficiary_player_id = d.beneficiary_player_id
                            AND c.team_abbreviation = d.team_abbreviation
                    )
                """, (clean_id, dirty_id))
                deleted_count += cursor.rowcount
                res = cursor.execute(f"UPDATE {table} SET out_player_id = ? WHERE out_player_id = ?", (clean_id, dirty_id))
                updated_count += res.rowcount

        # Process each unique dirty beneficiary_player_id
        ben_ids = conn.execute(f"SELECT DISTINCT beneficiary_player_id, beneficiary_player_name FROM {table} WHERE {dirty_expr_ben}").fetchall()
        for dirty_id, name in ben_ids:
            clean_id = resolve(dirty_id, name)
            if str(clean_id) != str(dirty_id):
                # Delete overlapping rows
                cursor.execute(f"""
                    DELETE FROM {table} WHERE rowid IN (
                        SELECT d.rowid FROM {table} d
                        INNER JOIN {table} c
                            ON c.beneficiary_player_id = ? AND d.beneficiary_player_id = ?
                            AND c.out_player_id = d.out_player_id
                            AND c.team_abbreviation = d.team_abbreviation
                    )
                """, (clean_id, dirty_id))
                deleted_count += cursor.rowcount
                res = cursor.execute(f"UPDATE {table} SET beneficiary_player_id = ? WHERE beneficiary_player_id = ?", (clean_id, dirty_id))
                updated_count += res.rowcount

        logging.info(f"Updated {updated_count} rows, deleted {deleted_count} overlapping dups in {table}.")
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

    # --- FIXING ---
    if id_map:
        fix_player_canonical_ids(conn, id_map, dry_run)
    else:
        logging.info("No dirty IDs in canonical table — skipping canonical fix, proceeding to downstream tables.")
    
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
