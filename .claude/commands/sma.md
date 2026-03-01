# Sports Model Architect (Alias)

Run the `sports-data-model-architect` skill workflow.

## Usage
- `/sma <task>`
- Example: `/sma audit temporal integrity and feature coverage for the current pipeline`

## Execution Contract
1. Run the required audit-first pass:
   - `skills/sports-data-model-architect/scripts/audit_temporal_integrity.py`
   - `skills/sports-data-model-architect/scripts/audit_feature_coverage.py`
   - `skills/sports-data-model-architect/scripts/audit_entity_resolution.py`
2. Return findings in severity order: `critical` -> `high` -> `medium`
3. Provide minimal sequenced change plan
4. Provide migration-safe SQL/Python snippets when implementation is requested
5. End with validation checklist and residual risks

## Task
$ARGUMENTS
