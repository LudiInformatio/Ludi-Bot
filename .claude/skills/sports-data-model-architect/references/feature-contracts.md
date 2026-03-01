# Feature Contracts

## Contract structure
For each feature set, specify:
- owner module/script
- source tables
- grain (player-game, team-game, player-day)
- as-of timestamp
- null handling rule
- refresh cadence

## Minimum quality bar
- Deterministic derivation from versioned inputs.
- Explicit fallback behavior when source unavailable.
- Coverage threshold documented (for example, >= 95% non-null on required features).

## Validation checks
- Row count parity against expected grain.
- Null-rate and distribution drift checks.
- Duplicate key checks at target grain.
- Temporal leakage checks against label timestamps.
