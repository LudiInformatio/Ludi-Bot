"""ops_logger.py — Log company operations events for local model training data."""
import logging

logger = logging.getLogger(__name__)


def log_ops_event(conn, event_type, **kwargs):
    """Log a company operations event for local model training data.

    Args:
        conn: Active sqlite3 connection
        event_type: One of ROUTING, CODE_REVIEW, OWNER_INTERACTION, ADR, PROMPT_CHANGE
        **kwargs: Any column in ludi_ops_log (actor, target_employee, task_type,
                  input_summary, output_summary, outcome, blocker_reason, session_id,
                  sequence_n, prompt_version, related_task_id, token_cost_usd, model, tags)

    Notes:
        tags column is stored as JSON string, e.g. '["ROUTING","CODE_REVIEW"]'
        outcome=None is valid (means in-progress / not yet resolved)
    """
    cols = ['event_type'] + list(kwargs.keys())
    vals = [event_type] + list(kwargs.values())
    placeholders = ','.join(['?'] * len(vals))
    col_str = ','.join(cols)
    try:
        conn.execute(
            f'INSERT INTO ludi_ops_log ({col_str}) VALUES ({placeholders})',
            vals
        )
        conn.commit()
    except Exception as e:
        logger.warning(f'[ops_logger] Failed to log ops event {event_type}: {e}')
