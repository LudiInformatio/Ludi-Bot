"""
Claude Analysis Logger — Phase 8.23 Layer 1
============================================
Hot-path write called from utils/claude_client.py after every get_claude_analysis() call.
Stores call metadata in claude_analysis_log for Wilson accuracy calibration (Layer 2)
and prompt drift detection.

Token pricing (as of Feb 2026):
  Haiku:  $0.0008/1k input + $0.004/1k output
  Sonnet: $0.003/1k input  + $0.015/1k output

Layer 2: scripts/calibrate_claude_outputs.py — weekly Wilson accuracy per call_type
Layer 3: inject calibration dict into _get_system_wr_context() (already wired for stat confidence)
"""

import os
import sqlite3

# Pricing per 1k tokens (Feb 2026 rates)
_HAIKU_IN  = 0.0008
_HAIKU_OUT = 0.004
_SONNET_IN = 0.003
_SONNET_OUT = 0.015

_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'ludi.db')


def _estimate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """Estimate USD cost from token counts."""
    if not input_tokens and not output_tokens:
        return 0.0
    m = (model or '').lower()
    if 'haiku' in m:
        return (input_tokens / 1000) * _HAIKU_IN + (output_tokens / 1000) * _HAIKU_OUT
    return (input_tokens / 1000) * _SONNET_IN + (output_tokens / 1000) * _SONNET_OUT


def log_claude_call(
    call_type: str,
    model: str,
    input_tokens: int,
    output_tokens: int,
    response_text: str,
    game_date: str = None,
    player_name: str = None,
) -> None:
    """
    Write one row to claude_analysis_log. Silent on failure — never breaks the pipeline.

    Args:
        call_type:     Semantic label, e.g. 'sanity_gate', 'curation', 'game_notes',
                       'spotlight', 'scheme', 'archetype', 'weekly'
        model:         Claude model string from response
        input_tokens:  From response.usage.input_tokens
        output_tokens: From response.usage.output_tokens
        response_text: Claude's response (truncated to 2000 chars internally)
        game_date:     Optional — ISO date of the game being analyzed
        player_name:   Optional — player being analyzed
    """
    try:
        cost = _estimate_cost(model, input_tokens, output_tokens)
        truncated = (response_text or '')[:2000]

        conn = sqlite3.connect(_DB_PATH)
        conn.execute("PRAGMA busy_timeout=30000")
        conn.execute(
            """
            INSERT INTO claude_analysis_log
                (call_type, model, input_tokens, output_tokens, game_date,
                 player_name, response_text, estimated_cost_usd,
                 signal_available_at, acted_on_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, NULL, NULL)
            """,
            (call_type, model, input_tokens, output_tokens, game_date,
             player_name, truncated, cost)
        )
        conn.commit()
        conn.close()
    except Exception:
        pass  # Never let logging break the pipeline
