"""
LUDI INFORMATIO | CLAUDE API CLIENT
====================================
OAuth-first authentication priority:
  - Priority 1: CLAUDE_CODE_OAUTH_TOKEN env var (GitHub Actions)
  - Priority 2: ~/.claude/config.json → oauthToken (local dev with Max plan)
  - Priority 3: ANTHROPIC_API_KEY env var (future fallback)

Temperature guide:
  - 0.1: Sanity gates, classification (Haiku)
  - 0.2: Game notes, player spotlights (Sonnet)
  - 0.3: Freestyle/narrative only

Created: February 2026
Purpose: Phase 8 AI Integration for Ludi-Bot
"""

import os
import json
from datetime import datetime

HAIKU_MODEL = "claude-haiku-4-5-20251001"
SONNET_MODEL = "claude-sonnet-4-6"
DEFAULT_MAX_TOKENS = 1500


def _get_claude_auth_token() -> str:
    """Get Claude auth token with OAuth-first priority."""
    if os.getenv('CLAUDE_CODE_OAUTH_TOKEN'):
        return os.getenv('CLAUDE_CODE_OAUTH_TOKEN')
    
    config_path = os.path.expanduser('~/.claude/config.json')
    if os.path.exists(config_path):
        try:
            data = json.load(open(config_path))
            if data.get('oauthToken'):
                return data['oauthToken']
        except Exception:
            pass
    
    return os.getenv('ANTHROPIC_API_KEY', '')


def get_claude_analysis(
    prompt: str,
    system_prompt: str,
    model: str = SONNET_MODEL,
    temperature: float = 0.2,
    max_tokens: int = DEFAULT_MAX_TOKENS
) -> str | None:
    """
    Get analysis from Claude API.

    Args:
        prompt: User message content
        system_prompt: System prompt (role, constraints, etc.)
        model: Claude model to use (default: SONNET_MODEL)
        temperature: Controls randomness (default: 0.2)
        max_tokens: Max response tokens (default: 1500)

    Returns:
        Response text or None on error/no auth
    """
    auth_token = _get_claude_auth_token()
    
    if not auth_token:
        print("[claude_client] Warning: No Claude auth token available")
        return None

    try:
        from anthropic import Anthropic
        
        client = Anthropic(api_key=auth_token)
        
        response = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system_prompt,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

        input_tokens = response.usage.input_tokens
        output_tokens = response.usage.output_tokens

        try:
            from utils.api_monitor import get_monitor
            monitor = get_monitor()
            monitor.log_claude_usage(model, input_tokens, output_tokens, task="get_claude_analysis")
        except Exception:
            pass

        return response.content[0].text

    except Exception as e:
        print(f"[claude_client] Error: {e}")
        return None
