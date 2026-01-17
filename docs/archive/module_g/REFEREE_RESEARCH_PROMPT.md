# Referee Research Prompt

## Objective
Research 12 NBA referees currently missing from our database and provide their estimated foul-calling statistics for the 2025-26 season.

---

## Research Instructions

I need you to research the following 12 NBA referees and provide their officiating statistics for the 2025-26 season. For each referee, please find:

1. **Background**: Are they a rookie ref, veteran, G-League callup, or international official?
2. **Games Officiated**: How many NBA games have they worked this season (2025-26)?
3. **Average Fouls Per Game**: If available, what's their average total fouls called per game?
4. **Style Classification**: Based on available data, are they STRICT (>23 fouls/game), NEUTRAL (20-23 fouls/game), or LENIENT (<20 fouls/game)?
5. **Over/Under Betting Record**: If available from betting sites, what's their O/U record this season?

---

## Referees to Research

### Group 1: Likely Rookies/New Officials
1. **JT Orr**
2. **Justin Van Duyne**
3. **Jonathan Sterling**
4. **Matt Kallio**

### Group 2: International Officials
5. **Gediminas Petraitis**
6. **Marat Kogut**

### Group 3: Female Official
7. **Jenna Schroeder**

### Group 4: Veterans (Should Have Data)
8. **Che Flores**
9. **Biniam Maru**
10. **Pat O'Connell**
11. **Sean Corbin**
12. **Suyash Mehta**

---

## Recommended Data Sources

Use the following sources in order of priority:

### Primary Sources (Most Reliable)
1. **RealGM NBA Referees**: https://basketball.realgm.com/nba/staff-members/1/Current/Referee
   - Complete roster with games officiated and experience

2. **Basketball-Reference Referees**: https://www.basketball-reference.com/referees/
   - Historical foul rates and career statistics

3. **Official NBA Referee Bios**: https://official.nba.com/referee-bios/
   - Background and experience level

### Secondary Sources (Fill Gaps)
4. **Covers.com Referee Stats**: https://www.covers.com/sport/basketball/nba/referees/statistics/2025-2026
   - O/U records, ATS trends (indicates strict vs lenient tendencies)

5. **Google Search**: "[Referee Name] NBA referee 2025-26 statistics fouls per game"

6. **Reddit r/nba**: Search `"[Referee Name]" site:reddit.com/r/nba`
   - Fan observations and game thread discussions

---

## Output Format

Please provide your findings in this exact format for each referee:

```
### [Referee Name]
- **Background**: [Rookie/Veteran/G-League/International/Years of Experience]
- **Games This Season**: [X games in 2025-26]
- **Avg Fouls/Game**: [X.X fouls per game] OR [Estimated: X.X based on Y]
- **Style**: [STRICT / NEUTRAL / LENIENT]
- **O/U Record**: [X-Y] OR [Not Available]
- **Data Source**: [Where you found this information]
- **Confidence Level**: [HIGH / MEDIUM / LOW]
- **Notes**: [Any additional relevant information]
```

---

## Estimation Guidelines (If Exact Data Not Available)

If you cannot find exact foul statistics for a referee, use these guidelines to estimate:

### Rookie/New Refs (1-2 years experience)
- **Default**: 21.5 fouls/game (league average)
- **Style**: NEUTRAL
- **Reasoning**: New refs typically call "by the book" until they develop a style
- **Confidence**: LOW

### International Refs (FIBA background)
- **Default**: 20.0 fouls/game
- **Style**: LENIENT
- **Reasoning**: FIBA-trained officials tend to allow more physical play than NBA
- **Confidence**: MEDIUM

### G-League Callups
- **Default**: 22.0 fouls/game
- **Style**: NEUTRAL
- **Reasoning**: G-League experience but less NBA adjustment
- **Confidence**: MEDIUM

### Veterans (3+ years NBA experience)
- **Action**: Search extensively - these refs should have public data
- **Confidence**: Should be HIGH if found

### Using O/U Records as Proxy
If you find a referee's Over/Under betting record but no foul data:
- **>55% Overs** → Estimate 23.0 fouls/game (STRICT)
- **45-55% Overs** → Estimate 21.5 fouls/game (NEUTRAL)
- **<45% Overs** → Estimate 19.5 fouls/game (LENIENT)

---

## Example Output

Here's an example of the desired output format:

```
### Scott Foster
- **Background**: Veteran (30+ years NBA experience)
- **Games This Season**: 28 games in 2025-26
- **Avg Fouls/Game**: 18.9 fouls per game
- **Style**: LENIENT
- **O/U Record**: 12-16 (42.9% Overs)
- **Data Source**: Basketball-Reference + Covers.com
- **Confidence Level**: HIGH
- **Notes**: Known for allowing physical play, especially in playoffs. One of the most experienced officials in the league.
```

---

## Priority Ranking

If you're short on time, prioritize in this order:

**HIGH PRIORITY** (Appear frequently in games):
1. Che Flores
2. Biniam Maru
3. Marat Kogut

**MEDIUM PRIORITY** (Veterans with likely data):
4. Pat O'Connell
5. Sean Corbin
6. Suyash Mehta

**LOW PRIORITY** (Can use defaults):
7-10. Rookie refs (JT Orr, Justin Van Duyne, Jonathan Sterling, Matt Kallio)
11. Gediminas Petraitis (international)
12. Jenna Schroeder (female official)

---

## Additional Context

**Why This Matters:**
We're building a referee impact model for NBA betting analysis. We need to know if a referee crew is strict (calls many fouls → more free throws → higher scoring) or lenient (lets them play → fewer stoppages → faster pace but fewer FTs).

**League Baseline:**
- League average fouls/game: **21.5 fouls** (2025-26 season)
- This is the total fouls called per game (both teams combined)

**Current Database:**
We already have 39 veteran referees in our system. These 12 are newly discovered because they're either:
- Rookie officials promoted mid-season
- G-League refs filling in due to injuries
- International refs on rotation
- Under-the-radar veterans we missed

---

## Deliverable

Please provide a single document with all 12 referees researched in the format above. At the end, include a summary table:

```
| Referee Name | Fouls/Game | Style | Confidence | Source |
|--------------|------------|-------|------------|--------|
| JT Orr | 21.5 (est) | NEUTRAL | LOW | Estimated (rookie) |
| ... | ... | ... | ... | ... |
```

---

## Questions to Ask If Needed

If you encounter any issues during research, please note:
- Which referees had NO data available at all?
- Which sources were most helpful?
- Are there any referees who appear to have retired or are no longer active?
- Did you find any contradictory information (e.g., one source says strict, another says lenient)?

---

Thank you for your thorough research! This data will help improve the accuracy of our NBA officiating impact model.
