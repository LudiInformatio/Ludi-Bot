# Future Data Sources Roadmap

**Discovered:** January 20, 2026
**Last Audited:** February 20, 2026 — End of Day
**Context:** Found during Module D (Yak) research in NBA Sense documentation (stats-prod.nba.com)

**Status:** ~80% implemented (as of Feb 19, 2026 7:39 PM EST). Section 4.2 dormant data fully activated. Section 4.4 endpoints wired. Section 5.2 trend/beneficiary/matchup patterns implemented in Phase 8.15 + calibration fixes. Phase 8.10 League Rankings DONE. Remaining: pipeline consolidation (4.3), DVP rankings, PlayerRebounding (1), Phase 8.11.

The following endpoints were discovered in the unofficial NBA Sense documentation and represent high-value opportunities for enhancing other Ludi-Bot modules.

---

## 1. Module E (Calibrator) Opportunities

### Synergy PlayType Data ✅ DONE
Granular efficiency data for specific play types. Crucial for matchup modeling.

*   **Endpoints:** `PlayerPlayTypePickAndRollBallHandler`, `PlayerPlayTypeIsolation`, `PlayerPlayTypePostup`, `PlayerPlayTypeSpotup`
*   **Status:** `player_synergy_playtypes` (1,326 records) synced and actively used in module_e.py (PPP efficiency, playtype matchup modifiers).

### SportVu Tracking ✅ MOSTLY DONE
Player tracking data for deeper behavioral analysis.

*   **PlayerDrives:** ✅ `player_drives` + `player_game_tracking` tables used in archetype classification and module_c drives data.
*   **PlayerTouches:** ✅ `player_touches` (505 records) now active in module_e.py `_apply_touches_context()` — quick decision-makers, paint presence, post-ups.
*   **PlayerSpeed:** ✅ `player_speed` (512 records) now active in module_e.py `_apply_speed_fatigue_context()` — guard hustle boosts, fatigue detection.
*   **PlayerRebounding:** ❌ NOT DONE — No table, no sync script. Still in ROADMAP as low-priority ("Sync PlayerRebounding tracking data — contested vs uncontested %).

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

### 4.2 Data Synced But NEVER Used (Quick Wins) ✅ RESOLVED

**All major dormant data sources are now active:**

| Table | Records | Synced | Used in Sims | Status |
|-------|---------|--------|--------------|--------|
| `player_shot_quality` | 499 | ✅ Daily | ✅ module_c (sq_mod FG%) + module_e (rim/corner freq) | DONE |
| `player_game_advanced` | 12,179 | ✅ Weekly | ✅ module_c (rolling 30d TS%) | DONE |
| `player_speed` | 512 | ✅ Weekly | ✅ module_e (guard hustle, fatigue) | DONE |
| `player_drives` | 512 | ✅ Weekly | ⚠️ Archetype only (drives loaded from player_game_tracking) | PARTIAL |
| `player_touches` | 505 | ✅ Weekly | ✅ module_e (touch context modifiers) | DONE |

### 4.3 Pipeline Redundancy (Efficiency Gains)

**Found duplicate/overlapping data fetches:**

| Issue | Scripts | Waste | Fix |
|-------|---------|-------|-----|
| Same endpoint 2x | `sync_pbp_totals.py` + `sync_pbp_shot_quality.py` | 1 API call/day | Keep one |
| WOWY 2x daily | In 2 workflows | 10+ calls/day | Consolidate |
| WOWY from 2 sources | `sync_wowy_hybrid.py` + `sync_pbp_wowy.py` | 20 min/day | Keep API |
| JSON anti-pattern | Module H → JSON → SQLite | 2-5 min/day | Direct SQLite |

### 4.4 Missing High-Value Endpoints ✅ PARTIALLY DONE

| Endpoint | Impact | Status |
|----------|--------|--------|
| `get_assist_combo_summary` | **CRITICAL** | ✅ `scripts/sync_assist_combos.py` wired in data_sync.yml |
| `get_four_factor_on_off` | HIGH | ✅ `scripts/sync_four_factor_wowy.py` wired in data_sync.yml |
| `get_possessions` | HIGH | ❌ Not done — clutch detection, blowout tax validation |
| `get_shot_query_summary` | MEDIUM | ❌ Not done — context-aware shot quality |
| `get_lineup_player_stats` | MEDIUM | ❌ Not done — lineup-specific projections |

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
| Pattern | Source | Status | Implementation |
|---------|--------|--------|---------------|
| Key Advantage callouts | BucketsToBucks | ❌ | Auto-identify #1 matchup advantage per game |
| Offense vs Defense matrix | BucketsToBucks | ❌ | Top 3 O-vs-D rankings per game |
| Injury beneficiary table | LandYourBets | ✅ Phase 8.15 | `get_beneficiary_context()` in `utils/trend_engine.py` |
| WOWY comparison table | StraightBettin | ✅ Phase 8.15 | `get_stagger_context()` in `utils/trend_engine.py` |
| Defensive funneling | StraightBettin | ❌ | Auto-surface OVER targets by weakness zone |
| Line movement tracking | Outlier.bet | ❌ | Evening mode: show how lines moved since morning |

**For Player Spotlights (8.3):**
| Pattern | Source | Status | Implementation |
|---------|--------|--------|---------------|
| Playtype Analysis table | PropsMadness | ✅ Feb 19 | `get_matchup_analysis()` in `trend_engine.py` — top 2 Synergy playtypes × opponent scheme in `analysis_block` |
| Similar Players comparison | PropsMadness | ❌ | Profile-similarity hit rate |
| Hit Rate badges | BucketsToBucks, Props.cash | ✅ Phase 8.15 | `hit_rate_l10` in `get_player_trends()` |
| Trend indicators | Multiple | ✅ Phase 8.15 | L7/L10/L15 + trend labels in `player_trends` table |
| DVP ranking | BucketsToBucks | ❌ | Defense vs Position rank (1-30) — `defender_matchups` table exists (0 rows), needs sync script |
| Matchup edge notes | LandYourBets | ✅ Feb 19 | `get_matchup_analysis()` — archetype-vs-scheme injected into every Spotlight `analysis_block` |
| On/Off per-36 stats | StraightBettin | ❌ | Full per-36 stat table with ON/OFF toggles |

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

---

## Phase 8.10: League Rankings Module ✅ DONE (Feb 19, 2026)

**Status:** Complete. `scripts/generate_rankings.py` ships weekly via `weekly_validation.yml`.
**Commit:** `dbe3a98` + min-games patch.

### Data Sources
| Table | Records | Used For |
|-------|---------|----------|
| `player_synergy_playtypes` | ~500 | PPP rankings by playtype |
| `team_scheme_cache` | 60 (30 teams × 2) | Defensive scheme rankings |
| `player_game_tracking` | ~12K | Drives, catch-shoot, pull-up rankings |

### Ranking Types
- **Player rankings:** Top P&R ball-handlers by PPP, top spot-up shooters by PPP, top ISO scorers by PPP
- **Team defensive rankings:** FUNNEL teams by drive FG% allowed, PAINT_PACK by 3PA allowed
- **Team offensive rankings:** MOTION teams by AST/FGM ratio, ISO_HEAVY by isolation frequency

### Implementation
- Weekly SQL queries via `scripts/generate_rankings.py` (new)
- Output: Markdown table via Telegram Tuesdays
- Cost: $0 (pure SQL, no API calls)

---

## Phase 8.11: Ludi Power Ratings ❌ NOT DONE

**Status:** Design phase. **NOTE:** `team_four_factors` table was never created. `team_leverage_profiles` exists as partial substitute (has pace/EFG/OREB by game state, but NOT Ortg/Drtg directly). Full team rankings require `pbp_stats_client.get_totals(entity_type="Team")` — deferred to Phase 8.10 implementation.

### Formula Concept
```
Power = 0.4 × Ortg + 0.3 × Drtg + 0.15 × PaceAdj + 0.15 × RecentForm
```

Where:
- **Ortg/Drg:** Needs `team_four_factors` (not yet created) or PBP Stats Team Totals
- **PaceAdj:** Pace deviation from league average (100 = neutral)
- **RecentForm:** 14d weighted win% with recency decay

### Advanced Extensions
- **Opponent Quality (SOS):** Strength-adjusted based on opponent power ratings
- **Margin of Victory Curves:** Weight wins by margin (close wins = 1.0, blowouts = 1.5)
- **Injury Adjusted:** Temporarily downgrade team rating when starters out

### Integration Points
- `morning_brief._score_game()` — add power rating differential as factor
- Future Ludi Lens dashboard — display team power bars
- Game selection — favor matchups with >5 point power differential

### Data Sources
- `team_four_factors` (ortg, drtg, pace)
- `team_leverage_profiles` (recent form)
- `player_injuries` (injury adjustments)

### Cost
- $0 (deterministic math, no API calls)

---

## 6. Phase 8.13 Research Findings — Ask Ludi Bot Architecture (Feb 20, 2026)

**Researched:** February 20, 2026 PM
**Sources:** 5 references — Medium articles on python-telegram-bot + Claude, GitHub repos (OpenClaw multi-channel adapter, telegram-claude-bot, ludi-lite), official docs
**Status:** Architecture finalized. Ready for implementation sprint.

### 6.1 Core Architecture Decision: Telegram Long Polling

**Why Telegram (not Slack) for the betting product:**
- Telegram is the existing channel for all betting product output (morning/evening cards)
- No webhook/public IP required — long polling works perfectly on the self-hosted Mac runner
- `python-telegram-bot` v21+ (async) is production-grade, widely documented

**3-File Implementation Plan:**

| File | Purpose |
|------|---------|
| `bots/ask_ludi.py` | Entry point — Application builder, `/start` handler, free-text dispatcher, long polling loop |
| `bots/ask_ludi_db.py` | Read-only DB layer — 8 intent handlers (injuries, edges, trends, standings, schedule, recap, free-text, fallback) |
| `bots/ask_ludi_handlers.py` | Intent classifier (Haiku → JSON) + DB fetch orchestration + Sonnet narrative → reply |
| `scripts/launchd/com.ludi.askludi.plist` | macOS launchd keepalive — `KeepAlive=true`, restart on crash |

**Key Design Principles:**
- **Read-only SQLite**: `sqlite3.connect("file:ludi.db?mode=ro", uri=True)` — WAL-safe, cannot corrupt pipeline writes even under concurrent access
- **Two-tier Claude routing**: Haiku for intent classification (<200ms, $0.0001/call, JSON output) → Python fetches DB rows → Sonnet for narrative (max_tokens=600, $0.003/call). No NBA facts from AI memory — all from DB.
- **Graceful degradation**: if Claude fails, return formatted DB data directly (no AI analysis, but data is still useful)
- **Rate limiting**: Per-user 10 req/minute cap prevents API cost explosion

### 6.2 Advanced Patterns for Future Sprints

**Tool Use / Function Calling (Phase 8.13-B):**
- Claude calls `get_injuries(team)`, `get_top_edges(n, min_edge)`, `get_player_trends(name, stat)` as tools
- Handles compound queries: "Who are the top UNDER plays for tonight with an injury angle?" → calls multiple tools → synthesizes
- Prevents hallucination: Claude can ONLY use provided tool results, cannot recall NBA facts
- Pattern: `client.messages.create(tools=[...], tool_choice={"type": "auto"})`

**Streaming Responses (Phase 8.13-C):**
- `client.messages.stream()` → `with client.messages.stream() as stream`
- Stream tokens → buffer → send when sentence complete (`.` or `?` delimiter)
- Perceived latency: 800ms first token vs 3-4s full response
- Telegram `bot.send_chat_action(TYPING)` while buffering

**Inline Keyboard Disambiguation:**
- User: "Tell me about the Lakers game" → multiple games found → bot sends `InlineKeyboardMarkup` with buttons
- User taps → `callback_query` fires → bot fetches specific game and responds
- Implementation: `ConversationHandler` with state machine for multi-turn

**Differential Context Injection:**
- Key principle: Only inject what Claude doesn't already know
- Don't send: raw DB schema, module internals, static config
- DO send: today's injury list, tonight's slate with lines, last 10 games for the asked player
- Pattern: build minimal context dict → serialize to compact JSON → inject into system prompt

### 6.3 Multi-Channel Adapter Pattern (OpenClaw-Inspired)

**The Pattern:** Decouple bot logic from channel implementation

```
ask_ludi_core.py          # Channel-agnostic: intent → DB → analysis
├── ask_ludi_telegram.py  # Telegram adapter (current)
├── ask_ludi_slack.py     # Slack adapter (future — vibestarters workspace)
└── ask_ludi_streamlit.py # Ludi Lens web app (future)
```

**Why this matters:** When Ludi Lens (web app) launches, the same `ask_ludi_core.py` handles queries. The Streamlit app just passes user input to core and displays the response — no duplicate logic.

**Current scope (8.13):** Build `ask_ludi_core.py` + `ask_ludi_telegram.py` only. Design with the adapter interface so Slack/Streamlit versions are plug-and-play.

### 6.4 MCP Servers for Ludi Lens (Future Phase)

**Relevance:** When Ludi Lens (Streamlit web app) launches, MCP servers expose `ludi.db` as a tool layer that Claude can call natively without custom Python glue.

**Pattern:** Instead of `select * from player_trends where player_id = ?` hardcoded in Python, Claude calls the MCP tool `query_trends(player_name, stat)` and the server handles the SQL.

**When to implement:** After Ludi Lens scaffold is complete. Not needed for Telegram bot phase.

### 6.5 Claude Ops / Cost Monitoring Patterns

**Weekly Cost Report:**
- `utils/api_monitor.py` already logs token usage to DB (via `monitor.log_claude_usage()`)
- Add `scripts/claude_cost_report.py`: query `claude_usage_log` → aggregate by model/task → compute weekly $ → send to Slack
- Rate table: Haiku=$0.0008/1k input + $0.004/1k output | Sonnet=$0.003 + $0.015

**Token Budget Guard:**
- `claude_client.py`: track daily token count in `cache/claude_daily_tokens.json`
- If projected daily spend > $2.00 → Slack alert, switch to Haiku fallback
- Reset at midnight EST

**`claude-ops-hub.yml` Upgrade:**
- Current: ad-hoc Sonnet call to diagnose failures
- Better: use `anthropics/claude-code-action@v1` with `CLAUDE_CODE_OAUTH_TOKEN` (the correct use case for that token)
- This gives Claude access to: workflow logs, repo context, PR diffs — much richer diagnosis

### 6.6 Auth Pattern Reference (Resolved Feb 20, 2026)

**For future sessions — correct auth priority in `utils/claude_client.py`:**

| Priority | Token | Use Case |
|----------|-------|---------|
| 1 | `ANTHROPIC_API_KEY` | All Python SDK calls (long-lived, works everywhere) |
| 2 | `~/.claude/config.json oauthToken` | Local dev only — skipped when `GITHUB_ACTIONS=true` |
| 3 | `CLAUDE_CODE_OAUTH_TOKEN` | Only for `anthropics/claude-code-action@v1` in workflows — NOT for SDK |

**Why this matters:** Self-hosted runner on local Mac has `~/.claude/config.json` with an OAuth token that expires every ~30 days. Priority 2 skip in CI prevents expired token from causing 401s. `CLAUDE_CODE_OAUTH_TOKEN` is a different OAuth flow meant for the GitHub Action tool, not the Python SDK.
