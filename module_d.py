import requests
import json
import os
import sqlite3
import time
import re
from datetime import datetime, timedelta
from duckduckgo_search import DDGS
import unidecode
import config
import feedparser
import pytz

# [NEW] Team mapping for RSS team extraction
from utils.mappings import TEAM_MAP, normalize_bdl_abbr


# [PAID TIER] Import monitoring and retry utilities
from utils.api_monitor import get_monitor

# [NEW] BallDontLie Client
from utils.bdl_client import BDLClient

# [Tank01] Player ID Resolution
from utils.player_id_resolver import PlayerIDResolver

# [PHASE 8] Claude Haiku for injury blurb parsing
from utils.claude_client import get_claude_analysis, HAIKU_MODEL
from utils.claude_prompts import INJURY_BLURB_SYSTEM, INJURY_BLURB_PARSE_PROMPT
from utils.injury_taxonomy import get_category
from utils.slack_notifier import send_slack_failure_alert

# ==========================================
# LUDI INFORMATIO | MODULE D: THE YAK
# V3.5 - FULL STATUS SPECTRUM (2025-26)
# ==========================================

INJURY_STALENESS_DAYS = 14  # Injuries older than this assumed resolved or season-ending

class LudiYak:
    def __init__(self):
        print(f"\n{'='*40}")
        print(f"LUDI INFORMATIO: MODULE D (YAK V3.5) ONLINE")
        print(f"   >>> 15-MIN SYNC | PROBABLE & AVAILABLE ACTIVE")
        print(f"{'='*40}")

        self.TANK_KEY = getattr(config, 'TANK01_KEY', '')
        self.TANK_HOST = "tank01-fantasy-stats.p.rapidapi.com"
        self.cache_file = "yak_cache.json"
        self.cache = self._load_cache()

        self.official_injuries = {}
        self.last_official_refresh = None
        
        # [PHASE 2] RotoWire RSS Config
        self.rss_url = "https://www.rotowire.com/rss/news.php?sport=NBA"
        self.rss_cache = []
        self.last_rss_refresh = None

        # [PHASE 2.5] RealGM RSS Config
        self.realgm_url = "https://basketball.realgm.com/rss/wiretap/0/0.xml"
        self.realgm_cache = []
        self.last_realgm_refresh = None

        # [PAID TIER] Initialize API Monitor
        self.monitor = get_monitor()
        
        # [NEW] Initialize BDL Client
        self.bdl = BDLClient()
        
        # [Tank01] Player ID Resolver
        self._id_resolver = PlayerIDResolver()
        
        # [PHASE 3] Load Keyword Taxonomy
        self.keywords_config = self._load_keyword_config()

        # [PHASE 8] Load Injury Taxonomy (get_category imported at module level above)
        try:
            from utils.injury_taxonomy import INJURY_TAXONOMY, INJURY_LANGUAGE_MAP
            self._taxonomy = INJURY_TAXONOMY
            self._language_map = INJURY_LANGUAGE_MAP
        except ImportError:
            self._taxonomy = {}
            self._language_map = []

        # [RSS] Canonical player name set for validation (lazy-loaded on first RealGM fetch)
        self._canonical_names = None

        # [CACHE] Per-run Haiku parse cache — keyed by (player_name, text_prefix).
        # temperature=0.0 makes Haiku deterministic: same input → same output every time.
        # Prevents redundant Haiku calls when _ai_parse_blurb + _parse_with_taxonomy_injection
        # fire for the same player in the same pipeline run.
        self._haiku_parse_cache: dict = {}


    def _load_cache(self):
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"   [YAK] ⚠️ Cache load error: {e}")
                return {}
        return {}

    def _load_keyword_config(self):
        """[PHASE 3] Load external keyword taxonomy."""
        config_path = "config/yak_keywords.json"
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"   [YAK] ⚠️ Kw Config Error: {e}")
        return {} # Fallback if missing

    def _extract_team_from_blurb(self, headline: str, description: str = '') -> str:
        """
        Extract team abbreviation from RSS blurbs for players not in canonical IDs.
        Uses pattern matching to find team names in headlines like:
        - "Lakers vs. Celtics: Tyler Herro questionable"
        - "@ Warriors: Player OUT"
        - "for the Heat"
        """
        full_text = f"{headline} {description}".lower()
        
        # Team name patterns to search for
        team_patterns = [
            r'vs\.?\s+([a-z][a-z\s]+)',      # vs. lakers, vs. celtics
            r'@\s+([a-z][a-z\s]+)',           # @ warriors
            r'against\s+the\s+([a-z][a-z\s]+)',  # against the heat
            r'for\s+the\s+([a-z][a-z\s]+)',   # for the heat
            r'([a-z]+)\s+vs',                 # lakers vs
            r'([a-z]+)\s+@',                 # lakers @
        ]
        
        for pattern in team_patterns:
            match = re.search(pattern, full_text)
            if match:
                team_name = match.group(1).strip()
                # Try to resolve via TEAM_MAP
                for full_name, abbr in TEAM_MAP.items():
                    if team_name in full_name.lower() or full_name.lower() in team_name:
                        return abbr
        
        # Direct team abbreviation patterns (common short forms)
        team_abbrs = ['LAL', 'LAC', 'GSW', 'BOS', 'NYK', 'NOP', 'PHX', 'SAS', 'CHI', 'CLE', 
                      'DAL', 'DEN', 'DET', 'HOU', 'IND', 'MEM', 'MIA', 'MIL', 'MIN', 'OKC', 
                      'ORL', 'PHI', 'POR', 'SAC', 'TOR', 'UTA', 'WAS', 'ATL', 'CHA', 'BKN']
        for abbr in team_abbrs:
            if abbr.lower() in full_text:
                return abbr
        
        return ''

    def _upsert_news_staging(self, player_name: str, team_abbreviation: str, source: str,
                            headline: str, description: str, status_extracted: str, 
                            confidence: float, conn=None) -> None:
        """
        Insert or update player_news_staging table for players discovered via RSS.
        Tracks rookies, two-ways, and call-ups not yet in canonical IDs.
        
        Args:
            conn: Optional sqlite3 connection. If provided, uses it instead of opening
                  a new connection. Caller is responsible for closing it.
        """
        _close = False
        try:
            if conn is None:
                db_path = getattr(config, 'DB_PATH', 'ludi.db')
                conn = sqlite3.connect(db_path)
                _close = True
            cursor = conn.cursor()
            
            now = datetime.now().isoformat()
            today = datetime.now().strftime('%Y-%m-%d')
            
            # Check for existing entry today
            cursor.execute('''
                SELECT id, seen_count, last_seen_at 
                FROM player_news_staging 
                WHERE player_name = ? AND source = ?
            ''', (player_name, source))
            
            existing = cursor.fetchone()
            
            if existing:
                # Update existing record - increment seen_count
                cursor.execute('''
                    UPDATE player_news_staging
                    SET last_seen_at = ?,
                        seen_count = seen_count + 1,
                        headline = ?,
                        description = ?,
                        status_extracted = ?,
                        confidence = ?
                    WHERE player_name = ? AND source = ?
                ''', (now, headline, description, status_extracted, confidence, player_name, source))
            else:
                # Insert new record
                cursor.execute('''
                    INSERT INTO player_news_staging 
                    (player_name, team_abbreviation, source, headline, description, 
                     status_extracted, confidence, first_seen_at, last_seen_at, seen_count)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
                ''', (player_name, team_abbreviation, source, headline, description,
                      status_extracted, confidence, now, now))
            
            conn.commit()
        except Exception as e:
            # Silent fail - don't break pipeline for staging issues
            print(f"[YAK] ⚠️   Staging error for {player_name}: {e}")
        finally:
            if _close and conn:
                conn.close()

    def refresh_official_injuries(self):
        """Syncs with the NBA's 15-minute reporting cycle."""
        if self.last_official_refresh:
            elapsed = datetime.now() - self.last_official_refresh
            if elapsed < timedelta(minutes=15):
                return True

        # PRIMARY SOURCE: Tank01
        tank_success = False
        try:
            url = f"https://{self.TANK_HOST}/getNBAInjuryList"
            headers = {"X-RapidAPI-Key": self.TANK_KEY, "X-RapidAPI-Host": self.TANK_HOST}
            
            r = requests.get(url, headers=headers, timeout=10)
            self.monitor.log_request('tank01', 'injury_list', r.headers)
            r.raise_for_status()
            data = r.json()

            if r.status_code == 200 and 'body' in data:
                self.official_injuries = {}
                self._injury_blurbs = {}
                for item in data['body']:
                    pid = item.get('playerID', '')
                    team_abv = item.get('teamAbv', '')  # Extract team from API
                    if not pid:
                        continue

                    # Try canonical ID resolution first
                    p_name = ''
                    resolved_team = ''
                    try:
                        info = self._id_resolver.get_player_info(pid)
                        p_name = info.get('full_name', '')
                        resolved_team = info.get('team', '')  # Get team from canonical
                    except (ValueError, KeyError):
                        # Fallback: try to extract name from description
                        desc = item.get('description', '')
                        import re
                        match = re.search(r':\s*(\w[\w\s\'-]+?)\s*\(', desc)
                        p_name = match.group(1).strip() if match else ''

                    if not p_name:
                        continue

                    # Use resolved team from canonical, or fall back to API teamAbv
                    final_team = resolved_team if resolved_team else team_abv

                    clean_name = unidecode.unidecode(p_name).replace('.', '').replace(' ', '').lower()
                    designation = item.get('designation', 'Available')
                    description = item.get('description', '')
                    # injReturnDate format: YYYYMMDD — convert to YYYY-MM-DD for readability
                    raw_ret = item.get('injReturnDate', '')
                    inj_return_date = f"{raw_ret[:4]}-{raw_ret[4:6]}-{raw_ret[6:]}" if len(raw_ret) == 8 else ''

                    self.official_injuries[clean_name] = designation
                    self._injury_blurbs[clean_name] = {
                        'description': description,
                        'inj_return_date': inj_return_date,
                        'team': final_team,  # Store team for schedule context
                    }
                
                tank_success = True
                self.last_official_refresh = datetime.now()
                print(f"   [YAK] 📋 Heartbeat: NBA Official Feed Synced (Tank01).")

        except Exception as e:
            print(f"   [YAK] ⚠️ Tank01 Sync Failed: {e}")
            self.monitor.log_failed_request('tank01', 'injury_list', str(e))
            send_slack_failure_alert(
                "Module D: Tank01 injury sync failed",
                f"Error: {e}\nFalling back to BallDontLie. If BDL also fails, injury data will be stale."
            )

        # FALLBACK SOURCE: BallDontLie
        if not tank_success:
            return self._refresh_injuries_bdl()

        return tank_success

    def _refresh_injuries_bdl(self):
        """BDL fallback for injury data with proper status mapping."""
        print(f"   [YAK] 🔄 Attempting Fallback: BallDontLie...")
        try:
            if not self.bdl.api_key:
                print("   [YAK] ❌ No BDL Key found. Aborting fallback.")
                return False

            injuries = self.bdl.get_active_injuries()

            if not injuries:
                print("   [YAK] ⚠️ BallDontLie returned 0 injuries.")
                return False

            # BDL status -> Ludi status mapping
            status_map = {
                'Out': 'Out',
                'Day-To-Day': 'Questionable',
                'Questionable': 'Questionable',
                'Doubtful': 'Doubtful',
                'Probable': 'Probable',
            }

            self.official_injuries = {}
            self._injury_blurbs = {}
            count = 0
            for item in injuries:
                player = item.get('player', {})
                p_name = f"{player.get('first_name', '')} {player.get('last_name', '')}".strip()
                if not p_name:
                    continue

                clean_name = unidecode.unidecode(p_name).replace('.', '').replace(' ', '').lower()
                bdl_status = item.get('status', 'Out')
                description = item.get('description', '')
                
                # Extract injury_type from description
                injury_type = ''
                if description:
                    type_match = re.search(r'\(([^)]+)\)', description)
                    if type_match:
                        injury_type = type_match.group(1).strip()
                
                # Extract return_date if available
                return_date = item.get('return_date', '')

                self.official_injuries[clean_name] = status_map.get(bdl_status, 'Out')
                self._injury_blurbs[clean_name] = {
                    'description': description,
                    'inj_return_date': return_date,
                    'injury_type': injury_type,
                }
                count += 1

            self.last_official_refresh = datetime.now()
            print(f"   [YAK] ✅ Fallback Successful: {count} injuries loaded from BallDontLie.")
            return True

        except Exception as e:
            print(f"   [YAK] ❌ Fallback Failed: {e}")
            send_slack_failure_alert(
                "Module D: BOTH injury sources failed (Tank01 + BDL)",
                f"BDL fallback error: {e}\nInjury data is now stale. Pipeline will run without current injury status — manual review required."
            )
            return False

    def classify_headline(self, text):
        """[PHASE 3] Classify news text using taxonomy."""
        text_lower = text.lower()
        
        best_match = None
        highest_conf = 0.0
        
        categories = self.keywords_config.get('categories', {})
        
        for cat_name, cat_data in categories.items():
            # Skip FILTER categories (like PERFORMANCE)
            if cat_data.get('filter') == 'SKIP':
                # Check if it matches skip keywords, if so return None
                if any(k in text_lower for k in cat_data['keywords']):
                    return None
                continue

            for kw in cat_data['keywords']:
                if kw in text_lower:
                    if cat_data['confidence'] > highest_conf:
                        highest_conf = cat_data['confidence']
                        best_match = {
                            'status': cat_data.get('status', 'VERIFY'),
                            'category': cat_name,
                            'confidence': cat_data['confidence']
                        }
        
        return best_match

    def get_refresh_interval(self):
        """
        [PHASE 2] Dynamic Refresh Rate based on EST Time:
        - 11:00 AM - 5:59 PM EST -> 120 minutes (2 hrs — injury_refresh.yml fires 4x/day)
        - 6:00 PM - 11:59 PM EST -> 20 minutes (Game Time — injury_refresh.yml fires every 20 min)
        - 12:00 AM - 10:59 AM EST -> 30 minutes (Off Hours)
        """
        est = pytz.timezone('US/Eastern')
        now = datetime.now(est)
        
        # Late Night / Morning (12 AM - 10:59 AM)
        if 0 <= now.hour < 11:
            return 30
        # Day (11 AM - 5:59 PM) — DB refreshed every 2 hrs by injury_refresh.yml
        elif 11 <= now.hour < 18:
            return 120
        # Game Time (6 PM - 11:59 PM) — DB refreshed every 20 min
        else:
            return 20

    def refresh_rotowire_rss(self):
        """[PHASE 2] Fetch RotoWire RSS Feed with dynamic cache."""
        interval = self.get_refresh_interval()
        
        if self.last_rss_refresh:
            elapsed = datetime.now() - self.last_rss_refresh
            if elapsed < timedelta(minutes=interval):
                return self.rss_cache
        
        try:
            # RSS Fetch (Using requests to handle SSL/Headers better than feedparser default)
            headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}
            r = requests.get(self.rss_url, headers=headers, timeout=10)
            
            if r.status_code != 200:
                print(f"   [YAK] ⚠️ RSS Fetch Fail: {r.status_code}")
                return self.rss_cache

            feed = feedparser.parse(r.content)
            new_cache = []
            
            for entry in feed.entries:
                # Parse "Player Name: Headline" format (handle both string and dict)
                entry_title = entry.title if isinstance(entry.title, str) else str(entry.title)
                title_parts = entry_title.split(': ', 1)
                player_name = title_parts[0] if len(title_parts) > 1 else entry_title
                headline = title_parts[1] if len(title_parts) > 1 else ""
                
                new_cache.append({
                    'player_name': player_name,
                    'headline': headline,
                    'description': getattr(entry, 'description', ''),
                    'pub_date': getattr(entry, 'published', ''),
                    'link': getattr(entry, 'link', '')
                })
            
            self.rss_cache = new_cache
            self.last_rss_refresh = datetime.now()
            # print(f"   [YAK] 📡 RotoWire RSS Synced ({len(new_cache)} items) | Next: {interval}m")
            return self.rss_cache
            
        except Exception as e:
            print(f"   [YAK] ⚠️ RSS Sync Error: {e}")
            return self.rss_cache # Return stale cache on error

    def get_rotowire_intel(self, player_name):
        """[PHASE 2] Check RotoWire for recent player news."""
        self.refresh_rotowire_rss()
        clean_query = player_name.lower().strip()
        
        for item in self.rss_cache:
            if clean_query in item['player_name'].lower():
                # [PHASE 3] Enhanced Classification
                full_text = f"{item['headline']} {item['description']}"
                classification = self.classify_headline(full_text)
                
                if classification:
                    # Check if player is in canonical IDs - if not, upsert to staging
                    canonical = self._load_canonical_names()
                    if canonical:
                        import unicodedata
                        nfd = unicodedata.normalize('NFD', player_name)
                        normalized = ''.join(c for c in nfd if unicodedata.category(c) != 'Mn')
                        
                        if normalized.lower() not in canonical:
                            # Player not in canonical IDs - extract team and stage
                            extracted_team = self._extract_team_from_blurb(
                                item['headline'], item['description']
                            )
                            self._upsert_news_staging(
                                player_name=player_name,
                                team_abbreviation=extracted_team,
                                source='RotoWire',
                                headline=item['headline'],
                                description=item.get('description', ''),
                                status_extracted=classification['status'],
                                confidence=classification['confidence']
                            )
                    
                    return {
                        'status': classification['status'],
                        'note': f"[ROTO] {item['headline']}",
                        'confidence': classification['confidence'],
                        'category': classification['category']
                    }
                    
        return None

    def _load_canonical_names(self):
        """Lazy-load canonical player name set for RSS validation.
        Prevents college players and non-NBA names from polluting cache."""
        if self._canonical_names is not None:
            return self._canonical_names
        try:
            db_path = getattr(config, 'DB_PATH', 'ludi.db')
            _conn = sqlite3.connect(db_path, timeout=5)
            self._canonical_names = {r[0] for r in _conn.execute(
                "SELECT normalized_name FROM player_canonical_ids WHERE is_active = 1"
            ).fetchall()}
            _conn.close()
        except Exception as e:
            print(f"   >>> [Yak] Canonical names load failed — name matching degraded: {e}")
            self._canonical_names = set()
        return self._canonical_names

    def _extract_realgm_player_name(self, title):
        """Extract player name from free-form RealGM article headline.
        Mirrors sync_injuries.py._extract_player_from_realgm_title() with expanded verb list.
        Returns None for articles where a player is not the subject (team news, stats, etc.)."""
        TEAM_WORDS = {
            'cavaliers','warriors','lakers','celtics','nets','knicks','76ers',
            'raptors','bulls','bucks','pacers','pistons','wizards','hornets',
            'heat','magic','hawks','spurs','suns','nuggets','thunder','trail',
            'blazers','jazz','clippers','kings','timberwolves','grizzlies',
            'mavericks','pelicans','rockets','nba','report','sources',
            'chicago','boston','golden','new','los','san','oklahoma','portland',
            'minnesota','memphis','dallas','denver','houston','indiana','detroit',
            'washington','charlotte','miami','orlando','atlanta',
        }
        first_word = title.split()[0].lower().rstrip(',') if title.split() else ''
        if first_word in TEAM_WORDS:
            return None

        ACTION_WORDS = [
            ' Out ', ' Will ', ' Is ', ' Has ', ' To ', " Won't ",
            ' Not ', ' Returns ', ' Ruled ', ' Expected ', ' Listed ',
            ' Leaves ', ' Underwent ', ' Undergo ', ' Undergoes ',
            ' Suffered ', ' Suffers ', ' Diagnosed ', ' Shut ',
            ' Plans ', ' Pushes ', ' Misses ', ' Missing ',
        ]
        name_part = title
        for verb in ACTION_WORDS:
            if verb in title:
                name_part = title[:title.index(verb)].strip()
                break

        words = name_part.split()
        if 2 <= len(words) <= 4 and ',' not in name_part:
            # Validate against canonical IDs — reject non-NBA players
            canonical = self._load_canonical_names()
            if canonical:
                import unicodedata, re as _re
                nfd = unicodedata.normalize('NFD', name_part)
                normalized = ''.join(c for c in nfd if unicodedata.category(c) != 'Mn')
                normalized = _re.sub(r'\s+(jr|sr|ii|iii|iv)\.?\s*$', '', normalized.lower().strip())
                if normalized not in canonical:
                    return None
            return name_part
        return None

    def refresh_realgm_rss(self):
        """[PHASE 2.5] Fetch RealGM RSS Feed with dynamic cache.
        Updated Feb 24, 2026 — now extracts player names properly instead of
        storing full article titles as player_name."""
        interval = self.get_refresh_interval()

        if self.last_realgm_refresh:
            elapsed = datetime.now() - self.last_realgm_refresh
            if elapsed < timedelta(minutes=interval):
                return self.realgm_cache

        try:
            headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}
            r = requests.get(self.realgm_url, headers=headers, timeout=10)

            if r.status_code != 200:
                print(f"   [YAK] ⚠️ RealGM RSS Fetch Fail: {r.status_code}")
                return self.realgm_cache

            feed = feedparser.parse(r.content)
            new_cache = []

            for entry in feed.entries:
                entry_title = entry.title if isinstance(entry.title, str) else str(entry.title)
                # Extract player name — skip articles where no valid NBA player is the subject
                extracted_name = self._extract_realgm_player_name(entry_title)
                if not extracted_name:
                    continue

                new_cache.append({
                    'player_name': extracted_name,   # clean player name (not full title)
                    'headline': entry_title,          # full title preserved for classification
                    'description': getattr(entry, 'description', ''),
                    'pub_date': getattr(entry, 'published', ''),
                    'link': getattr(entry, 'link', '')
                })

            self.realgm_cache = new_cache
            self.last_realgm_refresh = datetime.now()
            # print(f"   [YAK] 📡 RealGM RSS Synced ({len(new_cache)} injury-relevant items)")
            return self.realgm_cache

        except Exception as e:
            print(f"   [YAK] ⚠️ RealGM RSS Sync Error: {e}")
            return self.realgm_cache

    def get_realgm_intel(self, player_name):
        """[PHASE 2.5] Check RealGM for recent player news."""
        try:
            self.refresh_realgm_rss()
            clean_query = player_name.lower().strip()
            
            for item in self.realgm_cache:
                if clean_query in item['player_name'].lower():
                    full_text = f"{item['headline']} {item['description']}"
                    classification = self.classify_headline(full_text)
                    
                    if classification:
                        # Check if player is in canonical IDs - if not, upsert to staging
                        canonical = self._load_canonical_names()
                        if canonical:
                            import unicodedata
                            nfd = unicodedata.normalize('NFD', player_name)
                            normalized = ''.join(c for c in nfd if unicodedata.category(c) != 'Mn')
                            
                            if normalized.lower() not in canonical:
                                # Player not in canonical IDs - extract team and stage
                                extracted_team = self._extract_team_from_blurb(
                                    item['headline'], item.get('description', '')
                                )
                                self._upsert_news_staging(
                                    player_name=player_name,
                                    team_abbreviation=extracted_team,
                                    source='RealGM',
                                    headline=item['headline'],
                                    description=item.get('description', ''),
                                    status_extracted=classification['status'],
                                    confidence=classification['confidence']
                                )
                        
                        return {
                            'status': classification['status'],
                            'note': f"[REALGM] {item['headline']}",
                            'confidence': classification['confidence'],
                            'category': classification['category']
                        }
                        
            return None
        except Exception as e:
            print(f"   [YAK] ⚠️ RealGM Intel Error: {e}")
            return None

    def _save_cache(self):
        """Persist self.cache to yak_cache.json for cross-run durability."""
        try:
            with open(self.cache_file, 'w') as f:
                json.dump(self.cache, f)
        except Exception as e:
            print(f"   [YAK] ⚠️ Cache save error: {e}")

    def search_news(self, query):
        # In-memory cache check (20-min TTL) — prevents repeat API calls within same pipeline run
        if query in self.cache:
            entry = self.cache[query]
            try:
                if datetime.now() - datetime.fromisoformat(entry['timestamp']) < timedelta(minutes=20):
                    return entry['data']
            except Exception:
                pass

        result = {"items": []}

        if getattr(config, 'PERPLEXITY_API_KEY', None):
            try:
                from utils.perplexity_client import PerplexityClient
                perp = PerplexityClient()
                text = perp._query(query)
                if text:
                    result = {"items": [{"snippet": text, "link": "perplexity.ai"}]}
            except Exception as e:
                print(f"   [YAK] Perplexity failed, falling back to DuckDuckGo: {e}")

        if not result["items"]:
            # NOTE: DuckDuckGo is rate-limited and IP-blocked in CI. Perplexity (Phase 8.7) is primary.
            # DDGS remains as emergency fallback only when PERPLEXITY_API_KEY is not configured.
            try:
                results = DDGS().text(query, max_results=3, timelimit="w")
                result = {"items": [{"snippet": r['body'], "link": r['href']} for r in results]}
            except Exception as e:
                print(f"   [YAK] ⚠️ Search error for '{query}': {e}")

        # Cache the result (in-memory + disk) so repeat queries in the same pipeline don't re-hit APIs
        if result["items"]:
            self.cache[query] = {'timestamp': datetime.now().isoformat(), 'data': result}
            self._save_cache()

        return result

    def targeted_search(self, player_name, team_name, context="injury"):
        """
        [YAK ENHANCEMENT] Executes deep-dive searches for specific intel.
        Targets coach quotes and beat writer tweets.

        Cache-first: checks player_news_cache (synced daily from Tank01) before
        hitting external search (Perplexity → DuckDuckGo). This avoids burning
        Tank01/Perplexity credits for already-cached news.
        """
        # --- Cache-first: check today's player_news_cache before external search ---
        try:
            today = datetime.now().strftime('%Y-%m-%d')
            conn = sqlite3.connect(config.DATABASE if hasattr(config, 'DATABASE') else config.DB_PATH)
            news_rows = conn.execute("""
                SELECT headline, content FROM player_news_cache
                WHERE player_name LIKE ? AND fetched_date = ?
                ORDER BY published_at DESC
                LIMIT 3
            """, (f"%{player_name}%", today)).fetchall()
            conn.close()
            if news_rows:
                cached = " | ".join(
                    f"{r[0]}: {(r[1] or '')[:120]}" for r in news_rows
                )
                return {"items": [{"snippet": f"[Cached News] {cached}", "link": "tank01"}]}
        except Exception:
            pass  # cache miss or DB error — fall through to live search
        # --- End cache-first block ---

        queries = [
            f'{player_name} {team_name} coach quotes injury twitter',
            f'{player_name} {team_name} beat writer update'
        ]
        
        aggregated_items = []
        for q in queries:
            res = self.search_news(q)
            if res.get("items"):
                aggregated_items.extend(res["items"])
        
        return {"items": aggregated_items}

    def _check_news_catalyst(self, player_name, team, opponent, game_date=None):
        """Fetch relevant non-injury news for a player and classify betting impact."""
        query = f"{player_name} {team} vs {opponent} tonight lineup minutes rotation"
        news_text = self.targeted_search(player_name, query)
        if not news_text or not news_text.get('items'):
            return None
        
        items = news_text.get('items', [])
        if not items or len(items[0].get('snippet', '')) < 20:
            return None
        
        news_snippet = items[0].get('snippet', '')[:500]
        from utils.claude_prompts import NEWS_CATALYST_SYSTEM, NEWS_CATALYST_PROMPT
        from utils.claude_client import get_claude_analysis, HAIKU_MODEL
        prompt = NEWS_CATALYST_PROMPT.format(
            player_name=player_name, team=team, opponent=opponent, news_text=news_snippet
        )
        result_text = get_claude_analysis(
            prompt=prompt, system_prompt=NEWS_CATALYST_SYSTEM,
            model=HAIKU_MODEL, temperature=0.0, max_tokens=120,
            call_type='news_catalyst', player_name=player_name
        )
        if not result_text or not result_text.strip():
            return None
        try:
            result = json.loads(result_text.strip())
            if result.get('is_relevant') and result.get('confidence', 0) >= 0.6:
                return result
        except Exception:
            pass
        return None

    def _cache_and_return_status(self, cache_key: tuple, status: str, note: str, confidence: float) -> dict:
        """Build a status result dict, store it in the Haiku cache, and return it.

        Shared by _parse_with_taxonomy_injection and _ai_parse_blurb to avoid the
        three-line (build / store / return) pattern repeated at every early-exit branch.
        Includes a size guard so the cache doesn't grow unbounded in the ask_ludi bot
        (long-running process) where a single LudiYak instance handles many requests.
        """
        if len(self._haiku_parse_cache) > 200:
            self._haiku_parse_cache.clear()
        out = {"status": status, "note": note, "confidence": confidence}
        self._haiku_parse_cache[cache_key] = out
        return out

    def _perplexity_freshness_check(self, player_name, current_status, team_name="NBA"):
        """Phase 8 Staleness Challenger — verify older uncertain statuses.

        team_name must match what _nuance_check passes to targeted_search so both
        callers share the same yak_cache entry and we don't double-hit Perplexity
        for the same player in the same pipeline run.
        """
        news_text = self.targeted_search(player_name, team_name, context="injury")
        items = (news_text.get('items', []) if news_text else [])

        # Consolidate both "no results" and "snippet too short" into one guard
        if not items or len(items[0].get('snippet', '')) < 20:
            if current_status in ['GTD', 'PROBABLE', 'DOUBTFUL', 'QUESTIONABLE']:
                return {"status": "ACTIVE", "note": "[FRESHNESS] No new info, assumed Active", "confidence": 0.8}
            return None

        news_snippet = items[0].get('snippet', '')[:500]
        parsed = self._parse_with_taxonomy_injection(news_snippet, player_name, current_status)
        return parsed

    def _parse_with_taxonomy_injection(self, text, player_name, current_status):
        """Calls Haiku with taxonomy vocabulary injected as context."""
        # 120 chars reduces collision risk on similar blurbs vs the original 80.
        _cache_key = (player_name, text.strip()[:120])
        if _cache_key in self._haiku_parse_cache:
            raw = self._haiku_parse_cache[_cache_key]
            if isinstance(raw, dict) and 'status' in raw:
                return raw
        try:
            today_date = datetime.now().strftime('%Y-%m-%d')
            prompt = INJURY_BLURB_PARSE_PROMPT.format(
                description=text,
                player_name=player_name,
                today_date=today_date,
                inj_return_date='unknown',
            )

            result_text = get_claude_analysis(
                prompt=prompt,
                system_prompt=INJURY_BLURB_SYSTEM,
                model=HAIKU_MODEL,
                temperature=0.0,
                max_tokens=150,
                call_type='injury_freshness',
                player_name=player_name,
            )

            if not result_text or not result_text.strip():
                return None

            text_cleaned = result_text.strip()
            if text_cleaned.startswith('```'):
                text_cleaned = '\n'.join(text_cleaned.split('\n')[1:-1]).strip()

            result = json.loads(text_cleaned)

            status_override = result.get('status_override')
            if status_override:
                return self._cache_and_return_status(_cache_key, status_override, f"[AI] Override: {status_override}", 0.85)
            if result.get('no_designation'):
                return self._cache_and_return_status(_cache_key, "ACTIVE", "[AI] No designation found", 0.9)
            if result.get('rest'):
                return self._cache_and_return_status(_cache_key, "OUT_REST", "[AI] Load management", 0.9)
            tonight = result.get('tonight_available')
            if tonight is False:
                return self._cache_and_return_status(_cache_key, "OUT", "[AI] AI confirms out", 0.85)
            if tonight is True:
                return self._cache_and_return_status(_cache_key, "ACTIVE", "[AI] AI confirms active", 0.85)

            # Ambiguous result — cache a sentinel so we don't re-run Haiku on next call
            self._haiku_parse_cache[_cache_key] = {"status": None}
            return None
        except Exception as e:
            print(f"   [YAK] AI freshness parse failed for {player_name}: {e}")
            return None
    
    def get_team_schedule_context(self, team_name, target_date=None):
        """
        [WEEK 3] Get schedule context for B2B fatigue logic.
        
        Returns schedule metadata for B2B analysis:
        - is_back_to_back: bool (if team played yesterday)
        - rest_days: int (days since last game)  
        - is_road: bool (if game is away)
        - next_game_tomorrow: bool (if game tomorrow)
        - games_in_last_5_days: int (fatigue tracking)
        - games_in_next_5_days: int (load management)
        """
        if not target_date:
            target_date = datetime.now().strftime('%Y-%m-%d')
        
        # Use config.DB_PATH for proper database location
        db_path = getattr(config, 'DB_PATH', 'ludi.db')
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        try:
            # Get team's recent and near-future schedule context (wide window)
            # Fetching last 10 days and next 10 days roughly
            target_dt = datetime.strptime(target_date, '%Y-%m-%d')
            start_window = (target_dt - timedelta(days=7)).strftime('%Y-%m-%d')
            end_window = (target_dt + timedelta(days=7)).strftime('%Y-%m-%d')
            
            cursor.execute("""
                SELECT date, home_team, away_team
                FROM games 
                WHERE (home_team = ? OR away_team = ?)
                AND date BETWEEN ? AND ?
                ORDER BY date DESC
            """, (team_name, team_name, start_window, end_window))
            
            games_window = cursor.fetchall()
            
            # --- 1. B2B & Rest Analysis ---
            # Look strictly at days BEFORE target_date
            past_games = [g for g in games_window if g[0] < target_date]
            future_games = [g for g in games_window if g[0] > target_date]
            target_game_exists = any(g[0] == target_date for g in games_window)

            # Target game info (if known)
            is_road = False
            for g in games_window:
                if g[0] == target_date:
                    is_road = (g[2] == team_name) # Away team is index 2
                    break
            
            # Is Back-to-Back? (Played Yesterday)
            yesterday_str = (target_dt - timedelta(days=1)).strftime('%Y-%m-%d')
            is_back_to_back = any(g[0] == yesterday_str for g in past_games)
            
            # Rest Days
            rest_days = 999
            if past_games:
                # past_games is sorted DESC, so index 0 is most recent
                last_played = datetime.strptime(past_games[0][0], '%Y-%m-%d')
                rest_days = (target_dt - last_played).days
            
            # Next Game Tomorrow?
            tomorrow_str = (target_dt + timedelta(days=1)).strftime('%Y-%m-%d')
            next_game_tomorrow = any(g[0] == tomorrow_str for g in future_games)
            
            # --- 2. Density Analysis (Hashtag Matrix Style) ---
            # Games in Last 5 Days: Strict window [Target-5, Target-1]
            # If target is today (Day 0), we look at Day -5 to -1.
            # 4-in-5 means: Played -4, -3, -2, -1 (4 games) + Today = 5 in 5.
            # Usually strict metric is "Games played in last X days INCLUDING today".
            # WEEK 3 SPEC: "Calculation of `games_in_last_5_days`"
            # We will return the count EXCLUDING today to allow flexible aggregation.
            
            window_start_last = (target_dt - timedelta(days=5)).strftime('%Y-%m-%d')
            window_end_last = (target_dt - timedelta(days=1)).strftime('%Y-%m-%d')
            games_in_last_5_days = sum(1 for g in games_window if window_start_last <= g[0] <= window_end_last)
            
            # Forward Density: [Target+1, Target+5]
            window_start_next = (target_dt + timedelta(days=1)).strftime('%Y-%m-%d')
            window_end_next = (target_dt + timedelta(days=5)).strftime('%Y-%m-%d')
            games_in_next_5_days = sum(1 for g in games_window if window_start_next <= g[0] <= window_end_next)
            
            return {
                "is_back_to_back": is_back_to_back,
                "rest_days": rest_days,
                "is_road": is_road,
                "next_game_tomorrow": next_game_tomorrow,
                "games_in_last_5_days": games_in_last_5_days, # Trailing 5 (excluding target)
                "games_in_next_5_days": games_in_next_5_days
            }

        except Exception as e:
            print(f"   [YAK] ⚠️ Schedule Context Error: {e}")
            return {
                "is_back_to_back": False,
                "rest_days": 999,
                "is_road": False,
                "next_game_tomorrow": False,
                "games_in_last_5_days": 0,
                "games_in_next_5_days": 0
            }
        finally:
            conn.close()
    
    # Source priority order (matches ORDER BY in DB query below):
    #   1. ESPN — 15-30 min lag (sync_injuries_espn.py — fastest source)
    #   2. Tank01 — 2-6 hr lag (primary official API)
    #   3. BDL — 2-6 hr lag (fallback)
    #   4. Other (RotoWire/RealGM RSS — corroboration only)
    # Staleness: injuries > INJURY_STALENESS_DAYS days excluded (season-ender guard).
    
    def get_player_status(self, player_name, team_name="NBA"):
        # DB-FIRST: Check player_injuries table before hitting any API.
        # player_injuries now has ESPN (15-30min lag) + BDL/Tank01 + RSS — more current than
        # Module D's in-memory Tank01 cache (15-min TTL) for same-day rulings.
        # OUT/DOUBTFUL → return immediately (skip Perplexity + Claude).
        # GTD/QUESTIONABLE → fall through to nuance checks (Perplexity/Claude still valuable).
        try:
            _db_path = getattr(config, 'DB_PATH', 'ludi.db')
            _conn = sqlite3.connect(_db_path, timeout=5)
            _row = _conn.execute(f'''
                SELECT status, injury_type, days_out, source, snapshot_time
                FROM player_injuries
                WHERE LOWER(player_name) = LOWER(?)
                  AND resolved_at IS NULL
                  AND status NOT IN ('ACTIVE', 'PROBABLE')
                  AND snapshot_time >= datetime('now', '-{INJURY_STALENESS_DAYS} days')
                ORDER BY
                  CASE source WHEN 'ESPN' THEN 0 WHEN 'Tank01' THEN 1 WHEN 'BDL' THEN 2 ELSE 3 END,
                  snapshot_time DESC
                LIMIT 1
            ''', (player_name,)).fetchone()
            _conn.close()
            if _row:
                _status, _inj_type, _days_out, _source, _snapshot_time = _row
                
                try:
                    # Handle both naive and timezone-aware ISO formats
                    snapshot_dt = datetime.fromisoformat(_snapshot_time.replace('Z', '+00:00'))
                    if snapshot_dt.tzinfo:
                        snapshot_dt = snapshot_dt.replace(tzinfo=None)
                    age_hours = (datetime.now() - snapshot_dt).total_seconds() / 3600
                except Exception as e:
                    print(f"   >>> [Yak] Snapshot time parse failed, assuming fresh: {e}")
                    age_hours = 0

                # get_category + self._taxonomy imported at module level / loaded at __init__
                cat = get_category(_status)
                tax_info = self._taxonomy.get(_status, {})
                decay = tax_info.get('confidence_decay_hours', 24)
                
                if age_hours > decay and cat in ('UNCERTAIN', 'UNAVAILABLE'):
                    # Pass team_name so targeted_search uses same cache key as _nuance_check
                    fresh_intel = self._perplexity_freshness_check(player_name, _status, team_name=team_name)
                    if fresh_intel:
                        return fresh_intel

                if _status in ('OUT', 'DOUBTFUL'):
                    # Hard status confirmed in DB — skip API calls entirely
                    days_note = f" ({_days_out}d)" if _days_out and _days_out > 0 else ""
                    return {
                        "status": _status,
                        "note": f"[DB/{_source}] {_inj_type or _status}{days_note}",
                        "confidence": 1.0
                    }
                # GTD/QUESTIONABLE in DB — fall through to nuance check but skip Tank01 re-fetch
                elif _status in ('GTD', 'QUESTIONABLE'):
                    return self._nuance_check(player_name, team_name, _status,
                                              f"{_inj_type or _status} [{_source}]")
        except Exception as _e:
            pass  # DB unavailable — fall through to standard flow

        clean_name = unidecode.unidecode(player_name).replace('.', '').replace(' ', '').lower()
        self.refresh_official_injuries()

        status_tag = self.official_injuries.get(clean_name)
        
        # --- LAYER 1: HARD STATUS (Official) ---
        if status_tag:
            tag_lower = status_tag.lower()
            if any(x in tag_lower for x in ["out", "rest", "indefinitely", "inactive"]):
                return {"status": "OUT", "note": f"[OFFICIAL] {status_tag}", "confidence": 1.0}
            if "available" in tag_lower:
                return {"status": "ACTIVE", "note": f"[OFFICIAL] AVAILABLE", "confidence": 1.0}
        
        # --- LAYER 1.5: ROTOWIRE INTEL (Breaking News) ---
        roto_intel = self.get_rotowire_intel(player_name)
        if roto_intel:
            # RotoWire 'OUT' overrides official 'Questionable'
            if roto_intel['status'] in ['OUT', 'DOUBTFUL']:
                 return roto_intel
            # If RotoWire confirms active, trust it
            if roto_intel['status'] == 'ACTIVE':
                 return roto_intel
        
        # --- LAYER 2: OFFICIAL GTD/PROBABLE with schedule context ---
        base_status = {"status": "ACTIVE", "note": "Clear", "confidence": 1.0}
        
        if status_tag:
            tag_lower = status_tag.lower()
            if "doubtful" in tag_lower:
                base_status = {"status": "DOUBTFUL", "note": f"[OFFICIAL] {status_tag}", "confidence": 0.9}
            elif "probable" in tag_lower:
                # Still check news for 'minutes limit' even if probable
                base_status = self._nuance_check(player_name, team_name, "PROBABLE", status_tag)
            elif any(x in tag_lower for x in ["questionable", "gtd"]):
                base_status = self._nuance_check(player_name, team_name, "GTD", status_tag)
        
        # --- LAYER 3: SCHEDULE CONTEXT (B2B) ---
        # Use team from _injury_blurbs if available, otherwise fall back to team_name param
        schedule_team = team_name
        if not schedule_team or schedule_team == "NBA":
            blurb_data = getattr(self, '_injury_blurbs', {}).get(clean_name, {})
            if isinstance(blurb_data, dict):
                schedule_team = blurb_data.get('team', '')
        
        schedule_context = {}
        if schedule_team and schedule_team != "NBA":
            schedule_context = self.get_team_schedule_context(schedule_team)
        
        # Combine status with schedule context
        final_status = {**base_status, **schedule_context}
        
        return final_status

    def _ai_parse_blurb(self, description, player_name, inj_return_date=''):
        """
        Use Claude Haiku to extract structured injury intelligence from news blurb.
        Only called for GTD/Day-To-Day players where nuance matters.

        Args:
            description:     Raw Tank01 blurb text (e.g. "Feb 5: Herro (ribs) is not traveling...")
            player_name:     Human-readable name for context
            inj_return_date: YYYY-MM-DD expected return from Tank01 injReturnDate field

        Returns dict with parsed fields, or {} on failure (caller falls through to keyword logic).
        """
        if not description or len(description.strip()) < 10:
            return {}

        # 120 chars reduces collision risk on similar blurbs (e.g. same player different date).
        _cache_key = (player_name, description.strip()[:120])
        if _cache_key in self._haiku_parse_cache:
            return self._haiku_parse_cache[_cache_key]

        try:
            today_date = datetime.now().strftime('%Y-%m-%d')
            prompt = INJURY_BLURB_PARSE_PROMPT.format(
                description=description,
                player_name=player_name,
                today_date=today_date,
                inj_return_date=inj_return_date or 'unknown',
            )

            result_text = get_claude_analysis(
                prompt=prompt,
                system_prompt=INJURY_BLURB_SYSTEM,
                model=HAIKU_MODEL,
                temperature=0.0,   # deterministic — classification, not generation
                max_tokens=150,
                call_type='injury_nuance',
                player_name=player_name,
            )

            # Guard 1: None or empty response (auth failure, API error, empty blurb)
            if not result_text or not result_text.strip():
                print(f"   [YAK] AI blurb no response for {player_name} — keyword fallback")
                return {}

            # Guard 2: strip markdown code fences if Haiku wrapped output
            text = result_text.strip()
            if text.startswith('```'):
                lines_list = text.split('\n')
                text = '\n'.join(lines_list[1:-1]).strip()

            result = json.loads(text)
            self._haiku_parse_cache[_cache_key] = result  # store for same-run reuse
            return result
        except Exception as e:
            print(f"   [YAK] AI blurb parse failed for {player_name}: {e}")
            return {}

    def _nuance_check(self, player_name, team_name, primary_status, official_tag):
        """Internal helper to scan for 'Limits' or 'Scratch' news using Enhanced Yak logic."""
        
        roto_intel = self.get_rotowire_intel(player_name)
        realgm_intel = self.get_realgm_intel(player_name)
        intel_sources = [x for x in [roto_intel, realgm_intel] if x]

        if intel_sources:
            STATUS_PRIORITY = {'OUT': 0, 'DOUBTFUL': 1, 'MINUTES_LIMIT': 2, 'ACTIVE': 3}
            best = min(intel_sources, key=lambda x: STATUS_PRIORITY.get(x['status'], 99))
            statuses = [s['status'] for s in intel_sources]

            if len(intel_sources) >= 2 and len(set(statuses)) == 1:
                best = dict(best)
                best['confidence'] = 0.95
                best['note'] = best.get('note', '') + ' [2-source confirmed]'

            if best['status'] in ['OUT', 'DOUBTFUL']:
                return best
            if best['status'] == 'ACTIVE':
                return best
        
        # AI blurb parsing for richer intelligence
        clean_name = unidecode.unidecode(player_name).replace('.', '').replace(' ', '').lower()
        blurb_data = getattr(self, '_injury_blurbs', {}).get(clean_name, {})
        blurb = blurb_data.get('description', '') if isinstance(blurb_data, dict) else blurb_data
        inj_return_date = blurb_data.get('inj_return_date', '') if isinstance(blurb_data, dict) else ''
        if blurb:
            ai_parsed = self._ai_parse_blurb(blurb, player_name, inj_return_date=inj_return_date)
            if ai_parsed:
                tonight = ai_parsed.get('tonight_available')
                context = ai_parsed.get('context')
                severity = ai_parsed.get('severity')
                body = ai_parsed.get('body_part', '?')
                games_est = ai_parsed.get('games_out_estimate', '?')

                # Recently traded = not injured, flag as active
                if context == 'recently_traded':
                    return {"status": "ACTIVE", "note": "[AI] Recently traded — not injured", "confidence": 0.85}

                # Tonight definitively unavailable (moderate/severe)
                if tonight is False and severity in ('moderate', 'severe'):
                    return {"status": "DOUBTFUL", "note": f"[AI] {body} — {games_est}", "confidence": 0.85}

                # Minutes risk — probable but limited
                if ai_parsed.get('minutes_risk') and primary_status in ('PROBABLE', 'GTD') and tonight is not False:
                    return {"status": "MINUTES_LIMIT", "note": f"[AI] {body} — minutes risk", "confidence": 0.8}

                # Mid-game exit = fresh injury, likely out or limited next game
                if context == 'mid_game_exit':
                    return {"status": "DOUBTFUL", "note": f"[AI] Mid-game exit ({body})", "confidence": 0.85}
        
        # Use Targeted Search for deep intel
        news = self.targeted_search(player_name, team_name)
        
        if news.get("items"):
            # Scan recent snippets
            for item in news["items"][:5]:
                snippet = item['snippet'].lower()
                
                # Check for Limits
                # [PHASE 3] Update: Use config if available, fallback for robusteness
                limit_kws = self.keywords_config.get('categories', {}).get('MINUTES_LIMIT', {}).get('keywords', ["minutes limit", "restriction"])
                for k in limit_kws:
                    if k in snippet: 
                        return {"status": "MINUTES_LIMIT", "note": f"Intel: {k.upper()} found", "confidence": 0.8}
                
                # Check for Late Scratches
                out_kws = self.keywords_config.get('categories', {}).get('INJURY_OUT', {}).get('keywords', ["ruled out", "won't play"])
                for k in out_kws:
                    if k in snippet: 
                        return {"status": "OUT", "note": f"Intel: Late scratch detected", "confidence": 1.0}
                
                # Check for Coach Confirmation (Availability)
                if "coach" in snippet and any(x in snippet for x in ["will play", "expect him to go", "available"]):
                    return {"status": "ACTIVE", "note": "Intel: Coach confirms ACTIVE", "confidence": 0.9}

        return {"status": primary_status, "note": f"[OFFICIAL] {official_tag}", "confidence": 0.6}

    def resolve_scenarios(self, sim_results):
        final_card = []
        grouped = {}
        
        for res in sim_results:
            # V2.0 Fix: Group by Player Name only (Sim results are full profiles, not single stats)
            key = res['PLAYER_NAME']
            if key not in grouped: grouped[key] = {}
            grouped[key][res['SCENARIO']] = res

        for key, scenarios in grouped.items():
            base_res = scenarios.get("BASE")
            pivot_scen = next((s for s in scenarios if "WITHOUT" in s), None)
            
            if pivot_scen:
                pivot_player = pivot_scen.replace("WITHOUT ", "")
                report = self.get_player_status(pivot_player)
                
                # Logic: If player is OUT or DOUBTFUL, we always shift.
                # If GTD, we stick to base but add a warning.
                if report['status'] in ["OUT", "DOUBTFUL"]:
                    res = scenarios[pivot_scen]
                    res['decision_note'] = f"✅ {pivot_player} is {report['status']}"
                    final_card.append(res)
                else:
                    if base_res:
                        base_res['decision_note'] = f"🛡️ {pivot_player} is {report['status']}"
                        final_card.append(base_res)
            elif base_res:
                final_card.append(base_res)

        return final_card

    def get_injuries(self):
        """
        Returns dict of official injury statuses.
        Key format: unidecode(player_name).replace('.','').replace(' ','').lower()
        Example: 'Nikola Jokic' → 'nikolajokic', 'Joel Embiid' → 'joelembiid'
        Callers must normalize lookup keys to this format.
        """
        self.refresh_official_injuries()
        return self.official_injuries

if __name__ == "__main__":
    yak = LudiYak()
    # Testing status spectrum
    print(yak.get_player_status("Jalen Brunson", "Knicks"))
    
    print("\n--- Testing get_injuries() wrapper ---")
    injuries = yak.get_injuries()
    print(f"Total injuries tracked: {len(injuries)}")
    
    print("\n--- Testing RotoWire Feed ---")
    rss = yak.refresh_rotowire_rss()
    print(f"RSS Items: {len(rss)}")
    if rss:
        print(f"Top Item: {rss[0]['player_name']} - {rss[0]['headline']}")
        
    print(f"Current Refresh Interval: {yak.get_refresh_interval()} min")