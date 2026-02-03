# Agent Handoff: Phase 6.1 - Tank01 Depth Charts Integration

**Date:** February 2, 2026 @ 4:30 PM EST
**Task Type:** Data Integration + Script Creation + Module Enhancement
**Priority:** CRITICAL (First task of Phase 6)
**Estimated Complexity:** Medium (API sync + DB schema + module integration)

---

## YOUR ROLE

You are a **Senior Data Engineer** working on the Ludi-Bot NBA analytics platform. Your specialty is:
- API integration and data pipeline development
- Database schema design and optimization
- Python scripting with SQLite
- Test-driven development

You will be creating the depth charts sync system that identifies NBA starters vs backups.

---

## PROJECT CONTEXT

**Ludi-Bot** is an NBA betting analytics platform that generates player prop recommendations using Monte Carlo simulations and matchup analysis.

**Current Status:**
- Model is profitable: +292 units, 55.7% win rate (Jan 7-29, 2026)
- CLV (Closing Line Value) is positive across all edge buckets
- However, we discovered significant unused data sources

**Why Phase 6.1 Matters:**
Currently, the model treats ALL players equally regardless of whether they're starters or backups. This is a problem because:
- Starters get 30-38 minutes, backups get 12-22 minutes
- When a starter is OUT, we need to identify WHO moves up
- Depth charts tell us PG1 (starter) vs PG2 (backup) vs PG3 (deep bench)

---

## YOUR TASK

### Deliverable 1: Create `scripts/sync_depth_charts.py`

**API Endpoint:** Tank01 RapidAPI `/getNBADepthCharts`
- Host: `tank01-fantasy-stats.p.rapidapi.com`
- Returns: All 30 teams with position hierarchies

**Expected Response Structure:**
```json
{
  "body": [
    {
      "team": "ATL",
      "teamId": "1610612737",
      "depthChart": {
        "PG": [
          {"playerName": "Trae Young", "playerId": "1629027", "depthOrder": 1},
          {"playerName": "Bogdan Bogdanovic", "playerId": "203992", "depthOrder": 2}
        ],
        "SG": [...],
        "SF": [...],
        "PF": [...],
        "C": [...]
      }
    },
    ...
  ]
}
```

**Script Requirements:**
```python
# scripts/sync_depth_charts.py

"""
Tank01 Depth Charts Sync

Fetches NBA depth charts and updates local database.
Identifies starters (depth_order=1) vs backups (depth_order>=2).

Usage:
    python scripts/sync_depth_charts.py
    python scripts/sync_depth_charts.py --team ATL  # Single team
    python scripts/sync_depth_charts.py --dry-run   # Preview only
"""

import sqlite3
import requests
import config
from datetime import datetime

class DepthChartSync:
    def __init__(self, db_path='ludi.db'):
        self.db_path = db_path
        self.api_key = config.TANK01_KEY
        self.base_url = "https://tank01-fantasy-stats.p.rapidapi.com"

    def fetch_depth_charts(self) -> dict:
        """Fetch all 30 team depth charts from Tank01"""
        # Implementation here

    def sync_to_database(self, depth_data: dict) -> dict:
        """
        Sync depth chart data to database.
        Returns: {"teams_synced": int, "players_updated": int}
        """
        # Implementation here

    def update_player_starter_status(self) -> int:
        """
        Update is_starter column in players table.
        Returns: count of players updated
        """
        # Implementation here
```

---

### Deliverable 2: Database Schema Updates

**New Table: `depth_charts`**
```sql
CREATE TABLE IF NOT EXISTS depth_charts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    team_abbr TEXT NOT NULL,
    team_id TEXT,
    position TEXT NOT NULL,  -- PG, SG, SF, PF, C
    player_name TEXT NOT NULL,
    player_id TEXT,
    depth_order INTEGER NOT NULL,  -- 1=starter, 2=backup, 3=deep bench
    synced_at TEXT NOT NULL,
    UNIQUE(team_abbr, position, depth_order)
);

CREATE INDEX idx_depth_charts_team ON depth_charts(team_abbr);
CREATE INDEX idx_depth_charts_player ON depth_charts(player_name);
```

**Update `players` Table:**
```sql
-- Add is_starter column if not exists
ALTER TABLE players ADD COLUMN is_starter INTEGER DEFAULT 0;
-- 1 = starter (depth_order=1 for any position)
-- 0 = backup/bench
```

---

### Deliverable 3: Integration with Module E

**File:** `module_e.py` (LudiCalibrator)

**Current State:** Module E applies matchup modifiers but doesn't know starter status.

**Enhancement Needed:**
Add a method to check starter status and apply appropriate adjustments:

```python
def get_starter_status(self, player_name: str) -> dict:
    """
    Get player's depth chart status.

    Returns:
        {
            "is_starter": bool,
            "position": str,  # PG, SG, SF, PF, C
            "depth_order": int,  # 1, 2, or 3
            "team": str
        }
    """
    # Query depth_charts table

def apply_starter_adjustments(self, player_stats: dict, starter_info: dict) -> dict:
    """
    Apply minutes/usage adjustments based on starter status.

    Adjustments:
    - Starters: No change (baseline)
    - Backups (depth_order=2): -15% volume expectation
    - Deep bench (depth_order=3): -30% volume expectation
    """
```

---

## TECHNICAL DETAILS

### Config Setup

**File:** `config.py`
```python
# Tank01 API (already configured)
TANK01_KEY = os.getenv('TANK01_KEY')
TANK01_HOST = "tank01-fantasy-stats.p.rapidapi.com"
```

### Existing Database Location
- **Path:** `ludi.db` (project root)
- **Type:** SQLite with WAL mode enabled

### Team Abbreviation Mapping

Use this mapping for consistency (already exists in `utils/team_offensive_classifier.py`):
```python
TEAM_ABBR_MAP = {
    'GS': 'GSW', 'PHO': 'PHX', 'NO': 'NOP', 'SA': 'SAS', 'NY': 'NYK',
    # ... (30 teams total)
}
```

---

## TESTING REQUIREMENTS

### Unit Tests Required

Create `tests/test_depth_charts.py`:

```python
def test_fetch_depth_charts_returns_30_teams():
    """Verify API returns all 30 NBA teams"""

def test_depth_chart_has_5_positions():
    """Each team should have PG, SG, SF, PF, C"""

def test_starter_is_depth_order_1():
    """Verify depth_order=1 players are marked as starters"""

def test_database_upsert_idempotent():
    """Running sync twice shouldn't create duplicates"""

def test_player_starter_status_updated():
    """Verify players table is_starter column is updated"""
```

### Manual Validation

After running the sync, verify with these queries:
```sql
-- Check depth chart coverage
SELECT team_abbr, COUNT(*) as positions
FROM depth_charts
GROUP BY team_abbr;
-- Expected: 30 rows, each with ~15 players (3 per position)

-- Check starter identification
SELECT p.name, p.is_starter, d.position, d.depth_order
FROM players p
JOIN depth_charts d ON p.name = d.player_name
WHERE p.is_active = 1
ORDER BY d.team_abbr, d.position, d.depth_order;

-- Verify no duplicates
SELECT team_abbr, position, depth_order, COUNT(*) as cnt
FROM depth_charts
GROUP BY team_abbr, position, depth_order
HAVING cnt > 1;
-- Expected: 0 rows (no duplicates)
```

---

## SUCCESS CRITERIA

Before marking this task complete, verify:

- [ ] `scripts/sync_depth_charts.py` runs without errors
- [ ] `depth_charts` table created with proper schema
- [ ] All 30 teams synced (verify with SQL query)
- [ ] Each team has 5 positions with at least 2 players each
- [ ] `players.is_starter` column added and populated
- [ ] Module E integration method added (can be placeholder for now)
- [ ] All unit tests pass
- [ ] Dry-run mode works (preview without database writes)
- [ ] Script logs output (teams synced, players updated)

---

## FILES TO CREATE/MODIFY

| File | Action | Purpose |
|------|--------|---------|
| `scripts/sync_depth_charts.py` | CREATE | Main sync script |
| `tests/test_depth_charts.py` | CREATE | Unit tests |
| `module_e.py` | MODIFY | Add starter status methods |
| `database.py` | MODIFY | Add depth_charts table creation |

---

## DO NOT

- Do NOT modify `module_f.py` (that's for Phase 6.2)
- Do NOT change existing bet logging logic
- Do NOT remove any existing functionality
- Do NOT hardcode API keys (use config.py)

---

## USEFUL COMMANDS

```bash
# Activate environment
source .venv/bin/activate

# Run the sync script
python scripts/sync_depth_charts.py

# Run with dry-run
python scripts/sync_depth_charts.py --dry-run

# Run tests
python -m pytest tests/test_depth_charts.py -v

# Check database
sqlite3 ludi.db "SELECT COUNT(*) FROM depth_charts;"
sqlite3 ludi.db "SELECT * FROM depth_charts WHERE team_abbr='LAL';"
```

---

## REFERENCE FILES

Read these files for context:
- `ROADMAP.md` - Full project roadmap (Phase 6 section)
- `config.py` - API key configuration
- `database.py` - Database initialization patterns
- `utils/team_offensive_classifier.py` - Team abbreviation mapping example
- `module_e.py` - Where starter status will be integrated

---

## HANDOFF CHECKLIST

When complete, provide:
1. Summary of changes made
2. Test results (all passing)
3. SQL verification queries with output
4. Any issues encountered and how they were resolved
5. Recommendations for Phase 6.2 (BENEFICIARY tagging)

---

**Analysis completed by:** Claude Opus 4.5
**Handoff to:** New agent session
**Status:** READY TO BEGIN
