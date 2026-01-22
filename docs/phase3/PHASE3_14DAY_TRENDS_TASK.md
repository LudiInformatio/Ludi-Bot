# Phase 3 Expansion: 14-Day Playtype Trends Task

**Date:** January 21, 2026  
**Task Owner:** [Agent to be assigned]  
**Priority:** MEDIUM  
**Estimated Time:** 20-30 minutes  

---

## Mission

Run a **14-day trend analysis** for Secondary Playtype Matchups to identify recent shifts in how often these modifiers are triggering (e.g., changes in team defensive schemes over the last 2 weeks).

---

## Background

The user requested: *"i see you ran a 60 backtest did you do a 14 day also to spot any trends?"*

We ran a 30-day sensitivity analysis ("sensitivity analysis" labeled as "backtest"), but a dedicated 14-day view will help spot:
1. **Recent Defensive Shifts:** Teams playing more BLITZ or PAINT_PACK recently.
2. **Recent Player Usage:** Changes in secondary playtype assignment.

---

## Technical Implementation

### 1. Create `scripts/backtest_playtype_trends_14day.py`

Clone the existing `backtest_playtype_matchups.py` but modify it to:
- Look back only **14 days**.
- Report **Trend Frequency** compared to the 30-day baseline.
- Highlight specific **"Hot Matchups"** (e.g., "Luka facing 3 BLITZ defenses in last 5 games").

### Code Template

```python
#!/usr/bin/env python3
"""
14-Day Trend Analysis for Secondary Playtype Matchups.
Identifies recent spikes in specific playtype-defense interactions.
"""
import sys
sys.path.insert(0, '.')

from module_e import LudiCalibrator
import sqlite3
from datetime import datetime, timedelta

def run_14day_trends():
    print("=" * 70)
    print("PHASE 3: 14-DAY PLAYTYPE TRENDS ANALYSIS")
    print("=" * 70)
    
    calib = LudiCalibrator(debug_log=False)
    
    # 1. Get recent games (Last 14 days)
    conn = sqlite3.connect('ludi.db')
    cursor = conn.cursor()
    cutoff_date = (datetime.now() - timedelta(days=14)).strftime('%Y-%m-%d')
    
    print(f"📅 Analyzing games since {cutoff_date}...")
    
    query = """
    SELECT DISTINCT game_date, team_abbreviation, matchup 
    FROM player_game_logs 
    WHERE game_date >= ?
    AND team_abbreviation IS NOT NULL
    AND matchup IS NOT NULL
    ORDER BY game_date DESC
    """
    cursor.execute(query, (cutoff_date,))
    games = cursor.fetchall()
    conn.close()
    
    print(f"📊 Found {len(games)} team-games in window.")
    
    if not games:
        print("❌ No data found.")
        return

    # 2. Simulate Matchups
    # (We will check how often specific matchups WOULD have fired)
    
    matchup_counts = {
        "ISO_SCORER vs BLITZ": 0,
        "SPOT_UP vs PAINT_PACK": 0,
        "P&R_ROLL_MAN vs PAINT_PACK": 0,
        "TRANSITION vs FUNNEL": 0,
        "TOTAL_GAMES": len(games)
    }
    
    # Note: Accuracy requires scanning ALL players in these games, 
    # but for trends we can simulate against known player archetypes 
    # OR checking the team defense distribution.
    
    # Let's analyze the DEFENSE distribution in the last 14 days
    def_counts = {}
    for _, _, matchup in games:
        # Matchup string format might vary, assuming team abbr or parsing lookup
        # Actually need to get defense style for the OPPONENT
        # In player_game_logs, 'matchup' is "GSW vs LAL" or "GSW @ LAL". 
        # Simpler: Use the 'opponent' column if available (or parse matchup)
        # Wait, previous script used 'matchup' column which works.
        pass
        
    print("... [Complete Logic to be implemented by Agent] ...")
    
    # OUTPUT:
    # "Trending Defense: PHX (BLITZ) - Frequency up 20%"
    # "Hot Matchup: ISO_SCORER vs BLITZ occurring 15% more often"

if __name__ == "__main__":
    run_14day_trends()
```

---

## Deliverables

1.  **Script:** `scripts/backtest_playtype_trends_14day.py`
2.  **Report:** Terminal output showing:
    - Most common defensive styles seen in last 14 days.
    - Which Phase 3 matchups are triggering most frequently.
    - Identification of any "Trend Alerts" (e.g. sharp rise in BLITZ coverage).

---

**Estimated Time:** 20 mins
