"""
Calibration Loader — loads probability calibration from cache for use in curate_plays.py.
Fail-safe: returns empty dict if cache missing or corrupt.
"""

import json
import os
import logging

logger = logging.getLogger(__name__)

_CACHE_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                            'cache', 'probability_calibration.json')


def load_probability_calibration(cache_path: str = None) -> dict:
    """Load probability calibration from cache. Returns {} on missing/corrupt file."""
    path = cache_path or _CACHE_PATH
    if not os.path.exists(path):
        return {}
    try:
        with open(path, 'r') as f:
            data = json.load(f)
        if 'correction_table' not in data:
            logger.warning("calibration_loader: correction_table missing from cache")
            return {}
        return data
    except (json.JSONDecodeError, KeyError, IOError) as e:
        logger.warning(f"calibration_loader: failed to load {path}: {e}")
        return {}


def calibrated_prob_for_edge(edge: float, calibration: dict) -> float:
    """
    Look up calibrated probability for a given edge value.
    Falls back to linear mapping if calibration missing or edge out of range.
    """
    if not calibration or 'correction_table' not in calibration:
        # Fallback: linear heuristic (existing behavior in calibrate_claude_outputs.py)
        return 0.5 + (edge / 100.0 * 0.5)

    table = calibration['correction_table']
    for entry in table:
        if entry['edge_low'] <= edge < entry['edge_high']:
            return min(max(entry['calibrated_prob'], 0.01), 0.99)

    # Edge out of range — use linear fallback
    return 0.5 + (edge / 100.0 * 0.5)
