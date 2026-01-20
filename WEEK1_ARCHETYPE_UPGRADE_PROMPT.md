# Week 1: Archetype Upgrade - Data Collection & Thresholds

**Date:** January 19, 2026 @ 07:57 PM EST  
**Phase:** Data Collection & Threshold Calibration  
**Context:** Archetype Synergy Upgrade Plan (see `ARCHETYPE_SYNERGY_UPGRADE_PLAN.md`)

---

## Your Mission

You are implementing **Week 1** of the Archetype Synergy Upgrade Plan. This week focuses on **Data Collection & Threshold Calibration** for 8 new secondary playtypes that will enhance our betting model's accuracy.

**Goal:** Validate data coverage, calculate playtype frequency distributions, and set strict thresholds that prevent tag pollution.

---

## Background (Read First)

### What We're Building
We're upgrading Module E (Calibrator) to add **secondary playtypes** that mirror NBA Synergy classifications:
1. ISO_SCORER - Isolation efficiency
2. P&R_HANDLER - Pick & roll ball handler
3. P&R_ROLL_MAN - Pick & roll finisher
4. SPOT_UP - Catch & shoot specialist
5. OFF_BALL_CUTTER - Backdoor/cut specialist
6. TRANSITION - Fast break threat
7. PUTBACK - Offensive rebound finisher
8. POST_UP - Back-to-basket scoring

### Critical Design Principle
**Strict Thresholds:** Players must meet **2 of 3 criteria** for each playtype to prevent tag pollution. Without this, every player would populate every tag.

### Data Available
We have **60 days of backfilled data** (Nov 21, 2025 - Jan 19, 2026) from Ghost Protocol:
- `player_game_tracking` - drives, catch_shoot, pull_up, speed, distance (~14,700 records)
- `player_game_advanced` - off_rating, def_rating, ts_pct
- `player_shot_quality` - rim_freq, corner_3_freq, shot quality (from PBP Stats API)
- `team_lineups` - WOWY data (9,314 records with possessions)

---

## Week 1 Tasks

### Task 1: Validate Data Coverage
**Goal:** Confirm we have >80% tracking data coverage for backtest reliability.

**Steps:**
1. Query `player_game_tracking` table for Dec 20, 2025 - Jan 19, 2026 window
2. Calculate:
   - Total player-games in window (approx ~2,980)
   - Games with tracking data
   - Coverage % (need >80%)
3. Identify any coverage gaps (missing players, missing dates)

**SQL Query:**
```sql
-- Total player-games with tracking data in backtest window
SELECT 
    COUNT(DISTINCT player_name || game_date) as player_games_with_tracking,
    COUNT(DISTINCT player_name) as unique_players,
    MIN(game_date) as earliest_date,
    MAX(game_date) as latest_date
FROM player_game_tracking
WHERE game_date BETWEEN '2025-12-20' AND '2026-01-19';

-- Check for missing dates (should be ~30 game days)
SELECT 
    DATE(game_date) as game_day,
    COUNT(DISTINCT player_name) as players
FROM player_game_tracking
WHERE game_date BETWEEN '2025-12-20' AND '2026-01-19'
GROUP BY DATE(game_date)
ORDER BY game_day;
```

**Acceptance Criteria:**
- Coverage ≥ 80% ✅
- No gaps > 3 consecutive days
- At least 400+ unique players with tracking data

---

### Task 2: Calculate Playtype Frequency Distributions
**Goal:** Understand the distribution of each tracking stat to set realistic thresholds.

**Steps:**
1. Query average tracking stats per player (L20 games)
2. Calculate percentiles (P25, P50, P75, P90) for each metric
3. Identify "elite" thresholds (top 25% of players)

**SQL Query:**
```sql
-- Player averages with percentiles
WITH player_avgs AS (
    SELECT 
        player_name,
        AVG(drives) as avg_drives,
        AVG(catch_shoot_fga) as avg_cs_fga,
        AVG(CAST(catch_shoot_fgm AS FLOAT) / NULLIF(catch_shoot_fga, 0)) as cs_pct,
        AVG(pull_up_fga) as avg_pu_fga,
        AVG(speed) as avg_speed,
        AVG(distance) as avg_distance,
        COUNT(*) as games
    FROM player_game_tracking
    WHERE game_date >= date('now', '-60 days')
    GROUP BY player_name
    HAVING games >= 10  -- Min 10 games
)
SELECT 
    'drives' as metric,
    COUNT(*) as total_players,
    ROUND(AVG(avg_drives), 2) as mean,
    ROUND(MIN(avg_drives), 2) as min,
    ROUND(MAX(avg_drives), 2) as max,
    -- Percentiles (approximate)
    (SELECT ROUND(avg_drives, 2) FROM player_avgs ORDER BY avg_drives LIMIT 1 OFFSET (SELECT COUNT(*) * 0.25 FROM player_avgs)) as p25,
    (SELECT ROUND(avg_drives, 2) FROM player_avgs ORDER BY avg_drives LIMIT 1 OFFSET (SELECT COUNT(*) * 0.50 FROM player_avgs)) as p50,
    (SELECT ROUND(avg_drives, 2) FROM player_avgs ORDER BY avg_drives LIMIT 1 OFFSET (SELECT COUNT(*) * 0.75 FROM player_avgs)) as p75,
    (SELECT ROUND(avg_drives, 2) FROM player_avgs ORDER BY avg_drives LIMIT 1 OFFSET (SELECT COUNT(*) * 0.90 FROM player_avgs)) as p90
FROM player_avgs;

-- Repeat for: catch_shoot_fga, cs_pct, pull_up_fga, speed, distance
```

**Python Analysis Script (Create):**
```python
# scripts/analyze_playtype_distributions.py
import sqlite3
import pandas as pd
import numpy as np

conn = sqlite3.connect('ludi.db')

# Query player averages
query = """
SELECT 
    player_name,
    AVG(drives) as avg_drives,
    AVG(catch_shoot_fga) as avg_cs_fga,
    AVG(CAST(catch_shoot_fgm AS FLOAT) / NULLIF(catch_shoot_fga, 0)) as cs_pct,
    AVG(pull_up_fga) as avg_pu_fga,
    AVG(speed) as avg_speed,
    AVG(distance) as avg_distance,
    COUNT(*) as games
FROM player_game_tracking
WHERE game_date >= date('now', '-60 days')
GROUP BY player_name
HAVING games >= 10
"""

df = pd.read_sql(query, conn)
conn.close()

# Calculate percentiles for each metric
metrics = ['avg_drives', 'avg_cs_fga', 'cs_pct', 'avg_pu_fga', 'avg_speed', 'avg_distance']

print("=" * 80)
print("PLAYTYPE THRESHOLD ANALYSIS")
print("=" * 80)
print(f"Total Players (10+ games): {len(df)}")
print()

for metric in metrics:
    print(f"\n{metric.upper()}:")
    print(f"  Mean: {df[metric].mean():.2f}")
    print(f"  Median (P50): {df[metric].median():.2f}")
    print(f"  P25: {df[metric].quantile(0.25):.2f}")
    print(f"  P75: {df[metric].quantile(0.75):.2f}")
    print(f"  P90 (Elite): {df[metric].quantile(0.90):.2f}")
    print(f"  Proposed Threshold: ???")  # You'll fill this in

# Show example players at each threshold
print("\n" + "=" * 80)
print("SAMPLE PLAYERS AT PROPOSED THRESHOLDS")
print("=" * 80)

# ISO_SCORER candidates (drives > 8, pull_up_fga > 5)
iso_candidates = df[(df['avg_drives'] > 8) & (df['avg_pu_fga'] > 5)]
print(f"\nISO_SCORER Candidates: {len(iso_candidates)} players")
print(iso_candidates[['player_name', 'avg_drives', 'avg_pu_fga']].head(10).to_string(index=False))

# SPOT_UP candidates (catch_shoot_fga > 4, cs_pct > 0.38)
spot_candidates = df[(df['avg_cs_fga'] > 4) & (df['cs_pct'] > 0.38)]
print(f"\nSPOT_UP Candidates: {len(spot_candidates)} players")
print(spot_candidates[['player_name', 'avg_cs_fga', 'cs_pct']].head(10).to_string(index=False))

# TRANSITION candidates (speed > 4.5, distance > 2.3)
trans_candidates = df[(df['avg_speed'] > 4.5) & (df['avg_distance'] > 2.3)]
print(f"\nTRANSITION Candidates: {len(trans_candidates)} players")
print(trans_candidates[['player_name', 'avg_speed', 'avg_distance']].head(10).to_string(index=False))
```

**Run:**
```bash
python scripts/analyze_playtype_distributions.py
```

**Acceptance Criteria:**
- Distributions for all 6 key metrics calculated ✅
- Proposed thresholds identify 15-30% of players per playtype ✅
- Sample players at thresholds match expected names (e.g., Luka for ISO_SCORER) ✅

---

### Task 3: Set Strict Thresholds
**Goal:** Finalize thresholds that meet "2 of 3 criteria" rule and prevent tag pollution.

**Proposed Thresholds (From Plan):**
Based on research and Synergy benchmarks:

| Playtype | Criterion 1 | Criterion 2 | Criterion 3 |
|----------|------------|------------|------------|
| ISO_SCORER | drives > 8/game | pull_up_fga > 5/game | usg > 0.28 |
| P&R_HANDLER | drives > 5/game | ast > 6.0 | catch_shoot_fga < pull_up_fga |
| P&R_ROLL_MAN | rim_freq > 0.40 | catch_shoot_fga > pull_up_fga | ast < 3.0 |
| SPOT_UP | catch_shoot_fga > 4/game | catch_shoot_pct > 0.38 | 3pm > 1.5 |
| OFF_BALL_CUTTER | rim_fg_pct > 0.65 | catch_shoot_fga > pull_up_fga | drives < 4/game |
| TRANSITION | speed > 4.5 mph | distance > 2.3 miles/game | team_pace > 102 OR fast_break_pts > 3 |
| PUTBACK | oreb > 2.5 | rim_freq > 0.50 | rim_fga > 5 |
| POST_UP | paint_pts > 12 | rim_freq > 0.45 | speed < 4.0 mph |

**Your Task:**
1. Validate each threshold against your distribution analysis
2. Adjust if needed (e.g., if drives > 8 catches 50% of players, increase to 10)
3. Test "2 of 3" rule: Run simulation to see how many players qualify for each tag
4. Ensure no player qualifies for ALL 8 tags (max should be 2-3)

**Test Script (Create):**
```python
# scripts/test_playtype_thresholds.py
import sqlite3
import pandas as pd

# Load your final thresholds
THRESHOLDS = {
    'ISO_SCORER': {'drives': 8, 'pull_up_fga': 5, 'usg': 0.28},
    'SPOT_UP': {'catch_shoot_fga': 4, 'catch_shoot_pct': 0.38, '3pm': 1.5},
    # ... add all 8
}

conn = sqlite3.connect('ludi.db')

# Query player data
# ... (combine tracking + season stats)

# Apply thresholds with "2 of 3" rule
results = {}
for player in players:
    tags = []
    
    # ISO_SCORER (2 of 3)
    iso_criteria = [
        player['drives'] > THRESHOLDS['ISO_SCORER']['drives'],
        player['pull_up_fga'] > THRESHOLDS['ISO_SCORER']['pull_up_fga'],
        player['usg'] > THRESHOLDS['ISO_SCORER']['usg']
    ]
    if sum(iso_criteria) >= 2:
        tags.append('ISO_SCORER')
    
    # ... repeat for all 8 playtypes
    
    results[player['name']] = tags

# Analysis
print("THRESHOLD VALIDATION")
print("=" * 80)
for playtype in THRESHOLDS.keys():
    count = sum(1 for tags in results.values() if playtype in tags)
    print(f"{playtype}: {count} players ({count/len(results)*100:.1f}%)")

print("\nPlayers with ALL 8 tags (should be 0):")
max_tags = max(len(tags) for tags in results.values())
print(f"Max tags per player: {max_tags}")

print("\nSample Tag Assignments:")
for name, tags in list(results.items())[:20]:
    print(f"{name}: {', '.join(tags) if tags else 'NONE'}")
```

**Acceptance Criteria:**
- Each playtype captures 15-30% of players ✅
- No player has more than 3 secondary tags ✅
- Sample players match expected playstyles (Luka = ISO_SCORER, Duncan Robinson = SPOT_UP) ✅
- Thresholds documented in `config/playtype_thresholds.json` ✅

---

### Task 4: Create Configuration File
**Goal:** Store finalized thresholds in a JSON config file for Module E integration.

**File:** `config/playtype_thresholds.json`

```json
{
  "version": "1.0",
  "updated": "2026-01-19",
  "description": "Strict thresholds for secondary playtype assignment (2 of 3 criteria rule)",
  "playtypes": {
    "ISO_SCORER": {
      "criteria": {
        "drives_per_game": 8.0,
        "pull_up_fga_per_game": 5.0,
        "usage_rate": 0.28
      },
      "rule": "Must meet 2 of 3 criteria",
      "expected_coverage": "15-20% of players",
      "examples": ["Luka Doncic", "Jayson Tatum", "Shai Gilgeous-Alexander"]
    },
    "P&R_HANDLER": {
      "criteria": {
        "drives_per_game": 5.0,
        "assists_per_game": 6.0,
        "catch_shoot_less_than_pull_up": true
      },
      "rule": "Must meet 2 of 3 criteria",
      "expected_coverage": "12-18% of players",
      "examples": ["James Harden", "Trae Young", "Chris Paul"]
    },
    "P&R_ROLL_MAN": {
      "criteria": {
        "rim_frequency": 0.40,
        "catch_shoot_greater_than_pull_up": true,
        "assists_per_game_max": 3.0
      },
      "rule": "Must meet 2 of 3 criteria",
      "expected_coverage": "10-15% of players",
      "examples": ["Anthony Davis", "Clint Capela", "Nic Claxton"]
    },
    "SPOT_UP": {
      "criteria": {
        "catch_shoot_fga_per_game": 4.0,
        "catch_shoot_pct": 0.38,
        "three_pointers_per_game": 1.5
      },
      "rule": "Must meet 2 of 3 criteria",
      "expected_coverage": "20-25% of players",
      "examples": ["Duncan Robinson", "Klay Thompson", "Joe Harris"]
    },
    "OFF_BALL_CUTTER": {
      "criteria": {
        "rim_fg_pct": 0.65,
        "catch_shoot_greater_than_pull_up": true,
        "drives_per_game_max": 4.0
      },
      "rule": "Must meet 2 of 3 criteria",
      "expected_coverage": "10-15% of players",
      "examples": ["Dorian Finney-Smith", "Gary Payton II", "Bruce Brown"]
    },
    "TRANSITION": {
      "criteria": {
        "speed_mph": 4.5,
        "distance_miles_per_game": 2.3,
        "team_pace_or_fastbreak": "team_pace > 102 OR fast_break_pts > 3"
      },
      "rule": "Must meet 2 of 3 criteria",
      "expected_coverage": "15-20% of players",
      "examples": ["De'Aaron Fox", "Giannis Antetokounmpo", "Tyrese Maxey"]
    },
    "PUTBACK": {
      "criteria": {
        "oreb_per_game": 2.5,
        "rim_frequency": 0.50,
        "rim_fga_per_game": 5.0
      },
      "rule": "Must meet 2 of 3 criteria",
      "expected_coverage": "8-12% of players",
      "examples": ["Andre Drummond", "Ivica Zubac", "Isaiah Hartenstein"]
    },
    "POST_UP": {
      "criteria": {
        "paint_points_per_game": 12.0,
        "rim_frequency": 0.45,
        "speed_mph_max": 4.0
      },
      "rule": "Must meet 2 of 3 criteria",
      "expected_coverage": "10-15% of players",
      "examples": ["Joel Embiid", "Nikola Jokic", "Nikola Vucevic"],
      "note": "Approximation (no direct paint touches data)"
    }
  },
  "data_sources": {
    "player_game_tracking": "drives, catch_shoot, pull_up, speed, distance",
    "player_game_advanced": "off_rating, def_rating, ts_pct",
    "player_shot_quality": "rim_freq, corner_3_freq, rim_fg_pct",
    "season_stats": "pts, reb, ast, 3pm, usg, oreb"
  },
  "validation": {
    "backtest_window": "2025-12-20 to 2026-01-19",
    "min_games": 10,
    "target_roi_improvement": 0.03,
    "target_hit_rate_improvement": 0.02
  }
}
```

---

### Task 5: Generate Week 1 Summary Report
**Goal:** Document findings for review before Week 2 implementation.

**File:** `docs/WEEK1_ARCHETYPE_SUMMARY.md`

**Contents:**
```markdown
# Week 1 Summary: Archetype Upgrade - Data Collection & Thresholds

**Date:** [Your completion date]
**Status:** COMPLETE / NEEDS REVIEW

## Data Coverage Validation
- Total player-games with tracking: XXX
- Unique players: XXX
- Coverage %: XX.X%
- Date range: 2025-12-20 to 2026-01-19
- Status: ✅ / ⚠️ / ❌

[Include any coverage gaps or concerns]

## Playtype Frequency Distributions

### Drives (ISO_SCORER)
- Mean: X.X drives/game
- P50: X.X | P75: X.X | P90: X.X
- Proposed Threshold: 8.0 drives/game
- Players meeting threshold: XX (XX%)

[Repeat for all 8 playtypes]

## Threshold Validation Results

### Tag Assignment Summary
| Playtype | Players | Coverage % | Expected % | Status |
|----------|---------|------------|------------|--------|
| ISO_SCORER | XX | XX% | 15-20% | ✅ / ⚠️ |
| P&R_HANDLER | XX | XX% | 12-18% | ✅ / ⚠️ |
| P&R_ROLL_MAN | XX | XX% | 10-15% | ✅ / ⚠️ |
| SPOT_UP | XX | XX% | 20-25% | ✅ / ⚠️ |
| OFF_BALL_CUTTER | XX | XX% | 10-15% | ✅ / ⚠️ |
| TRANSITION | XX | XX% | 15-20% | ✅ / ⚠️ |
| PUTBACK | XX | XX% | 8-12% | ✅ / ⚠️ |
| POST_UP | XX | XX% | 10-15% | ✅ / ⚠️ |

### Sample Tag Assignments (Top 20 Players)
[List player name + their assigned secondary tags]

### Tag Pollution Check
- Max tags per player: X
- Players with 4+ tags: X (should be 0)
- Players with 0 tags: XX%
- Status: ✅ Tag pollution prevented

## Configuration Files Created
- ✅ `config/playtype_thresholds.json` (finalized thresholds)
- ✅ `scripts/analyze_playtype_distributions.py` (distribution analysis)
- ✅ `scripts/test_playtype_thresholds.py` (threshold validation)

## Issues / Adjustments Made
[Document any threshold adjustments, data quality issues, or concerns]

## Recommendations for Week 2
[Any notes for the implementation phase]

## Ready for Week 2?
- [ ] YES - Thresholds validated, data coverage sufficient
- [ ] NO - Issues to resolve first (describe below)

[Additional notes]
```

---

## Deliverables Checklist

At the end of Week 1, you should have:

- [ ] **Data Coverage Report** - Confirmed >80% tracking data coverage
- [ ] **Distribution Analysis** - Percentiles calculated for all 6 key metrics
- [ ] **Threshold Validation** - "2 of 3" rule tested, tag pollution prevented
- [ ] **Config File** - `config/playtype_thresholds.json` created with final thresholds
- [ ] **Analysis Scripts** - `analyze_playtype_distributions.py` and `test_playtype_thresholds.py`
- [ ] **Week 1 Summary** - `docs/WEEK1_ARCHETYPE_SUMMARY.md` documenting findings

---

## Important Context

### Current System State
- **Module C (Oracle):** Already running 5,000 simulations ✅
- **Module E (Calibrator):** Has 11 primary archetypes, needs secondary playtypes
- **Blowout Tax:** Smart context-aware system already implemented (`utils/blowout_tax.py`)
- **Database:** `ludi.db` contains all backfilled tracking data (60 days)

### What You're NOT Doing (Yet)
- **Week 2:** Code implementation in Module E
- **Week 3:** Backtest validation
- **Week 4:** Deployment

Focus ONLY on data validation and threshold calibration this week.

---

## Questions?

If you encounter issues:
1. Check `ARCHETYPE_SYNERGY_UPGRADE_PLAN.md` (full 767-line plan)
2. Check `CLAUDE.md` (project context)
3. Query the database to verify data availability
4. Adjust thresholds if distributions don't match expectations

**Remember:** The goal is to set thresholds that are **strict enough** to prevent tag pollution (every player getting every tag) but **loose enough** to capture meaningful player archetypes (15-30% of players per tag).

---

**Good luck with Week 1! Report back with your findings for review before proceeding to Week 2.**
