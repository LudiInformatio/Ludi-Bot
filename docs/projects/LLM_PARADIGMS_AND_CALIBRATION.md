# Phase 9: Advanced LLM Paradigms & Model Calibration

**Created:** March 8, 2026
**Status:** Planned — not yet started
**Principle:** LLMs orchestrate, never calculate. ML learns constants OFFLINE; math stays deterministic at runtime.

---

## Vision

Expand Ludi-Bot's AI capabilities beyond the 9 BERT-derived prompt patterns into 7 additional paradigms (CoT, Many-Shot ICL, Prefilling, Self-Consistency, Debate, Reflexion, Confidence Scoring), while using offline ML to replace hardcoded simulation constants with data-learned values.

**Three pillars:**
1. **Prompt Engineering** — paradigms 10-16 in `best-practices/ai/PROMPT_ENGINEERING_PATTERNS.md`
2. **Math Calibration** — patterns in `best-practices/data/MODEL_CALIBRATION_PATTERNS.md`
3. **Employee Training** — paradigms in `best-practices/ai/EMPLOYEE_TRAINING_PARADIGMS.md`

**Research archive:** `docs/research/LLM_TRAINING_METHODOLOGIES_LANDSCAPE.md`, `docs/research/LLM_CANONICAL_RESEARCH_TABLE.md`

---

## Sprint Breakdown

### Sprint 1: Measurement Infrastructure (2 sessions)

**Goal:** Build calibration and residual analysis tools that every subsequent sprint depends on.

| Deliverable | Type | File |
|-------------|------|------|
| Brier Score + calibration curves + edge monotonicity + binomial significance | CREATE | `scripts/calibration_analysis.py` |
| Residual analysis by stat/archetype/scheme/context | CREATE | `scripts/residual_analysis.py` |
| Lena gets calibration vocabulary + DPO wrong-output example | MODIFY | `employees/lena/ONBOARDING.md` |

**Key schema notes:** `outcome='WIN'` (not `is_won`), `true_edge` (not `edge_pct`), `WHERE actual_result >= 0` (excludes -998/-999 sentinels).

**Outputs:** `cache/calibration_report.json`, `cache/residual_report.json`

---

### Sprint 2: Learned Constants (3 sessions)

**Goal:** Replace 3 highest-impact hardcoded constants with values learned OFFLINE from ludi.db.

| Deliverable | Type | File | Replaces |
|-------------|------|------|----------|
| Isotonic regression per stat category | CREATE | `scripts/learn_stat_calibration.py` | Static 19%/14% deflators in `module_f.py:1143-1172` |
| Per-stat variance coefficients | CREATE | `scripts/learn_stat_variance.py` | Uniform `SIM_VARIANCE=0.35` in `module_c.py:650` |
| WOWY-derived absorption rates | CREATE | `scripts/learn_absorption_rates.py` | 60%/30% hardcoded in `module_x_scenario.py:9-15` |
| Henrik gets learned-constant staleness check | MODIFY | `employees/henrik/ONBOARDING.md` | — |

**Integration pattern:** Script learns → writes `cache/*.json` with `generated_date` → pipeline reads at init → falls back to hardcoded defaults if cache missing.

---

### Sprint 3: Curation Prompt Engineering (2 sessions)

**Goal:** Apply 5 prompt paradigms to `curate_plays.py`.

| Deliverable | Type | File |
|-------------|------|------|
| Randomize bet order before Sonnet | MODIFY | `scripts/curate_plays.py` (~L400) |
| Response prefilling for JSON compliance | MODIFY | `utils/claude_client.py` + `scripts/curate_plays.py` |
| Many-Shot ICL from historical bets | MODIFY | `scripts/curate_plays.py` (new `_select_icl_examples()`) |
| Chain-of-Thought `"thinking"` field | MODIFY | `scripts/curate_plays.py` + `utils/claude_logger.py` |
| Post-generation bet_id verification | MODIFY | `scripts/curate_plays.py` |
| Constitutional AI self-checks for all employees | MODIFY | All 8 `employees/*/ONBOARDING.md` |

---

### Sprint 4: Knowledge Distillation + Reflexion (2 sessions)

**Goal:** Close feedback loops — system learns from its own mistakes.

| Deliverable | Type | File |
|-------------|------|------|
| Reflexion context (yesterday's mistakes) | MODIFY | `scripts/curate_plays.py` (new `_build_reflexion_context()`) |
| Haiku vs Sonnet disagreement analysis | CREATE | `scripts/calibrate_haiku_criteria.py` |
| Negative few-shot expansion to curation | MODIFY | `scripts/curate_plays.py` |
| Per-employee LESSONS_LEARNED.md | CREATE | `employees/{henrik,lena,silas}/LESSONS_LEARNED.md` |

**Prerequisite:** `claude_analysis_log.actual_outcome` backfill via `bet_recommendations` JOIN.

---

### Sprint 5: Advanced Patterns + Structural Hardening (2 sessions)

**Goal:** Debate pattern, confidence scoring, and employee coordination.

| Deliverable | Type | File |
|-------------|------|------|
| Maren debate skill (bull/bear for top 10 bets) | CREATE | `skills/maren-debate/SKILL.md` |
| Confidence scoring for all employees | MODIFY | All `employees/*/ONBOARDING.md` + `.claude/agents/*.md` |
| Employee Handoff Protocols | CREATE | `docs/projects/EMPLOYEE_HANDOFF_PROTOCOLS.md` |
| Temporal Correctness references | MODIFY | All `employees/*/ONBOARDING.md` |
| Many-Shot ICL galleries (5-8 real examples) | MODIFY | `employees/{henrik,lena,silas}/ONBOARDING.md` |

---

## Sprint Dependencies

```
Sprint 1 (Measurement) ──┬──> Sprint 2 (Learned Constants)
                         └──> Sprint 3 (Prompt Engineering) ──┬──> Sprint 4 (Distillation)
                                                              └──> Sprint 5 (Advanced)
```

Sprints 2 and 3 can run in parallel after Sprint 1. Sprints 4 and 5 can run in parallel after Sprint 3.

---

## Verification (End-to-End)

After all 5 sprints:
1. `scripts/calibration_analysis.py` shows Brier Score improvement vs pre-Phase 9 baseline
2. `main.py --limit-games 1 --verbose` runs cleanly with learned constants
3. Delete all `cache/*.json` → pipeline falls back to hardcoded defaults with no errors
4. `curate_plays.py --dry-run --verbose` shows randomized order, ICL examples, CoT thinking, prefilled JSON
5. All employee invocations show confidence levels and reference LESSONS_LEARNED.md

---

*Plan created March 8, 2026 — implementation begins after current Phase 8 sprint completes*
