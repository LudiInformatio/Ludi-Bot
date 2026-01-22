# Defensive Style Backtests: 60-Day + 14-Day Trends

**Date:** January 21, 2026  
**Priority:** HIGH  
**Prerequisite:** Offensive backtests complete ✅  
**Estimated Time:** 30 minutes

---

## Objective

Create matching backtest scripts for **DEFENSIVE_STYLES** classifications (PAINT_PACK, BLITZ, PERIMETER, FUNNEL, HACKERS).

Currently only offensive styles have backtests. Defensive needs the same treatment.

---

## Part 1: 60-Day Defensive Backtest

### Create `scripts/backtest_defense_styles_60day.py`

**Purpose:** Verify all 30 teams' DEFENSIVE_STYLES classifications against actual data.

**Key Data Sources:**
- `player_defense` table (509 players) - diff_pct, dfg_pct, freq_pct
- `team_lineups` table - def_rating, pace (IMPORTANT: use this for pace, NOT games.pace)
- `player_game_opponent` - opponent matchup data

**Classification Rules (from utils/team_defensive_classifier.py):**

| Defensive Style | Criteria |
|-----------------|----------|
| PAINT_PACK | opp_rim_fg_diff < -5% (forces bad rim shots) |
| BLITZ | high_press_rate > 20% OR opp_tov_rate > 15% |
| PERIMETER | opp_3p_fg_diff < -3% (denies 3s) |
| FUNNEL | low opp_3p_rate, high opp_drive_rate (funnel to rim) |
| HACKERS | opp_ft_rate > 25% (fouls a lot) |
| RIM_FORTRESS | opp_rim_fg_pct < 60% (elite) |

### Template Code:

```python
#!/usr/bin/env python3
"""
60-day backtest to verify team defensive style classifications.
Uses player_defense + team_lineups data for validation.
"""
import sys
sys.path.insert(0, '.')
import sqlite3
from module_e import LudiCalibrator

def get_team_defensive_profile(conn, team_abbr, days=60):
    """Calculate team defensive profile from available data"""
    cursor = conn.cursor()
    
    # Get opponent vs team stats from player_defense
    cursor.execute("""
        SELECT 
            AVG(diff_pct) as avg_diff_pct,
            AVG(dfg_pct) as avg_dfg_pct,
            COUNT(*) as sample_size
        FROM player_defense
        WHERE team_abbr = ?
    """, (team_abbr,))
    
    defense_data = cursor.fetchone()
    
    # Get team defensive rating from team_lineups
    cursor.execute("""
        SELECT 
            AVG(def_rating) as def_rtg,
            SUM(possessions) * 48.0 / NULLIF(SUM(minutes), 0) as pace
        FROM team_lineups
        WHERE team_abbreviation = ?
        AND game_date >= date('now', '-{} days')
    """.format(days), (team_abbr,))
    
    lineup_data = cursor.fetchone()
    
    if not defense_data or not lineup_data:
        return None, 0
    
    return {
        'avg_diff_pct': defense_data[0] or 0,
        'avg_dfg_pct': defense_data[1] or 0,
        'sample_size': defense_data[2] or 0,
        'def_rating': lineup_data[0] or 110,
        'pace': lineup_data[1] or 100
    }, defense_data[2] or 0

def backtest_60_days():
    print("=" * 70)
    print("60-DAY DEFENSIVE STYLE VERIFICATION BACKTEST")
    print("=" * 70)
    
    conn = sqlite3.connect('ludi.db')
    calib = LudiCalibrator()
    
    teams = list(calib.DEFENSIVE_STYLES.keys())
    mismatches = []
    
    print(f"Analyzing {len(teams)} teams over last 60 days...\n")
    
    for team in teams:
        assigned_style = calib.DEFENSIVE_STYLES[team]
        profile, sample_size = get_team_defensive_profile(conn, team)
        
        if profile is None:
            print(f"{team:3} | {assigned_style:12} | ⚠️ No data")
            continue
        
        # Check style consistency
        style_mismatch = False
        reason = ""
        
        # PAINT_PACK should have negative diff_pct (forcing bad rim shots)
        if assigned_style == "PAINT_PACK" and profile['avg_diff_pct'] > 0:
            style_mismatch = True
            reason = f"diff_pct {profile['avg_diff_pct']:.1f}% > 0 (not protecting rim)"
        
        # BLITZ should have lower opponent fg% (pressure working)
        elif assigned_style == "BLITZ" and profile['avg_dfg_pct'] > 48:
            style_mismatch = True
            reason = f"opp_dfg {profile['avg_dfg_pct']:.1f}% high (pressure not working?)"
        
        # Good defensive teams should have def_rating < 112
        elif profile['def_rating'] > 115 and assigned_style in ["PAINT_PACK", "PERIMETER"]:
            style_mismatch = True
            reason = f"def_rtg {profile['def_rating']:.1f} (elite style but poor rating)"
        
        status = "⚠️" if style_mismatch else "✅"
        print(f"{team:3} | {assigned_style:12} | diff%: {profile['avg_diff_pct']:+5.1f} | "
              f"dfg%: {profile['avg_dfg_pct']:4.1f} | def_rtg: {profile['def_rating']:.1f} | {status}")
        
        if style_mismatch:
            mismatches.append({'team': team, 'style': assigned_style, 'reason': reason})
    
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    
    mismatch_rate = (len(mismatches) / len(teams)) * 100 if teams else 0
    print(f"Teams analyzed: {len(teams)}")
    print(f"Style mismatches: {len(mismatches)} ({mismatch_rate:.1f}%)")
    
    if mismatches:
        print(f"\n⚠️ POTENTIAL MISCLASSIFICATIONS:")
        for m in mismatches:
            print(f"  {m['team']:3} ({m['style']:12}): {m['reason']}")
    
    print(f"\n✅ Target mismatch rate: <10%")
    print(f"   Current rate: {mismatch_rate:.1f}%")
    
    conn.close()
    return mismatch_rate < 10

if __name__ == "__main__":
    success = backtest_60_days()
    sys.exit(0 if success else 1)
```

---

## Part 2: 14-Day Defensive Trends

### Create `scripts/backtest_defense_styles_14day.py`

**Purpose:** Detect teams that changed defensive approach in last 2 weeks.

**Key Data:** Use `team_lineups.def_rating` for trend comparison.

**Important:** Use `team_lineups` for pace, NOT `games.pace` (which is empty!)

### Template Code:

```python
#!/usr/bin/env python3
"""
14-day recent trends backtest for defensive styles.
Identifies teams with changing defensive schemes.
"""
import sys
sys.path.insert(0, '.')
import sqlite3
from module_e import LudiCalibrator

def get_defensive_trend(conn, team_abbr, recent_days=14, prior_days=46):
    """Compare recent vs prior defensive rating and tendencies"""
    cursor = conn.cursor()
    
    # Recent period - from team_lineups (NOT games.pace)
    cursor.execute("""
        SELECT 
            AVG(def_rating) as def_rtg,
            SUM(possessions) * 48.0 / NULLIF(SUM(minutes), 0) as pace
        FROM team_lineups
        WHERE team_abbreviation = ?
        AND game_date >= date('now', '-{} days')
    """.format(recent_days), (team_abbr,))
    
    recent = cursor.fetchone()
    recent_def_rtg = recent[0] or 0
    recent_pace = recent[1] or 0
    
    # Prior period
    cursor.execute("""
        SELECT 
            AVG(def_rating) as def_rtg,
            SUM(possessions) * 48.0 / NULLIF(SUM(minutes), 0) as pace
        FROM team_lineups
        WHERE team_abbreviation = ?
        AND game_date >= date('now', '-{} days')
        AND game_date < date('now', '-{} days')
    """.format(recent_days + prior_days, recent_days), (team_abbr,))
    
    prior = cursor.fetchone()
    prior_def_rtg = prior[0] or 0
    prior_pace = prior[1] or 0
    
    return {
        'recent_def_rtg': recent_def_rtg,
        'prior_def_rtg': prior_def_rtg,
        'recent_pace': recent_pace,
        'prior_pace': prior_pace
    }

def analyze_defensive_trends():
    print("=" * 70)
    print("14-DAY DEFENSIVE TRENDS ANALYSIS")
    print("=" * 70)
    
    conn = sqlite3.connect('ludi.db')
    calib = LudiCalibrator()
    
    teams = list(calib.DEFENSIVE_STYLES.keys())
    teams_to_watch = []
    
    print(f"Analyzing defensive trends for {len(teams)} teams...\n")
    
    for team in teams:
        assigned_style = calib.DEFENSIVE_STYLES[team]
        trend = get_defensive_trend(conn, team)
        
        if not trend['prior_def_rtg'] or not trend['recent_def_rtg']:
            continue
        
        # Calculate changes
        def_rtg_change = trend['recent_def_rtg'] - trend['prior_def_rtg']
        
        # Significant change = >5 points defensive rating
        significant_change = abs(def_rtg_change) > 5
        
        change_type = "Stable"
        if def_rtg_change < -5:
            change_type = f"Improving ({def_rtg_change:+.1f})"
        elif def_rtg_change > 5:
            change_type = f"Declining ({def_rtg_change:+.1f})"
        
        status = "⚠️" if significant_change else "✅"
        print(f"{team:3} | {assigned_style:12} | {change_type:20} | "
              f"DefRtg: {trend['prior_def_rtg']:.1f}→{trend['recent_def_rtg']:.1f} | {status}")
        
        if significant_change:
            teams_to_watch.append({
                'team': team,
                'style': assigned_style,
                'change': def_rtg_change,
                'recent': trend['recent_def_rtg'],
                'prior': trend['prior_def_rtg']
            })
    
    print("\n" + "=" * 70)
    print("TEAMS WITH SIGNIFICANT DEFENSIVE CHANGES")
    print("=" * 70)
    
    if teams_to_watch:
        for t in teams_to_watch:
            direction = "IMPROVING 📈" if t['change'] < 0 else "DECLINING 📉"
            print(f"🏀 {t['team']} ({t['style']}): {direction}")
            print(f"   DefRtg: {t['prior']:.1f} → {t['recent']:.1f} ({t['change']:+.1f})")
            
            # Suggest reclassification if needed
            if t['change'] < -7 and t['style'] not in ["PAINT_PACK", "PERIMETER"]:
                print(f"   💡 Consider upgrade to elite defense classification")
            elif t['change'] > 7 and t['style'] in ["PAINT_PACK", "PERIMETER"]:
                print(f"   💡 Consider downgrade - elite status may be outdated")
            print()
    else:
        print("✅ No significant defensive changes in last 14 days")
    
    conn.close()
    return teams_to_watch

if __name__ == "__main__":
    teams_to_watch = analyze_defensive_trends()
```

---

## Part 3: Run All Backtests

After creating both scripts, run all 4 backtests:

```bash
# Offensive backtests
python3 scripts/backtest_team_styles_60day.py
python3 scripts/backtest_team_styles_14day.py

# Defensive backtests
python3 scripts/backtest_defense_styles_60day.py
python3 scripts/backtest_defense_styles_14day.py
```

---

## Success Criteria

- [ ] `backtest_defense_styles_60day.py` created and runs
- [ ] `backtest_defense_styles_14day.py` created and runs
- [ ] Uses `team_lineups` for pace (NOT `games.pace`)
- [ ] 60-day mismatch rate <10%
- [ ] 14-day trends identifies any significant changes
- [ ] Report summary of all 4 backtests

---

## Data Tables Reference

| Table | Key Columns | Records |
|-------|-------------|---------|
| `player_defense` | team_abbr, diff_pct, dfg_pct | 509 |
| `team_lineups` | team_abbreviation, def_rating, pace, possessions, minutes | 10,875 |
| `player_game_opponent` | opponent data | varies |

**IMPORTANT:** Always use `team_lineups` for pace calculation:
```sql
SUM(possessions) * 48.0 / NULLIF(SUM(minutes), 0) as pace
```

Do NOT use `games.pace` (it's empty!)

---

## Deliverables

1. `scripts/backtest_defense_styles_60day.py` (working script)
2. `scripts/backtest_defense_styles_14day.py` (working script)
3. Summary report of all 4 backtest results:
   - Offensive 60-day: X% mismatch
   - Offensive 14-day: X teams with changes
   - Defensive 60-day: X% mismatch
   - Defensive 14-day: X teams with changes

**Estimated Time:** 30 minutes
