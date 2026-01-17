# Archetype & Defensive Scheme Update Prompt - Ludi Informatio v2.0

**Created:** January 8, 2026, 7:51 PM ET  
**For:** Session Continuation (After Crash Recovery)  
**Phase:** Week 2 - Data Completion Task

---

## 📋 COPY THIS PROMPT TO NEW TERMINAL

```
I'm continuing work on the Ludi Informatio v2.0 NBA analytics platform.

## Context (Crash Recovery)

Our last session crashed while updating player/team/referee archetypes. I need you to complete:

1. **TASK A:** Complete the missing 9 team defensive schemes in Module E
2. **TASK B:** Create a script to bulk-populate player archetypes in the database

## Current State Analysis

**Database:**
- 572 players have NULL archetype (needs population)
- Database path: `/home/mnprice86/ludi_bot/ludi.db`
- Archetype column exists in `players` table

**Module E (module_e.py) - DEFENSIVE_STYLES:**
Currently mapped (21 teams):
- PAINT_PACK: OKC, BOS, DET, MIN, SAS, ORL
- BLITZ: HOU, TOR, MIA, PHO
- PERIMETER: GSW, DAL, NYK
- FUNNEL: WAS, ATL, CHI, UTA, SAC
- HACKERS: IND, CHA, POR

**MISSING (9 teams):** LAL, LAC, BKN, CLE, DEN, MEM, MIL, NOP, PHI

**Module G (module_g.py) - IMPACT_MAP:**
Currently has 14 referees mapped with pace factors (0.96 - 1.04)

## TASK A: Complete Defensive Schemes

Add the missing 9 teams to `DEFENSIVE_STYLES` dict in `module_e.py`:

Research needed (use 2025-26 season context):
- LAL (Lakers): Style? 
- LAC (Clippers): Style?
- BKN (Nets): Style?
- CLE (Cavaliers): Style?
- DEN (Nuggets): Style?
- MEM (Grizzlies): Style?
- MIL (Bucks): Style?
- NOP (Pelicans): Style?
- PHI (76ers): Style?

Scheme options: PAINT_PACK, BLITZ, PERIMETER, FUNNEL, HACKERS

## TASK B: Create Archetype Population Script

Create `populate_player_archetypes.py` that:
1. Reads all players from database
2. Uses Module E's `_assign_archetype()` logic (or tag_classifier)
3. Updates each player's archetype in the database
4. Logs changes

**Archetype definitions (from module_e.py):**
```python
# Current logic in _assign_archetype():
if reb > 6.5 and tpm > 1.8: return "STRETCH_BIG"
if pts > 22.0 and usg > 0.30 and tpm < 2.0: return "SLASHER"
if tpm > 2.8 and ast < 3.5: return "SNIPER"
if reb > 8.0 and tpm < 0.6: return "RIM_RUNNER"
if usg > 0.30 and ast > 6.0: return "BALL_HOG"
return "GENERALIST"
```

**Stat columns in player_game_logs (for averages):**
- pts, reb, ast, fg3m (for 3PM), fga, fta

## Key Files to Reference

1. `/home/mnprice86/ludi_bot/module_e.py` - LudiCalibrator with DEFENSIVE_STYLES and _assign_archetype
2. `/home/mnprice86/ludi_bot/module_g.py` - LudiRefEngine with IMPACT_MAP (referee data)
3. `/home/mnprice86/ludi_bot/database.py` - LudiHistorian, schema definitions
4. `/home/mnprice86/ludi_bot/utils/tag_classifier.py` - TagClassifier with assign_archetype_tag
5. `/home/mnprice86/ludi_bot/ludi.db` - SQLite database

## Success Criteria

**Task A:**
- [ ] All 30 NBA teams have defensive schemes in module_e.py
- [ ] Schemes are accurate for 2025-26 season

**Task B:**
- [ ] `populate_player_archetypes.py` created
- [ ] Script calculates player averages from game logs
- [ ] Script updates archetype column in players table
- [ ] Dry-run mode available (preview before commit)
- [ ] Log output shows which players got which archetypes

## Commands

**Activate environment:**
```bash
cd /home/mnprice86/ludi_bot
source venv/bin/activate
```

**Run archetype population (after script is created):**
```bash
./venv/bin/python populate_player_archetypes.py --dry-run
./venv/bin/python populate_player_archetypes.py
```

Ready to complete these tasks!
```

---

## 🚀 QUICK START

1. **Open New Terminal** (or paste into current Claude session)
2. **Copy entire block above** (between triple backticks)
3. **Claude will:**
   - Add missing teams to Module E
   - Create `populate_player_archetypes.py`
   - Run and verify archetypes are populated

---

**Last Updated:** January 8, 2026, 7:51 PM ET  
**Tasks:** Complete Defensive Schemes + Populate Player Archetypes
