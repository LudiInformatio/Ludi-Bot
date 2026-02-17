# Player Archetype System Overhaul: Defensive Classification + Synergy Alignment

## Context

Phase 7.9 audited team defensive schemes (93% NEUTRAL -> 23%), team offensive schemes (100% BALANCED -> 47%), and player offensive archetypes (300 reclassified). But **player defensive classification was never specifically audited** — it was only incidentally touched during the bulk reclassify run. The two defensive archetypes (`SCREEN_NAVIGATOR` = 0 players, `ISLAND_DEFENDER` = ~1 player) are effectively dead code. Meanwhile, our `player_synergy_playtypes` table has 1,740 rows of Synergy data that `_assign_secondary_playtypes()` completely ignores, using tracking-data proxies instead.

This matters because:
- STL RMSE is the one failing stat (0.96 vs 0.80 target) — likely tied to misfiring defensive archetypes
- Module F archetype modifiers remain DISABLED pending this audit
- GENERALIST is ~49% of players, meaning half the roster gets zero matchup adjustments
- The backtest showed vs_FUNNEL = -105u at 49.6% WR (TRANSITION +15% too aggressive)

**Goal:** Replace broken defensive archetypes with new Synergy-aligned ones, wire Synergy data into secondary playtypes via hybrid scoring, reduce GENERALIST %, and prepare for defensive Synergy data scraping.

---

## Phase 1: Diagnostic Audit (Day 1)

**Goal:** Establish a clear baseline before changing anything.

### 1A: Run current archetype distribution report
- Query `players.archetype` for full distribution (count per archetype, % of total)
- Query `player_defense` for distribution of `diff_pct` values (histogram buckets: <-5, -5 to -3, -3 to -1, -1 to +1, +1 to +3, >+3)
- Query `player_synergy_playtypes` for coverage: how many of the ~500 active players have Synergy data?
- Count how many players currently get secondary playtypes assigned
- **Output:** `reports/archetype_diagnostic_2026-02-16.md` with tables

### 1B: Identify GENERALIST players who SHOULD have archetypes
- Pull all GENERALIST players and their stats (pts, ast, reb, tpm, usg, stl, blk)
- Cross-reference with `player_synergy_playtypes` to see if Synergy data would classify them
- Identify the "low-hanging fruit" — players clearly fitting an archetype but falling through thresholds

**Files:** `module_e.py` (read), `ludi.db` (query), new report file

---

## Phase 2: New Defensive Archetypes (Days 2-3)

**Goal:** Replace `SCREEN_NAVIGATOR` and `ISLAND_DEFENDER` with Synergy-aligned defensive archetypes that actually fire.

### NBA Synergy Defensive Clustering (Research Basis)

Per [Synergy play type analysis](https://fansided.com/2017/09/08/nylon-calculus-understanding-synergy-play-type-data/) and [defensive play type study](https://www.thestrick.land/strick/a-study-on-defensive-play-type-data), defensive play types cluster into two groups:
- **Interior cluster:** P&R Roll Man defense, ISO defense, Post-Up defense (correlated)
- **Perimeter cluster:** P&R Ball Handler defense, Hand-Off defense, Off-Screen defense (correlated)
- **Spot-Up defense** correlates with all types (general versatility signal)

### New Defensive Archetype Design (5 types, replacing 2)

| Archetype | Signal (Available Now) | Ideal Signal (Phase 4) | What It Means |
|-----------|----------------------|----------------------|---------------|
| `RIM_GUARDIAN` | `diff_pct < -2.0` + `blk > 1.0` + position C/F | Synergy P&R Roll Man def PPP < 0.95 | Elite paint protector — penalizes opponent interior scoring |
| `PERIMETER_HAWK` | `diff_pct < -1.0` + `stl > 1.0` + position G/F | Synergy ISO def PPP < 0.85 | Elite perimeter stopper — penalizes opponent ISO/spot-up |
| `SWITCHABLE_ANCHOR` | `diff_pct < -0.5` + `(stl+blk) > 2.0` + speed > 4.0 | Top 30th percentile in 3+ defensive play types | Can guard multiple positions — versatility signal |
| `HUSTLE_DISRUPTOR` | `stl > 1.5` OR (`stl > 1.0` AND defensive distance > 2.5mi) | High deflections + steals per possession | Creates chaos — boosts TOV generation against sloppy teams |
| `WEAK_LINK` | `diff_pct > 2.0` + `freq_pct > 0.10` (opponents target them often) | Bottom 25th percentile in 2+ defensive categories | Opponents hunt them — boost for opposing scorers in matchups |

### Implementation in `module_e.py`

**2A: Replace SCREEN_NAVIGATOR and ISLAND_DEFENDER in `_assign_unified_archetype()`** (lines 1283-1295)
- Remove old: `SCREEN_NAVIGATOR` and `ISLAND_DEFENDER` checks
- Add new 5-archetype defensive tier with relaxed, data-backed thresholds
- These remain Tier 4 (role players & defenders) in the priority cascade
- **Key change:** Use data from `_load_defense_profiles()` + `_load_hustle_profiles()` + `_load_speed_fatigue_data()` (all already loaded at init)

**2B: Update the matchup matrix** (lines 868-998)
- Remove `SCREEN_NAVIGATOR` and `ISLAND_DEFENDER` matchup rules (lines 974-985)
- Add new matchup rules:

| Archetype | vs Defense | Boost | Rationale |
|-----------|-----------|-------|-----------|
| `RIM_GUARDIAN` | vs FUNNEL | `proj_blk +12%` | Funnel drives into paint protector |
| `RIM_GUARDIAN` | vs BLITZ | `proj_blk +8%, proj_reb +5%` | Help-side blocks on collapsed drives |
| `PERIMETER_HAWK` | vs PERIMETER | `proj_stl +10%` | Switch-everything creates passing lane steals |
| `PERIMETER_HAWK` | vs HACKERS | `proj_stl +8%` | Sloppy ball-handling against active hands |
| `SWITCHABLE_ANCHOR` | vs BLITZ | `proj_stl +8%, proj_blk +5%` | Versatility in pressure schemes |
| `HUSTLE_DISRUPTOR` | vs FUNNEL | `proj_stl +12%` | Transition chaos creates steals |
| `HUSTLE_DISRUPTOR` | vs HACKERS | `proj_stl +10%` | Double disruption |
| `WEAK_LINK` | N/A | (applied to OPPONENT — see 2C) | Not a self-boost |

**2C: Add `_apply_opponent_weak_link_boost()`** — NEW function
- When our player faces a team with a `WEAK_LINK` defender at their position:
  - If our player is ISO_ASSASSIN/SLASHING_CREATOR facing a WEAK_LINK guard: `proj_pts +5%`
  - If our player is WARRIOR_BIG/ROLL_MAN facing a WEAK_LINK big: `proj_pts +5%, proj_reb +5%`
- This flips defensive data to an offensive advantage for the opposing team

**2D: Update `_load_defense_profiles()`** (lines 264-289)
- Instead of mapping both `def_diff_vs_screen` and `def_diff_vs_iso` to the same value, load additional columns:
  - `freq_pct` (how often opponents attack this player)
  - `dfga` (volume of shots contested)
  - Position (for archetype targeting)
- Enrich with speed data from `self.speed_data` and hustle from `self.hustle_profiles`

**Files to modify:** `module_e.py`

---

## Phase 3: Synergy-Powered Secondary Playtypes (Days 3-4)

**Goal:** Use Synergy `freq_pct` as the primary signal for secondary playtype assignment, with tracking data as a weighted fallback.

### 3A: Hybrid scoring model for `_assign_secondary_playtypes()`

Current approach (tracking-only):
```python
iso_criteria = [drives > 8, pu_fga > 4.5, usg > 0.28]  # All proxies
```

New hybrid approach:
```python
# For each playtype, compute a hybrid score:
# score = (synergy_weight * synergy_signal) + (tracking_weight * tracking_signal)
#
# If player has Synergy data: 70% Synergy + 30% tracking
# If player has NO Synergy data: 0% Synergy + 100% tracking (fallback)
```

**Mapping table (Synergy playtype -> secondary playtype -> tracking proxy):**

| Secondary Playtype | Synergy Signal (`freq_pct`) | Tracking Proxy | Threshold |
|--------------------|-----------------------------|----------------|-----------|
| `ISO_SCORER` | `ISO` freq_pct > 8% | drives > 8, pu_fga > 4.5 | hybrid score > 0.6 |
| `P&R_HANDLER` | `PR_BALL_HANDLER` freq_pct > 12% | drives > 5, ast > 6.0 | hybrid score > 0.6 |
| `P&R_ROLL_MAN` | `PR_ROLL_MAN` freq_pct > 8% | rim_freq > 0.40, ast < 3.0 | hybrid score > 0.6 |
| `SPOT_UP` | `SPOT_UP` freq_pct > 12% | cs_fga > 3.5, cs_pct > 0.38 | hybrid score > 0.6 |
| `OFF_BALL_CUTTER` | `CUT` freq_pct > 8% | rim_fg_pct > 0.65, drives < 4 | hybrid score > 0.6 |
| `TRANSITION` | `TRANSITION` freq_pct > 10% | speed > 4.5, distance > 2.3 | hybrid score > 0.6 |
| `PUTBACK` | `PUTBACK` freq_pct > 5% | oreb > 2.2, rim_freq > 0.45 | hybrid score > 0.6 |
| `POST_UP` | `POST_UP` freq_pct > 8% | paint_pts > 10, speed < 4.0 | hybrid score > 0.6 |

### 3B: Add `HANDOFF` and `OFF_SCREEN` secondary playtypes

These are tracked in Synergy but missing from our system:
- `HANDOFF` — Dribble-handoff actions (different from P&R, common for guards running off big screens)
  - Synergy: `HANDOFF` freq_pct > 6%
  - Tracking proxy: cs_fga moderate, speed > 4.0, drives < 5
- `OFF_SCREEN` — Off-ball movement shooters (different from spot-up, involves running off screens)
  - Synergy: `OFF_SCREEN` freq_pct > 5%
  - Tracking proxy: cs_fga > 3.0, distance > 2.5

Add matchup rules:
- `HANDOFF` vs `BLITZ`: `-5% pts` (blitz destroys handoff actions)
- `HANDOFF` vs `PAINT_PACK`: `+8% pts` (drop coverage gives space)
- `OFF_SCREEN` vs `PAINT_PACK`: `+10% 3pm` (help-side late closing)
- `OFF_SCREEN` vs `PERIMETER`: `-5% 3pm` (tight coverage through screens)

### 3C: Load Synergy data in `_assign_secondary_playtypes()`

Currently this function receives `(self, p, tracking_data)`. Change signature to `(self, p, tracking_data, synergy_data)`:
- `synergy_data` comes from `_get_synergy_playtypes(raw_name)` (already called in `_assign_unified_archetype`)
- Pass it down through `calibrate_player()` to avoid duplicate DB queries
- Build `synergy_dict` with `{playtype: freq_pct}` for hybrid scoring

**Files to modify:** `module_e.py`

---

## Phase 4: Defensive Synergy Data Acquisition (Days 5-7)

**Goal:** Scrape per-playtype defensive data from NBA.com to replace the single aggregate `diff_pct`.

### 4A: Extend `sync_synergy_playtypes.py` for defensive data

NBA.com defensive Synergy pages use the same URL structure with `TypeGrouping=Defensive`:
- `https://www.nba.com/stats/players/isolation?TypeGrouping=Defensive`
- `https://www.nba.com/stats/players/ball-handler?TypeGrouping=Defensive`
- `https://www.nba.com/stats/players/roll-man?TypeGrouping=Defensive`
- `https://www.nba.com/stats/players/spot-up?TypeGrouping=Defensive`
- `https://www.nba.com/stats/players/playtype-post-up?TypeGrouping=Defensive`
- `https://www.nba.com/stats/players/cut?TypeGrouping=Defensive`

**New table:** `player_defensive_synergy`
```sql
CREATE TABLE IF NOT EXISTS player_defensive_synergy (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    player_name TEXT NOT NULL,
    team_abbr TEXT,
    season TEXT DEFAULT '2025-26',
    playtype TEXT NOT NULL,     -- ISO, PR_BALL_HANDLER, PR_ROLL_MAN, SPOT_UP, POST_UP, CUT
    games_played INTEGER,
    poss_per_game REAL,
    freq_pct REAL,
    ppp_allowed REAL,           -- Lower = better defender
    fg_pct_allowed REAL,
    percentile INTEGER,         -- Higher = better defender (0-100)
    synced_at TEXT,
    UNIQUE(player_name, playtype, season)
);
```

**Approach:** Reuse existing Ghost Protocol Playwright browser for NBA.com WAF bypass. Add a `--defensive` flag to the scraper. Scrape 6 defensive play types (skip MISC, HANDOFF, OFF_SCREEN, TRANSITION — less meaningful defensively).

### 4B: Upgrade defensive archetypes with real Synergy data

Once `player_defensive_synergy` is populated, upgrade the Phase 2 archetypes:

| Archetype | Phase 2 Signal (proxy) | Phase 4 Signal (Synergy) |
|-----------|----------------------|------------------------|
| `RIM_GUARDIAN` | `diff_pct < -2.0 + blk > 1.0` | P&R Roll Man def percentile >= 75th + Post-Up def percentile >= 70th |
| `PERIMETER_HAWK` | `diff_pct < -1.0 + stl > 1.0` | ISO def percentile >= 75th + Spot-Up def percentile >= 70th |
| `SWITCHABLE_ANCHOR` | `(stl+blk) > 2.0 + speed > 4.0` | Top 40th percentile in 3+ defensive categories |
| `HUSTLE_DISRUPTOR` | `stl > 1.5` | ISO def percentile >= 60th + steals per poss top 20% |
| `WEAK_LINK` | `diff_pct > 2.0 + freq_pct high` | Bottom 30th percentile in 2+ categories |

### 4C: Improve `_apply_defensive_diff_adjustment()` with per-playtype data

Currently targets ALL opponent players equally when facing elite rim protectors. With defensive Synergy data:
- Only penalize `P&R_ROLL_MAN` / `PUTBACK` players when opponent has elite `PR_ROLL_MAN` defender
- Only penalize `ISO_SCORER` players when opponent has elite `ISO` defender
- Only penalize `SPOT_UP` players when opponent has elite `SPOT_UP` defender
- Add FG% penalty alongside PTS penalty for interior scorers

### 4D: Add to workflow schedule

Add defensive Synergy scraping to `ghost_protocol_sync.yml` (Sundays):
- After existing offensive Synergy scrape
- Run `reclassify_player_archetypes.py` after both scrapes complete

**Files to modify:** `scripts/sync_synergy_playtypes.py`, `database.py` (migration), `module_e.py`, `.github/workflows/ghost_protocol_sync.yml`

---

## Phase 5: Reduce GENERALIST + System Sync (Days 7-8)

### 5A: Lower thresholds for underclassified players

Target: GENERALIST < 25% (from ~49%)

Changes to fallback cascade in `_assign_unified_archetype()`:
- `TWO_LEVEL_SCORER` fallback: lower `pts > 15.0` to `pts > 12.0` (bench scorers)
- Add `CONNECTOR` archetype: `ast > 2.5, pts < 12.0, usg < 0.22` — playmaking bench guards
- Add `ENERGY_BIG` archetype: `reb > 4.0, (stl+blk) > 1.0, pts < 10.0, position C/F` — low-usage bigs who contribute defensively
- These get simple matchup rules (CONNECTOR: `+5% ast vs PAINT_PACK`, ENERGY_BIG: `+8% reb vs PERIMETER`)

### 5B: Sync `tag_classifier.py` to new archetype system

`utils/tag_classifier.py` uses the old 8-archetype rules. Update:
- Replace `ARCHETYPE_RULES` with the full 18+ archetype list (16 offensive + new defensive + CONNECTOR + ENERGY_BIG)
- Or better: have it read `players.archetype` from DB instead of re-computing
- Sync `DEFENSIVE_SCHEMES` dict with Module E's `DEFENSIVE_STYLES`

### 5C: Update batch scripts

- `populate_archetypes.py`: Import and call Module E's `_assign_unified_archetype()` instead of duplicating logic
- `scripts/reclassify_player_archetypes.py`: Add defensive tag population
- Fix `archetype_validation_audit.py`: Update to use correct method name `_assign_unified_archetype()`

### 5D: Wire `TeamDefensiveClassifier` into pipeline

`utils/team_defensive_classifier.py` exists but isn't used. In `LudiCalibrator.__init__()`:
- Instantiate classifier, use its output to populate `self.DEFENSIVE_STYLES`
- Keep hardcoded dict as fallback when dynamic classifier returns NEUTRAL (insufficient data)

**Files to modify:** `module_e.py`, `utils/tag_classifier.py`, `populate_archetypes.py`, `scripts/reclassify_player_archetypes.py`

---

## Phase 6: Re-enable Module F + Validate (Days 8-9)

### 6A: Re-enable archetype modifiers in Module F

Per MEMORY.md, Module F archetype modifiers are currently DISABLED. Once phases 1-5 are complete:
- Re-enable archetype-based edge bonuses/penalties in `module_f.py`
- Validate with backtesting before going live

### 6B: Run full reclassification

- Execute `scripts/reclassify_player_archetypes.py` on all ~500 active players
- Generate before/after comparison report
- Validate: GENERALIST < 25%, defensive archetypes > 15%, all 18+ archetypes have at least 1 player

### 6C: Backtest validation

- Run `backtest_archetypes.py` with updated archetypes
- Target: STL RMSE < 0.85 (from 0.96)
- Target: All 7 stat categories passing
- Compare matchup boost firing rate (target: > 60% of players get at least 1 matchup adjustment)

---

## Critical Files

| File | Changes |
|------|---------|
| `module_e.py` | Phases 2-5: New defensive archetypes, hybrid secondary playtypes, matchup matrix, weak link function |
| `scripts/sync_synergy_playtypes.py` | Phase 4: Add defensive Synergy scraping |
| `database.py` | Phase 4: Add `player_defensive_synergy` table migration |
| `utils/tag_classifier.py` | Phase 5: Sync to 18+ archetype system |
| `populate_archetypes.py` | Phase 5: Import Module E logic instead of duplicating |
| `scripts/reclassify_player_archetypes.py` | Phase 5: Add defensive tag population |
| `module_f.py` | Phase 6: Re-enable archetype modifiers |
| `.github/workflows/ghost_protocol_sync.yml` | Phase 4: Add defensive Synergy to Sunday sync |

## Verification

After each phase:
1. Run `scripts/reclassify_player_archetypes.py` and check distribution
2. Run `python -c "from module_e import LudiCalibrator; c = LudiCalibrator(); print('OK')"` — smoke test
3. After Phase 5: Run `backtest_archetypes.py` — all 7 stats should pass
4. After Phase 6: Run `python test_pipeline.py` — full integration test
5. Paper trade for 2-3 game days (Feb 19-21) before enabling in production

Sources:
- [Nylon Calculus: Understanding Synergy Play Type Categories](https://fansided.com/2017/09/08/nylon-calculus-understanding-synergy-play-type-data/)
- [The Strickland: A Study on Defensive Play Type Data](https://www.thestrick.land/strick/a-study-on-defensive-play-type-data)
- [NBA.com Players Pick & Roll Ball Handler](https://www.nba.com/stats/players/ball-handler)
