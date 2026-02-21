# AI Prompting Best Practices

**Last Updated:** February 20, 2026
**Applies to:** Claude (Haiku/Sonnet) and Perplexity Sonar used throughout Ludi-Bot

---

## Quick Reference

| Use Case | Model | Location | Cost |
|----------|-------|----------|------|
| Injury blurb classification | Haiku | `utils/claude_prompts.py::INJURY_BLURB_PARSE_PROMPT` | ~$0.01/day |
| Game notes generation | Sonnet | `utils/claude_prompts.py::GAME_NOTES_TEMPLATE` | ~$0.12/day |
| Player spotlight narrative | Sonnet | `utils/claude_prompts.py::SPOTLIGHT_TEMPLATE` | ~$0.15/day |
| Play curation Top 5 | Sonnet | `utils/claude_prompts.py` | ~$0.08/day |
| Archetype classification | Haiku | `scripts/classify_archetypes.py` | ~$0.03/week |
| Game context search | Perplexity Sonar | `utils/perplexity_client.py` | ~$0.10/day |
| Suspension detection | Perplexity Sonar | Phase 8.16 (planned) | ~$0.02/day |

---

## Core Principles

### 1. Data First, Instructions Last
Claude reads top-to-bottom. Always inject game/player data BEFORE instructions.

```
# Good
system: role + rules + constraints
user: [injected data block] + "Based on the above, answer: ..."

# Bad
user: "Here are the instructions... [instructions] ... Here is the data: [data]"
```

### 2. System Prompt = Identity + Guardrails (Cache It)
Keep `system=` identical across calls of the same type. Anthropic caches system prompts — changing it breaks the cache and doubles cost.

```python
# Same system prompt every call = cached after first call
system_prompt = INJURY_BLURB_SYSTEM  # constant from claude_prompts.py

# Different data per call goes in user prompt
user_prompt = INJURY_BLURB_PARSE_PROMPT.format(description=blurb, player_name=name)
```

### 3. Temperature Rules
| Task Type | Temperature | Reason |
|-----------|-------------|--------|
| Classification (JSON output) | 0.0 | Deterministic — same input = same output |
| Structured analysis | 0.1–0.2 | Slight variation for edge cases |
| Narrative generation | 0.5–0.7 | Natural language, some creativity OK |
| Curation / ranking | 0.3–0.5 | Balanced — not fully random |

### 4. Use Few-Shot Examples for JSON Tasks
Haiku needs to see the pattern. Without examples, it invents field names or wraps output in markdown.

```python
# Bad — no examples
"Return JSON with: body_part, severity, context"

# Good — show the format
"""
Blurb: "Hart (ankle) is questionable for Sunday"
Player: Josh Hart
Output: {"body_part": "ankle", "severity": "moderate", "tonight_available": "uncertain"}

Blurb: "{description}"
Player: {player_name}
Output: """
```

### 5. Right Model for the Job
| Model | Use When |
|-------|----------|
| **Haiku** | Classification, JSON extraction, simple categorization, high-volume tasks |
| **Sonnet** | Multi-step reasoning, narrative generation, nuanced analysis |
| **Perplexity Sonar** | Real-time web search needed (news, suspensions, lineup changes) |

Never use Sonnet for tasks Haiku can handle — it's 5× more expensive.

---

## Prompt Structure Templates

### Classification Prompt (Haiku)
```python
SYSTEM = """You are [specific role].
Your job: [single clear task].
[Key constraint, e.g. "Focus on tonight's game"].
Return ONLY [output format]. No explanation, no markdown."""

PROMPT = """[Task description]

=== EXAMPLES ===

Input: [example 1 input]
Output: [example 1 output]

Input: [example 2 input]
Output: [example 2 output]

=== YOUR TASK ===

Input: {variable}
Output:"""
```

### Analysis Prompt (Sonnet)
```python
SYSTEM = """You are [role].
{ROSTER_RULES}  # always include — prevents hallucinating injured players
{ANALYSIS_PROTOCOL}  # source citation + reasoning steps
"""

PROMPT = """=== GAME DATA ===
{injected_data}

=== QUESTION ===
{specific_question}"""
```

### Search Query (Perplexity)
```python
# Good — specific, current, player-named
query = f"{home_team} vs {away_team} injury update {date} {out_players_list}"

# Bad — vague
query = f"NBA game news today"
```

---

## The CLAUDE.md Data Rules (Always Apply)

**NEVER use AI training data for NBA roster/player/trade knowledge.**
AI knowledge is outdated and will produce wrong results (wrong teams, missed trades).

Always provide data explicitly in the prompt:
- Stats from `ludi.db`
- Injuries from `player_injuries` table or Tank01 API call
- Rosters from `players` table
- Odds from The-Odds-API or BDL

```python
# Wrong — asking Claude to "know" the roster
"Who are the top scorers on the Celtics?"

# Correct — inject the data
"Given this roster data: {celtics_roster_from_db}, who are the top scorers?"
```

---

## Claude Prompts Centralization Rule

**All reusable prompts live in `utils/claude_prompts.py`.**
Never define prompts inline in modules — it breaks caching and makes prompt iteration hard.

```python
# Wrong — inline in module_d.py
prompt = f"Parse this injury report: {blurb}. Return JSON with..."

# Correct — centralized
from utils.claude_prompts import INJURY_BLURB_PARSE_PROMPT
prompt = INJURY_BLURB_PARSE_PROMPT.format(description=blurb, player_name=name)
```

Prompts currently in `utils/claude_prompts.py`:
- `ROSTER_RULES` — global guardrail (never mention injured players)
- `ANALYSIS_PROTOCOL` — data citation rules for analysis prompts
- `GAME_NOTES_TEMPLATE` — S.A.V.A.G.E. game card template
- `SPOTLIGHT_TEMPLATE` — player spotlight card template
- `INJURY_BLURB_SYSTEM` + `INJURY_BLURB_PARSE_PROMPT` — Module D blurb classifier

---

## Graceful Degradation Pattern

Every AI call must fall back to deterministic logic if the API is unavailable.

```python
def _ai_parse_blurb(self, description, player_name):
    try:
        from utils.claude_client import get_claude_analysis, HAIKU_MODEL
        result_text = get_claude_analysis(prompt=..., ...)
        return json.loads(result_text)
    except Exception as e:
        print(f"[YAK] AI blurb parse failed: {e}")
        return {}  # caller falls through to keyword matching

# Caller:
ai_result = self._ai_parse_blurb(blurb, player_name)
if ai_result:
    # use AI result
    ...
# Always continues to keyword fallback regardless
```

---

## Perplexity-Specific Patterns

### When to Use Perplexity vs Claude
| Need | Use |
|------|-----|
| Breaking injury news not in DB | Perplexity |
| Real-time game context (weather, lineup) | Perplexity |
| Suspension intel (not in Tank01/BDL feeds) | Perplexity |
| Classifying data already in hand | Claude Haiku |
| Generating narrative from structured data | Claude Sonnet |

### Perplexity Query Best Practices
```python
# Good — specific, time-bounded, player-named
query = f"Tyler Herro injury update status tonight February 20 2026"

# Good — multiple OUT players in one query (efficient)
query = f"{home_team} vs {away_team} {', '.join(out_players)} OUT injury news {date}"

# Bad — too broad, costs same credits but returns noise
query = f"NBA injuries today"
```

### Perplexity Rate Limiting
- All Perplexity calls go through `utils/perplexity_client.py`
- 20-minute cache via `module_d.cache` — never make the same query twice in one session
- 4 injection points in production: injury nuance, game scoring, game notes, curation

---

## Lessons Learned

| Date | Lesson |
|------|--------|
| Feb 2026 | `temperature=0.1` on JSON tasks → occasional output wrapping in markdown fences. Fixed: `temperature=0.0` + explicit "Return JSON only" in system prompt |
| Feb 2026 | Inline prompts in module_d.py → prompt drift when updating logic. Fixed: centralize in `claude_prompts.py` |
| Feb 2026 | No few-shot examples → Haiku invented `expected_return` as date string sometimes, enum other times. Fixed: 5 examples in `INJURY_BLURB_PARSE_PROMPT` |
| Feb 2026 | Sonnet for injury classification → 5× cost for same accuracy as Haiku. Rule: Haiku for classification, Sonnet for reasoning |

---

## Claude Code Session Memory (`MEMORY.md`)

Claude Code auto-loads `memory/MEMORY.md` at the start of every session. Lines after **200 are truncated** — Claude never sees them. Treat it as a tight index, not a log.

### The 200-Line Rule

MEMORY.md has a hard 200-line display cap. When the file grows past that:
1. Move detailed notes into a topic file (e.g., `memory/schema_notes.md`, `memory/api_lessons.md`)
2. Replace the detail in MEMORY.md with a 1-line reference: `- Full schema notes: memory/schema_notes.md`
3. Keep MEMORY.md as a scannable index only

### What to Save

✅ **Save these:**
- Stable patterns confirmed across multiple sessions (e.g., "BDL team abbr mismatch: GS→GSW")
- Key architectural decisions and the reason behind them
- Schema gotchas that would cause silent bugs if forgotten (e.g., `games.date` not `game_date`)
- Bugs that recur — so Claude doesn't re-introduce them
- User preferences stated explicitly ("always use bun", "never auto-commit")

❌ **Don't save these:**
- Current task state or in-progress work notes
- Anything that duplicates CLAUDE.md or AGENTS.md
- Speculative conclusions from reading a single file
- Module-level implementation details (put those in code comments)

### How to Organize

**Semantic over chronological.** Group by topic, not by date. Bad:

```
## Feb 20 session
- Fixed X
- Found Y
- Decided Z
```

Good:
```
## Database Schema Notes
- games.date (not game_date) — confirmed correct column name
- bet_recommendations.confidence_tier (not tier, not bet_tier)

## BDL API Gotchas
- Abbr mismatches: GS/NO/NY/PHO/SA → normalize to GSW/NOP/NYK/PHX/SAS
```

### Priority Ordering

High-importance items go **at the top** of the file. Claude reads top-to-bottom and the last ~30 lines may be cut off at session start. Important recurring lessons should be near line 1, not line 180.

### Save Habit

Update MEMORY.md at the **end of each session** (before `/compact`), not during. Mid-session entries are often incomplete. End-of-session: one pass, add what's stable, remove what turned out to be wrong.

### Quick Checks

```bash
# See current line count (stay under 200)
wc -l memory/MEMORY.md

# Check what Claude actually sees (first 200 lines)
head -200 memory/MEMORY.md
```
