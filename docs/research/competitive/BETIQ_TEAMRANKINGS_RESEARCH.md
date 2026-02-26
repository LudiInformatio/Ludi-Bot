# BetIQ / TeamRankings Research Sprint

**Date:** February 20, 2026
**Sessions:** 3 (Feb 20, 2026 AM)
**Purpose:** Competitive analysis of BetIQ's per-game dossier format and TeamRankings data layers to identify signals and features worth incorporating into Ludi-Bot.

---

## Sites Researched

| Site | URL Pattern | Access |
|------|-------------|--------|
| BetIQ (on TeamRankings) | `betiq.teamrankings.com/nba/matchups/{team1}-{team2}-{YYYY-MM-DD}/` | Public |
| TeamRankings main | `teamrankings.com` | Public (slow — heavy ads) |

---

## BetIQ Dossier Structure (14 Pages Per Game)

Every game has the same 14-tab structure:

| # | Tab | Key Data |
|---|-----|----------|
| 1 | Overview | Power ratings (20+ dims), off/def stat comparison |
| 2 | Injury Report | Standard injury list |
| 3 | Point Spread Analysis | ATS trend tables by situation |
| 4 | Over/Under Analysis | O/U trend tables by situation |
| 5 | Money Line Analysis | ML trend tables by situation |
| 6 | **Trends** | 22-row situational ATS/O/U/W-L tables |
| 7 | Simulation | Their model's projected score |
| 8 | Rosters & Stats | Standard box score averages |
| 9 | Offense vs. Defense | Head-to-head stat matchup grids |
| 10 | Offense vs. Offense | Offensive comparison |
| 11 | Stat Splits | Home/away/rest splits |
| 12 | Game Logs | Recent game history |
| 13 | Head to Head | H2H record |
| 14 | Common Opponents | Shared schedule analysis |

---

## Power Ratings Dimensions (Overview Tab)

BetIQ tracks 20+ dimensions per team — far more granular than most public tools:

| Dimension | What It Measures |
|-----------|-----------------|
| **Predictive** | Overall season rating (their primary model) |
| **L5 / L10** | Recent form (last 5 / last 10 games) |
| **Home / Away** | Venue-split ratings |
| **Home Advantage** | Neutral-venue adjusted home edge (eliminates travel bias) |
| **First Half / Second Half** | Period-specific performance rating |
| **SOS Past** | Strength of schedule already played |
| **SOS Future** | Remaining schedule difficulty |
| **SOS Season** | Full-season SOS |
| **SOS Basic** | Simple win% SOS |
| **SOS In-Div / Non-Div** | Division vs. non-division SOS |
| **Vs. Top 25%** | Performance vs. elite opponents |
| **Vs. Bottom 25%** | Performance vs. weak opponents |
| **Luck Rating** | Pythagorean luck adjustment |
| **Consistency Rating** | Game-to-game variance (lower # = more consistent) |
| **Division** | Division-only rating |
| **Non-Division** | Non-division rating |

### Key Findings From Live Data (CLE@CHA, Feb 20, 2026)

| Dimension | CLE | CHA |
|-----------|-----|-----|
| Predictive | #7 (3.3) | #19 (-3.3) |
| L10 | **#1 (14.6)** | #5 (8.3) |
| Home | #4 (7.6) | #12 (-0.5) |
| Home Advantage | #24 (-2.2) | **#29 (-6.0)** |
| First Half | #15 (0.1) | #10 (2.0) |
| **Second Half** | **#2 (4.1)** | #17 (-0.3) |
| Consistency | — | **#29 (16.3) most volatile** |

**Takeaways:**
- CLE is a 2H team (#2 in NBA) — Charlotte fades late
- CHA has near-zero home court advantage (-6.0 → #29) — don't credit CHA for "home game"
- CHA Consistency = #29 (most volatile team) — high variance suppresses confidence on any single CHA prop

---

## Situational Trend Tables (Betting Trends Tab)

### Format: 22-Row Table Per Team Per Metric (ATS / O/U / W-L)

| Row | Situation | Includes |
|-----|-----------|----------|
| All Games | Full season baseline | — |
| After Win / After Loss | Momentum | — |
| Home / Away | Venue | — |
| As Favorite / As Underdog | Market role | — |
| No Rest (B2B) | ≤1 day between games | True B2B |
| 1 Day Off | Standard rest | Most common |
| 2-3 Days Off | Extended rest | |
| 4+ Days Off | Coming off long break | |
| Rest Advantage | More rest than opponent | |
| Rest Disadvantage | Less rest than opponent | |
| Equal Rest | Same rest as opponent | |
| Division / Non-Division | Schedule type | |
| Conference / Non-Conference | Conference split | |

### Live Data: CLE @ CHA (Feb 20, 2026, CLE -6.5)

#### Charlotte (CHA) ATS — Key Rows

| Situation | ATS Record | Win% | Signal |
|-----------|-----------|------|--------|
| All Games | 33-23 | **59%** | Strong ATS team overall |
| After Win | 9-6 | 60% | Consistent |
| After Loss | 24-17 | 59% | Resilient cover team |
| Home | 12-14 | 46% | Fade at home ATS |
| Away | 21-9 | 70% | **Elite road ATS** |
| As Favorite | 8-7 | 53% | Neutral |
| **As Underdog** | **25-16** | **61%** | Key signal: CHA covers as dog |
| **No Rest (B2B)** | **9-2** | **82%** | Massive — B2B CHA covers |
| 1 Day Off | 11-9 | 55% | Slight lean |
| **2-3 Days Off** | 5-8 | **38%** | Trap: Well-rested CHA fades |
| 4+ Days Off | 8-4 | 67% | Strong long rest |

#### Charlotte (CHA) O/U — Key Rows

| Situation | O/U Record | OVER% | Signal |
|-----------|-----------|-------|--------|
| All Games | 23-33 | 41% | UNDER lean |
| **Home** | **8-19** | **30%** | Strong home UNDER |
| Away | 15-14 | 52% | Neutral away |

#### Cleveland (CLE) ATS — Key Rows

| Situation | ATS Record | Win% | Signal |
|-----------|-----------|------|--------|
| All Games | 27-29 | 48% | Chalk that doesn't cover |
| As Favorite | 17-27 | **39%** | Heavy fade signal |
| **2-3 Days Off** | **1-6** | **14%** | Massive fade: well-rested CLE fails ATS |
| No Rest (B2B) | 3-3 | 50% | Neutral |

### Live Data: DAL @ MIN (Feb 20, 2026, MIN -14.5)

#### Dallas (DAL) ATS — Key Rows

| Situation | ATS Record | Win% | Signal |
|-----------|-----------|------|--------|
| All Games | 23-31 | 43% | Poor ATS team |
| **No Rest (B2B)** | **7-2** | **78%** | B2B DAL covers |
| **2-3 Days Off** | **2-8** | **20%** | Well-rested DAL fails badly |
| As Underdog | 14-15 | 48% | Neutral |
| **Home Underdog** | **12-7** | **63%** | Strong |

#### Minnesota (MIN) O/U — Key Rows

| Situation | O/U Record | OVER% | Signal |
|-----------|-----------|-------|--------|
| **Home** | **10-19** | **34%** | Strong home UNDER |
| **Away** | **18-9** | **67%** | Strong away OVER |
| As Favorite | 18-19 | 49% | Neutral |
| **Home Favorite** | **11-14** | **44%** | MIN fails to cover at home as chalk |

---

## Cross-Game Patterns (Confirmed Across 3 Games)

### Pattern 1: B2B Teams Cover at Disproportionate Rates
- CHA on No Rest: **82% ATS** (9-2)
- DAL on No Rest: **78% ATS** (7-2)
- **Hypothesis:** Market over-penalizes B2B teams on the spread; actual fatigue impact is smaller than priced in
- **Ludi Action:** Reduce blowout tax / spread dampener for B2B teams specifically on ATS-driven context

### Pattern 2: 2-3 Days Rest = ATS Trap
- CLE on 2-3 days off: **14% ATS** (1-6) — worst bucket
- DAL on 2-3 days off: **20% ATS** (2-8)
- **Hypothesis:** Market rewards well-rested teams with favorable lines → creates negative EV when rest > 2 days
- **Ludi Action:** New rest-disadvantage flag: when opponent has 0-1 days rest AND our team has 2-3 days off → flag as "ATS trap" context

### Pattern 3: Home Teams Lean UNDER Strongly
- CHA at home: **30% OVER** (8-19)
- MIN at home: **34% OVER** (10-19)
- CLE at home: **40% OVER** (12-18)
- **Hypothesis:** Home games tend to be tighter, lower tempo, more defensive effort
- **Ludi Action:** Reinforce existing home UNDER lean (already have UNDER bias in scoring environment) — add home team flag to further dampen OVER projections

### Pattern 4: Heavy Favorites Fail ATS
- CLE as any favorite: **39% ATS** (17-27)
- MIN as home favorite: **44% ATS** (11-14, -14.5 is extreme)
- **Hypothesis:** Books set chalk lines that over-correct; props for star players on big favorites → usage drops in garbage time
- **Ludi Action:** Already have blowout tax. For heavy favorites (spread > 10), additionally flag individual player OVER props with a volume risk note.

### Pattern 5: Underdog Teams Cover Consistently
- CHA as underdog: **61% ATS** (25-16)
- DAL as home underdog: **63% ATS** (12-7)
- **Hypothesis:** Underdog spreads provide value; smaller-margin players on underdog teams may see unexpected volume
- **Ludi Action:** When our player is on the underdog team + archetype benefits from open court/higher usage → positive modifier

### Pattern 6: First Half vs. Second Half Team Identity
- CLE: #2 in 2H rating (4.1), #15 in 1H (0.1) — dominant closer
- CHA: #10 in 1H (2.0), #17 in 2H (-0.3) — fades late
- **Ludi Action:** H1/H2 rating split → apply to prop categories that skew to game flow (clutch stats, late-game volume)

---

## Feature Gap Analysis: BetIQ vs. Ludi-Bot

| BetIQ Feature | Ludi Has? | Priority | Notes |
|---------------|-----------|----------|-------|
| Situational ATS trends (B2B, rest, home/away) | Partial | **Tier 1** | Have B2B fatigue; need rest-bucket ATS rates |
| Home Advantage Rating (neutral-venue adj) | ❌ | **Tier 1** | Easy to compute from game logs |
| H1 vs H2 team rating | ❌ | **Tier 1** | Build from game logs quarter scores |
| Consistency Rating (team variance) | ❌ | **Tier 1** | Std dev of scores; directly impacts confidence |
| L5 / L10 form ratings | Partial | **Tier 1** | Have player trends; need team-level form |
| Rest splits (0/1/2-3/4+ days) | Partial | **Tier 1** | Have B2B flag; need full rest-bucket splits |
| O/U situational trends (home/rest/opponent) | Partial | **Tier 2** | Have scoring environment; not situational |
| ATS trend by situation (dog/fav/rest) | ❌ | **Tier 2** | Need team ATS table computation |
| Power rating (overall predictive) | ❌ | **Tier 2** | Phase 8.11 Ludi Power Ratings |
| SOS (past/future/season) | ❌ | **Tier 2** | Medium complexity; useful for projections |
| Underdog vs. favorite performer identification | ❌ | **Tier 2** | Tie to prop sizing logic |
| Head-to-head records | ❌ | **Tier 3** | Low predictive value short-term |
| Common opponents analysis | ❌ | **Tier 3** | Complex, marginal value |

---

## Implementation Roadmap

### Tier 1 — High Value, Buildable from Existing Data

**1A. Rest Split Context (days_rest bucketing)**
- Compute `days_since_last_game` from `player_game_logs` for each player
- Bucket into: B2B (0-1d) / Standard (2d) / Extended (3d) / Long Break (4+d)
- Add to `game_context` dict threaded to Module C + Module F
- ATS context note: flag 2-3 days rest as potential trap for heavy favorites

**1B. Home/Away UNDER Lean Amplification**
- Already have home UNDER lean from scoring environment
- Add explicit "home team" flag to further dampen OVER for home teams by stat category
- Data confirmed: 30-40% home OVER rate across 3 sampled teams

**1C. Consistency Rating (Team Variance Score)**
- Compute from `player_game_logs`: std dev of team scores over last 21 days
- High variance teams → reduce confidence tier (DIAMOND → BLUE CHIP for volatile teams)
- Example: CHA Consistency #29 → bump all CHA props down 1 tier

**1D. H1 vs H2 Team Rating**
- Compute from game logs if quarter scores available
- If not available: proxy via 3rd/4th quarter win rate from game log margins
- Use for: clutch props, late-game volume players on strong 2H teams

### Tier 2 — Valuable But Require New Data

**2A. ATS Situational Table (Team Level)**
- Build `team_ats_splits` table: compute from `games` table + `bet_recommendations`
- Columns: team, situation (home/away/b2b/rest/dog/fav), ats_wins, ats_losses
- Feed into Module F as context for prop sizing on related players

**2B. Ludi Power Ratings (Phase 8.11)**
- Blended ortg + drtg + pace + recent form
- Already on roadmap; BetIQ confirms the value

**2C. O/U Situational Trends (Team Level)**
- Compute from `games` table: home/away O/U hit rate per team per rest bucket
- Augments existing scoring environment with team-specific context

### Tier 3 — Low Priority

- H2H records: minimal predictive value in modern prop betting
- Common opponents: complex, marginal lift
- Travel analysis: deprioritized (user confirmed overkill for Ludi)

---

## NBA API / Data Sources for Implementation

All Tier 1 features can be built from existing `ludi.db` data:
- `player_game_logs` → rest buckets, quarter scores (if `q1/q2/q3/q4` columns exist)
- `games` → home/away spreads, totals, actual scores → ATS/O/U outcomes
- `rotation_profiles` → already tracks B2B minutes context
- `team_leverage_profiles` → already has clutch_factor, garbage_time_boost

No new API calls needed for Tier 1.

---

## Notes from `lbiedma` NBA Repos

**`nba-stats-analysis`** (Jupyter notebooks using `nba_api` wrapper):
- **FourFactorsAnalysis**: Dean Oliver's 4 factors via sklearn LinearRegression — EFG%, FTA_RATE, TM_TOV_PCT, OREB_PCT. Weights: Shooting 40%, TOV 25%, REB 20%, FT 15%. Useful as validation for Module E matchup modifiers.
- **PageRankNBA**: Win probability matrix → Power Method eigenvalue → PR scores. Blueprint for Phase 8.11 Ludi Power Ratings. The math is simple: build win-loss matrix, apply 0.85 damping factor, iterate until convergence.
- **OffensiveRatings**: Full Dean Oliver ORtg formula from box score only — `ORtg = 100 × PTSProd / TotPoss`. Could validate our Module C projections.
- **AvgPossessionsOverTime**: 20-season pace trend — confirms modern era (2022+) is peak pace. Aligns with our pace modifier logic.

**`gVegascp`**: CUDA/GPU Monte Carlo integration (academic) — not relevant to NBA props.

---

*This document captures all research from the Feb 20, 2026 competitive analysis sprint. See ROADMAP.md for implementation priority within Phase 8 roadmap.*
