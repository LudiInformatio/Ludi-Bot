# Architect: Implement

Generate migration-safe SQL/Python snippets with validation checks and rollback notes. Final phase of the 3-phase workflow — comes after `/architect-design`.

## Usage
- `/architect-implement`
- `/architect-implement generate the ALTER TABLE + backfill for the proposed schema changes`

## Execution Contract
1. Activate the `sports-data-model-architect` skill
2. Review proposed design (from `/architect-design` output or attached context)
3. Generate concise, migration-safe SQL/Python for each change
4. For each material change include:
   - Validation query or assertion to confirm the change applied correctly
   - Rollback/fallback note for any destructive or risky operation
5. End with a residual risk summary

## Task
$ARGUMENTS
