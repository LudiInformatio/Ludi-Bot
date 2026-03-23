# Technical Debt Register

**Last Updated:** March 23, 2026 — 5:24 PM EDT
**Owners:** Henrik (Code Auditor) + Junior Dev
**Review Cadence:** Every session where Henrik audits code — append new items, update existing

This register tracks known technical debt across the Ludi-Bot codebase. Each entry has a severity, location, and recommended fix. Items are logged when discovered during audits, backfill planning, or production incidents — not when they're fixed.

**When to add an entry:**
- Henrik discovers a code smell, silent failure pattern, or architectural inconsistency during `/ludi-audit`
- Junior dev encounters a workaround, hardcoded value, or TODO during implementation
- Any employee discovers a pattern that "works but shouldn't"

**When to remove an entry:**
- The fix is committed, pushed, and verified in production. Move to the Archive section with the commit hash.

---

## Severity Levels

| Level | Meaning | Action Timeline |
|-------|---------|-----------------|
| **P0** | Silent data corruption or pipeline breaker if triggered | Fix in current sprint |
| **P1** | Blocks a planned feature or degrades data quality | Fix before dependent work starts |
| **P2** | Code smell or maintenance burden, no immediate impact | Fix when touching the file |
| **P3** | Cosmetic or minor inefficiency | Fix opportunistically |

---

## Active Debt

### TD-001: Conflicting unique indexes on `player_game_logs`
- **Severity:** P0
- **Location:** `database.py` L298 vs `module_h_historian.py` L81-88
- **Description:** Two different UNIQUE constraints defined with the same index name (`idx_player_game_logs_unique`). `database.py` defines `UNIQUE(game_id, player_id)`. Module H's `_ensure_unique_index()` creates `UNIQUE(player_id, game_date)`. Whichever code ran last determines the live index. UPSERT behavior depends on which index exists.
- **Impact:** If the wrong index is live, UPSERT operations silently INSERT duplicates instead of updating existing rows. Affects any backfill or sync script targeting `player_game_logs`.
- **Recommended Fix:** Audit live DB index, pick one authoritative constraint (likely `player_id, game_date`), update both `database.py` and `module_h_historian.py` to match, remove the conflicting definition.
- **Discovered:** 2026-03-23 (Henrik, BDL backfill planning)
- **Blocked by:** Nothing — can fix immediately
- **Blocks:** BDL historical backfill (Phase 0 gate)

### TD-004: `get_stats()` single-page truncation
- **Severity:** P2
- **Location:** `utils/bdl_client.py` L216-229
- **Description:** `get_stats()` uses `_get()` (single-page fetch) instead of `_get_all_pages()`. With `per_page=100`, games with more than 100 player stat lines would silently truncate. NBA games have ~25-30 players, so this doesn't trigger in practice, but it's architecturally wrong.
- **Impact:** Low for current use. Would become P0 if `get_stats()` is used for multi-game or season-level queries.
- **Recommended Fix:** Change `get_stats()` to use `_get_all_pages()` and return a list, or add a `get_all_stats()` method that paginates.
- **Discovered:** 2026-03-23 (Henrik, BDL backfill planning)

### TD-005: Partial-date commits mask player-level failures
- **Severity:** P2
- **Location:** `scripts/sync_bdl_advanced_stats.py` L421-428
- **Description:** The backfill loop commits per-date even when `errors > 0`. If 20 players succeed and 5 fail, the date is marked "done" (has `bdl_source=1` rows) and won't be retried on next `--backfill` run. Failed players are permanently skipped.
- **Impact:** Systematic gaps in advanced stats for players whose API response had transient errors. No alerting or retry mechanism.
- **Recommended Fix:** Track error count per date. If errors > threshold (e.g., >20% of expected players), don't commit that date — let it retry next run.
- **Discovered:** 2026-03-23 (Henrik, BDL backfill planning)

### TD-006: `_detect_stats_format()` heuristic fragility
- **Severity:** P2
- **Location:** `scripts/sync_bdl_tracking.py` L99-122
- **Description:** Uses hard threshold (`sample > 50 and gp < 20`) to detect whether BDL returns per-game or totals format. For full 82-game seasons, the heuristic could misclassify and silently double all counting stats.
- **Impact:** Low for current-season (mid-season data has low GP). Could cause 2× inflated stats for full-season historical backfill of 2023-24.
- **Recommended Fix:** Test with known full-season data before bulk historical pull. Consider using BDL's explicit format indicator if available, or add a GP-based sanity cap.
- **Discovered:** 2026-03-23 (Henrik, BDL backfill planning)

### TD-007: No 429 retry/backoff in BDL client
- **Severity:** P3
- **Location:** `utils/bdl_client.py` L124-143
- **Description:** `_get()` logs 429 rate limit errors but returns empty `{}` to the caller. `_get_all_pages()` treats this as "no more data" and breaks pagination. No retry or exponential backoff. Current usage stays under limits (600 req/min), but bulk operations or concurrent workflows could trigger it.
- **Impact:** Low at current scale. Would silently return partial data during rate limit events.
- **Recommended Fix:** Add retry with exponential backoff (3 attempts, 2s/4s/8s delay) on 429 responses.
- **Discovered:** 2026-03-23 (Henrik, BDL backfill planning)

### TD-008: `_record_missing_canonical_id()` opens second DB connection in loop
- **Severity:** P2
- **Location:** `module_h_historian.py` L130-158
- **Description:** Called from inside the player processing loop. Opens its own `sqlite3.connect()` per call while the parent function already has an open connection. Under WAL mode this works, but under write contention (concurrent workflows), it's the same pattern that caused Issue #39's DB lock cascade.
- **Impact:** Latent — only triggers during concurrent writes. Was the root cause pattern for the weekly_validation timeout cascade.
- **Recommended Fix:** Batch staging writes outside the loop, or pass the existing connection through.
- **Discovered:** 2026-03-23 (Henrik, BDL backfill planning)

### TD-009: `sync_bdl_clutch_usage.py` missing `--season` flag
- **Severity:** P2
- **Location:** `scripts/sync_bdl_clutch_usage.py`
- **Description:** No `--season` argument. `BDL_SEASON = 2025` hardcoded. Cannot be used for historical backfill without code change.
- **Impact:** Blocks clutch usage backfill for 2023-24 and 2024-25.
- **Recommended Fix:** Add `--season` arg following the pattern in `sync_bdl_season_averages.py`.
- **Discovered:** 2026-03-23 (Henrik, BDL backfill planning)

### TD-010: 175+ hardcoded multipliers across Modules C/E/F/X
- **Severity:** P1
- **Location:** `module_c.py`, `module_e.py`, `module_f.py`, `module_x_scenario.py`
- **Description:** ~175 hardcoded multipliers for matchup modifiers, fatigue adjustments, blowout tax, etc. ~35% are heuristic guesses with no empirical validation. Empirical Modifiers Sprint 1 replaced starter/bench + stdev + WOWY, but matchup modifiers remain hardcoded.
- **Impact:** Model accuracy limited by unvalidated constants. Can't be replaced until archetype taxonomy stabilizes (~60 days post-fix).
- **Recommended Fix:** Sprint 2+ of Empirical Modifiers — data-driven matchup modifiers from `player_game_logs` + `team_scheme_cache`. Blocked on taxonomy stabilization.
- **Discovered:** 2026-03-21 (Henrik + Lena, Empirical Modifiers Sprint 1)
- **Blocked by:** Archetype taxonomy stabilization (TD-011)

### TD-011: 79.8% archetype drift between Module E and `players.archetype`
- **Severity:** P1
- **Location:** `module_e.py` (runtime classifier) vs `players` table (`archetype` column)
- **Description:** Module E classifies at runtime with different logic than the batch classifier (`classify_archetypes.py`). 79.8% of players get different archetypes depending on which path runs. Root cause: taxonomy split, not data bug. Spec complete (`memory/player_classification_architecture.md`).
- **Impact:** Bet recommendations use Module E's classification, but `players.archetype` (used by Ask Ludi, calibration queries) shows different labels. Inconsistent user-facing data.
- **Recommended Fix:** Module E = canonical classifier. `players.archetype` = nightly sync FROM Module E. Build `sync_archetype_to_players.py`. Full spec in memory file.
- **Discovered:** 2026-03-21 (Henrik + Lena + Maren, classification architecture review)
- **Blocked by:** Junior dev build time

---

## Archive (Fixed)

| ID | Description | Fixed In | Date |
|----|-------------|----------|------|
| TD-002 | `is_active=1` filter in `build_player_lookup()` | BDL backfill commit (Mar 23) | 2026-03-23 |
| TD-003 | `CURRENT_SEASON` hardcoded in tracking/clutch scripts | BDL backfill commit (Mar 23) | 2026-03-23 |

---

## Process

**Adding entries:**
1. Use the next available `TD-XXX` number
2. Fill all fields (severity, location, description, impact, fix, discovered)
3. Set `Blocked by` and `Blocks` if there are dependencies
4. Commit the update with the related work

**Resolving entries:**
1. Move the row to the Archive table with commit hash
2. Update `Last Updated` date
3. If the fix revealed new debt, log it as a new entry

**Review cadence:**
- Henrik reviews during every `/ludi-audit` — append new items found
- Junior dev appends when encountering workarounds during implementation
- Solomon reviews during `/session-debrief` — flag any P0/P1 items that need sprint priority
