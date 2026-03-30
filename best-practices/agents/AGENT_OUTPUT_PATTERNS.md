# Agent Output Patterns
**Last Updated:** March 30, 2026

## Root Cause: Silent Agent Failure (No Output Returned)

### What happens
A subagent completes all its tool work but returns no text output. Resuming the
agent with a follow-up prompt retrieves the report because the work was already done —
the agent simply ran out of turns before writing its final summary.

### Why it happens
Every agent has a `maxTurns` cap (Haiku: 15, Sonnet: 30, Solomon: 50). Tool calls
consume turns. When an agent exhausts its turn budget doing reads/searches/bash
commands, no turns remain to write the final text response. The agent silently stops.

### Evidence from March 8, 2026
- Kai: 39 tool calls → hit 15-turn Haiku limit → no output
- Solomon: 45 tool calls → hit 30-turn Sonnet limit → no output
- Both recovered on resume because the underlying work was complete

---

## Fix: Output Rule (applied to all agents)

All 7 agent `.md` files include this section:

```
## Output Rule
Your FINAL action must always be a written text response summarizing your findings.
If you are approaching your turn limit, stop tool work immediately and write your
report with what you have. Never end your response on a tool call.
```

---

## Fix: maxTurns Configuration

| Agent | Model | maxTurns | Rationale |
|-------|-------|----------|-----------|
| Solomon | Sonnet | 50 | Heavy orchestration — reads ROADMAP, delegates, builds tickets |
| Henrik | Sonnet | 30 | Targeted audits — reads diffs, runs ludi-audit checklist |
| Lena | Sonnet | 30 | DB queries + analysis — bounded by query scope |
| Maren | Sonnet | 30 | Prompt audits — reads claude_prompts.py + proposes edits |
| Silas | Haiku | 15 | Health checks — fast, structured, bounded checks |
| Vera | Haiku | 15 | Pre-flight checks — pass/fail, limited tool scope |
| Kai | Haiku | 15 | Hygiene audit — git ls-files + find commands, well-scoped |

**Rule:** If an agent consistently returns no output, check turn consumption first.
Heavy tasks (build + audit + delegate) should go through Solomon (maxTurns: 50).
Single-domain tasks (audit only, QA only, health check only) stay within 15-30.

---

## Reducing Tool Usage

Three levers to reduce tool call count per agent run:

| Lever | How | Typical savings |
|-------|-----|-----------------|
| **Pre-scope the prompt** | Name exact files/line ranges instead of letting agent explore broadly | 5–15 tool calls |
| **Pre-pass context** | When chaining agents (Kai → Silas → Solomon), include prior agent's full findings in the next agent's prompt | Eliminates redundant reads |
| **Scope bash commands** | Tell agent to limit `git ls-files` / `find` to specific dirs, not repo root | Prevents broad sweeps |

### Example — scoped vs unscoped prompt

**Unscoped (high tool usage):**
> "Find the combo correlation logic and audit it."

**Scoped (low tool usage):**
> "Audit `module_f.py` lines 840–870 — specifically the `_map_stat()` combo correlation factors."

Scoped prompts cut tool calls because the agent reads exactly what's needed and stops.

---

## When to Resume vs Re-run

If an agent returns no output:
1. **Resume first** (`resume: <agentId>`) with a prompt like "Please provide your full report from the work you just completed."
2. The work is already done — resume retrieves it in 1 turn, no repeated tool calls.
3. **Re-run only if** the resume returns no useful context (rare).

Never re-run an agent that just returned no output without trying resume first — re-running wastes all the tool calls from the previous run.

---

## TK Task Contract Format (MANDATORY for all junior dev dispatches)

Every employee→junior dev handoff must use this 8-field contract. No unstructured prose. No exceptions.

```
TASK: [One-sentence description of what to build/change]
CONTEXT: [Why this is needed — sprint goal, blocker, or finding it addresses]
DELIVERABLE: [Exact files changed + what the output looks like]
DEADLINE: [Session / today / this sprint / next sprint]
RESOURCES: [Files to read, tables to query, prior examples to reference]
SUCCESS: [How completion is verified — specific assertion, query, or test]
CONFIDENCE: [Minimum confidence required: HIGH / MEDIUM / LOW — and N= if data-dependent]
ESCALATE_IF: [Specific conditions that should pause the task and route back to reviewer]
```

**Rules:**
- No `SUCCESS` field = task is incomplete spec. Reject and re-spec before dispatching.
- `ESCALATE_IF` must name at least one condition (e.g., "schema change touches >2 tables", "test fails on first run").
- `CONFIDENCE` must specify a minimum level. If data-dependent, state minimum N before marking complete.
- Applies to ALL employees, not just Henrik — Maren uses it for prompt proposals, Lena for schema specs, Silas for infra tasks.

**Why:** Tasks dispatched without this format routinely return wrong deliverables, skip verification, or fail silently. The 8-field contract forces spec completeness BEFORE execution. Adopted Mar 30, 2026.

---

## Agent Confidence Footer (MANDATORY for all audit reports)

Every Henrik audit report and any agent producing findings must end with:

```
CONFIDENCE: HIGH | MEDIUM | LOW
N= [integer — number of code lines, test results, or data points reviewed]
SOURCES: [files read, line numbers cited, test results referenced]
```

**Why:** Findings without sourcing cannot be acted on. The footer forces agents to cite specific evidence and prevents MEDIUM-confidence guesses from being treated as HIGH-confidence conclusions. Adopted Mar 30, 2026.

---

## 5-Cluster Parallel All-Hands Pattern

For deep cross-company reviews (50+ documents, multiple domains), dispatch 5 background agents simultaneously, each scoped to one domain:

| Cluster | Agent | Scope |
|---------|-------|-------|
| Engineering | Henrik | Code quality, pipeline risk, architectural findings |
| Ops/Infra | Silas | Infrastructure patterns, monitoring gaps, ops risk |
| AI/Prompts | Maren | Prompt patterns, calibration signals, BERT findings |
| Data/Schema | Lena | Schema design, data model patterns, query findings |
| Org/Summaries | Lena (or general-purpose) | People patterns, process findings, cross-cluster synthesis |

**Rules:**
- All 5 run in background (`run_in_background: true`) — do not block main session
- Each agent reads only their cluster's docs — no overlap
- Solomon synthesizes findings into architectural decisions after all 5 complete
- Token-efficient: extract last assistant message from task JSON with `python3 -c "import json; ..."` rather than reading full task file (avoids 90K+ token reads)

**Evidence from Mar 30, 2026:** 5-cluster review over 50+ Sankore docs resolved the 3-option game notes debate (Option A/B/C) in one session, surfaced DIAMOND tier inversion root cause, and identified the FUNNEL scheme misclassification bug.
