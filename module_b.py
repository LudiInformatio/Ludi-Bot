"""
Module B: LudiEngine — Trend/Streak Consolidation Layer

Pre-loads player_trends + recent game values at init (zero runtime DB queries).
Enriches player dicts with L5/L10/L15 averages, hit rates vs sportsbook lines,
streak scores. Persists opening prop lines to prop_line_snapshots.

Follows Module C's _load_foul_splits_data() pre-load pattern.
"""

import sqlite3
import unicodedata
from collections import defaultdict
import config
from utils.tag_classifier import calculate_streak_score

# 2025-26 season start — single rollover point (update each season alongside module_c.py)
_SEASON_START = '2025-10-22'

# Normalize Module A's long-form prop keys to game_values_cache short-form keys.
# Module A stores sportsbook_props with 'points', 'rebounds' (long-form via market_key.replace('player_', '')).
# game_values_cache uses 'PTS', 'REB' (short-form DB column aliases from player_game_logs).
_PROP_KEY_TO_CACHE = {
    'POINTS': 'PTS', 'REBOUNDS': 'REB', 'ASSISTS': 'AST',
    'THREES': 'FG3M', '3PM': 'FG3M', 'FG3M': 'FG3M',
    'BLOCKS': 'BLK', 'STEALS': 'STL', 'TURNOVERS': 'TOV',
}


class LudiEngine:
    """
    Unified trend/streak consolidation layer.

    Pre-loads all data at init. Zero DB queries during per-player enrichment.

    Keys added to player dict via enrich_player():
    | Key | Type | Description |
    |-----|------|-------------|
    | L5_PTS, L5_REB, L5_AST | float | Last 5 game average |
    | L10_PTS, L10_REB, L10_AST | float | Last 10 game average |
    | L15_PTS, L15_REB, L15_AST | float | Last 15 game average |
    | season_avg_PTS, season_avg_REB, season_avg_AST | float | Season average |
    | streak_score | int | -3 to +3 from calculate_streak_score() |
    | trend_label | str | From player_trends table |
    | trend_delta | float | From player_trends table |
    | hit_rates_by_market | dict | {stat: {over_l5..over_l20, over_vs_scheme_l5, vs_scheme}} |
    """

    def __init__(self, db_path=None):
        self.db_path = db_path or config.DB_PATH
        self.trends_cache = {}          # (player_id, stat, team) → trend dict
        self.game_values_cache = {}     # (player_id, stat) → [recent values, full season]
        self.name_to_id = {}            # player_name → (player_id, team)
        self.team_scheme_map = {}       # team_abbr → active defense style (from team_scheme_cache)
        self.vs_scheme_cache = {}       # (player_id, stat, scheme) → [last-5 game values vs that scheme]
        self._load_trends_cache()
        self._load_game_values_cache()
        self._load_vs_scheme_cache()
        self._load_name_map()

    def _load_trends_cache(self):
        """Load all player_trends rows into memory.
        Keyed by (player_id, stat, team_abbr).
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            rows = conn.execute("""
                SELECT player_id, player_name, team_abbreviation, stat,
                       l7_avg, l10_avg, l15_avg, season_avg,
                       trend_delta, trend_label, streak_vs_avg
                FROM player_trends
            """).fetchall()
            conn.close()

            for row in rows:
                key = (row['player_id'], row['stat'], row['team_abbreviation'])
                self.trends_cache[key] = {
                    'player_name': row['player_name'],
                    'l7_avg': row['l7_avg'],
                    'l10_avg': row['l10_avg'],
                    'l15_avg': row['l15_avg'],
                    'season_avg': row['season_avg'],
                    'trend_delta': row['trend_delta'],
                    'trend_label': row['trend_label'],
                    'streak_vs_avg': row['streak_vs_avg']
                }
            print(f"   >>> Trends cache loaded: {len(self.trends_cache)} rows")
        except Exception as e:
            print(f"   ⚠️ Trends cache load failed: {e}")
            self.trends_cache = {}

    def _load_game_values_cache(self):
        """Load last 20 raw game values per player per stat from player_game_logs.
        Uses ROW_NUMBER window function. Supports L5/L10/L15/L20 hit rate windows.

        Uses full season data (SEASON_START = '2025-10-22') rather than a rolling
        day window, so L20 always has reliable samples (SGA has 49 games this season
        vs only 23 in a -70 day window). Update _SEASON_START at each season rollover.
        Combo stats (PRA/PA/PR/RA) fall back to Module F _get_hit_rates_vs_line() DB query.
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row

            # Load basic stats - use actual column names from player_game_logs
            stat_map = {
                'PTS': 'pts',
                'REB': 'reb',
                'AST': 'ast',
                'FG3M': 'fg3m',
                'BLK': 'blk',
                'STL': 'stl',
                'TOV': 'tov'
            }

            for stat_key, col in stat_map.items():
                rows = conn.execute(f"""
                    WITH ranked AS (
                        SELECT player_id, player_name, {col} AS stat_val, game_date,
                               ROW_NUMBER() OVER (PARTITION BY player_id ORDER BY game_date DESC) AS rn
                        FROM player_game_logs
                        WHERE game_date >= '{_SEASON_START}' AND minutes > 0
                    )
                    SELECT player_id, player_name, stat_val
                    FROM ranked
                    WHERE rn <= 20
                    ORDER BY player_id, game_date DESC
                """).fetchall()

                for row in rows:
                    player_id = row['player_id']
                    key = (player_id, stat_key)
                    if key not in self.game_values_cache:
                        self.game_values_cache[key] = []
                    if row['stat_val'] is not None:
                        self.game_values_cache[key].append(float(row['stat_val']))

            # Combo stats are derived from component averages elsewhere
            # No need to pre-compute here

            conn.close()
            print(f"   >>> Game values cache loaded: {len(self.game_values_cache)} stat-player combinations")
        except Exception as e:
            print(f"   ⚠️ Game values cache load failed: {e}")
            self.game_values_cache = {}

    def _load_vs_scheme_cache(self):
        """Pre-load last 5 game values per player/stat vs each defense scheme.

        Reads live defensive schemes from team_scheme_cache.active_style (updated daily by
        module_e.py's _load_dynamic_defensive_styles). Uses DISTINCT games subquery to
        avoid triple-counting rows from the 3 duplicate game_id formats in the games table.
        Skips NEUTRAL opponents — not enough differentiation for a meaningful signal.

        Pattern: same as _load_game_values_cache() but with opponent-scheme grouping.
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row

            # Step 1: Load live team → defense scheme map from DB (NOT hardcoded)
            scheme_rows = conn.execute("""
                SELECT team_abbr, active_style
                FROM team_scheme_cache
                WHERE scheme_type = 'DEFENSE'
            """).fetchall()
            self.team_scheme_map = {r['team_abbr']: r['active_style'] for r in scheme_rows}

            if not self.team_scheme_map:
                print("   ⚠️ team_scheme_cache empty — vs_scheme cache skipped (will retry next run)")
                conn.close()
                return

            stat_map = {
                'PTS': 'pts', 'REB': 'reb', 'AST': 'ast',
                'FG3M': 'fg3m', 'BLK': 'blk', 'STL': 'stl', 'TOV': 'tov'
            }

            for stat_key, col in stat_map.items():
                # canonical_games has exactly ONE row per (date, home_team, away_team) —
                # replaces the old DISTINCT games CTE workaround. Cleaner, faster, and
                # normalizes abbreviations via canonical_teams.standard_abbr at write time.
                rows = conn.execute(f"""
                    SELECT pgl.player_id,
                           pgl.{col} AS stat_val,
                           pgl.game_date,
                           CASE WHEN pgl.team_abbreviation = cg.home_team
                                THEN cg.away_team ELSE cg.home_team END AS opponent
                    FROM player_game_logs pgl
                    JOIN canonical_games cg ON cg.date = pgl.game_date
                        AND (pgl.team_abbreviation = cg.home_team
                             OR pgl.team_abbreviation = cg.away_team)
                    WHERE pgl.game_date >= '{_SEASON_START}'
                      AND pgl.minutes > 0
                      AND pgl.{col} IS NOT NULL
                    ORDER BY pgl.player_id, pgl.game_date DESC
                """).fetchall()

                for row in rows:
                    opponent = row['opponent']
                    if not opponent:
                        continue
                    scheme = self.team_scheme_map.get(opponent)
                    if not scheme or scheme == 'NEUTRAL':
                        continue  # NEUTRAL is non-actionable — skip to keep cache lean

                    key = (row['player_id'], stat_key, scheme)
                    if key not in self.vs_scheme_cache:
                        self.vs_scheme_cache[key] = []

                    # Already DESC order — keep only last 5 per scheme
                    if len(self.vs_scheme_cache[key]) < 5:
                        self.vs_scheme_cache[key].append(float(row['stat_val']))

            conn.close()
            print(f"   >>> Vs-scheme cache loaded: {len(self.vs_scheme_cache)} scheme-player-stat combinations")
        except Exception as e:
            print(f"   ⚠️ Vs-scheme cache load failed: {e}")
            self.vs_scheme_cache = {}

    def _load_name_map(self):
        """Build player_name → (player_id, team) from player_game_logs (canonical source).
        Uses player_game_logs as primary because it has the IDs that match game values.
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row

            # Primary: from player_game_logs (this is the canonical source for game data)
            rows = conn.execute("""
                SELECT DISTINCT player_id, player_name, team_abbreviation
                FROM player_game_logs
                WHERE game_date >= date('now', '-60 days')
            """).fetchall()
            for row in rows:
                normalized = self._normalize_name(row['player_name'])
                # Store with the player_game_logs player_id which matches game values
                # Only set if not already present (first occurrence wins)
                if normalized not in self.name_to_id:
                    self.name_to_id[normalized] = (row['player_id'], row['team_abbreviation'])

            conn.close()
            print(f"   >>> Name map loaded: {len(self.name_to_id)} players")
        except Exception as e:
            print(f"   ⚠️ Name map load failed: {e}")
            self.name_to_id = {}

    def _normalize_name(self, name):
        """Strip accents using NFKD decomposition — handles all scripts (ć, č, š, ž, etc).
        Consistent with _strip_accents() in capture_closing_lines.py.
        """
        if not name:
            return ''
        return ''.join(
            c for c in unicodedata.normalize('NFKD', name)
            if unicodedata.category(c) != 'Mn'
        ).strip()

    def enrich_player(self, p_dict, props_fmt=None):
        """
        Enrich player dict with trends, hit rates, and streak scores.

        Mutates p_dict in place. Called per player in build_reporter_input().

        Args:
            p_dict: Player dict from main.py build_reporter_input()
            props_fmt: Dict of prop markets with lines (for hit rate calculation)
        """
        player_name = p_dict.get('name', '')
        if not player_name:
            print(f"⚠️   Module B enrich_player: missing 'name' key — skipping enrichment for this player")
            return

        normalized = self._normalize_name(player_name)
        player_id, team = self.name_to_id.get(normalized, (None, p_dict.get('team', '')))

        # Set L5/L10/L15 averages for PTS/REB/AST
        for stat, stat_key in [('PTS', 'PTS'), ('REB', 'REB'), ('AST', 'AST')]:
            values = self.game_values_cache.get((player_id, stat_key), [])
            if len(values) >= 5:
                p_dict[f'L5_{stat_key}'] = sum(values[:5]) / 5
            if len(values) >= 10:
                p_dict[f'L10_{stat_key}'] = sum(values[:10]) / 10
            if len(values) >= 15:
                p_dict[f'L15_{stat_key}'] = sum(values[:15]) / 15

        # Get season averages from trends cache
        if player_id and team:
            for stat in ['PTS', 'REB', 'AST']:
                key = (player_id, stat, team)
                trend = self.trends_cache.get(key, {})
                if trend:
                    p_dict[f'season_avg_{stat}'] = trend.get('season_avg', 0)
                    p_dict['trend_label'] = trend.get('trend_label', '')
                    p_dict['trend_delta'] = trend.get('trend_delta', 0)

        # Calculate streak_score using calculate_streak_score()
        l5_pts = p_dict.get('L5_PTS', 0)
        l10_pts = p_dict.get('L10_PTS', 0)
        l15_pts = p_dict.get('L15_PTS', 0)
        season_avg_pts = p_dict.get('season_avg_PTS', p_dict.get('base_pts', 0))

        l5_reb = p_dict.get('L5_REB', 0)
        l10_reb = p_dict.get('L10_REB', 0)
        l15_reb = p_dict.get('L15_REB', 0)
        season_avg_reb = p_dict.get('season_avg_REB', p_dict.get('base_reb', 0))

        l5_ast = p_dict.get('L5_AST', 0)
        l10_ast = p_dict.get('L10_AST', 0)
        l15_ast = p_dict.get('L15_AST', 0)
        season_avg_ast = p_dict.get('season_avg_AST', p_dict.get('base_ast', 0))

        # Calculate streak score for each stat, take the max
        streak_scores = []
        if l5_pts or l10_pts or l15_pts or season_avg_pts:
            streak_scores.append(calculate_streak_score(l5_pts, l10_pts, l15_pts, season_avg_pts))
        if l5_reb or l10_reb or l15_reb or season_avg_reb:
            streak_scores.append(calculate_streak_score(l5_reb, l10_reb, l15_reb, season_avg_reb))
        if l5_ast or l10_ast or l15_ast or season_avg_ast:
            streak_scores.append(calculate_streak_score(l5_ast, l10_ast, l15_ast, season_avg_ast))

        p_dict['streak_score'] = max(streak_scores) if streak_scores else 0

        # Calculate hit_rates_by_market from game values vs prop lines.
        # _PROP_KEY_TO_CACHE is module-level (defined after _SEASON_START).
        hit_rates = {}
        if props_fmt:
            for prop_key, prop_data in props_fmt.items():
                if isinstance(prop_data, dict):
                    line = prop_data.get('line', 0)
                    if line <= 0:
                        continue

                    # Normalize to cache key ('points' → 'POINTS' → 'PTS')
                    prop_upper = prop_key.upper()
                    cache_key = _PROP_KEY_TO_CACHE.get(prop_upper, prop_upper)
                    values = self.game_values_cache.get((player_id, cache_key), [])
                    if not values:
                        continue

                    # Calculate hit rates — L5/L10/L15/L20 windows
                    # Denominator = min(window, actual_sample) so partial windows are still valid.
                    over_l5 = sum(1 for v in values[:5] if v > line) / min(5, len(values[:5])) if values[:5] else 0
                    over_l10 = sum(1 for v in values[:10] if v > line) / min(10, len(values[:10])) if values[:10] else 0
                    over_l15 = sum(1 for v in values[:15] if v > line) / min(15, len(values[:15])) if values[:15] else 0
                    over_l20 = sum(1 for v in values[:20] if v > line) / min(20, len(values[:20])) if values[:20] else 0
                    under_l5 = sum(1 for v in values[:5] if v <= line) / min(5, len(values[:5])) if values[:5] else 0
                    under_l10 = sum(1 for v in values[:10] if v <= line) / min(10, len(values[:10])) if values[:10] else 0
                    under_l15 = sum(1 for v in values[:15] if v <= line) / min(15, len(values[:15])) if values[:15] else 0
                    under_l20 = sum(1 for v in values[:20] if v <= line) / min(20, len(values[:20])) if values[:20] else 0

                    # Store with original prop_key (lowercase) so Module F lookup matches:
                    # Module F: stat_key='points' → _hr_by_mkt.get('points') → finds entry
                    hit_rates[prop_key.lower()] = {
                        'over_l5': round(over_l5, 3),
                        'over_l10': round(over_l10, 3),
                        'over_l15': round(over_l15, 3),
                        'over_l20': round(over_l20, 3),
                        'under_l5': round(under_l5, 3),
                        'under_l10': round(under_l10, 3),
                        'under_l15': round(under_l15, 3),
                        'under_l20': round(under_l20, 3),
                    }

            # Add vs-opponent-defense-scheme L5 hit rates using pre-loaded vs_scheme_cache.
            # team_scheme_map is loaded from team_scheme_cache.active_style at init — live DB data.
            # Skips when opponent scheme is NEUTRAL (no differentiated signal).
            opponent_team = p_dict.get('opponent', '')
            if opponent_team and hit_rates and player_id:
                opponent_scheme = self.team_scheme_map.get(opponent_team)
                if opponent_scheme and opponent_scheme != 'NEUTRAL':
                    for prop_key, hr_entry in hit_rates.items():
                        prop_upper = prop_key.upper()
                        cache_key = _PROP_KEY_TO_CACHE.get(prop_upper, prop_upper)
                        scheme_values = self.vs_scheme_cache.get((player_id, cache_key, opponent_scheme), [])
                        if scheme_values:
                            line = props_fmt.get(prop_key, {}).get('line', 0)
                            if line > 0:
                                n = len(scheme_values)
                                vs_over = sum(1 for v in scheme_values if v > line) / n
                                vs_under = sum(1 for v in scheme_values if v <= line) / n
                                hr_entry['over_vs_scheme_l5'] = round(vs_over, 3)
                                hr_entry['under_vs_scheme_l5'] = round(vs_under, 3)
                                hr_entry['vs_scheme'] = opponent_scheme
                                hr_entry['vs_scheme_sample'] = n

        if hit_rates:
            p_dict['hit_rates_by_market'] = hit_rates

    def snapshot_opening_lines(self, games_dict, game_date):
        """Persist opening prop lines to prop_line_snapshots table."""
        import datetime
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            inserted = 0
            for game_id, game in games_dict.items():
                home = game.get('home', '')
                away = game.get('away', '')
                home_abbr = self._get_abbr(home)
                away_abbr = self._get_abbr(away)

                for player_name, stats in game.get('props', {}).items():
                    normalized = self._normalize_name(player_name)
                    player_id, team = self.name_to_id.get(normalized, (None, ''))

                    for stat_key, prop_data in stats.items():
                        if not isinstance(prop_data, dict):
                            continue

                        line = prop_data.get('line', 0)
                        if line <= 0:
                            continue

                        # Determine opponent
                        opp = away_abbr if team == home_abbr else home_abbr

                        cursor.execute("""
                            INSERT OR IGNORE INTO prop_line_snapshots (
                                game_date, player_name, player_id, stat_category,
                                opening_line, opening_odds_over, opening_odds_under,
                                opening_bookmaker, vendor_count, source_quality,
                                team, opponent, captured_at
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            game_date,
                            player_name,
                            player_id,
                            stat_key.upper(),
                            line,
                            prop_data.get('odds_over'),
                            prop_data.get('odds_under'),
                            prop_data.get('book_over'),
                            prop_data.get('vendor_count', 1),
                            prop_data.get('source_quality'),
                            team,
                            opp,
                            datetime.datetime.now().isoformat()
                        ))
                        inserted += cursor.rowcount

            conn.commit()
            conn.close()
            print(f"   >>> Opening lines snapshotted: {inserted} rows")
        except Exception as e:
            print(f"   ⚠️ Snapshot failed: {e}")

    def _get_abbr(self, team_name):
        """Convert full team name to abbreviation."""
        team_map = {
            'Atlanta Hawks': 'ATL', 'Boston Celtics': 'BOS', 'Brooklyn Nets': 'BKN',
            'Charlotte Hornets': 'CHA', 'Chicago Bulls': 'CHI', 'Cleveland Cavaliers': 'CLE',
            'Dallas Mavericks': 'DAL', 'Denver Nuggets': 'DEN', 'Detroit Pistons': 'DET',
            'Golden State Warriors': 'GSW', 'Houston Rockets': 'HOU', 'Indiana Pacers': 'IND',
            'LA Clippers': 'LAC', 'Los Angeles Clippers': 'LAC', 'LA Lakers': 'LAL',
            'Los Angeles Lakers': 'LAL', 'Memphis Grizzlies': 'MEM', 'Miami Heat': 'MIA',
            'Milwaukee Bucks': 'MIL', 'Minnesota Timberwolves': 'MIN', 'New Orleans Pelicans': 'NOP',
            'New York Knicks': 'NYK', 'Oklahoma City Thunder': 'OKC', 'Orlando Magic': 'ORL',
            'Philadelphia 76ers': 'PHI', 'Phoenix Suns': 'PHX', 'Portland Trail Blazers': 'POR',
            'Sacramento Kings': 'SAC', 'San Antonio Spurs': 'SAS', 'Toronto Raptors': 'TOR',
            'Utah Jazz': 'UTA', 'Washington Wizards': 'WAS'
        }
        return team_map.get(team_name, team_name)


# Backwards compatibility: keep old function for any direct imports
def print_sharp_box_score(player_name, sim_results, l10_context, prop_line=None, prop_type="Points", game_context=None):
    """Legacy display function — deprecated. Use LudiEngine class instead."""
    print("⚠️ print_sharp_box_score() is deprecated. Use LudiEngine class.")
    pass
