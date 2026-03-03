# Decision Engine — Full Architecture Spec

**Status:** Future Sprint (post Workflow Audit Sprint 2)
**Created:** March 3, 2026
**Scope:** Unified decision-making layer for simulations, scenarios, and bet recommendations

---

## Problem Statement

The pipeline makes every decision correctly but makes them **scattered across 5 files with no
hierarchy, audit trail, or conflict resolution**. Signals that are computed independently
(ramp-up in Module C, tier in Module F) cannot talk to each other, producing contradictions
like: Game 1 return player + hot streak = DIAMOND tier, even though the underlying projection
is at 70% of baseline.

### Current Decision Logic — Where It Lives

| Decision | File | Location | Issue |
|----------|------|----------|-------|
| Skip OUT players (pre-sim) | `module_c.py` | L389 | Duplicate of Module F L260 |
| G3 injury ramp-up modifier | `module_c.py` | L414-427 | Applied IN PLACE — double fires when player in multiple scenarios |
| Season baseline blend (G2) | `module_c.py` | L392-411 | Implicit order within sim loop |
| Fork this player? (USG/MIN gate) | `module_x_scenario.py` | L500-503 | Hardcoded thresholds |
| Vacuum scale (days out) | `module_x_scenario.py` | `_classify_vacuum_smart()` | Hardcoded thresholds |
| Skip OUT players (pre-bet) | `module_f.py` | L260 | Duplicate of Module C |
| Blowout tax | `module_f.py` | L271-276 | Applied in same loop as edge calc |
| STRUCTURAL_LOSERS filter | `module_f.py` | L408 | After blowout tax, after edge calc |
| Stat edge minimums | `module_f.py` | L412-413 | No hierarchy relative to above |
| 8-signal confidence score | `module_f.py` | L975-1108 | Doesn't know ramp-up was applied |
| Tier assignment | `module_f.py` | L993-1108 | No conflict resolution |
| AI sanity gate | `scripts/curate_plays.py` | L162-265 | Post-pipeline, can't prevent bets |

---

## Architecture: `utils/decision_engine.py`

```
DecisionEngine
├── SimDecisionTree       → consulted by module_c.py before each player's simulation
├── ScenarioDecisionTree  → consulted by module_x_scenario.py before forking
└── BetDecisionTree       → consulted by module_f.py before generating each bet
```

Single instantiation in `main.py`, passed by reference to all three modules.

---

## Part 1 — `DecisionContext` (Shared Data Bag)

Passed through all three layers. Filled incrementally as pipeline progresses.

```python
@dataclass
class DecisionContext:
    player_name: str
    player_id: str
    team: str
    opponent: str
    status: str                    # ACTIVE / GTD / DOUBTFUL / OUT
    scenario_name: str             # BASE / WITHOUT [Player]
    games_since_return: int | None # G3 ramp-up tier (1–5)
    spread: float
    total: float
    base_min: float
    base_usg: float
    wowy_confidence: str | None    # high / medium / low
    archetype: str
    source_quality: str            # ODDS_API / BDL_FALLBACK
    edge: float                    # computed in BetDecisionTree after all modifiers
    confidence_score: float        # 8-signal weighted sum from module_f.py
    is_b2b: bool                   # back-to-back flag
    days_out: int | None           # from Module X (for beneficiary scenarios)
    blowout_mult: float            # computed by BetDecisionTree
    audit_log: list[str]           # each layer appends its decisions here
```

---

## Part 2 — `SimDecisionTree`

**Purpose:** Owns the modifier application sequence. Replaces the implicit order
currently embedded in `run_simulation_batch()`. Modules C calls this instead of
applying modifiers inline.

### Modifier Sequence (explicit, ordered, documented)

```python
MODIFIER_SEQUENCE = [
    'g2_season_blend',     # Thin-sample confidence: <15 recent games → blend with season avg
    'g3_injury_ramp_up',   # Game 1-4 back from 7+ day absence → 62.5%/75%/87.5%/100%
    'conditional_mods',    # From Module X: H/A split, starter/bench, lineup-conditional
    'fatigue_tax',         # B2B (-4%) or rest rust (≥4 days, -6%)
    'referee_pace',        # Crew pace impact (Module G)
    'referee_whistle',     # FTA-only whistle tendency (Module G)
    # NOTE: efficiency_modifier and drives_boost are outcome-stage (not volume-stage)
    # and stay in Module C's _simulate_outcomes()
]
```

### Pre-Sim Gate

```python
def pre_sim_gate(self, ctx: DecisionContext) -> tuple[bool, str]:
    """Returns (skip, reason). Called before any modifiers run."""
    if ctx.status in ('OUT', 'DOUBTFUL'):
        return True, f"status={ctx.status}"
    if ctx.base_min == 0:
        return True, "base_min=0 (did not play)"
    return False, ""
```

### Module C Integration Point

```python
# module_c.py run_simulation_batch() — replace inline modifier block with:
skip, reason = decision_engine.sim_tree.pre_sim_gate(ctx)
if skip:
    ctx.audit_log.append(f"SIM SKIP: {reason}")
    continue

mod_stack = decision_engine.sim_tree.build_modifier_stack(ctx, player)
# mod_stack consumed by _simulate_volume() and _simulate_outcomes()
```

---

## Part 3 — `ScenarioDecisionTree`

**Purpose:** Externalizes fork criteria and vacuum scale thresholds from Module X
hardcoded constants. Makes them tunable without touching the sim engine.

### Configurable Thresholds

```python
# Currently hardcoded in module_x_scenario.py — extract to ScenarioDecisionTree
FORK_MIN_USG = 0.18
FORK_MIN_MIN = 24.0
FORK_STATUSES = {'Q', 'GTD'}

VACUUM_FULL_DAYS = 3       # ≤3 days out → 100% vacuum (team hasn't adjusted)
VACUUM_ZERO_DAYS = 14      # >14 days out → 0% (team fully adjusted)
```

### Should-Fork Gate

```python
def should_fork(self, ctx: DecisionContext) -> tuple[bool, str]:
    if ctx.base_usg < self.FORK_MIN_USG: return False, f"usg={ctx.base_usg:.2f} < {self.FORK_MIN_USG}"
    if ctx.base_min < self.FORK_MIN_MIN: return False, f"min={ctx.base_min:.1f} < {self.FORK_MIN_MIN}"
    if ctx.status not in self.FORK_STATUSES: return False, f"status={ctx.status}"
    return True, f"fork: usg={ctx.base_usg:.2f}, min={ctx.base_min:.1f}"
```

### Scenario Validity Pre-Flight (NEW — doesn't exist today)

Before generating bets from a "WITHOUT [Player Y]" scenario, check if Player Y
is actually out. If Player Y is ACTIVE in the live injury table, all "WITHOUT Y"
bets are phantom — generated from a scenario that won't occur.

```python
def validate_scenario(self, scenario_name: str, live_injury_status: dict) -> bool:
    """Returns False if a WITHOUT scenario's star is actually playing."""
    if not scenario_name.startswith('WITHOUT '):
        return True  # BASE scenario always valid
    out_player = scenario_name.replace('WITHOUT ', '')
    current_status = live_injury_status.get(out_player, 'ACTIVE')
    if current_status not in ('OUT', 'DOUBTFUL'):
        return False  # Star is playing — scenario is phantom
    return True
```

---

## Part 4 — `BetDecisionTree`

**Purpose:** Replaces the flat scattered filter chain in `module_f.py:generate_report()`.
Five explicit layers with early termination at hard gates.

### Layer Architecture

```
L0  Hard Eliminators    → ANY condition = reject (no scoring, no processing)
L2  Contextual Mods     → Apply once, in order: blowout_tax → wowy_penalty → edge_dampening
L3  Edge Gate           → edge < stat_minimum → reject
L4  Conflict Resolution → ramp-up, GTD, WOWY-low, B2B, thin-market, contra-signal
L5  Tier Assignment     → base_tier (edge) + confidence_adj + ceiling_enforcement
```

*(L1 is intentionally reserved for projection adjustments owned by SimDecisionTree —
by the time BetDecisionTree runs, projections are already module-adjusted)*

### L0 — Hard Eliminators

```python
HARD_ELIMINATORS = [
    lambda ctx, stat, dir: ctx.status == 'OUT',                           # OUT player
    lambda ctx, stat, dir: (stat, dir) in STRUCTURAL_LOSERS,              # statistical losers
    lambda ctx, stat, dir: stat == 'reb' and dir == 'over',               # REB OVER
    lambda ctx, stat, dir: stat in ('blk', 'blocks') and dir == 'over',  # BLK OVER
    lambda ctx, stat, dir: ctx.source_quality == 'BDL_FALLBACK' and      # BDL gap sanity
                           abs(proj - line) / max(proj, 0.01) > 0.40,
]
```

### L4 — Conflict Resolution (THE NEW BEHAVIOR)

Returns a `tier_ceiling` integer (3=DIAMOND, 2=BLUE CHIP, 1=CORE ASSET, 0=THE STEAL).
Tier assignment in L5 cannot exceed the ceiling set here.

| Conflict | Condition | Ceiling | Audit Log Entry |
|----------|-----------|---------|-----------------|
| Ramp-up Game 1-2 | `games_since_return in (1, 2)` | BLUE CHIP | `ramp_up(game N) caps at BLUE CHIP` |
| Ramp-up Game 3 | `games_since_return == 3` | DIAMOND (allow, log) | `ramp_up(game 3) — 87.5% projection` |
| GTD + high edge | `status in ('GTD','Q') and edge ≥ 15%` | BLUE CHIP | `GTD_RISK caps at BLUE CHIP` |
| WOWY low | `wowy_confidence == 'low' and edge ≥ 15%` | BLUE CHIP | `wowy_low caps at BLUE CHIP` |
| B2B fatigue | `is_b2b and edge ≥ 15%` | BLUE CHIP | `b2b_fatigue caps at BLUE CHIP` |
| Thin market | `source_quality == 'BDL_FALLBACK'` | CORE ASSET | `thin_market caps at CORE ASSET` |
| BENEFICIARY + low WOWY | `scenario != 'BASE' and wowy_confidence == 'low'` | CORE ASSET | `beneficiary_low_wowy caps at CORE ASSET` |
| Suspicious edge | `edge > 20%` | BLUE CHIP | `VERIFY_LINE — edge > 20%` |
| DIAMOND confidence floor | `edge ≥ 15% and confidence_score < 0.65` | BLUE CHIP | `confidence_floor — score < 0.65` |

### Conflict Resolution Code Sketch

```python
def _resolve_conflicts(self, ctx: DecisionContext, edge: float) -> int:
    ceiling = 3  # start at DIAMOND

    if ctx.games_since_return in (1, 2):
        ceiling = min(ceiling, 2)
        ctx.audit_log.append(f"L4: ramp_up(game {ctx.games_since_return}) → ceiling=BLUE CHIP")

    if ctx.status in ('GTD', 'Q') and edge >= 15.0:
        ceiling = min(ceiling, 2)
        ctx.audit_log.append("L4: GTD_RISK → ceiling=BLUE CHIP")

    if ctx.wowy_confidence == 'low' and edge >= 15.0:
        ceiling = min(ceiling, 2)
        ctx.audit_log.append("L4: wowy_low → ceiling=BLUE CHIP")

    if ctx.is_b2b and edge >= 15.0:
        ceiling = min(ceiling, 2)
        ctx.audit_log.append("L4: b2b_fatigue → ceiling=BLUE CHIP")

    if ctx.source_quality == 'BDL_FALLBACK':
        ceiling = min(ceiling, 1)
        ctx.audit_log.append("L4: thin_market(BDL_FALLBACK) → ceiling=CORE ASSET")

    if ctx.scenario_name != 'BASE' and ctx.wowy_confidence == 'low':
        ceiling = min(ceiling, 1)
        ctx.audit_log.append("L4: beneficiary_low_wowy → ceiling=CORE ASSET")

    if edge > 20.0:
        ceiling = min(ceiling, 2)
        ctx.audit_log.append(f"L4: VERIFY_LINE edge={edge:.1f}% → ceiling=BLUE CHIP")

    if edge >= 15.0 and ctx.confidence_score < 0.65:
        ceiling = min(ceiling, 2)
        ctx.audit_log.append(f"L4: confidence_floor score={ctx.confidence_score:.2f} → ceiling=BLUE CHIP")

    return ceiling
```

---

## Part 5 — Cross-Stat Correlation Detection (NEW)

Not currently handled anywhere. When two or more bets are accepted for the same player
from the same scenario, they're highly correlated (the same simulation produced both).

**Detection rule:** Two bets from same `(player_name, scenario_name)` pair where both are OVER
and both stats are volume-driven (PTS + AST, PTS + REB, PTS + FGA) → flag as correlated.

**Handling options (pick one at implementation time):**
- A: Keep highest-edge bet only (simpler, conservative)
- B: Keep both but halve unit size on each (allows correlated SGP capture)
- C: Flag with `CORRELATED_SGP` tag, no unit change (informational)

Recommendation: Option C for first version — adds signal without removing bets, lets
the user decide via curate_plays.py Sonnet gate.

```python
def detect_correlated_bets(self, accepted_bets: list[BetDecision]) -> list[BetDecision]:
    """Flag bets where same player has multiple volume-OVER in same scenario."""
    VOLUME_STATS = {'pts', 'reb', 'ast', 'fga', 'fta', 'pra', 'pa', 'pr', 'ra'}
    player_scenario_overs = defaultdict(list)
    for bet in accepted_bets:
        if bet.direction == 'over' and bet.stat in VOLUME_STATS:
            player_scenario_overs[(bet.player_name, bet.scenario)].append(bet)
    for key, bets in player_scenario_overs.items():
        if len(bets) >= 2:
            for bet in bets:
                bet.tags.add('CORRELATED_SGP')
                bet.ctx.audit_log.append(f"L5: CORRELATED_SGP with {[b.stat for b in bets]}")
    return accepted_bets
```

---

## Part 6 — Audit Trail Column

New column `decision_log TEXT` in `bet_recommendations` (migration-safe ALTER TABLE).
Module F logs `' | '.join(ctx.audit_log)` for every accepted and every rejected bet
(rejected bets logged at DEBUG level only — not written to DB).

```sql
ALTER TABLE bet_recommendations ADD COLUMN decision_log TEXT;
```

Example stored value for an accepted bet:
```
"L0: PASS | SIM: g3_injury_ramp_up 0.70x | SIM: fatigue_tax 0.98x |
L3: edge=9.2% PASS (min=8.0%) | L4: ramp_up(game 1) → ceiling=BLUE CHIP |
L5: ACCEPT — BLUE CHIP (base=DIAMOND, conf_adj=+0, ceiling=BLUE CHIP)"
```

This enables post-hoc queries like:
```sql
-- All bets where conflict resolution changed the tier
SELECT player_name, confidence_tier, decision_log
FROM bet_recommendations
WHERE decision_log LIKE '%ceiling=%'
AND game_date >= date('now', '-7 days');
```

---

## Implementation Sequence

1. **`utils/decision_engine.py`** — `DecisionContext` + all three trees (~350 lines)
2. **`module_f.py`** — Wire `BetDecisionTree` — replaces scattered filter chain, adds L4 conflict resolution
3. **`module_c.py`** — Wire `SimDecisionTree` — modifier stack formalization
4. **`module_x_scenario.py`** — Wire `ScenarioDecisionTree` — threshold extraction + scenario validity pre-flight
5. **`main.py`** — Single `DecisionEngine` instantiation, pass to all modules
6. **`database.py`** — Add `decision_log` migration

**Backward compatibility:** All modules check `if hasattr(self, 'decision_engine')` —
safe fallback to existing logic if engine not wired. Tests don't break.

---

## Verification

```bash
# Import sanity check
.venv/bin/python -c "from utils.decision_engine import DecisionEngine; print('OK')"

# Ramp-up player capped at BLUE CHIP max
sqlite3 ludi.db "
  SELECT player_name, confidence_tier, decision_log
  FROM bet_recommendations
  WHERE game_date = date('now')
    AND decision_log LIKE '%ramp_up%'
    AND confidence_tier = 'DIAMOND';"
# Expected: 0 rows

# Audit trail populated
sqlite3 ludi.db "
  SELECT player_name, confidence_tier, substr(decision_log, 1, 120)
  FROM bet_recommendations
  WHERE game_date = date('now')
    AND decision_log IS NOT NULL
  LIMIT 5;"

# Cross-stat correlation detection
sqlite3 ludi.db "
  SELECT player_name, tags FROM bet_recommendations
  WHERE game_date = date('now')
    AND tags LIKE '%CORRELATED_SGP%';"
```

---

## Notes & Open Questions

1. **Stat calibration factors** (`_STAT_EDGE_CALIBRATION` in module_f.py) — should these move
   into the decision engine or stay in Module F? They're calibration math, not decision logic.
   Recommendation: leave in Module F for now, move in Phase 2.

2. **curate_plays.py relationship** — the Haiku sanity gate (Stage 1) overlaps with L0 hard
   eliminators. Once BetDecisionTree is live, Stage 1 may become redundant for injury checks.
   Consider removing Haiku gate (save ~$0.005/day) and relying on L0 + L4 conflict detection.

3. **Scenario validity pre-flight timing** — Module X runs before Module D's final injury check
   in `main.py`. The scenario validity check needs live injury status from Module D. Consider
   wiring it as a post-Module D sweep rather than inside ScenarioDecisionTree.

4. **Contra-signal detection** (line movement against our bet direction) — requires
   `prop_line_snapshots` opening line vs current line comparison. `capture_closing_lines.py`
   captures these post-game, but intraday line movement is not tracked yet. Phase 2 feature.
