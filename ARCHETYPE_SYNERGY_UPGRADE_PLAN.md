# Archetype & Team Type Upgrade Plan - Synergy Integration
**Created:** January 20, 2026  
**Status:** Ready for Implementation  
**Phase:** Post Ghost Protocol + Module A Upgrades

---

## Executive Summary

Upgrade the archetype classification system by blending **current Ludi archetypes** with **NBA Synergy playtype data**, leveraging 60-day backfilled tracking stats, shot quality, WOWY, and clutch data from NBA API + PBP Stats.

**Key Upgrades:**
1. **Secondary Playtypes** - Synergy-aligned classifications with strict thresholds
2. **Team Offensive Types** - Automated weekly classification system (mirrors defense)
3. **Matchup Matrix Expansion** - 14+ new research-backed modifiers
4. **Blowout Tax Review** - Validate current smart blowout tax logic
5. **B2B Fatigue Integration** - Research-backed schedule adjustments

**Backtest Framework:**
- **Window:** Dec 20, 2025 - Jan 16, 2026 (28 days, 60-day data coverage)
- **Baseline:** Pre-Jan 17 Module A + Current Module E archetypes
- **New System:** Post-Jan 17 Module A + Synergy archetypes + new matchups
- **Target:** +3% ROI improvement, +2% hit rate (Moderate success tier)
- **Sims:** Already 5,000 iterations in Module C ✅

---

## Current System State

### Module C (Oracle) - Confirmed
- **Sim Count:** 5,000 iterations (line 28-32) ✅
- **Variance:** 0.40 (40%) for conservative NBA volatility (line 114, 160)
- **Hybrid Engine:** Normal distribution (high-volume) + Poisson (rare events)
- **Hit Rate Calculation:** Correct Monte Carlo approach (lines 170-200)

### Blowout Tax (Smart Context-Aware) - Confirmed
**File:** `utils/blowout_tax.py` (215 lines, Jan 2026)

**Current Logic:**
- **Favorites:** Tax starts at 10pt spread, scales 2%/point (max -30% at 25pt)
- **Starters:** Get taxed (sit early in blowouts)
- **Bench:** Get boosted (garbage time opportunity)
- **Underdogs:** Neutral (keep fighting regardless)

**Tax Examples:**
- Favorite starter, 15pt spread: 0.90 (-10%)
- Favorite bench, 15pt spread: 1.05 (+5%)
- Underdog (both), 15pt spread: 1.00 (neutral)

**Status:** ✅ Already research-backed, may need minor tuning post-backtest

### Module E (Calibrator V6.0)
- **Current Archetypes:** 11 types (HELIOCENTRIC, SLASHER, ELITE_SCORER, etc.)
- **Defensive Types:** 30 teams classified (PAINT_PACK, BLITZ, PERIMETER, etc.)
- **Matchup Matrix:** 11 archetype vs defense combos
- **Missing:** Secondary playtypes, team offensive types, B2B fatigue

### Available Data (60-Day Backfill)
**Sources:** NBA API + PBP Stats API (Nov 21 - Jan 19, 2026)

**Tables:**
- `player_game_tracking` - drives, catch_shoot, pull_up, speed, distance
- `player_game_advanced` - off_rating, def_rating, net_rating, ts_pct
- `player_clutch_stats` - clutch performance (PBP Stats)
- `shot_quality` - Expected FG%, rim freq, corner 3 freq
- `player_game_opponent` - Defensive matchup data
- `team_lineups` - WOWY data (possessions, NetRtg splits)

**Season Data:** Tank01 API has full 2025-26 season team stats for offensive classification

---

## Phase 1: Secondary Playtypes (Synergy-Aligned with Strict Thresholds)

### Why Strict Thresholds?
**Problem:** Without thresholds, every player populates every playtype.

**Solution:** Only assign secondary playtype if player meets **2+ criteria** from each category.

### 8 Secondary Playtypes

**1. ISO_SCORER** (Isolation Efficiency)
```python
# Must meet 2 of 3:
drives > 8/game AND
pull_up_fga > 5/game AND
usg > 0.28
```
**Examples:** Luka, Tatum, SGA, Kyrie

---

**2. P&R_HANDLER** (Pick & Roll Ball Handler)
```python
# Must meet 2 of 3:
drives > 5/game AND
ast > 6.0 AND
catch_shoot_fga < pull_up_fga
```
**Examples:** Harden, Trae, CP3, Tyus Jones

---

**3. P&R_ROLL_MAN** (Pick & Roll Finisher)
```python
# Must meet 2 of 3:
rim_freq > 0.40 AND
catch_shoot_fga > pull_up_fga AND
ast < 3.0
```
**Examples:** AD, Capela, Claxton, Gafford

---

**4. SPOT_UP** (Catch & Shoot Specialist)
```python
# Must meet 2 of 3:
catch_shoot_fga > 4/game AND
catch_shoot_pct > 0.38 AND
3pm > 1.5
```
**Examples:** Duncan Robinson, Klay, Joe Harris

---

**5. OFF_BALL_CUTTER** (Backdoor/Cut Specialist)
```python
# Must meet 2 of 3:
rim_fg_pct > 0.65 AND
catch_shoot_fga > pull_up_fga AND
drives < 4/game
```
**Examples:** Finney-Smith, GP2, Bruce Brown

---

**6. TRANSITION** (Fast Break Threat)
```python
# Must meet 2 of 3:
speed > 4.5 mph AND
distance > 2.3 miles/game AND
(fast_break_pts > 3 OR team_pace > 102)
```
**Examples:** Fox, Giannis, Maxey, Ja

---

**7. PUTBACK** (Offensive Rebound Finisher)
```python
# Must meet 2 of 3:
oreb > 2.5 AND
rim_freq > 0.50 AND
dunks+layups > 4/game (approx: rim_fga > 5)
```
**Examples:** Drummond, Zubac, Hartenstein

---

**8. POST_UP** (Back-to-Basket Scoring)
```python
# Approximate (no direct paint touches data):
# Must meet 2 of 3:
paint_pts > 12 AND
rim_freq > 0.45 AND
speed < 4.0 mph
```
**Examples:** Embiid, Jokic (secondary), Vucevic

---

### Implementation Code

**File:** `module_e.py` (new method)

```python
def _get_tracking_stats(self, player_name, days=20):
    """Query tracking data from player_game_tracking table"""
    import sqlite3
    try:
        conn = sqlite3.connect('ludi.db')
        cursor = conn.cursor()
        
        query = '''
        SELECT 
            AVG(drives) as drives,
            AVG(drive_pts) as drive_pts,
            AVG(catch_shoot_fgm) as cs_fgm,
            AVG(catch_shoot_fga) as cs_fga,
            AVG(catch_shoot_pts) as cs_pts,
            AVG(pull_up_fgm) as pu_fgm,
            AVG(pull_up_fga) as pu_fga,
            AVG(pull_up_pts) as pu_pts,
            AVG(speed) as speed,
            AVG(distance) as distance
        FROM player_game_tracking
        WHERE player_name = ?
        AND game_date >= date('now', '-' || ? || ' days')
        '''
        
        cursor.execute(query, (player_name, days))
        row = cursor.fetchone()
        conn.close()
        
        if row and row[0] is not None:
            cs_pct = row[2] / row[3] if row[3] > 0 else 0.0
            return {
                'drives': row[0] or 0.0,
                'catch_shoot_fga': row[3] or 0.0,
                'catch_shoot_pct': cs_pct,
                'pull_up_fga': row[6] or 0.0,
                'speed': row[8] or 0.0,
                'distance': row[9] or 0.0
            }
        return {}
    except:
        return {}


def _assign_secondary_playtypes(self, p, tracking_data):
    """
    Assign 0-2 secondary playtypes using strict thresholds.
    
    Threshold Logic: Player must meet 2 of 3 criteria for each playtype.
    This prevents every player from populating every tag.
    """
    secondaries = []
    
    # Extract stats
    drives = tracking_data.get('drives', 0)
    cs_fga = tracking_data.get('catch_shoot_fga', 0)
    cs_pct = tracking_data.get('catch_shoot_pct', 0)
    pu_fga = tracking_data.get('pull_up_fga', 0)
    speed = tracking_data.get('speed', 0)
    distance = tracking_data.get('distance', 0)
    
    ast = p.get('base_ast', 0)
    usg = p.get('base_usg', 0)
    oreb = p.get('base_oreb', 0)
    tpm = p.get('base_3pm', 0)
    
    # Approximate metrics (from database if available)
    rim_freq = p.get('pbp_rim_freq', 0)  # From shot quality
    rim_fg_pct = p.get('pbp_rim_fg_pct', 0)
    paint_pts = p.get('base_pts', 0) * 0.5  # Rough estimate (50% from paint)
    
    # 1. ISO_SCORER (2 of 3)
    iso_criteria = [drives > 8, pu_fga > 5, usg > 0.28]
    if sum(iso_criteria) >= 2:
        secondaries.append('ISO_SCORER')
    
    # 2. P&R_HANDLER (2 of 3)
    prh_criteria = [drives > 5, ast > 6.0, cs_fga < pu_fga]
    if sum(prh_criteria) >= 2:
        secondaries.append('P&R_HANDLER')
    
    # 3. P&R_ROLL_MAN (2 of 3)
    prr_criteria = [rim_freq > 0.40, cs_fga > pu_fga, ast < 3.0]
    if sum(prr_criteria) >= 2:
        secondaries.append('P&R_ROLL_MAN')
    
    # 4. SPOT_UP (2 of 3)
    spot_criteria = [cs_fga > 4, cs_pct > 0.38, tpm > 1.5]
    if sum(spot_criteria) >= 2:
        secondaries.append('SPOT_UP')
    
    # 5. OFF_BALL_CUTTER (2 of 3)
    cut_criteria = [rim_fg_pct > 0.65, cs_fga > pu_fga, drives < 4]
    if sum(cut_criteria) >= 2:
        secondaries.append('OFF_BALL_CUTTER')
    
    # 6. TRANSITION (2 of 3)
    # Get team pace if available
    team_pace = p.get('team_pace', 100)
    trans_criteria = [speed > 4.5, distance > 2.3, team_pace > 102]
    if sum(trans_criteria) >= 2:
        secondaries.append('TRANSITION')
    
    # 7. PUTBACK (2 of 3)
    rim_fga = p.get('base_fga', 0) * rim_freq if rim_freq > 0 else 0
    putback_criteria = [oreb > 2.5, rim_freq > 0.50, rim_fga > 5]
    if sum(putback_criteria) >= 2:
        secondaries.append('PUTBACK')
    
    # 8. POST_UP (2 of 3) - Approximation
    post_criteria = [paint_pts > 12, rim_freq > 0.45, speed < 4.0]
    if sum(post_criteria) >= 2:
        secondaries.append('POST_UP')
    
    # Return max 2 secondary playtypes (prioritize first matches)
    return secondaries[:2]
```

**Update `calibrate_player()` method:**

```python
def calibrate_player(self, player_packet, yak_report):
    calibrated = player_packet.copy()
    if 'notes' not in calibrated: calibrated['notes'] = ""
    
    # 1. ASSIGN PRIMARY ARCHETYPE
    archetype, _ = self._assign_archetype(calibrated)
    
    # NEW: ASSIGN SECONDARY PLAYTYPES
    tracking_data = self._get_tracking_stats(calibrated.get('name', ''))
    secondary_playtypes = self._assign_secondary_playtypes(calibrated, tracking_data)
    
    if archetype:
        calibrated['archetype'] = archetype
        calibrated['notes'] += f" [{archetype}]"
    
    if secondary_playtypes:
        calibrated['secondary_playtypes'] = secondary_playtypes
        calibrated['notes'] += f" / {', '.join(secondary_playtypes)}"
    
    # ... rest of calibrate_player logic
```

---

## Phase 2: Team Offensive Types (Automated Weekly Classification)

### Goal
Mirror defensive type system: **automated, weekly updates, data-driven**

### 6 Offensive Types

| Type | Criteria | Key Metric | Example Teams |
|------|----------|------------|---------------|
| `PACE_AND_SPACE` | pace > 100.5, 3pa > 38, efg% > 0.55 | 3PA rate | BOS, GSW, DAL |
| `PAINT_ATTACK` | team_drives > 50, rim_freq > 0.35 | Drives/game | MEM, CLE, MIL |
| `MOTION_OFFENSE` | passes > 300, ast > 26, ast/fgm > 0.65 | Ball movement | SAS, DEN, GSW |
| `ISOLATION_HEAVY` | iso_freq > 12%, pace < 99, top2_usg > 55% | ISO frequency | LAL, MIA |
| `TRANSITION_FOCUSED` | fast_break_pts > 18, pace > 102, steals > 9 | Fast break pts | OKC, SAC, ATL |
| `THREE_POINT_CENTRIC` | 3pa > 42, 3pa_rate > 50%, 3pm > 15 | 3PA volume | BOS, HOU |

### Implementation

**New File:** `utils/team_offensive_classifier.py`

```python
"""
Team Offensive Type Classifier

Automated weekly classification system that mirrors defensive type logic.
Uses Tank01 API season data + aggregated tracking data.

Updates: Weekly (Mondays) via GitHub Actions or manual trigger
"""

import requests
import sqlite3
from typing import Dict

class TeamOffensiveClassifier:
    def __init__(self):
        self.TEAM_OFFENSIVE_TYPES = {}
        
    def classify_all_teams(self) -> Dict[str, str]:
        """
        Classify all 30 NBA teams by offensive identity.
        
        Returns:
            Dict mapping team_abbr -> offensive_type
        """
        team_stats = self._fetch_team_stats()
        
        for team_abbr, stats in team_stats.items():
            off_type = self._classify_team(team_abbr, stats)
            self.TEAM_OFFENSIVE_TYPES[team_abbr] = off_type
        
        return self.TEAM_OFFENSIVE_TYPES
    
    def _fetch_team_stats(self) -> Dict:
        """Fetch team stats from Tank01 API + aggregate tracking data"""
        # TODO: Implement Tank01 API call for season team stats
        # TODO: Aggregate tracking data from player_game_tracking table
        
        # Placeholder structure:
        return {
            "BOS": {
                "pace": 101.2,
                "3pa": 42.3,
                "efg_pct": 0.578,
                "team_drives": 48.2,
                "rim_freq": 0.32,
                "passes": 315.4,
                "ast": 28.1,
                "ast_per_fgm": 0.68,
                "fast_break_pts": 16.5,
                "steals": 8.7,
                "3pa_rate": 0.52,
                "3pm": 16.8
            },
            # ... all 30 teams
        }
    
    def _classify_team(self, team_abbr: str, stats: Dict) -> str:
        """
        Classify single team using research-backed thresholds.
        
        Priority order (check in sequence, return first match):
        1. THREE_POINT_CENTRIC
        2. PACE_AND_SPACE
        3. PAINT_ATTACK
        4. TRANSITION_FOCUSED
        5. MOTION_OFFENSE
        6. ISOLATION_HEAVY
        7. BALANCED (fallback)
        """
        
        # THREE_POINT_CENTRIC (most specific)
        if stats['3pa'] > 42 and stats['3pa_rate'] > 0.50 and stats['3pm'] > 15:
            return "THREE_POINT_CENTRIC"
        
        # PACE_AND_SPACE
        if stats['pace'] > 100.5 and stats['3pa'] > 38 and stats['efg_pct'] > 0.55:
            return "PACE_AND_SPACE"
        
        # PAINT_ATTACK
        if stats['team_drives'] > 50 and stats['rim_freq'] > 0.35:
            return "PAINT_ATTACK"
        
        # TRANSITION_FOCUSED
        if stats['fast_break_pts'] > 18 and stats['pace'] > 102 and stats['steals'] > 9:
            return "TRANSITION_FOCUSED"
        
        # MOTION_OFFENSE
        if stats['passes'] > 300 and stats['ast'] > 26 and stats['ast_per_fgm'] > 0.65:
            return "MOTION_OFFENSE"
        
        # ISOLATION_HEAVY (hardest to detect without Synergy ISO freq)
        # Approximate: low pace + low assists + high top 2 player usage
        if stats['pace'] < 99 and stats['ast'] < 24:
            return "ISOLATION_HEAVY"
        
        return "BALANCED"
    
    def get_offensive_type(self, team_abbr: str) -> str:
        """Get cached offensive type for team"""
        return self.TEAM_OFFENSIVE_TYPES.get(team_abbr, "BALANCED")


# Auto-run on import (like defensive types)
_classifier = TeamOffensiveClassifier()
TEAM_OFFENSIVE_TYPES = _classifier.classify_all_teams()
```

**Integration in Module E:**

```python
from utils.team_offensive_classifier import TEAM_OFFENSIVE_TYPES

# In calibrate_player():
team_offensive_type = TEAM_OFFENSIVE_TYPES.get(calibrated['team'], 'BALANCED')
opponent_offensive_type = TEAM_OFFENSIVE_TYPES.get(calibrated['opponent'], 'BALANCED')

# Use in matchup matrix (Phase 3)
```

---

## Phase 3: Expanded Matchup Matrix

### Current Matchups (Keep - Already Validated)
- STRETCH_BIG vs PAINT_PACK: +15% 3PM/3PA
- SLASHER vs HACKERS: +20% FTA
- RIM_RUNNER vs PERIMETER: +30% OREB
- HELIOCENTRIC vs BLITZ: +18% AST, -8% PTS, +10% TOV
- TWO_WAY_WING vs FUNNEL: +12% 3PA, +15% STL
- ELITE_SCORER vs PERIMETER: +8% PTS, +10% 3PM
- HUB_BIG vs PERIMETER: +12% AST, +15% REB
- JUMBO_CREATOR vs PERIMETER: +8% PTS, +10% REB

### NEW: Secondary Playtype Matchups (Add to Module E)

**Implementation in `module_e.py` (lines 92-167):**

```python
# After existing matchup logic (line ~129), add:

# === NEW: SECONDARY PLAYTYPE MATCHUPS ===
secondary_types = calibrated.get('secondary_playtypes', [])

for playtype in secondary_types:
    # ISO_SCORER matchups
    if playtype == 'ISO_SCORER':
        if def_style == "BLITZ":
            self._boost_stat(calibrated, 'proj_pts', 0.92)
            self._boost_stat(calibrated, 'proj_tov', 1.12)
            calibrated['notes'] += " | ISO Tax vs Blitz"
        elif def_style == "PERIMETER":
            self._boost_stat(calibrated, 'proj_pts', 1.10)
            calibrated['notes'] += " | ISO Mismatch"
    
    # P&R_HANDLER matchups
    elif playtype == 'P&R_HANDLER':
        if def_style == "PAINT_PACK":
            self._boost_stat(calibrated, 'proj_ast', 1.08)
            calibrated['notes'] += " | P&R Drop Edge"
        elif def_style == "BLITZ":
            self._boost_stat(calibrated, 'proj_ast', 0.90)
            self._boost_stat(calibrated, 'proj_tov', 1.15)
            calibrated['notes'] += " | P&R Blitz Tax"
    
    # SPOT_UP matchups (strongest research validation)
    elif playtype == 'SPOT_UP':
        if def_style == "PAINT_PACK":
            self._boost_stat(calibrated, 'proj_3pm', 1.12)
            calibrated['notes'] += " | Spot-Up vs Helpers"
        elif def_style == "PERIMETER":
            self._boost_stat(calibrated, 'proj_3pm', 0.95)
    
    # TRANSITION matchups
    elif playtype == 'TRANSITION':
        if def_style == "FUNNEL":
            self._boost_stat(calibrated, 'proj_pts', 1.15)
            calibrated['notes'] += " | Transition Chaos"
        elif def_style == "PAINT_PACK":
            self._boost_stat(calibrated, 'proj_pts', 0.92)  # Set defense
    
    # P&R_ROLL_MAN matchups
    elif playtype == 'P&R_ROLL_MAN':
        if def_style == "PAINT_PACK":
            self._boost_stat(calibrated, 'proj_pts', 1.15)
            self._boost_stat(calibrated, 'proj_fg_pct', 1.10)
            calibrated['notes'] += " | Roll Man vs Drop"
        elif def_style == "BLITZ":
            self._boost_stat(calibrated, 'proj_pts', 0.88)
    
    # OFF_BALL_CUTTER matchups
    elif playtype == 'OFF_BALL_CUTTER':
        if def_style == "PERIMETER":
            self._boost_stat(calibrated, 'proj_pts', 1.12)
            calibrated['notes'] += " | Cutter vs Small Ball"
        elif def_style == "PAINT_PACK":
            self._boost_stat(calibrated, 'proj_fg_pct', 0.90)
    
    # PUTBACK matchups
    elif playtype == 'PUTBACK':
        if def_style == "PERIMETER":
            self._boost_stat(calibrated, 'proj_oreb', 1.20)
            self._boost_stat(calibrated, 'proj_pts', 1.15)
            calibrated['notes'] += " | Putback vs Small Ball"

# === NEW: TEAM OFFENSE vs TEAM DEFENSE ===
team_off = TEAM_OFFENSIVE_TYPES.get(calibrated.get('team', ''), 'BALANCED')
opp_def = def_style

# Favorable matchups boost total
if team_off == "PACE_AND_SPACE" and opp_def == "PAINT_PACK":
    calibrated['notes'] += " | Team: Pace Edge"
elif team_off == "PAINT_ATTACK" and opp_def == "PERIMETER":
    calibrated['notes'] += " | Team: Size Edge"
elif team_off == "TRANSITION_FOCUSED" and opp_def == "FUNNEL":
    calibrated['notes'] += " | Team: Speed Edge"
```

---

## Phase 4: B2B Fatigue Integration (Research-Backed)

### Research
- **García et al. (2020):** -1.27 effect size Q1→Q4 within-game
- **Topendsports:** 2-3 point performance decline on B2B road games
- **Guards Most Affected:** Cover 5+ miles/game, pts/ast decline most

### Implementation

**Add to Module E `calibrate_player()` method:**

```python
# After matchup logic, before return:

# === NEW: B2B FATIGUE TAX ===
is_b2b = yak_report.get('is_back_to_back', False)
is_road = calibrated.get('is_road', False)
rest_days = yak_report.get('rest_days', 2)
position = calibrated.get('position', '')

if is_b2b:
    if is_road:
        # Road B2B: -6% volume (research: 2-3 pt decline)
        self._apply_factor(calibrated, 0.94)
        calibrated['notes'] += " | B2B Road Tax"
    else:
        # Home B2B: -3% volume
        self._apply_factor(calibrated, 0.97)
        calibrated['notes'] += " | B2B Home Tax"
    
    # Guard-specific penalty (cover most distance)
    if position in ['PG', 'SG', 'G']:
        self._boost_stat(calibrated, 'proj_pts', 0.96)
        self._boost_stat(calibrated, 'proj_ast', 0.95)
        calibrated['notes'] += " | Guard Fatigue"

# Rested home team advantage
elif rest_days >= 3 and not is_road:
    self._apply_factor(calibrated, 1.03)
    calibrated['notes'] += " | Rested Home Edge"
```

**Data Source:**
- Add `is_back_to_back`, `rest_days`, `is_road` to game metadata
- Calculate from schedule (Tank01 API or parse game dates)

---

## Phase 5: Blowout Tax Review

### Current System (Already Smart)
**File:** `utils/blowout_tax.py`

**Logic:**
- Starts at 10pt spread
- Scales 2%/point
- Context-aware (favorite/underdog, starter/bench)
- Floor at 70% (max -30% tax)
- Cap at 120% (max +20% boost)

### Backtest Validation
**Question:** Does current blowout tax predict blowout behavior accurately?

**Metrics to Track:**
1. **Favorite Starters** - Do they hit "Under" more often in 15+ pt spreads?
2. **Favorite Bench** - Do they hit "Over" more often (garbage time)?
3. **Tax Magnitude** - Is -10% at 15pt too aggressive/conservative?

**Post-Backtest Action:**
- If tax validates: Keep as-is ✅
- If starters still overperform: Increase tax (-12% instead of -10%)
- If bench underperforms: Reduce boost (+3% instead of +5%)

---

## Phase 6: Backtest & Validation

### Window
- **Dates:** December 20, 2025 - January 16, 2026 (28 days)
- **Games:** ~420 NBA games
- **Player-Games:** ~2,980 (assuming 87.3% tracking coverage)
- **Data Sources:** 60-day backfill (NBA API + PBP Stats)

### Comparison

**Baseline (Old System):**
- Pre-Jan 17 Module A (old EV/odds logic)
- Current Module E (no secondary playtypes, no B2B tax)

**New System:**
- Post-Jan 17 Module A (new line shopping + devigging)
- Upgraded Module E:
  - Secondary playtypes (strict thresholds)
  - 14+ new matchup modifiers
  - B2B fatigue tax
  - Team offensive type integration

### Success Criteria (Moderate Tier)

| Metric | Target | Status |
|--------|--------|--------|
| **RMSE (PTS)** | < 5.0 | Measure improvement |
| **Hit Rate** | > 53% (+2% improvement) | **Primary target** ✅ |
| **ROI** | > +4% (+3% improvement) | **Primary target** ✅ |
| **CLV** | > +4 cents | Validation metric |
| **Tag Performance** | 3+ new tags > 55% WR | Playtype validation |

**Deploy if:** Hit Rate +2% AND ROI +3% (Moderate success)

### Script

**New File:** `scripts/backtest_archetype_upgrade.py`

**Features:**
1. 3-fold cross-validation (prevent overfitting)
2. Tag performance analysis (primary + secondary)
3. Matchup validation (SPOT_UP vs PAINT_PACK, etc.)
4. B2B tax effectiveness (guards pts/ast decline)
5. Blowout tax validation (15+ pt spreads)
6. Feature importance (eFG%, TOV%, STL%)

**Output Structure:**
```
=== BACKTEST RESULTS ===
Window: Dec 20-Jan 16 (28 days, 420 games)

BASELINE (Old):
- RMSE: 5.2 | Hit Rate: 51.8% | ROI: +2.3% | CLV: +3.1c

NEW SYSTEM:
- RMSE: 4.7 (-9.6%) | Hit Rate: 54.1% (+2.3% ✅) | ROI: +5.8% (+3.5% ✅)

STATUS: TIER 1 SUCCESS - DEPLOY IMMEDIATELY

TOP TAGS:
1. SPOT_UP vs PAINT_PACK: 62.1% WR | +14.8% ROI (87 bets)
2. ISO_SCORER vs PERIMETER: 59.4% WR | +11.2% ROI (64 bets)
3. P&R_HANDLER vs PAINT_PACK: 58.7% WR | +10.3% ROI (52 bets)

NEEDS TUNING:
1. ISO_SCORER vs BLITZ: 46.3% WR (-2.8% ROI) → Reduce -8% tax to -5%

B2B VALIDATION:
- Guards B2B Road: -1.8 pts avg (vs -2.3 research = 78% accurate ✅)
- B2B Tax: 147 bets | 56.1% WR | +4.2% ROI ✅

BLOWOUT TAX:
- Favorite starters 15+ spread: 47.2% hit rate (Under edge confirmed ✅)
- Favorite bench 15+ spread: 54.8% hit rate (Over edge confirmed ✅)
```

---

## Implementation Checklist

### Week 1: Data Collection & Thresholds
- [ ] Query tracking stats (Dec 20 - Jan 19, all players)
- [ ] Validate 60-day backfill coverage (>80%)
- [ ] Calculate playtype frequency distributions
- [ ] Set strict thresholds (2 of 3 criteria per playtype)
- [ ] Create `config/playtype_thresholds.json`

### Week 2: Code Implementation
- [ ] Module E: Add `_get_tracking_stats()` helper
- [ ] Module E: Add `_assign_secondary_playtypes()` method
- [ ] Module E: Update `calibrate_player()` integration
- [ ] Module E: Expand matchup matrix (14 new modifiers)
- [ ] Module E: Add B2B fatigue logic
- [ ] Create `utils/team_offensive_classifier.py`
- [ ] Update `utils/tag_classifier.py` (8 new tags)

### Week 3: Backtest & Validation
- [ ] Create `scripts/backtest_archetype_upgrade.py`
- [ ] Run 3-fold cross-validation
- [ ] Analyze tag performance (primary + secondary)
- [ ] Validate matchup modifiers
- [ ] Validate B2B tax effectiveness
- [ ] Review blowout tax accuracy
- [ ] Tune underperforming matchups if needed

### Week 4: Deploy or Iterate
- [ ] If Moderate success (ROI +3%, Hit Rate +2%): **Deploy** ✅
- [ ] If needs tuning: Adjust modifiers, re-test
- [ ] If failure: Rollback Module E, keep Module A upgrades
- [ ] Update CLAUDE.md with new archetype system
- [ ] Schedule weekly team offensive type updates

---

## Next Steps

**Immediate Actions:**
1. Confirm 60-day backfill coverage (run query on `player_game_tracking`)
2. Choose database approach for secondary playtypes (runtime vs persistent)
3. Begin Week 1 data collection
4. Review strict threshold logic (2 of 3 criteria)

**Questions Resolved:**
- ✅ Module A changes confirmed (line shopping + devigging)
- ✅ Sim count confirmed (5,000 in Module C)
- ✅ Blowout tax confirmed (smart context-aware system)
- ✅ Backtest approach confirmed (Option A: real historical comparison)
- ✅ ROI target confirmed (Moderate: +3% ROI, +2% hit rate)
- ✅ No Synergy API access (using tracking data approximation)
- ✅ Post-up approximation acceptable
- ✅ Team offensive types: Automated weekly (mirrors defense)

**Ready to begin implementation on your signal.**
