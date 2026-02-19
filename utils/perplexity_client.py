import json
import hashlib
import time
import requests
from pathlib import Path
from datetime import date
import config

CACHE_DIR = Path("cache/perplexity")
CACHE_TTL = 4 * 3600


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
                            out_players: list = None) -> str:
        """Combined query: injuries + lineup changes + role shifts.
        Same API cost as search_game_news (one call), richer context."""
        out_str = f" Key absences: {', '.join(out_players[:3])}." if out_players else ""
        query = (
            f"NBA {away_team} at {home_team} tonight: "
            f"injury updates, lineup changes, rotation adjustments, role changes.{out_str}"
        )
        return self._query(query)

    def _query(self, query: str) -> str:
        key = hashlib.md5(query.encode()).hexdigest()
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
                    "messages": [{"role": "user", "content": query}],
                    "search_recency_filter": "day",
                    "max_tokens": 200
                },
                timeout=10
            )
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
