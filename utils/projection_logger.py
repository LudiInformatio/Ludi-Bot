# LUDI INFORMATIO | PROJECTION LOGGER
# -------------------------------------------
# Priority 2: Stores full projection breakdown for every simulated player.
# Enables post-hoc modifier attribution, calibration curves, and residual analysis.
# Mirrors utils/bet_logger.py singleton pattern.

import sqlite3
import logging
import numpy as np
from datetime import datetime
from typing import Dict, List, Optional

import config

logger = logging.getLogger(__name__)

# Stat categories to extract from _distributions (Module C output key -> DB stat_category)
_STAT_MAP = {
    'PTS': 'pts',
    'REB': 'reb',
    'AST': 'ast',
    'FG3M': '3pm',
    'STL': 'stl',
    'BLK': 'blk',
    'TOV': 'tov',
    'OREB': 'oreb',
}


class ProjectionLogger:
    """
    Logs full projection breakdowns to player_projections table.

    Singleton pattern — use get_projection_logger() for module-level access.
    """

    def __init__(self, db_path=None):
        self.db_path = db_path or config.DB_PATH
        logger.info(f"ProjectionLogger initialized (DB: {self.db_path})")

    def _get_conn(self) -> sqlite3.Connection:
        """Create a new database connection with busy timeout."""
        conn = sqlite3.connect(self.db_path, timeout=30)
        conn.execute("PRAGMA busy_timeout = 30000")
        return conn

    def log_projection_batch(
        self,
        sim_results: List[Dict],
        game_context: Dict,
        run_date: str,
        bet_id_map: Optional[Dict] = None,
    ) -> int:
        """
        Batch-insert projection rows for all simulated players in a game.

        Args:
            sim_results: List of sim_profile dicts from Module C (one per player).
            game_context: Dict with game_id, game_date, opponent (optional), opponent_scheme (optional).
            run_date: Pipeline run date (YYYY-MM-DD).
            bet_id_map: Optional dict mapping (player_name, stat_category) -> bet_rec_id.

        Returns:
            Number of rows inserted.
        """
        if not sim_results:
            return 0

        bet_id_map = bet_id_map or {}
        rows_inserted = 0
        conn = self._get_conn()
        c = conn.cursor()

        try:
            for sim in sim_results:
                player_name = sim.get('PLAYER_NAME')
                if not player_name:
                    continue

                distributions = sim.get('_distributions', {})
                if not distributions:
                    continue

                team = sim.get('TEAM', '')
                scenario = sim.get('SCENARIO', 'BASE')
                player_id = sim.get('player_id') or sim.get('PLAYER_ID')

                # Extract modifier values from sim_profile (set by Module C Priority 1)
                pace_mod = sim.get('_raw_pace_factor', 1.0)
                fatigue_mod = sim.get('_fatigue_tax', 1.0)
                ref_mod = sim.get('_ref_pace_factor', 1.0)

                # Volume stats for context
                proj_fga = sim.get('FGA')
                proj_fg3a = sim.get('FG3A')
                proj_fta = sim.get('FTA')

                # Shooting percentages (from input player dict, stored on sim_profile)
                assumed_fg_pct = sim.get('FG_PCT')
                assumed_fg3_pct = sim.get('FG3_PCT')
                assumed_ft_pct = sim.get('FT_PCT')

                for dist_key, stat_cat in _STAT_MAP.items():
                    dist = distributions.get(dist_key)
                    if dist is None or not hasattr(dist, '__len__') or len(dist) == 0:
                        continue

                    # numpy operations — convert to Python floats for SQLite
                    final_proj = float(np.mean(dist))
                    p10 = float(np.percentile(dist, 10))
                    p25 = float(np.percentile(dist, 25))
                    p75 = float(np.percentile(dist, 75))
                    p90 = float(np.percentile(dist, 90))
                    stdev = float(np.std(dist))

                    # Base projection = mean of distribution (pre-Module-E)
                    base_proj = sim.get(f'_base_{stat_cat}', final_proj)
                    if hasattr(base_proj, 'item'):  # numpy scalar -> Python float
                        base_proj = float(base_proj)

                    # Check if this player+stat was a bet
                    lookup_key = (player_name, stat_cat)
                    bet_rec_id = bet_id_map.get(lookup_key)
                    is_bet = 1 if bet_rec_id else 0

                    c.execute('''
                        INSERT OR REPLACE INTO player_projections (
                            run_date, game_date, game_id, player_id, player_name,
                            team, opponent, archetype, opponent_scheme,
                            stat_category, line,
                            proj_fga, proj_fg3a, proj_fta,
                            assumed_fg_pct, assumed_fg3_pct, assumed_ft_pct,
                            base_projection, pace_mod, fatigue_mod, ref_mod,
                            blowout_mod, scheme_mod, empirical_mod,
                            final_projection, prob_over_line,
                            p10, p25, p75, p90, sim_stdev,
                            is_bet, bet_rec_id, scenario, role_data_flag
                        ) VALUES (
                            ?, ?, ?, ?, ?,
                            ?, ?, ?, ?,
                            ?, ?,
                            ?, ?, ?,
                            ?, ?, ?,
                            ?, ?, ?, ?,
                            ?, ?, ?,
                            ?, ?,
                            ?, ?, ?, ?, ?,
                            ?, ?, ?, ?
                        )
                    ''', (
                        run_date,
                        game_context.get('game_date', run_date),
                        game_context.get('game_id'),
                        str(player_id) if player_id else None,
                        player_name,
                        team,
                        game_context.get('opponent'),
                        sim.get('archetype'),
                        game_context.get('opponent_scheme'),
                        stat_cat,
                        None,  # line — not known at sim time, only at Module F
                        float(proj_fga) if proj_fga is not None else None,
                        float(proj_fg3a) if proj_fg3a is not None else None,
                        float(proj_fta) if proj_fta is not None else None,
                        float(assumed_fg_pct) if assumed_fg_pct is not None else None,
                        float(assumed_fg3_pct) if assumed_fg3_pct is not None else None,
                        float(assumed_ft_pct) if assumed_ft_pct is not None else None,
                        float(base_proj),
                        float(pace_mod) if pace_mod is not None else 1.0,
                        float(fatigue_mod) if fatigue_mod is not None else 1.0,
                        float(ref_mod) if ref_mod is not None else 1.0,
                        1.0,  # blowout_mod — applied later in Module F, not available at sim time
                        1.0,  # scheme_mod — applied by Module E, not available at sim time
                        float(sim.get('_empirical_mod_scalar', 1.0)),  # empirical_mod — composite scalar from Module C role modifier block
                        float(final_proj),
                        None,  # prob_over_line — requires line, computed in Module F
                        float(p10), float(p25), float(p75), float(p90),
                        float(stdev),
                        is_bet,
                        bet_rec_id,
                        scenario,
                        sim.get('role_flag'),
                    ))
                    rows_inserted += 1

            conn.commit()
            logger.info(f"[ProjectionLogger] Inserted {rows_inserted} projection rows")

        except Exception as e:
            conn.rollback()
            logger.error(f"[ProjectionLogger] Batch insert failed: {e}")
            raise
        finally:
            conn.close()

        return rows_inserted


# ============================================================
# SINGLETON PATTERN
# ============================================================

_logger_instance = None


def get_projection_logger(db_path=None) -> ProjectionLogger:
    """
    Get singleton ProjectionLogger instance.

    Usage:
        from utils.projection_logger import get_projection_logger
        proj_logger = get_projection_logger()
        proj_logger.log_projection_batch(sim_results, game_ctx, run_date)
    """
    global _logger_instance
    if _logger_instance is None:
        _logger_instance = ProjectionLogger(db_path=db_path)
    return _logger_instance
