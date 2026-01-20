#!/usr/bin/env python3
"""
Populate Canonical ID Table - Tank01 ID Reconciliation

Created: January 20, 2026
Purpose: Populate player_canonical_ids table from existing players data

Process:
1. Find all players with NBA-format IDs (4-7 digits, numeric only)
2. Insert them as canonical records with normalized names
3. Find Tank01 IDs (11+ digits) and add as aliases
4. Find legacy string IDs (with underscores) and add as aliases

Usage:
    python scripts/populate_canonical_ids.py
"""

import sqlite3
import json
import sys
import os

# Add project root to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.player_id_resolver import PlayerIDResolver

def main():
    db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'ludi.db')
    resolver = PlayerIDResolver(db_path)
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    print("=" * 80)
    print("PHASE 2: POPULATING CANONICAL ID TABLE")
    print("=" * 80)
    
    # =========================================================================
    # STEP 1: Find all players with NBA-format IDs (4-7 digits, numeric only)
    # =========================================================================
    print("\n📋 STEP 1: Finding players with NBA IDs...")
    
    # NBA IDs are 4-7 digit numbers (e.g., 2544 for LeBron, 203507 for Giannis)
    c.execute('''
        SELECT DISTINCT player_id, name, team, position
        FROM players
        WHERE LENGTH(player_id) BETWEEN 4 AND 7
        AND player_id NOT GLOB '*_*'
        AND player_id GLOB '[0-9]*'
        ORDER BY name
    ''')
    
    nba_players = c.fetchall()
    print(f"Found {len(nba_players)} players with NBA IDs\n")
    
    # =========================================================================
    # STEP 2: Insert into canonical table
    # =========================================================================
    print("📥 STEP 2: Inserting canonical records...")
    
    inserted = 0
    skipped = 0
    errors = []
    
    for player_id, name, team, position in nba_players:
        normalized = resolver.normalize_name(name)
        
        try:
            c.execute('''
                INSERT INTO player_canonical_ids 
                (canonical_id, full_name, normalized_name, team, position, tank01_aliases, nba_api_id)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (player_id, name, normalized, team, position, json.dumps([]), player_id))
            inserted += 1
            
            # Print key players
            if any(star in name.lower() for star in ['doncic', 'jokic', 'giannis', 'lebron', 'curry', 'tatum', 'durant']):
                print(f"⭐ {name} ({player_id}) → normalized: '{normalized}'")
                
        except sqlite3.IntegrityError as e:
            # Duplicate normalized name - player already exists
            skipped += 1
            if 'UNIQUE constraint' in str(e):
                errors.append(f"DUPLICATE: {name} ({player_id}) - normalized '{normalized}' already exists")
    
    conn.commit()
    print(f"\n✅ Inserted: {inserted} canonical records")
    print(f"⚠️  Skipped: {skipped} duplicates")
    
    if errors and len(errors) <= 10:
        print("\nDuplicate details:")
        for err in errors:
            print(f"  - {err}")
    elif errors:
        print(f"\n(Showing first 10 of {len(errors)} duplicates)")
        for err in errors[:10]:
            print(f"  - {err}")
    
    # =========================================================================
    # STEP 3: Find Tank01 aliases (11+ digit IDs)
    # =========================================================================
    print("\n" + "=" * 80)
    print("📋 STEP 3: Finding Tank01 aliases (11+ digit IDs)...")
    print("=" * 80)
    
    c.execute('''
        SELECT player_id, name FROM players
        WHERE LENGTH(player_id) >= 10
        AND player_id GLOB '[0-9]*'
    ''')
    
    tank01_ids = c.fetchall()
    print(f"Found {len(tank01_ids)} Tank01 IDs to process\n")
    
    aliases_added = 0
    aliases_not_matched = 0
    
    for tank01_id, name in tank01_ids:
        normalized = resolver.normalize_name(name)
        
        # Find matching canonical player
        c.execute('SELECT canonical_id FROM player_canonical_ids WHERE normalized_name = ?', (normalized,))
        row = c.fetchone()
        
        if row:
            canonical_id = row[0]
            
            # Add as alias
            c.execute('SELECT tank01_aliases FROM player_canonical_ids WHERE canonical_id = ?', (canonical_id,))
            aliases_json = c.fetchone()[0]
            aliases = json.loads(aliases_json) if aliases_json else []
            
            if tank01_id not in aliases:
                aliases.append(tank01_id)
                c.execute('''
                    UPDATE player_canonical_ids 
                    SET tank01_aliases = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE canonical_id = ?
                ''', (json.dumps(aliases), canonical_id))
                aliases_added += 1
                
                # Print key players
                if any(star in name.lower() for star in ['doncic', 'jokic', 'giannis', 'lebron', 'curry']):
                    print(f"⭐ Alias: {name} → {tank01_id} (canonical: {canonical_id})")
        else:
            aliases_not_matched += 1
    
    conn.commit()
    print(f"\n✅ Tank01 aliases added: {aliases_added}")
    print(f"⚠️  Not matched: {aliases_not_matched}")
    
    # =========================================================================
    # STEP 4: Find legacy string aliases (with underscores)
    # =========================================================================
    print("\n" + "=" * 80)
    print("📋 STEP 4: Finding legacy string aliases (underscores)...")
    print("=" * 80)
    
    c.execute('''
        SELECT player_id, name FROM players
        WHERE player_id LIKE '%_%'
    ''')
    
    legacy_ids = c.fetchall()
    print(f"Found {len(legacy_ids)} legacy IDs to process\n")
    
    legacy_added = 0
    legacy_not_matched = 0
    
    for legacy_id, name in legacy_ids:
        normalized = resolver.normalize_name(name)
        
        # Find matching canonical player
        c.execute('SELECT canonical_id FROM player_canonical_ids WHERE normalized_name = ?', (normalized,))
        row = c.fetchone()
        
        if row:
            canonical_id = row[0]
            
            # Add as alias
            c.execute('SELECT tank01_aliases FROM player_canonical_ids WHERE canonical_id = ?', (canonical_id,))
            aliases_json = c.fetchone()[0]
            aliases = json.loads(aliases_json) if aliases_json else []
            
            if legacy_id not in aliases:
                aliases.append(legacy_id)
                c.execute('''
                    UPDATE player_canonical_ids 
                    SET tank01_aliases = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE canonical_id = ?
                ''', (json.dumps(aliases), canonical_id))
                legacy_added += 1
        else:
            legacy_not_matched += 1
    
    conn.commit()
    print(f"✅ Legacy aliases added: {legacy_added}")
    print(f"⚠️  Not matched: {legacy_not_matched}")
    
    # =========================================================================
    # SUMMARY
    # =========================================================================
    print("\n" + "=" * 80)
    print("📊 FINAL SUMMARY")
    print("=" * 80)
    
    c.execute('SELECT COUNT(*) FROM player_canonical_ids')
    total_canonical = c.fetchone()[0]
    
    c.execute('SELECT COUNT(*) FROM player_canonical_ids WHERE tank01_aliases != "[]"')
    with_aliases = c.fetchone()[0]
    
    c.execute('SELECT COUNT(*) FROM players')
    total_players = c.fetchone()[0]
    
    c.execute('SELECT COUNT(*) FROM players WHERE LENGTH(player_id) BETWEEN 4 AND 7 AND player_id GLOB "[0-9]*"')
    nba_id_count = c.fetchone()[0]
    
    print(f"Total canonical records: {total_canonical}")
    print(f"Records with aliases: {with_aliases}")
    print(f"Total players table: {total_players}")
    print(f"Players with NBA IDs: {nba_id_count}")
    print(f"Duplicate reduction: {total_players - total_canonical} records")
    
    # Show a few examples with aliases
    print("\n📋 Sample records with aliases:")
    c.execute('''
        SELECT canonical_id, full_name, tank01_aliases 
        FROM player_canonical_ids 
        WHERE tank01_aliases != "[]"
        LIMIT 5
    ''')
    for row in c.fetchall():
        aliases = json.loads(row[2])
        print(f"  {row[1]} ({row[0]}): {len(aliases)} alias(es)")
    
    conn.close()
    print("\n✅ Canonical ID table populated successfully!")


if __name__ == '__main__':
    main()
