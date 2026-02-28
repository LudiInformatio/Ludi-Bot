"""
Centralized Mappings for Ludi Informatio

Provides standardized dictionaries and resolver functions to ensure
data consistency across different modules and data sources.

- TEAM_MAP: Standardizes team names and abbreviations.
"""

TEAM_MAP = {
    "Atlanta": "ATL", "Boston": "BOS", "Brooklyn": "BKN", "Charlotte": "CHA",
    "Chicago": "CHI", "Cleveland": "CLE", "Dallas": "DAL", "Denver": "DEN",
    "Detroit": "DET", "Golden State": "GSW", "Houston": "HOU", "Indiana": "IND",
    "L.A. Clippers": "LAC", "LA Clippers": "LAC", "Clippers": "LAC",
    "L.A. Lakers": "LAL", "LA Lakers": "LAL", "Lakers": "LAL", "Los Angeles Lakers": "LAL",
    "Memphis": "MEM", "Miami": "MIA", "Milwaukee": "MIL", "Minnesota": "MIN",
    "New Orleans": "NOP", "New York": "NYK", "Knicks": "NYK",
    "Oklahoma City": "OKC", "Orlando": "ORL", "Philadelphia": "PHI", "Phoenix": "PHX",
    "Portland": "POR", "Sacramento": "SAC", "San Antonio": "SAS", "Toronto": "TOR",
    "Utah": "UTA", "Washington": "WAS",
    "Atlanta Hawks": "ATL",
    "Boston Celtics": "BOS",
    "Brooklyn Nets": "BKN",
    "Charlotte Hornets": "CHA",
    "Chicago Bulls": "CHI",
    "Cleveland Cavaliers": "CLE",
    "Dallas Mavericks": "DAL",
    "Denver Nuggets": "DEN",
    "Detroit Pistons": "DET",
    "Golden State Warriors": "GSW",
    "Houston Rockets": "HOU",
    "Indiana Pacers": "IND",
    "Los Angeles Clippers": "LAC",
    "Los Angeles Lakers": "LAL",
    "Memphis Grizzlies": "MEM",
    "Miami Heat": "MIA",
    "Milwaukee Bucks": "MIL",
    "Minnesota Timberwolves": "MIN",
    "New Orleans Pelicans": "NOP",
    "New York Knicks": "NYK",
    "Oklahoma City Thunder": "OKC",
    "Orlando Magic": "ORL",
    "Philadelphia 76ers": "PHI",
    "Phoenix Suns": "PHX",
    "Portland Trail Blazers": "POR",
    "Sacramento Kings": "SAC",
    "San Antonio Spurs": "SAS",
    "Toronto Raptors": "TOR",
    "Utah Jazz": "UTA",
    "Washington Wizards": "WAS"
}

def resolve_team_abbr(raw_name: str, conn=None) -> str:
    """
    Standardize team names to 3-letter abbreviations.

    When ``conn`` (a sqlite3 connection) is provided, tries canonical_teams
    DB lookup first — this is the single source of truth for team mappings.
    Falls back to the hardcoded TEAM_MAP dict if conn is None or query misses.
    """
    if not raw_name:
        return None

    clean_name = raw_name.replace('.', '').strip()

    # DB-first: canonical_teams is the authoritative source (30 rows)
    if conn is not None:
        try:
            row = conn.execute(
                "SELECT standard_abbr FROM canonical_teams "
                "WHERE standard_abbr = ? OR bdl_abbr = ? OR tank01_abbr = ? OR full_name = ?",
                (clean_name, clean_name, clean_name, clean_name)
            ).fetchone()
            if row:
                return row[0]
        except Exception:
            pass  # Table may not exist in test DBs — fall through to dict

    if clean_name in TEAM_MAP:
        return TEAM_MAP[clean_name]

    for key, abbr in TEAM_MAP.items():
        if key in clean_name:
            return abbr

    # Final check for cases where the abbreviation itself is passed
    if len(clean_name) == 3 and clean_name.isupper() and clean_name in TEAM_MAP.values():
        return clean_name

    return None


# BDL and Tank01 use 5 non-standard short codes; all other 25 teams match our standard abbr.
_BDL_TO_STANDARD = {
    'GS':  'GSW',   # Golden State Warriors
    'NO':  'NOP',   # New Orleans Pelicans
    'NY':  'NYK',   # New York Knicks
    'PHO': 'PHX',   # Phoenix Suns
    'SA':  'SAS',   # San Antonio Spurs
}


def normalize_bdl_abbr(abbr: str) -> str:
    """
    Convert a BDL/Tank01 short-code team abbreviation to our standard 3-letter form.

    Idempotent — passing an already-standard abbreviation returns it unchanged:
        normalize_bdl_abbr('GS')  → 'GSW'
        normalize_bdl_abbr('GSW') → 'GSW'
        normalize_bdl_abbr('PHO') → 'PHX'
        normalize_bdl_abbr('PHX') → 'PHX'

    This is the single source of truth for BDL abbreviation normalization.
    All modules and scripts must import from here instead of maintaining local dicts.
    """
    if not abbr:
        return abbr
    return _BDL_TO_STANDARD.get(abbr.upper(), abbr.upper())
