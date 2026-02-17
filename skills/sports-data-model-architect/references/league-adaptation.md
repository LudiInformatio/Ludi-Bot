# League Adaptation (NBA -> WNBA/NFL)

## Portability principles
- Keep core modeling workflow invariant: audit -> design -> implement -> validate.
- Isolate league-specific vocab in mapping/config tables, not hardcoded logic.
- Separate schedule semantics (game frequency, roster size, injury reporting cadence).

## What should remain shared
- Entity resolution framework
- Temporal integrity checks
- Feature contract format
- Migration and rollback standards

## What should be league-specific
- Position taxonomy and roles
- Rest/fatigue priors
- Market types and settlement rules
- Data source reliability and latency assumptions
