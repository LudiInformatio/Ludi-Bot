# Sportsbook Tier Architecture & Betting Math Reference
*Ludi-Bot Sharp Betting Model — Last Updated: February 2026*

This is the definitive reference for how each platform type works mathematically, and how
the Ludi-Bot model should treat it.

---

## Tier 0: Sharp Reference Books (CLV Benchmark — NC Inaccessible)

Used to **validate the model**, not to bet. If your odds consistently beat their closing line,
the model is provably sharp.

| Book | Vig/Hold | Bet Limits | CLV Benchmark Quality |
|------|---------|-----------|----------------------|
| Pinnacle | 1–3% | $50,000+ | Gold standard globally |
| Circa | 2.5–3.8% | $20k–$100k | Best US land-based sharp ref |
| Bovada | ~3.67% | Moderate | Secondary reference (crypto-friendly) |
| BetOnline | ~3.18% | Moderate | Slightly sharper than Bovada |

**CLV threshold targets (Pinnacle close):**
- 50–54%: baseline, keep tracking
- 55–60%: promising, likely profitable edge
- 60–70%: strong edge — model is sharp
- 70%+: elite territory

**Math:** Always devig Pinnacle's closing price before computing CLV, even though their vig is low.
Your existing `devig_multiplicative()` function handles this correctly.

**Tools:** Unabated's "Unabated Line" is a vig-free consensus from market-making books —
good alternative to manually devigging Pinnacle: [unabated.com/nba/odds](https://unabated.com/nba/odds)

---

## Tier 1: Peer-to-Peer / Exchange Books (Near-Zero Vig — NC Available)

**Key insight: No devigging needed.** Prices are near true market probability.
`edge = model_prob - exchange_implied_prob` directly.

### Novig
- **Structure:** P2P matching; Novig market-makes with 1–4% spread when liquidity is thin
- **Commission:** ~0% P2P, 1–4% when Novig is the market maker
- **Math:** At -100/-100 (even money), true prob = 50.0%. Any model_prob > 50% = +EV.
- **NC Status:** Operating under sweepstakes model; pursuing CFTC approval (Ludlow Exchange, $75M Series B)
- **URL:** [novig.us](https://www.novig.us)

### ProphetX
- **Structure:** P2P exchange, user-proposed odds matched by algo
- **Commission:** 1% on spreads/totals; **0% on player props** ← use for NBA props
- **Math:** At 0% commission, ProphetX price IS the market's true probability. No devig.
- **NBA Props edge formula:** `edge = model_prob - prophetx_implied_prob`
- **NC Status:** Available in multiple states — verify at [prophetx.com](https://www.prophetx.com)
- **URL:** [oddsshopper.com — ProphetX overview](https://www.oddsshopper.com/articles/betting-101/what-is-prophetx-sports-betting-what-to-know-about-prophet-x-y10)

### Rebet
- **Structure:** Sweepstakes + P2P challenge feature (set your own odds, find a taker)
- **Commission:** 0% on P2P challenges
- **Math:** For even-money P2P challenges, `edge = model_prob - 0.50` directly
- **NC Status:** Yes (44 states, sweepstakes model)
- **URL:** [dimers.com — Rebet Guide](https://www.dimers.com/social-sportsbooks/rebet/betting-guide)

### Oxyn Odds
- Research found no verified results for this platform as of Feb 2026. May be new/regional.
- Verify directly before adding to pipeline.

---

## Tier 2: NC Legal Sportsbooks (Primary Betting Volume)

**Key insight: Devigging required.** Standard 4–6% vig means you need model_prob > 52.4%
to beat a -110/-110 market. Use `devig_multiplicative()` from `utils/devig.py`.

**Edge formula:** `(model_prob - fair_prob) / fair_prob × 100`

| Book | Typical Prop Vig | Notes |
|------|-----------------|-------|
| FanDuel | 4–5% | Best parlay odds, widest prop market |
| DraftKings | 4–5% | Wide coverage, alt lines available |
| Fanatics | 4–5% | Growing NC presence |
| BetMGM | 4–6% | Good alt line coverage |
| Caesars | 5–6% | Promo-heavy, good for juice plays |
| TheScore Bet | 4–5% | Competitive props |
| Bet365 | 4–5% | Best live betting odds |

**Break-even by juice level:**
| Odds | Fair Prob (devigged) | Break-even model_prob |
|------|--------------------|-----------------------|
| -110 | 50.0% | 52.4% |
| -115 | 51.2% | 53.7% |
| -120 | 52.4% | 54.6% |
| -130 | 54.2% | 56.5% |

**Best practice:** Always find the best decimal odds at Tier 2 books for the chosen direction.
The `book_over`/`book_under` fields in the pipeline output tell you where to bet.

---

## Tier 3: DFS Pick'em Platforms (Different Math Entirely)

**CRITICAL: The EV formula for DFS is NOT the same as traditional sports betting.**

DFS pick'em platforms have no traditional over/under odds. You pick More/Less on a line
and receive a fixed multiplier. The math is parlay probability, not edge calculation.

**DFS Edge Formula:**
```
entry_ev = (P(win_leg_1) × P(win_leg_2) × ... × P(win_leg_n)) × multiplier - 1
```

**Where is the edge?** These platforms lag sportsbook line movement. Edge windows:
1. After injury news hits sportsbooks before DFS adjusts
2. When sportsbook implied prob for a leg > 55% but DFS still treats as 50/50
3. "Middling" — when PrizePicks and Underdog disagree on same player's line

### PrizePicks
- **NC:** Yes (18+)
- **How lines are set:** Target 50/50 outcome. "Bumps" line if sportsbook odds are heavy one way.
  Props too juiced are removed from board.
- **Math note:** Their projected line ≈ market fair line. Lag between sportsbook and PP = the edge.

**Payout Table:**
| Picks | Power Play | Flex (All) | Flex (1 Miss) | Flex (2 Miss) |
|-------|-----------|-----------|---------------|---------------|
| 2 | 3× | — | — | — |
| 3 | 5× | — | — | — |
| 4 | 10× | 5× | 0.5× | — |
| 5 | 22× | 10× | 2× | 0.4× |
| 6 | 37.5× | 25× | 2× | 0.4× |

**Special modifiers:** Demons (harder line, up to 2,000× boost) / Goblins (easier line, lower mult)
**DNPs:** Entry reverts to next lower pick count
- URLs: [prizepicks.com/resources/how-to-play-prizepicks](https://www.prizepicks.com/resources/how-to-play-prizepicks)

### Underdog Fantasy
- **NC:** Yes (integrated licensed sportsbook also available)
- **Payout Table:**
| Picks | Standard | Insured (All) | Insured (1 Miss) |
|-------|----------|---------------|------------------|
| 2 | 3× | — | — |
| 3 | 6× | ~4× | partial |
| 4 | ~12× | ~6× | ~1.5× |
| 5 | 20× | 10× | 2.5× |
- **Scorchers:** Boosted picks (+1.5–2.5× bonus) — evaluate underlying line first before taking boost
- **Middling:** PrizePicks vs Underdog on same player is a well-known tactic when lines diverge 1+ point
- URL: [app.underdogfantasy.com/rules/pick-em](https://app.underdogfantasy.com/rules/pick-em)

### Sleeper Fantasy
- **NC:** Yes
- **Key differentiator:** Dynamic multipliers (each leg has own floating multiplier based on user activity).
  Sleeper adjusts multipliers rather than bumping lines. This can lock in above-fair-value odds
  before the market recognizes mispricing.
- **Flex:** Available for 3+ picks; 5+ picks for 2-miss insurance
- URL: [support.sleeper.com — Player Picks Rules](https://support.sleeper.com/en/articles/9047931-sleeper-player-picks-rules)

### Betr Picks
- **NC:** Yes (24 states)
- **Power Play:** All-or-nothing, up to 100× (10 picks). **Dynamic Play (Flex):** 1 miss allowed.
- **Smaller user base = slower line adjustment.** Potential for larger timing windows after news.
- URL: [rithmm.com — How Does Betr Picks Work](https://www.rithmm.com/post/how-does-betr-picks-work)

### Fliff
- **NC:** Yes (45 states, sweepstakes)
- **Structure:** Sweepstakes model using virtual currency (Fliff Coins + Fliff Cash). NOT real-money.
  Fliff Cash earns at 1 FC = $1, min $50 to redeem.
- **Model relevance:** LOW. Sweepstakes currency limits scale. Use for recreational engagement only.
- URL: [getfliff.com](https://www.getfliff.com)

### Dabble
- **NC:** Verify directly — state availability unclear
- **Structure:** Similar to PrizePicks. Up to 12 picks, up to 5,000× multiplier.
- **Note:** High pick counts erode EV fast via compounding error rate.

---

## Mathematical Framework Summary

| Platform | Vig Structure | Devig? | Edge Formula |
|----------|-------------|--------|-------------|
| PrizePicks / Underdog / Sleeper / Betr | ~12–15% implied per leg | No | `Π(P_i) × multiplier − 1` |
| Novig / ProphetX (exchange) | 0–1% commission | No | `model_prob − exchange_implied_prob` |
| Rebet (P2P challenge) | 0% | No | `model_prob − 0.50` |
| FD / DK / BetMGM / Caesars (NC legal) | 4–6% | Yes | `(model_prob − fair_prob) / fair_prob` |
| Pinnacle / Circa (CLV ref) | 1–4% | Yes (for CLV) | Reference only |

---

## Integration with Ludi-Bot Pipeline

**Current gaps to close (Phase 8.14+):**
1. DFS layer: flag props where sportsbook implied_prob > 55% but DFS line = 50/50 → "DFS PLAY" tag
2. Exchange layer: track Novig/ProphetX odds when available → use as fair_prob (no devig step)
3. CLV: use Pinnacle close (Phase 8.6 complete) + add ProphetX as secondary CLV benchmark
4. Book tier update: add Fanatics, TheScore to NC Legal list in `module_a.py`

**Optimal bet routing logic (future):**
```
1. Check ProphetX props (0% commission) → if available and model has edge → bet here first
2. Check Novig (0-1%) → if available → bet here second
3. Best NC Legal odds → FD/DK/BetMGM/Caesars → bet here for volume
4. Check DFS platforms → flag if PP/Underdog line lags sportsbook consensus by 0.5+ points
```
