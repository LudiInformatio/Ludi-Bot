# Archetype Audit Report — 2026-02-17

Generated: 2026-02-17 12:52:11

## Dependency Check

- Required tables present: player_defense, player_defensive_synergy, player_game_tracking, player_speed
- player_game_tracking: 14152 rows, max date 2026-02-12
- tracking nonzero last 30 days: catch_shoot_3pa=3183, drives_fga=2724, avg_defender_dist=3882
- player_defensive_synergy: 1751 rows, max synced_at 2026-02-17T11:38:32.454182
- player_defense: 546 rows, max synced_at 2026-02-17T04:22:02.557181
- player_speed: 550 rows, max synced_at 2026-02-17T04:22:06.924003

## Fix Summary

- Active players: 503
- NULL archetypes: 0
- GENERALIST count: 120 (23.9%)
- Defensive tags populated: 2

## Part A — Team Defensive Schemes

### Static vs Dynamic (mapped) disagreements

| Team | Static | Dynamic Raw | Dynamic Mapped |
| --- | --- | --- | --- |
| ATL | NEUTRAL | SWITCH_HEAVY | PERIMETER |
| CHI | NEUTRAL | RIM_FORTRESS | PAINT_PACK |
| DAL | PERIMETER | DROP_COVERAGE | PAINT_PACK |
| DEN | PERIMETER | NEUTRAL | NEUTRAL |
| GSW | PAINT_PACK | SWITCH_HEAVY | PERIMETER |
| HOU | BLITZ | NEUTRAL | NEUTRAL |
| LAC | NEUTRAL | RIM_FORTRESS | PAINT_PACK |
| MIA | NEUTRAL | RIM_FORTRESS | PAINT_PACK |
| MIL | BLITZ | NEUTRAL | NEUTRAL |
| NOP | PAINT_PACK | SWITCH_HEAVY | PERIMETER |
| NYK | NEUTRAL | RIM_FORTRESS | PAINT_PACK |
| OKC | PAINT_PACK | SWITCH_HEAVY | PERIMETER |
| PHI | PERIMETER | ZONE_FLUID | BLITZ |
| PHX | NEUTRAL | SWITCH_HEAVY | PERIMETER |
| POR | PERIMETER | NEUTRAL | NEUTRAL |
| SAC | PERIMETER | NEUTRAL | NEUTRAL |
| SAS | NEUTRAL | RIM_FORTRESS | PAINT_PACK |
| TOR | PAINT_PACK | SWITCH_HEAVY | PERIMETER |
| WAS | PERIMETER | NEUTRAL | NEUTRAL |

### Distribution

**Static:** BLITZ: 2, NEUTRAL: 10, PAINT_PACK: 8, PERIMETER: 10
**Dynamic (mapped):** BLITZ: 1, NEUTRAL: 9, PAINT_PACK: 10, PERIMETER: 10

### Key Teams (DET/BKN/DEN)

- DET: static=PERIMETER, dynamic_raw=SWITCH_HEAVY, dynamic_mapped=PERIMETER
- BKN: static=PERIMETER, dynamic_raw=SWITCH_HEAVY, dynamic_mapped=PERIMETER
- DEN: static=PERIMETER, dynamic_raw=NEUTRAL, dynamic_mapped=NEUTRAL

## Part B — Player Spot Check (Top 50 by Minutes)

No obvious misclassifications flagged by heuristics.

## Part C — Population Health

### Archetype Distribution

| Archetype | Count | % |
| --- | --- | --- |
| GENERALIST | 120 | 23.9% |
| PERIMETER_HAWK | 70 | 13.9% |
| ENERGY_BIG | 53 | 10.5% |
| TWO_LEVEL_SCORER | 49 | 9.7% |
| RIM_GUARDIAN | 44 | 8.7% |
| CUTTER_SPECIALIST | 38 | 7.6% |
| CONNECTOR | 28 | 5.6% |
| SWITCHABLE_ANCHOR | 22 | 4.4% |
| WARRIOR_BIG | 13 | 2.6% |
| HELIOCENTRIC_MAESTRO | 13 | 2.6% |
| FACILITATOR | 13 | 2.6% |
| STRETCH_BIG | 12 | 2.4% |
| SNIPER_ELITE | 11 | 2.2% |
| JUMBO_FACILITATOR | 5 | 1.0% |
| HUSTLE_DISRUPTOR | 5 | 1.0% |
| SLASHING_CREATOR | 2 | 0.4% |
| ROLL_MAN | 2 | 0.4% |
| HUB_BIG | 2 | 0.4% |
| ISO_ASSASSIN | 1 | 0.2% |

### Position Snapshot (Top archetypes per position)

- G: 148 players | top archetypes: GENERALIST:38, PERIMETER_HAWK:26, TWO_LEVEL_SCORER:18, CONNECTOR:11, ENERGY_BIG:10
- UNK: 144 players | top archetypes: GENERALIST:35, PERIMETER_HAWK:27, TWO_LEVEL_SCORER:16, RIM_GUARDIAN:13, CUTTER_SPECIALIST:11
- F: 134 players | top archetypes: GENERALIST:31, ENERGY_BIG:27, CUTTER_SPECIALIST:14, PERIMETER_HAWK:14, TWO_LEVEL_SCORER:11
- C: 58 players | top archetypes: RIM_GUARDIAN:15, GENERALIST:8, CUTTER_SPECIALIST:7, SWITCHABLE_ANCHOR:7, WARRIOR_BIG:6
- SG: 9 players | top archetypes: GENERALIST:5, CONNECTOR:2, SNIPER_ELITE:2
- PF: 4 players | top archetypes: GENERALIST:2, ENERGY_BIG:1, TWO_LEVEL_SCORER:1
- PG: 3 players | top archetypes: PERIMETER_HAWK:2, CUTTER_SPECIALIST:1
- SF: 3 players | top archetypes: GENERALIST:1, ISO_ASSASSIN:1, TWO_LEVEL_SCORER:1

### Archetypes with 0 or 1 players

ATHLETIC_FINISHER (0), POST_ANCHOR (0), VULTURE_BIG (0)

### Archetypes with >80 players

GENERALIST (120)

### Defensive Archetypes by Position

| Position | RIM_GUARDIAN | PERIMETER_HAWK | SWITCHABLE_ANCHOR | HUSTLE_DISRUPTOR | Total |
| --- | --- | --- | --- | --- | --- |
| UNK | 13 | 27 | 6 | 1 | 47 |
| G | 9 | 26 | 3 | 3 | 41 |
| F | 7 | 14 | 6 | 0 | 27 |
| C | 15 | 1 | 7 | 1 | 24 |
| PG | 0 | 2 | 0 | 0 | 2 |

### Module F Positive Archetypes Presence

| Archetype | Count |
| --- | --- |
| HELIOCENTRIC_MAESTRO | 13 |
| ISO_ASSASSIN | 1 |
| SLASHING_CREATOR | 2 |
| SNIPER_ELITE | 11 |
| WARRIOR_BIG | 13 |
| RIM_GUARDIAN | 44 |
| PERIMETER_HAWK | 70 |
| SWITCHABLE_ANCHOR | 22 |
| HUSTLE_DISRUPTOR | 5 |

## Part D — Team Offensive Schemes

### Distribution

BALANCED: 4, HALF_COURT: 11, ISO_HEAVY: 6, MOTION: 6, PACE_PUSH: 3
Balanced %: 13.3% (4/30 teams)

### Key Teams (LAL/BOS/DEN)

- LAL: HALF_COURT
- BOS: ISO_HEAVY
- DEN: PACE_PUSH

## Recent Window Snapshot (Ending 2026-02-12)

**14-day active players:** 426
| Archetype | Count | % |
| --- | --- | --- |
| GENERALIST | 81 | 19.0% |
| PERIMETER_HAWK | 66 | 15.5% |
| ENERGY_BIG | 49 | 11.5% |
| TWO_LEVEL_SCORER | 44 | 10.3% |
| RIM_GUARDIAN | 37 | 8.7% |
| CUTTER_SPECIALIST | 33 | 7.7% |
| CONNECTOR | 27 | 6.3% |
| SWITCHABLE_ANCHOR | 20 | 4.7% |
| FACILITATOR | 12 | 2.8% |
| WARRIOR_BIG | 11 | 2.6% |
| HELIOCENTRIC_MAESTRO | 11 | 2.6% |
| STRETCH_BIG | 10 | 2.3% |
| SNIPER_ELITE | 10 | 2.3% |
| HUSTLE_DISRUPTOR | 5 | 1.2% |
| JUMBO_FACILITATOR | 4 | 0.9% |
| ROLL_MAN | 2 | 0.5% |
| HUB_BIG | 2 | 0.5% |
| SLASHING_CREATOR | 1 | 0.2% |
| ISO_ASSASSIN | 1 | 0.2% |

**21-day active players:** 439
| Archetype | Count | % |
| --- | --- | --- |
| GENERALIST | 86 | 19.6% |
| PERIMETER_HAWK | 66 | 15.0% |
| ENERGY_BIG | 49 | 11.2% |
| TWO_LEVEL_SCORER | 45 | 10.3% |
| RIM_GUARDIAN | 37 | 8.4% |
| CUTTER_SPECIALIST | 35 | 8.0% |
| CONNECTOR | 27 | 6.2% |
| SWITCHABLE_ANCHOR | 20 | 4.6% |
| WARRIOR_BIG | 12 | 2.7% |
| FACILITATOR | 12 | 2.7% |
| STRETCH_BIG | 11 | 2.5% |
| SNIPER_ELITE | 11 | 2.5% |
| HELIOCENTRIC_MAESTRO | 11 | 2.5% |
| JUMBO_FACILITATOR | 5 | 1.1% |
| HUSTLE_DISRUPTOR | 5 | 1.1% |
| SLASHING_CREATOR | 2 | 0.5% |
| ROLL_MAN | 2 | 0.5% |
| HUB_BIG | 2 | 0.5% |
| ISO_ASSASSIN | 1 | 0.2% |

## Team Defense (Season-Long Dynamic vs Static)

Season window: 2025-10-01 to 2026-02-12. Dynamic styles mapped via DEFENSIVE_STYLE_MAP.

| Team | Dynamic (Mapped) | Static | Match |
|---|---|---|---|
| ATL | FUNNEL | FUNNEL | OK |
| BOS | NEUTRAL | NEUTRAL | OK |
| BKN | PERIMETER | PERIMETER | OK |
| CHA | PAINT_PACK | PAINT_PACK | OK |
| CHI | PAINT_PACK | PAINT_PACK | OK |
| CLE | PAINT_PACK | PAINT_PACK | OK |
| DAL | NEUTRAL | NEUTRAL | OK |
| DEN | NEUTRAL | NEUTRAL | OK |
| DET | NEUTRAL | NEUTRAL | OK |
| GSW | PERIMETER | PERIMETER | OK |
| HOU | BLITZ | BLITZ | OK |
| IND | FUNNEL | FUNNEL | OK |
| LAC | FUNNEL | FUNNEL | OK |
| LAL | PAINT_PACK | PAINT_PACK | OK |
| MEM | PAINT_PACK | PAINT_PACK | OK |
| MIA | NEUTRAL | NEUTRAL | OK |
| MIL | PERIMETER | PERIMETER | OK |
| MIN | PAINT_PACK | PAINT_PACK | OK |
| NOP | PAINT_PACK | PAINT_PACK | OK |
| NYK | PERIMETER | PERIMETER | OK |
| OKC | PAINT_PACK | PAINT_PACK | OK |
| ORL | NEUTRAL | NEUTRAL | OK |
| PHI | BLITZ | BLITZ | OK |
| PHX | PERIMETER | PERIMETER | OK |
| POR | NEUTRAL | NEUTRAL | OK |
| SAC | NEUTRAL | NEUTRAL | OK |
| SAS | PERIMETER | PERIMETER | OK |
| TOR | PAINT_PACK | PAINT_PACK | OK |
| UTA | NEUTRAL | NEUTRAL | OK |
| WAS | NEUTRAL | NEUTRAL | OK |
