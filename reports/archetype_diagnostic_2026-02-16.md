# Archetype Diagnostic Report

Date: 2026-02-16
Phase: 1 (Diagnostic Audit)
Source: `ludi.db` + live `module_e.py` assignment logic

## 1) Active Archetype Distribution

Active players: 503

| Archetype | Count | Percent |
|---|---:|---:|
| GENERALIST | 236 | 46.9% |
| CUTTER_SPECIALIST | 76 | 15.1% |
| FACILITATOR | 44 | 8.7% |
| SNIPER_ELITE | 33 | 6.6% |
| TWO_LEVEL_SCORER | 28 | 5.6% |
| NULL | 21 | 4.2% |
| HELIOCENTRIC_MAESTRO | 14 | 2.8% |
| ROLL_MAN | 13 | 2.6% |
| WARRIOR_BIG | 12 | 2.4% |
| STRETCH_BIG | 9 | 1.8% |
| SLASHING_CREATOR | 5 | 1.0% |
| JUMBO_FACILITATOR | 5 | 1.0% |
| TWO_WAY_WING | 3 | 0.6% |
| HUB_BIG | 2 | 0.4% |
| ISO_ASSASSIN | 1 | 0.2% |
| ATHLETIC_FINISHER | 1 | 0.2% |

Observation: `GENERALIST` is the dominant class at 46.9%, close to the plan baseline (~49%).

## 2) Defensive Differential Distribution (`player_defense.diff_pct`)

Rows with non-null `diff_pct` in `player_defense` (season 2025-26): 546

| Bucket | Count |
|---|---:|
| < -5 | 1 |
| -5 to -3 | 1 |
| -3 to -1 | 2 |
| -1 to +1 | 538 |
| +1 to +3 | 1 |
| > +3 | 3 |

Observation: The aggregate defensive proxy is almost fully concentrated around neutral values (`-1 to +1`), confirming poor separation for defensive archetype triggers.

## 3) Synergy Coverage (`player_synergy_playtypes`)

- Total active players: 503
- Active players with Synergy rows: 357
- Coverage: 71.0%
- Total Synergy rows in table: 2,740
- Distinct players in Synergy table: 405

Observation: Coverage is strong enough to support Synergy-first logic with fallback behavior.

## 4) Secondary Playtype Coverage (Current Tracking-Only Path)

Computed using live Module E (`_assign_secondary_playtypes`) over active players:

- Active players evaluated: 503
- Players with tracking profile data: 433
- Players assigned at least one secondary playtype: 383
- Assignment rate (all active): 76.1%
- Assignment rate (tracking-eligible): 88.5%

Observation: Secondary tags are firing, but they are generated from tracking proxies and do not use the Synergy frequencies already available.

## 5) GENERALIST Audit: Low-Hanging Candidates

The following GENERALIST players already show clear Synergy signals that map to existing playtype logic and should be easier to reclassify with hybrid scoring and relaxed fallback thresholds.

| Player | Team | Pos | PTS | AST | REB | 3PM | STL | BLK | USG | Signal |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| Thomas Bryant | CLE | C | 5.0 | 0.5 | 2.8 | 0.6 | 0.2 | 0.4 | 0.204 | SPOT_UP signal |
| Bones Hyland | MIN | G | 6.9 | 2.4 | 1.6 | 1.3 | 0.6 | 0.2 | 0.221 | PNR_HANDLER signal |
| Devin Carter | SAC | G | 5.3 | 1.7 | 1.9 | 0.5 | 0.6 | 0.2 | 0.253 | PNR_HANDLER signal |
| Grant Williams | CHA | F | 6.4 | 1.6 | 4.0 | 1.0 | 0.4 | 0.3 | 0.173 | SPOT_UP signal |
| Ace Bailey | UTA | G | 11.2 | 1.6 | 3.6 | 1.5 | 0.8 | 0.4 | 0.222 | SPOT_UP signal |
| Craig Porter Jr. | CLE | G | 4.7 | 2.9 | 3.4 | 0.5 | 1.0 | 0.6 | 0.141 | PNR_HANDLER signal |
| Tyler Kolek | NYK | UNK | 5.1 | 3.0 | 1.9 | 0.7 | 0.4 | 0.1 | 0.207 | PNR_HANDLER signal |
| Collin Sexton | CHI | UNK | 14.7 | 3.9 | 2.1 | 1.3 | 0.8 | 0.2 | 0.291 | PNR_HANDLER signal |
| Brook Lopez | LAC | C | 6.9 | 0.9 | 2.7 | 1.5 | 0.5 | 1.0 | 0.191 | PNR_ROLL_MAN signal |
| Tre Mann | CHA | G | 7.5 | 2.3 | 2.5 | 1.3 | 0.5 | 0.1 | 0.268 | PNR_HANDLER signal |
| Jaylin Williams | OKC | F | 6.0 | 2.5 | 4.8 | 1.2 | 0.6 | 0.6 | 0.170 | PNR_ROLL_MAN signal |
| Jay Huff | IND | C | 8.3 | 1.3 | 3.8 | 1.3 | 0.5 | 2.1 | 0.193 | PNR_ROLL_MAN signal |
| Jalen Smith | CHI | F | 9.7 | 1.3 | 6.6 | 1.5 | 0.4 | 0.8 | 0.223 | PNR_ROLL_MAN signal |
| Bennedict Mathurin | LAC | UNK | 17.9 | 2.2 | 5.4 | 2.1 | 0.7 | 0.2 | 0.262 | PNR_HANDLER signal |
| Jordan Miller | LAC | G | 8.2 | 1.5 | 3.1 | 0.7 | 0.6 | 0.2 | 0.200 | CUTTER signal |

Observation: Many GENERALIST players have meaningful Synergy signals now. This supports Phase 3 hybrid scoring and Phase 5 fallback changes.

## 6) Baseline Targets for Later Phases

- Lower GENERALIST from 46.9% to less than 25%
- Replace dead defensive archetypes with five active defensive types
- Keep Synergy coverage-aware fallback path for players without Synergy rows
- Move secondary tags to Synergy-led hybrid scoring
