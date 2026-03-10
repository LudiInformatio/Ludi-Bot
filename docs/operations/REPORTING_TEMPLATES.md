# Reporting Templates

**Created:** March 9, 2026
**Owner:** Solomon (PM)
**Purpose:** Standardize agent-to-Solomon and Solomon-to-owner reporting. Scannable in under 60 seconds.

---

## Template A — Agent-to-Solomon Report

Use this format when reporting back to Solomon after any assigned task. All fields required. Omit none — write "N/A" if not applicable.

```
## [Agent Name] Report — [Date] [Time]

**Task:** [T-ID if assigned, or brief task description]
**Status:** COMPLETE | PARTIAL | BLOCKED

### Work Done
- [Bullet per action taken. Be specific — file name, line number, query run.]
- [If code changed: what was changed and why, not just that it was changed.]

### Key Findings
- [Bullet per finding. Include confidence level: HIGH / MEDIUM / LOW and sample size where applicable.]
- [Flag anything unexpected or contradicting prior assumptions.]

### Files Changed
| File | Lines | Change |
|------|-------|--------|
| `path/to/file.py` | L120–135 | [what changed] |
| `path/to/other.md` | N/A | [new file created] |

### Gaps / Risks
- [What is still unknown or unresolved.]
- [Any dependencies that could break downstream.]
- [Data quality caveats (small n, date range limitations, etc.).]

### Recommended Next Step
[One sentence. Name the specific file, task, or person this should go to next.]
```

**Notes:**
- Confidence levels: HIGH = statistically significant or code-verified. MEDIUM = directional but small sample or inferred. LOW = hypothesis only, not validated.
- "Files Changed" is mandatory for any code or doc edit — omitting it blocks Henrik audit.
- If BLOCKED: describe exactly what is blocking and what is needed to unblock.

---

## Template B — Solomon-to-Owner Report

Use this after any sprint or multi-employee workstream completes. This is the final delivery document.

```
## Solomon Sprint Report — [Sprint Name] — [Date]

**Employees Involved:** [list]
**Sprint Duration:** [start date] → [end date or "same session"]

### Tasks Completed

| Task ID | Owner | Status | Commit / File |
|---------|-------|--------|---------------|
| T-001   | Lena  | DONE   | `docs/operations/REPORTING_TEMPLATES.md` |
| T-002   | Henrik| APPROVED | [commit hash or N/A] |

### Key Findings
- [One bullet per insight that affects decisions. Cite employee + confidence level.]
- [If data-driven: include n and WR or metric where relevant.]

### Decisions Made This Sprint
- [What was decided, and why. These are permanent record entries.]
- [Include any "will NOT do" decisions — important to log what was explicitly rejected.]

### Open Items / Blockers
| Item | Owner | Status | Blocking |
|------|-------|--------|---------|
| [description] | [name] | OPEN | [what it blocks] |

### Recommended Next Action
[One sentence. The single most important thing to do next, with the specific file or ticket.]
```

**Notes:**
- "Tasks Completed" table must include commit hash for any code change — no hash = not verified.
- "Decisions Made" is permanent intel. Do not omit even if the decision feels minor.
- If no blockers: write "None — clear to proceed."
- Keep total length under 1 page (approx 40 lines). If findings require more, append a separate findings doc and link it.
