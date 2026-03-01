# Ludi-Bot Best Practices

This directory contains comprehensive best practices documentation organized by category. Each category contains detailed guides, quick references, and lessons learned from building and operating Ludi-Bot.

## Structure

```
best-practices/
├── api/                    # ✅ API integration patterns (COMPLETE)
│   ├── API_BEST_PRACTICES.md
│   ├── API_QUICK_REFERENCE.md
│   ├── API_DOCUMENTATION_INDEX.md
│   ├── LLM_INTEGRATION.md
│   └── SPORTSBOOK_TIERS_AND_MATH.md
├── ai/                     # ✅ Prompt engineering patterns (COMPLETE)
│   └── PROMPT_ENGINEERING_PATTERNS.md
├── ai-prompting/           # ✅ Operational AI prompting guide (COMPLETE)
│   └── AI_PROMPTING_BEST_PRACTICES.md
├── coding/                 # ✅ Code quality, patterns, style (COMPLETE)
│   └── README.md
├── data/                   # ✅ Stat confidence & edge calibration (COMPLETE)
│   └── STAT_CONFIDENCE_FRAMEWORK.md
├── data-modeling/          # ✅ Database design, schema patterns (COMPLETE)
│   └── README.md
├── debugging/              # ✅ Troubleshooting strategies (COMPLETE)
│   └── README.md
├── ops-hub/                # ✅ Claude Ops Hub institutional memory (AUTO-MAINTAINED)
│   ├── README.md
│   ├── KNOWN_FIXES.md       ← auto-appended by claude-ops-hub.yml on every diagnosis
│   └── DOMAIN_PATTERNS.md   ← few-shot examples per workflow domain
├── testing/                # 📋 Testing patterns and validation (INITIALIZED)
│   └── README.md
└── deployment/             # 📋 CI/CD, production operations (INITIALIZED)
    └── README.md
```

## Categories

### 📡 API Integration (`api/`)
**Status:** ✅ Complete (Feb 19, 2026)
- `API_BEST_PRACTICES.md` — 15 sections, 60+ examples; 25 real mistakes documented
- `LLM_INTEGRATION.md` — Claude/Anthropic Phase 8 integration patterns
- `API_QUICK_REFERENCE.md` — 1-page cheatsheet
- `SPORTSBOOK_TIERS_AND_MATH.md` — NC Legal book tiers, devig math, CLV formula

---

### 🤖 AI — Prompt Engineering Research (`ai/`)
**Status:** ✅ Complete (Mar 1, 2026)
- `PROMPT_ENGINEERING_PATTERNS.md` — 8 BERT-derived patterns mapped to Claude prompts
- Source: Google BERT codebase + Procedia CS 2024 sentiment paper
- Explains root cause of format drift, 400 errors, and few-shot vs zero-shot tradeoffs
- `PM_BOT_NOTES_GUIDE.md` — BERT grounding pattern applied to human-written ROADMAP notes; formula for `**Active Work:**`, `**Completed:**`, and `- [ ]` bullets so Gemini gets specific context
- `SKILLS_GUIDE.md` — How to write, assign, refine, and retire AI employee skills. Includes Maren's 3-question ideation test, refinement protocol, deprecation process, and skill creation template

### 🤖 AI — Operational Prompting Guide (`ai-prompting/`)
**Status:** ✅ Complete (Feb 20, 2026)
- `AI_PROMPTING_BEST_PRACTICES.md` — Practical rules for Haiku, Sonnet, and Perplexity Sonar
- Temperature rules, cost breakdown, injection points per pipeline stage

---

### 🔧 Coding Patterns (`coding/`)
**Status:** ✅ Complete (Feb 19, 2026)
- `README.md` — 7 patterns: error handling, tuple unpacking, bash defaults, lazy imports, type hints, module-level constants

---

### 📊 Data — Stat Confidence & Edge Calibration (`data/`)
**Status:** ✅ Complete (Feb 25, 2026)
- `STAT_CONFIDENCE_FRAMEWORK.md` — A+ to F grades across all stat markets; 14k+ bets analyzed
- Key finding: BLOCKS UNDER 70.7% WR; PTS OVER systematically overconfident at high edges
- `DVP_AND_SCHEME_METHODOLOGY.md` — DVP rankings methodology, scheme fingerprints, BERT training rules
- `CANONICAL_NAME_RESOLUTION.md` — Accent handling across APIs, two-direction transforms
- `SGP_AND_PROP_CURATION.md` — SGP correlation theory, prop value identification, portfolio rules
- `GAME_LINE_CURATION.md` — Game selection signals: rest differential, RLM, pace, spread zones, referee impact

---

### 🗄️ Data Modeling (`data-modeling/`)
**Status:** ✅ Complete (Feb 19, 2026)
- `README.md` — 9 patterns: schema design, canonical IDs, indexes, freshness validation, self-healing, constraint validation

---

### 🐛 Debugging (`debugging/`)
**Status:** ✅ Complete (Feb 19, 2026)
- `README.md` — 7 patterns: CI diagnosis playbook, silent failure detection, library param inspection, bash empty-var crash, function return mismatch, DB corruption check, parameter propagation
- Anti-pattern table: `except: continue` → always log; `|| echo` → use `${VAR:-default}`

---

### ✅ Testing (`testing/`)
**Status:** 📋 Initialized — topics outlined, patterns pending

### 🤖 Ops Hub Knowledge Base (`ops-hub/`)
**Status:** ✅ Active — auto-maintained by `claude-ops-hub.yml`

Unlike other folders (written by humans), this folder is written by Claude Ops Hub itself.
Each time the ops-hub diagnoses a failure, it appends an entry to `KNOWN_FIXES.md` and commits.

- `README.md` — folder overview + OAuth token refresh procedure
- `KNOWN_FIXES.md` — running log of diagnosed failures + actions taken (pre-seeded: 3 entries)
- `DOMAIN_PATTERNS.md` — few-shot worked examples per domain (Settlement, Pipeline, Data Sync, DB, Validation)

**BERT patterns applied** (from `ai/PROMPT_ENGINEERING_PATTERNS.md`):
- Pattern 1 (label space first): valid tier decisions defined before any log content
- Pattern 2 (section dividers): `=== METADATA ===` | `=== LOGS ===` separation
- Pattern 3 (few-shot): DOMAIN_PATTERNS.md provides one worked chain per domain
- Pattern 5 (NSP gate): JSON classification object required before any action

---

### 🚀 Deployment (`deployment/`)
**Status:** 📋 Initialized — topics outlined, patterns pending

---

## How to Use This Documentation

### For Current Work
1. Navigate to the relevant category folder
2. Check the `*_INDEX.md` file for navigation
3. Use `*_QUICK_REFERENCE.md` for fast lookups
4. Read `*_BEST_PRACTICES.md` for comprehensive guidance

### For Future Projects (WNBA/NFL/MLB)
1. Review all categories relevant to your project type
2. Copy templates from Quick Reference guides
3. Adapt patterns to sport-specific requirements
4. Document new lessons learned in the appropriate category

### Contributing New Best Practices
When you discover a new pattern or lesson:
1. Determine which category it belongs to
2. Add it to the comprehensive guide (`*_BEST_PRACTICES.md`)
3. Add a quick reference entry if it's commonly used
4. Update the index with cross-references
5. Document the context (what problem it solves, when to use it)

---

## Documentation Philosophy

### What Belongs Here
✅ Patterns that work across multiple projects
✅ Lessons learned from real mistakes
✅ Reusable templates and examples
✅ Decision frameworks (when to use X vs Y)
✅ Best practices backed by experience

### What Doesn't Belong Here
❌ Project-specific implementation details (use `docs/` instead)
❌ One-off fixes or hacks
❌ Unverified or experimental approaches
❌ External library documentation (link to it instead)

---

## Maintenance Guidelines

### Keeping Documentation Current
- Review and update quarterly (or after major incidents)
- Add new lessons as they're discovered
- Remove or archive outdated practices
- Update examples when code patterns change
- Verify all code examples still work

### Quality Standards
- **Concrete examples:** Every pattern includes working code
- **Context provided:** Explain why, not just what
- **Real failures:** Document actual bugs that happened
- **Actionable:** Readers should be able to implement immediately
- **Cross-referenced:** Link related patterns across categories

---

## Quick Links

- **API Best Practices:** [api/API_BEST_PRACTICES.md](api/API_BEST_PRACTICES.md)
- **API Quick Reference:** [api/API_QUICK_REFERENCE.md](api/API_QUICK_REFERENCE.md)
- **Prompt Engineering:** [ai/PROMPT_ENGINEERING_PATTERNS.md](ai/PROMPT_ENGINEERING_PATTERNS.md)
- **AI Prompting Guide:** [ai-prompting/AI_PROMPTING_BEST_PRACTICES.md](ai-prompting/AI_PROMPTING_BEST_PRACTICES.md)
- **Stat Confidence:** [data/STAT_CONFIDENCE_FRAMEWORK.md](data/STAT_CONFIDENCE_FRAMEWORK.md)
- **Debugging Playbook:** [debugging/README.md](debugging/README.md)
- **Ops Hub Fixes:** [ops-hub/KNOWN_FIXES.md](ops-hub/KNOWN_FIXES.md)
- **Ops Hub Patterns:** [ops-hub/DOMAIN_PATTERNS.md](ops-hub/DOMAIN_PATTERNS.md)
- **Skills Guide:** [ai/SKILLS_GUIDE.md](ai/SKILLS_GUIDE.md)
- **Project Documentation:** [../docs/](../docs/)
- **Architecture Guide:** [../docs/ARCHITECTURE.md](../docs/ARCHITECTURE.md)
- **Roadmap:** [../ROADMAP.md](../ROADMAP.md)

---

**Last Updated:** March 1, 2026 EST
**Categories Complete:** 8 (api, ai, ai-prompting, coding, data, data-modeling, debugging, ops-hub)
**Categories Initialized:** 2 (testing, deployment)
