# Architect: Audit

> **Agent**: Delegate this task to the **Lena** agent for statistical data quality analysis.

Run the sports data model audit pass — temporal integrity, feature coverage, and entity resolution. First step of the 3-phase workflow before design or implementation.

## Usage
- `/architect-audit`
- `/architect-audit focus on entity resolution drift in player_canonical_ids`

## Execution Contract
1. Activate the `sports-data-model-architect` skill
2. Run all 3 audit scripts in order:
   - `skills/sports-data-model-architect/scripts/audit_temporal_integrity.py`
   - `skills/sports-data-model-architect/scripts/audit_feature_coverage.py`
   - `skills/sports-data-model-architect/scripts/audit_entity_resolution.py`
3. Summarize findings grouped by severity: **critical → high → medium**
4. Stop here — do not propose changes. Use `/architect-design` for the next phase.

## Task
$ARGUMENTS
