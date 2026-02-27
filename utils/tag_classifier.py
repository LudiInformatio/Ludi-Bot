# LUDI INFORMATIO | TAG CLASSIFIER UTILITY
# ----------------------------------------
# Purpose: Classify betting recommendations into searchable tags
# Categories: Archetype, Scenario, Matchup, Market
# Storage: JSON array format in bet_recommendations.tags column
# Version: 1.0 (Week 2, Days 3-4)

import json
import sqlite3
from typing import Dict, List, Optional
from utils.mappings import normalize_bdl_abbr


def calculate_streak_score(
    l5_avg: float,
    l10_avg: float,
    l15_avg: float,
    season_avg: float,
) -> int:
    """
    C2: Unified multi-window streak score. Returns -3 to +3.

    Each window contributes +1 (hot) or -1 (cold) independently:
      L5:  ±15% from season avg
      L10: ±10% from season avg
      L15: ±8%  from season avg

    A score ≥ 2 = HOT_STREAK tag. Score ≤ -2 = cold label in morning brief.
    Labels (morning brief): ON FIRE (+3), HOT (+2), COOLING (-2), ICE COLD (-3)
    """
    if not season_avg or season_avg <= 0:
        return 0
    score = 0
    # L5 window
    if l5_avg is not None:
        pct = (l5_avg - season_avg) / season_avg
        if pct >= 0.15:
            score += 1
        elif pct <= -0.15:
            score -= 1
    # L10 window
    if l10_avg is not None:
        pct = (l10_avg - season_avg) / season_avg
        if pct >= 0.10:
            score += 1
        elif pct <= -0.10:
            score -= 1
    # L15 window
    if l15_avg is not None:
        pct = (l15_avg - season_avg) / season_avg
        if pct >= 0.08:
            score += 1
        elif pct <= -0.08:
            score -= 1
    return score


class TagClassifier:
    """
    Classifies betting recommendations into tags for filtering and analysis.

    Four tag categories:
    1. ARCHETYPE TAGS (6): Player style classification
    2. SCENARIO TAGS (4): Context-based modifiers
    3. MATCHUP TAGS (5): Defensive scheme exploits
    4. MARKET TAGS (1+): Correlation and market inefficiencies

    Usage:
        from utils.tag_classifier import TagClassifier
        classifier = TagClassifier()
        tags = classifier.assign_all_tags(player_packet, game_context, yak_report, all_game_props)

    Design Philosophy:
        - Reuses validated logic from Module E (archetypes), Module X (scenarios)
        - JSON array storage for SQLite compatibility
        - Non-mutually exclusive scenarios (player can have multiple tags)
    """

    def __init__(self, db_path: str = "ludi.db"):
        """Initialize with defensive scheme mapping and threshold constants."""
        self.db_path = db_path

        # DEFENSIVE SCHEME MAPPING (30 NBA Teams → 5 Defensive Styles)
        # Source: team_scheme_cache (fallback to static mapping if cache unavailable)
        # NOTE: Using PHX for Phoenix (not PHO) per Tank01 standard
        self.DEFENSIVE_SCHEMES = {
            "ATL": "FUNNEL",
            "BOS": "NEUTRAL",
            "BKN": "PERIMETER",
            "CHA": "PAINT_PACK",
            "CHI": "PAINT_PACK",
            "CLE": "PAINT_PACK",
            "DAL": "NEUTRAL",
            "DEN": "NEUTRAL",
            "DET": "NEUTRAL",
            "GSW": "PERIMETER",
            "HOU": "BLITZ",
            "IND": "FUNNEL",
            "LAC": "FUNNEL",
            "LAL": "PAINT_PACK",
            "MEM": "PAINT_PACK",
            "MIA": "NEUTRAL",
            "MIL": "PERIMETER",
            "MIN": "PAINT_PACK",
            "NOP": "PAINT_PACK",
            "NYK": "PERIMETER",
            "OKC": "PAINT_PACK",
            "ORL": "NEUTRAL",
            "PHI": "BLITZ",
            "PHX": "PERIMETER",
            "POR": "NEUTRAL",
            "SAC": "NEUTRAL",
            "SAS": "PERIMETER",
            "TOR": "PAINT_PACK",
            "UTA": "NEUTRAL",
            "WAS": "NEUTRAL",
        }
        self._load_defensive_schemes_from_cache()

        self.ARCHETYPE_RULES = {}

        # SCENARIO THRESHOLDS
        # C2: HOT_STREAK now uses calculate_streak_score() — score ≥ 2 triggers the tag
        self.BENEFICIARY_USAGE_THRESHOLD = 0.18  # Minimum usage to be considered key player
        self.HIGH_UNIT_THRESHOLD = 1.2  # For correlated SGP detection

        print("✅ TagClassifier initialized with synced defensive schemes")

    def _load_defensive_schemes_from_cache(self) -> None:
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='team_scheme_cache'"
            )
            if not cursor.fetchone():
                conn.close()
                return
            cursor.execute(
                """
                SELECT team_abbr, active_style
                FROM team_scheme_cache
                WHERE scheme_type = 'DEFENSE'
                """
            )
            rows = cursor.fetchall()
            conn.close()
            if not rows:
                return
            for team, style in rows:
                if not style or style == "INSUFFICIENT":
                    self.DEFENSIVE_SCHEMES[team] = "NEUTRAL"
                else:
                    self.DEFENSIVE_SCHEMES[team] = style
        except Exception:
            return

    def assign_archetype_tag(self, player_stats: Dict) -> str:
        """
        Assign single archetype tag based on player statistics.

        Mirrors Module E logic (_assign_archetype method, lines 114-125).
        Uses decision tree with priority ordering - first match wins.

        Args:
            player_stats: Player packet with 'base_pts', 'base_reb', 'base_ast',
                         'base_usg', 'base_3pm' fields

        Returns:
            Single archetype tag string (e.g., "STRETCH_BIG", "GENERALIST")

        Example:
            >>> stats = {'base_reb': 7.2, 'base_3pm': 2.1, 'base_pts': 15}
            >>> classifier.assign_archetype_tag(stats)
            'STRETCH_BIG'
        """
        if player_stats.get('archetype'):
            return player_stats['archetype']

        player_id = player_stats.get('player_id')
        player_name = player_stats.get('name') or player_stats.get('PLAYER_NAME')
        if player_id or player_name:
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                if player_id:
                    cursor.execute("SELECT archetype FROM players WHERE player_id = ? LIMIT 1", (player_id,))
                else:
                    cursor.execute("SELECT archetype FROM players WHERE name = ? LIMIT 1", (player_name,))
                row = cursor.fetchone()
                conn.close()
                if row and row[0]:
                    return row[0]
            except Exception:
                pass

        return "GENERALIST"

    def assign_scenario_tags(self, player: Dict, game_context: Dict,
                            yak_report: Optional[Dict] = None) -> List[str]:
        """
        Assign context-based scenario tags.

        Four possible tags (NOT mutually exclusive):
        - BENEFICIARY: Player scales usage when key teammate is OUT
        - USAGE_VACUUM: This player is the key OUT player creating vacuum
        - MINUTES_LIMIT: Player on injury management restriction
        - HOT_STREAK: Recent L5 performance > 20% above season avg

        Args:
            player: Player packet with scenario, status, L5 stats
            game_context: Game object with players list, opponent info
            yak_report: Optional injury report from Module D

        Returns:
            List of scenario tags (0-4 tags possible)

        Example:
            >>> player = {'scenario': 'WITHOUT Luka Doncic', 'status': 'ACTIVE', ...}
            >>> tags = classifier.assign_scenario_tags(player, game_ctx, yak)
            ['BENEFICIARY_CONFIRMED', 'HOT_STREAK']
        """
        tags = []

        # 1. BENEFICIARY TAG (with WOWY confidence levels)
        # Triggered when scenario indicates "WITHOUT [PLAYER]"
        scenario = player.get('scenario', 'BASE')
        if "WITHOUT" in scenario:
            # Extract absent player name (format: "WITHOUT PlayerName")
            absent_star = scenario.replace("WITHOUT ", "").strip()
            
            # Check for WOWY confidence metadata (added by Module X)
            wowy_confidence = player.get('wowy_confidence', None)
            
            if wowy_confidence == 'high':
                tags.append("BENEFICIARY_CONFIRMED")  # 500+ possessions
            elif wowy_confidence == 'medium':
                tags.append("BENEFICIARY_LIKELY")     # 350+ possessions
            else:
                tags.append("BENEFICIARY")            # Heuristic/low confidence

        # 2. USAGE_VACUUM TAG
        # This player is OUT and has high usage (creating vacuum for teammates)
        status = player.get('status', 'ACTIVE')
        base_usg = player.get('base_usg', 0)
        if status == 'OUT' and base_usg > self.BENEFICIARY_USAGE_THRESHOLD:
            tags.append("USAGE_VACUUM")

        # 3. MINUTES_LIMIT TAG
        # Player flagged by Module D or Module E as having minutes restriction
        if status == 'MINUTES_LIMIT':
            tags.append("MINUTES_LIMIT")

        # Alternative: Check yak_report if provided
        if yak_report and yak_report.get('status') == 'MINUTES_LIMIT':
            if "MINUTES_LIMIT" not in tags:
                tags.append("MINUTES_LIMIT")

        # 4. HOT_STREAK TAG — C2: Unified multi-window scorer (score ≥ 2 = hot streak)
        # Checks PTS, REB, AST independently; tags if any stat shows score ≥ 2
        try:
            hot_streak_detected = False

            for (l5_key, l10_key, l15_key, base_key) in [
                ('L5_PTS', 'L10_PTS', 'L15_PTS', 'base_pts'),
                ('L5_REB', 'L10_REB', 'L15_REB', 'base_reb'),
                ('L5_AST', 'L10_AST', 'L15_AST', 'base_ast'),
            ]:
                season_avg = player.get(base_key, 0) or 0
                l5_avg = player.get(l5_key) or 0
                l10_avg = player.get(l10_key) or 0
                l15_avg = player.get(l15_key) or 0
                if calculate_streak_score(l5_avg, l10_avg, l15_avg, season_avg) >= 2:
                    hot_streak_detected = True
                    break

            if hot_streak_detected:
                tags.append("HOT_STREAK")

        except (KeyError, TypeError, ZeroDivisionError):
            # Missing L5 data (rookies, new signings) - skip hot streak detection
            pass

        return tags

    def assign_matchup_tag(self, opponent_team: str) -> str:
        """
        Assign defensive scheme matchup tag based on opponent.

        Maps opponent team abbreviation to their defensive scheme.
        Handles historical aliases (PHO → PHX) automatically.

        Args:
            opponent_team: 3-letter team abbreviation (e.g., 'OKC', 'GSW')

        Returns:
            Matchup tag with 'vs_' prefix (e.g., "vs_PAINT_PACK", "vs_NEUTRAL")

        Example:
            >>> classifier.assign_matchup_tag('OKC')
            'vs_PAINT_PACK'
            >>> classifier.assign_matchup_tag('PHX')
            'vs_BLITZ'
            >>> classifier.assign_matchup_tag('PHO')  # Historical alias
            'vs_BLITZ'
        """
        if not opponent_team:
            return "vs_NEUTRAL"

        # Normalize team abbreviation (handle case variations)
        opponent_upper = opponent_team.upper().strip()

        # Check for historical alias (PHO → PHX)
        opponent_upper = normalize_bdl_abbr(opponent_upper)

        # Lookup scheme
        scheme = self.DEFENSIVE_SCHEMES.get(opponent_upper, "NEUTRAL")

        return f"vs_{scheme}"

    def assign_market_tags(self, player_name: str, stat_category: str,
                          units: float, all_game_props: List[Dict]) -> List[str]:
        """
        Assign market-based correlation tags.

        Currently implements:
        - CORRELATED_SGP: 2+ high-unit bets (≥1.2u) in same game

        Future extensions could include:
        - CONTRARIAN: Heavy public betting on opposite side
        - STEAM_MOVE: Line movement indicating sharp action
        - CLOSING_VALUE: Line has moved in our favor since logging

        Args:
            player_name: Name of player for this bet
            stat_category: Stat being bet (PTS, REB, AST, etc.)
            units: Unit size for this bet
            all_game_props: List of ALL player prop dicts in this game

        Returns:
            List of market tags (0-n tags possible)

        Example:
            >>> all_props = [
            ...     {'name': 'Luka', 'units': 1.5, 'stat': 'PTS'},
            ...     {'name': 'Luka', 'units': 1.3, 'stat': 'AST'},
            ...     {'name': 'Kyrie', 'units': 0.5, 'stat': 'PTS'}
            ... ]
            >>> classifier.assign_market_tags('Luka', 'PTS', 1.5, all_props)
            ['CORRELATED_SGP']
        """
        tags = []

        # 1. CORRELATED_SGP TAG
        # Detect if same game has 2+ high-unit bets
        # Logic from Module F lines 178-181
        high_unit_bets = [
            p for p in all_game_props
            if p.get('units', 0) >= self.HIGH_UNIT_THRESHOLD
        ]

        if len(high_unit_bets) >= 2:
            tags.append("CORRELATED_SGP")

        # Future: Add CONTRARIAN, STEAM_MOVE, CLOSING_VALUE tags here

        return tags

    def assign_all_tags(self, player_packet: Dict, game_context: Dict,
                       yak_report: Optional[Dict] = None,
                       all_game_props: Optional[List[Dict]] = None) -> List[str]:
        """
        Master function to assign all tag categories at once.

        Combines archetype, scenario, matchup, and market tags into single list.
        Tags are returned in logical order: Archetype, Scenarios, Matchup, Market.

        Args:
            player_packet: Full player dict with stats, status, scenario
            game_context: Game object with opponent, spread, players
            yak_report: Optional Module D injury intelligence
            all_game_props: Optional list of all props in game (for correlation)

        Returns:
            Combined list of all assigned tags

        Example:
            >>> player = {
            ...     'name': 'Kyrie Irving',
            ...     'base_pts': 25.0, 'base_usg': 0.32, 'base_3pm': 2.9,
            ...     'base_ast': 5.5, 'scenario': 'WITHOUT Luka Doncic',
            ...     'status': 'ACTIVE', 'opponent': 'OKC'
            ... }
            >>> game_ctx = {'opponent': 'OKC', 'spread': 6.5, 'players': [...]}
            >>> tags = classifier.assign_all_tags(player, game_ctx)
            >>> print(tags)
            ['SNIPER_ELITE', 'BENEFICIARY', 'vs_PAINT_PACK']
        """
        all_tags = []

        # 1. Archetype tag (single tag)
        archetype = self.assign_archetype_tag(player_packet)
        all_tags.append(archetype)

        # 2. Scenario tags (0-4 tags)
        scenario_tags = self.assign_scenario_tags(
            player_packet,
            game_context,
            yak_report
        )
        all_tags.extend(scenario_tags)

        # 3. Matchup tag (single tag)
        # Try to get opponent from multiple sources
        opponent = player_packet.get('opponent') or game_context.get('opponent', '')
        matchup_tag = self.assign_matchup_tag(opponent)
        all_tags.append(matchup_tag)

        # 4. Market tags (0-n tags)
        if all_game_props is not None:
            market_tags = self.assign_market_tags(
                player_packet.get('name', ''),
                player_packet.get('stat_category', ''),
                player_packet.get('units', 0),
                all_game_props
            )
            all_tags.extend(market_tags)

        return all_tags

    def format_tags_for_db(self, tags: List[str]) -> str:
        """
        Format tag list for database storage.

        Uses JSON array format for better SQLite querying with JSON functions.
        Example: ["STRETCH_BIG", "vs_PAINT_PACK", "CORRELATED_SGP"]

        Args:
            tags: List of tag strings

        Returns:
            JSON-formatted string for database TEXT column

        Example:
            >>> tags = ['STRETCH_BIG', 'vs_PAINT_PACK']
            >>> formatted = classifier.format_tags_for_db(tags)
            >>> print(formatted)
            '["STRETCH_BIG", "vs_PAINT_PACK"]'
        """
        return json.dumps(tags)

    def parse_tags_from_db(self, tags_str: str) -> List[str]:
        """
        Parse tags from database storage format.

        Handles JSON array format and provides fallback for edge cases.

        Args:
            tags_str: Stored tag string from database

        Returns:
            List of tag strings

        Example:
            >>> tags_str = '["STRETCH_BIG", "vs_PAINT_PACK"]'
            >>> tags = classifier.parse_tags_from_db(tags_str)
            >>> print(tags)
            ['STRETCH_BIG', 'vs_PAINT_PACK']
        """
        if not tags_str:
            return []

        # Try JSON first
        try:
            return json.loads(tags_str)
        except (json.JSONDecodeError, TypeError):
            pass

        # Fallback: pipe-delimited (legacy support)
        if '|' in tags_str:
            return tags_str.split('|')

        # Single tag (no delimiters)
        return [tags_str]


# Singleton instance for module-level access
_classifier_instance = None

def get_tag_classifier() -> TagClassifier:
    """
    Get singleton instance of TagClassifier.

    Ensures only one instance exists across all imports,
    preventing duplicate initialization.

    Returns:
        TagClassifier instance

    Usage:
        from utils.tag_classifier import get_tag_classifier
        classifier = get_tag_classifier()
        tags = classifier.assign_all_tags(player, game_ctx)
    """
    global _classifier_instance
    if _classifier_instance is None:
        _classifier_instance = TagClassifier()
    return _classifier_instance


if __name__ == "__main__":
    # Quick self-test
    print("\n🧪 TagClassifier Self-Test\n")

    classifier = TagClassifier()

    # Test 1: Archetype classification
    print("Test 1: Archetype Classification")
    test_players = [
        {'name': 'Karl-Anthony Towns', 'base_reb': 8.5, 'base_3pm': 2.2, 'base_pts': 22},
        {'name': 'Giannis', 'base_pts': 30, 'base_usg': 0.35, 'base_3pm': 0.5},
        {'name': 'Duncan Robinson', 'base_3pm': 3.2, 'base_ast': 2.1},
        {'name': 'Role Player', 'base_pts': 12, 'base_reb': 4, 'base_ast': 2},
    ]

    for p in test_players:
        archetype = classifier.assign_archetype_tag(p)
        print(f"   {p['name']}: {archetype}")

    # Test 2: Matchup tags
    print("\nTest 2: Matchup Tags")
    opponents = ['OKC', 'PHX', 'PHO', 'GSW', 'BKN']
    for team in opponents:
        tag = classifier.assign_matchup_tag(team)
        print(f"   vs {team}: {tag}")

    # Test 3: Scenario tags
    print("\nTest 3: Scenario Tags")
    scenario_player = {
        'scenario': 'WITHOUT Luka Doncic',
        'status': 'ACTIVE',
        'base_pts': 18.0,
        'L5_PTS': 23.0,  # Hot streak
        'base_usg': 0.20
    }
    game_ctx = {'opponent': 'OKC', 'players': []}
    scenario_tags = classifier.assign_scenario_tags(scenario_player, game_ctx)
    print(f"   Scenario tags: {scenario_tags}")

    # Test 4: Full pipeline
    print("\nTest 4: Full Tag Assignment")
    full_player = {
        'name': 'Kyrie Irving',
        'opponent': 'OKC',
        'base_pts': 25.0,
        'base_usg': 0.32,
        'base_3pm': 2.9,
        'base_ast': 5.5,
        'L5_PTS': 30.5,
        'scenario': 'WITHOUT Luka Doncic',
        'status': 'ACTIVE',
        'stat_category': 'PTS',
        'units': 1.4
    }
    all_props = [
        {'name': 'Kyrie', 'stat': 'PTS', 'units': 1.4},
        {'name': 'Kyrie', 'stat': 'AST', 'units': 1.2}
    ]

    tags = classifier.assign_all_tags(full_player, game_ctx, None, all_props)
    formatted = classifier.format_tags_for_db(tags)
    parsed = classifier.parse_tags_from_db(formatted)

    print(f"   All tags: {tags}")
    print(f"   Formatted for DB: {formatted}")
    print(f"   Parsed from DB: {parsed}")

    print("\n✅ Self-test complete!\n")
