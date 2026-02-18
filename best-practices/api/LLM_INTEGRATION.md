# LLM API Integration Best Practices
**Applies to:** Claude (Anthropic) integration — Phase 8 AI-Enhanced Pipeline
**Created:** February 19, 2026
**Status:** ✅ Active

LLMs have fundamentally different constraints than REST APIs. This guide lives separately from `API_BEST_PRACTICES.md` because the patterns don't overlap.

---

## Core Ground Rules

These are non-negotiable for the Ludi-Bot integration:

1. **Claude reasons, never calculates.** Edge %, Poisson sims, Kelly sizing — all stay deterministic Python. Claude gets the output, not the inputs, for math operations.
2. **All NBA facts come from `ludi.db` or live APIs — never from Claude recall.** Training data is outdated. Rosters, trades, injuries: always fetched, never assumed.
3. **Pipeline must never block on Claude.** If Claude fails, the pipeline continues using rule-based fallback logic.
4. **All Claude outputs must be auditable.** Log inputs + outputs for every call.

---

## Authentication: OAuth-First Pattern

Claude Max plan does not issue standalone API keys — it uses OAuth tokens. Always use this priority chain:

```python
def _get_claude_auth_token() -> str:
    """OAuth-first auth. Priority: env var → local config → API key."""
    # 1. GitHub Actions (CI/CD) — set CLAUDE_CODE_OAUTH_TOKEN as a secret
    if os.getenv('CLAUDE_CODE_OAUTH_TOKEN'):
        return os.getenv('CLAUDE_CODE_OAUTH_TOKEN')

    # 2. Local dev with Max plan — Claude Code writes token here automatically
    config_path = os.path.expanduser('~/.claude/config.json')
    if os.path.exists(config_path):
        try:
            import json as _json
            data = _json.load(open(config_path))
            if data.get('oauthToken'):
                return data['oauthToken']
        except Exception:
            pass

    # 3. Fallback: direct API key (future/testing)
    return os.getenv('ANTHROPIC_API_KEY', '')
```

**Why:** Claude Max plan ($100/mo) provides far more capacity than a pay-per-use API key at our token volume (~$22/mo equivalent). OAuth token is the native auth method.

**GitHub Actions setup:** Add `CLAUDE_CODE_OAUTH_TOKEN` as a repository secret (Settings → Secrets → Actions).

---

## Model Selection

Use exact model IDs — no substitutions, no "latest" aliases. Aliases break when Anthropic releases new versions.

```python
HAIKU_MODEL = "claude-haiku-4-5-20251001"   # Sanity gates, classification
SONNET_MODEL = "claude-sonnet-4-6"           # Game notes, player spotlights
DEFAULT_MAX_TOKENS = 1500
```

**Temperature guide:**

| Temp | Use Case | Model |
|------|----------|-------|
| 0.1 | Sanity gates, classification, factual checks | Haiku |
| 0.2 | Game notes, player spotlight cards | Sonnet |
| 0.3 | Freestyle narrative only | Sonnet |

Never use temperature above 0.3 for Ludi-Bot tasks. Higher temperatures increase hallucination risk with sports facts.

---

## SDK Patterns

### Lazy Import (Critical)

Import `anthropic` inside the function body, not at module level. This prevents import errors if the package isn't installed on a machine that doesn't need Claude.

```python
def get_claude_analysis(prompt, system_prompt, model=SONNET_MODEL,
                        temperature=0.2, max_tokens=DEFAULT_MAX_TOKENS):
    """Call Claude API with graceful degradation."""
    try:
        import anthropic  # Lazy import — prevents failure if package missing
    except ImportError:
        print("[claude_client] anthropic package not installed")
        return None

    token = _get_claude_auth_token()
    if not token:
        print("[claude_client] No auth token available — skipping Claude call")
        return None

    try:
        # Create client inside function (not module-level singleton)
        client = anthropic.Anthropic(api_key=token)

        response = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system_prompt,        # Role + constraints + ROSTER_RULES
            messages=[{"role": "user", "content": prompt}]  # Data + question
        )

        # Log usage before returning
        from utils.api_monitor import get_monitor
        get_monitor().log_claude_usage(
            model=model,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            task="game_notes"  # Pass task label from caller
        )

        return response.content[0].text

    except Exception as e:
        print(f"[claude_client] Error: {e}")
        return None  # Never raise — let caller use fallback
```

**Why client inside function:** Avoids module-level init failure if auth token isn't available at import time (e.g., CI environment without Claude secrets).

### system= vs user= Separation

Always use `system=` for role, constraints, and ROSTER_RULES. Use `user=` for game-specific data and the question.

```python
# ✅ Correct: system= holds instructions, user= holds data
response = client.messages.create(
    system=ROSTER_RULES + "\n\n" + task_instructions,
    messages=[{"role": "user", "content": game_data_block + "\n\n" + question}]
)

# ❌ Wrong: prepending to user message
combined = ROSTER_RULES + task_instructions + game_data + question
messages=[{"role": "user", "content": combined}]
```

**Why:** `system=` is cached by Anthropic when identical across calls — reduces cost. Separation also makes prompts easier to test and debug.

---

## Context Engineering

The order of information in your prompts matters. Claude reads top-to-bottom; constraints must reference data that appears before them.

### The 5 Rules

1. **Data first, instructions last.** Inject game/injury data BEFORE `ROSTER_RULES` and task instructions. "Check the injury report above" must reference something that's actually above.

2. **Only inject data for THIS game.** For a single-game analysis, inject only the two teams' players. Never pass the full database — it wastes tokens and confuses the model.

3. **Pre-format data as clean text blocks.** Convert DB rows to readable text before injecting. Claude handles structured markdown tables better than raw JSON.

4. **Keep system prompts identical across same-type calls.** Identical system prompts are eligible for Anthropic's prompt caching, which reduces cost by ~90% on cached portions.

5. **Include ROSTER_RULES in every call.** The anti-hallucination block that prevents Claude from mentioning injured/suspended players. Never omit it.

### Example: Correct Context Assembly

```python
# Correct ordering for a game analysis call
user_message = f"""
=== GAME DATA ===
{game_context_block}      # Real data from ludi.db

=== INJURY REPORT ===
{injury_block}            # From player_injuries table, fetched live

=== YOUR TASK ===
Analyze the matchup for {away_team} @ {home_team}.
Focus on scheme edges and usage vacuum opportunities.
"""

system_message = ROSTER_RULES + "\n\n" + GAME_NOTES_INSTRUCTIONS
```

---

## Token Tracking

Extend `utils/api_monitor.py` (don't create a new file). The `APIMonitor` singleton already handles quota logging for Odds API and Tank01 — add one method for Claude.

```python
def log_claude_usage(self, model: str, input_tokens: int,
                     output_tokens: int, task: str = ""):
    """Log Claude token usage alongside existing API quota tracking."""
    # Rough cost rates (not billed separately on Max plan, but tracked for budgeting)
    if 'haiku' in model:
        cost = (input_tokens * 0.00025 + output_tokens * 0.00125) / 1000
    else:  # sonnet
        cost = (input_tokens * 0.003 + output_tokens * 0.015) / 1000

    print(f"[Claude] {task} | {model.split('-')[1]} | "
          f"{input_tokens}in/{output_tokens}out | ~${cost:.4f}")
    # ... log to api_usage_log.json under 'claude' key
```

**Daily budget target:** ~$0.73/day (~$22/month) based on current Phase 8 task plan.

| Task | Model | ~Tokens/call | Freq | Daily cost |
|------|-------|-------------|------|------------|
| Sanity gate | Haiku (0.1) | ~800 | ~300/day | ~$0.02 |
| Top 5 curation | Sonnet (0.1) | ~2,000 | Once/day | ~$0.06 |
| Game notes | Sonnet (0.2) | ~1,500 | ~10 games | ~$0.35 |
| Spotlights | Sonnet (0.2) | ~1,000 | ~5/day | ~$0.15 |

---

## Graceful Degradation

Claude being unavailable must never take down the pipeline. The pattern:

```python
# In morning_brief.py (example)
game_notes = get_claude_analysis(user_msg, system_msg, model=SONNET_MODEL)

if game_notes is None:
    # Fallback: use existing rule-based text generation
    game_notes = generate_rule_based_summary(game_data)
    print("[morning_brief] Claude unavailable — using rule-based fallback")

send_telegram(game_notes)
```

**Rule:** Every Claude call site must have a non-Claude fallback. If you can't implement a fallback, the Claude call isn't ready for production.

---

## Anti-Patterns

### ❌ Using Claude for NBA Facts

```python
# BAD: Claude's training data is outdated
prompt = "Who are the Lakers' top 3 scorers this season?"

# GOOD: Fetch from ludi.db, then give Claude the data
players = db.query("SELECT ... FROM player_game_logs WHERE team='LAL'...")
prompt = f"Given these Lakers stats: {players}\nAnalyze the matchup..."
```

### ❌ Module-Level Client Init

```python
# BAD: Fails at import if anthropic not installed or no token
import anthropic
client = anthropic.Anthropic(api_key=TOKEN)  # Module-level

# GOOD: Lazy import inside function body (see SDK Patterns above)
```

### ❌ Blocking Pipeline on Claude Failure

```python
# BAD: Claude failure crashes the morning brief
game_notes = get_claude_analysis(...)  # Returns None on failure
send_telegram(game_notes)              # TypeError: None is not a string

# GOOD: Check for None, use fallback
game_notes = get_claude_analysis(...) or generate_fallback_summary(...)
```

### ❌ Passing Raw JSON to Claude

```python
# BAD: Raw DB rows are noisy and waste tokens
prompt = f"Analyze this game: {json.dumps(raw_db_rows)}"

# GOOD: Pre-format into clean text before injecting
formatted = format_game_context(raw_db_rows)  # Markdown tables/bullets
prompt = f"Analyze this game:\n{formatted}"
```

---

## Checklist for Adding a New Claude Call

- [ ] Data fetched from `ludi.db` or live API — not recalled by Claude
- [ ] Context assembled in correct order (data → ROSTER_RULES → instructions)
- [ ] `system=` holds role + constraints, `user=` holds data + question
- [ ] Model and temperature match the task type (see temperature guide above)
- [ ] `log_claude_usage()` called on success
- [ ] Returns `None` on any exception (never raises)
- [ ] Caller has a non-Claude fallback
- [ ] No NBA facts asked of Claude (only reasoning about provided data)
