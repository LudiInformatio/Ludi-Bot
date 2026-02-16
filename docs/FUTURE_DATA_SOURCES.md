# Future Data Sources Roadmap

**Discovered:** January 20, 2026
**Last Audited:** February 14, 2026
**Context:** Found during Module D (Yak) research in NBA Sense documentation (stats-prod.nba.com)

**Status:** ~60% implemented. Remaining items folded into `ROADMAP.md` under "Dormant Data Activation", "Missing PBP Stats Endpoints", and "Data Pipeline Improvements". Section 5 added Feb 15 with competitive UI/UX research for Phase 8.

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

## 5. Competitive Landscape: Betting Analytics Sites (Feb 2026 Research)

**Discovered:** February 15, 2026
**Context:** UI/UX research for Phase 8 AI-Enhanced Pipeline — how competitors present game notes, player data, and bet narratives
**Design Doc:** `.claude/plans/crystalline-swimming-horizon.md`

### 5.1 Sites Reviewed

| Site | Focus | Free/Paid | Key Strength |
|------|-------|-----------|-------------|
| **PropsMadness** | Player prop analysis | Paywall ($20/mo) | Shooting zones, playtype analysis, similar players comparison |
| **LandYourBets** | Edge-based curation | Free tier + Premium | 4 edge categories, injury beneficiary tables, matchup notes |
| **BucketsToBucks** | Schedule + matchup tools | Free | Offense vs Defense matrices, DVP filtering, Key Advantage callouts |
| **Outlier.bet** | Multi-sportsbook tooling | Premium ($20-80/mo) | 2-click betting, positive EV feed, sharp book comparison |
| **Props.cash** | Mobile-first prop analysis | $20/mo | Correlated props, real-time injury intel, 200K+ users |
| **StraightBettin** | Research tools (On/Off, Funnels) | Free | WOWY comparison tables with +/- deltas, defensive funneling |

### 5.2 High-Value Patterns for Phase 8

**For Game Notes (8.2):**
| Pattern | Source | Implementation |
|---------|--------|---------------|
| Key Advantage callouts | BucketsToBucks | Auto-identify #1 matchup advantage per game (e.g., "Spot Up #3 off vs #29 def") |
| Offense vs Defense matrix | BucketsToBucks | Top 3 O-vs-D rankings per game: Paint, 3PT, Pace, Playtype |
| Injury beneficiary table | LandYourBets | Per OUT player: who benefits with Mins+, Pts+, Reb+, Ast+, Usg+ |
| WOWY comparison table | StraightBettin | Teammate stat deltas when key player is OFF (green=up, red=down) |
| Defensive funneling | StraightBettin | "Teams that ALLOW the most" — auto-surface OVER targets by weakness zone |
| Line movement tracking | Outlier.bet | Evening mode: show how lines moved since morning |

**For Player Spotlights (8.3):**
| Pattern | Source | Implementation |
|---------|--------|---------------|
| Playtype Analysis table | PropsMadness | Per-player: Isolation, PnR, Spot Up, Transition with PPP% and Opp Def Rank |
| Similar Players comparison | PropsMadness | "Players with similar profiles hit this line X% of the time" |
| Hit Rate badges | BucketsToBucks, Props.cash | L10 Hit Rate %, Season Hit Rate % — simple visual indicators |
| DVP ranking | BucketsToBucks | Defense vs Position rank (1-30) for the specific stat category |
| Matchup edge notes | LandYourBets | "Post Scorer — POR allows 1st most FGA to Post Scorers" |
| On/Off per-36 stats | StraightBettin | Full per-36 stat table with ON/OFF toggles per teammate |

**For Play Curation (8.5):**
| Pattern | Source | Implementation |
|---------|--------|---------------|
| Projection vs Line diff table | LandYourBets | Top 5 plays ranked by projection-line gap with direction |
| Edge type categorization | LandYourBets | Separate: Projection, Matchup, Injury/Vacuum, Hot/Cold Trend edges |
| Correlated props flagging | Props.cash | Flag when 2+ bets in same game are correlated (SGP risk) |
| DVP + Hit Rate filters | BucketsToBucks | Surface plays where DVP rank <= 5 AND L10 hit rate >= 70% |
| Funneling targets | StraightBettin | Auto-identify players who exploit specific defensive weakness zones |

### 5.3 Anti-Patterns to Avoid

| Anti-Pattern | Source | Lesson |
|-------------|--------|--------|
| Paywall basic data | PropsMadness | Our free Telegram tier should have real analytical insight |
| Data dump without curation | BucketsToBucks | Great data but no "so what?" — needs Claude reasoning layer |
| Generic marketing landing pages | Outlier/Props.cash | Our Telegram output IS the product, not a sales funnel |
| Too many filters for casual users | BucketsToBucks | Telegram needs pre-filtered top picks, not 4 filter dimensions |

### 5.4 StraightBettin On/Off Tool — Direct Parallel to Our WOWY System

**What they built:** Interactive On/Off tool showing per-36 stats for every NBA team with player toggle buttons.
- Click player name → see team stats when that player is ON court
- Click "OFF" → see team stats when that player is OFF court
- **COMPARISON table** appears showing +/- deltas per stat with color coding (green = better, red = worse, intensity = magnitude)
- Also has PROJECTION section with configurable minutes input

**Our equivalent:** `utils/wowy_calculator.py` + `team_lineups` table (10,669 records) + Module X Scenario Builder
**Gap:** We have the data but present it as internal pipeline math. StraightBettin makes it user-facing and interactive.
**Phase 8 action:** Use this pattern in 8.2 Game Notes (injury beneficiary deltas) and 8.3 Player Spotlights (WOWY context).

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
