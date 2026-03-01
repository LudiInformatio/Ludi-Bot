# Schema Blueprints

## Layering
- Raw layer: source-native payloads, minimal transformation.
- Canonical layer: resolved entities and stable keys.
- Feature layer: model-ready aggregates with as-of timestamps.
- Outcome layer: realized results, settlement, evaluation metrics.

## Preferred table roles
- Facts: event-like records (`player_game_logs`, odds snapshots, outcomes).
- Dimensions: slowly changing entities (players, teams, games, books).
- Bridges: many-to-many mappings (player aliases, external IDs).

## Key design rules
- Prefer surrogate keys for internal joins plus stored external IDs.
- Store source + ingest timestamp for traceability.
- Keep nullable fields explicit; do not overload sentinel values.

## Migration guidance
- Favor additive migrations (`ADD COLUMN`, new table, backfill).
- Avoid destructive operations in the same release as behavior changes.
- Add index changes with explicit validation query.
