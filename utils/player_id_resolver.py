# utils/player_id_resolver.py
"""
Player ID Resolution System - Canonical ID Reconciliation

Created: January 20, 2026
Purpose: Handle Tank01 API ID changes and accent normalization

Usage:
    from utils.player_id_resolver import PlayerIDResolver
    
    resolver = PlayerIDResolver()
    
    # Resolve any input to canonical NBA ID
    canonical_id = resolver.resolve_to_canonical_id("Luka Dončić")  # Returns "1629029"
    canonical_id = resolver.resolve_to_canonical_id("Luka Doncic")   # Returns "1629029"
    canonical_id = resolver.resolve_to_canonical_id("28398804489")   # Returns "1629029" (Tank01 alias)
    
    # Get full player info
    player = resolver.get_player_info("Giannis Antetokounmpo")
    # {'canonical_id': '203507', 'full_name': 'Giannis Antetokounmpo', ...}
"""

import sqlite3
import unicodedata
import json
import os


class PlayerIDResolver:
    """
    Single source of truth for player ID resolution.
    Handles Tank01 ID changes, accent normalization, and cross-API mapping.
    """
    
    def __init__(self, db_path=None):
        if db_path is None:
            # Default to ludi.db in project root
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            db_path = os.path.join(base_dir, 'ludi.db')
        self.db_path = db_path
        self._cache = {}  # In-memory cache for performance
    
    @staticmethod
    def normalize_name(name: str) -> str:
        """
        Normalize player name for matching across APIs.
        
        Handles:
        - Accents: Dončić → Doncic
        - Case: LUKA → luka
        - Suffixes: Jr., Sr., III, II removed
        - Whitespace: trimmed
        
        Examples:
            "Luka Dončić" → "luka doncic"
            "Nikola Jokić" → "nikola jokic"
            "Gary Payton II" → "gary payton"
        """
        if not name:
            return ''
        
        # Normalize whitespace (e.g., NBSP) before stripping accents
        name = ''.join(' ' if ch.isspace() else ch for ch in name)

        # Remove accents using Unicode normalization
        name = unicodedata.normalize('NFKD', name)
        name = name.encode('ASCII', 'ignore').decode('ASCII')
        
        # Lowercase and strip
        name = name.lower().strip()
        
        # Remove hyphens and other punctuation
        name = name.replace('-', '').replace('.', '').replace("'", "")
        
        # Remove suffixes — endswith only, not replace() which strips mid-name matches
        # e.g. ' v' in 'gabe vincent' or ' ii' in a hypothetical name with 'ii' mid-word
        for suffix in [' jr.', ' jr', ' sr.', ' sr', ' iii', ' ii', ' iv', ' v']:
            if name.endswith(suffix):
                name = name[:-len(suffix)]
        
        # Remove extra whitespace
        name = ' '.join(name.split())
        
        return name
    
    def resolve_to_canonical_id(self, input_value: str) -> str:
        """
        Resolve any player identifier (ID, name, alias) to canonical NBA ID.
        
        Args:
            input_value: Can be:
                - NBA ID: "203507"
                - Tank01 ID: "28118035349"
                - Name with accent: "Luka Dončić"
                - Name without accent: "Luka Doncic"
        
        Returns:
            Canonical NBA ID (e.g., "203507")
        
        Raises:
            ValueError: If player not found
        """
        if not input_value:
            raise ValueError("Empty input value")
        
        input_value = str(input_value).strip()
        
        # Check cache first
        if input_value and input_value in self._cache:
            return self._cache[input_value]
        
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA busy_timeout=30000")
        c = conn.cursor()
        
        # Try exact canonical ID match
        c.execute('SELECT canonical_id FROM player_canonical_ids WHERE canonical_id = ?', (input_value,))
        row = c.fetchone()
        if row:
            conn.close()
            if input_value:
                self._cache[input_value] = row[0]
            return row[0]
        
        # Try normalized name match
        normalized = self.normalize_name(input_value)
        c.execute('SELECT canonical_id FROM player_canonical_ids WHERE normalized_name = ?', (normalized,))
        row = c.fetchone()
        if row:
            conn.close()
            if input_value:
                self._cache[input_value] = row[0]
            return row[0]
        
        # Try Tank01 alias match
        c.execute('SELECT canonical_id, tank01_aliases FROM player_canonical_ids WHERE is_active = 1')
        rows = c.fetchall()
        for canonical_id, aliases_json in rows:
            if aliases_json:
                try:
                    aliases = json.loads(aliases_json)
                    if input_value in aliases:
                        conn.close()
                        self._cache[input_value] = canonical_id
                        return canonical_id
                except json.JSONDecodeError:
                    continue
        
        conn.close()
        raise ValueError(f"Player not found: {input_value} (normalized: {normalized})")
    
    def get_player_info(self, input_value: str) -> dict:
        """
        Get full player info by any identifier.
        
        Returns:
            {
                'canonical_id': '203507',
                'full_name': 'Giannis Antetokounmpo',
                'normalized_name': 'giannis antetokounmpo',
                'team': 'MIL',
                'position': 'F'
            }
        """
        canonical_id = self.resolve_to_canonical_id(input_value)
        
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA busy_timeout=30000")
        c = conn.cursor()
        c.execute('''
            SELECT pci.canonical_id, pci.full_name, pci.normalized_name, p.team, pci.position
            FROM player_canonical_ids pci
            LEFT JOIN players p ON pci.canonical_id = p.player_id
            WHERE pci.canonical_id = ?
        ''', (canonical_id,))
        row = c.fetchone()
        conn.close()
        
        if not row:
            raise ValueError(f"Canonical ID not found: {canonical_id}")
        
        return {
            'canonical_id': row[0],
            'full_name': row[1],
            'normalized_name': row[2],
            'team': row[3],
            'position': row[4]
        }
    
    def add_alias(self, canonical_id: str, new_alias: str):
        """Add a new Tank01 alias to existing player."""
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA busy_timeout=30000")
        c = conn.cursor()
        
        c.execute('SELECT tank01_aliases FROM player_canonical_ids WHERE canonical_id = ?', (canonical_id,))
        row = c.fetchone()
        
        if not row:
            conn.close()
            raise ValueError(f"Player not found: {canonical_id}")
        
        aliases = json.loads(row[0]) if row[0] else []
        if new_alias not in aliases:
            aliases.append(new_alias)
            c.execute('''
                UPDATE player_canonical_ids 
                SET tank01_aliases = ?, updated_at = CURRENT_TIMESTAMP 
                WHERE canonical_id = ?
            ''', (json.dumps(aliases), canonical_id))
            conn.commit()
        
        conn.close()
    
    def clear_cache(self):
        """Clear the in-memory cache (useful after bulk updates)."""
        self._cache = {}
    
    def get_all_canonical_ids(self) -> list:
        """Get list of all canonical player IDs."""
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA busy_timeout=30000")
        c = conn.cursor()
        c.execute('SELECT canonical_id FROM player_canonical_ids WHERE is_active = 1')
        ids = [row[0] for row in c.fetchall()]
        conn.close()
        return ids


# Module-level singleton for convenience
_resolver_instance = None

def get_resolver() -> PlayerIDResolver:
    """Get singleton resolver instance."""
    global _resolver_instance
    if _resolver_instance is None:
        _resolver_instance = PlayerIDResolver()
    return _resolver_instance


def normalize_player_name(name: str, db_path: str = 'ludi.db') -> str:
    """
    Quick utility to normalize a player name using PlayerIDResolver.
    Use this in sync scripts for consistent name formatting.
    
    Args:
        name: Raw player name from API/scraper
        db_path: Path to database
        
    Returns:
        Canonical player name
    """
    if not name:
        return name
        
    resolver = get_resolver()
    # Try to find canonical name
    try:
        result = resolver.get_player_info(name)
        if result and result.get('full_name'):
            return result['full_name']
    except (ValueError, KeyError):
        # Player not found in canonical IDs, use basic accent normalization only
        return resolver.normalize_name(name)
    
    return name  # Fallback to original if no match


def resolve_canonical_name(conn: sqlite3.Connection, player_name: str) -> str:
    """
    Resolve a raw player display name to its canonical full_name stored in
    player_canonical_ids (e.g. 'Nikola Jokic' → 'Nikola Jokić').

    Uses NFKD normalization (same as PlayerIDResolver.normalize_name) to strip
    accents from the input before the lookup — so both accented AND non-accented
    inputs resolve to the same canonical full_name.

    Call this before any query that matches player_name against:
      - player_injuries          (stores canonical full_name with accents)
      - player_synergy_playtypes (mixed encoding — canonical is safest)
      - player_season_averages_bdl
      - player_trends
      - beneficiary_minutes

    Args:
        conn: Open SQLite connection (caller's existing connection — no extra opens)
        player_name: Raw name from bet_recommendations, Odds API, etc.

    Returns:
        Canonical full_name string (e.g. 'Jusuf Nurkić'), or original player_name
        unchanged if no canonical match exists (graceful fallback, never raises).
    """
    if not player_name:
        return player_name
    try:
        # NFKD normalization — identical to PlayerIDResolver.normalize_name()
        norm = unicodedata.normalize('NFKD', player_name).encode('ASCII', 'ignore').decode('ASCII')
        norm = norm.lower().strip()
        for suffix in [' jr.', ' jr', ' sr.', ' sr', ' iii', ' ii', ' iv', ' v']:
            norm = norm.replace(suffix, '')
        norm = ' '.join(norm.split())
        row = conn.execute(
            "SELECT full_name FROM player_canonical_ids WHERE normalized_name = ? LIMIT 1",
            (norm,)
        ).fetchone()
        if row and row[0]:
            return row[0]
    except Exception:
        pass
    return player_name  # Graceful fallback — never breaks caller


if __name__ == '__main__':
    # Quick test
    resolver = PlayerIDResolver()
    print(f"Resolver loaded with db: {resolver.db_path}")
    print(f"Normalize test: 'Luka Dončić' → '{resolver.normalize_name('Luka Dončić')}'")
    print(f"Normalize test: 'Gary Payton II' → '{resolver.normalize_name('Gary Payton II')}'")
