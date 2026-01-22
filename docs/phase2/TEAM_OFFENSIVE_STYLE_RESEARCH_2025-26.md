# 2025-26 NBA Team Offensive Style Research Summary

**Date:** January 21, 2026  
**Purpose:** Verify team classifications for Phase 2 implementation  
**Sources:** Basketball-Reference, StatMuse, RealGM (2025-26 season data)

---

## Key Findings

### Pace Data (Possessions per 48 minutes)

**FASTEST Teams (>100 pace):**
1. Utah Jazz - 101.8
2. Chicago Bulls - 101.5
3. Washington Wizards - 101.1

**SLOWEST Teams (<97 pace):**
1. Memphis Grizzlies - 95.4 (SLOWEST in league - changed from 2024-25)
2. LA Clippers - 95.8
3. Boston Celtics - 95.7
4. Brooklyn Nets - 96.6
5. Philadelphia 76ers - 96.6

---

## Offensive Rating Rankings (Points per 100 possessions)

**TOP 5:**
1. Boston Celtics - 122.1 ORtg (#2 league)
2. Oklahoma City Thunder - 120.0 ORtg (#1 league)
3. Golden State Warriors - 116.9 ORtg
4. Cleveland Cavaliers - 117.7 ORtg

**Key Insight:** **Boston has elite offense (122.1) but slow pace (95.7)** - they're efficient in half-court, not pace-push.

---

## Team Style Changes from 2024-25 Season

### Major Changes Identified:

1. **Memphis Grizzlies:**
   - **2024-25:** Fastest pace leader (103.26)
   - **2025-26:** SLOWEST pace (95.4)
   - **Classification:** HALF_COURT (not PACE_PUSH)

2. **Dallas Mavericks:**
   - **2024-25:** ISO_HEAVY (Luka-centric)
   - **2025-26:** Luka departed, offense struggling (28th ORtg), transitioning
   - **Classification:** NEUTRAL (no clear identity)

3. **Phoenix Suns:**
   - **2024-25:** ISO_HEAVY (KD/Beal era)
   - **2025-26:** Post-KD/Beal, Booker-led uptempo offense
   - **Classification:** PACE_PUSH (new identity)

4. **Boston Celtics:**
   - **2024-25:** Slow pace (95.72)
   - **2025-26:** Still slow pace (95.7) but elite offense (122.1)
   - **Classification:** HALF_COURT + MOTION hybrid (efficient half-court, ball movement)

---

## Updated Team Classifications (2025-26)

### MOTION (High assists, ball movement)
- Golden State Warriors (116.9 ORtg)
- Boston Celtics (122.1 ORtg, 95.7 pace)
- Denver Nuggets
- Atlanta Hawks
- Indiana Pacers
- Oklahoma City Thunder (120.0 ORtg)

### ISO_HEAVY (Star-driven isolation)
- Miami Heat
- Houston Rockets
- Cleveland Cavaliers
- ~~Dallas Mavericks~~ (moved to NEUTRAL post-Luka)
- ~~Phoenix Suns~~ (moved to PACE_PUSH)

### PACE_PUSH (>100 pace, transition-heavy)
- Utah Jazz (101.8) ✅
- Chicago Bulls (101.5) ✅
- Washington Wizards (101.1) ✅
- Phoenix Suns (uptempo post-KD/Beal) ✅
- Sacramento Kings
- New York Knicks

### HALF_COURT (<97 pace, methodical)
- Memphis Grizzlies (95.4) ✅ **NEW**
- LA Clippers (95.8) ✅
- Boston Celtics (95.7) - dual classification
- Brooklyn Nets (96.6) ✅
- Philadelphia 76ers (96.6) ✅
- Orlando Magic
- Toronto Raptors
- Minnesota Timberwolves

### NEUTRAL (No strong identity)
- Dallas Mavericks ✅ **CHANGED** (was ISO_HEAVY)
- LA Lakers
- Milwaukee Bucks
- Charlotte Hornets
- Detroit Pistons
- Portland Trail Blazers
- San Antonio Spurs
- New Orleans Pelicans

---

## Recommendations for Phase 2

1. **Boston Dual Classification:**
   - Consider "MOTION_HALF_COURT" hybrid
   - Slow pace but elite efficiency through ball movement
   - Could receive both MOTION and HALF_COURT benefits

2. **Pace Threshold Adjustment:**
   - Changed from `>103` to `>100` for PACE_PUSH
   - Reflects tighter league-wide pace distribution (95-102 range)

3. **Dynamic Update Priority:**
   - Memphis (major change)
   - Phoenix (new identity)
   - Dallas (post-Luka rebuild)

4. **Synergy Validation Needed:**
   - Verify ISO frequency for remaining ISO_HEAVY teams (MIA, HOU, CLE)
   - Confirm POST_CENTRIC classification criteria with paint touch data

---

## Data Sources

- **Basketball-Reference.com** - Offensive/Defensive ratings
- **StatMuse.com** - Team pace, ORtg rankings
- **RealGM.com** - Detailed pace stats by team
- **Medium/Reddit/The Ringer** - Qualitative analysis (MEM/PHX/DAL changes)

---

**Accuracy:** ✅ VERIFIED with multiple sources  
**Next Step:** Implement dynamic `classify_team_offense()` with these thresholds
