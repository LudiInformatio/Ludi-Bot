import json
import hashlib
import re as _re
import time
import requests
from pathlib import Path
from datetime import date
import config

CACHE_DIR = Path("cache/perplexity")
CACHE_TTL = 4 * 3600
REF_CACHE_TTL = 30 * 60  # 30 minutes — refs need fresh data close to game time


class PerplexityClient:
    def __init__(self):
        self.api_key = getattr(config, 'PERPLEXITY_API_KEY', None)
        self._cache = self._load_cache()

    def search_player_news(self, player_name: str, team: str) -> str:
        query = f"NBA {player_name} {team} injury status tonight"
        return self._query(query)

    def search_game_news(self, home_team: str, away_team: str) -> str:
        query = f"NBA {away_team} at {home_team} tonight injury lineup news"
        return self._query(query)

    def search_game_context(self, home_team: str, away_team: str,
                            out_players: list = None,
                            hours_to_game: float = 12.0) -> str:
        """Combined query: injuries + lineup changes + role shifts.
        Same API cost as search_game_news (one call), richer context.
        hours_to_game drives the recency filter — tighter window closer to tip."""
        out_str = f" Key absences: {', '.join(out_players[:3])}." if out_players else ""
        query = (
            f"NBA {away_team} at {home_team} tonight: "
            f"injury updates, lineup changes, rotation adjustments, role changes.{out_str}"
        )
        recency = self._get_recency_filter(hours_to_game)
        return self._query(query, recency_filter=recency)

    def search_referee_assignments(self, target_date: str, games: list,
                                      known_refs: list = None) -> dict:
        """Single bulk Perplexity query for all referee assignments on a date.

        Args:
            target_date: 'YYYY-MM-DD'
            games: list of dicts/tuples with home_team, away_team
            known_refs: list of known referee names for fuzzy matching

        Returns:
            dict: {home_team: [ref1, ref2, ref3]} — only populated entries
        """
        cache_key_str = f"ref_bulk_{target_date}"
        key = hashlib.md5(cache_key_str.encode()).hexdigest()
        if key in self._cache:
            entry = self._cache[key]
            if time.time() - entry["ts"] < REF_CACHE_TTL:
                try:
                    return json.loads(entry["text"])
                except Exception:
                    pass

        if not self.api_key or not games:
            return {}

        # Build game list for prompt — handle both dict and tuple formats
        game_lines = []
        for g in games:
            if isinstance(g, dict):
                home = g.get('home_team', '')
                away = g.get('away_team', '')
            else:
                # tuple: (game_id, home_team, away_team)
                home = g[1] if len(g) > 1 else ''
                away = g[2] if len(g) > 2 else ''
            game_lines.append(f"- {away} at {home}")

        prompt = (
            f"NBA referee assignments for {target_date}.\n"
            f"For each game below, return the 3 assigned referees.\n"
            f"Format each line exactly as: AWAY at HOME: Ref1, Ref2, Ref3\n"
            f"If unknown, write: AWAY at HOME: unknown\n\n"
            f"Games:\n" + "\n".join(game_lines) + "\n\n"
            f"Return ONLY the formatted list. No explanations."
        )

        try:
            resp = requests.post(
                "https://api.perplexity.ai/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={
                    "model": "sonar",
                    "messages": [
                        {"role": "system", "content": "You are an NBA data assistant. Return referee crew assignments in the exact format requested."},
                        {"role": "user", "content": prompt}
                    ],
                    "search_recency_filter": "day",
                    "max_tokens": 600
                },
                timeout=15
            )
            if not resp.text.strip():
                print(f"[Perplexity] Empty ref response. HTTP {resp.status_code}")
                return {}

            text = resp.json()["choices"][0]["message"]["content"]
        except Exception as e:
            print(f"[Perplexity] ref query error: {e}")
            return {}

        # Parse structured output — match "TEAM at TEAM: Name, Name, Name"
        result = {}
        for line in text.strip().split("\n"):
            line = line.strip().lstrip("- ")
            if "unknown" in line.lower():
                continue
            # Pattern: anything "at" HOME_TEAM ":" comma-separated names
            m = _re.match(r'.+\s+at\s+(\w+)\s*:\s*(.+)', line)
            if not m:
                continue
            home_raw = m.group(1).strip()
            refs_raw = [r.strip() for r in m.group(2).split(",") if r.strip()]

            # If known_refs provided, fuzzy-match against roster
            if known_refs and refs_raw:
                matched = []
                for ref_text in refs_raw:
                    ref_lower = ref_text.lower()
                    for kr in known_refs:
                        if kr.lower() in ref_lower or ref_lower in kr.lower():
                            matched.append(kr)
                            break
                    else:
                        matched.append(ref_text)  # Keep raw name if no match
                refs_raw = matched

            if refs_raw:
                result[home_raw] = refs_raw

        # Cache the parsed result
        self._cache[key] = {"text": json.dumps(result), "ts": time.time()}
        self._save_cache()
        return result

    def _get_recency_filter(self, hours_to_game: float) -> str:
        """Dynamic recency filter based on time to tipoff (from Ludi-Lite pattern).
        - <=2 hrs: 'hour'  — pre-game window, late scratches only
        - <=12 hrs: 'day'  — game-day context
        - >12 hrs: 'week'  — advance look, trends and matchup history
        """
        if hours_to_game <= 2:
            return "hour"
        elif hours_to_game <= 12:
            return "day"
        else:
            return "week"

    def _query(self, query: str, recency_filter: str = "day") -> str:
        # Include recency filter in cache key so different windows don't collide
        cache_key_str = f"{query}|{recency_filter}"
        key = hashlib.md5(cache_key_str.encode()).hexdigest()
        if key in self._cache:
            entry = self._cache[key]
            if time.time() - entry["ts"] < CACHE_TTL:
                return entry["text"]

        if not self.api_key:
            return ""

        try:
            resp = requests.post(
                "https://api.perplexity.ai/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={
                    "model": "sonar",
                    "messages": [
                        {
                            "role": "system",
                            "content": (
                                "You are an NBA sports news analyst. Focus on official team injury reports, "
                                "head coach statements, and credentialed beat reporters. "
                                "When summarizing injury news, include: player name, injury type, "
                                "game availability tonight, and expected timeline if mentioned. "
                                "Be concise and factual — no speculation."
                            )
                        },
                        {"role": "user", "content": query}
                    ],
                    "search_recency_filter": recency_filter,
                    "max_tokens": 200
                },
                timeout=10
            )
            # Log empty responses so we can diagnose auth vs rate limit issues
            if not resp.text.strip():
                print(f"[Perplexity] Empty response. HTTP {resp.status_code}")
                return ""
            text = resp.json()["choices"][0]["message"]["content"]
            self._cache[key] = {"text": text, "ts": time.time()}
            self._save_cache()
            return text
        except Exception as e:
            print(f"[Perplexity] error: {e}")
            return ""

    def _load_cache(self) -> dict:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        cache_file = CACHE_DIR / f"{date.today()}.json"
        if cache_file.exists():
            try:
                return json.loads(cache_file.read_text())
            except Exception:
                return {}
        return {}

    def _save_cache(self):
        cache_file = CACHE_DIR / f"{date.today()}.json"
        cache_file.write_text(json.dumps(self._cache))
