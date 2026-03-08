# AI Employee Training Paradigms

**Created:** March 8, 2026
**Purpose:** 7 academic LLM training paradigms adapted for AI employee (subagent) training
**Applies to:** All employees in `.claude/agents/*.md` + `employees/*/ONBOARDING.md`
**Source:** Phase 9 research — DPO, CoT, Constitutional AI, Knowledge Distillation, Reflexion, Many-Shot ICL

---

## Overview

Each AI employee (Henrik, Silas, Lena, Vera, Kai, Solomon, Maren, Iris) has three training layers:
1. **Agent YAML** (`.claude/agents/*.md`) — model, tools, constraints
2. **SOUL.md** (`employees/*/SOUL.md`) — persona, domain knowledge, behavioral principles
3. **ONBOARDING.md** (`employees/*/ONBOARDING.md`) — procedures, examples, escalation

These 7 paradigms enhance all three layers. Each paradigm includes the academic source, the pattern, and a concrete employee example.

---

## Paradigm 1: DPO / Negative Examples

**Source:** Direct Preference Optimization (Rafailov et al. 2023) + ELECTRA replaced token detection (Clark et al. 2020)

**Principle:** Models trained on preferred/dispreferred pairs outperform positive-only training. Showing what's WRONG is 4× more training-efficient than only showing what's right.

**Pattern:** Every ONBOARDING.md should include at least 2 "wrong output" examples alongside correct ones.

**Format:**
```markdown
### Example: WRONG — [description of the error]
[The bad output]
**Why this is wrong:** [1-2 sentence explanation]

### Example: CORRECT — [description of proper approach]
[The good output]
```

**Employee-specific examples:**

| Employee | Wrong Example to Add |
|----------|---------------------|
| Henrik | "Approved a PR with Tank01 composite ID (28398804489) passing through — should have flagged as dirty" |
| Lena | "Reported 71% WR with N=7 as a finding — insufficient sample, p=0.23, not significant" |
| Vera | "Reported CLEAR TO RUN when injury table was 25.5h old — threshold is 24h, should have flagged" |
| Silas | "Reported pipeline healthy but didn't check recent workflow runs — 5 silent failures undetected" |
| Solomon | "Routed a Module C change to Gemini — Module C is out-of-scope for junior dev" |
| Maren | "Approved a prompt change that removed `*(Unverified)*` tag but left the unverified content — should have removed the content entirely" |

---

## Paradigm 2: Chain-of-Thought (CoT)

**Source:** Wei et al. 2022 — "Chain-of-Thought Prompting Elicits Reasoning in Large Language Models"

**Principle:** Forcing explicit reasoning traces BEFORE output improves classification accuracy by 12-15% and creates an auditable trail.

**Pattern:** Every structured output should include a `Reasoning:` field before the `Verdict:` field.

**Format:**
```markdown
### Before (no CoT)
✅ canonical_games JOIN — correct

### After (with CoT)
🔍 canonical_games JOIN — checking for Pattern-B (date+team pair)...
   Found: `JOIN canonical_games cg ON cg.date = g.date AND cg.home_team = g.home_team`
   Reasoning: Uses canonical_games (not games table), prevents 3× row inflation.
   Verdict: ✅ PASS
```

**Where to apply:**
- Henrik audit: reasoning before each of 11 checklist items
- Lena analysis: reasoning chain from data → finding → actionable recommendation
- Vera pre-flight: reasoning for each health check (not just pass/fail)
- Sonnet curation: `"thinking"` field in JSON output before `"grade"`

---

## Paradigm 3: Knowledge Distillation Loops

**Source:** Hinton et al. 2015 + BERT Pattern 7 (Sonnet→Haiku) + LIMA (2023, 1000 examples suffice)

**Principle:** Findings from one employee should flow into other employees' training. A finding that stays siloed has zero downstream impact.

**Pattern:** Create explicit knowledge flow paths between employees.

**Flow diagram:**
```
Lena discovers pattern → logs to employees/lena/FINDINGS_LOG.md
                          ↓
Solomon reads finding → adds to relevant employee's ONBOARDING.md
                          ↓
Downstream employee's next invocation benefits from the knowledge
```

**Specific flows:**
| Source | Finding Type | Destination | Integration Point |
|--------|-------------|-------------|-------------------|
| Lena | "BLK UNDER 63% WR" | Maren | Add to curation prompt domain context (Pattern 6) |
| Lena | "B2B Guards underprojected +1.5 pts" | Module C calibration | Bake into fatigue modifier or residual correction |
| Henrik | "normalize_bdl_abbr missing" | Gemini ONBOARDING | Add to "Known Gotchas" section |
| Vera | Schema mismatch found | Henrik | New audit checklist item |
| Silas | Recurring workflow failure | Solomon | Add to routing decision tree |

**Update cadence:** After each significant finding. Solomon is responsible for routing.

---

## Paradigm 4: Constitutional AI Self-Check

**Source:** Bai et al. 2022 (Anthropic) — "Constitutional AI: Harmlessness from AI Feedback"

**Principle:** Defining explicit principles that the model self-critiques against before outputting. The model generates, then reviews its own output against the constitution.

**Pattern:** Add a "Before Submitting" checklist to every employee's ONBOARDING.md.

**Template:**
```markdown
## Before Submitting Any Output
1. [ ] Does my output match the required format exactly?
2. [ ] Have I cited specific data sources (table, column, date range)?
3. [ ] [Domain-specific check 1]
4. [ ] [Domain-specific check 2]
5. [ ] Would I be confident showing this to the user with zero additional context?
```

**Employee-specific checklists:**

**Henrik:**
1. Did I check all 11 audit points?
2. Did I verify no new hardcoded constants that should be learned?
3. Did I check that no existing functions were accidentally deleted?
4. Is every finding backed by a specific line number?

**Lena:**
1. Does every finding have N ≥ 20?
2. Did I include p-value and confidence level?
3. Did I check for confounds (B2B, game total, opponent strength)?
4. Is this finding actionable for Module E, F, or Curation?

**Silas:**
1. Did I verify the service is actually down before alerting?
2. Did I check the status page API (not just workflow logs)?
3. Is my severity level (🔴/🟡/🟢) justified by the evidence?
4. Did I include the specific threshold that was violated?

---

## Paradigm 5: Many-Shot ICL (In-Context Learning)

**Source:** Google DeepMind 2024 — "Many-Shot In-Context Learning"

**Principle:** 50-100 examples consistently outperform 3-5 for structured tasks. Quality matters more than quantity, but MORE quality examples > fewer.

**Pattern:** Expand ONBOARDING.md from 1-2 examples to 5-8 real outputs per employee, annotated with quality notes.

**Format:**
```markdown
## Output Gallery (Real Examples)

### Example 1: HIGH QUALITY — [what makes it good]
[Full output from a real production run]
**Quality note:** [Why this is the gold standard]

### Example 2: ACCEPTABLE — [minor issues]
[Output with minor formatting issues]
**Quality note:** [What could be improved]

### Example 3: WRONG — [what went wrong] (DPO negative)
[Bad output]
**Quality note:** [Why this fails and how to fix]
```

**Source for examples:** Extract from `claude_analysis_log`, session transcripts, and actual employee outputs from production runs.

**Selection method:** TF-IDF similarity matching (Few-Shot Dilemma 2025) — choose examples most similar to the current task, not random.

---

## Paradigm 6: Reflexion (Memory-Based Self-Improvement)

**Source:** Shinn et al. 2023 — "Reflexion: Language Agents with Verbal Reinforcement Learning"

**Principle:** Agent reflects on failures, stores reflections in memory, retries with accumulated wisdom. Over time, the agent avoids repeating past mistakes.

**Pattern:** Create `employees/{name}/LESSONS_LEARNED.md` consulted at the start of every invocation.

**File format:**
```markdown
# Lessons Learned — [Employee Name]

## [Date]: [Brief title]
- **What happened:** [1-2 sentences]
- **What went wrong:** [Root cause]
- **Lesson:** [What to do differently next time]
- **Applies to:** [Which task types this affects]
```

**Agent integration:** Add to agent YAML description or instructions:
```
"Before starting work, read employees/{name}/LESSONS_LEARNED.md to avoid repeating past mistakes."
```

**Maintenance:**
- Cap at 20 entries (oldest roll off to `_ARCHIVE` section within the file)
- Employee updates their own file after a mistake is identified
- Solomon reviews quarterly for cross-employee patterns

---

## Paradigm 7: Confidence Scoring

**Source:** LLM-as-Judge Survey (Dec 2024) — Forcing confidence scores improves calibration and enables downstream filtering.

**Principle:** Every employee output should include a confidence level. Binary pass/fail loses information that downstream consumers need.

**Standard levels:**
| Level | Criteria | When to Use |
|-------|----------|-------------|
| **HIGH** | N > 100, p < 0.01 (or equivalent certainty) | Strong evidence, clear pattern, reproducible |
| **MEDIUM** | N > 50, p < 0.05 (or moderate certainty) | Reasonable evidence, may need more data |
| **LOW** | N < 50 or p > 0.05 (or uncertain) | Preliminary, requires validation |

**Output format (standardized across all employees):**
```
Confidence: HIGH — [brief justification]
```

**How downstream systems use confidence:**
- HIGH findings → auto-inject into Module E/F modifiers
- MEDIUM findings → queue for human review
- LOW findings → log for future validation, do NOT act on

---

## Implementation Checklist

| Paradigm | Add to ONBOARDING.md | Add to Agent YAML | Add to Skills | Sprint |
|----------|---------------------|-------------------|---------------|--------|
| 1. DPO/Negative Examples | 2+ wrong examples | — | — | Sprint 1 (Lena) |
| 2. Chain-of-Thought | Reasoning trace format | — | Require `Reasoning:` field | Sprint 3 |
| 3. Knowledge Distillation | — | — | FINDINGS_LOG.md flow | Sprint 4 |
| 4. Constitutional Self-Check | "Before Submitting" checklist | — | — | Sprint 3 |
| 5. Many-Shot ICL | 5-8 real examples | — | — | Sprint 5 |
| 6. Reflexion | — | Read LESSONS_LEARNED.md | — | Sprint 4 |
| 7. Confidence Scoring | Standard levels table | Output format update | — | Sprint 5 |

---

## References

- Rafailov et al. 2023 — DPO
- Clark et al. 2020 — ELECTRA (replaced token detection)
- Wei et al. 2022 — Chain-of-Thought Prompting
- Hinton et al. 2015 — Knowledge Distillation
- Bai et al. 2022 — Constitutional AI (Anthropic)
- Google DeepMind 2024 — Many-Shot In-Context Learning
- Shinn et al. 2023 — Reflexion
- LLM-as-Judge Survey, Dec 2024 — Confidence scoring + bias mitigation

---

*Created March 8, 2026 — reusable paradigms for any AI employee workforce*
