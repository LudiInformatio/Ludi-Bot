# 🛠️ LUDI TOOLKIT: ANALYTICS & AUDIT

This guide documents the specialized tools available for maintaining the mathematical integrity and scouting accuracy of the Ludi system.

## 1. The Archetype Census (`audit_roster.py`)
**Purpose:** Visualize how the system classifies players based on 2025-26 stats.
**Use Case:** Spot-checking if a player (e.g., Russ) is mislabeled or if thresholds need tuning.

```bash
# Run the full census (Top 300 Players)
python3 audit_roster.py
```

**Key Features:**
- **Trend Watch:** Flags players whose role has shifted in the last 15 days (e.g., `➚ HELIOCENTRIC`).
- **Secondary Archetypes:** Identifies multi-talented players (e.g., `HELIOCENTRIC / HUB_BIG`).
- **Validation Warnings:** Flags anomalies (e.g., a "Sniper" with low 3PM).

## 2. The Backtest Suite (`backtest_archetypes.py`)
**Purpose:** Verify the mathematical soundness of our matchup logic (Module E) against historical data.
**Use Case:** Running a "Sanity Check" after changing logic or before a major slate.

```bash
# Run the standard 60-day validation
python3 backtest_archetypes.py --mode 60

# Run the 15-day "Recent Trend" validation
python3 backtest_archetypes.py --mode 15

# Run the FULL SEASON validation (Since Oct 21, 2025)
python3 backtest_archetypes.py --mode season

# Run ALL modes sequentially
python3 backtest_archetypes.py --mode all
```

**Key Metrics:**
- **RMSE (Root Mean Square Error):** Measures prediction accuracy. Target: PTS < 7.0.
- **Hypothesis Tests:** Validates specific interactions (e.g., do Slashers actually get more FTA vs Hackers?).

## 3. The Math Auditor (`test_math_integrity.py`)
*Note: This is a temporary test script, typically deleted after use.*
**Purpose:** Verifies that Module F calculates EV correctly (e.g., -150 odds = lower EV than -110).
