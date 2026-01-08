# Ludi Informatio: Project History & Strategic Evolution

**Document Created:** January 5, 2026
**Purpose:** Comprehensive historical context documenting the origins, evolution, and strategic decisions that shaped the Ludi Informatio platform.
**Source:** Gemini AI Studio & ChatGPT conversations from Summer 2025 - January 2026

---

## Table of Contents

1. [Project Origins](#1-project-origins)
2. [The S.A.V.A.G.E. Engine](#2-the-savage-engine)
3. [Brand Hierarchy & Naming](#3-brand-hierarchy--naming)
4. [Mathematical Foundation](#4-mathematical-foundation)
5. [Play Classification System](#5-play-classification-system)
6. [Archetype Definitions](#6-archetype-definitions)
7. [Strategic Market Focus](#7-strategic-market-focus)
8. [Data Sources & Integration](#8-data-sources--integration)
9. [Front Office Terminology](#9-front-office-terminology)
10. [Pro Standards & Validation](#10-pro-standards--validation)
11. [Future Expansion Roadmap](#11-future-expansion-roadmap)
12. [Lessons Learned](#12-lessons-learned)

---

## 1. Project Origins

### The Genesis (Summer 2025)

The Ludi Informatio project began as a **WNBA betting model** built in ChatGPT during Summer 2025. The original goal was to create a systematic approach to sports betting that went beyond gut feelings and "picks."

**Key Quote from Original Conversations:**
> "When I started building out my WNBA model in ChatGPT over the summer and then I started talking about building it out with ChatGPT, the other support starting with the NFL and the NBA. I then pivoted it over and called it my Savage model."

### The Pivot to "Savage Model"

The project quickly expanded from WNBA to include:
- **NFL** - Football props and spreads
- **NBA** - The primary focus that eventually dominated

The name "Savage Model" reflected the aggressive, edge-hunting mentality of the approach.

### Evolution to "Ludi Informatio"

As the project matured, the need for a more professional brand became apparent:
- "Savage" sounded too aggressive or "degen" for a premium product
- The pivot to an "Executive/Front Office" aesthetic required elevated naming
- "Ludi Informatio" (Latin for "Games Information") provided prestige while maintaining substance

---

## 2. The S.A.V.A.G.E. Engine

### The Backronym Solution

Rather than abandoning the original "Savage" name entirely, it was retrofitted into a professional acronym:

**S.A.V.A.G.E. = Scenario Analysis & Value Assessment Game Engine**

| Letter | Meaning | Description |
|--------|---------|-------------|
| **S** | Scenario | Dynamic roster/injury scenarios (Module X) |
| **A** | Analysis | Data processing and matchup evaluation |
| **V** | Value | Edge detection and EV calculation |
| **A** | Assessment | Confidence grading and risk evaluation |
| **G** | Game | Sport-specific modeling (NBA/NFL/WNBA) |
| **E** | Engine | The Poisson simulation core |

### Why This Works

1. **Personal History Preserved**: The founder can say "The Savage Model" on podcasts
2. **Professional Face**: On the website, it appears as "Powered by the S.A.V.A.G.E. Engine"
3. **Technical Credibility**: Sounds like a military/defense contractor system name
4. **Talking Point**: "We run it through the Savage Engine..." creates intrigue

---

## 3. Brand Hierarchy & Naming

### The Corporate Structure

```
LUDI INFORMATIO (Parent Company)
│
├── LUDI LENS (Product/Dashboard)
│   └── Powered by: S.A.V.A.G.E. Protocol
│
├── Triple Zero Podcast
│   └── Sports Business/Marketing Focus
│   └── "Powered by Ludi Informatio"
│
├── Cashing Chips Podcast
│   └── Betting Education/Plays Focus
│   └── "Powered by Ludi Lens"
│
└── CLV Tracker (Premium Feature - Future)
    └── "The Truth Serum" / "Ludi Verify"
```

### Naming Rationale

**LUDI INFORMATIO:**
- Latin for "Games Information"
- Sounds institutional, rigorous, mathematical
- Creates curiosity and trust
- Professional enough for investors/business people

**LUDI LENS:**
- "Lens" implies focus, zooming in, seeing what others miss
- Feels like a tool (similar to "Google Lens")
- Tagline options: "Focus Your Edge" or "Your Chief of Staff for Sports Betting"

### Alternative Names Considered (Rejected)

| Name | Reasoning | Why Rejected |
|------|-----------|--------------|
| The Praetorian Model | Elite Roman guards | Too stiff for podcast audience |
| The Imperium Model | Absolute command | Too aggressive |
| Ludi Core | Central processor | Too generic |

---

## 4. Mathematical Foundation

### Core Principle: Poisson Over Normal

**The Rookie Mistake:**
Using a Normal Distribution (Bell Curve) assumes a player is equally likely to score -5 points as +5 points. But you can't score negative points.

**The Pro Standard:**
- **Points/Rebounds/Assists**: Use **Poisson Distribution** (designed for counting events, ensures values ≥ 0)
- **Efficiency (FG%)**: Use Normal Distribution, but clamp between 0% and 100%

**Why Poisson Matters:**
- Captures the "fat right tail" (rare 50+ point explosion games)
- More accurately models NBA scoring reality
- Enables proper "Alt Lines" betting (LeBron 30+ Points at +200)

### Simulation Count: The Sweet Spot

| Sims | Margin of Error | Speed | Verdict |
|------|-----------------|-------|---------|
| 1,000 | ~3.1% | Fastest | Too imprecise |
| 2,500 | ~2.0% | Balanced | **Optimal** |
| 10,000 | ~1.0% | Slow | Overnight only |

**Formula:** Standard Error = 1/√N

**Recommendation:** Default to **2,500 simulations** for live use.

### Coefficient of Variation (CV)

**Formula:** CV = Standard Deviation / Mean

**Why It Matters:**
- Allows comparison of volatility between stars and role players
- A "20 PPG scorer" with high CV is riskier than a consistent one
- Helps identify "Stable Base" vs "Volatile Edge" opportunities

**Implementation:**
```python
cv_points = player_std_dev_pts / player_avg_pts
# High CV = wider simulation range
# Low CV = tighter, more predictable
```

### Recency Decay Weights

The model weights recent performance more heavily:

| Time Period | Weight |
|-------------|--------|
| Last 10 Games | 50% |
| Current Season | 30% |
| Last Season | 20% |

**Example (Giannis 2025-26):**
If Giannis averaged 7.2 assists over the last month under Doc Rivers (up from career 5.8), the model shifts heavily toward "Facilitator" regardless of historical averages.

### The "One Ball Rule" (Negative Correlation)

**The Concept:**
There is only one basketball. If the simulation gives Giannis 15 rebounds in a specific run, it mathematically forces Brook Lopez's rebound probability DOWN for that same run.

**Implementation:**
- Rebounds, assists, and touches are zero-sum across teammates within each simulation run
- Enables accurate **correlation betting** (PIVOT PLAYS)

---

## 5. Play Classification System

### The "Front Office" Grading Scale

Moving away from generic betting terms to executive-level classifications:

| Tag | Old Term | Criteria | Visual |
|-----|----------|----------|--------|
| **BLUE CHIP** | Diamond | Edge >10% AND WinProb >60% | Top tier, franchise cornerstone |
| **CORE ASSET** | Gold | Edge >4% AND WinProb >55% | Reliable, part of the rotation |
| **THE STEAL** | Silver/Value | Edge >5% AND Line Diff >1.5 pts | Market correction opportunity |
| **STRUCTURED** | Combo/SGP | Correlation value detected | Optimized parlay structure |
| **MARKET CORRECTION** | Mispriced | Book dropped line incorrectly | Buy low on temporary dip |
| **PIVOT PLAY** | Correlation | High Assist = Low Rebound | Trade-off prop opportunity |

### The Math Behind Tags

**BLUE CHIP Calculation:**
```python
if edge_pct > 10 and win_probability > 0.60:
    tag = "BLUE CHIP"
    # Translation: "Huge mathematical advantage. High confidence."
```

**THE STEAL Calculation:**
```python
if edge_pct > 5 and abs(projection - line) > 1.5:
    tag = "THE STEAL"
    # Translation: "The Market Price is wrong (5.5 vs 7.0). Buy the mistake."
```

**STRUCTURED Calculation:**
```python
# Check if combined probability exceeds implied odds
if prob_combined > implied_prob_parlay:
    tag = "STRUCTURED"
    # Example: 20 Points + 5 Assists combo pays +250
    # but fair value is only +180
```

---

## 6. Archetype Definitions

### Player Rebounding Archetypes

| Archetype | Criteria | Scouting Report | Betting Edge |
|-----------|----------|-----------------|--------------|
| **THE WARRIOR** | Contested Reb % > 40% | Fights in traffic | Bet OVER vs soft rebounding teams |
| **THE VULTURE** | Uncontested % > 80% AND Avg Distance > 6ft | Chases long rebounds | Bet UNDER if opponent shoots high FG% |

### Player Defensive Archetypes

| Archetype | Criteria | The Victim | Scouting Report |
|-----------|----------|------------|-----------------|
| **SCREEN NAVIGATOR** | Top 20th percentile vs OffScreen/Handoff | Steph Curry, Klay Thompson | DO NOT bet "Catch & Shoot" props against him |
| **THE ISLAND** | Top 20th percentile vs Isolation | Luka, SGA | Downgrade Points projections for Iso scorers |
| **DROP ANCHOR** | Top 20th percentile vs PnR Roll Man | Ja Morant (Drivers) | Kills "Points in Paint" but allows floaters |

### Player Playmaking Archetypes

| Archetype | Criteria | Example | Betting Edge |
|-----------|----------|---------|--------------|
| **PnR MAESTRO** | High PRBallHandler Freq + High Potential Assists | Trae Young, Haliburton | If opponent plays Drop = UNDER assists. If Blitz = OVER assists |
| **THE CONNECTOR** | High Passes Made but lower Assists | Draymond, Horford | Don't bet his assists. Bet teammate points |
| **TRANSITION ARTIST** | High Transition Freq + High Pace | LaMelo Ball | Only bet OVER in high pace games |

### Team Offensive Archetypes

| Archetype | Traits | Betting Application |
|-----------|--------|---------------------|
| **PACE & SPACE** | High 3PT Rate, Fast Pace | Great for Over Totals, Rebound chaos |
| **BULLY BALL** | High Paint Points, High FT Rate | Target opponent Center fouls, Block props |
| **HELIOCENTRIC** | One player >35% Usage, Low Team Assists | If star OUT, smash Team Total UNDER |

### Team Defensive Archetypes

| Archetype | Traits | How to Attack |
|-----------|--------|---------------|
| **THE FUNNEL (Drop)** | High Mid-Range allowed, Low Rim allowed | Target floater/mid-range shooters OVER |
| **THE SWARM (Blitz)** | High Turnover Force Rate, High Corner 3 allowed | Fade star Points, smash corner 3 shooters |
| **SWITCH EVERYTHING** | Low Assists Allowed, High Iso frequency | Target Iso scorers, fade catch-and-shoot guys |

---

## 7. Strategic Market Focus

### The Pro Verdict: Props Over Main Lines

**For Main Markets (Spreads/Totals):**
> NO. It is incredibly difficult for a solo developer to beat the closing line on "Lakers -5" consistently. The market is too efficient, and the "Wiseguys" with millions of dollars shape that line before you even wake up.

**For Player Props (Our Focus):**
> YES. This is the "Soft" market. Books cannot perfectly price 300+ player props every night, especially when news breaks. This is where Module X (Scenario Builder) gives a legitimate mathematical edge.

### Why Props Are Exploitable

1. **Volume Problem**: Books price hundreds of props per slate with less attention each
2. **News Lag**: When injury news breaks, props adjust slower than main lines
3. **Conditional Probability**: Books use static averages; we use dynamic scenarios
4. **Late Scratches**: The 15-minute window before tip is where value appears

### The "Edge" Reality

| Your Architecture | Pro Verdict |
|-------------------|-------------|
| Conditional Probability (Module X) | **STRONGEST ASSET** - This is exactly how syndicates print money |
| Blowout Tax (Module F) | **PRO-LEVEL** - Separates you from novices |
| Game Script / Correlation | **MATHEMATICALLY SOUND** - Matches correlation betting principles |

---

## 8. Data Sources & Integration

### The Multi-Source Strategy

| Source | Frequency | Purpose | Module |
|--------|-----------|---------|--------|
| **Basketball-Reference** | Weekly (Mondays) | Referee personality profiles | Module G |
| **NBAstuffer** | Daily (5 AM) | Hot/cold referee recent data | Module G |
| **Covers.com** | Daily | Profitability audit (O/U trends) | Module G |
| **OddsShark** | Daily | Consensus verification | Module A |
| **nba_api** | Live | Official NBA data, tracking stats | Module H |
| **The-Odds-API** | 4x Daily | Lines from FD/DK/MGM | Module A |

### The "Sniper Protocol"

To conserve API calls and costs:
- Check lines **4 times daily** (not continuous)
- Times: 8 AM, 12 PM, 5 PM, 7 PM
- Save fetched data to SQLite immediately
- Only fetch "heavy" data (tracking stats) overnight

### Tracking Data Endpoints (nba_api)

| Endpoint | Data | Use Case |
|----------|------|----------|
| `PlayerDashPtPass` | Potential Assists | Regression detection |
| `PlayerDashPtReb` | Contested/Uncontested Reb | Archetype classification |
| `SynergyPlayType` | Play type frequencies | Matchup analysis |
| `BoxScoreMatchupsV3` | Defender assignments | Shadow matrix |

---

## 9. Front Office Terminology

### The Language Upgrade

To elevate the brand from "betting site" to "sports intelligence platform":

| Old Term (Degen) | New Term (Executive) |
|------------------|----------------------|
| Odds | Implied Probability |
| Bet Size | Allocation |
| Picks | The Briefing |
| War Room | The Front Office |
| Diamond Plays | Blue Chip Assets |
| Lock | High Conviction |
| Parlay | Structured Position |
| Degen | Originator |
| Tout | Analyst |
| Whale | Institutional Capital |

### Dashboard Terminology

| Section | Professional Name |
|---------|-------------------|
| Main Page | Executive Briefing |
| Best Plays | The Shortlist |
| Injury Feed | The Radar |
| Line Movement | Market Pulse |
| Chat Interface | Ludi Chat |
| Scenario Builder | Scenario Control |

---

## 10. Pro Standards & Validation

### The CLV Obsession

**What Amateurs Track:** Win/Loss Record
**What Pros Track:** Closing Line Value (CLV)

**The Pro Standard:**
> "If you bet LeBron Over 24.5, and the line closes at 26.5, you WON even if LeBron only scores 20. You identified a discrepancy that the entire market eventually agreed with."

### The "Reverse Line Movement" Alert

**The Scenario:**
- You love the OVER
- 80% of public bets the OVER
- The line moves DOWN (22.5 → 21.5)

**The Translation:**
A "Sharp" or syndicate hammered the UNDER with enough money to move the line against the public.

**The Rule:**
> If (Public% > 60%) AND (Line Moves Opposite), **KILL THE BET**. Do not fight the Sharps.

### Validation Requirements (Non-Negotiable)

| Gate | Requirement | Consequence of Failure |
|------|-------------|------------------------|
| Week 5 | RMSE < 15%, Hit Rate > 50% | Stop, diagnose, refactor |
| Week 6 | RMSE < 10%, Hit Rate > 52% | Extend calibration |
| Week 8 | 200+ paper bets tracked | No real money until passed |

### Key Metrics to Track

| Metric | Purpose | Target |
|--------|---------|--------|
| **RMSE** | Projection accuracy | < 10% |
| **Hit Rate** | Overall win percentage | > 52.4% (breakeven at -110) |
| **CLV %** | Beating closing lines | > 60% |
| **Brier Score** | Probability calibration | < 0.25 |
| **Log Loss** | Model confidence accuracy | Lower is better |

---

## 11. Future Expansion Roadmap

### Deferred to Post-Week 8

| Feature | Description | Priority |
|---------|-------------|----------|
| **Module R (Ledger)** | Bankroll tracking, CLV monitoring | Month 3 |
| **Module S (Scout)** | Beat writer monitoring (30-min polling) | Month 3 |
| **Module T (Telegram)** | Two-way bot with remote commands | Week 8 |
| **ML Layer** | XGBoost/SHAP for feature importance | Month 4 |
| **Multi-Sport** | WNBA, NFL props expansion | Month 6 |
| **Android App** | Mobile interface | Month 6+ |

### The "Pro Tool" (Option B) Requirements

Only pursue after 3 months of profitable betting with core system:
- ~$50-100/mo hosting budget
- Paid API tiers
- Dedicated server (not free tier)

---

## 12. Lessons Learned

### What Works

1. **Poisson > Normal**: Real NBA stats have floors and fat tails
2. **Props > Spreads**: Soft market beats efficient market
3. **Scenarios > Averages**: Conditional probability is the edge
4. **CLV > Win Rate**: The only true measure of model accuracy
5. **Validation > Features**: Don't build UI for unproven math

### What to Avoid

1. **Generic DvP Stats**: "Wizards allow most points to PGs" is noise
2. **Career Averages**: Player roles change (Giannis 2025 ≠ Giannis 2021)
3. **Fighting Sharp Money**: If line moves against public, step aside
4. **Skipping Validation**: The most expensive mistake is betting unvalidated projections
5. **Scope Creep**: Nail NBA before expanding to other sports

### The Developer Contract

**Commitments Made:**
1. Week 1 Day 1: Fix API key security (DONE)
2. Week 5: Build validation framework (no shortcuts)
3. Week 5 Gate: If validation fails, extend Week 6
4. No Real Money: Until 200 paper bets show >52% hit rate
5. No Scope Creep: Option B features are OFF LIMITS until Month 6

---

## Appendix A: Key Formulas

### Expected Value (EV)
```python
ev = (win_prob * potential_profit) - (lose_prob * stake)
edge_pct = (win_prob - implied_prob) / implied_prob * 100
```

### Win Probability from Edge
```python
# Theoretical (to be calibrated empirically in Week 5-6)
win_prob = 0.50 + (edge / 140)
```

### Kelly Criterion (Bet Sizing)
```python
kelly_fraction = (win_prob * odds - 1) / (odds - 1)
# Use fractional Kelly (25-50%) for risk management
```

### Poisson Probability
```python
import numpy as np
projected_points = np.random.poisson(lam=mean_projection, size=2500)
```

---

## Appendix B: Reference Links

### NBA Data Sources
- https://github.com/JovaniPink/awesome-nba-data
- https://www.nbastuffer.com/2025-2026-nba-referee-stats/
- https://www.basketball-reference.com/referees/2026_register.html
- https://www.rotowire.com/basketball/ref-stats.php
- https://www.oddsshark.com/nba/referee-handicapping-statistics
- https://www.covers.com/sport/basketball/nba/referees

### Official NBA Resources
- https://official.nba.com/2025-26-points-of-emphasis/
- https://official.nba.com/2025-26-nba-officiating-last-two-minute-reports/
- https://ak-static.cms.nba.com/wp-content/uploads/sites/4/2025/10/Official-2025-26-NBA-Playing-Rules.pdf

### Research & Academic
- https://www.nature.com/articles/s41598-025-13657-1
- https://www.sciencedirect.com/science/article/pii/S266682702400015X
- https://dlevine820.github.io/Beating-Vegas-Thesis/6-appendix.html
- https://www.kaggle.com/code/perry613/nba-sports-betting-model
- https://medium.com/@jriordan1/beating-the-bookmakers-with-a-simple-ev-algorithm-nba-spreads-7f59b1ab314d

---

**Document Version:** 1.0
**Created:** January 5, 2026
**Last Updated:** January 5, 2026
**Author:** Claude Opus 4.5 via Claude Code
**Project:** Ludi Informatio v2.0 - NBA Analytics Platform
