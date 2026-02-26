# SGP Correlation Theory & Player Prop Curation Best Practices

**Created:** February 25, 2026
**Source:** Multi-source research (Unabated, OddsIndex, PMC, SHRStats, OddsShopper, LSports, WagerTheorem)
**Purpose:** Reference for Phase 8.26 (Correlated Props Flagging) + Phase 8.24 (Edge Type Labeling)
         + AI prompt engineering for `curate_plays.py` Sonnet curation call.

---

## Part 1: SGP Correlation Theory

### Why Books Earn 20%+ Hold on SGPs

Standard -110/-110 prop: **4.8% vig**. Common -115/-115 prop: **7.4% vig**. Same-game parlay: **20%+ hold**.

The mechanism is the "correlation tax" — books reduce parlay payouts when outcomes share positive variance.
But their pricing of that reduction is imprecise. The exploitation opportunity:
- **Under-priced correlation** (book gives more payout than correlation warrants) = positive-EV
- **Over-priced correlation** = paying too much for the combination
- Every sportsbook prices correlation differently — Caesars vs bet365 can differ materially on the same SGP

### NBA Stat Correlation Map

**Within-Player Positive Correlations (same player, same game):**

| Stat Pair | Correlation | Mechanism |
|-----------|-------------|-----------|
| PTS + FGA | r ≈ 0.85+ | Direct causal — volume = scoring |
| PTS + MIN | r ≈ 0.70–0.80 | Minutes is the floor under all volume stats |
| PTS + 3PM | r ≈ 0.70+ | Volume scorers attempt more threes |
| PTS + FTA | r ≈ 0.50–0.65 | Aggressive scorers draw more fouls |
| PTS + REB | r ≈ 0.50–0.55 | Both correlate with on-court time + usage |
| AST + MIN | r ≈ 0.65–0.75 | Ball handlers need time to accumulate |
| PTS + AST | r ≈ 0.40–0.55 | Role-dependent — heliocentrics do both; spot-up shooters do not |
| REB + BLK | r ≈ 0.45–0.55 | Big-man physical profile drives both |

**PRA/PA/PR Composite Stat — Critical Rule:**
- PTS is a component of PRA — they are structurally correlated (PRA = PTS + REB + AST)
- NEVER bet PTS OVER + PRA OVER same player same game → both fail in same low-usage outcome
- Our `CORRELATED_STAT_PAIRS` frozenset in `curate_plays.py` enforces this programmatically

**Cross-Player Correlations:**

| Scenario | Risk | Notes |
|----------|------|-------|
| Same team, 2× OVER | MODERATE-HIGH | Blowout eliminates both; pace affects both |
| Playmaker AST OVER + Finisher PTS OVER | Positive (acceptable) | r ≈ 0.35–0.50 assist-to-score chain |
| Star OUT + Beneficiary OVER | Strongly positive (desirable) | Core of usage vacuum theory |
| Star PTS OVER + Teammate PTS OVER | Weakly negative | Finite possessions → star's big game reduces teammate volume |

**Game-Level Correlations:**

| Scenario | Direction |
|----------|-----------|
| High team total (>238) + Multiple OVER volume props | Positive — pace creates opportunities |
| Large spread (>10) + Star PTS OVER | Negative — blowout risk destroys OVER |
| Large spread (>10) + Bench player MIN OVER | Positive — garbage time expansion |

---

### Game Script Effects (Blowout Threshold: 15pt margin Q4)

When a game becomes a blowout:
- Starters lose ~12 minutes of expected playing time (entire Q4)
- A player averaging 36 min loses ~33% of expected production
- Bench players gain garbage-time minutes (+5-10% on minute props)
- Trailing team may speed up pace → higher attempts per minute but fewer total minutes

**Research confirms our existing blowout tax logic is correct.** The key curation implication:
for spreads > 10, avoid correlated `star PTS OVER + team to cover` parlays entirely.

---

### Pace/Total Effects on Correlations

- Games with pace differential > 8 possessions: total hits over **58.3%** of the time
- Total > 240: each additional possession adds ~0.5-1.0 expected points per player (usage-weighted)
- Total < 218: volume props for ALL players compress — UNDER structurally more valuable
- Roughly linear: each +5 on the total adds ~0.3-0.5 pts to an average starter's expected output

**Thresholds (matching existing Module E `USE_TEAM_TOTALS_MODIFIER`):**
```python
if total > 238:    pace_mult = 1.05  # already implemented
if total < 218:    pace_mult = 0.95  # already implemented
# Future refinement:
if total > 245:    pace_mult = 1.08  # ultra-fast game
```

---

## Part 2: Player Prop Value Identification

### How Books Set Prop Lines (Their Weaknesses)

Books start from rolling median (L10-L15), apply rough home/away split (±0.5-1.0), apply basic opponent DRTG,
then vig to both sides. They do **NOT**:
- Apply archetype-specific matchup modifiers (Module E advantage)
- Update beneficiary lines in real-time after star scratches (Module X + D advantage)
- Model game-script blowout probability with nuance (blowout tax advantage)
- Account for referee pace impact (Module G advantage)

**Market hold rates:**
- Standard -110/-110: 4.8% vig
- Common -115/-110: 6.2% vig
- Problematic -120/-110: 8.9% vig
- Same-game parlays: 20%+ hold

### Value vs. Trap Signal Checklist

**VALUE PROP indicators:**
- Line set below player's rolling median by 1+ units (books overweighting a single down game)
- Archetype matchup advantage present (Module E edge)
- Star teammate OUT creating usage vacuum (Module X scenario)
- High-pace game with historically tight prop line (pace not priced in)
- Recent Pinnacle line moved toward your side (sharp corroboration)
- CLV positive in simulation output

**TRAP PROP indicators:**
- Player coming off outlier performance (recency bias inflating the line)
- High public over% (>70%) with flat or rising line — public buying narrative, books holding correctly
- Large spread on star player's side + their PTS OVER (blowout risk)
- Line above player's median + hype narrative (return from injury, rivalry)
- Vig worse than -115 (book signaling it's protecting the sharp side)

**The UNDER structural bias:**
Public bets OVER on player props ~70% of the time (they want to root for big performances).
This creates systematic UNDER value in high-profile markets.
Our live data confirms: OVER hit rate 42.1% vs UNDER hit rate 55.0% (14,423 bets, Jan-Feb 2026).
This is NOT coincidence — it is a structural feature of the market.

---

### Injury News as Edge Source (Value Creation Timeline)

| Time Before Tip | Event | Window Status |
|-----------------|-------|---------------|
| -120 min | NBA official injury report published | Books begin adjusting |
| -90 to -60 min | RotoWire/ESPN RSS breaks news | 🟢 OPEN — books lag by 20-40 min on BENEFICIARY lines |
| -45 min | Books fully reprice OUT player's props (removed) | Beneficiary lines still lagging |
| -20 min | Late GTD/Q scratches | 🟢 Second window — beneficiary props repriced slowly |
| -5 min | Warm-up reports via Twitter/X | 🔴 CLOSED — books already updated |

**Key insight from research (Unabated):** Books are fast at removing the OUT player's line, but
**slow at correctly boosting the beneficiary's line** — 20-40 minute lag. This is why
usage vacuum theory (Module X) + Module D injury timing = strongest combined edge source.

---

### DVP Best Practices for Prop Selection

1. Use recent stretches (L10-L15) over full-season DVP — teams change schemes mid-season
2. Gate on `data_confidence = 'HIGH'` (30+ game sample) for hard recommendations
3. Archetype-to-scheme mismatches are more predictive than raw positional DVP
4. DVP value scales with pace — a soft DVP matchup in a slow game is less valuable than in a fast game
5. Minimum 75 possessions per Synergy playtype (already `module_e.py` line 636)

**Validated matchup effects (research-backed):**
- STRETCH_BIG/SNIPER_ELITE vs PAINT_PACK: +12-15% 3PM
- ROLL_MAN vs PAINT_PACK: +10-15% PTS at rim
- ISO_ASSASSIN vs BLITZ: -8-12% PPP
- HELIOCENTRIC_MAESTRO vs BLITZ: +15-20% AST (forced to pass out of double)

---

## Part 3: Portfolio Construction Rules

### Correlation Risk Framework

**Adverse scenarios that kill multiple bets simultaneously:**
1. **Blowout**: Spread > 10, all-star OVER bets lose together
2. **Low-pace game**: Total under projection, all OVER volume bets lose
3. **Whistle drought**: Ref projection was foul-heavy, but clean game → FTA OVERs lose
4. **Minutes restriction**: Star plays fewer minutes → all volume OVERs correlated

**Max exposure guidelines (research + industry practice):**

| Exposure Type | Research Recommendation | Ludi Current |
|---------------|------------------------|--------------|
| Single bet | 1-3% bankroll | 0.25u-1.5u ✓ |
| Single game | 3-5% bankroll (max 2 bets) | Max 2 per game ✓ |
| Single team | 2-3% bankroll | Not yet enforced |
| Single stat type | 10-15% total | Not enforced |
| Daily session | 5-10% bankroll | 5 picks × avg |

**New rules to consider (Phase 8.26 upgrade path):**
- Max 1 bet per team (not just per game) — reduces team-collapse risk
- Max 2 bets of same stat type per day (max 2 PTS bets)
- No combining team OVER on game total + same team's star PTS OVER (explicit blowout correlation)

### Kelly Criterion for Correlated Props

Standard Kelly assumes bet independence. Correlated bets break this assumption.

**Research-backed corrections:**

**Method 1: Treat correlated bets as a single position**
```python
# If bet_a and bet_b from same game (correlation ≈ 0.3-0.5):
kelly_a_adj = kelly_a * (1 - correlation)
kelly_b_adj = kelly_b * (1 - correlation)
```

**Method 2: Fractional Kelly (simplest)**
- Full Kelly: Maximum growth, dangerous with correlated risk
- Half Kelly (1/2 K): 75% of Full Kelly growth, cuts variance 50%
- Quarter Kelly (1/4 K): Captures growth, most conservative
- Ludi current 1/8 Kelly (divide by 8) → **validated by industry research** as appropriate
  given model uncertainty + correlated prop risk + bookmaker limits

**Our 0.25u-1.5u tiering with ÷8 Kelly is research-validated. Do not change.**

---

## Part 4: AI Curation Enhancement Patterns

### SGP Correlation Rules for Sonnet Prompt (Future Enhancement)

Add to `_sonnet_curate()` system prompt for Phase 8.26 upgrade:

```
CORRELATION RED FLAGS (flag these combinations in reasoning):
- Same player, multiple volume stats (PTS + REB + AST all OVER = avoid)
- Same team, 2× OVER with spread > 8 (blowout kills both legs)
- Any OVER where game spread is same team's side AND spread > 10
- Opponent's star OVER + team's star OVER when game total < 220 (finite scoring)

POSITIVE CORRELATION STACKS (acceptable patterns):
- Playmaker AST OVER + finisher PTS OVER (r ≈ 0.35-0.50)
- High-pace game (total > 238) + multiple OVER props from DIFFERENT games
- Usage vacuum OVER (OUT star) + direct beneficiary OVER = always #1 combo
```

### Pace/Total Signal in Curation Prompt (Future Enhancement)

Add to `_sonnet_curate()` user prompt:
```python
if total and float(total) > 238:
    env_context += "\nGAME NOTE: High-pace (total={total}) — OVER volume props structurally favored."
elif total and float(total) < 218:
    env_context += "\nGAME NOTE: Slow game (total={total}) — UNDER props favored; deprioritize volume OVERs."
```

### High-Variance Stat Gate (Future Enhancement)

3PM, BLK, STL, TOV have high variance relative to their edge signals.
Add to Sonnet system prompt:
```
HIGH VARIANCE STATS (3PM, BLK, STL, TOV): require edge ≥ 8% before selecting.
These stats have high game-to-game variance; a 5% edge is statistically
indistinguishable from noise until 200+ sample size.
```

### DVP Confidence Gate for Prompt (Future Enhancement)

Enrich `_fetch_todays_bets()` or add enrichment function:
```python
dvp_query = """
    SELECT rank_pts, data_confidence, avg_pts_per100
    FROM team_dvp_by_archetype
    WHERE opponent_team = ? AND archetype = ? AND season = '2025-26'
    ORDER BY updated_at DESC LIMIT 1
"""
# Append to bet dict: dvp_rank, dvp_confidence
# Pass to Sonnet: "DVP rank: 3/30 (HIGH confidence) — strong matchup edge"
```

---

## Key Numbers to Know

| Metric | Value | Source |
|--------|-------|--------|
| SGP hold rate | 20%+ | Industry data |
| Standard -110/-110 prop vig | 4.8% | Wizard of Odds |
| Correlation tax (2-leg SGP payout reduction) | ~15% | OddsIndex |
| Sharp bettor CLV beat rate | 55-60% of bets | Professional standard |
| Our UNDER hit rate (live data) | 55.0% | ludi.db 14,423 bets |
| Our OVER hit rate (live data) | 42.1% | ludi.db 14,423 bets |
| PTS+REB within-player correlation | r ≈ 0.53 | NBA data analysis |
| Blowout threshold (star sits Q4) | 15pt margin entering Q4 | LSports research |
| Minutes lost in blowout | ~12 min (entire Q4) | WagerTheorem |
| High-pace over rate (pace differential >8) | 58.3% | Sports analytics |
| 1/8 Kelly: Ludi current sizing | Validated | Industry consensus |
| Prop lines lag injury news (beneficiaries) | 20-40 min | Unabated research |
| Public OVER% structural bias | ~70% on star props | Market observation |

---

## Related Files

- `scripts/curate_plays.py` — Phase 8.26: `CORRELATED_STAT_PAIRS` + `_detect_same_game_pairs()`
- `module_f.py` — Phase 8.24: `_classify_edge_type()` (Projection/Matchup/Injury-Vacuum/Hot-Streak)
- `utils/blowout_tax.py` — Existing blowout probability by spread/context
- `best-practices/data/DVP_AND_SCHEME_METHODOLOGY.md` — DVP matchup signal rules
- `docs/METHODOLOGY.md` — Kelly sizing, devigging, CLV methodology
