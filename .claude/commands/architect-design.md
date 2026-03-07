# Architect: Design

> **Agent**: Delegate this task to the **Henrik** agent for design review against the ludi-audit checklist.

Propose minimal schema and contract changes based on audit findings. Second phase of the 3-phase workflow — comes after `/architect-audit`, before `/architect-implement`.

## Usage
- `/architect-design`
- `/architect-design propose additive-only changes for the temporal leakage finding`

## Execution Contract
1. Activate the `sports-data-model-architect` skill
2. Review previous audit findings (from `/architect-audit` output or attached context)
3. Propose **minimal, additive changes only** — prefer `ADD COLUMN`, new tables, backfills
4. Enforce as-of correctness — all proposals must preserve effective-date semantics
5. Output: sequenced change plan with rationale per item
6. Stop here — do not generate SQL/Python yet. Use `/architect-implement` for the next phase.

## Task
$ARGUMENTS
