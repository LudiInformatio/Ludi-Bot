# Prompt Engineering Patterns for Ludi-Bot AI Pipeline

**Created:** February 21, 2026
**Source:** BERT codebase analysis (google-research/bert) + ScienceDirect sentiment paper
**Purpose:** Map foundational NLP research patterns to Claude prompt architecture

---

## Why This Document Exists

After studying the Google BERT codebase and a 2024 Procedia Computer Science paper on fine-tuning BERT for sentiment classification, we identified 8 structural patterns that directly map to our Claude prompt architecture. These aren't theoretical — they explain specific failures we've observed (Markdown 400 errors, inconsistent game note formatting, stale injury context leaking into curation) and have clear, low-effort fixes.

**Key insight:** Claude is already a pre-trained language model. Our prompts are the "fine-tuning." BERT research tells us exactly how fine-tuning should be structured to work reliably.

---

## The BERT → Claude Analogy Map

| BERT Concept | BERT Implementation | Claude Equivalent |
|---|---|---|
| Pre-trained model | Wikipedia + BookCorpus training | Claude Sonnet / Haiku base model |
| Fine-tuning | Task-specific supervised training (3 epochs) | Few-shot examples in system/user prompt |
| `InputExample(text_a, text_b, label)` | Structured input with two sequences | `system=` (context_a) + `user=` (context_b) |
| `[SEP]` separator token | Marks boundary between text_a and text_b | `---TONIGHT---` or `===` section divider |
| `[CLS]` classification token | One pooled output per input | One JSON object per Claude call |
| `DataProcessor.get_labels()` | Define valid output space BEFORE data | List all valid field values in prompt FIRST |
| `max_seq_length=128` | Hard truncation at token limit | Pre-truncate injected blocks before `.format()` |
| Domain-specific pre-training | Additional training on movie reviews / papers | Inject system WR stats into curation context |
| Next Sentence Prediction (NSP) | "Is sentence B a continuation of sentence A?" | Haiku relevance gate: "Does this news invalidate this bet?" |
| Knowledge distillation | Small BERT learns labels from large BERT | Sonnet curation decisions improve Haiku gate criteria |
| `temperature=0.0` for classification | Deterministic fine-tuning inference | Haiku calls: `temperature=0.1` ✅ |
| Warmup + 3 epochs (fast convergence) | Few examples needed with pre-training | 3-5 examples sufficient; more examples = marginal gain |

---

## Pattern 1: Define the Label Space First

**BERT pattern:** `DataProcessor.get_labels()` is always called BEFORE loading any training data. The model knows the complete valid output space (`["contradiction", "entailment", "neutral"]`) before seeing a single example.

**Current state — Haiku sanity gate (`curate_plays.py:195`):**
```python
user_prompt = f"""Sanity check this bet. Return JSON only, no other text:
{{"result": "PASS" or "FLAG", "reason": "<one sentence max>"}}

BET:
- Player: {bet['player_name']}...
```

The schema is buried after the instruction. Claude has to parse "or" logic to understand valid values.

**Improved pattern:**
```python
system_prompt = """You are a bet sanity checker for an NBA analytics model.
VALID OUTPUT ONLY:
  {"result": "PASS", "reason": ""}
  {"result": "FLAG", "reason": "<one sentence describing the contradiction>"}
No other values are valid for "result". Return JSON only."""
```

Label space in system prompt = consistent across all calls = enables Anthropic prompt caching.

**Files affected:** `curate_plays.py:188-210`, `utils/claude_prompts.py`

---

## Pattern 2: Sentence-Pair Input (text_a + [SEP] + text_b)

**BERT pattern:** The most powerful BERT tasks use TWO text sequences separated by `[SEP]`. The model reasons about the RELATIONSHIP between them — not just each one in isolation. Example:
- NLI: `text_a = premise` | `text_b = hypothesis` → Does B follow from A?
- Q&A: `text_a = question` | `text_b = document` → Where is the answer?

**Current state — GAME_NOTES_TEMPLATE and SPOTLIGHT_TEMPLATE:**
Historical data and tonight's context are mixed in one undifferentiated block. Claude must self-organize them before reasoning.

**Improved pattern — explicit two-section input:**
```
=== HISTORICAL CONTEXT (text_a) ===
Player: Tyrese Haliburton
L10 avg PTS: 22.1 | L7 trend: +2.3 | Season avg: 20.8
Hit rate OVER 22.5 (L10): 6/10 (60%)
Archetype: HELIOCENTRIC | Synergy: 28% ISO, 22% P&R_HANDLER

=== TONIGHT'S CONTEXT (text_b) ===
Opponent: WAS | Their scheme: FUNNEL (allows rim + mid-range, closes 3PM)
Spread: IND -6.5 | Team Total: 115.5 | Rest: 2 days
Injuries OUT: None | GTD: None
News: (Perplexity) "Haliburton expected full go after light Thursday practice"

=== QUESTION ===
Given text_a (history) and text_b (tonight), write the spotlight analysis.
```

**Why it works:** Claude's reasoning is explicitly comparative. "Given his 60% hit rate AND tonight's favorable matchup AND positive news" produces more coherent analysis than mixing all three in one paragraph.

**Files to update:** `utils/claude_prompts.py` — both `GAME_NOTES_TEMPLATE` and `SPOTLIGHT_TEMPLATE`

---

## Pattern 3: Few-Shot Examples = Fine-Tuning Proxy (Highest ROI)

**BERT research finding:** Pre-trained models converge in as few as 3 epochs on downstream tasks. For prompting, this means 3-5 high-quality examples outperform 20 mediocre ones.

**Current state audit:**

| Prompt | Few-Shot Examples | Quality | Issues Observed |
|--------|-----------------|---------|-----------------|
| `INJURY_BLURB_PARSE_PROMPT` | 5 examples ✅ | Excellent | None — this is the template |
| `GAME_NOTES_TEMPLATE` | 0 examples ❌ | Zero-shot | Inconsistent section ordering, missing pipe separators |
| `SPOTLIGHT_TEMPLATE` | 0 examples ❌ | Zero-shot | Kyle Anderson 400 Bad Request (malformed Markdown) |
| `_haiku_sanity_check` | 0 examples ❌ | Zero-shot | Occasional false FLAGs on GTD players who played |
| `_sonnet_curate` | 0 examples ❌ | Zero-shot | No guidance on what a "good portfolio" looks like |

**The fix for each:**

### GAME_NOTES_TEMPLATE — Add 1 complete example card
The example should show exactly the Markdown format, section order, and tone. Claude will match it precisely. One completed example beats 500 words of format instructions.

### SPOTLIGHT_TEMPLATE — Add 1 complete example spotlight
Critical: include an example where the player IS the player being analyzed (not a generic placeholder). This eliminates the Markdown format drift that caused 400 errors.

### Sonnet curation — Add 1 GOOD and 1 BAD selection example
```
EXAMPLE OF GOOD SELECTION: [bet_id=101] Tyrese Haliburton PTS OVER 22.5
  ✓ DIAMOND tier, 12.3% edge, favorable matchup, clean injury status
  ✓ Diversifies from existing REB pick in same game
  → SELECTED rank=1

EXAMPLE OF BAD SELECTION: [bet_id=102] Goga Bitadze BLK OVER 1.5
  ✗ CORE ASSET tier — lower priority
  ✗ BLK OVER historically 33.6% WR in this system — documented weak category
  ✗ Duplicates game coverage (already have 2 picks from this game_id)
  → NOT SELECTED
```

**Files to update:** `utils/claude_prompts.py`

---

## Pattern 4: max_seq_length — Token Budget Discipline

**BERT pattern:** Every sequence is truncated to `max_seq_length=128` tokens. The truncation heuristic (`_truncate_seq_pair`) removes tokens from the LONGER sequence first — protecting the shorter, more information-dense sequence.

**Current state — Risky injection points:**
```python
# morning_brief.py — these can be arbitrarily long
GAME_NOTES_TEMPLATE.format(
    situational_context=situational_context,    # could be 2000 chars
    injury_intel_block=injury_intel_block,       # could be 1500 chars
    beneficiary_block=beneficiary_block,         # could be 800 chars
    edges_block=edges_block,                     # could be 3000 chars
)
```

If total prompt > 8K tokens on Haiku, you hit the context limit and get truncated output with no warning.

**Fix — Pre-truncate before `.format()`:**
```python
MAX_BLOCK = {
    'situational_context': 500,
    'injury_intel_block': 600,
    'beneficiary_block': 400,
    'edges_block': 800,
}

def _safe_inject(text, max_chars):
    if len(text) > max_chars:
        return text[:max_chars] + "... [truncated]"
    return text
```

**Files to update:** `morning_brief.py` (template variable injection block ~lines 363-430)

---

## Pattern 5: Next Sentence Prediction → News Relevance Gate

**BERT pattern:** NSP task trains the model to answer "Is sentence B a logical continuation of sentence A?" This is the most under-appreciated BERT capability and directly maps to a gap in our pipeline.

**Current state — `_score_game()` in `morning_brief.py`:**
```python
if any(kw in news for kw in _INJURY_KWS):   score += 1.5
if any(kw in news for kw in _NARRATIVE_KWS): score += 0.5
```

This keyword matching has no sense of whether the news is relevant TO THE SPECIFIC BETS in that game.

**Proposed Haiku relevance gate (~$0.0001/game, 5 games/day = $0.0005/day):**
```python
def _haiku_news_relevance(game_bets: list[dict], news: str) -> dict:
    """
    NSP-style: Does this news change anything for these specific bets?
    Returns: {"score_delta": float, "key_signal": str, "affected_players": list}
    """
    players = [b['player_name'] for b in game_bets[:5]]
    stats = list({b['stat_category'] for b in game_bets})

    prompt = f"""
VALID OUTPUT: {{"score_delta": <-2.0 to +2.0>, "key_signal": "<10 words>", "affected_players": [<names or []>]}}

BETS IN THIS GAME:
Players: {', '.join(players)}
Stats being bet: {', '.join(stats)}

NEWS:
{news[:600]}

QUESTION: Does this news change the expected outcome for any of these specific bets?
- Positive score_delta (0.5-2.0): News boosts confidence (player returning, favorable news)
- Negative score_delta (-0.5 to -2.0): News reduces confidence (late scratch, unfavorable)
- Zero: News is irrelevant to these specific players/stats
Return JSON only."""
```

This replaces keyword matching with semantic reasoning about relevance.

---

## Pattern 6: Domain-Specific Context Injection (Domain Pre-training Proxy)

**BERT research finding:** "If your task has a large domain-specific corpus available (e.g., 'movie reviews'), it will likely be beneficial to run additional steps of pre-training on your corpus."

For us: our `bet_recommendations` table IS our domain corpus. We have 14,000+ settled bets with documented win rates. This data should be injected into every curation prompt as "system knowledge."

**Current state — Sonnet curation prompt:**
No mention of our system's historical performance patterns.

**Improved — Inject domain knowledge as system context:**
```python
SYSTEM_KNOWLEDGE = """
LUDI-BOT DOCUMENTED WIN RATES (14,000+ settled bets, Jan-Feb 2026):
- BLOCKS UNDER: 63.2% WR (870 bets) — STRONGEST signal, prioritize
- UNDER bets overall: 55.0% WR — prefer UNDER when edge is equal
- OVER bets overall: 42.1% WR — OVER plays need 10%+ edge minimum
- BLK OVER: 33.6% WR — NEVER select (filtered by system, should not appear)
- PTS OVER (line 25+): 30.5% WR — weak, deprioritize high-line PTS OVER
- 20%+ edge bets: 44.8% WR — edge alone does NOT predict win rate (books adjust)
- <5% edge bets: 58.3% WR — low edge, high-frequency bets can outperform

CURRENT SCORING ENVIRONMENT: {env_label} ({over_rate:.0%} 14d OVER hit rate)
"""
```

This gives Claude our actual empirical knowledge, not just instructions. The model can now reason: "System says UNDER bets outperform, and I'm choosing between two equal-edge plays — prefer the UNDER."

**Files to update:** `scripts/curate_plays.py` — `_sonnet_curate()` system prompt

---

## Pattern 7: Knowledge Distillation — Sonnet → Haiku Feedback Loop

**BERT pattern:** Smaller BERT models are most effective via knowledge distillation — the small model learns labels produced by the large model teacher.

**Current state:** Sonnet picks Top 5 bets. Haiku runs the sanity gate. No feedback between them.

**Proposed feedback loop:**
When Sonnet selects a bet that Haiku initially wanted to FLAG (but passed deterministic), that's a label: "Haiku was wrong here." When Sonnet avoids a bet despite it passing Haiku, that's another label.

**Simple version (no code required):** Weekly review of which bets Haiku passed but Sonnet skipped → update Haiku's `FLAG` criteria based on patterns.

**Automated version (future):** After `curate_plays.py` runs, log:
```sql
-- Create table: haiku_sonnet_disagreements
-- player_name, stat, bet_side, haiku_result, sonnet_selected, outcome
-- Weekly batch: Claude Haiku re-reads disagreements → update criteria
```

This is Phase 8.19 territory. Document for future implementation.

---

## Pattern 8: Output Contract Validation

**BERT pattern:** `convert_single_example()` asserts exact lengths after tokenization:
```python
assert len(input_ids) == max_seq_length
assert len(input_mask) == max_seq_length
assert len(segment_ids) == max_seq_length
```

Failures are caught immediately, not silently propagated.

**Current state:** Claude responses parsed with `try/except json.JSONDecodeError → PASS`. Failures are silently swallowed.

**Improved — Log parse failures for audit:**
```python
except (json.JSONDecodeError, KeyError) as e:
    print(f"[HAIKU PARSE FAIL] {bet['player_name']}: {e} | raw={response[:100]}")
    # Still default to PASS, but LOG it
    return 'PASS', f'[parse_error: {type(e).__name__}]'
```

Over time, parse failure logs reveal which prompts are producing malformed outputs — allowing targeted prompt fixes.

---

## Implementation Priority

| Priority | Pattern | Effort | Impact | File |
|----------|---------|--------|--------|------|
| 1 | Few-shot example in GAME_NOTES_TEMPLATE | 45 min | High | `claude_prompts.py` |
| 2 | Few-shot example in SPOTLIGHT_TEMPLATE | 30 min | High | `claude_prompts.py` |
| 3 | Domain WR stats in Sonnet curation | 20 min | Medium | `curate_plays.py` |
| 4 | text_a/text_b separation in templates | 60 min | Medium | `claude_prompts.py` |
| 5 | Label space in Haiku system prompt | 15 min | Medium | `curate_plays.py` |
| 6 | Pre-truncate injected blocks | 30 min | Low-Med | `morning_brief.py` |
| 7 | Haiku NSP news relevance gate | 2 hrs | Medium | `morning_brief.py` |
| 8 | Parse failure logging | 15 min | Low | `curate_plays.py` |
| 9 | Sonnet→Haiku feedback loop | Future | High | Phase 8.19 |

---

## What NOT to Do

- **Do NOT** implement BERT itself — Claude IS the pre-trained model. We only control fine-tuning (prompts).
- **Do NOT** add more examples than 5 per prompt. BERT converges in 3 epochs; more examples = diminishing returns and token cost.
- **Do NOT** change the Haiku/Sonnet split — this maps exactly to BERT's architecture (fast classifier head + deep representation). It's correct.
- **Do NOT** change the system/user split — `system=` for stable role/constraints (enables caching), `user=` for dynamic game data. This is already optimal.
- **Do NOT** raise temperature above 0.2 for any structured output. BERT inference is deterministic. Our classification tasks should be too.

---

## Reference Files

- `utils/claude_prompts.py` — All prompt templates
- `utils/claude_client.py` — API client, model selection, auth
- `scripts/curate_plays.py` — Haiku sanity gate + Sonnet curation
- `morning_brief.py` — Game notes + spotlight generation, `_score_game()`
- `/Users/flyprice/Desktop/Ludi Informatio/Projects/bert/` — BERT source reference

---

*Authored Feb 21, 2026 — based on google-research/bert codebase + S1877050924025766 (Procedia CS 2024)*
