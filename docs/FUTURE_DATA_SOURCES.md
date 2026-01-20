# Future Data Sources Roadmap 🔮

**Discovered:** January 20, 2026  
**Context:** Found during Module D (Yak) research in NBA Sense documentation (stats-prod.nba.com)

The following endpoints were discovered in the unofficial NBA Sense documentation and represent high-value opportunities for enhancing other Ludi-Bot modules.

---

## 1. Module E (Calibrator) Opportunities

### Synergy PlayType Data
Granular efficiency data for specific play types. Crucial for matchup modeling.

*   **Endpoints:**
    *   `PlayerPlayTypePickAndRollBallHandler`
    *   `PlayerPlayTypeIsolation`
    *   `PlayerPlayTypePostup`
    *   `PlayerPlayTypeSpotup`
*   **Use Case:**
    *   Adjust player projections based on defensive matchup efficiency (e.g., "Curry P&R vs Gobert drop coverage").
    *   Identify mismatch exploitations.

### SportVu Tracking
Player tracking data for deeper behavioral analysis.

*   **Endpoints:**
    *   `PlayerDrives`: Drives per game, FG% on drives, Pass% on drives.
    *   `PlayerTouches`: Time of possession, avg seconds per touch.
    *   `PlayerSpeed`: Avg speed, distance traveled (good for fatigue monitoring).
    *   `PlayerRebounding`: Contested vs Uncontested rebound %.
*   **Use Case:**
    *   Refine "Usage" metrics beyond simple USG%.
    *   Detect fatigue (slower speed + lower shot quality) for finding "Under" props.

---

## 2. Module X (Scenario Builder) Opportunities

### Expected Lineups
RotoWire's projected starting units.

*   **Source:** RotoWire API / stats-prod endpoint
*   **Use Case:**
    *   Automating the start of the scenario building process.
    *   Triggering "Bench Unit" scenarios when a starter is ruled out.

---

## 3. Module G (Ref Engine) Opportunities

### SportVu Defense
Defensive impact metrics.

*   **Endpoints:**
    *   `PlayerDefense`: FG% allowed at rim, < 6ft, > 15ft.
*   **Use Case:**
    *   Correlate referee tendencies with defensive aggression.
    *   Identify "Foul Prone" defenders in matchups with "Whistle Happy" refs.

---

## Implementation Notes

*   **Auth:** Most of these appear to be accessible via the same `stats-prod.nba.com` endpoints used freely.
*   **Format:** JSON responses.
*   **Risk:** Undocumented APIs can change without warning. Always implement with fallbacks.
