"""
SportsDataIO Player ID Crosswalk Builder
Maps SportsDataIO PlayerIDs (20000xxx format) → player_canonical_ids

What it does:
  1. ALTER TABLE player_canonical_ids to add sportsdata_id, dk_player_id, fd_player_id
  2. Fetch /Players from SportsDataIO (1 API call)
  3. Match by normalized name (handles accents: Jokić → Jokic)
  4. Write matched IDs back to player_canonical_ids

Usage:
    python scripts/build_sportsdata_crosswalk.py           # Full run
    python scripts/build_sportsdata_crosswalk.py --dry-run # Preview matches, no DB writes
    python scripts/build_sportsdata_crosswalk.py --verbose # Show all matches + misses

Cost: 1 API call (uses /Players cache if fresh)
Run: Once after initial setup, then weekly via weekly_validation.yml
"""

import os
import sys
import re
import unicodedata
import argparse
import sqlite3

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
from utils.sportsdata_client import get_client


# ---------------------------------------------------------------------------
# Name normalization (handles accents, apostrophes, hyphens)
# ---------------------------------------------------------------------------

def _normalize_name(name: str) -> str:
    """
    Normalize a player name for fuzzy matching.
    Jokić → jokic, De'Aaron → deaaron, O'Neale → oneale, Dončić → doncic
    """
    if not name:
        return ""
    # Decompose unicode (NFD separates base char from diacritic), keep only ASCII
    nfd = unicodedata.normalize("NFD", name)
    ascii_name = nfd.encode("ascii", "ignore").decode("ascii")
    # Lowercase, remove apostrophes/hyphens, collapse spaces
    clean = re.sub(r"['\-\.]", "", ascii_name).lower().strip()
    clean = re.sub(r"\s+", " ", clean)
    return clean


# ---------------------------------------------------------------------------
# Schema migration — add columns if missing
# ---------------------------------------------------------------------------

def _add_columns_if_missing(conn: sqlite3.Connection, dry_run: bool) -> list:
    """Add sportsdata_id, dk_player_id, fd_player_id to player_canonical_ids if not present."""
    cursor = conn.execute("PRAGMA table_info(player_canonical_ids)")
    existing_cols = {row[1] for row in cursor.fetchall()}

    new_cols = [
        ("sportsdata_id",  "TEXT", "SportsDataIO PlayerID (20000xxx format)"),
        ("dk_player_id",   "TEXT", "DraftKings PlayerID (from SportsDataIO /Players)"),
        ("fd_player_id",   "TEXT", "FanDuel PlayerID (from SportsDataIO /Players)"),
    ]

    added = []
    for col_name, col_type, description in new_cols:
        if col_name not in existing_cols:
            if dry_run:
                print(f"  [DRY RUN] Would ALTER TABLE player_canonical_ids ADD COLUMN {col_name} {col_type}")
            else:
                conn.execute(f"ALTER TABLE player_canonical_ids ADD COLUMN {col_name} {col_type}")
                print(f"  ✅  Added column: {col_name} — {description}")
            added.append(col_name)
        else:
            print(f"  ℹ️   Column already exists: {col_name}")
    if not dry_run and added:
        conn.commit()
    return added


# ---------------------------------------------------------------------------
# Main crosswalk logic
# ---------------------------------------------------------------------------

def build_crosswalk(dry_run: bool = False, verbose: bool = False):
    print("\n" + "=" * 65)
    print("  SPORTSDATA.IO PLAYER ID CROSSWALK BUILDER")
    print("=" * 65)

    if not config.USE_SPORTSDATA:
        print("❌  SPORTSDATA_API_KEY not set — cannot build crosswalk.")
        sys.exit(1)

    # -----------------------------------------------
    # Step 1: Schema migration
    # -----------------------------------------------
    print("\n[1/4] Schema migration")
    conn = sqlite3.connect(config.DB_PATH)
    _add_columns_if_missing(conn, dry_run)

    # -----------------------------------------------
    # Step 2: Load existing canonical IDs from DB
    # -----------------------------------------------
    print("\n[2/4] Loading player_canonical_ids from DB")
    cursor = conn.execute("""
        SELECT
            pci.canonical_id,
            pci.full_name,
            pci.normalized_name,
            p.team
        FROM player_canonical_ids pci
        LEFT JOIN players p ON pci.canonical_id = p.player_id
        WHERE pci.is_active = 1
    """)
    db_players = cursor.fetchall()
    print(f"  Found {len(db_players)} active players in player_canonical_ids")

    # Build lookup: normalized_name → (canonical_id, full_name, team)
    db_by_name = {}
    for cid, full_name, norm_name, team in db_players:
        # Use our own normalization as primary key (handles accents)
        key = _normalize_name(full_name)
        db_by_name[key] = (cid, full_name, team)
        # Also index by stored normalized_name in case it differs
        if norm_name and _normalize_name(norm_name) not in db_by_name:
            db_by_name[_normalize_name(norm_name)] = (cid, full_name, team)

    # -----------------------------------------------
    # Step 3: Fetch players from SportsDataIO
    # -----------------------------------------------
    print("\n[3/4] Fetching players from SportsDataIO /Players")
    client = get_client()
    sd_players = client.get_players()
    if not sd_players:
        print("❌  No players returned from SportsDataIO. Check API key.")
        conn.close()
        sys.exit(1)
    print(f"  Received {len(sd_players)} players from SportsDataIO")

    # -----------------------------------------------
    # Step 4: Match and write crosswalk
    # -----------------------------------------------
    print("\n[4/4] Matching players and writing crosswalk")

    matched = 0
    not_matched = []
    updates = []

    for p in sd_players:
        first = p.get("FirstName", "") or ""
        last  = p.get("LastName", "") or ""
        full  = f"{first} {last}".strip()
        sd_id = p.get("PlayerID")
        dk_id = p.get("DraftKingsPlayerID")
        fd_id = p.get("FanDuelPlayerID")

        if not sd_id or not full:
            continue

        key = _normalize_name(full)
        match = db_by_name.get(key)

        if match:
            cid, db_full_name, db_team = match
            updates.append((sd_id, dk_id, fd_id, cid))
            matched += 1
            if verbose:
                sd_team = p.get("Team", "?")
                print(f"  ✅  {full:<28} SD:{sd_id}  DB: {db_full_name} ({db_team}) → SD team: {sd_team}")
        else:
            not_matched.append((full, sd_id, p.get("Team", "?")))

    print(f"\n  Matched:     {matched}/{len(sd_players)} SportsDataIO players")
    print(f"  Not matched: {len(not_matched)}")

    if not_matched and verbose:
        print("\n  ⚠️  Unmatched players (may be G-League, Two-Way, or name variant):")
        for name, sd_id, team in not_matched[:30]:
            print(f"     {name:<28} SD:{sd_id}  Team: {team}")
        if len(not_matched) > 30:
            print(f"     ... and {len(not_matched) - 30} more")

    if dry_run:
        print(f"\n  [DRY RUN] Would write {len(updates)} crosswalk rows to DB")
        print("  No changes written.")
    else:
        # Write matches to DB
        conn.executemany("""
            UPDATE player_canonical_ids
            SET sportsdata_id = ?,
                dk_player_id  = ?,
                fd_player_id  = ?,
                updated_at    = CURRENT_TIMESTAMP
            WHERE canonical_id = ?
        """, updates)
        conn.commit()
        print(f"  ✅  Wrote {len(updates)} crosswalk rows to player_canonical_ids")

        # Verify
        cursor = conn.execute(
            "SELECT COUNT(*) FROM player_canonical_ids WHERE sportsdata_id IS NOT NULL"
        )
        count = cursor.fetchone()[0]
        print(f"  ✅  {count} players now have sportsdata_id in DB")

    conn.close()

    # -----------------------------------------------
    # Summary
    # -----------------------------------------------
    match_rate = (matched / len(sd_players) * 100) if sd_players else 0
    print(f"\n{'='*65}")
    print(f"  Match rate: {match_rate:.1f}%")
    if match_rate < 80:
        print("  ⚠️  Low match rate — check for name format differences")
    else:
        print("  ✅  Crosswalk complete")
    print(f"{'='*65}\n")


def main():
    parser = argparse.ArgumentParser(description="Build SportsDataIO → player_canonical_ids crosswalk")
    parser.add_argument("--dry-run", action="store_true", help="Preview matches without writing to DB")
    parser.add_argument("--verbose", action="store_true", help="Show all matches and unmatched players")
    args = parser.parse_args()

    build_crosswalk(dry_run=args.dry_run, verbose=args.verbose)


if __name__ == "__main__":
    main()
