# Technical Debt Register

**Last Updated:** March 24, 2026 (Sprint 3 — TD-017/018/019/020 added)
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

### TD-015: `players.depth_chart_position` column missing
- **Severity:** P2
- **Location:** `scripts/compute_empirical_modifiers.py` L286-297, `players` table
- **Description:** Script queries `players.depth_chart_position` but the column doesn't exist (only `position`). Soft-fail: returns NULL depth_slot. The depth_slot feature was specced but the column was never added to the `players` table.
- **Impact:** All `player_empirical_modifiers.depth_slot` values are NULL. Low impact — depth_slot is informational only, not consumed by Module C/F.
- **Recommended Fix:** Either add `depth_chart_position` column to `players` (populated from Tank01 depth charts), or modify the query to derive from `team_lineups` data.
- **Discovered:** 2026-03-24 (Sprint 0 execution)

### TD-016: `compute_empirical_modifiers.py` never tested against live schema
- **Severity:** P1
- **Location:** Best practice gap
- **Description:** The Empirical Modifiers Sprint 1 shipped March 21 with Henrik APPROVED, but the script was never run against `ludi.db` before commit. Three column name mismatches (`season`, `min`, `is_starter`) went undetected because the schema check was done against the spec, not the live DB. The GH Actions workflow ran nightly for 3 days with 0 output and no alert (until ops-hub was wired).
- **Impact:** Best practice: all data scripts must pass a `--dry-run` against live DB before shipping.
- **Recommended Fix:** Add to Henrik's audit checklist: "Run `--dry-run` against live DB for any new data script before APPROVED."
- **Discovered:** 2026-03-24

### TD-013: `player_projections.player_id` is unfirewalled
- **Severity:** P3
- **Location:** `utils/projection_logger.py` L86
- **Description:** `player_id` is written to `player_projections` table without passing through `resolve_player_id_for_insert()`. Analytics table only — not joined to `player_canonical_ids` or `players` — so no canonical contamination risk.
- **Impact:** Cosmetic. Dirty IDs can accumulate in the projections table but do not affect pipeline outputs.
- **Recommended Fix:** None required. If future analytics JOINs are added, wire the firewall at insert time.
- **Discovered:** 2026-03-23 (Henrik, projection tracking audit)

### TD-017: `module_x_scenario.py` secondary DB connections missing `busy_timeout`
- **Severity:** P2
- **Location:** `module_x_scenario.py` L709, L743, L810, L921, L963
- **Description:** Five `sqlite3.connect(DB_PATH)` calls inside scenario-building methods have no `timeout` argument and no `PRAGMA busy_timeout`. Under concurrent pipeline runs, these will fail immediately on the default 5s SQLite lock timeout.
- **Impact:** Silent scenario-building failures during concurrent DB writes.
- **Recommended Fix:** Add `timeout=30` + `PRAGMA busy_timeout = 5000` to each connect call.
- **Discovered:** 2026-03-24 (Henrik, Sprint 3 audit)

### TD-018: Pace double-application — Module C game pace × Module E leverage pace
- **Severity:** P2
- **Location:** `module_c.py` L415-416, `module_e.py` `_apply_leverage_context()`
- **Description:** Module C applies `scenario_pace * ref_pace` to all volume stats. Module E `_apply_leverage_context()` subsequently applies a second pace ratio (up to ±5%) from historical team `l_pace`/`vh_pace` vs `overall_pace`. On blowout games with a low-pace team, combined effect can reach `0.97 × 0.95 = 0.922`.
- **Impact:** Unclear until modifier ablation baseline is established. Inputs are different (external game market vs team historical split) — may be intentional.
- **Recommended Fix:** Evaluate after WS2 ablation baseline. Disable via `MODIFIER_FLAGS['leverage_context']` if ablation shows negative lift.
- **Discovered:** 2026-03-24 (Henrik, Sprint 3 audit)

### TD-020: `player_projections.actual_result` missing — ablation blocker
- **Severity:** P1
- **Location:** `player_projections` table, `scripts/run_modifier_ablation.py` L48-54
- **Description:** `run_modifier_ablation.py` expects an `actual_result` column in `player_projections`. Column does not exist. Script detects the absence at runtime (L53-54) and returns empty list — no exception raised, no error surfaced. Correct fix is Option A: add a `_settle_actual_results()` function that JOINs `player_projections` → `player_game_logs` on `(player_id, game_date)` and maps `stat_category` strings (`'pts'`, `'reb'`, `'ast'`, etc.) to the corresponding `player_game_logs` columns. No schema change to `player_projections` needed.
- **Impact:** WS2 (modifier ablation baseline) is fully blocked. 0 rows returned, 0 RMSE computed, no ablation output. Modifier flags cannot be evaluated until fixed.
- **Recommended Fix:** Option A — see `plans/agent-chain-of-command.md` Decision 1 spec. Add `_settle_actual_results(conn, min_date, stat_cat)` to `run_modifier_ablation.py` that does: `SELECT pp.id, pgl.[stat_col] FROM player_projections pp JOIN player_game_logs pgl ON pp.player_id = pgl.player_id AND pp.game_date = pgl.game_date WHERE pp.stat_category = ?`, then bulk-UPDATEs `actual_result`. Add `--settle` CLI flag.
- **Discovered:** 2026-03-24 (Henrik, Sprint 3 Decision 1 review)

### TD-019: Calibration curve is not grade-stratified
- **Severity:** P2
- **Location:** `scripts/calibrate_model_probabilities.py` (new Sprint 3 file)
- **Description:** Single calibration curve across all grades obscures grade-level inversion signal (FADE WR > LEAN WR > STRONG WR). v1 is a Brier score improvement but true calibration requires per-grade curves.
- **Impact:** Miscalibrated probability estimates per grade.
- **Recommended Fix:** v2 per-grade isotonic curves — Sprint 4.
- **Discovered:** 2026-03-24 (Henrik, Sprint 3 audit)

### TD-021: `player_game_hustle` not consumed by Module B — hustle stats absent from trend layer
- **Severity:** P2
- **Location:** `module_b.py` (missing hustle table load), `player_game_hustle` table (68,040 rows)
- **Description:** Module B does not load `player_game_hustle`. Deflections, contested shots, and charges data from 2 seasons of BDL backfill are available but never reach the trend/streak layer. Module E consumes hustle stats for archetype classification only.
- **Impact:** Hustle metrics (a strong indicator of defensive impact and motor) are not factored into L5/L10/L15 trend calculations or HOT_STREAK detection.
- **Recommended Fix:** Add `_load_hustle_trends()` to Module B — compute L10 deflections + contested shots per player, expose as `hustle_l10` and `hustle_trend` in the player dict for Module E consumption.
- **Discovered:** 2026-03-24 (Lena, data flow audit)

---

### TD-022: `TIER_UNITS` dict re-instantiated on every inner loop iteration in `module_f.py`
- **Severity:** P2
- **Location:** `module_f.py` lines 534–539, inside per-player × per-prop inner loop
- **Description:** `TIER_UNITS = {'DIAMOND': 1.25, 'BLUE CHIP': 1.00, ...}` is a constant dict reconstructed from scratch on every simulation output iteration. With 10+ players × 3–5 props each per slate, this runs 30–50+ times per pipeline invocation for no benefit.
- **Impact:** Negligible runtime penalty at current slate sizes, but a clean-code violation that compounds if slate volume grows.
- **Recommended Fix:** Hoist `TIER_UNITS` to module-level constant (alongside `_STAT_RMSE`, `_STAT_EDGE_CALIBRATION`). One-line change.
- **Discovered:** 2026-03-24 (Henrik, Sprint 4-A audit)

---

## Archive (Fixed)

| ID | Description | Fixed In | Date |
|----|-------------|----------|------|
| TD-002 | `is_active=1` filter in `build_player_lookup()` | BDL backfill commit (Mar 23) | 2026-03-23 |
| TD-003 | `CURRENT_SEASON` hardcoded in tracking/clutch scripts | BDL backfill commit (Mar 23) | 2026-03-23 |
| TD-009 | `sync_bdl_clutch_usage.py` missing `--season` flag | BDL backfill commit (Mar 23) | 2026-03-23 |
| TD-012 | `main.py` projection_logger uses `print()` not `logging.warning()` | This commit (Mar 23) | 2026-03-23 |
| TD-001 | Conflicting unique indexes on `player_game_logs` | `database.py` index aligned (`93d84d7`, Mar 23) | 2026-03-23 |
| TD-014 | `compute_empirical_modifiers.py` 3 column name mismatches | `aec6909` (Mar 24) | 2026-03-24 |

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
