---
name: backtest
description: >
  Run validation suite to check model accuracy against historical data.
  Verifies fatigue modifiers, playtype matchups, and archetype performance.
  Trigger phrases: "backtest", "run validation", "model accuracy", "/backtest".
agent: lena
user-invocable: true
---

# Backtest Validation

Runs a multi-tier validation suite organized by data source: **team games first** (macro
calibration), **player games second** (projection accuracy), **bet outcomes third** (edge
quality). Each tier runs at multiple time windows to surface both long-term drift and recent
trends. Per `best-practices/testing/README.md` Pattern 9: team infrastructure must be
verified before player signals — flat `1.0` modifiers mean no data, not no edge.

## Test Architecture

```
Tier 1 — Team Games (canonical_games + team_betting_trends + team_scheme_cache)
  Window A: Full season   → systematic calibration check
  Window B: 30-day        → recent drift detection
  Selection: all 4 scheme types (PAINT_PACK, BLITZ, PERIMETER, NEUTRAL) — full coverage

Tier 2 — Player Games (player_game_logs + player_type_profiles + players)
  Window A: 21-day        → B2B fatigue modifier validation
  Window B: 14-day        → archetype vs scheme matchup accuracy
  Selection: usg_pct >= 0.18 AND avg_min >= 24 (last 30d), 7-9 players

Tier 3 — Bet Outcomes (bet_recommendations + prop_line_snapshots)
  Window A: 14-day        → edge-to-outcome correlation
  Window B: CLV floor     → closing line value correlation (2026-02-27 onward)
```

**Run order is mandatory:** Tier 1 → Tier 2 → Tier 3. If Tier 1 shows empty scheme cache or
0 team rows, Tier 2 results are unreliable — report the infrastructure failure and stop.

---

## Execution Steps

### Step 1 — Tier 1: Team Games

First verify team infrastructure (scheme cache, canonical_games coverage):

```bash
sqlite3 ludi.db "
-- Verify ALL 4 defensive scheme types are present (BLITZ, NEUTRAL, PAINT_PACK, PERIMETER)
-- Missing a type = modifiers for that scheme are untestable
SELECT
  defensive_scheme,
  COUNT(*) AS teams,
  GROUP_CONCAT(team_abbr, ', ') AS team_list
FROM team_scheme_cache
GROUP BY defensive_scheme
ORDER BY defensive_scheme;
-- BLITZ: ATL (1 team)
-- NEUTRAL: DAL, DET, HOU, LAL, MIL, NOP, OKC, POR, UTA (9 teams)
-- PAINT_PACK: BOS, CHI, CLE, DEN, IND, LAC, MEM, MIA, MIN, NYK, PHI, SAS (12 teams)
-- PERIMETER: BKN, CHA, GSW, ORL, PHX, SAC, TOR, WAS (8 teams)
"

sqlite3 ludi.db "
-- canonical_games coverage check (use this, never JOIN games ON date+team)
SELECT COUNT(*) AS total_games, MAX(game_date) AS latest_game
FROM canonical_games;
"

sqlite3 ludi.db "
-- Blowout tax check: spread > 12.5 games — do volume props miss more?
-- Uses canonical_games (single row per game, no 3x inflation from games table)
SELECT
  CASE WHEN ABS(cg.spread) > 12.5 THEN 'blowout' ELSE 'normal' END AS game_type,
  COUNT(*) AS N,
  ROUND(AVG(CASE WHEN br.is_won = 1 THEN 1.0 ELSE 0.0 END) * 100, 1) AS win_rate_pct
FROM canonical_games cg
JOIN bet_recommendations br ON br.game_date = cg.game_date
WHERE cg.game_date >= date('now', '-30 days')
  AND br.stat_category IN ('points', 'rebounds', 'assists')
  AND br.is_won IS NOT NULL
  AND cg.spread IS NOT NULL
GROUP BY game_type;
-- Expect: blowout win_rate < normal win_rate (blowout tax working)
"

sqlite3 ludi.db "
-- Win rates vs all 4 defensive schemes — full coverage check
-- If any scheme row is missing, that archetype modifier family is untested
SELECT
  tsc.defensive_scheme,
  COUNT(*) AS bets,
  ROUND(AVG(CASE WHEN br.is_won = 1 THEN 1.0 ELSE 0.0 END) * 100, 1) AS win_rate_pct,
  ROUND(AVG(br.edge_pct), 1) AS avg_edge,
  COUNT(DISTINCT p.team) AS opponent_teams
FROM bet_recommendations br
JOIN players p ON p.name = br.player_name
JOIN team_scheme_cache tsc ON tsc.team_abbr = p.team
WHERE br.game_date >= date('now', '-30 days')
  AND br.is_won IS NOT NULL
GROUP BY tsc.defensive_scheme
ORDER BY tsc.defensive_scheme;
-- Must show all 4 rows: BLITZ, NEUTRAL, PAINT_PACK, PERIMETER
-- Missing row = no bets vs that scheme this window (small sample warning, not a data bug)
"
```

### Step 2 — Tier 2: Player Games

Select qualified test players first (Pattern 9 standard: usg_pct >= 0.18, avg_min >= 24):

```bash
sqlite3 ludi.db "
-- Find 7-9 qualified players for signal testing
SELECT p.player_id, p.name, p.team, p.archetype, ROUND(p.usg_pct, 3) AS usg_pct,
       ROUND(AVG(l.minutes), 1) AS avg_min, COUNT(*) AS recent_games
FROM players p
JOIN player_game_logs l ON p.player_id = l.player_id
WHERE p.usg_pct >= 0.18
  AND l.game_date >= date('now', '-30 days')
  AND l.minutes IS NOT NULL
GROUP BY p.player_id
HAVING AVG(l.minutes) >= 24
ORDER BY p.usg_pct DESC
LIMIT 9;
"
```

Run both player-level backtest scripts:

```bash
source .venv/bin/activate
python scripts/backtest_fatigue_21day.py --verbose
python scripts/backtest_playtype_trends_14day.py --verbose
```

Then validate actual **simulation projection accuracy** — `projection` vs `actual_result`:

```bash
sqlite3 ludi.db "
-- Sim projection accuracy: RMSE + mean error by stat category (30-day window)
-- projection = Module C Monte Carlo output; actual_result = settled outcome
SELECT
  stat_category,
  COUNT(*) AS N,
  ROUND(AVG(actual_result - projection), 2) AS mean_error,
  ROUND(SQRT(AVG((actual_result - projection) * (actual_result - projection))), 2) AS rmse,
  ROUND(AVG(CASE WHEN actual_result > line THEN 1.0 ELSE 0.0 END) * 100, 1) AS actual_over_pct,
  ROUND(AVG(CASE WHEN projection > line THEN 1.0 ELSE 0.0 END) * 100, 1) AS proj_over_pct
FROM bet_recommendations
WHERE game_date >= date('now', '-30 days')
  AND actual_result IS NOT NULL
  AND actual_result != -998
  AND projection IS NOT NULL
GROUP BY stat_category
HAVING N >= 20
ORDER BY rmse DESC;
-- mean_error > 0 = model underprojecting (actual > projection = systematic bias)
-- mean_error < 0 = model overprojecting
-- RMSE targets: PTS < 7.0, AST < 2.5, REB < 3.5
"

sqlite3 ludi.db "
-- Projection bias by confidence tier — do DIAMOND plays have lower RMSE?
SELECT
  confidence_tier,
  COUNT(*) AS N,
  ROUND(AVG(actual_result - projection), 2) AS mean_error,
  ROUND(SQRT(AVG((actual_result - projection) * (actual_result - projection))), 2) AS rmse,
  ROUND(AVG(CASE WHEN is_won = 1 THEN 1.0 ELSE 0.0 END) * 100, 1) AS win_rate_pct
FROM bet_recommendations
WHERE game_date >= date('now', '-30 days')
  AND actual_result IS NOT NULL
  AND actual_result != -998
  AND projection IS NOT NULL
  AND confidence_tier IS NOT NULL
GROUP BY confidence_tier
ORDER BY rmse ASC;
-- Expect: DIAMOND/BLUE_CHIP have lower RMSE than CORE_ASSET/THE_STEAL
-- If DIAMOND has higher RMSE: edge filter may be selecting for noise, not signal
"
```

Then verify archetype x scheme modifier signal is non-flat (all `1.0` = data problem):

```bash
sqlite3 ludi.db "
-- Archetype vs scheme win rates — 14-day window, N >= 5 per combo
SELECT
  br.archetype_tag,
  br.matchup_tag,
  COUNT(*) AS N,
  ROUND(AVG(CASE WHEN br.is_won = 1 THEN 1.0 ELSE 0.0 END) * 100, 1) AS win_rate_pct,
  ROUND(AVG(br.edge_pct), 1) AS avg_edge
FROM bet_recommendations br
WHERE br.game_date >= date('now', '-14 days')
  AND br.is_won IS NOT NULL
  AND br.archetype_tag IS NOT NULL
  AND br.matchup_tag IS NOT NULL
GROUP BY br.archetype_tag, br.matchup_tag
HAVING N >= 5
ORDER BY win_rate_pct DESC;
-- If every row has the same win_rate: data flow issue, not model performance
"
```

### Step 3 — Tier 3: Bet Outcomes

```bash
sqlite3 ludi.db "
-- Edge tier win rates: is higher edge tier actually predicting more wins?
SELECT
  CASE
    WHEN edge_pct >= 15 THEN 'DIAMOND (>=15%)'
    WHEN edge_pct >= 10 THEN 'BLUE_CHIP (10-15%)'
    WHEN edge_pct >= 7  THEN 'CORE_ASSET (7-10%)'
    ELSE 'THE_STEAL (5-7%)'
  END AS tier,
  COUNT(*) AS N,
  ROUND(AVG(CASE WHEN is_won = 1 THEN 1.0 ELSE 0.0 END) * 100, 1) AS win_rate_pct,
  ROUND(AVG(edge_pct), 1) AS avg_edge
FROM bet_recommendations
WHERE game_date >= date('now', '-14 days')
  AND is_won IS NOT NULL
GROUP BY tier
ORDER BY MIN(edge_pct) DESC;
-- Expect: DIAMOND WR > BLUE_CHIP > CORE_ASSET > STEAL (monotonic correlation)
"

sqlite3 ludi.db "
-- CLV correlation: bets that beat the opening line — do they win more?
-- Note: clv data floor is 2026-02-27, filter ABS(clv_cents) < 200 for clean mean
SELECT
  CASE WHEN clv_cents > 0 THEN 'Beat line (CLV+)' ELSE 'Lost line (CLV-)' END AS clv_direction,
  COUNT(*) AS N,
  ROUND(AVG(CASE WHEN is_won = 1 THEN 1.0 ELSE 0.0 END) * 100, 1) AS win_rate_pct,
  ROUND(AVG(clv_cents), 1) AS avg_clv_cents
FROM bet_recommendations
WHERE game_date >= '2026-02-27'
  AND is_won IS NOT NULL
  AND clv_cents IS NOT NULL
  AND ABS(clv_cents) < 200
GROUP BY clv_direction;
-- Expect: CLV+ bets > 54% WR; CLV- bets < 50% WR
"
```

### Step 4 — Lena Interprets Results

After running all queries and scripts, Lena synthesizes:
- Is scheme cache populated? Are all 4 types present? (Team infra check)
- Is blowout tax reducing volume prop win rates as expected?
- Is any B2B or playtype drift outside ±1.5 pts? Systematic or random noise?
- Are archetype x scheme modifiers non-flat (any `abs(wr - league_avg) > 5%`)? If all flat → data flow issue, not model issue.
- Is edge tier correlation monotonic? If STEAL wins more than DIAMOND → devigging or edge calculation bug.
- Are CLV+ bets outperforming CLV- bets? Validates line shopping strategy.
- Report N and confidence for every finding. N < 20 = "insufficient sample."

---

## Success Criteria

| Metric | Target | Warning | Fail |
|--------|--------|---------|------|
| B2B Mean Error | ±1.0 pts | ±1.0–1.5 pts | >±1.5 pts |
| Hit Rate (overall) | >52% | 50–52% | <50% |
| Modifier Drift | ±1.0 pts | ±1.0–1.5 pts | >±1.5 pts |
| **Sim RMSE — PTS** | **<7.0 pts** | **7.0–10.0 pts** | **>10.0 pts** |
| **Sim RMSE — AST** | **<2.5** | **2.5–4.0** | **>4.0** |
| **Sim RMSE — REB** | **<3.5** | **3.5–5.0** | **>5.0** |
| **Projection mean error** | **±0.5 pts** | **±0.5–1.5 pts** | **>±1.5 pts (systematic bias)** |
| Edge tier correlation | DIAMOND > STEAL WR | Flat across tiers | Inverted |
| CLV+ win rate | >54% | 50–54% | <50% |
| Blowout tax | blowout WR < normal WR | Within 2% | Blowout WR >= normal |
| Scheme cache | All 4 types present | 3 types | <3 types |

---

## Output Format

```
## Backtest Results — [date]

### Tier 1 — Team Games
Scheme cache: [X types] — [PASS/WARNING/FAIL]
canonical_games: [N total games, latest: DATE]
Blowout Tax: normal [X]% WR vs blowout [Y]% WR — [PASS/WARNING/FAIL]
Scheme win rates: BLITZ [X]% | NEUTRAL [X]% | PAINT_PACK [X]% | PERIMETER [X]%

### Tier 2 — Player Games
Test players: [N qualified] (usg >= 0.18, avg_min >= 24)
Sim accuracy (30-day): PTS RMSE [X.X] pts, mean error [±X.X] — [PASS/WARNING/FAIL]
Sim accuracy (30-day): AST RMSE [X.X], REB RMSE [X.X] — [PASS/WARNING/FAIL]
DIAMOND vs STEAL RMSE: DIAMOND [X.X] vs STEAL [X.X] — [expected: DIAMOND lower]
Fatigue Test (21-day): Mean Error [X.X] pts, Hit Rate [X]% — [PASS/WARNING/FAIL]
Playtype Trends (14-day): Drift [X.X] pts — [PASS/WARNING/FAIL]
Top archetype x scheme: [combo, WR X%, N=Y]
Flat modifier warning: [yes/no — signals data flow issue if yes]

### Tier 3 — Bet Outcomes
Edge tier WR: DIAMOND [X]% | BLUE_CHIP [X]% | CORE_ASSET [X]% | STEAL [X]% — [PASS/WARNING/FAIL]
CLV+ bets: [X]% WR on [N] bets (avg CLV: +[X] cents) — [PASS/WARNING/FAIL]

### Lena's Read
[2-3 sentences: calibrated? most actionable finding? anything needing Module E/F attention?]

### Overall Status
[PASS/WARNING/FAIL] — [one-line summary]
```

---

## Post-Backtest Actions

- **PASS**: Report to Solomon "✅ /backtest: All tiers passed"
- **WARNING**: Report "⚠️ /backtest: [Tier X] warning — [specific metrics]"
- **FAIL**: Report "🔴 /backtest: FAILED — [tier + specific metrics needing attention]"

---

## When to Run

- After any model/calibration changes (Module C, E, or F)
- Weekly (Tuesdays via `weekly_validation.yml`)
- Before deploying to production
- When hit rate drops below 52% for 3+ consecutive days
