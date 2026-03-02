import pandas as pd
import numpy as np
import sqlite3
import config
from database import DB_PATH

# Module X — Scenario building thresholds
EFFECTIVE_STARTER_MIN_THRESHOLD = 25.0   # MPG threshold for bench player starter elevation
PRIMARY_BACKUP_ABSORPTION = 0.60         # Usage absorption rate for primary beneficiary (heuristic)
SECONDARY_BACKUP_ABSORPTION = 0.30       # Usage absorption rate for secondary beneficiary
DEPTH_CHART_ABSORPTION = 0.70            # Absorption rate from depth_chart position-specific backup
MAX_ABSORPTION_CAP = 0.80                # Maximum absorption rate any beneficiary can receive
EFFICIENCY_DAMPENING = 0.90              # Stat scale dampening for elevated-role players
WOWY_LOW_CONFIDENCE_PENALTY = 0.20       # Additional reduction for low-confidence WOWY data
WOWY_MEDIUM_CONFIDENCE_PENALTY = 0.10    # Additional reduction for medium-confidence WOWY data

# ==========================================
# LUDI INFORMATIO | MODULE X: SCENARIO BUILDER
# V3.7 - LIVE SCHEMA COMPATIBLE (UPPERCASE KEYS)
# ==========================================

class ScenarioBuilder:
    def __init__(self):
        print(f"\n{'='*40}")
        print(f"LUDI INFORMATIO: MODULE X (SCENARIO V3.7) ONLINE")
        print(f"   >>> DYNAMIC ROSTERS | LIVE SCHEMA ACTIVE")
        print(f"{'='*40}")
        
        try:
            self.conn = sqlite3.connect(DB_PATH, timeout=30)
            self.conn.row_factory = sqlite3.Row
        except sqlite3.Error as e:
            print(f"   [Module X] FATAL: Could not connect to ludi.db: {e}")
            self.conn = None

        self.TANK_KEY = getattr(config, 'TANK01_KEY', '')

        # Conditional baseline pre-loads (loaded once at init, used across all scenarios)
        self._ha_splits = self._load_ha_splits()         # Condition 1: home/away split
        self._starter_splits = self._load_starter_splits()  # Condition 4: starter/bench split
        self._scheme_map = self._load_scheme_map()       # Condition 3: scheme baseline
        # Condition 2 (lineup-conditional) uses self.wowy_calc which is already loaded

    def __del__(self):
        if self.conn:
            self.conn.close()

    def _load_ha_splits(self) -> dict:
        """Pre-load home vs away avg PPG per player for conditional baseline."""
        if not self.conn: return {}
        try:
            rows = self.conn.execute('''
                SELECT l.player_id,
                       l.home_or_away,
                       COUNT(*) as n_games,
                       AVG(l.pts) as avg_pts,
                       AVG(l.fta) as avg_fta,
                       AVG(l.ast) as avg_ast,
                       AVG(l.reb) as avg_reb
                FROM player_game_logs l
                WHERE l.home_or_away IS NOT NULL
                  AND l.home_or_away != ''
                  AND l.minutes >= 20
                GROUP BY l.player_id, l.home_or_away
                HAVING COUNT(*) >= 3
            ''').fetchall()

            result = {}
            for row in rows:
                pid, ha, n, pts, fta, ast, reb = row['player_id'], row['home_or_away'], row['n_games'], row['avg_pts'], row['avg_fta'], row['avg_ast'], row['avg_reb']
                if pid not in result:
                    result[pid] = {}
                result[pid][ha] = {'n': n, 'pts': pts or 0, 'fta': fta or 0,
                                   'ast': ast or 0, 'reb': reb or 0}
            return result
        except sqlite3.Error as e:
            print(f"   [Module X] _load_ha_splits failed: {e}")
            return {}

    def _load_starter_splits(self) -> dict:
        """Pre-load starter vs bench avg stats per player."""
        if not self.conn: return {}
        try:
            rows = self.conn.execute('''
                SELECT l.player_id,
                       l.started,
                       COUNT(*) as n_games,
                       AVG(l.pts) as avg_pts,
                       AVG(l.fta) as avg_fta,
                       AVG(l.ast) as avg_ast,
                       AVG(l.reb) as avg_reb
                FROM player_game_logs l
                WHERE l.started IS NOT NULL
                  AND l.minutes >= 15
                GROUP BY l.player_id, l.started
                HAVING COUNT(*) >= 3
            ''').fetchall()

            result = {}
            for row in rows:
                pid, started, n, pts, fta, ast, reb = row['player_id'], row['started'], row['n_games'], row['avg_pts'], row['avg_fta'], row['avg_ast'], row['avg_reb']
                if pid not in result:
                    result[pid] = {}
                key = 'starter' if started == 1 else 'bench'
                result[pid][key] = {'n': n, 'pts': pts or 0, 'fta': fta or 0,
                                    'ast': ast or 0, 'reb': reb or 0}
            return result
        except sqlite3.Error as e:
            print(f"   [Module X] _load_starter_splits failed: {e}")
            return {}

    def _load_scheme_map(self) -> dict:
        """Pre-load current defensive scheme per team."""
        if not self.conn: return {}
        try:
            # Corrected query based on schema investigation
            rows = self.conn.execute('''
                SELECT team_abbr, active_style
                FROM team_scheme_cache
            ''').fetchall()
            return {r['team_abbr']: r['active_style'] for r in rows}
        except Exception as e:
            print(f"   [Module X] scheme_map load failed (non-fatal): {e}")
            return {}

    def _build_conditional_baseline(self, player: dict, scenario_context: dict) -> dict:
        """
        Compute a combined conditional modifier for a player given tonight's context.

        Returns a dict of stat-specific multipliers, e.g.:
        {'pts': 1.08, 'fta': 1.12, 'ast': 1.02, 'reb': 0.96, 'combined_n': 15}

        Uses dampened modifier approach:
        - modifier = conditional_avg / season_avg
        - dampened = 1 + (modifier - 1) * confidence_weight
        - confidence_weight = clamp((n_qualifying - 5) / 15.0, 0.0, 1.0)
        """
        pid = player.get('player_id')
        modifiers = {}  # stat_key -> list of (modifier_value, n_games)

        # --- Condition 1: H/A Split ---
        ha_context = scenario_context.get('home_or_away')  # 'home' or 'away'
        ha_data = self._ha_splits.get(pid, {})

        if ha_context and ha_data:
            ha_stats = ha_data.get(ha_context)
            all_games = list(ha_data.values())
            if ha_stats and len(all_games) >= 2:
                # Compute season avg from both home + away games
                total_n = sum(g['n'] for g in all_games)
                for stat in ['pts', 'fta', 'ast', 'reb']:
                    season_avg = sum(g[stat] * g['n'] for g in all_games) / total_n if total_n > 0 else 0
                    conditional_avg = ha_stats[stat]
                    n = ha_stats['n']
                    if season_avg > 0 and n >= 3:
                        raw_mod = conditional_avg / season_avg
                        weight = min(1.0, max(0.0, (n - 5) / 15.0))
                        dampened = 1.0 + (raw_mod - 1.0) * weight
                        modifiers.setdefault(stat, []).append((dampened, n))

        # --- Condition 4: Starter/Bench Split ---
        # Only applies when player is an effective_starter (bench player elevated tonight)
        if player.get('effective_starter') and not player.get('is_starter'):
            starter_data = self._starter_splits.get(pid, {})
            starter_stats = starter_data.get('starter')
            bench_stats = starter_data.get('bench')

            if starter_stats and bench_stats:
                # Compare starter games vs bench games for this player
                for stat in ['pts', 'fta', 'ast', 'reb']:
                    bench_avg = bench_stats[stat]
                    starter_avg = starter_stats[stat]
                    n = starter_stats['n']
                    if bench_avg > 0 and n >= 3:
                        # Modifier: how much better does this player perform when starting?
                        raw_mod = starter_avg / bench_avg
                        weight = min(1.0, max(0.0, (n - 3) / 12.0)) # Lower threshold for starter split
                        dampened = 1.0 + (raw_mod - 1.0) * weight
                        modifiers.setdefault(stat, []).append((dampened, n))

        # --- Condition 3: Scheme-Conditional ---
        opponent_team = scenario_context.get('opponent_team')
        opp_scheme = self._scheme_map.get(opponent_team) if opponent_team else None
        # NOTE: Scheme-conditional baseline requires per-game scheme JOIN — deferred to Sprint 2
        # Current: scheme modifier comes from Module E archetype matchup, not baseline shift
        # Placeholder for future: when player_game_logs has opponent_scheme column per game

        # --- Combine all modifiers ---
        # For each stat: average all condition modifiers (weighted by n), then cap
        combined = {}
        for stat, mod_list in modifiers.items():
            if not mod_list:
                combined[stat] = 1.0
                continue
            # Simple average of all dampened modifiers for this stat
            avg_mod = sum(m for m, n in mod_list) / len(mod_list)
            # Per-condition cap: ±20%
            combined[stat] = max(0.80, min(1.20, avg_mod))

        # Apply combined cap: ±25% across all stats
        pts_mod = combined.get('pts', 1.0)
        fta_mod = combined.get('fta', 1.0)
        ast_mod = combined.get('ast', 1.0)
        reb_mod = combined.get('reb', 1.0)

        # Don't over-dampen: if any single modifier is significant, trust it
        # (combined cap handles outliers without zeroing signal)
        combined['pts'] = max(0.75, min(1.25, pts_mod))
        combined['fta'] = max(0.75, min(1.25, fta_mod))
        combined['ast'] = max(0.75, min(1.25, ast_mod))
        combined['reb'] = max(0.75, min(1.25, reb_mod))

        return combined

    def _classify_vacuum_smart(self, out_player_name: str, team_abbr: str) -> dict:
        """
        Classify how much vacuum to apply for an absent player using DB data.
        Returns: {'status': str, 'scale': float, 'reason': str}
        
        Graceful fallback: if player_injuries table missing, returns scale=1.0 (full vacuum).
        """
        import sqlite3
        try:
            conn = sqlite3.connect("ludi.db", timeout=30)
            conn.execute("PRAGMA journal_mode=WAL")
            c = conn.cursor()
            # Phase 8.12: filter by team to avoid stale injury from old team post-trade
            c.execute("""
                SELECT days_out FROM player_injuries
                WHERE player_name = ? AND resolved_at IS NULL
                  AND snapshot_time >= datetime('now','-14 days')
                  AND (team_abbreviation = ? OR team_abbreviation IS NULL)
                ORDER BY snapshot_time DESC LIMIT 1
            """, (out_player_name, team_abbr))
            row = c.fetchone()
            conn.close()

            if not row:
                return {'status': 'active', 'scale': 1.0, 'reason': 'Not in injury table'}

            days_out = row[0] or 0

            if days_out > 14:
                return {'status': 'absorbed', 'scale': 0.0, 'reason': f'{days_out} days — team adjusted'}
            elif days_out <= 3:
                return {'status': 'active', 'scale': 1.0, 'reason': f'Recent absence ({days_out}d)'}
            else:
                scale = round(1.0 - ((days_out - 3) / 11 * 0.7), 2)
                return {'status': 'partial', 'scale': scale, 'reason': f'{days_out}d out — {int(scale*100)}% weight'}
        except Exception as e:
            print(f"[ScenarioBuilder] Smart vacuum fallback: {e}")
            return {'status': 'active', 'scale': 1.0, 'reason': 'DB fallback'}

    def _get_l10_stats(self, player_name: str, team_abbr: str) -> dict:
        """Get last 10 games average stats from player_game_logs. Returns {} if unavailable."""
        import sqlite3
        try:
            conn = sqlite3.connect("ludi.db", timeout=30)
            conn.execute("PRAGMA journal_mode=WAL")
            c = conn.cursor()
            c.execute("""
                SELECT AVG(pts), AVG(reb), AVG(ast), AVG(minutes), AVG(fga), AVG(fg3a), AVG(fta)
                FROM (
                    SELECT pts, reb, ast, minutes, fga, fg3a, fta
                    FROM player_game_logs
                    WHERE player_name = ? AND team_abbreviation = ?
                    ORDER BY game_date DESC LIMIT 10
                )
            """, (player_name, team_abbr))
            row = c.fetchone()
            conn.close()
            if not row or row[0] is None:
                return {}
            return {
                'PTS': round(row[0] or 0, 1), 'REB': round(row[1] or 0, 1),
                'AST': round(row[2] or 0, 1), 'MIN': round(row[3] or 0, 1),
                'FGA': round(row[4] or 0, 1), 'FG3A': round(row[5] or 0, 1),
                'FTA': round(row[6] or 0, 1)
            }
        except Exception as e:
            print(f"[Module X _get_l10_stats]: {e}")
            return {}

    def generate_scenarios(self, processed_slate):
        """
        Input: List of Game Objects from Module B/Sim Engine.
        Output: Enhanced list containing Base AND Contingency scenarios.
        """
        final_scenarios = []
        
        for game in processed_slate:
            # 1. Base Scenario (All Active/GTD players included)
            base_scenario = game.copy()
            base_scenario['scenario_name'] = "BASE"
            final_scenarios.append(base_scenario)
            
            # 2. GTD Forks (The "Scenario Fork")
            # Create branching realities for Questionable/GTD stars
            for player in game['players']:
                # Only fork for KEY players who are uncertain
                is_key_player = player.get('base_usg', 0) > 0.18 and player.get('base_min', 0) > 24.0
                is_uncertain = player.get('status') in ['Q', 'GTD', 'Questionable']
                
                if is_key_player and is_uncertain:
                    # Scenario A: Player Plays (Standard Risk Tax)
                    # (This is effectively covered by BASE, but we can make it explicit or apply tax)
                    # For now, BASE assumes they play. We could add a specific "Risk Adjusted" one if needed.
                    
                    # Scenario B: Player Sits (Usage Vacuum)
                    contingency = self._build_out_scenario(game, player)
                    if contingency:
                        # Keep "WITHOUT" format for resolver detection
                        # (Module D resolve_scenarios() searches for "WITHOUT" keyword)
                        final_scenarios.append(contingency)
                        
        return final_scenarios

    def _build_out_scenario(self, game, starter_out):
        scenario = game.copy()
        scenario['scenario_name'] = f"WITHOUT {starter_out['PLAYER_NAME']}"
        scenario['players'] = [] 
        
        # DYNAMIC: Find the backup from the current roster
        # V3.8: Returns dict with 'matrix' and 'confidence' keys if WOWY used
        backup_data = self._infer_dynamic_backup(game['players'], starter_out)
        
        # Extract matrix and confidence
        if isinstance(backup_data, dict) and 'matrix' in backup_data:
            minutes_matrix = backup_data['matrix']
            wowy_confidence = backup_data.get('confidence', None)
        else:
            # Fallback: Old format (just dict of names:rates)
            minutes_matrix = backup_data if isinstance(backup_data, dict) else {}
            wowy_confidence = None
        
        vacuum_info = self._classify_vacuum_smart(
            starter_out.get('PLAYER_NAME', ''),
            starter_out.get('TEAM_ABBREVIATION', '')
        )
        vacuum_scale = vacuum_info.get('scale', 1.0) if isinstance(vacuum_info, dict) else 1.0

        vacated_usage = starter_out.get('base_usg', 0) * vacuum_scale
        vacated_mins = starter_out.get('base_min', 0) * vacuum_scale
        
        raw_players = []
        
        for p in game['players']:
            new_p = p.copy()
            
            # --- CASE A: The Player Who Is Out ---
            if (p.get('PLAYER_ID') or p.get('player_id')) == (starter_out.get('PLAYER_ID') or starter_out.get('player_id')):
                # KILL LIST: Updated to match LIVE SCHEMA (Uppercase)
                keys_to_zero = [
                    'MIN', 'PTS', 'AST', 'REB', 'FG3M',
                    'STL', 'BLK', 'TOV', 
                    'FGA', 'FG3A', 'FTA',
                    'OREB', 'DREB'
                ]
                for k in keys_to_zero:
                    if k in new_p:
                        new_p[k] = 0.0
            
            # --- CASE B: The Beneficiaries (Dynamic Matrix) ---
            elif p['PLAYER_NAME'] in minutes_matrix:
                absorption_rate = minutes_matrix[p['PLAYER_NAME']]
                added_min = vacated_mins * absorption_rate
                
                l10_stats = self._get_l10_stats(
                    p.get('PLAYER_NAME', ''),
                    p.get('TEAM_ABBREVIATION', '')
                )
                if l10_stats:
                    for key in ['PTS', 'REB', 'AST', 'MIN', 'FGA', 'FG3A', 'FTA']:
                        if key in l10_stats:
                            new_p[key] = l10_stats[key]

                old_min = p.get('base_min', 0)
                if l10_stats and l10_stats.get('MIN') is not None:
                    old_min = l10_stats.get('MIN', old_min)
                # Cap minutes reasonable (max 38 or +12 bump)
                new_min = min(old_min + added_min, 38.0, old_min + 12.0)

                scale_ratio = new_min / old_min if old_min > 0 else 1.0

                new_p['MIN'] = new_min

                # H4: Mark as effective_starter if elevated to starter-level minutes
                if new_min >= EFFECTIVE_STARTER_MIN_THRESHOLD:
                    new_p['effective_starter'] = True
                
                # Attach WOWY confidence for tag classifier
                if wowy_confidence:
                    new_p['wowy_confidence'] = wowy_confidence

                # Efficiency Tax (10% decay on volume efficiency)
                dampened_ratio = 1.0 + ((scale_ratio - 1.0) * EFFICIENCY_DAMPENING)

                # WOWY Confidence Penalty (Phase 6.3 Enhancement)
                # Dampen the effect further if we don't fully trust the WOWY sample
                if wowy_confidence == 'low':
                    # Extra 20% dampening: if dampened_ratio was 1.54, now 1.432
                    dampened_ratio = 1.0 + ((dampened_ratio - 1.0) * (1.0 - WOWY_LOW_CONFIDENCE_PENALTY))
                elif wowy_confidence == 'medium':
                    # Extra 10% dampening: if dampened_ratio was 1.54, now 1.486
                    dampened_ratio = 1.0 + ((dampened_ratio - 1.0) * (1.0 - WOWY_MEDIUM_CONFIDENCE_PENALTY))
                # HIGH confidence: no extra penalty (already has 90% efficiency tax)

                # SCALE LIST: Updated to match LIVE SCHEMA (Uppercase)
                stats_to_scale = [
                    'PTS', 'AST', 'REB', 'FG3M', 
                    'STL', 'BLK', 'TOV',
                    'FGA', 'FG3A', 'FTA',
                    'OREB', 'DREB'
                ]
                for stat in stats_to_scale:
                    if stat in new_p:
                        new_p[stat] = round(new_p[stat] * dampened_ratio, 1)

            # --- CASE C: The Alpha Stars (Usage Vacuum) ---
            elif p.get('TEAM_ABBREVIATION') == starter_out.get('TEAM_ABBREVIATION') and p.get('base_usg', 0) > 0.22:
                # Stars don't play more minutes, but they shoot more
                boost = 1 + (vacated_usage * 0.15)
                scoring_keys = ['PTS', 'AST', 'FGA', 'FTA']
                for k in scoring_keys:
                    if k in new_p:
                        new_p[k] = round(new_p[k] * boost, 1)

            # --- CASE D: Everyone Else ---
            else:
                pass 
                
            raw_players.append(new_p)
            
        final_players = self._apply_vegas_guardrail(raw_players, game.get('odds', {}))
        scenario['players'] = final_players
        
        return scenario

    def _lookup_wowy_observed(self, star_canonical_id: str, team_abbr: str) -> list:
        """
        Sprint 4 / Tier 0A: Query player_wowy_observed for empirical beneficiary data.

        Returns pairs sorted by (pts_delta × role_match_score) DESC.
        Filters: confidence_adjusted != 'TOO_LOW', pts_delta > 0, obs_games >= 5.
        Returns [] on any error (graceful degradation).
        """
        if not star_canonical_id or not team_abbr:
            return []
        try:
            conn = sqlite3.connect('ludi.db')
            conn.row_factory = sqlite3.Row
            rows = conn.execute("""
                SELECT wo.canonical_id, wo.pts_delta, wo.min_delta,
                       wo.obs_games, wo.confidence, wo.confidence_adjusted,
                       wo.role_match_score, wo.obs_min,
                       pci.full_name AS beneficiary_name
                FROM player_wowy_observed wo
                JOIN player_canonical_ids pci ON pci.canonical_id = wo.canonical_id
                WHERE wo.star_canonical_id = ?
                  AND wo.team_abbreviation = ?
                  AND wo.confidence_adjusted NOT IN ('TOO_LOW')
                  AND wo.pts_delta > 0
                  AND wo.obs_games >= 5
                ORDER BY (wo.pts_delta * COALESCE(wo.role_match_score, 0.4)) DESC
                LIMIT 5
            """, (str(star_canonical_id), team_abbr)).fetchall()
            conn.close()
            return [dict(r) for r in rows]
        except Exception as e:
            print(f"[Module X] wowy_observed lookup failed: {e}")
            return []

    def _lookup_beneficiary_minutes(self, out_player_id: str, team_abbr: str) -> list:
        """
        Phase 8.9 Tier 0: Query beneficiary_minutes table for data-driven backup estimation.

        Returns list of dicts sorted by minutes_delta DESC:
          [{'player_id': str, 'name': str, 'minutes_delta': float, 'games_without': int}]
        Returns [] on any error (graceful degradation).
        """
        if not out_player_id or not team_abbr:
            return []
        try:
            conn = sqlite3.connect('ludi.db')
            rows = conn.execute("""
                SELECT beneficiary_player_id, beneficiary_player_name,
                       minutes_delta, games_without
                FROM beneficiary_minutes
                WHERE out_player_id = ? AND team_abbreviation = ? AND minutes_delta > 1.0
                ORDER BY minutes_delta DESC
                LIMIT 5
            """, (str(out_player_id), team_abbr)).fetchall()
            conn.close()
            return [
                {
                    'player_id': r[0],
                    'name': r[1],
                    'minutes_delta': r[2],
                    'games_without': r[3],
                }
                for r in rows
            ]
        except Exception as e:
            print(f"[Module X _lookup_beneficiary_minutes]: {e}")
            return []

    def _infer_dynamic_backup(self, all_players, starter_out):
        """
        Scans the game roster to find the most likely backup.

        V3.8 UPGRADE: Uses WOWY data when available (350+ poss confidence),
        falls back to heuristic 60/30 split for insufficient samples.

        Phase 7.4: Also sets wowy_confidence for all players in the game
        by querying player_season_wowy table.

        Phase 8.9: TIER 0 — beneficiary_minutes table (data-driven absence cross-join).

        Returns:
            dict with 'matrix' (name:absorption_rate) and 'confidence' (high/medium/low/None)
        """
        team_abbr = starter_out.get('TEAM_ABBREVIATION')

        # Phase 7.4: Set wowy_confidence for all players in game
        self._set_wowy_confidence_for_players(all_players)

        # TIER 0A: player_wowy_observed — empirical, role-match weighted (Sprint 4)
        # Only available after build_wowy_observed.py has run (Phase 2B+).
        # Hybrid off/def system (Feb 22 2026): players.archetype is now always an offensive role.
        # ALL players generate a scoring vacuum when absent. Defensive identity is in
        # players.defensive_tag and used for matchup context — not for vacuum skip logic.
        star_id = str(starter_out.get('PLAYER_ID', '') or starter_out.get('player_id', ''))
        star_arch = starter_out.get('archetype', '') or ''
        wowy_rows = self._lookup_wowy_observed(star_id, team_abbr)
        if wowy_rows:
            star_base_pts = starter_out.get('PTS', 20) or 20
            absorption = {}
            for r in wowy_rows:
                ben_name = r.get('beneficiary_name')
                pts_delta = r.get('pts_delta') or 0
                if ben_name and pts_delta > 0:
                    # Normalize to fraction of star's offensive output (absorption rate)
                    absorption[ben_name] = round(min(pts_delta / max(star_base_pts, 1), MAX_ABSORPTION_CAP), 3)
            if absorption:
                print(f"[Module X] TIER 0A wowy_observed for {starter_out.get('PLAYER_NAME', '?')}: "
                      f"{list(absorption.keys())[:3]}")
                return {'matrix': absorption, 'confidence': 'high'}

        # H5: TIER 0 - depth_charts lookup (position-specific backup)
        try:
            conn = sqlite3.connect('ludi.db')
            c = conn.cursor()
            c.execute("""
                SELECT dc.player_name
                FROM depth_charts dc
                WHERE dc.team_abbr = ?
                  AND dc.position = (
                      SELECT position FROM depth_charts
                      WHERE player_name = ? AND team_abbr = ?
                  )
                  AND dc.depth_order = 2
                  AND dc.player_name != ?
            """, (team_abbr, starter_out.get('PLAYER_NAME', ''), team_abbr, starter_out.get('PLAYER_NAME', '')))
            row = c.fetchone()
            conn.close()
            if row:
                backup_name = row[0]
                absorption = {backup_name: DEPTH_CHART_ABSORPTION}
                print(f"[Module X] H5 depth_charts backup for {starter_out.get('PLAYER_NAME', '?')}: {backup_name}")
                return {'matrix': absorption, 'confidence': 'medium'}
        except Exception as e:
            player_name = starter_out.get('PLAYER_NAME', '?')
            print(f"   [Module X] depth_charts lookup failed for {player_name}: {e}")

        # TIER 0B: beneficiary_minutes — data-driven absence analysis (Phase 8.9)
        bene_data = self._lookup_beneficiary_minutes(
            starter_out.get('PLAYER_ID', ''), team_abbr
        )
        if bene_data and sum(b['games_without'] for b in bene_data) >= 3:
            base_min = starter_out.get('base_min', 1) or 1
            absorption = {}
            for b in bene_data:
                if b['minutes_delta'] > 0:
                    absorption[b['name']] = round(b['minutes_delta'] / base_min, 3)
            if absorption:
                print(f"[Module X] TIER 0B beneficiary_minutes for {starter_out.get('PLAYER_NAME', '?')}: "
                      f"{list(absorption.keys())[:3]}")
                return {'matrix': absorption, 'confidence': 'high'}

        # TRY WOWY FIRST (real lineup data)
        try:
            from utils.wowy_calculator import WOWYCalculator
            wowy = WOWYCalculator()
            beneficiaries = wowy.find_beneficiaries(
                starter_out.get('PLAYER_NAME', ''),
                team_abbr
            )
            
            # Use WOWY if medium+ confidence (350+ possessions)
            if beneficiaries:
                high_conf = [b for b in beneficiaries if b.get('confidence') in ['high', 'medium']]
                if high_conf:
                    print(f"[Module X] Using WOWY data for {starter_out.get('PLAYER_NAME')} beneficiaries")
                    matrix = {b['player_name']: b['absorption_rate'] for b in high_conf[:2]}
                    confidence = high_conf[0].get('confidence', 'medium')
                    return {'matrix': matrix, 'confidence': confidence}
        except Exception as e:
            print(f"[Module X] WOWY lookup failed: {e}. Using heuristic.")
        
        # SECOND FALLBACK: Assist combo data (who receives the star's passes)
        star_name = starter_out.get('PLAYER_NAME', '')
        teammate_names = [
            p['PLAYER_NAME'] for p in all_players
            if p.get('TEAM_ABBREVIATION') == team_abbr and (p.get('PLAYER_ID') or p.get('player_id')) != (starter_out.get('PLAYER_ID') or starter_out.get('player_id'))
        ]
        assist_shares = self._get_assist_share(star_name, teammate_names)

        if assist_shares:
            # Convert assist shares to absorption rates (share × 0.15 = PTS boost factor)
            # Top beneficiaries by assist share get proportional minutes
            sorted_shares = sorted(assist_shares.items(), key=lambda x: x[1], reverse=True)
            matrix = {}
            for name, share in sorted_shares[:3]:  # Top 3 beneficiaries
                # Scale: highest share teammate gets ~60% absorption, others proportional
                matrix[name] = round(share * PRIMARY_BACKUP_ABSORPTION / sorted_shares[0][1], 2) if sorted_shares[0][1] > 0 else 0
            print(f"[Module X] Using assist combo data for {star_name} beneficiaries ({len(matrix)} teammates)")
            return {'matrix': matrix, 'confidence': 'medium'}

        # LAST RESORT: Heuristic 60/30 split (original logic)
        bench_candidates = []

        for p in all_players:
            # Must be same team, different player
            if p.get('TEAM_ABBREVIATION') == team_abbr and (p.get('PLAYER_ID') or p.get('player_id')) != (starter_out.get('PLAYER_ID') or starter_out.get('player_id')):
                # Bench Player Criteria: plays between 10 and 28 minutes
                p_min = p.get('base_min', 0)
                if 10.0 < p_min < 28.0:
                    bench_candidates.append(p)

        if not bench_candidates:
            return {'matrix': {}, 'confidence': None}

        # Sort candidates by Usage Rate (Best proxy for "Sixth Man")
        bench_candidates.sort(key=lambda x: x.get('base_usg', 0), reverse=True)

        # The primary backup gets 60% of minutes, secondary gets 30%
        matrix = {}
        if len(bench_candidates) >= 1:
            matrix[bench_candidates[0]['PLAYER_NAME']] = PRIMARY_BACKUP_ABSORPTION
        if len(bench_candidates) >= 2:
            matrix[bench_candidates[1]['PLAYER_NAME']] = SECONDARY_BACKUP_ABSORPTION

        print(f"[Module X] Using heuristic backup matrix (WOWY + assist combos unavailable)")
        return {'matrix': matrix, 'confidence': None}

    def _get_assist_share(self, star_name, teammates):
        """
        Query assist_combos table for assists from the star to each teammate.
        Returns dict of {teammate_name: share_pct} or empty dict if unavailable.
        """
        try:
            conn = sqlite3.connect('ludi.db')
            c = conn.cursor()
            c.execute("""
                SELECT scorer_name, assist_count
                FROM assist_combos
                WHERE passer_name = ? AND season = '2025-26'
            """, (star_name,))
            rows = c.fetchall()
            conn.close()

            if not rows:
                return {}

            # Filter to only teammates in this game
            teammate_set = set(teammates)
            relevant = {row[0]: row[1] for row in rows if row[0] in teammate_set}

            if not relevant:
                return {}

            # Calculate share percentages
            total_assists = sum(relevant.values())
            if total_assists == 0:
                return {}

            return {name: count / total_assists for name, count in relevant.items()}
        except Exception as e:
            return {}

    def _set_wowy_confidence_for_players(self, players):
        """
        Phase 7.4: Query player_season_wowy table to set wowy_confidence
        for all players in the game.
        
        Uses on_off_diff to set confidence:
        - HIGH if on_off_diff > 5.0
        - MEDIUM if on_off_diff > 2.5
        - LOW otherwise
        """
        import sqlite3
        
        try:
            conn = sqlite3.connect('ludi.db')
            c = conn.cursor()
            
            # Bulk pre-fetch — single query instead of N per-player queries
            all_wowy = conn.execute(
                "SELECT player_name, on_off_diff FROM player_season_wowy WHERE season = '2025-26'"
            ).fetchall()
            wowy_lookup = {row[0]: row[1] for row in all_wowy}
            
            for player in players:
                player_name = player.get('PLAYER_NAME', '')
                if not player_name:
                    continue
                
                on_off_diff_val = wowy_lookup.get(player_name)
                row = (on_off_diff_val,) if on_off_diff_val is not None else None
                
                if row and row[0] is not None:
                    on_off_diff = float(row[0])
                    if on_off_diff > 5.0:
                        player['wowy_confidence'] = 'high'
                    elif on_off_diff > 2.5:
                        player['wowy_confidence'] = 'medium'
                    else:
                        player['wowy_confidence'] = 'low'
                else:
                    player['wowy_confidence'] = None
            
            conn.close()
        except Exception as e:
            pass

    def _apply_vegas_guardrail(self, players, odds):
        spread = odds.get('spread', 0)
        total = odds.get('total', 0)
        
        # Guardrail: Need valid Vegas data
        if not total or total == 'N/A' or total == 0: 
            return players 
        
        # Ensure numeric types
        try:
            total = float(total)
            spread = float(spread) if spread != 'N/A' else 0
        except Exception as e:
            print(f"[Module X _apply_vegas_guardrail]: {e}")
            return players

        implied_total = (total / 2) - (spread / 2)
        
        # Sum projected points in this new scenario
        raw_sum = sum(p.get('PTS', 0) for p in players)
        
        if raw_sum == 0: return players
        
        correction = implied_total / raw_sum
        
        normalized = []
        for p in players:
            # Apply correction to main stats
            if 'PTS' in p: p['PTS'] = round(p['PTS'] * correction, 2)
            if 'REB' in p: p['REB'] = round(p['REB'] * correction, 2)
            if 'AST' in p: p['AST'] = round(p['AST'] * correction, 2)
            normalized.append(p)
            
        return normalized




if __name__ == "__main__":
    print("Module X (V3.7 - Live Schema) Loaded.")
