# Skills Guide — Writing, Assigning & Evolving Employee Skills

**Created:** March 1, 2026
**Purpose:** How to create, assign, refine, and retire skills for the AI Employee Workforce. Maren's reference for ideating new skills over time.

---

## What Is a Skill?

A skill is a `SKILL.md` file that gives a Claude Code agent a **specialized workflow mode**. When an employee invokes a skill, they load its instructions into their context and follow that workflow — like switching from "default mode" to "audit mode" or "research mode."

**Skills are not:**
- Scripts or code (those live in `scripts/`)
- Prompts injected into the pipeline (those live in `utils/claude_prompts.py`)
- Standing instructions (those live in `AGENTS.md` or `SOUL.md`)

**Skills are:**
- Ordered, multi-step workflows with specific output formats
- Domain-specialized procedures that would be too long to put in a soul file
- Reusable across sessions — the employee always follows the same process

---

## Anatomy of a Skill

Every skill file lives at `.claude/skills/{skill-name}/SKILL.md` and follows this structure.

> **Gemini mirror:** Skills are duplicated in `.gemini/skills/{skill-name}/SKILL.md` for the Gemini CLI writer. Commands that invoke skills live in `.gemini/commands/{name}.toml` (TOML format with `{{args}}`) vs Claude's `.claude/commands/{name}.md` (Markdown with `$ARGUMENTS`). Keep both in sync.

```markdown
---
name: skill-name
description: >
  One paragraph describing when this skill is invoked and what it does.
  Include trigger phrases if applicable.
---

# Skill Name

## Overview
What this skill does in 2-3 sentences. Who uses it. When to use it vs alternatives.

## Workflow

### Step 1 — [Name]
Clear instructions. What to read. What to do. What to produce.

### Step 2 — [Name]
...

## Output Format
Exact format the skill returns. Always include a template.

## When to Use
- Use for: [specific trigger conditions]
- Don't use for: [cases this skill shouldn't handle]
```

**Optional extras:**
- `references/` subfolder — supporting docs the skill reads (e.g., `schema-blueprints.md`)
- `scripts/` subfolder — helper scripts the skill runs (e.g., `audit_temporal_integrity.py`)

---

## Current Skills Catalog

**Location:** `.claude/skills/`

| Skill | File | Owner | Purpose | When to invoke |
|-------|------|-------|---------|----------------|
| `session-brief` | `.claude/skills/session-brief/SKILL.md` | Solomon | Start-of-session orientation | Every session start |
| `session-debrief` | `.claude/skills/session-debrief/SKILL.md` | Solomon | End-of-session wrap-up + commit | Every session end |
| `sports-data-model-architect` | `.claude/skills/sports-data-model-architect/SKILL.md` | Henrik | Full schema audit + design + implementation | Any DB schema change |
| ↳ `architect-audit` | `.claude/commands/architect-audit.md` | Henrik | Audit phase only — run scripts, return severity findings | Step 1 of schema work |
| ↳ `architect-design` | `.claude/commands/architect-design.md` | Henrik | Design phase only — propose minimal additive changes | Step 2, after audit findings reviewed |
| ↳ `architect-implement` | `.claude/commands/architect-implement.md` | Henrik | Implement phase only — migration-safe SQL/Python + validation | Step 3, after design approved |
| `ludi-audit` | `.claude/skills/ludi-audit/SKILL.md` | Henrik | Ludi-specific 10-point gotcha checklist | After any `.py` code change |
| `backtest` | `.claude/skills/backtest/SKILL.md` | Vera | Model validation suite | Weekly or after model changes |
| `daily` | `.claude/skills/daily/SKILL.md` | Vera | Pipeline health check | Daily pre-pipeline |
| `simplify` | (global plugin) | Henrik | Code quality + DRY review | After writing new code |
| `research` | (global plugin) | Maren | Quick web research | On-demand competitive/API questions |
| `ultrathink` | (global plugin) | Maren | Deep thinking protocol | Complex architectural decisions |
| `design` | (global plugin) | Maren | Design philosophy check | UI/UX decisions |

---

## Employee Skill Stack

| Employee | Assigned Skills | Role |
|----------|----------------|------|
| Solomon (PM Lead) | `session-brief`, `session-debrief` | Coordinates all work, owns session lifecycle |
| Henrik (Code Auditor) | `ludi-audit`, `sports-data-model-architect`, `architect-audit`, `architect-design`, `architect-implement`, `simplify` | Reviews ALL code changes |
| Vera (Pipeline QA) | `daily`, `backtest` | Pre-flight checks, model validation |
| Lena (Data Analyst) | `backtest`, `sports-data-model-architect` | Model calibration, stat confidence grades, backtest analysis |
| Maren (Content/Ideas) | `ultrathink`, `research`, `design` | Brainstorming, BERT refinement, skill ideation |
| Silas (Monitor) | N/A — runs via OpenClaw | Always-on monitoring, not skill-based |
| Iris (Scout) | N/A — runs via OpenClaw | Always-on collection, not skill-based |

---

## Refinement Protocol — When to Update a Skill

A skill should be refined when **empirical evidence shows it isn't working**. Don't refine preemptively.

### Trigger Conditions (any one is sufficient)

| Trigger | Example | Action |
|---------|---------|--------|
| **3+ false positives** | Henrik's ludi-audit flags the same non-issue three times | Remove or tighten that check |
| **3+ missed catches** | A known gotcha slips through ludi-audit 3 times | Add a new check or harden an existing one |
| **Output format drifted** | Henrik's audit reports aren't in P0/P1/P2 format anymore | Clarify the output template section |
| **New gotcha discovered** | A new bug pattern found in `MEMORY.md` or `KNOWN_FIXES.md` | Add to the relevant checklist |
| **Skill invoked wrong** | Employee uses ludi-audit when they should use simplify | Tighten the "When to Use" section |
| **Context window pressure** | Skill reads too many files and runs out of tokens | Trim reference docs or split into sub-skills |

### How to Refine

1. Find the specific failing step (read the skill, identify the weak section)
2. Make the minimal change — don't rewrite the whole skill for one issue
3. Test: invoke the skill on a recent example and verify the fix works
4. Note the change in the skill's header (update `**Last Updated:**` if the skill has one)
5. Log it in `best-practices/ops-hub/KNOWN_FIXES.md` if it was a real production miss

---

## Maren's Skill Ideation Framework

Maren owns skill ideation for the team. Use this process to evaluate whether something deserves a new skill.

### The 3-Question Test

**Before proposing a new skill, Maren asks:**

1. **Is it repeated?** — Has someone done this workflow 3+ times manually without a skill? One-off tasks don't need skills.
2. **Is it specialized?** — Does it require domain knowledge that wouldn't be obvious from `AGENTS.md` or `CLAUDE.md`? Generic tasks don't need skills.
3. **Is it ordered?** — Does the workflow have a specific sequence of steps that must be followed? Unstructured tasks don't need skills.

If all three are YES → propose the skill. If any is NO → document it as a prompt pattern instead (in `PROMPT_ENGINEERING_PATTERNS.md` or `ai-prompting/`).

### Skill Ideation Triggers

Maren should evaluate new skills when:
- A session debrief notes the same manual process 3 sessions in a row
- A new employee capability is added (new data source, new workflow, new API)
- A global plugin is discovered that could be adapted for Ludi's specific needs
- An employee consistently asks Solomon for the same multi-step guidance
- A new ROADMAP phase begins that introduces domain patterns not in existing skills

### Naming Conventions

| Pattern | Example | Use when |
|---------|---------|----------|
| `ludi-{thing}` | `ludi-audit`, `ludi-scout` | Ludi-specific workflows |
| `{employee}-{thing}` | (avoid — use ludi- prefix instead) | Don't couple skill name to employee |
| Verb-first | `validate-schema`, `backfill-odds` | Action-oriented one-shot tasks |
| Noun-first | `session-brief`, `sports-data-model-architect` | Named workflows/modes |

**Rule:** Never name a skill after the employee who uses it (e.g., `henrik-review`). Skills can be reassigned. Name them after what they do.

### Skill vs Prompt Pattern — Decision Table

| Scenario | Use skill | Use prompt pattern |
|----------|-----------|-------------------|
| Multi-step workflow (3+ sequential steps) | ✅ | ❌ |
| Single-shot classification or generation | ❌ | ✅ |
| Domain-specific checklist | ✅ | ❌ |
| Temperature / output format rule | ❌ | ✅ |
| Repeated across many sessions | ✅ | ❌ |
| Tightly coupled to one prompt injection point | ❌ | ✅ |

---

## Skill Creation Template

When creating a new skill, copy this template and fill it in:

```markdown
---
name: {skill-name}
description: >
  One paragraph. What employee uses this, when, and what it produces.
  Trigger phrases: "{phrase}", "{phrase}".
---

# {Skill Display Name}

**Last Updated:** {date}
**Owner:** {employee name}

## Overview
What this skill does. How it relates to other skills (what it replaces, what it supplements).

## When to Use
- Use for: ...
- Don't use for: ...
- Run AFTER: {other skill if applicable}
- Run INSTEAD OF: {skill this replaces, if applicable}

## Workflow

### Step 1 — {Name}
Instructions. What to read. What to do.

### Step 2 — {Name}
Instructions.

### Step N — Output
What to produce. See Output Format below.

## Output Format

```
## {Skill Name} — [{context}]

### {Section 1}
[content]

### {Section 2}
[content]

Verdict: {OUTCOME_A} | {OUTCOME_B}
[One sentence summary]
```

## References
- {link to relevant best-practices doc}
- {link to relevant CLAUDE.md section}
```

---

## Deprecating / Retiring Skills

Retire a skill when:
- The workflow it covers no longer exists (feature removed, pipeline changed)
- A better skill supersedes it (merge them, keep the better one)
- The skill hasn't been invoked in 30+ days and the workflow it covered is now documented elsewhere

**Retirement process:**
1. Remove the skill file (or move to `.claude/skills/archived/`)
2. Update `AGENTS.md` to remove the skill assignment
3. Update this catalog table above
4. Note in `MEMORY.md` what replaced it

---

## Related Docs

- `PROMPT_ENGINEERING_PATTERNS.md` — BERT-derived patterns for Claude prompt engineering
- `PM_BOT_NOTES_GUIDE.md` — ROADMAP grounding for Gemini PM messages
- `AI_PROMPTING_BEST_PRACTICES.md` — Temperature rules, cost breakdown per model
- `AGENTS.md` (project root) — Employee role definitions + skill assignments
- `docs/projects/AI_EMPLOYEE_WORKFORCE.md` — Full PRD for the 7-employee workforce
