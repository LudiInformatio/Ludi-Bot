# Module G (Zebras) - Referee Intelligence Upgrade
**Date:** January 15, 2026  
**Status:** 🟡 Planning → Implementation  
**Priority:** HIGH (System currently operating at ~20% referee coverage)

---

## Executive Summary

**Current State:**
- **Refs in Database:** 13 (hardcoded in `module_g.py`)
- **Active NBA Refs:** ~74 officials
- **Coverage:** 17.6% (13/74)
- **Impact Type:** Pace only (missing FTA/Foul bias)
- **Current Outcome:** 80%+ of games default to neutral (1.0x) referee impact

**Target State:**
- **Refs in Database:** 74+ (full roster)
- **Coverage:** 100%
- **Impact Types:** Pace + Whistle (FTA) + Ejection Risk
- **Data Sources:** Basketball-Reference (weekly) + NBAStuffer (daily) + Covers.com (validation)

---

## Phase 1: Data Pipeline Expansion (Week 4)

### 1.1 Database Schema Updates

**New Table: `referee_profiles`**
```sql
CREATE TABLE IF NOT EXISTS referee_profiles (
    referee_id INTEGER PRIMARY KEY AUTOINCREMENT,
    referee_name TEXT UNIQUE NOT NULL,
    seasons_active INTEGER DEFAULT 1,
    
    -- Weekly baseline stats (from Basketball-Reference)
    avg_fouls_per_game REAL DEFAULT 0.0,
    avg_pace_impact REAL DEFAULT 1.0,      -- Relative to league avg
    avg_technical_rate REAL DEFAULT 0.0,   -- Techs per game
    
    -- Classification
    style TEXT DEFAULT 'NEUTRAL',          -- LENIENT, NEUTRAL, STRICT
    
    -- Metadata
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    data_source TEXT DEFAULT 'basketball-reference'
);

CREATE INDEX idx_referee_name ON referee_profiles(referee_name);
```

**New Table: `referee_daily_stats`**
```sql
CREATE TABLE IF NOT EXISTS referee_daily_stats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    referee_id INTEGER,
    
    -- Last 5 games (from NBAStuffer)
    last5_fouls_avg REAL DEFAULT 0.0,
    last5_pace_impact REAL DEFAULT 1.0,
    last5_over_under_record TEXT,          -- "3-2 O" format
    
    -- Recency flags
    is_hot_whistle BOOLEAN DEFAULT 0,      -- Last 5 > season avg by 15%+
    is_fast_paced BOOLEAN DEFAULT 0,       -- Last 5 > league pace
    
    -- Metadata
    sync_date DATE DEFAULT CURRENT_DATE,
    data_source TEXT DEFAULT 'nbastuffer',
    
    FOREIGN KEY (referee_id) REFERENCES referee_profiles(referee_id)
);

CREATE INDEX idx_referee_daily_date ON referee_daily_stats(sync_date);
```

**Modified Table: `games` (add referee tracking)**
```sql
-- Already exists, just add column if missing
ALTER TABLE games ADD COLUMN referee_pace_impact REAL DEFAULT 1.0;
ALTER TABLE games ADD COLUMN referee_whistle_impact REAL DEFAULT 1.0;
```

---

### 1.2 Scraper Scripts

#### A. `scripts/scrape_referee_roster.py` (Weekly)
**Purpose:** Sync full referee roster and baseline stats from Basketball-Reference  
**Schedule:** Monday 5:00 AM EST (via GitHub Actions)  
**Target URL:** `https://www.basketball-reference.com/referees/2026_register.html`

**Key Functions:**
```python
def scrape_referee_roster():
    """
    Scrapes Basketball-Reference for full 2025-26 referee roster.
    Returns: List of dicts with referee stats.
    """
    # 1. Hit BBR with pandas.read_html
    # 2. Parse table for: Name, Games, Fouls/Game, Avg Pace
    # 3. Calculate pace_impact (pace / league_avg_pace)
    # 4. Classify style: LENIENT (<20 fouls/g), NEUTRAL (20-23), STRICT (>23)
    # 5. Return structured data
    
def sync_to_database(referee_data):
    """
    Upserts referee_profiles table.
    Uses ON CONFLICT (referee_name) DO UPDATE.
    """
```

**Output Example:**
```json
[
  {
    "referee_name": "Zach Zarba",
    "avg_fouls_per_game": 21.3,
    "avg_pace_impact": 1.02,
    "avg_technical_rate": 0.15,
    "style": "NEUTRAL"
  },
  ...
]
```

---

#### B. `scripts/scrape_referee_recency.py` (Daily)
**Purpose:** Update "hot whistle" and recent trends from NBAStuffer  
**Schedule:** Daily 5:00 AM EST (before referee assignments)  
**Target URL:** `https://www.nbastuffer.com/2025-2026-nba-referee-stats/`

**Key Functions:**
```python
def scrape_referee_recency():
    """
    Scrapes NBAStuffer for Last 5 Games stats.
    Returns: List of dicts with recent trends.
    """
    # 1. Hit NBAStuffer with pandas.read_html or BeautifulSoup
    # 2. Parse "Last 5 Games" columns
    # 3. Flag hot_whistle if Last5 > Season by 15%+
    # 4. Return structured data
    
def sync_daily_stats(recency_data):
    """
    Inserts new row into referee_daily_stats.
    One row per referee per day.
    """
```

---

### 1.3 Module G Refactor (`module_g.py`)

**Changes:**
1. **Delete:** Hardcoded `IMPACT_MAP` (lines 21-36)
2. **Add:** Database query to `referee_profiles` and `referee_daily_stats`
3. **Add:** Logic to return **TWO** factors: `pace_impact` and `whistle_impact`

**New Method:**
```python
def get_game_impact(self, home_team_abbr: str) -> dict:
    """
    Returns: {
        'pace_impact': 1.02,      # Multiplier for possessions
        'whistle_impact': 1.05,   # Multiplier for FTA
        'crew': ['Zach Zarba', 'Scott Foster', 'Ed Malloy'],
        'confidence': 0.85        # Based on data coverage
    }
    """
    crew = self.daily_assignments.get(home_team_abbr, [])
    if not crew:
        return {'pace_impact': 1.0, 'whistle_impact': 1.0, 'crew': [], 'confidence': 0.0}
    
    # Query database for each ref in crew
    pace_factors = []
    whistle_factors = []
    
    for ref_name in crew:
        profile = self._get_referee_profile(ref_name)  # DB query
        if profile:
            # Blend baseline + recency
            pace_factors.append(profile['pace_impact'])
            whistle_factors.append(profile['whistle_impact'])
        else:
            # Unknown ref, use neutral
            pace_factors.append(1.0)
            whistle_factors.append(1.0)
    
    # Average crew impact
    avg_pace = sum(pace_factors) / len(pace_factors)
    avg_whistle = sum(whistle_factors) / len(whistle_factors)
    
    return {
        'pace_impact': round(avg_pace, 3),
        'whistle_impact': round(avg_whistle, 3),
        'crew': crew,
        'confidence': len([f for f in pace_factors if f != 1.0]) / len(crew)
    }
```

---

### 1.4 Module C Integration (`module_c.py`)

**Current State (Line 57):**
```python
macro_mods = {
    "pace": scenario.get('pace_factor', 1.0) * ref_factor * fatigue_tax,
    ...
```

**New State:**
```python
ref_data = scenario.get('ref_data', {})  # Now a dict, not a float
ref_pace = ref_data.get('pace_impact', 1.0)
ref_whistle = ref_data.get('whistle_impact', 1.0)

macro_mods = {
    "pace": scenario.get('pace_factor', 1.0) * ref_pace * fatigue_tax,
    "whistle": ref_whistle,  # NEW: Applied to FTA in _simulate_volume
    ...
}
```

**Update `_simulate_volume` (Line 106):**
```python
if stat == 'FTA':
    stat_mod *= mods['whistle']  # Apply referee whistle impact
```

---

### 1.5 Main Pipeline Update (`main.py`)

**Current (Line 125):**
```python
def build_simulation_scenario(self, game_data, home_roster, away_roster):
    return {
        'scenario_name': ...,
        'ref_impact': game_data.get('archetypes', {}).get('ref_impact', 1.0),  # OLD: single float
        ...
    }
```

**New:**
```python
def build_simulation_scenario(self, game_data, home_roster, away_roster):
    ref_data = game_data.get('archetypes', {}).get('ref_data', {})  # NEW: dict
    return {
        'scenario_name': ...,
        'ref_data': ref_data,  # Pass full dict to Oracle
        ...
    }
```

---

## Phase 2: Logic Engine Refinement (Week 5)

### 2.1 Ejection Risk Modeling
- **Source:** Rotowire (Technical Fouls per game by ref)
- **Implementation:** Add `ejection_risk` multiplier to `macro_mods`
- **Effect:** Slightly increase turnover variance for high-usage players vs "Strict" refs

### 2.2 L2M Variance
- **Source:** NBA.com Last Two Minute Reports
- **Implementation:** If ref has low L2M accuracy (<90%), widen StdDev for clutch simulations
- **Effect:** Models "chaos" in close games

---

## Phase 3: Validators (Week 6)

### 3.1 Covers.com Cross-Reference
- **Logic:** Compare NBAStuffer "Physics" (fouls) vs Covers "Economics" (O/U record)
- **Flag:** If Physics says "High Fouls" but Economics says "Under Trend", alert as "Trap Game"

### 3.2 Dashboard Integration
- **Display:** Show referee crew, pace/whistle impact, and confidence score in daily briefing
- **Format:** `🦓 Crew: Zarba/Foster/Malloy | Pace: 1.02x | Whistle: 1.05x | Confidence: 85%`

---

## Testing Strategy

### Unit Tests
```bash
# Test scraper parsing
python -m pytest tests/test_referee_scraper.py

# Test Module G database queries
python -m pytest tests/test_module_g.py

# Test Oracle whistle integration
python -m pytest tests/test_module_c_whistle.py
```

### Integration Test
```bash
# End-to-end: Scrape → DB → Module G → Oracle → Report
python test_referee_pipeline.py
```

**Success Criteria:**
- ✅ All 74+ refs loaded into database
- ✅ `get_game_impact()` returns non-1.0 values for 95%+ of games
- ✅ FTA projections change by ±5-10% when whistle_impact ≠ 1.0
- ✅ Briefing displays referee crew and confidence score

---

## Implementation Checklist

### Week 4 (Current)
- [ ] Create `scripts/scrape_referee_roster.py`
- [ ] Create `scripts/scrape_referee_recency.py`
- [ ] Update `database.py` with new schema
- [ ] Refactor `module_g.py` (delete hardcoded map, add DB queries)
- [ ] Update `module_c.py` (add whistle_impact to FTA)
- [ ] Update `main.py` (pass ref_data dict instead of float)
- [ ] Create GitHub Action workflow for weekly scrapes
- [ ] Test end-to-end with tonight's slate

### Week 5
- [ ] Add Rotowire ejection risk scraper
- [ ] Add L2M variance logic to Oracle
- [ ] Backtest referee impact on Jan 1-15 slate

### Week 6
- [ ] Add Covers.com validation scraper
- [ ] Update daily briefing format with referee display
- [ ] Production deployment

---

## Next Steps

**Immediate Action (Today):**
1. Run `python database.py` to add new tables
2. Create `scripts/scrape_referee_roster.py` skeleton
3. Test scraper against Basketball-Reference live page

**Tomorrow (Jan 16):**
1. Complete scraper implementation
2. Populate database with full roster
3. Refactor `module_g.py` to use database
4. Run integration test on tomorrow's slate

---

**Would you like me to start with Step 1 (Database Schema) or Step 2 (Scraper Script)?**
