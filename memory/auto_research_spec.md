# Post-Game Auto-Research System — Joint Spec

**Authors:** Henrik (Code Auditor) + Lena (Data Analyst)
**Date:** March 23, 2026
**Status:** SPEC — pending implementation after Sprint 2 ships
**ROADMAP slot:** Phase 8.29

---

## 1. Overview

Applies the Karpathy auto-research pattern to sports analytics: after games settle overnight, automatically re-simulate yesterday's slate through Module C (`LudiOracle`), compare sim distributions vs actual box scores, and surface systematic drift/patterns. The system interrogates itself daily — no human needed to spot model decay.

**Core principle:** LLMs orchestrate, never calculate. The re-simulation is pure Module C math (10k Poisson iterations). Pattern detection is deterministic SQL over the `projection_residuals` table.

---

## 2. Architecture

**Script:** `scripts/resimulate_yesterday.py`

**Nightly schedule slot:** **1:30 AM EST** — after `db_backup.yml` (1:00 AM) settles CLV + backups, before `empirical_modifiers.yml` (2:30 AM) computes new modifiers.

**Data flow:**
```
canonical_games (yesterday)
  → player_game_logs (L10 pre-game, excluding game date)
  → bet_recommendations (players who had bets)
  → LudiOracle.run_simulation_batch() (10k sims per player)
  → Compare sim output vs actual box scores
  → INSERT INTO projection_residuals
  → Generate daily drift report → Slack #ludi-pipeline-alerts
```

**Scope:** Only re-simulate players who had a `bet_recommendation` for yesterday's games. This keeps compute cost bounded (~20-40 players/night × 10k sims ≈ 200k-400k iterations, <30 seconds).

---

## 3. Anti-Look-Ahead Design (Henrik)

**Rule:** The re-simulation must reconstruct the pre-game state *exactly as it existed before tipoff*. No data from the game being simulated may leak into inputs.

### 3.1 Player Packet Construction

```python
# L10 stats: exclude game_date being re-simmed
SELECT * FROM player_game_logs
WHERE player_name = ? AND game_date < ?  -- strict less-than
ORDER BY game_date DESC LIMIT 10
```

- `FG_PCT`, `FG3_PCT`, `FT_PCT`, `MIN`, `USG_PCT` — all computed from these L10 rows
- If player has <5 games before the re-sim date, use `season_baselines` blend (G2 pattern already in Module C)

### 3.2 Pre-Loaded Dict Snapshots

Module C pre-loads 8 data dicts at `__init__()`:
- `shot_quality_data` — PBP Stats averages (updated weekly, no daily drift risk)
- `rolling_ts_data` — TS% from last 25 games (CTE with ROW_NUMBER)
- `drives_data`, `foul_splits_data` — rolling windows
- `empirical_modifiers` — nightly-computed role/stdev/WOWY
- `season_baselines` — G2 season averages
- `return_status` — G3 injury ramp-up

**Decision:** For Phase 1, accept that pre-loaded dicts reflect *current* state (post-game), not pre-game snapshots. The temporal difference is <24h and these dicts change slowly (25-game windows, weekly syncs). Phase 3 can add temporal snapshots if residual analysis reveals contamination signal.

### 3.3 Edge Cases

| Case | Handling |
|------|----------|
| Player has <5 games before re-sim date | Use G2 season baseline blend (already in Module C) |
| Player's first game of season | Skip — insufficient data for meaningful re-sim |
| DNP (0 minutes) | Skip — not a model failure, lineup decision |
| Blowout (<20 or >20 min vs avg) | Flag in residuals with `is_blowout=1` for separate analysis |

---

## 4. `projection_residuals` Table Schema (Lena)

```sql
CREATE TABLE IF NOT EXISTS projection_residuals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    game_date TEXT NOT NULL,           -- YYYY-MM-DD
    player_name TEXT NOT NULL,
    player_id TEXT,                     -- canonical ID
    stat_category TEXT NOT NULL,        -- PTS, REB, AST, FG3M, STL, BLK, TOV
    projected_mean REAL NOT NULL,       -- Module C sim mean
    projected_stdev REAL,               -- Module C sim stdev (from _distributions)
    projected_p_over REAL,              -- P(over line) from sim
    prop_line REAL,                     -- the line that was bet
    actual_value REAL NOT NULL,         -- actual box score
    residual REAL NOT NULL,             -- projected_mean - actual_value
    z_score REAL,                       -- residual / projected_stdev (NULL if stdev=0)
    archetype TEXT,                     -- player archetype at time of game
    defensive_tag TEXT,                 -- player defensive tag
    matchup_scheme TEXT,                -- opponent defensive scheme
    opponent TEXT,                      -- opponent team abbreviation
    is_home INTEGER,                    -- 1=home, 0=away
    days_rest INTEGER,                  -- rest days before game
    is_blowout INTEGER DEFAULT 0,      -- 1 if minutes <20 or >20 vs avg
    bet_outcome TEXT,                   -- WIN/LOSS/PUSH from bet_recommendations
    season TEXT DEFAULT '2025-26',
    created_at TEXT DEFAULT (datetime('now')),
    UNIQUE(game_date, player_name, stat_category)
);

-- Indexes for common query patterns
CREATE INDEX IF NOT EXISTS idx_proj_res_date ON projection_residuals(game_date);
CREATE INDEX IF NOT EXISTS idx_proj_res_player ON projection_residuals(player_name);
CREATE INDEX IF NOT EXISTS idx_proj_res_archetype_scheme ON projection_residuals(archetype, matchup_scheme);
CREATE INDEX IF NOT EXISTS idx_proj_res_stat ON projection_residuals(stat_category);
CREATE INDEX IF NOT EXISTS idx_proj_res_season ON projection_residuals(season);
```

**Retention policy:** Keep all rows for current season. Archive to `archives/data/` at season rollover (same pattern as `ludi.db` archive plan).

---

## 5. Statistical Significance Framework (Lena)

### 5.1 N-Gates (Minimum Sample Sizes)

| Analysis Type | Minimum N | Confidence Level |
|--------------|-----------|-----------------|
| Player-level drift | N >= 10 games | HIGH if N >= 20, MEDIUM if N >= 10 |
| Archetype-level RMSE | N >= 30 player-games | HIGH if N >= 50 |
| Archetype × Scheme drift | N >= 15 matchups | MEDIUM (rare combos may never reach HIGH) |
| Stat-specific bias | N >= 20 per stat | HIGH if N >= 40 |
| 7-day rolling window | N >= 5 games in window | LOW (early warning only) |

### 5.2 z-Score Interpretation

| |z-score| Range | Label | Action |
|------------------|-------|--------|
| 0.0 – 1.0 | NORMAL | No action — expected variance |
| 1.0 – 1.5 | MILD | Log only — within 1.5 stdev |
| 1.5 – 2.0 | ELEVATED | Flag in drift report if pattern persists 3+ games |
| 2.0 – 3.0 | SIGNIFICANT | Include in Top 3 misses, investigate root cause |
| > 3.0 | EXTREME | Immediate flag — likely model error, stale line, or blowout |

### 5.3 Drift Detection Thresholds

| Metric | Threshold | Window | Action |
|--------|-----------|--------|--------|
| Archetype RMSE (PTS) | > 7.5 | 7-day rolling | Flag in drift report |
| Archetype × Scheme bias | > 2.0 PTS mean residual | 7-day rolling, N >= 5 | Flag modifier drift |
| Stat-specific bias | > 1.5 mean residual | 14-day rolling, N >= 10 | Flag systematic over/under |
| Blowout contamination | > 30% of residuals are `is_blowout=1` | 7-day | Exclude blowouts from drift calc |

---

## 6. Daily Drift Report

**Format:** Machine-parseable markdown (agent-first standard).

```markdown
## Auto-Research Report — [YYYY-MM-DD]

### Games Re-Simulated
- Games: [N] | Players: [N] | Stat-lines: [N]

### Top 3 Misses (by |z_score|)
1. [Player] [STAT] — Projected: [X.X] | Actual: [Y] | z=[Z.ZZ] | [ARCHETYPE] vs [SCHEME] | Tag: [ROOT_CAUSE]
2. ...
3. ...

### Archetype RMSE (7-Day Rolling)
| Archetype | PTS RMSE | REB RMSE | AST RMSE | N | Status |
|-----------|----------|----------|----------|---|--------|
| [name] | [X.X] | [X.X] | [X.X] | [N] | [ON_TRACK/DRIFT] |

### Modifier Drift Flags
[Archetype × Scheme pairs with mean residual > 2.0 PTS over 7 days — or "None"]

### Mean Residual by Stat
| Stat | Mean Residual | N | Bias Direction |
|------|--------------|---|----------------|
| PTS | [+/-X.X] | [N] | [OVER/UNDER/NEUTRAL] |

### Status: [CLEAN | DRIFT_DETECTED | REVIEW_NEEDED]
```

**Root cause tags** for Top 3 misses:
- `BLOWOUT` — minutes <20 or >20 vs avg
- `INJURY_RETURN` — first 3 games back from injury
- `MATCHUP_DRIFT` — archetype × scheme modifier appears off
- `PACE_MISMATCH` — actual game pace >> or << projected
- `ROLE_CHANGE` — starter/bench role changed mid-week
- `UNKNOWN` — no obvious root cause

---

## 7. Feedback Loop Design

### 7.1 Residuals → `player_empirical_modifiers`

**Phase 3 enhancement:** If `projection_residuals` shows consistent stat-specific bias for an archetype × scheme pair (N >= 15, mean residual > 2.0, sustained for 14+ days), flag for owner review as a potential modifier adjustment.

**Auto-adjust threshold:** NEVER auto-adjust modifiers. All modifier changes require owner sign-off (per Decision Authority Matrix in `COMMUNICATION_PROTOCOL.md`). The auto-research system *surfaces* drift — it does not *fix* it.

### 7.2 Residuals → `calibrate_claude_outputs.py`

Connect re-sim P(Over) distributions to Brier score calibration:
- `projected_p_over` from re-sim vs `bet_outcome` (WIN/LOSS) → feeds Brier score
- Compare Brier score from re-sim P(Over) vs original pipeline P(Over) stored in `bet_recommendations`
- If re-sim Brier < original Brier → suggests sim engine is well-calibrated but curation (Claude) is adding noise
- If re-sim Brier > original Brier → suggests original pipeline had better calibration data

### 7.3 Residuals → Weekly Review

`/weekly-review` skill should pull 7-day rolling RMSE from `projection_residuals` if table exists. Add to Model Performance section.

---

## 8. GH Actions Workflow

**File:** `.github/workflows/auto_research.yml`

```yaml
name: Auto-Research Re-Simulation
on:
  schedule:
    - cron: '30 6 * * *'  # 1:30 AM EST (UTC-5) / 6:30 UTC
  workflow_dispatch:       # manual trigger

jobs:
  resimulate:
    runs-on: self-hosted
    steps:
      - uses: actions/checkout@v4
      - name: Run re-simulation
        run: |
          source .venv/bin/activate
          python scripts/resimulate_yesterday.py --verbose
        env:
          IS_SELF_HOSTED: 'true'
```

**Dependencies:**
- Runs AFTER: `db_backup.yml` (1:00 AM) — needs settled outcomes + CLV
- Runs BEFORE: `empirical_modifiers.yml` (2:30 AM) — residuals may inform modifier compute
- On failure: log to Slack `#ludi-pipeline-alerts` via `SLACK_WEBHOOK_ALERTS`

---

## 9. Implementation Phases

### Phase 1: Script + Table + Basic Residuals (1 session)
- Create `projection_residuals` table in `database.py`
- Build `scripts/resimulate_yesterday.py`:
  - Query `canonical_games` for yesterday
  - Build anti-look-ahead player packets
  - Call `LudiOracle.run_simulation_batch()`
  - Compare vs `player_game_logs` actuals
  - INSERT residuals
- Manual run and verify

### Phase 2: Drift Report + GH Action (1 session)
- Add daily drift report generation (markdown to `reports/auto_research/`)
- Wire `auto_research.yml` GH Action at 1:30 AM
- Add Slack notification on DRIFT_DETECTED status
- Wire 7-day RMSE into `/weekly-review` skill

### Phase 3: Feedback Loop + Brier Integration (needs Henrik audit)
- Connect residuals to `calibrate_claude_outputs.py` Brier score
- Add drift flag → GitHub Issue auto-creation for owner review
- Evaluate temporal snapshots for pre-loaded dicts (if Phase 1-2 residuals show contamination)

---

## 10. Risks & Mitigations

| Risk | Severity | Mitigation |
|------|----------|------------|
| Look-ahead contamination | HIGH | Strict `game_date < ?` in L10 query. Phase 1 accepts dict temporal drift (<24h). Phase 3 adds snapshots if needed. |
| Module C performance | LOW | Only re-sim players with bets (~20-40/night). 10k sims × 40 players ≈ 400k iterations, <30s on self-hosted runner. |
| Storage growth | LOW | ~7 stats × 40 players × 180 game-days = ~50k rows/season. Negligible vs `player_game_logs` (10k+). |
| False drift signals | MEDIUM | N-gates + rolling windows prevent premature flagging. Blowout filter prevents score-based contamination. |
| Modifier auto-adjustment | HIGH | Explicitly prohibited. All modifier changes require owner sign-off. System surfaces, never fixes. |

---

## Sign-Off

- **Henrik (Code Auditor):** Architecture review — anti-look-ahead design, Module C callability, GH Actions slot. APPROVED pending implementation review.
- **Lena (Data Analyst):** Statistical framework — N-gates, z-score thresholds, drift detection, Brier integration. APPROVED with note: revisit thresholds after 30 days of data accumulation.
