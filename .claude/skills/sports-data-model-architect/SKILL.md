---
name: sports-data-model-architect
description: Design, audit, and evolve sports analytics data models with a balanced audit-first workflow plus implementation support. Use when working on schema design, SQL queries, migrations, feature pipelines, entity resolution, temporal joins, backtest dataset quality, or model-readiness checks for NBA analytics (and league-portable patterns for future WNBA/NFL use).
---

# Sports Data Model Architect

## Overview
Use this skill to run a balanced workflow: audit current data quality and temporal correctness first, then implement schema/feature improvements with migration-safe SQL and Python.

## Workflow

### 1) Scope and constraints
- Confirm business goal: analytics question, model target, or pipeline reliability objective.
- Identify affected layers: raw ingest, canonical entities, feature store, model/backtest outputs.
- Confirm DB path and execution context before proposing changes.

### 2) Audit pass (required)
- Run deterministic checks first:
  - `scripts/audit_temporal_integrity.py`
  - `scripts/audit_feature_coverage.py`
  - `scripts/audit_entity_resolution.py`
- Summarize findings by severity:
  - `critical`: leakage/corruption/blocking defects
  - `high`: high-confidence model-risk defects
  - `medium`: quality drift/coverage gaps

### 3) Design pass
- Propose minimal schema and contract changes to address highest-severity findings.
- Enforce as-of correctness:
  - no future leakage
  - valid effective dating
  - stable entity keys
- Prefer additive changes over destructive rewrites.

### 4) Implementation pass
- Generate concise migration-safe SQL/Python snippets.
- Add validation queries or tests for each material change.
- Include rollback or fallback notes for risky data operations.

### 5) Delivery format
Return results in this order:
1. Audit findings (`critical` -> `high` -> `medium`)
2. Recommended change plan (minimal, sequenced)
3. SQL/Python snippets for implementation
4. Validation checklist and residual risks

## Standards
- Use database and API truth for roster/team assignments; do not infer from model memory.
- Protect temporal integrity on every join and feature derivation.
- Preserve reproducibility: explicit filters, clear as-of windows, deterministic transforms.
- Document assumptions when source tables are missing or stale.

## References
- Temporal rules: `references/temporal-integrity.md`
- Schema patterns: `references/schema-blueprints.md`
- Feature contracts: `references/feature-contracts.md`
- League portability notes: `references/league-adaptation.md`

## Scripts
- `scripts/audit_temporal_integrity.py`: temporal leakage and chronology checks
- `scripts/audit_feature_coverage.py`: key-table and null-coverage checks
- `scripts/audit_entity_resolution.py`: canonical/entity consistency checks
