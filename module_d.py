import requests
import json
import os
import time
from datetime import datetime, timedelta
from duckduckgo_search import DDGS
import unidecode
import config

# [PAID TIER] Import monitoring and retry utilities
from utils.api_monitor import get_monitor
from utils.api_helpers import retry_with_backoff

# ==========================================
# LUDI INFORMATIO | MODULE D: THE YAK
# V3.5 - FULL STATUS SPECTRUM (2025-26)
# ==========================================

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

        # [PAID TIER] Initialize API Monitor
        self.monitor = get_monitor()
        
        self.KEYWORDS = {
            "OUT": ["ruled out", "won't play", "surgery", "out indefinitely", "downgraded", "rest", "inactive"],
            "DOUBTFUL": ["doubtful", "unlikely", "not expected"],
            "LIMITED": ["minutes limit", "restriction", "ramp up", "short leash", "injury management", "conditioning"], 
            "PROMOTION": ["starting lineup", "will start", "replacing", "first-team"],
            "AVAILABLE": ["available", "cleared", "will play", "warmed up"]
        }

    def _load_cache(self):
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'r') as f:
                    return json.load(f)
            except: return {}
        return {}

    def _save_cache(self):
        with open(self.cache_file, 'w') as f:
            json.dump(self.cache, f)

    @retry_with_backoff(max_attempts=3, backoff=2.0)
    def refresh_official_injuries(self):
        """Syncs with the NBA's 15-minute reporting cycle."""
        if self.last_official_refresh:
            elapsed = datetime.now() - self.last_official_refresh
            if elapsed < timedelta(minutes=15):
                return True

        url = f"https://{self.TANK_HOST}/getNBAInjuryList"
        headers = {"X-RapidAPI-Key": self.TANK_KEY, "X-RapidAPI-Host": self.TANK_HOST}

        try:
            r = requests.get(url, headers=headers, timeout=10)

            # [PAID TIER] Log API usage
            self.monitor.log_request('tank01', 'injury_list', r.headers)

            # Enhanced error handling
            r.raise_for_status()  # Raise for 4xx/5xx
            data = r.json()

            if r.status_code == 200 and 'body' in data:
                self.official_injuries = {}
                for item in data['body']:
                    p_name = item.get('longName', 'Unknown')
                    clean_name = unidecode.unidecode(p_name).replace('.', '').replace(' ', '').lower()
                    # Designation handles: Out, Doubtful, Questionable, Probable, Available
                    self.official_injuries[clean_name] = item.get('designation', 'Available')

                self.last_official_refresh = datetime.now()
                print(f"   [YAK] 📋 Heartbeat: NBA Official Feed Synced.")
                return True

        except requests.exceptions.HTTPError as e:
            if e.response and e.response.status_code == 429:
                print(f"   [YAK] ⚠️ Rate limit - extending cache...")
                return False  # Use cached data
            else:
                error_msg = f"HTTP Error {e.response.status_code if e.response else 'Unknown'}"
                print(f"   [YAK] ❌ {error_msg}")
                self.monitor.log_failed_request('tank01', 'injury_list', error_msg)
                raise

        except Exception as e:
            error_msg = f"{type(e).__name__}: {str(e)}"
            print(f"   [YAK] ❌ Error: {error_msg}")
            self.monitor.log_failed_request('tank01', 'injury_list', error_msg)
            raise

    def refresh_injuries_balldontlie(self):
        """ [SECONDARY] BallDontLie Injury Source """
        bdl_key = getattr(config, 'BALLDONTLIE_KEY', None)
        if not bdl_key:
            return False

        url = f"https://{config.BALLDONTLIE_HOST}/v1/player_injuries"
        headers = {"Authorization": bdl_key}
        
        try:
            # r = requests.get(url, headers=headers)
            # data = r.json()
            # if r.status_code == 200:
            #     print(f"   [YAK] 🛡️ Secondary Feed (BDL) Synced.")
            #     # Logic to merge with self.official_injuries would go here
            pass
        except Exception as e:
            print(f"   [YAK] ⚠️ BDL Refresh Error: {e}")

    def search_news(self, query):
        if query in self.cache:
            entry = self.cache[query]
            if datetime.now() - datetime.fromisoformat(entry['timestamp']) < timedelta(minutes=20):
                return entry['data']

        try:
            results = DDGS().text(query, max_results=3, timelimit="w") 
            formatted = [{"snippet": r['body'], "link": r['href']} for r in results]
            self.cache[query] = {"timestamp": datetime.now().isoformat(), "data": {"items": formatted}}
            self._save_cache()
            return {"items": formatted}
        except:
            return {"items": []}

    def targeted_search(self, player_name, team_name, context="injury"):
        """
        [YAK ENHANCEMENT] Executes deep-dive searches for specific intel.
        Targets coach quotes and beat writer tweets.
        """
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

    def get_player_status(self, player_name, team_name="NBA"):
        clean_name = unidecode.unidecode(player_name).replace('.', '').replace(' ', '').lower()
        self.refresh_official_injuries()
        self.refresh_injuries_balldontlie() # BDL Backup
            
        status_tag = self.official_injuries.get(clean_name)
        
        # --- LAYER 1: HARD STATUS ---
        if status_tag:
            tag_lower = status_tag.lower()
            if any(x in tag_lower for x in ["out", "rest", "indefinitely", "inactive"]):
                return {"status": "OUT", "note": f"[OFFICIAL] {status_tag}", "confidence": 1.0}
            if "available" in tag_lower:
                return {"status": "ACTIVE", "note": f"[OFFICIAL] AVAILABLE", "confidence": 1.0}
            if "doubtful" in tag_lower:
                return {"status": "DOUBTFUL", "note": f"[OFFICIAL] {status_tag}", "confidence": 0.9}
            if "probable" in tag_lower:
                # Still check news for 'minutes limit' even if probable
                return self._nuance_check(player_name, team_name, "PROBABLE", status_tag)
            if any(x in tag_lower for x in ["questionable", "gtd"]):
                return self._nuance_check(player_name, team_name, "GTD", status_tag)

        return {"status": "ACTIVE", "note": "Clear", "confidence": 1.0}

    def _nuance_check(self, player_name, team_name, primary_status, official_tag):
        """Internal helper to scan for 'Limits' or 'Scratch' news using Enhanced Yak logic."""
        
        # Use Targeted Search for deep intel
        news = self.targeted_search(player_name, team_name)
        
        if news.get("items"):
            # Scan recent snippets
            for item in news["items"][:5]:
                snippet = item['snippet'].lower()
                
                # Check for Limits
                for k in self.KEYWORDS["LIMITED"]:
                    if k in snippet: 
                        return {"status": "MINUTES_LIMIT", "note": f"Intel: {k.upper()} found", "confidence": 0.8}
                
                # Check for Late Scratches
                for k in self.KEYWORDS["OUT"]:
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
            key = f"{res['PLAYER_NAME']}_{res['stat']}"
            if key not in grouped: grouped[key] = {}
            grouped[key][res['scenario']] = res

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

if __name__ == "__main__":
    yak = LudiYak()
    # Testing status spectrum
    print(yak.get_player_status("Jalen Brunson", "Knicks"))