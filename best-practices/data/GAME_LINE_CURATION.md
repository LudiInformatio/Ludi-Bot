# NBA Game Line Selection & Curation Best Practices

**Created:** February 25, 2026
**Source:** Multi-source research (Sports Insights, Action Network, OddsShopper, NBASstuffer,
           PMC academic ML studies, OddsShark referee data, BoydsBets)
**Purpose:** Inform `_score_game()` algorithm in `morning_brief.py` — what signals should
           drive game priority scoring and selection from the daily slate.

---

## Part 1: Sharp Bettor Game Selection Framework

### What Sharp Bettors Prioritize

Sharp bettors treat game selection like portfolio management — they bet **numbers, not teams**.

| Priority | Factor | Why It Matters |
|---|---|---|
| 1 | **Line Value (early entry)** | Lines softest 24-48 hrs after posting; sharps capture early inefficiency |
| 2 | **Situational Spots** | Rest differential, B2B, road trips — structural advantages not fully priced |
| 3 | **Sharp vs. Public Split** | Public inflates favorites and overs; fade public where divergence is large |
| 4 | **Steam Move Count** | Coordinated sharp-side moves across books = high-confidence signal |
| 5 | **Reverse Line Movement (RLM)** | Line moves opposite to public % = most reliable sharp-money signal |

Sharps hit ~55% overall; top professionals reach 60-65%. Breakeven at -110 is 52.4%.

---

### Steam Moves — What They Are and When to Use Them

A **steam move** is a sudden, simultaneous line shift across multiple sportsbooks within minutes.
It indicates coordinated sharp syndicate action.

**Detection logic:**
- Line moves from -2.5 to -4 in under 5 minutes across Pinnacle, Bet365, DraftKings simultaneously
- NOT triggered by a single large bet at one book — must be multi-book
- Bet Labs (Sports Insights) calls these "Bet Signals" — more signals = higher confidence

**Operationalization for `_score_game()` (requires Phase 8.22 odds_snapshots table):**
```python
# steam_flag = abs(current_spread - opening_spread) >= 1.5 AND move < 30 min
# score += 2.0 if steam_flag
```

---

### Reverse Line Movement (RLM) — The Strongest Single Signal

**Definition:** Public betting % is on Team A (≥65%), but the line moves to favor Team B.

**Threshold:**
- Public bet % ≥ 65% on one side AND line moves the other direction = strong RLM signal
- Bet% vs. Money% divergence: e.g., Team A has 86% of tickets but only 47% of money = sharps on Team B

**Line Freeze:** When a team gets 80%+ of tickets but the line does NOT move — book has liability on
the other side and is freezing intentionally. Equally actionable as RLM.

**Operationalization (requires public % data from Action Network or Sports Insights):**
```python
# rlm_signal = (public_bet_pct > 65) AND (line_moved_against_public)
# line_freeze = (public_bet_pct > 80) AND (abs(line_move) < 0.5)
# score += 2.5 if rlm_signal
# score += 1.5 if line_freeze
```

---

## Part 2: Rest Differential — Most Documented NBA Edge

### Quantified Rest Advantage

From analysis of 2,295+ NBA games over 10 years:

| Situation | ATS Impact |
|---|---|
| B2B teams (second night) | Lose **57% ATS** = prime fade signal |
| Teams with 2+ days rest vs B2B opponent | Win **57% ATS** |
| Road B2B performance decline | ~4.8% output reduction (confirmed in our Feb 2026 backtest) |
| Rest defense tightening | ~1.1 points better per game with 2 days rest |
| B2B frequency 2024-25 | 14.9 per team (down 23% from a decade ago) |

NBA players need 48-72 hrs to replenish glycogen stores after high-intensity play.
The physiological deficit compounds throughout game 2 of a B2B.

**Key gap in current system:** Our existing B2B tax in Module E/F adjusts **player projections**
but the game **selection layer** does not boost B2B-advantaged games as a selection priority.
Games where the opponent is on a B2B should score higher in `_score_game()`.

**Operationalization (data already in `ludi.db` game schedule):**
```python
away_days_rest = get_days_rest(conn, away_team, game_date)
home_days_rest = get_days_rest(conn, home_team, game_date)
if away_days_rest == 0 and home_days_rest >= 2:
    score += 2.0   # home team rested vs road B2B — most reliable NBA spot
elif home_days_rest == 0 and away_days_rest >= 2:
    score += 1.0   # road team exploiting home B2B (less reliable)
```

---

## Part 3: Game Total (Over/Under) Selection

### Factors That Favor Overs

| Factor | Signal |
|--------|--------|
| Fast-pace vs. fast-pace | Both teams pace > 100 possessions/game → +4-6 projected pts combined |
| "Whistle-heavy" referee crew | Crew avg fouls > league avg → more FTA = more points |
| Offensive-heavy schemes | Funnel/Perimeter defenses allow corner 3s freely |

### Factors That Favor Unders

| Factor | Signal |
|--------|--------|
| Slow-pace vs. slow-pace | Both teams pace < 96 → -4-6 projected pts |
| PAINT_PACK/BLITZ defensive crews | OKC, BOS, DET, MIN, SAS, ORL = lower scoring |
| "Tight" referee crew | Low fouls/game avg, fewer FTA, contested game |
| Public over bias (>70% of bets) | Classic sharp fade — market inflated |

### Referee Impact on Totals — Quantified

From OddsShark 2025-26 referee handicapping data:
- **Highest-total referee:** 227.8 pts/game average
- **Lowest-total referee:** 214.8 pts/game average
- **Range: 13 points difference** — highly material for totals betting
- Foul rate difference (high vs low): only 3.3 fouls/game (36.2 to 39.5 avg)

Our system tracks referee profiles (Module G) but ref total tendency is NOT yet a `_score_game()` signal.

**Operationalization (data in `referee_profiles` table):**
```python
ref_crew_avg = get_ref_crew_total(conn, home_team, game_date)  # lookup referee_profiles
if ref_crew_avg and game_total:
    divergence = abs(ref_crew_avg - game_total)
    if divergence >= 10:
        score += 1.5  # crew vs. market mismatch = significant totals edge
    elif divergence >= 6:
        score += 0.75
```

### Pace Matchup — Primary Total Driver

Pace (possessions per 48 min) is the **single best predictor** of combined game score.

**Projected total formula:**
```
projected_total = (avg_pace / 100) × (home_ortg + away_ortg) / 2 × 2
```

A matchup between two fast teams (~102 pace each) vs two slow teams (~95 pace) can differ
by **15-18 combined projected points** — often not fully reflected in the market total.

**Practical rule:** When two high-pace teams meet, totals trend over.
When two defensive/slow-pace teams meet, unders are reliable.

**Operationalization (requires `player_season_averages_bdl` team pace data):**
```python
home_pace = get_team_pace(conn, home_team)
away_pace = get_team_pace(conn, away_team)
avg_pace = (home_pace + away_pace) / 2
if avg_pace > 100 and game_total < 225:
    score += 1.0   # market under-pricing pace
elif avg_pace < 97 and game_total > 225:
    score += 1.0   # market over-pricing pace
```

---

## Part 4: ATS (Against the Spread) Signals

### NBA Key Numbers

NBA margin-of-victory distribution differs significantly from NFL:

| Range | Frequency | Note |
|---|---|---|
| **5-8 points** | Most common NBA margin | Key crossing range (more important than 3 or 7) |
| 1-2 points | Common — free throw sequences matter | |
| 3 points | Less critical than NFL (no field goals) | |

**Key NBA spread crossing points:** approximately +3, +5, +7, +10.
At -8 in the NBA, favored teams win outright **79%** of the time (vs 61.6% at -4).

**For `_score_game()`:**
```python
spread = abs(first.get('spread', 0))
if 7 <= spread <= 10:
    score += 0.5   # ATS edge zone — home dog pattern fires here
elif spread > 12:
    score -= 0.5   # blowout zone — prop volume risk + garbage time
```

### Home Underdog Pattern — Most Durable Sharp Signal

Home underdogs cover ATS at above-50% rates historically.

**Why it works:** Public bettors over-lay road favorites (narrative bias toward the "better" team).
Books consistently shade spreads to attract public money onto favorites.
**Home dogs at +3 to +7** are the sweet spot — genuine upset potential.

A game where the home team is the underdog by 3-10 points = prime ATS-value candidate
regardless of our prop model's output → should score higher in `_score_game()`.

**Operationalization:**
```python
home_underdog = first.get('spread', 0) > 0  # positive spread = home team is dog
if home_underdog and 3 <= spread <= 10:
    score += 0.5  # home dog flag
```

### Injury Impact on Spread Timing

When a star (20+ PPG or primary ball-handler) is ruled out:
- Efficient books adjust spread **2-6 points** within 30-60 minutes
- **Late scratch** (GTD → OUT within 2 hours of tip) = spread is stale = highest line inefficiency

**Operationalization (injury recency signal):**
```python
has_beneficiary = any('BENEFICIARY' in str(b.get('tags', '')) for b in bets)
if has_beneficiary:
    # Query player_injuries for snapshot_time recency
    # If snapshot_time < 3 hours: fresh vacuum = market hasn't fully adjusted
    score += 1.5  # (was +1.0 — under-weighted vs research backing)
```

---

## Part 5: Gap Analysis — Current `_score_game()` vs. Research

| Signal | Currently Implemented | Priority | Gap |
|--------|----------------------|----------|-----|
| Bet tier quality (DIAMOND/etc.) | ✅ — tier_weights dict | — | Solid foundation |
| Beneficiary/usage vacuum | ✅ — +1.0 for BENEFICIARY tag | — | Under-weighted; should be +1.5 |
| Injury keyword in news | ✅ — +1.5 for injury keywords | — | Refine by injury recency |
| Narrative keywords | ✅ — +0.5 for revenge/rivalry | — | Low signal; keep as-is |
| Rest differential | ❌ | **High** | 57% ATS win rate on B2B fades — data in ludi.db |
| Referee crew vs. market total | ❌ | **Medium** | 13pt range between best/worst officials |
| Spread size / blowout zone | Partial — `blowout_risk` string | **Medium** | Needs numeric scoring contribution |
| Home underdog flag | ❌ | Medium | Low-cost boolean to add |
| Pace matchup | ❌ | Medium | Requires `player_season_averages_bdl` query |
| Line movement / steam | ❌ | **Tier 2** | Requires Phase 8.22 odds_snapshots |
| RLM / public bet % | ❌ | **Tier 3** | Requires Action Network API integration |
| CLV feedback loop | ❌ | **Future** | Phase 8.23 Layer 2 — query claude_analysis_log CLV by game type |

---

## Part 6: Prioritized Implementation Roadmap for `_score_game()`

### Tier 1 — High Signal, Zero New Data Required

**A. Rest Differential Bonus** (data: `games` table schedule already in ludi.db)
```python
# Query: days since last game for each team from games table
# away_days_rest == 0 and home_days_rest >= 2: score += 2.0
# home_days_rest == 0 and away_days_rest >= 2: score += 1.0
```

**B. Injury Recency / Vacuum Freshness**
```python
# When BENEFICIARY bets exist AND injury_snapshot_time < 3 hours: score += 1.5 (was +1.0)
# Fresh vacuum = market lag opportunity; stale vacuum = books already adjusted
```

**C. Referee Crew Total Divergence** (data: `referee_profiles` already in ludi.db)
```python
# ref_crew_avg vs game_total; divergence >= 10: score += 1.5; divergence >= 6: score += 0.75
```

**D. Spread Zone Bonus/Penalty**
```python
# 7-10 point spread: score += 0.5 (ATS edge zone, home dog pattern)
# 12+ point spread: score -= 0.5 (blowout/prop volume risk)
```

### Tier 2 — Medium Signal, Requires `player_season_averages_bdl` Query

**E. Pace Mismatch Signal** (data in `player_season_averages_bdl` subtype='general')
```python
# avg_pace > 100 and game_total < 225: score += 1.0 (market under-pricing pace)
# avg_pace < 97 and game_total > 225: score += 1.0 (market over-pricing pace)
```

### Tier 3 — Requires Phase 8.22 Odds Snapshots (Future)

**F. Line Movement / Steam Signal**
```python
# abs(current_spread - opening_spread) >= 1.5: score += 1.5
```

**G. RLM / Public Bet % (Requires Action Network API)**
```python
# public_pct > 65% AND line moved against public: score += 2.5
# public_pct > 80% AND abs(line_move) < 0.5: score += 1.5 (line freeze)
```

### Tier 4 — Phase 8.23 Layer 2 CLV Feedback (Future)

**H. Historical CLV by Game Type**
- Query `bet_recommendations + claude_analysis_log` for CLV by B2B games, injury-vacuum games, home-dog games
- Weight `_score_game()` toward game types with CLV > 0 over 90+ day window

---

## Part 7: AI/Algorithmic Game Selection — Industry Reference

### Bet Labs (Sports Insights) Methodology

Four-condition gold standard stack (when all four align = highest-confidence selection):
1. **Multiple Bet Signals** — sharp-triggered line moves per game
2. **Bet % vs. Money % divergence** — institutional money vs. public tickets
3. **Bet Labs system match** — historical pattern with documented win rate
4. **Favorable historical trend** — team/spot combo has empirical edge

### Academic ML Model Best Inputs (2024-25 Research)

From PMC/Nature peer-reviewed NBA prediction studies:
- **Offensive/defensive efficiency** (per-100 possessions, adjusted) — highest-weight feature
- **Rolling form window** — L10, L20, L30 rolling averages
- **Home/away splits** — separate treatment required
- **Pace factors** — most predictive single feature for totals
- **Rest/schedule factors** — B2B, days rest differential
- **Shooting percentages** (eFG%, TS%) — recent form vs season

Best ML models achieve ~0.87 accuracy on binary outcomes — but the edge comes from **game selection**
(selecting only games where model confidence exceeds a threshold), not just prediction quality.

### CLV as Game Selection Feedback Loop

Closing lines (Pinnacle) predict game outcomes better than opening lines.
- CLV > 0 on >55% of bets in a **category of games** = that category has confirmed market edge
- Use `bet_recommendations` CLV history to identify which game-type categories the model wins on
- This feedback loop (Phase 8.23 Layer 2) would automatically tune `_score_game()` weights toward
  historically high-CLV categories

---

## Related Files

- `morning_brief.py` — `_score_game()` function (game priority algorithm)
- `module_e.py` — Module E `USE_TEAM_TOTALS_MODIFIER` (total-adjusted projections)
- `module_g.py` — Referee pace impact, `referee_profiles` table
- `utils/blowout_tax.py` — Existing blowout probability by spread/context
- `best-practices/data/DVP_AND_SCHEME_METHODOLOGY.md` — DVP signal rules
- `docs/METHODOLOGY.md` — CLV tracking, Kelly sizing, devigging
