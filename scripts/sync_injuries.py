#!/usr/bin/env python3
"""
Injury Sync Script

Fetches NBA injury data from BDL (primary) and Tank01 (fallback),
syncs to local database with status-change detection.

Usage:
    python scripts/sync_injuries.py              # Sync all injuries
    python scripts/sync_injuries.py --dry-run    # Preview only
    python scripts/sync_injuries.py --verbose    # Debug output

Author: Phase 8.0 Implementation
Date: February 17, 2026
"""

import sqlite3
import argparse
import sys
import os
from datetime import datetime, date
from pathlib import Path
import requests
import re

sys.path.insert(0, str(Path(__file__).parent.parent))

import config
from utils.bdl_client import BDLClient
from utils.player_id_resolver import PlayerIDResolver


class InjurySync:
    """
    Syncs NBA injury data to local database.

    Responsibilities:
    1. Fetch injuries from BDL (primary) and Tank01 (fallback)
    2. Status-change detection: only INSERT when status changes
    3. Update players table with current injury status
    4. Handle resolved injuries (set resolved_at)
    """

    STATUS_MAP = {
        'Out': 'OUT',
        'Day-To-Day': 'QUESTIONABLE',
        'Doubtful': 'DOUBTFUL',
        'Questionable': 'QUESTIONABLE',
        'Probable': 'PROBABLE',
    }

    def __init__(self, db_path='ludi.db', verbose=False, dry_run=False):
        self.db_path = db_path
        self.verbose = verbose
        self.dry_run = dry_run
        self.is_game_day_report = os.getenv('IS_GAME_DAY_REPORT', 'false').lower() == 'true'

    def _log(self, message):
        """Print message if verbose mode enabled"""
        if self.verbose:
            print(message)

    def _get_conn(self):
        """Get database connection with WAL mode"""
        conn = sqlite3.connect(self.db_path, timeout=30)
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA busy_timeout=30000;")
        return conn

    def _calculate_days_out(self, return_date_str, onset_date_str):
        """
        Calculate days_out based on return_date or onset_date.

        Args:
            return_date_str: Expected return date (YYYY-MM-DD) or None
            onset_date_str: When injury first appeared in our records or None

        Returns:
            int: Number of days out (positive = still out, negative = returning soon)
        """
        today = date.today()

        if return_date_str:
            try:
                return_date = datetime.strptime(return_date_str, '%Y-%m-%d').date()
                return (return_date - today).days
            except (ValueError, TypeError):
                pass

        if onset_date_str:
            try:
                onset_date = datetime.strptime(onset_date_str, '%Y-%m-%d').date()
                return (today - onset_date).days
            except (ValueError, TypeError):
                pass

        return 0

    def _parse_injury_type(self, description):
        """
        Parse injury type from description field.

        Takes first few words as injury type.
        Example: "Left ankle sprain" -> "Left ankle"
        """
        if not description:
            return None

        words = description.split()[:3]
        return ' '.join(words) if words else None

    def _classify_rss_headline(self, text):
        """Classify RSS headline text into injury status.
        Updated Feb 24, 2026 — expanded from live verb audit of both feeds."""
        t = text.lower()
        if any(k in t for k in [
            # Existing (verified working)
            'ruled out', "won't play", 'will not play',
            'not traveling', 'sit out', ' out ', 'out for',
            'out friday', 'out saturday', 'out sunday',
            'out monday', 'out tuesday', 'out wednesday',
            'out thursday', 'out tonight', 'out indefinitely',
            # NEW — from Feb 23 live audit (previously missed injury patterns)
            'surgery', 'season-ending', 'shut down',
            'diagnosed with', 'suffers ', 'suffered ',
            'leaves game', 'leaves practice', 'left the game',
            'out for the season', 'out for the remainder',
        ]):
            return 'OUT'
        if any(k in t for k in [
            'doubtful', 'unlikely to play', 'not expected to play',
        ]):
            return 'DOUBTFUL'
        if any(k in t for k in [
            # "undergo" anything = imaging/procedure pending → treat as DOUBTFUL
            'undergo imaging', 'undergo an mri', 'undergo surgery', 'undergo a procedure',
            'questionable', 'day-to-day', 'game-time decision',
            'game time decision', 'gtd', 'iffy',
        ]):
            return 'DOUBTFUL'
        if any(k in t for k in ['probable', 'expected to play', 'cleared',
                                  're-evaluated', 'return from']):
            return 'PROBABLE'
        return None

    def _extract_player_from_realgm_title(self, title):
        """Extract player name from free-form RealGM sentence headlines.
        Updated Feb 24, 2026 — expanded ACTION_WORDS from live feed verb audit."""
        TEAM_WORDS = {
            'cavaliers','warriors','lakers','celtics','nets','knicks','76ers',
            'raptors','bulls','bucks','pacers','pistons','wizards','hornets',
            'heat','magic','hawks','spurs','suns','nuggets','thunder','trail',
            'blazers','jazz','clippers','kings','timberwolves','grizzlies',
            'mavericks','pelicans','rockets','nba','report','sources',
            # City names that appear as first word
            'chicago','boston','golden','new','los','san','oklahoma','portland',
            'minnesota','memphis','dallas','denver','houston','indiana','detroit',
            'washington','charlotte','miami','orlando','atlanta',
        }
        first_word = title.split()[0].lower().rstrip(',') if title.split() else ''
        if first_word in TEAM_WORDS:
            return None

        ACTION_WORDS = [
            # Current (verified working)
            ' Out ', ' Will ', ' Is ', ' Has ', ' To ', " Won't ",
            ' Not ', ' Returns ', ' Ruled ', ' Expected ', ' Listed ',
            # NEW — from Feb 23 live feed verb audit:
            ' Leaves ',      # "Avdija Leaves Game With Lower Back Injury"
            ' Underwent ',   # past tense surgery/procedure
            ' Undergo ',     # "Simons To Undergo Imaging" (also caught by ' To ')
            ' Undergoes ',   # present tense
            ' Suffered ',    # "Broome Suffered Torn Meniscus"
            ' Suffers ',     # present tense
            ' Diagnosed ',   # "Haliburton Diagnosed With Shingles"
            ' Shut ',        # "Collins Shut Down By Team" (player as subject)
            ' Plans ',       # "Durant Plans To Play" → ACTIVE (filtered by classification)
            ' Pushes ',      # "Peterson Pushes Back" → ACTIVE (filtered by classification)
            ' Misses ',      # "Player Misses Practice"
            ' Missing ',     # "Player Missing With Injury"
        ]
        name_part = title
        for verb in ACTION_WORDS:
            if verb in title:
                name_part = title[:title.index(verb)].strip()
                break

        words = name_part.split()
        if 2 <= len(words) <= 4 and ',' not in name_part:
            return name_part
        return None

    def _get_last_injury_record(self, conn, player_name):
        """Get the most recent injury record for a player"""
        cursor = conn.cursor()
        cursor.execute('''
            SELECT status, onset_date, resolved_at
            FROM player_injuries
            WHERE player_name = ?
            ORDER BY snapshot_time DESC
            LIMIT 1
        ''', (player_name,))
        row = cursor.fetchone()
        if row:
            return {'status': row[0], 'onset_date': row[1], 'resolved_at': row[2]}
        return None

    def _get_active_players_from_db(self, conn):
        """Get list of all players from database"""
        cursor = conn.cursor()
        cursor.execute('SELECT name, team FROM players')
        return {(row[0], row[1]) for row in cursor.fetchall()}

    def _get_canonical_lookup_from_db(self, conn):
        """Build normalized_name → (full_name, team) lookup from player_canonical_ids."""
        cursor = conn.cursor()
        cursor.execute('''
            SELECT
                pci.normalized_name,
                pci.full_name,
                p.team
            FROM player_canonical_ids pci
            LEFT JOIN players p ON pci.canonical_id = p.player_id
            WHERE pci.is_active = 1
        ''')
        return {row[0]: (row[1], row[2]) for row in cursor.fetchall()}

    def _normalize_for_canonical(self, name: str) -> str:
        """Normalize player name to match player_canonical_ids.normalized_name format.
        Strips accents via NFD decomposition + removes common suffixes (Jr., Sr., II, III)."""
        import unicodedata
        # Strip accent marks via Unicode NFD decomposition
        nfd = unicodedata.normalize('NFD', name)
        without_accents = ''.join(c for c in nfd if unicodedata.category(c) != 'Mn')
        # Lowercase, strip trailing punctuation, remove name suffixes
        clean = without_accents.lower().strip()
        clean = re.sub(r'\s+(jr|sr|ii|iii|iv)\.?\s*$', '', clean).strip()
        return clean

    def fetch_injuries_bdl(self):
        """
        Fetch injuries from BallDontLie API (primary source).

        Returns:
            {
                "success": bool,
                "injuries": [...],
                "errors": []
            }
        """
        self._log("🔍 Fetching injuries from BDL...")

        try:
            client = BDLClient()
            if not client.api_key:
                return {
                    "success": False,
                    "injuries": [],
                    "errors": ["BDL API key not configured"]
                }

            injuries = client.get_active_injuries()

            if injuries is None:
                return {
                    "success": False,
                    "injuries": [],
                    "errors": ["BDL returned None"]
                }

            self._log(f"✅ BDL returned {len(injuries)} injury records")

            parsed_injuries = []
            for item in injuries:
                player = item.get('player', {})
                if not player:
                    continue

                first_name = player.get('first_name', '')
                last_name = player.get('last_name', '')
                player_name = f"{first_name} {last_name}".strip()

                if not player_name:
                    continue

                # BDL injury endpoint returns team_id only (no team object)
                # Resolve abbreviation from our players table by name
                team_abbreviation = None  # populated later in sync_to_database

                bdl_status = item.get('status', 'Out')
                normalized_status = self.STATUS_MAP.get(bdl_status, 'OUT')

                return_date = item.get('return_date')
                description = item.get('description', '')

                injury_type = self._parse_injury_type(description)

                parsed_injuries.append({
                    'player_name': player_name,
                    'team_abbreviation': team_abbreviation,
                    'status': normalized_status,
                    'return_date': return_date,
                    'description': description,
                    'injury_type': injury_type,
                    'source': 'BDL'
                })

            return {
                "success": True,
                "injuries": parsed_injuries,
                "errors": []
            }

        except Exception as e:
            return {
                "success": False,
                "injuries": [],
                "errors": [str(e)]
            }

    def fetch_injuries_tank01(self):
        """
        Fetch injuries from Tank01 API (fallback source).

        Returns:
            {
                "success": bool,
                "injuries": [...],
                "errors": []
            }
        """
        self._log("🔍 Fetching injuries from Tank01 (fallback)...")

        try:
            url = f"https://{config.TANK01_HOST}/getNBAInjuryList"
            headers = {
                "X-RapidAPI-Key": config.TANK01_KEY,
                "X-RapidAPI-Host": config.TANK01_HOST
            }

            response = requests.get(url, headers=headers, timeout=15)

            if response.status_code != 200:
                return {
                    "success": False,
                    "injuries": [],
                    "errors": [f"Tank01 returned status {response.status_code}"]
                }

            data = response.json()

            if 'body' not in data:
                return {
                    "success": False,
                    "injuries": [],
                    "errors": ["Tank01 response missing 'body' key"]
                }

            resolver = PlayerIDResolver()

            parsed_injuries = []
            for item in data['body']:
                # Tank01 getNBAInjuryList has no 'longName' field.
                # Resolve player name from playerID via canonical ID table.
                player_id = item.get('playerID', '')
                player_name = ''
                team_abbreviation = item.get('teamAbv', '')

                if player_id:
                    try:
                        player_info = resolver.get_player_info(player_id)
                        player_name = player_info.get('full_name', '')
                        if not team_abbreviation:
                            team_abbreviation = player_info.get('team', '')
                    except (ValueError, Exception):
                        pass  # name stays empty → skipped below

                if not player_name:
                    continue

                designation = item.get('designation', 'Available')
                normalized_status = self.STATUS_MAP.get(designation, 'ACTIVE')

                if normalized_status == 'ACTIVE':
                    continue

                # injReturnDate is YYYYMMDD; convert to YYYY-MM-DD
                raw_ret = item.get('injReturnDate', '')
                return_date = (
                    f"{raw_ret[:4]}-{raw_ret[4:6]}-{raw_ret[6:]}"
                    if len(raw_ret) == 8 else None
                )

                description = item.get('description', '')
                injury_type = self._parse_injury_type(description)

                parsed_injuries.append({
                    'player_name': player_name,
                    'team_abbreviation': team_abbreviation,
                    'status': normalized_status,
                    'return_date': return_date,
                    'description': description,
                    'injury_type': injury_type,
                    'source': 'Tank01'
                })

            self._log(f"✅ Tank01 returned {len(parsed_injuries)} injury records")

            return {
                "success": True,
                "injuries": parsed_injuries,
                "errors": []
            }

        except Exception as e:
            return {
                "success": False,
                "injuries": [],
                "errors": [str(e)]
            }

    def fetch_injuries_rss(self):
        """Fetch injuries from RotoWire + RealGM RSS feeds."""
        self._log("🔍 Fetching injuries from RSS feeds (RotoWire + RealGM)...")
        try:
            import feedparser
        except ImportError:
            return {"success": False, "injuries": [], "errors": ["feedparser not installed"]}

        # Load canonical names once for player validation (prevents college/non-NBA players)
        canonical_names = set()
        try:
            _conn = sqlite3.connect(self.db_path, timeout=5)
            canonical_names = {r[0] for r in _conn.execute(
                "SELECT normalized_name FROM player_canonical_ids WHERE is_active = 1"
            ).fetchall()}
            _conn.close()
            self._log(f"   📋 Canonical lookup loaded: {len(canonical_names)} players")
        except Exception as _e:
            self._log(f"   ⚠️  Could not load canonical names: {_e} (validation skipped)")

        parsed_injuries = []
        feeds = [
            ("RotoWire", "https://www.rotowire.com/rss/news.php?sport=NBA", "rotowire"),
            ("RealGM", "https://basketball.realgm.com/rss/wiretap/0/0.xml", "realgm"),
        ]

        for feed_name, feed_url, source_key in feeds:
            try:
                headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}
                r = requests.get(feed_url, headers=headers, timeout=10)
                if r.status_code != 200:
                    self._log(f"   ⚠️  {feed_name} RSS returned {r.status_code}")
                    continue

                feed = feedparser.parse(r.content)

                for entry in feed.entries:
                    title = entry.title if isinstance(entry.title, str) else str(entry.title)

                    if source_key == "rotowire":
                        parts = title.split(': ', 1)
                        player_name = parts[0].strip() if len(parts) > 1 else None
                        headline = parts[1] if len(parts) > 1 else title
                    else:
                        player_name = self._extract_player_from_realgm_title(title)
                        headline = title

                    if not player_name:
                        continue

                    # Validate extracted name against player_canonical_ids
                    # Rejects college players, coaches, and headline fragments
                    if canonical_names:
                        normalized_check = self._normalize_for_canonical(player_name)
                        if normalized_check not in canonical_names:
                            self._log(f"   ⚠️  RSS skip (not in roster): '{player_name}'")
                            continue

                    status = self._classify_rss_headline(f"{headline} {getattr(entry, 'description', '')}")
                    if status not in ('OUT', 'DOUBTFUL'):
                        continue

                    parsed_injuries.append({
                        'player_name': player_name,
                        'team_abbreviation': None,
                        'status': status,
                        'return_date': None,
                        'description': headline[:500],
                        'injury_type': self._parse_injury_type(headline),
                        'source': f'RSS_{feed_name.upper()}'
                    })

            except Exception as e:
                self._log(f"   ⚠️  {feed_name} RSS error: {e}")

        self._log(f"✅ RSS feeds: {len(parsed_injuries)} OUT/DOUBTFUL found")
        return {"success": True, "injuries": parsed_injuries, "errors": []}

    def sync_to_database(self, injury_data, skip_resolve=False):
        """
        Sync injury data to database with status-change detection.

        Args:
            injury_data: Output from fetch_injuries_* methods

        Returns:
            {
                "injuries_synced": int,
                "status_changes": int,
                "resolved": int,
                "errors": []
            }
        """
        if not injury_data["success"]:
            return {
                "injuries_synced": 0,
                "status_changes": 0,
                "resolved": 0,
                "errors": injury_data["errors"]
            }

        conn = self._get_conn()
        cursor = conn.cursor()

        injuries_synced = 0
        status_changes = 0
        resolved_count = 0
        errors = []
        snapshot_time = datetime.now().isoformat()

        active_player_names = {inj['player_name'] for inj in injury_data["injuries"]}
        all_db_players = self._get_active_players_from_db(conn)
        # Canonical lookup: normalized_name → (full_name, team) — accent+suffix safe
        canonical_lookup = self._get_canonical_lookup_from_db(conn)

        try:
            for injury in injury_data["injuries"]:
                player_name = injury['player_name']
                new_status = injury['status']
                return_date = injury.get('return_date')
                description = injury.get('description', '')
                injury_type = injury.get('injury_type')
                source = injury.get('source', 'Unknown')

                # Resolve team + canonical name via player_canonical_ids.normalized_name
                # This handles accented names (Nurkić→Nurkic) and suffixes (Jr./Sr./III).
                # Using .lower() only (old approach) silently failed for these cases.
                team_abbreviation = injury.get('team_abbreviation')
                normalized_input = self._normalize_for_canonical(player_name)
                canonical_match = canonical_lookup.get(normalized_input)

                if canonical_match:
                    canonical_full_name, canonical_team = canonical_match
                    # Always use the canonical full_name for consistent DB storage
                    player_name = canonical_full_name
                    active_player_names.discard(injury['player_name'])
                    active_player_names.add(player_name)
                    if not team_abbreviation:
                        team_abbreviation = canonical_team
                elif not team_abbreviation:
                    # Fallback: plain .lower() match against players table
                    for pname, team in all_db_players:
                        if pname.lower() == player_name.lower():
                            team_abbreviation = team
                            break

                injury['team_abbreviation'] = team_abbreviation

                last_injury = self._get_last_injury_record(conn, player_name)

                # ESPN PROTECTION: Use taxonomy and semantic distance for conflict resolution
                from utils.injury_taxonomy import INJURY_TAXONOMY, get_category, semantic_distance
                _espn_row = cursor.execute('''
                    SELECT status, snapshot_time FROM player_injuries
                    WHERE player_name = ? AND source = 'ESPN'
                      AND resolved_at IS NULL
                    ORDER BY snapshot_time DESC LIMIT 1
                ''', (player_name,)).fetchone()
                if _espn_row:
                    espn_status, espn_time_str = _espn_row
                    try:
                        espn_time = datetime.fromisoformat(espn_time_str.replace('Z', '+00:00'))
                        if espn_time.tzinfo: espn_time = espn_time.replace(tzinfo=None)
                        espn_age_hours = (datetime.now() - espn_time).total_seconds() / 3600
                    except (ValueError, TypeError, AttributeError) as e:
                        print(f"[sync_injuries] Failed to parse ESPN timestamp {espn_time_str!r}: {e}")
                        espn_age_hours = 0

                    espn_cat = get_category(espn_status)
                    new_cat = get_category(new_status)
                    espn_sev = INJURY_TAXONOMY.get(espn_status, {}).get('severity_score', 0)
                    new_sev = INJURY_TAXONOMY.get(new_status, {}).get('severity_score', 0)
                    dist = semantic_distance(espn_status, new_status)
                    
                    if espn_cat == new_cat:
                        # same-category conflict → recency tiebreaker
                        if espn_age_hours < 2:
                            self._log(f"  🛡️  ESPN PROTECTION (recency): {player_name} kept as {espn_status} (new: {new_status})")
                            continue
                    else:
                        # cross-category conflict → keep harder status unless other is 2h+ fresher
                        if espn_sev > new_sev and espn_age_hours < 2:
                            self._log(f"  🛡️  ESPN PROTECTION (cross-cat, dist {dist}): {player_name} kept as {espn_status} (new: {new_status})")
                            continue

                should_insert = False
                onset_date = None

                if last_injury:
                    if last_injury['status'] != new_status:
                        should_insert = True
                        status_changes += 1
                        self._log(f"  🔄 Status change: {player_name}: {last_injury['status']} -> {new_status}")
                else:
                    should_insert = True

                if should_insert and new_status != 'ACTIVE':
                    onset_date = datetime.now().strftime('%Y-%m-%d')

                if should_insert and not self.dry_run:
                    # Dedup guard: skip if same player already recorded today (any status)
                    # Prevents the Naji Marshall 7-row problem from recurring
                    # Note: removed status= from WHERE to catch same-player/different-injury-type duplicates
                    _existing = cursor.execute('''
                        SELECT id FROM player_injuries
                        WHERE player_name = ? AND DATE(snapshot_time) = DATE('now')
                          AND resolved_at IS NULL
                        LIMIT 1
                    ''', (player_name,)).fetchone()
                    if _existing:
                        self._log(f"  ⏭️  Dedup skip: {player_name} already recorded today")
                        should_insert = False

                if should_insert and not self.dry_run:
                    try:
                        cursor.execute('''
                            INSERT INTO player_injuries (
                                player_name, team_abbreviation, status, injury_type,
                                return_date, days_out, onset_date, description, source,
                                snapshot_time, is_game_day_report, resolved_at
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL)
                        ''', (
                            player_name,
                            injury.get('team_abbreviation'),
                            new_status,
                            injury_type,
                            return_date,
                            self._calculate_days_out(return_date, onset_date),
                            onset_date,
                            description,
                            source,
                            snapshot_time,
                            1 if self.is_game_day_report else 0
                        ))
                        injuries_synced += 1
                    except sqlite3.Error as e:
                        errors.append(f"Insert error for {player_name}: {e}")

                if not self.dry_run:
                    # Update players table — match by canonical full_name (already normalized above)
                    cursor.execute('''
                        UPDATE players SET
                            current_injury_status = ?,
                            injury_updated_at = ?,
                            injury_return_date = ?,
                            days_out_current = ?
                        WHERE LOWER(name) = LOWER(?)
                    ''', (
                        new_status,
                        snapshot_time,
                        return_date,
                        self._calculate_days_out(return_date, onset_date),
                        player_name
                    ))

            # skip_resolve=True when called for supplementary data (e.g. RSS-only additions)
            # to avoid wiping injuries that were synced in the primary BDL/Tank01 pass.
            # IMPORTANT: Only resolve BDL/Tank01/RSS-sourced entries — never touch ESPN records.
            # ESPN has its own resolve logic in sync_injuries_espn.py (source-scoped).
            # Without this filter, BDL sync would resolve ESPN-sourced injuries when BDL
            # hasn't caught up yet (e.g. JJJ injury: ESPN=OUT, BDL=not listed yet → wipes ESPN entry).
            if not skip_resolve:
                resolved_cursor = conn.cursor()
                resolved_cursor.execute('''
                    SELECT DISTINCT player_name
                    FROM player_injuries
                    WHERE resolved_at IS NULL
                      AND source NOT IN ('ESPN', 'espn_suspension')
                ''')
                currently_injured = {row[0] for row in resolved_cursor.fetchall()}

                players_no_longer_injured = currently_injured - active_player_names

                for player_name in players_no_longer_injured:
                    if not self.dry_run:
                        resolved_cursor.execute('''
                            UPDATE player_injuries
                            SET resolved_at = ?
                            WHERE player_name = ? AND resolved_at IS NULL
                        ''', (snapshot_time, player_name))

                        resolved_cursor.execute('''
                            UPDATE players SET
                                current_injury_status = 'ACTIVE',
                                injury_updated_at = ?,
                                injury_return_date = NULL,
                                days_out_current = 0
                            WHERE LOWER(name) = LOWER(?)
                        ''', (snapshot_time, player_name))

                        if resolved_cursor.rowcount > 0:
                            resolved_count += 1
                            self._log(f"  ✅ Resolved: {player_name}")
                    else:
                        resolved_count += 1
                        self._log(f"  [DRY RUN] Would resolve: {player_name}")

            if not self.dry_run:
                conn.commit()

        except Exception as e:
            conn.rollback()
            errors.append(f"Database error: {str(e)}")

        finally:
            conn.close()

        return {
            "injuries_synced": injuries_synced,
            "status_changes": status_changes,
            "resolved": resolved_count,
            "errors": errors
        }


def _get_stale_threshold_minutes():
    """
    Time-of-day threshold for considering DB injury data stale.
    Matches the intraday refresh schedule in injury_refresh.yml.
    """
    hour = datetime.now().hour
    if 18 <= hour < 23:   # 6 PM - 11 PM: game time — refresh every 20 min
        return 20
    elif 11 <= hour < 18: # 11 AM - 6 PM: daytime — refresh every 2 hrs
        return 120
    else:                  # overnight (11 PM - 11 AM): only scheduled 5 AM run matters
        return 480


def _is_db_fresh(db_path='ludi.db'):
    """
    Returns True if player_injuries was synced within the current stale threshold.
    Prevents redundant Tank01/BDL API calls when data is already current.
    """
    threshold = _get_stale_threshold_minutes()
    try:
        conn = sqlite3.connect(db_path, timeout=10)
        row = conn.execute(
            "SELECT MAX(snapshot_time) FROM player_injuries"
        ).fetchone()
        conn.close()
        if not row or not row[0]:
            return False
        last = datetime.fromisoformat(row[0])
        age_minutes = (datetime.now() - last).total_seconds() / 60
        return age_minutes < threshold
    except Exception:
        return False


def main():
    parser = argparse.ArgumentParser(description="Sync NBA injuries to database")
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing")
    parser.add_argument("--verbose", action="store_true", help="Enable debug output")
    parser.add_argument("--force", action="store_true",
                        help="Force sync even if DB is already fresh (bypass staleness check)")

    args = parser.parse_args()

    # Staleness guard: skip if DB was synced recently — unless --force is passed.
    # This lets the workflow run frequently (every 20 min during game time)
    # without hammering Tank01/BDL quota when data is already current.
    if not args.force and not args.dry_run and _is_db_fresh():
        threshold = _get_stale_threshold_minutes()
        print(f"✅ Injury data is fresh (< {threshold} min old). Skipping sync.")
        print("   Pass --force to override.")
        sys.exit(0)

    syncer = InjurySync(verbose=args.verbose, dry_run=args.dry_run)

    print("🏥 Injury Sync")
    print("=" * 50)

    if args.dry_run:
        print("⚠️  DRY RUN MODE - No changes will be saved")
        print()

    print(f"Game Day Report: {syncer.is_game_day_report}")
    print()

    print("Step 1: Fetching from BDL (primary)...")
    injury_data = syncer.fetch_injuries_bdl()

    if not injury_data["success"]:
        print(f"⚠️  BDL fetch failed: {injury_data['errors']}")
        print()
        print("Step 2: Trying Tank01 (fallback)...")
        injury_data = syncer.fetch_injuries_tank01()

        if not injury_data["success"]:
            print(f"⚠️  Tank01 fetch also failed: {injury_data['errors']}")
            print()
            print("⚠️  WARNING: Both BDL and Tank01 failed. Exiting gracefully.")
            print("   This is not a critical failure - workflow should continue.")
            sys.exit(0)
    else:
        print(f"✅ BDL fetch successful: {len(injury_data['injuries'])} injuries")
        print()

        print("Step 2: Checking Tank01 for additional data...")
        tank01_data = syncer.fetch_injuries_tank01()

        if tank01_data["success"]:
            tank01_names = {inj['player_name'] for inj in tank01_data["injuries"]}
            bdl_names = {inj['player_name'] for inj in injury_data["injuries"]}
            new_from_tank01 = tank01_names - bdl_names

            if new_from_tank01:
                print(f"   Found {len(new_from_tank01)} additional injuries from Tank01")
                for inj in tank01_data["injuries"]:
                    if inj['player_name'] in new_from_tank01:
                        injury_data["injuries"].append(inj)
            else:
                print("   No additional injuries from Tank01")
        print()

    print("Step 3: Syncing to database...")
    result = syncer.sync_to_database(injury_data)

    if result["errors"]:
        print(f"⚠️  Encountered {len(result['errors'])} errors:")
        for error in result["errors"][:5]:
            print(f"   - {error}")

    print()
    print("📊 Sync Results")
    print("=" * 50)
    print(f"Injuries synced: {result['injuries_synced']}")
    print(f"Status changes: {result['status_changes']}")
    print(f"Resolved: {result['resolved']}")
    print()

    print("Step 4: Enriching from RSS feeds (RotoWire + RealGM)...")
    rss_data = syncer.fetch_injuries_rss()
    if rss_data["success"] and rss_data["injuries"]:
        existing_names = {inj['player_name'].lower() for inj in injury_data["injuries"]}
        new_from_rss = [
            i for i in rss_data["injuries"]
            if i['player_name'].lower() not in existing_names
        ]
        if new_from_rss:
            print(f"   📰 {len(new_from_rss)} new OUT/DOUBTFUL from RSS → writing to DB")
            rss_result = syncer.sync_to_database({"success": True, "injuries": new_from_rss, "errors": []}, skip_resolve=True)
            print(f"   Synced: {rss_result['injuries_synced']} | Changes: {rss_result['status_changes']}")
        else:
            print("   No additional injuries from RSS feeds")
    print()

    print("Step 5: Auto-promoting RSS-discovered players to canonical IDs...")
    promoted = auto_promote_staging_to_canonical(syncer)
    if promoted:
        print(f"   ✅ Promoted {promoted} players from staging to canonical IDs")
    else:
        print("   No players eligible for auto-promotion (need 3+ consistent appearances)")
    print()

    if args.dry_run:
        print("\n⚠️  DRY RUN - No changes saved to database")

    print()
    print("Step 6: Auto-resolving ghost injuries (players active in last 3 days)...")
    syncer = InjurySync(verbose=args.verbose, dry_run=args.dry_run)
    _auto_resolve_active_players(syncer._get_conn())

    print()
    print("✅ Sync complete!")


def auto_promote_staging_to_canonical(syncer) -> int:
    """
    Auto-promote players from player_news_staging to player_canonical_ids.
    
    Criteria:
    - seen_count >= 3 (3+ consistent appearances)
    - team_abbreviation is not NULL
    - Not already in player_canonical_ids
    
    Returns: count of promoted players
    """
    try:
        conn = syncer._get_conn()
        cursor = conn.cursor()
        
        # Find players eligible for promotion
        cursor.execute('''
            SELECT player_name, team_abbreviation, status_extracted
            FROM player_news_staging
            WHERE seen_count >= 3
              AND team_abbreviation IS NOT NULL
              AND team_abbreviation != ''
              AND is_reviewed = 0
              AND NOT EXISTS (
                  SELECT 1 FROM player_canonical_ids 
                  WHERE LOWER(full_name) = LOWER(player_news_staging.player_name)
              )
            GROUP BY player_name, team_abbreviation
            HAVING COUNT(DISTINCT source) >= 1
        ''')
        
        eligible = cursor.fetchall()
        
        if not eligible:
            return 0
        
        promoted = 0
        now = datetime.now().isoformat()
        
        for row in eligible:
            player_name, team_abbr, status = row
            
            # Generate a staging canonical_id
            import time
            staging_id = f"staging_{int(time.time())}_{player_name.replace(' ', '_').lower()}"
            
            # Insert into canonical_ids
            cursor.execute('''
                INSERT INTO player_canonical_ids (
                    canonical_id, full_name, normalized_name, team, position, is_active, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, 1, ?, ?)
            ''', (
                staging_id,
                player_name,
                player_name.lower(),
                team_abbr,
                '',  # position unknown
                now,
                now
            ))
            
            # Mark as reviewed in staging
            cursor.execute('''
                UPDATE player_news_staging
                SET is_reviewed = 1, last_seen_at = ?
                WHERE player_name = ? AND is_reviewed = 0
            ''', (now, player_name))
            
            promoted += 1
        
        conn.commit()
        return promoted
        
    except Exception as e:
        print(f"   ⚠️ Auto-promotion error: {e}")
        return 0


def _auto_resolve_active_players(conn):
    """Auto-resolve injuries where player logged 10+ min in last 3 game days.
    Called at end of sync_injuries() to fix ghost injuries from stale Tank01 data."""
    try:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE player_injuries
            SET resolved_at = datetime('now')
            WHERE resolved_at IS NULL
              AND status NOT IN ('ACTIVE', 'PROBABLE')
              AND LOWER(player_name) IN (
                  SELECT LOWER(player_name)
                  FROM player_game_logs
                  WHERE game_date >= date('now', '-3 days')
                    AND minutes >= 10
              )
        """)
        count = cursor.rowcount
        if count > 0:
            print(f"   [INJURIES] Auto-resolved {count} ghost injuries (active in last 3 days)")
        conn.commit()
    except Exception as e:
        print(f"   ⚠️ Auto-resolve error: {e}")


if __name__ == "__main__":
    main()
