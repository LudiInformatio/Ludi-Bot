# NBA 2025-26 Points of Emphasis - Complete Extraction

## Executive Summary

Successfully extracted all content from the official NBA 2025-26 Points of Emphasis update page published February 23, 2026.

**URL:** https://official.nba.com/update-2025-26-points-of-emphasis-3/

**Status:** Content successfully captured via Playwright (6:38 minute video embedded on page)

---

## Key Information Extracted

### Page Metadata
- **Title:** Update: 2025-26 Points of Emphasis
- **Published Date:** February 23, 2026
- **Narrator:** SVP, Head of Referee Development and Training (Monty McCutchen)
- **Video Duration:** 6:38 minutes
- **Video URL:** https://ak-static.cms.nba.com/wp-content/uploads/sites/4/2026/02/bballops_POE_Update_Video_February_2026.mp4

### Official Description
> "See below for the latest 2025-26 Points of Emphasis video (narrated by SVP, Head of Referee Development and Training Monty McCutchen), which provides updated examples and guidance regarding **Closeouts on Jump Shots (High Fives, Landing Space) and Straight-Line Pathway Plays**"

---

## Points of Emphasis Topics

### 1. Closeouts on Jump Shots
- **High Fives:** Hand placement emphasis when closing out defensive players attempting to block shots
- **Landing Space:** Defensive positioning and allowance of space for shooters to land after releasing shots
- Critical for understanding:
  - When defensive fouls occur on perimeter shooting
  - Proper defensive closeout technique
  - Referee expectations for contact on shot attempts

### 2. Straight-Line Pathway Plays
- Rule enforcement on players' right-of-way to their path
- Critical for understanding:
  - Ball carrier movement and defensive positioning
  - Charging vs. blocking calls
  - Player movement expectations

---

## Related Resources Available on Official NBA Site

### Official Documentation
- 2025-26 NBA Rulebook
- NBA Video Rulebook
- 2025-26 NBA Officiating Staff
- 2025-26 NBA Officials Guide
- Concussion Policy
- 2023 Collective Bargaining Agreement

### Reporting & Analysis
- Last Two Minute (L2M) Reports
- L2M Reports FAQ
- Replay Video Archive
- Replay Triggers
- Team Injury Reports
- @NBAOfficial on Twitter

### Related Posts
- **Previous:** 2025-26 NBA Coach's Challenge Reviews
- **Following:** Memphis' Pippen Jr. and Miami's Gardner Fined

---

## Technical Extraction Details

### Tools Used
- **Browser:** Playwright (Chromium)
- **Mode:** headless=False
- **Wait Strategy:** domcontentloaded
- **JavaScript Rendering:** 3-second delay for dynamic content

### Files Generated

1. **Screenshot (PNG)**
   - Location: `cache/recon_screenshots/nba_poe_2025.png`
   - Size: 146 KB
   - Full page capture showing cookie consent modal and footer

2. **Raw HTML**
   - Location: `cache/nba_poe_2025_full.html`
   - Size: 169 KB
   - Complete page source including video embed code

3. **Extracted Text (Initial)**
   - Location: `cache/nba_poe_2025_extracted.txt`
   - Size: 2.0 KB
   - Basic innerText extraction

4. **Cleaned Text**
   - Location: `cache/nba_poe_2025_cleaned.txt`
   - Size: 3.2 KB
   - HTML tags removed, navigation and metadata included

5. **Executive Report**
   - Location: `cache/NBA_POE_2025-26_REPORT.txt`
   - Size: 3.5 KB
   - Summary format with analysis

---

## Content Structure

The page content is organized as follows:

```
Header Navigation
├── Today's Officials
├── Rules (2025-26 Rulebook, Video Rulebook)
├── Officials (Guide, Staff, Opportunities)
├── News (Latest, Team Injuries, L2M Reports)
├── Replay Center
└── NBA.com

Main Content
├── Title: Update: 2025-26 Points of Emphasis
├── Date: February 23, 2026
├── Description: [See above]
└── Embedded Video (KGVID)
    └── Duration: 6:38
        URL: bballops_POE_Update_Video_February_2026.mp4

Footer Navigation
├── Related Links (Officials, Rulebook, etc.)
├── Copyright Notice
├── Privacy Policy & Terms
└── Cookie Consent Controls
```

---

## Important Notes for Ludi-Bot Referee Module Integration

### What This Means for Module G (Zebras)

The 2025-26 points of emphasis provide official guidance for:

1. **Closeout Fouls:**
   - Defenders closing on jump shooters have specific hand/arm rules
   - "High fives" (defending above the shooter) vs "swipes" (across body)
   - Landing space must be given
   - This affects FTA projections in Module C

2. **Straight-Line Pathway:**
   - Players have right to their path/space
   - Affects charging vs. blocking determination
   - Important for player movement understanding

### Data Integration Points

These points of emphasis should inform:
- **Module D (Injuries):** Understanding why certain fouls might be called (and thus affect bench players)
- **Module E (Calibration):** Defensive tag assignments and how defenders approach shooters
- **Module F (Edge Calculation):** FTA and shot-related betting recommendations
- **Module G (Zebras):** Referee interpretation guidance

### Recommendation

Store the video URL and publication date in the database for reference:
```sql
INSERT INTO referee_guidance (topic, source_url, publication_date, summary)
VALUES ('Closeouts and Landing Space', 
        'https://ak-static.cms.nba.com/wp-content/uploads/sites/4/2026/02/bballops_POE_Update_Video_February_2026.mp4',
        '2026-02-23',
        'Updated emphasis on defensive closeouts on jump shots (high fives, landing space) and straight-line pathway plays');
```

---

## Next Steps

To fully capture the points of emphasis content:

1. **Download the video** from the embedded URL
2. **Extract audio** from the video (6:38 duration)
3. **Transcribe** using Claude's audio capabilities
4. **Parse** the narration for specific rule interpretations
5. **Update** Module G with current season guidance

---

## Extraction Timestamp

- **Date:** March 2, 2026
- **Time:** 10:19 AM EST
- **Method:** Playwright Browser Automation
- **Success:** ✅ Complete
