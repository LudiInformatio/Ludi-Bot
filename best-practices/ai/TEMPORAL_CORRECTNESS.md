# Temporal Correctness Framework

**Created:** March 8, 2026
**Purpose:** Unified rules for data freshness, as-of dates, and preventing training-data contamination
**Applies to:** All AI employees, all pipeline scripts, all prompt templates

---

## Core Rule

> **NEVER use AI training data for current-season NBA facts.**
> The AI's training data is outdated and WILL produce incorrect results.
> Always cite a specific data source (table + column + date range).

---

## Data Freshness Requirements

| Table | Max Staleness | Check Method | Alert If |
|-------|--------------|--------------|----------|
| `player_game_logs` | 26 hours | `MAX(game_date)` | Yesterday's games missing by 10 AM |
| `player_injuries` | 2 hours (game day), 24 hours (off day) | `MAX(snapshot_time)` | Stale during active slate |
| `bet_recommendations` | 24 hours | `MAX(created_at)` | No pipeline run today |
| `team_lineups` | 24 hours | `MAX(updated_at)` | Missing after lineup sync (9:45 AM) |
| `referee_profiles` | 7 days | `MAX(last_updated)` | Weekly sync missed |
| `prop_line_snapshots` | 26 hours | `MAX(snapshot_date)` | CLV capture missed |
| `player_canonical_ids` | 14 days | Count dirty IDs (8+ digits) | > 10 dirty entries |

---

## As-Of Date Rules

### Rule 1: Player Team Assignment
- **Source:** `players.team` column (synced daily via roster sync)
- **Verification:** `SELECT name, team FROM players WHERE name = '[player]'`
- **NEVER:** Assume a player's team from AI memory. Players trade mid-season.

### Rule 2: Injury Status
- **Source:** `player_injuries` table with `snapshot_time`
- **Freshness:** Must be within 2 hours on game day
- **NEVER:** State a player is "OUT" or "PROBABLE" without citing the snapshot timestamp
- **Override:** If player appears in confirmed `team_lineups` starters, they are NOT out

### Rule 3: Seasonal Statistics
- **Source:** `player_game_logs` with explicit date range
- **Format:** "L10 average: 22.5 PTS (Feb 25 – Mar 7, 2026)"
- **NEVER:** Quote a season average without specifying the date range it covers
- **NEVER:** Use approximate numbers with tilde (~22 PPG) — always query exact

### Rule 4: Win Rates and Performance
- **Source:** `bet_recommendations` with `WHERE actual_result >= 0` (excludes -998/-999 sentinels)
- **Floor:** CLV data starts 2026-02-27. No CLV analysis before that date.
- **Format:** "52.3% WR (N=267, Jan 12 – Mar 7)"

### Rule 5: When Data Is Unavailable
- **Say:** "Data not available" or "Not enough data to answer"
- **NEVER:** Estimate, approximate, or fill in from training knowledge
- **NEVER:** Use tilde (~) estimates for any stat, PPG, or percentage

---

## Employee Application

Every employee's ONBOARDING.md should reference this framework:

```markdown
## Data Grounding
All claims must cite a specific data source. See `best-practices/ai/TEMPORAL_CORRECTNESS.md`.
- Never use AI training data for roster, injury, or statistical claims
- Always include date range for any seasonal statistic
- Say "data not available" rather than estimating
```

---

## Prompt Template Application

All Claude prompt templates (`utils/claude_prompts.py`) must include:

```
DATA GROUNDING RULE:
- Every claim must reference injected data, not training knowledge
- No tilde (~) estimates — use exact numbers from the data provided
- If a fact is not in the provided data, say "not available" — do NOT guess
- *(Unverified)* = omit entirely (do not include with disclaimer)
```

This is already implemented in `ANALYSIS_PROTOCOL` (commit `f72da62`, Mar 6).

---

*Created March 8, 2026 — unified temporal correctness for all AI employees and pipeline scripts*
