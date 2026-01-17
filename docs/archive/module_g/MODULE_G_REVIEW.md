# Module G (Zebras) - System Review & Upgrade Plan

## 1. Executive Summary
**Current Status:** 🟡 **Partially Operational / Low Impact**
**Verdict:** The module is technically connected to the simulation engine, but its impact is negligible due to missing data (missing ~80% of refs) and simplistic logic (only affects Pace, ignores Foul bias).

## 2. Current Architecture Audit

### A. Integration Check (The Wiring)
*   **Status:** ✅ **Connected**
*   **Flow:** `Module G` -> `Module A (Gatekeeper)` -> `Main` -> `Module C (Oracle)`
*   **Mechanism:** `Module C` receives a `ref_impact` float (e.g., 1.04).
*   **Current Application:** This factor **ONLY multiplies the Pace (Possessions)**.
    *   *Code:* `macro_mods['pace'] = ... * ref_factor`
    *   *Gap:* It does **NOT** currently adjust Free Throw Rates (FTA), Foul Trouble probability, or Technical Ejections. A "high foul" ref makes the game faster in the current code, but doesn't necessarily create more free throws for specific players.

### B. Data Integrity (The Roster)
*   **Status:** ❌ **Critical Data Vacuum**
*   **Registered Refs in DB:** **13**
*   **Actual NBA Staff:** **~74**
*   **Impact:** For ~80% of games, the system returns `1.0` (Neutral) because it doesn't recognize the crew.
*   **Missing Names:** Virtually the entire league (e.g., Zach Zarba is present, but newer/less famous refs are absent).

### C. Logic gaps Analysis ("Ludi Lens" Requirements)
| Feature | Current State | Required State (Target) |
| :--- | :--- | :--- |
| **Baseline Profile** | Hardcoded Dict (13 items) | Weekly Scrape (Basketball-Ref) of all 74+ refs |
| **Recency Bias** | None | Daily Scrape (NBAStuffer) for "Last 5 Games" trends |
| **Impact Type** | Pace Only | Split: **Pace** (Possessions) vs **Whistle** (FTA Rate) |
| **Context** | None | Cross-ref with **Covers.com** (O/U Trends) |
| **L2M Variance** | None | "Clutch Chaos" factor for low-accuracy refs |
| **Ejections** | None | **Rotowire** integration for "Tilt" factor |

## 3. Implementation Plan (The "S.A.V.A.G.E." Upgrade)

To bring Module G up to the "Ludi Lens Bot" specifications, we need a 3-phase overhaul.

### Phase 1: The Data Pipeline (Expansion)
1.  **Retire Hardcoded Map:** Delete the static `IMPACT_MAP`.
2.  **Weekly Scraper (`module_g_loader.py`):**
    *   Target: `basketball-reference.com/referees/2026_register.html`
    *   Metric: Extract per-referee `Fouls/Game` and `Pace` relative to league average.
    *   Storage: Save to `db/ref_profiles.json`.
3.  **Daily Scraper (NBAStuffer):**
    *   Target: `nbastuffer.com` (Last 5 Games).
    *   Metric: Identify "Hot" whistle refs.

### Phase 2: The Logic Engine (Refinement)
1.  **Split Impact Factors:**
    *   Create `pace_impact` (Speed of game).
    *   Create `whistle_impact` (Frequency of fouls).
2.  **Update Oracle (`module_c.py`):**
    *   Apply `pace_impact` -> `macro_mods['pace']` (Existing).
    *   Apply `whistle_impact` -> `macro_mods['whistle']` -> Multiplies player `FTA` projections (New).

### Phase 3: The Validators (Intelligence)
1.  **Covers.com Integration:** Checks if the "Physics" (Stuffer) matches the "Economics" (Betting Trends).
2.  **L2M Integration:** If a ref has low accuracy in the Last 2 Minutes, slightly increase the variance (StdDev) of the simulation results to model chaos.

## 4. Immediate Action Item
**Recommendation:** We should immediately implement **Phase 1 (Data Pipeline)**. The system cannot function correctly with only 13 referees.

*Would you like me to begin drafting the `implementation_plan.md` for this Data Pipeline upgrade?*
