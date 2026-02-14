# API Usage Audit

**Last Updated:** February 14, 2026
**Purpose:** Document all API integrations — what we use, what's available, redundancy map, and cost analysis.

---

## 1. The-Odds-API

**Tier:** PAID ($30/mo, 20,000 credits/month)
**Docs:** https://the-odds-api.com/liveapi/guides/v4/

### Currently Used

| Endpoint | Module | Credits | Purpose |
|----------|--------|---------|---------|
| `GET /v4/sports/{sport}/odds` | Module A | 1/region | Game lines (spreads, totals, ML) |
| `GET /v4/sports/{sport}/events/{id}/odds` | Module A | 1/region | Player props per game |

### Available but Unused

| Endpoint | Credits | Potential Use |
|----------|---------|---------------|
| `GET /v4/sports/{sport}/scores` | 1 | Live scores for CLV capture timing |
| `GET /v4/historical/sports/{sport}/odds` | 10 | Historical odds for backtesting |
| `GET /v4/historical/sports/{sport}/events/{id}/odds` | 10 | Historical player props |

### Usage Pattern
- **Daily:** ~75 credits (3 games avg, props + lines)
- **Monthly:** ~2,250 credits (30 days)
- **Headroom:** 88.75% unused capacity
- **Credit cost:** 1 credit per bookmaker per request

### Recommendations
- **Forward CLV capture** (Phase 7.4): Use `/scores` to detect tipoff timing, then fetch closing lines 5 min before
- **Historical odds** for backtest validation: 10 credits each but could validate model vs market over 60+ days
- Consider dropping unused regions to reduce credit burn

---

## 2. Tank01 (RapidAPI)

**Tier:** PAID ($10/mo, 1,000 req/day)
**Docs:** https://rapidapi.com/tank01/api/tank01-fantasy-stats

### Currently Used

| Endpoint | Module | Purpose |
|----------|--------|---------|
| `getNBAInjuryList` | Module D | Official injury designations |
| `getNBABoxScore` | Module H | Game box scores (backfill) |
| `getNBATeamRoster` | Module H | Roster + player IDs |
| `getNBADepthCharts` | Depth Charts | Starter/bench classification |
| `getNBAPlayerInfo` | Module H | Player metadata |
| `getNBAGamesForDate` | Module H | Game schedule |

### Available but Unused

| Endpoint | Potential Use |
|----------|---------------|
| `getNBATeamSchedule` | B2B detection, schedule density |
| `getNBAStandings` | Playoff implications for load management |
| `getNBAPlayByPlay` | Clutch performance, shot distribution |
| `getNBAPlayerStatsByGameID` | Per-game stats (alternative to box score) |
| `getNBANews` | Supplementary injury intel |
| `getNBAOdds` | **Redundant** with The-Odds-API |

### Usage Pattern
- **Daily budget:** 200 req/day (self-imposed, 20% of limit)
- **Typical daily use:** ~50-80 requests
- **Backfill mode:** Can spike to 200/day during multi-day catch-up
- **Rate limiting:** Implemented in Module H with resume state

### Recommendations
- `getNBATeamSchedule` could improve B2B detection (currently uses games table)
- `getNBAPlayByPlay` is the richest untapped endpoint — shot-by-shot data for shot difficulty modeling
- ID format change (composite IDs) is handled by canonical ID system in `database.py`

---

## 3. PBP Stats

**Tier:** FREE (no rate limit documented, respect fair use)
**Docs:** https://pbpstats.readthedocs.io/

### Currently Used

| Endpoint | Module | Purpose |
|----------|--------|---------|
| `get_player_totals` | Shot Quality | Season shooting stats |
| `get_team_on_off` | WOWY | Lineup on/off data |
| `get_player_on_off_impact` | WOWY | Player +/- impact |

### Available but Unused

| Endpoint | Potential Use |
|----------|---------------|
| `get_game_stats(Type="Lineup")` | Specific lineup combos for WOWY |
| `get_team_leverage_summary` | Clutch/leverage performance |
| `get_shot_chart_data` | Shot location heat maps |
| `get_player_tracking` | Speed, distance, touches |

### Usage Pattern
- **Caching:** Local JSON cache with 19.4x speedup (implemented Phase 6.5c)
- **Retry:** 429 handling with exponential backoff
- **Timeouts:** 30s per request
- **Daily:** ~20-40 requests (most served from cache)

### Recommendations
- **Shot chart data** for archetype refinement (rim frequency, corner 3 tendency)
- **Leverage summary** for "Clutch Killers" tag in Module E
- **Lineup stats** could replace WOWY heuristics with direct lineup NetRtg data

---

## 4. Ball Don't Lie (BDL)

**Tier:** GOAT ($39.99/mo, 600 req/min)
**Docs:** https://docs.balldontlie.io/
**Client:** `utils/bdl_client.py`

### Currently Used

| Endpoint | Module | Purpose |
|----------|--------|---------|
| `/nba/v1/games` | Module A | Game lookup for props cross-reference |
| `/nba/v1/player_injuries` | Module D | Fallback injury source (when Tank01 fails) |
| `/nba/v2/odds/player_props` | Module A | Props validation/backup |

### Available (Implemented in Client)

| Endpoint | Version | Purpose |
|----------|---------|---------|
| `/nba/v1/players` | v1 | Player search and lookup |
| `/nba/v1/teams` | v1 | Team data |
| `/nba/v1/stats` | v1 | Box score stats |
| `/nba/v1/season_averages/{category}` | v1 | 8 categories: general, advanced, scoring, usage, per_36, per_48, opponent, defense |
| `/nba/v1/team_season_averages/{category}` | v1 | Team-level season averages |
| `/nba/v1/box_scores` | v1 | Full box scores by date |
| `/nba/v1/box_scores/live` | v1 | Live box scores |
| `/nba/v2/odds` | v2 | Game odds |
| `/nba/v2/stats/advanced` | v2 | Advanced player stats |

### BDL Labs (Assessment)

BDL offers a "Labs" product with 6+ years of historical data for backtesting:
- **Factors:** Shot quality, pace factors, offensive/defensive ratings
- **Access:** Requires separate Labs subscription
- **Recommendation:** Consider 1-week PRO trial to pull historical factor data into local cache for backtest enrichment
- **Not currently needed** — our PBP Stats + Tank01 historical data covers 2025-26 season adequately

### Labs-Inspired Tactics (Using GOAT Tier)

Even without Labs, we can build similar signals:
1. **Shot quality proxy:** Use `season_averages/scoring` for TS%, eFG% trends
2. **Pace factors:** Use `team_season_averages/general` for team pace data
3. **Usage trends:** Use `season_averages/usage` for USG%, AST% over time
4. **Defensive matchups:** Use `season_averages/opponent` for opponent-adjusted stats

### Usage Pattern
- **Rate limit:** 600 req/min (GOAT tier)
- **Caching:** File-based with configurable TTL (15 min for injuries, 24h for season averages)
- **Primary role:** Fallback/validation for Tank01 and The-Odds-API
- **Daily estimate:** ~30-50 requests (mostly cached)

---

## Redundancy Map

Shows which data points have multiple sources for reliability:

| Data Point | Primary Source | Fallback Source | Status |
|------------|---------------|-----------------|--------|
| Game lines (spread, total, ML) | The-Odds-API | BDL v2 Odds | Active |
| Player props | The-Odds-API | BDL v2 Props | Active |
| Injury list | Tank01 | BDL v1 Injuries | Active |
| Box scores | Tank01 | BDL v1 Box Scores | Available |
| Player stats | Tank01 | BDL v1 Stats | Available |
| Season averages | Tank01 | BDL v1 Season Averages | Available |
| Shot quality | PBP Stats | BDL Labs (future) | PBP Stats only |
| WOWY/Lineup data | PBP Stats | — | PBP Stats only |
| Referee data | NBA.com (scraping) | — | Single source |
| Depth charts | Tank01 | — | Single source |

---

## Cost Summary

| API | Monthly Cost | Monthly Limit | Typical Usage | Utilization |
|-----|-------------|---------------|---------------|-------------|
| The-Odds-API | $30.00 | 20,000 credits | ~2,250 credits | 11% |
| Tank01 | $10.00 | 30,000 req (1K/day) | ~2,000 req | 7% |
| PBP Stats | Free | Unlimited | ~600-1,200 req | N/A |
| Ball Don't Lie | $39.99 | 25,920,000 req (600/min) | ~1,000 req | <0.01% |
| **Total** | **$79.99/mo** | | | |

### Cost Optimization Notes
- BDL GOAT tier is massively over-provisioned — consider downgrading to Allstar ($14.99/mo, 60 req/min) if usage stays low
- The-Odds-API has 89% headroom — could add historical odds queries for backtest validation
- Tank01 is the tightest constraint at 200 req/day self-imposed budget

---

## Migration Path

### Current Architecture (Feb 2026)
```
Primary Pipeline:    The-Odds-API → Tank01 → PBP Stats → Ludi Engine
Fallback Layer:      BDL (injuries, props, box scores)
Scraping Layer:      NBA.com (referees, tracking data)
```

### Target Architecture (Post All-Star Break)
```
Primary Pipeline:    The-Odds-API → Tank01 → PBP Stats → Ludi Engine
Redundancy Layer:    BDL (auto-failover for any primary source failure)
CLV Layer:           The-Odds-API /scores + closing line capture
Scraping Layer:      NBA.com (referees only — tracking data via BDL)
```

### Key Migrations
1. **Forward CLV** (Phase 7.4): Add `/scores` endpoint to detect tipoff timing
2. **Tracking data**: Consider migrating NBA.com scraping to BDL `season_averages/advanced` to reduce scraping fragility
3. **Box score failover**: If Tank01 has an outage, BDL `box_scores` can fill the gap
4. **BDL tier review**: After 30 days of usage data, evaluate if Allstar tier ($14.99) is sufficient
