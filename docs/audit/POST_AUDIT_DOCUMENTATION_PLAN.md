# Post-Audit Documentation & Best Practices Integration

## Context

The 10-sprint comprehensive audit (Sprints 0-10) is complete. Two production bugs discovered during Sprint 10 have been fixed and verified. This plan addresses remaining documentation and knowledge capture work.

**Completed:**
- ✅ Bug 1: Morning brief title mode fixed (module_f.py, morning_brief.py)
- ✅ Bug 2: Defensive playtype filtering fixed (trend_engine.py, morning_brief.py)
- ✅ Best practices proposal document created (NEW_BEST_PRACTICES_PROPOSAL.md)
- ✅ Documentation cross-reference audit complete

**Pending:**
- Documentation cross-reference gaps in CLAUDE.md and README.md
- Optional: Integration of 3 critical patterns into existing best-practices files

---

## Phase 1: Documentation Cross-Reference Fixes (REQUIRED)

### Gap Analysis

| Document | Missing from CLAUDE.md | Missing from README.md |
|----------|----------------------|----------------------|
| TOOLS_GUIDE.md | ✗ | ✗ |
| STATUS_HISTORY.md | ✓ (present) | ✗ |
| Research docs | ✗ | ✓ (present) |

### Changes Required

**File 1: CLAUDE.md**

Add to "Project Context" section (after line 22):
```markdown
See @docs/TOOLS_GUIDE.md for task automation scripts and helpers.
```

Add to "Resources" section (after line 183):
```markdown
- **Tools Guide**: @docs/TOOLS_GUIDE.md (automation scripts, helpers)
- **Research**: `docs/research/` (competitive analysis, prompt engineering)
```

**File 2: README.md**

Add to "Documentation" table (after line 183):
```markdown
| [docs/TOOLS_GUIDE.md](docs/TOOLS_GUIDE.md) | Task automation scripts and helpers |
| [docs/STATUS_HISTORY.md](docs/STATUS_HISTORY.md) | Archived project status updates (Phases 1-4) |
```

### Verification

```bash
# Check all references exist
grep -l "TOOLS_GUIDE" CLAUDE.md README.md
grep -l "STATUS_HISTORY" CLAUDE.md README.md

# Expected:
# CLAUDE.md (both)
# README.md (both)
```

---

## Phase 2: Best Practices Integration (OPTIONAL)

### Rationale

The audit uncovered 10 patterns across 3 categories. The proposal document (NEW_BEST_PRACTICES_PROPOSAL.md) contains all details. Three patterns are critical enough to integrate into existing files:

1. **Schema Constraint Validation** (Data Modeling) - prevents silent insert failures
2. **Module-Level Constants** (Coding) - prevents magic values scattered across functions
3. **Parameter Propagation Debugging** (Debugging) - prevents tuple unpacking crashes

### Integration Strategy

**Pattern 1: Schema Constraint Validation**
- Target: `best-practices/data-modeling/README.md`
- Location: After "Pattern 2: CREATE TABLE IF NOT EXISTS" (line 93)
- Length: ~20 lines (example + explanation)

**Pattern 2: Module-Level Constants**
- Target: `best-practices/coding/README.md`
- Location: After "Pattern 2: Bash Default Variable Substitution" (line 87)
- Length: ~25 lines (before/after example)

**Pattern 3: Parameter Propagation Debugging**
- Target: `best-practices/debugging/README.md`
- Location: After "Pattern 2: Function Return Tuple Mismatch" (line 142)
- Length: ~30 lines (grep commands + example)

### Format Guidelines (Ultra-Lean)

Each pattern must follow existing file style:
- Title + one-sentence problem statement
- Code example (before/after or good/bad)
- Real incident reference from audit
- Zero philosophical commentary

Example structure:
```markdown
## Pattern N — Title

**Problem:** One sentence root cause.

**Example:**
[code block with before/after or good/bad]

**Real incident:** Module H `ON CONFLICT` mismatch (Sprint 8 finding).
```

### Updates Required After Integration

**File: best-practices/README.md**

If patterns are integrated, update pattern counts:
- Coding: 6 → 7 patterns
- Data Modeling: 7 → 8 patterns
- Debugging: 6 → 7 patterns

**File: MEMORY.md**

Add one-line entry:
```markdown
### Post-Audit Best Practices (Feb 21, 2026)
- 3 critical patterns integrated: Schema Constraint Validation, Module-Level Constants, Parameter Propagation Debugging
```

---

## Phase 3: Cleanup

### Archive Proposal Document

After Phase 2 (if executed):
```bash
mkdir -p docs/audit/proposals
mv docs/audit/NEW_BEST_PRACTICES_PROPOSAL.md docs/audit/proposals/
```

Rationale: Keep docs/ clean. Proposal document served its purpose once patterns are integrated.

### Update Audit Report

Add completion note to `docs/audit/AUDIT_2026_02_21.md`:
```markdown
### Post-Audit Follow-Up (Feb 21, 2026 PM)

**Documentation:**
- Cross-reference gaps fixed in CLAUDE.md and README.md
- TOOLS_GUIDE.md and STATUS_HISTORY.md now properly indexed

**Best Practices Integration:** [COMPLETED | DEFERRED]
- [If completed: 3 critical patterns integrated into existing files]
- [If deferred: Proposal document preserved at docs/audit/proposals/]
```

---

## Decision Point

**Phase 1 (Documentation Cross-References):** REQUIRED - execute immediately

**Phase 2 (Best Practices Integration):** OPTIONAL - user preference

**Options:**
1. Execute both phases → comprehensive knowledge capture
2. Execute Phase 1 only → minimal intervention, keep proposal as standalone reference

**Recommendation:** Execute Phase 1 immediately. Phase 2 can be deferred to next maintenance window if user prefers to keep proposal document as-is.

---

## Files Modified Summary

### Phase 1 Only (Required)
- CLAUDE.md (2 additions)
- README.md (2 additions)
- **Total: 2 files, ~6 lines changed**

### Phase 1 + Phase 2 (Optional)
- CLAUDE.md (2 additions)
- README.md (2 additions)
- best-practices/coding/README.md (~25 lines)
- best-practices/data-modeling/README.md (~20 lines)
- best-practices/debugging/README.md (~30 lines)
- best-practices/README.md (pattern count updates)
- MEMORY.md (1 entry)
- docs/audit/AUDIT_2026_02_21.md (completion note)
- **Total: 8 files, ~110 lines changed**

---

## Verification Steps

**Phase 1:**
```bash
# All docs are cross-referenced
grep -c "TOOLS_GUIDE\|STATUS_HISTORY" CLAUDE.md README.md
# Expected: 2 hits each file

# No broken links
grep -o '@[^ ]*' CLAUDE.md | while read f; do
  [ -f "${f#@}" ] || echo "BROKEN: $f"
done
```

**Phase 2 (if executed):**
```bash
# Pattern counts match
grep "Pattern [0-9]" best-practices/coding/README.md | wc -l
grep "Pattern [0-9]" best-practices/data-modeling/README.md | wc -l
grep "Pattern [0-9]" best-practices/debugging/README.md | wc -l

# Proposal archived
[ -f docs/audit/proposals/NEW_BEST_PRACTICES_PROPOSAL.md ] && echo "✅ Archived"
```

---

## Terminal Prompt for Agent

**Phase 1 Only:**
```bash
# Execute documentation cross-reference fixes only (required, minimal intervention)
# No best practices integration - keeps proposal document as standalone reference
```

**Phase 1 + Phase 2:**
```bash
# Execute full post-audit documentation plan
# Includes: cross-reference fixes + 3 critical pattern integrations + cleanup
# Results in comprehensive knowledge capture across all best-practices files
```

User selects execution mode based on preference.
