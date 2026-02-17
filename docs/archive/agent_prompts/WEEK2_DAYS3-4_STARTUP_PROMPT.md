# Week 2 Days 3-4 Startup Prompt - Ludi Informatio v2.0

**Created:** January 8, 2026, 12:55 PM ET
**For:** New Terminal Window/Session
**Phase:** Week 2, Days 3-4 (Play Classification Tags)

---

## 📋 COPY THIS PROMPT TO NEW TERMINAL

```
I'm continuing work on the Ludi Informatio v2.0 NBA analytics platform.

## Current Status (Jan 8, 2026, 12:55 PM ET)

**Week 1 Complete ✅:**
- All 9 modules (A-H + X) production-ready: 73,688 lines
- test_pipeline.py: ✅ PASSED (3 games, 19 players, $0.1125 cost)
- Database: 10,840 player game logs, 505 players

**Week 2 Days 1-2 Complete ✅:**
- `utils/bet_logger.py` (650 lines) - BetLogger class with dual storage
- SQLite tables: `bet_recommendations`, `bet_daily_summaries` in ludi.db
- JSON logs: `logs/bets/YYYY-MM-DD.json` format
- Module F integrated with `get_bet_logger()` singleton
- 5 Week 1 Diamond plays logged with full context
- `backfill_week1_bets.py` (221 lines) - Week 1 data import

## Week 2 Goal: Play Classification Tags (Days 3-4)

I need to create a tag classification system for bet analysis and filtering.

### Deliverables

**1. utils/tag_classifier.py - TagClassifier class**
Functions:
- `assign_archetype_tag(player_stats)` → SLASHER, STRETCH_BIG, RIM_RUNNER, TWO_WAY_WING, FACILITATOR
- `assign_scenario_tags(player, game_context)` → BENEFICIARY, USAGE_VACUUM, MINUTES_LIMIT, HOT_STREAK
- `assign_matchup_tags(team, opponent, defense_scheme)` → HACKERS, PAINT_PACK, PERIMETER, BLITZ
- `assign_market_tags(bet_data)` → CORRELATED_SGP, CONTRARIAN, SHARP_MOVE, STEAM_PLAY

**2. Module F Integration**
- Import tag_classifier in module_f.py
- Call tag functions before generating briefing
- Append tags to each recommendation
- Include tags in bet_logger entries

**3. Database Schema Update**
- Add `tags` column (JSON array) to bet_recommendations
- Add `archetype` column
- Add `scenario` column

**4. Defense Scheme Mappings (30 NBA Teams)**
From Module E:
- PAINT_PACK: OKC, BOS, DET, MIN, SAS, ORL
- BLITZ: HOU, TOR, MIA, PHX
- PERIMETER: GSW, DAL, NYK
- FUNNEL: WAS, ATL, CHI, UTA, SAC
- HACKERS: IND, CHA, POR

### Success Criteria
- [ ] All 5 archetypes defined and testable
- [ ] Scenario detection working (beneficiary, usage vacuum)
- [ ] Defense scheme mappings for 30 NBA teams
- [ ] Tags appear in daily briefing
- [ ] Tags logged to database
- [ ] Query by tag working

## Context Files

**Read these first:**
1. /home/mnprice86/ludi_bot/CLAUDE.md - Project overview & current status
2. /home/mnprice86/ludi_bot/UPDATED_STATUS_AND_NEXT_STEPS.md - Week 2 plan with tag specs
3. /home/mnprice86/ludi_bot/module_e.py - Archetype and defense scheme definitions
4. /home/mnprice86/ludi_bot/module_f.py - Reporter to integrate with
5. /home/mnprice86/ludi_bot/utils/bet_logger.py - Logging system to update

**Key Directories:**
- Project root: /home/mnprice86/ludi_bot
- Utils: /home/mnprice86/ludi_bot/utils/
- Database: /home/mnprice86/ludi_bot/ludi.db

## Tag Definitions

### Archetype Tags (from Module E)
| Tag | Description | Detection Criteria |
|-----|-------------|-------------------|
| SLASHER | High FTA, low 3PA | FTA/G > 4.0, 3PA/G < 3.0 |
| STRETCH_BIG | Centers with 3PM | Position = C, 3PM/G > 1.0 |
| RIM_RUNNER | High OREB, low usage | OREB/G > 2.0, USG% < 18% |
| TWO_WAY_WING | Balanced offense/defense | PTS 12-18, STL+BLK > 1.5 |
| FACILITATOR | High AST% guards | AST/G > 6.0, Position = G |

### Scenario Tags (from Module X)
| Tag | Description | Detection Criteria |
|-----|-------------|-------------------|
| BENEFICIARY | Scales usage from injury | Teammate OUT, USG% increase expected |
| USAGE_VACUUM | Star player out | Top 3 usage player on team is OUT |
| MINUTES_LIMIT | Player on restriction | Injury status = "MINUTES_LIMIT" |
| HOT_STREAK | 5+ game trend above avg | L5 stat > Season avg by 20% |

### Matchup Tags (from defensive schemes)
| Tag | Description | Effect |
|-----|-------------|--------|
| vs_HACKERS | Aggressive foul defense | +20% FTA |
| vs_PAINT_PACK | Packed paint | +15% 3PM |
| vs_PERIMETER | Small ball | +30% OREB |
| vs_BLITZ | Blitzing defense | +TOV risk |

## Example Tagged Output

**Before:**
```
🏀 Duncan Robinson (DET) | OVER 17.5 PTS
   Sharp Proj: 10.52 | EV: +43.25% | 1.5u
```

**After:**
```
🏀 Duncan Robinson (DET) | OVER 17.5 PTS
   Sharp Proj: 10.52 | EV: +43.25% | 1.5u
   [STRETCH_BIG] [vs_PAINT_PACK] [🔥 CORRELATED SGP]
```

## Commands

**Activate environment:**
```bash
cd /home/mnprice86/ludi_bot
source venv/bin/activate
```

**Test tag classifier:**
```python
from utils.tag_classifier import TagClassifier
tc = TagClassifier()
tags = tc.assign_archetype_tag(player_stats)
```

**Query by tag:**
```python
from utils.bet_logger import get_bet_logger
logger = get_bet_logger()
# Filter bets by archetype
```

Ready to start! Please help me implement the tag classification system.
```

---

## 🚀 QUICK START INSTRUCTIONS

1. **Open New Terminal**
2. **Copy entire block above** (between triple backticks)
3. **Paste into Claude Code**
4. **Claude will:**
   - Read context files
   - Create utils/tag_classifier.py
   - Integrate with Module F
   - Update database schema
   - Test everything

---

**Last Updated:** January 8, 2026, 12:55 PM ET
**Use In:** New terminal window/Claude session
**Phase:** Week 2, Days 3-4
