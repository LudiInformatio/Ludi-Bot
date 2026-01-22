# Team Pace Data - Available in Database

**Date:** January 21, 2026  
**Issue:** Agent hit snag - thought pace data was missing  
**Resolution:** Pace data exists in `team_lineups` table  

---

## Data Discovery

### Where Pace Data Lives

```sql
-- team_lineups table has pace/possessions/minutes
SELECT team_abbreviation, AVG(pace), SUM(possessions), SUM(minutes)
FROM team_lineups
WHERE game_date >= date('now', '-60 days')
GROUP BY team_abbreviation
```

**Records with pace:** 10,875 lineup records  
**Date range:** Nov 2025 - Jan 2026

---

## Calculated Team Pace (60-Day Window)

**Formula:** `SUM(possessions) * 48.0 / SUM(minutes) = pace per 48 min`

### FASTEST Teams (>106):
| Team | Pace | Recommendation |
|------|------|----------------|
| ATL | 108.1 | PACE_PUSH or MOTION |
| CHI | 107.6 | **PACE_PUSH** ✅ |
| MIA | 107.1 | Consider PACE_PUSH? |
| UTA | 106.7 | **PACE_PUSH** ✅ |
| WAS | 106.6 | **PACE_PUSH** ✅ |

### SLOWEST Teams (<102):
| Team | Pace | Recommendation |
|------|------|----------------|
| BOS | 101.1 | **HALF_COURT** ✅ |
| HOU | 101.0 | HALF_COURT? |
| DEN | 101.2 | HALF_COURT or MOTION |
| BKN | 101.4 | HALF_COURT |
| MIL | 102.3 | NEUTRAL |

### Notable Comparisons to Web Research:

| Team | Web Claim | Our DB | Match? |
|------|-----------|--------|--------|
| MEM | 95.4 (slowest) | 105.4 | ❌ Different |
| UTA | 101.8 (fastest) | 106.7 | ✅ Fast |
| CHI | 101.5 (#2 fast) | 107.6 | ✅ Fast |
| WAS | 101.1 (#3 fast) | 106.6 | ✅ Fast |
| BOS | 95.7 (slow) | 101.1 | ✅ Slow |
| PHX | PACE_PUSH | 102.5 | ❓ Medium |

**Note:** Our DB uses lineup-level possessions calculation. Web sources may use different methodology.

---

## Updated Dynamic Classifier

**Use `team_lineups` for dynamic classification:**

```python
def classify_team_offense(self, team_abbr: str) -> str:
    """Dynamically classify team offensive style using team_lineups data."""
    try:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Calculate pace from lineups (last 30 days)
        cursor.execute("""
            SELECT 
                SUM(possessions) * 48.0 / NULLIF(SUM(minutes), 0) as pace,
                AVG(off_rating) as ortg,
                AVG(ast_pct) as ast_pct
            FROM team_lineups
            WHERE team_abbreviation = ?
            AND game_date >= date('now', '-30 days')
        """, (team_abbr,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row and row[0]:
            pace = row[0]
            ortg = row[1] or 110
            ast_pct = row[2] or 0.25
            
            # Classification thresholds (based on 60-day DB analysis)
            if pace > 106:
                return "PACE_PUSH"
            elif pace < 102:
                return "HALF_COURT"
            elif ast_pct > 0.28 and ortg > 115:
                return "MOTION"
            
        return self.OFFENSIVE_STYLES.get(team_abbr, "NEUTRAL")
        
    except Exception as e:
        return self.OFFENSIVE_STYLES.get(team_abbr, "NEUTRAL")
```

---

## Action for Agent

1. **Update `classify_team_offense()`** to query `team_lineups` table
2. **Adjust thresholds** based on our DB data:
   - PACE_PUSH: pace > 106 (not 103 or 100)
   - HALF_COURT: pace < 102 (not 97)
3. **Run backtest** with new data-driven logic
4. **Compare** DB classifications vs static dict

---

**Summary:** We have the data! Just needed correct query.
