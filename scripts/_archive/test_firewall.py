
import logging
import sqlite3
import json
from database import LudiHistorian

# Setup logging to see the firewall warnings
logging.basicConfig(level=logging.INFO)

def test_firewall():
    db = LudiHistorian("ludi.db")
    
    # Test Tier 1: Exact canonical match (pass through)
    # LeBron James is 2544
    res = db.resolve_player_id_for_insert("2544", "LeBron James")
    print(f"Tier 1 Test: '2544' -> {res}")
    
    # Test Tier 3: Name-based resolution + Auto-register
    # Use a fake dirty ID for Nikola Jokic (canonical: 203999)
    dirty_id = "99999999999"
    res = db.resolve_player_id_for_insert(dirty_id, "Nikola Jokić")
    print(f"Tier 3 Test: '{dirty_id}' -> {res}")
    
    # Verify auto-register
    conn = sqlite3.connect("ludi.db")
    row = conn.execute("SELECT aliases FROM player_canonical_ids WHERE canonical_id = '203999'").fetchone()
    print(f"Auto-register check (aliases): {row[0]}")
    conn.close()
    
    # Test Tier 2: Alias lookup
    # Now that it's registered, it should be found via Tier 2
    res2 = db.resolve_player_id_for_insert(dirty_id, "Some Name")
    print(f"Tier 2 Test: '{dirty_id}' -> {res2}")
    
    # Test Tier 4: Fallback
    # Unresolvable dirty ID
    unresolvable_id = "88888888888"
    res3 = db.resolve_player_id_for_insert(unresolvable_id, "Unknown Player")
    print(f"Tier 4 Test: '{unresolvable_id}' -> {res3}")

if __name__ == "__main__":
    test_firewall()
