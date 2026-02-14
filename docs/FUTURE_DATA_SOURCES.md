# Future Data Sources Roadmap

**Discovered:** January 20, 2026
**Last Audited:** February 14, 2026
**Context:** Found during Module D (Yak) research in NBA Sense documentation (stats-prod.nba.com)

**Status:** ~60% implemented. Remaining items folded into `ROADMAP.md` under "Dormant Data Activation", "Missing PBP Stats Endpoints", and "Data Pipeline Improvements". This document is now a reference — see ROADMAP.md for actionable tasks.

The following endpoints were discovered in the unofficial NBA Sense documentation and represent high-value opportunities for enhancing other Ludi-Bot modules.

---

## 1. Module E (Calibrator) Opportunities

### Synergy PlayType Data
Granular efficiency data for specific play types. Crucial for matchup modeling.

*   **Endpoints:**
    *   `PlayerPlayTypePickAndRollBallHandler`
    *   `PlayerPlayTypeIsolation`
    *   `PlayerPlayTypePostup`
    *   `PlayerPlayTypeSpotup`
*   **Use Case:**
    *   Adjust player projections based on defensive matchup efficiency (e.g., "Curry P&R vs Gobert drop coverage").
    *   Identify mismatch exploitations.

### SportVu Tracking
Player tracking data for deeper behavioral analysis.

*   **Endpoints:**
    *   `PlayerDrives`: Drives per game, FG% on drives, Pass% on drives.
    *   `PlayerTouches`: Time of possession, avg seconds per touch.
    *   `PlayerSpeed`: Avg speed, distance traveled (good for fatigue monitoring).
    *   `PlayerRebounding`: Contested vs Uncontested rebound %.
*   **Use Case:**
    *   Refine "Usage" metrics beyond simple USG%.
    *   Detect fatigue (slower speed + lower shot quality) for finding "Under" props.

---

## 2. Module X (Scenario Builder) Opportunities

### Expected Lineups
RotoWire's projected starting units.

*   **Source:** RotoWire API / stats-prod endpoint
*   **Use Case:**
    *   Automating the start of the scenario building process.
    *   Triggering "Bench Unit" scenarios when a starter is ruled out.

---

## 3. Module G (Ref Engine) Opportunities

### SportVu Defense
Defensive impact metrics.

*   **Endpoints:**
    *   `PlayerDefense`: FG% allowed at rim, < 6ft, > 15ft.
*   **Use Case:**
    *   Correlate referee tendencies with defensive aggression.
    *   Identify "Foul Prone" defenders in matchups with "Whistle Happy" refs.

---

---

## 4. PBP Stats API Optimization (Feb 2026 Discovery)

**Discovered:** February 3, 2026
**Context:** ULTRATHINK analysis of data_sync.yml workflow hangs and PBP Stats API documentation audit

### 4.1 Critical Infrastructure Fixes (Priority: URGENT)

**Problem:** Workflow hanging indefinitely on WOWY sync step (40% failure rate)

**Fixes Required:**
| Fix | File | Change |
|-----|------|--------|
| Job timeout | `data_sync.yml` | Add `timeout-minutes: 60` |
| Step timeouts | `data_sync.yml` | Add 5-30 min per step |
| API timeout | `pbp_stats_client.py` | Increase 60s → 120s |
| Rate limit handling | `pbp_stats_client.py` | Add 429 to retry list |
| Retry optimization | `pbp_stats_client.py` | `total=3, backoff_factor=2` |

### 4.2 Data Synced But NEVER Used (Quick Wins)

**Analysis found valuable data sitting unused in the database:**

| Table | Records | Synced | Used in Sims | Effort | Impact |
|-------|---------|--------|--------------|--------|--------|
| `player_shot_quality` | 499 | ✅ Daily | ❌ NEVER | 30 min | +1-2% RMSE |
| `player_game_advanced` | 12,179 | ✅ Weekly | ❌ NEVER | 1 hr | Rolling TS% |
| `player_speed` | 512 | ✅ Weekly | ❌ NEVER | 30 min | Guard context |
| `player_drives` | 512 | ✅ Weekly | ⚠️ Archetype only | 1 hr | Drives AST boost |
| `player_touches` | 505 | ✅ Weekly | ❌ NEVER | Future | Usage refinement |

**Integration Points:**
- **Module C**: Integrate `shot_quality_avg` for FG% simulation adjustment
- **Module E**: Add speed context for guards (+8% FTA, +5% AST)
- **Module E**: Use rolling 5-game TS% from `player_game_advanced`

### 4.3 Pipeline Redundancy (Efficiency Gains)

**Found duplicate/overlapping data fetches:**

| Issue | Scripts | Waste | Fix |
|-------|---------|-------|-----|
| Same endpoint 2x | `sync_pbp_totals.py` + `sync_pbp_shot_quality.py` | 1 API call/day | Keep one |
| WOWY 2x daily | In 2 workflows | 10+ calls/day | Consolidate |
| WOWY from 2 sources | `sync_wowy_hybrid.py` + `sync_pbp_wowy.py` | 20 min/day | Keep API |
| JSON anti-pattern | Module H → JSON → SQLite | 2-5 min/day | Direct SQLite |

### 4.4 Missing High-Value Endpoints

**PBP Stats endpoints that would unlock new capabilities:**

| Endpoint | Impact | Fixes |
|----------|--------|-------|
| `get_assist_combo_summary` | **CRITICAL** | Phase 6.2 BENEFICIARY (99.9% NULL) |
| `get_four_factor_on_off` | HIGH | Better WOWY (4 dimensions vs 1) |
| `get_possessions` | HIGH | Clutch detection, blowout tax validation |
| `get_shot_query_summary` | MEDIUM | Context-aware shot quality |
| `get_lineup_player_stats` | MEDIUM | Lineup-specific projections (Phase 7+) |

**Assist Combo Summary (Fixes BENEFICIARY):**
```python
# Returns passer→scorer assist combinations
# When star OUT, calculate who benefits:
star_assists = query_assist_combos(passer_id=star_id)
for teammate in teammates:
    teammate_share = teammate_assists_from_star / total_assists
    proj_pts *= (1 + 0.15 * teammate_share)  # BENEFICIARY boost
```

### 4.5 Performance Optimizations

**Local Response Caching:**
- Cache API responses for 24 hours
- Expected savings: 50-70% API calls
- Structure: `cache/pbp_stats/{endpoint}/{key}.json`

**Resume Capability:**
- Track sync state in `cache/pbp_wowy_state.json`
- Resume from last successful team after timeout
- Prevents losing progress on partial failures

### 4.6 Expected Results (When Implemented)

| Metric | Before | After |
|--------|--------|-------|
| Workflow failure rate | 40% | <5% |
| API calls/day | ~50 | ~15 |
| Sync time | 8-12 min | 3-5 min |
| Data utilization | ~40% | ~90% |
| BENEFICIARY NULL rate | 99.9% | <10% |
| Mean error (PTS) | +0.56 pts | +0.25 pts (est) |

### 4.7 Helper File Created

**File:** `utils/pbp_stats_api_reference.py` (500+ lines)

Contains all 40+ PBP Stats endpoints documented with:
- Function signatures and parameters
- Return types and data structure
- Integration priority ratings
- Search functionality for debugging

---

## Implementation Notes

*   **Auth:** Most of these appear to be accessible via the same `stats-prod.nba.com` endpoints used freely.
*   **Format:** JSON responses.
*   **Risk:** Undocumented APIs can change without warning. Always implement with fallbacks.

### PBP Stats API Notes
*   **API Docs:** https://api.pbpstats.com/docs
*   **Rate Limits:** Generous but recommend 120s timeout for WOWY queries
*   **Best Practice:** Cache responses locally with 24h TTL
*   **Helper:** `utils/pbp_stats_api_reference.py` for endpoint discovery
