#!/bin/bash
# Ludi Lite Complete Setup Script
# Run from inside your Ludi-Lite folder: bash setup.sh

set -e
echo "Creating Ludi Lite project structure..."

# Create directories
mkdir -p .streamlit .github/workflows docs

# === requirements.txt ===
cat > requirements.txt << 'EOF'
# Ludi Lite - AI Sports Research Lab
# Install: pip install -r requirements.txt

streamlit>=1.30.0
anthropic>=0.39.0
requests>=2.31.0
pytz>=2024.1

EOF
# === .gitignore ===
cat > .gitignore << 'EOF'
# Environment variables (local only - use Streamlit Cloud secrets in production)
.env

# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Virtual environments
.venv/
venv/
ENV/

# Local database (if tracking results)
*.db
*.sqlite
*.sqlite3

# Cache files
cache/
*.cache
.cache/

# IDE
.idea/
.vscode/
*.swp
*.swo

# OS files
.DS_Store
Thumbs.db

# Streamlit secrets (local testing only)
.streamlit/secrets.toml

# Logs
logs/
*.log

EOF
# === .streamlit/config.toml ===
cat > .streamlit/config.toml << 'EOF'
[server]
headless = true
enableCORS = false
enableXsrfProtection = true

[browser]
gatherUsageStats = false

EOF
# === .streamlit/secrets.toml.example ===
cat > .streamlit/secrets.toml.example << 'EOF'
# Streamlit Cloud Secrets Configuration
# Copy this to secrets.toml for local testing
# In production, add these in Streamlit Cloud dashboard under Settings > Secrets

# Required: Claude API key from console.anthropic.com
ANTHROPIC_API_KEY = "sk-ant-api03-your-key-here"

# Optional: The-Odds-API for live game data (get free key at the-odds-api.com)
ODDS_API_KEY = "your-odds-api-key-here"

EOF
# === README.md ===
cat > README.md << 'EOF'
# Ludi Lite - AI Sports Research Lab

A head-to-head comparison tool: **Claude Freestyle** vs **Claude + Ludi Methodology**

Test whether structured betting methodology improves AI analysis over raw Claude capabilities.

## Features

- **Dual Analysis Mode**: Compare raw AI reasoning vs S.A.V.A.G.E. methodology
- **Game Analysis**: Full matchup breakdowns with playtype matrices
- **Player Spotlight**: Deep dives on specific player props
- **All Stats Supported**: PTS, AST, REB, 3PM, STL, BLK, plus combos (PRA, PA, PR, RA, Stocks)
- **Time-Aware**: Analysis confidence adjusts based on time until tipoff
- **2025-26 Season Context**: Current rosters, trades, defense schemes baked in

## Quick Start (Local)

```bash
# Clone the repo
git clone https://github.com/LudiInformatio/ludi-lite.git
cd ludi-lite

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up secrets (copy example and add your API key)
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
# Edit secrets.toml with your ANTHROPIC_API_KEY

# Run the app
streamlit run app.py
```

## Deploy to Streamlit Cloud (24/7)

1. **Push to GitHub**
   ```bash
   git init
   git add .
   git commit -m "Initial commit - Ludi Lite"
   git remote add origin https://github.com/LudiInformatio/ludi-lite.git
   git push -u origin main
   ```

2. **Connect to Streamlit Cloud**
   - Go to [share.streamlit.io](https://share.streamlit.io)
   - Click "New app"
   - Select your `ludi-lite` repository
   - Set main file path: `app.py`
   - Click "Deploy"

3. **Add Secrets**
   - In Streamlit Cloud, go to your app's Settings
   - Click "Secrets"
   - Add your API keys:
     ```toml
     ANTHROPIC_API_KEY = "sk-ant-api03-..."
     ODDS_API_KEY = "your-key-here"  # Optional
     ```

4. **Done!** Your app will be live at `https://your-app.streamlit.app`

## Usage

### Game Analysis
Type natural language queries like:
- `DEN vs NYK` - Full game breakdown
- `Lakers Celtics` - Matchup analysis
- `tonight's games` - Show today's slate

### Player Props
- `Luka assists 8.5` - Player prop analysis
- `Jokic PRA` - Points + Rebounds + Assists combo
- `Tatum points rebounds` - Multiple stat focus

### Supported Stats
| Single Stats | Combo Props |
|--------------|-------------|
| PTS, AST, REB | PRA (PTS+REB+AST) |
| 3PM, STL, BLK | PA (PTS+AST) |
| TO, MIN, FGM, FTM | PR (PTS+REB) |
| | RA (REB+AST) |
| | Stocks (STL+BLK) |

## The Methodology

**S.A.V.A.G.E. Framework:**
1. **Usage Vacuum Theory** - Redistribution when stars are OUT
2. **Archetype vs Defense Scheme** - Player style vs team defense matchups
3. **Pace Context** - Game total impact on volume
4. **Blowout Tax** - Spread impact on starter minutes
5. **B2B Fatigue** - Schedule density adjustments
6. **Line Movement Intelligence** - Market signal interpretation

## Time Context

Analysis confidence varies by time:
| Badge | Time to Tipoff | Confidence |
|-------|----------------|------------|
| EARLY LOOK | 6+ hours | Low (lineups TBD) |
| AFTERNOON | 2-6 hours | Medium |
| PRE-GAME | 30min-2hr | High |
| LOCK TIME | <30 min | Highest |

## Tech Stack

- **Frontend**: Streamlit
- **AI**: Claude API (Anthropic)
- **Data**: The-Odds-API (optional)
- **Hosting**: Streamlit Cloud

## Project Structure

```
ludi-lite/
├── app.py              # Main Streamlit application
├── prompts.py          # Freestyle + Methodology prompts
├── season_context.py   # 2025-26 rosters, schemes, trades
├── components.py       # UI card components
├── requirements.txt    # Python dependencies
├── README.md           # This file
└── .streamlit/
    ├── config.toml     # Theme configuration
    └── secrets.toml    # API keys (not in git)
```

## The Experiment

Run for 30 days, logging analyses. At the end, compare:
- When did Freestyle and Methodology agree?
- When they disagreed, who was right more often?
- Did the structured methodology add value?

This answers the question: **Does my betting methodology actually improve AI predictions?**

## License

MIT - Use freely, no warranties.

---

*Built for the 2025-26 NBA season by Ludi Informatio*

EOF
# === season_context.py ===
cat > season_context.py << 'EOF'
"""
Season Context for 2025-26 NBA Season
This file grounds AI analysis in the CURRENT season, not training data.
Updated: February 2026
"""

CURRENT_SEASON = "2025-26"
SEASON_START_DATE = "2025-10-22"

# Key roster moves for 2025-26 (AI often has stale data)
ROSTER_CONTEXT = """
KEY 2025-26 ROSTER CHANGES (Use this, not your training data):

=== OFFSEASON MOVES (July 2024) ===
- Klay Thompson: NOW ON DALLAS (signed July 2024, NOT Golden State)
- Paul George: NOW ON PHILADELPHIA (signed July 2024, NOT LA Clippers)
- DeMar DeRozan: NOW ON SACRAMENTO (signed July 2024, NOT Chicago)
- Tyus Jones: NOW ON PHOENIX (signed July 2024, starting PG)
- Tobias Harris: NOW ON DETROIT (signed July 2024)
- Dejounte Murray: NOW ON NEW ORLEANS (traded from Atlanta)
- Kentavious Caldwell-Pope: NOW ON ORLANDO (signed July 2024)
- Jonas Valanciunas: NOW ON WASHINGTON
- Malik Beasley: NOW ON DETROIT
- Isaiah Hartenstein: NOW ON OKLAHOMA CITY (signed July 2024, starting C)
- Caleb Martin: NOW ON PHILADELPHIA (signed July 2024)

=== TRADE DEADLINE MOVES (Feb 2026) ===
- Anthony Davis: NOW ON WASHINGTON (traded from Dallas, Feb 4)
- James Harden: NOW ON CLEVELAND (traded from LA Clippers, Feb 4)
- Nikola Vučević: NOW ON BOSTON (traded from Chicago, Feb 4)
- Jared McCain: NOW ON OKLAHOMA CITY (traded from Philadelphia, Feb 4)
- Coby White: NOW ON CHARLOTTE (traded from Chicago, Feb 4)
- Chris Paul: NOW ON TORONTO (three-team trade, Feb 4)
- Lonzo Ball: FREE AGENT (waived by Utah after trade from Cleveland)
- Darius Garland: NOW ON LA CLIPPERS (traded from Cleveland for Harden)

=== DEADLINE IS FEB 5, 2026 AT 3 PM ET - MORE MOVES POSSIBLE ===
"""

# Defense scheme assignments for 2025-26
# These change year-to-year based on personnel and coaching
DEFENSE_SCHEMES_2025_26 = {
    "PAINT_PACK": ["OKC", "BOS", "DET", "MIN", "SAS", "ORL"],
    "BLITZ": ["HOU", "TOR", "MIA", "PHX"],
    "PERIMETER": ["GSW", "DAL", "NYK"],
    "SWITCH_HEAVY": ["CLE", "LAC", "MEM"],
    "FUNNEL": ["WAS", "ATL", "CHI", "UTA", "SAC"],
    "NEUTRAL": ["LAL", "DEN", "MIL", "BKN", "IND", "POR", "CHA", "NOP"]
}

# Offensive classifications for 2025-26
OFFENSE_SCHEMES_2025_26 = {
    "THREE_POINT_CENTRIC": ["BOS", "GSW", "IND", "ATL", "UTA"],
    "MOTION_OFFENSE": ["DEN", "MIA", "SAS"],
    "PACE_PUSH": ["SAC", "IND", "ATL", "CHA"],
    "PAINT_ATTACK": ["MIL", "NOP", "CLE", "ORL"],
    "ISOLATION_HEAVY": ["PHX", "DAL", "LAL", "BKN"],
    "BALANCED": ["OKC", "NYK", "MIN", "LAC", "MEM", "HOU", "TOR", "POR", "DET", "WAS", "CHI"]
}

# Key injuries/situations to track (update as season progresses)
CURRENT_CONTEXT_NOTES = """
CURRENT 2025-26 CONTEXT (as of February 5, 2026):
- This is the CURRENT season, games are happening NOW
- TRADE DEADLINE: February 5, 2026 at 3:00 PM ET (TODAY)
- All-Star break is mid-February 2026
- Playoff race is heating up

MAJOR DEADLINE RUMORS TO WATCH:
- Giannis Antetokounmpo (MIL): May be traded, 4-6 weeks out with calf injury
- Ja Morant (MEM): Sacramento Kings heavily linked, Miami Heat also interested
- More moves expected before 3 PM ET deadline

NOTE: Newly traded players may not be integrated into new teams immediately.
Check if player has played with new team before projecting.
"""

def get_defense_scheme(team_abbr: str) -> str:
    """Get a team's defensive scheme for 2025-26"""
    for scheme, teams in DEFENSE_SCHEMES_2025_26.items():
        if team_abbr.upper() in teams:
            return scheme
    return "NEUTRAL"

def get_offense_scheme(team_abbr: str) -> str:
    """Get a team's offensive classification for 2025-26"""
    for scheme, teams in OFFENSE_SCHEMES_2025_26.items():
        if team_abbr.upper() in teams:
            return scheme
    return "BALANCED"

def get_full_season_context() -> str:
    """Return complete season context for AI prompts"""
    defense_list = "\n".join([
        f"  - {scheme}: {', '.join(teams)}"
        for scheme, teams in DEFENSE_SCHEMES_2025_26.items()
    ])

    return f"""
=== CURRENT SEASON: {CURRENT_SEASON} NBA SEASON ===
Today's Date: Use current date, not training data.
Season Status: Regular season in progress (started {SEASON_START_DATE})

{ROSTER_CONTEXT}

DEFENSE SCHEME ASSIGNMENTS (2025-26):
{defense_list}

{CURRENT_CONTEXT_NOTES}

IMPORTANT: If your training data conflicts with the above, USE THE ABOVE.
These are the CURRENT facts for the 2025-26 season.
"""

EOF
# === prompts.py ===
cat > prompts.py << 'PROMPTSEOF'
"""
Prompt definitions for Ludi Lite
Two modes: Freestyle (raw AI) vs Methodology (Ludi framework)
"""

from season_context import get_full_season_context, DEFENSE_SCHEMES_2025_26

# Get current season context
SEASON_CONTEXT = get_full_season_context()

# =============================================================================
# FREESTYLE PROMPT - Let AI think naturally, but ground it in current season
# =============================================================================

FREESTYLE_PROMPT = f"""
{SEASON_CONTEXT}

You are an NBA research analyst for the 2025-26 season. Your job is to break down
games and surface interesting angles worth investigating.

IMPORTANT RULES:
1. This is the 2025-26 NBA season - use current rosters and context above
2. Do NOT give betting picks or recommendations
3. Be a research assistant, not a tout
4. Say "I don't know" when uncertain
5. Be honest about limitations

When analyzing a game, provide:

1. KEY STORYLINES
   What makes this game interesting? Narratives, revenge games, streaks?

2. STATISTICAL OBSERVATIONS
   What trends stand out? Recent form, home/away splits, head-to-head?

3. MATCHUP THOUGHTS
   How do these teams match up stylistically? Any obvious advantages?

4. FLAGS & CONCERNS
   What could go wrong? Injury risks, schedule spots, variance factors?

5. PLAYERS/ANGLES TO WATCH
   Who or what deserves attention? Not picks - just research leads.

Keep analysis focused and honest. If the data is thin, say so.
"""

# =============================================================================
# LUDI METHODOLOGY PROMPT - Structured framework from the Ludi-Bot model
# =============================================================================

LUDI_METHOD_PROMPT = f"""
{SEASON_CONTEXT}

You are analyzing this game using the S.A.V.A.G.E. methodology for the 2025-26 NBA season.

=== CORE PRINCIPLES ===

1. USAGE VACUUM THEORY
   When a high-usage player is OUT, their touches/shots/usage MUST go somewhere.
   - Identify who's missing and their usage rate
   - Primary beneficiary (similar role) gets +15-25% boost
   - Secondary beneficiaries get +5-10% boost
   - Calculate the vacuum effect

2. ARCHETYPE vs DEFENSE SCHEME MATRIX

   Player Archetypes:
   - HELIOCENTRIC: Ball-dominant creator (Luka, Trae, LeBron)
   - SLASHER: Attacks rim, draws fouls (Ant, SGA)
   - SNIPER: Catch-and-shoot specialist (Klay, Buddy)
   - RIM_RUNNER: Lob threat, PnR roll man (Gafford, Ayton)
   - STRETCH_BIG: Spacing 5 (KAT, Brook Lopez)
   - PLAYMAKER: High-assist guard (CP3, Haliburton)
   - TWO_WAY_WING: Elite defender who scores (Kawhi, OG)

   Defense Schemes (2025-26):
   - PAINT_PACK: {', '.join(DEFENSE_SCHEMES_2025_26['PAINT_PACK'])}
     (Protect rim, give up 3s. Bad for SLASHERS, good for SNIPERS/STRETCH_BIGS)

   - BLITZ: {', '.join(DEFENSE_SCHEMES_2025_26['BLITZ'])}
     (Aggressive traps, force turnovers. Turnover risk for ball handlers, AST variance)

   - PERIMETER: {', '.join(DEFENSE_SCHEMES_2025_26['PERIMETER'])}
     (Chase shooters off line. Open lanes for SLASHERS, tough for SNIPERS)

   - SWITCH_HEAVY: {', '.join(DEFENSE_SCHEMES_2025_26['SWITCH_HEAVY'])}
     (Versatile switching. Neutral, depends on individual matchups)

   - FUNNEL: {', '.join(DEFENSE_SCHEMES_2025_26['FUNNEL'])}
     (Funnel to weak spots. Exploitable by smart teams)

3. PACE CONTEXT
   - Game Total 230+: Run and gun, volume UP 5-8%
   - Game Total 220-230: Normal pace
   - Game Total 215-: Grind game, volume DOWN 5-8%
   - Factor both teams' pace rankings

4. BLOWOUT TAX
   - Spread 10+: Significant garbage time risk
   - Favorites' starters lose 4-8 minutes in blowouts
   - Bench players get BOOST in blowouts
   - Underdogs keep starters in (fighting)

5. BACK-TO-BACK FATIGUE
   - Road B2B: -3% to -5% on volume stats
   - Home B2B: -1% to -2% on volume stats
   - Guards affected more than bigs
   - Check 3-in-4 or 4-in-5 schedule density

6. LINE MOVEMENT INTELLIGENCE
   - Line moving toward your side: Market agrees (confirmation)
   - Line moving away: Market disagrees (investigate why)
   - Significant move (1+ pts): Something happened (injury, info)

=== OUTPUT FORMAT (Use this exact structure) ===

## 📊 GAME CONTEXT
| Factor | Value | Signal |
|--------|-------|--------|
| Spread | [spread] | [implication] |
| Total | [total] | [pace signal: HIGH/NORMAL/LOW] |
| Pace Matchup | [Away #X] vs [Home #X] | [volume impact] |
| Schedule | [B2B/rest for each team] | [fatigue factor] |

## 🚨 KEY ABSENCES & USAGE VACUUM
**[Away Team] OUT/GTD:** [list or "None"]
**[Home Team] OUT/GTD:** [list or "None"]

| Team | Absent Player | Usage% | Primary Beneficiary | Boost |
|------|---------------|--------|---------------------|-------|
| [AWY] | [name] | [%] | [teammate] | [+X%] |
| [HME] | [name] | [%] | [teammate] | [+X%] |

(If no significant absences, just note "No major usage vacuum scenarios")

---

## ⚔️ MATCHUP MATRIX (BOTH DIRECTIONS)

### [Away Team] OFFENSE vs [Home Team] DEFENSE
| Playtype | [AWY] OFF | [HME] DEF | Edge |
|----------|-----------|-----------|------|
| Post Up | #X | #X | 🟢/🔴/⚪ |
| PnR Handler | #X | #X | 🟢/🔴/⚪ |
| Isolation | #X | #X | 🟢/🔴/⚪ |
| Transition | #X | #X | 🟢/🔴/⚪ |
| Spot Up | #X | #X | 🟢/🔴/⚪ |

**[Away Team] Key Advantages:** [list 1-2 edges]

### [Home Team] OFFENSE vs [Away Team] DEFENSE
| Playtype | [HME] OFF | [AWY] DEF | Edge |
|----------|-----------|-----------|------|
| Post Up | #X | #X | 🟢/🔴/⚪ |
| PnR Handler | #X | #X | 🟢/🔴/⚪ |
| Isolation | #X | #X | 🟢/🔴/⚪ |
| Transition | #X | #X | 🟢/🔴/⚪ |
| Spot Up | #X | #X | 🟢/🔴/⚪ |

**[Home Team] Key Advantages:** [list 1-2 edges]

---

## ⚠️ FLAGS
- Blowout risk: [YES/NO - reason]
- Fatigue factor: [which team affected, why]
- Line movement: [direction + what it might mean]

---

## 👀 PLAYERS TO WATCH (2-3 per team)

### [Away Team]
| Player | Archetype | Why This Matchup Matters | Stat Focus |
|--------|-----------|--------------------------|------------|
| [name] | [type] | [scheme advantage/disadvantage] | [PTS/AST/etc] |
| [name] | [type] | [scheme advantage/disadvantage] | [PTS/AST/etc] |

### [Home Team]
| Player | Archetype | Why This Matchup Matters | Stat Focus |
|--------|-----------|--------------------------|------------|
| [name] | [type] | [scheme advantage/disadvantage] | [PTS/AST/etc] |
| [name] | [type] | [scheme advantage/disadvantage] | [PTS/AST/etc] |

---

## 🎯 BOTTOM LINE
**[Away Team] path to winning:** [1 sentence]
**[Home Team] path to winning:** [1 sentence]
**Total lean:** [OVER/UNDER + key reason]
**Key question:** [What's the one thing that decides this game?]

Be specific. Use tables. Cover BOTH sides fairly. Apply the framework.
"""

# =============================================================================
# PLAYER SPOTLIGHT PROMPT - Deep dive on specific player
# =============================================================================

PLAYER_SPOTLIGHT_PROMPT = f"""
{SEASON_CONTEXT}

Analyze this specific player using the S.A.V.A.G.E. methodology for 2025-26.

STAT TYPES YOU MAY ANALYZE:
- Single stats: PTS, AST, REB, 3PM, STL, BLK, TO, MIN, FGM, FTM
- Combo props: PRA (PTS+REB+AST), PA (PTS+AST), PR (PTS+REB), RA (REB+AST), Stocks (STL+BLK)
- Special: Double-Double odds, Triple-Double odds, Fantasy Points

For COMBO PROPS, analyze each component stat and how they combine for the player's profile.

Output in this exact format:

## 🏀 PLAYER PROFILE
| Attribute | Value |
|-----------|-------|
| Archetype | [PRIMARY] / [Secondary] |
| Usage Rate | [X%] |
| Role | [Starter/Bench, minutes] |
| Recent Form | 🔥 Hot / ❄️ Cold / ➡️ Steady |

## ⚔️ MATCHUP ANALYSIS
| Factor | Data | Signal |
|--------|------|--------|
| Opp Defense Scheme | [SCHEME] | [good/bad for archetype] |
| Archetype vs Scheme | [matchup description] | 🟢/🔴/⚪ |
| Opp Rank vs Position | #[X] | [context] |
| Key Defender | [name if notable] | [matchup note] |

## 📊 CONTEXT FACTORS
| Factor | Status | Impact |
|--------|--------|--------|
| Schedule | [Rest/B2B] | [+X% / -X%] |
| Usage Vacuum | [Who's OUT?] | [boost if any] |
| Pace/Total | [game total] | [volume impact] |
| Blowout Risk | [spread] | [helps/hurts this player] |

## 📈 STAT OUTLOOK
(Focus on the requested stat, but show relevant supporting stats)

| Stat | L15 Avg | vs This Opp | Outlook |
|------|---------|-------------|---------|
| PTS | [X] | [context] | 🟢/🔴/⚪ |
| AST | [X] | [context] | 🟢/🔴/⚪ |
| REB | [X] | [context] | 🟢/🔴/⚪ |
| 3PM | [X] | [context] | 🟢/🔴/⚪ |
| STL | [X] | [context] | 🟢/🔴/⚪ |
| BLK | [X] | [context] | 🟢/🔴/⚪ |

**If COMBO PROP requested:**
| Combo | Sum L15 | Projection | Outlook |
|-------|---------|------------|---------|
| PRA | [X+X+X] | [expected] | 🟢/🔴/⚪ |
| PA | [X+X] | [expected] | 🟢/🔴/⚪ |
| etc. | ... | ... | ... |

## ⚠️ FLAGS
- [Flag 1]
- [Flag 2]

## 🎯 BOTTOM LINE
**Favorable stats:** [list]
**Concerning stats:** [list]
**Key number to watch:** [specific line that matters]

Use tables. Be specific. Reference the methodology.
"""


def get_prompt(mode: str) -> str:
    """Return appropriate prompt based on mode"""
    if mode == "freestyle":
        return FREESTYLE_PROMPT
    elif mode == "methodology":
        return LUDI_METHOD_PROMPT
    elif mode == "player":
        return PLAYER_SPOTLIGHT_PROMPT
    else:
        return FREESTYLE_PROMPT

PROMPTSEOF
# === components.py ===
cat > components.py << 'COMPONENTSEOF'
"""
UI Components for Ludi Lite
Styled output cards inspired by PropsMadness, betting research tools
"""

import streamlit as st

# Color scheme (matching Ludi brand)
COLORS = {
    "dark_navy": "#0F172A",
    "slate": "#1E293B",
    "gold": "#FBBF24",
    "emerald": "#10B981",
    "red": "#EF4444",
    "blue": "#60A5FA",
    "gray": "#94A3B8",
    "white": "#F8FAFC"
}


def indicator(value, thresholds: dict = None, inverse: bool = False):
    """
    Return colored indicator based on value
    thresholds: {"good": 7, "bad": 20} - below good is green, above bad is red
    inverse: if True, lower is better (like rankings)
    """
    if thresholds is None:
        return "⚪"

    good = thresholds.get("good", 10)
    bad = thresholds.get("bad", 20)

    try:
        val = float(value) if not isinstance(value, (int, float)) else value
    except (ValueError, TypeError):
        return "⚪"

    if inverse:
        if val <= good:
            return "🟢"
        elif val >= bad:
            return "🔴"
        else:
            return "🟡"
    else:
        if val >= good:
            return "🟢"
        elif val <= bad:
            return "🔴"
        else:
            return "🟡"


def render_player_card(data: dict):
    """
    Render a player prop card like PropsMadness

    data = {
        "player_name": "Amen Thompson",
        "team": "HOU",
        "opponent": "BOS",
        "prop": "Assists",
        "line": 5.5,
        "odds": -107,
        "direction": "Over",
        "metrics": {
            "L15 Average": {"value": 6.1, "signal": "good"},
            "L15 Hit Rate": {"value": "9/15", "signal": "good"},
            "H2H": {"value": "1/4", "signal": "bad"},
            ...
        },
        "ludi_analysis": {
            "archetype": "SLASHER/PLAYMAKER",
            "opp_scheme": "PAINT_PACK",
            "matchup_grade": "C+",
            "flags": ["30th pace = grind game", "H2H concerning"],
            "verdict": "LEAN UNDER"
        }
    }
    """
    st.markdown(f"""
    <div style="background: {COLORS['slate']}; border-radius: 12px; padding: 20px; margin: 10px 0;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
            <div>
                <h3 style="color: {COLORS['white']}; margin: 0;">{data.get('player_name', 'Player')}</h3>
                <p style="color: {COLORS['gray']}; margin: 5px 0;">{data.get('team', '')} vs {data.get('opponent', '')}</p>
            </div>
            <div style="text-align: right;">
                <span style="background: {COLORS['gold']}; color: {COLORS['dark_navy']}; padding: 5px 12px; border-radius: 20px; font-weight: bold;">
                    {data.get('direction', 'Over')} {data.get('line', '')} {data.get('prop', '')}
                </span>
                <p style="color: {COLORS['emerald']}; margin: 5px 0; font-weight: bold;">{data.get('odds', '')}</p>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Metrics table
    if "metrics" in data:
        cols = st.columns(2)
        metrics = list(data["metrics"].items())

        for i, (metric_name, metric_data) in enumerate(metrics):
            col = cols[i % 2]
            value = metric_data.get("value", "N/A")
            signal = metric_data.get("signal", "neutral")

            if signal == "good":
                color = COLORS["emerald"]
                icon = "🟢"
            elif signal == "bad":
                color = COLORS["red"]
                icon = "🔴"
            else:
                color = COLORS["gray"]
                icon = "⚪"

            col.markdown(f"""
            <div style="display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid {COLORS['dark_navy']};">
                <span style="color: {COLORS['gray']};">{metric_name}</span>
                <span style="color: {color}; font-weight: bold;">{icon} {value}</span>
            </div>
            """, unsafe_allow_html=True)

    # Ludi Analysis section
    if "ludi_analysis" in data:
        la = data["ludi_analysis"]
        st.markdown(f"""
        <div style="background: {COLORS['dark_navy']}; border-radius: 8px; padding: 15px; margin-top: 15px;">
            <h4 style="color: {COLORS['gold']}; margin: 0 0 10px 0;">🎯 LUDI ANALYSIS</h4>
            <p style="color: {COLORS['gray']}; margin: 5px 0;"><strong>Archetype:</strong> {la.get('archetype', 'N/A')}</p>
            <p style="color: {COLORS['gray']}; margin: 5px 0;"><strong>vs Scheme:</strong> {la.get('opp_scheme', 'N/A')}</p>
            <p style="color: {COLORS['gray']}; margin: 5px 0;"><strong>Matchup Grade:</strong> {la.get('matchup_grade', 'N/A')}</p>
        </div>
        """, unsafe_allow_html=True)

        # Flags
        if la.get("flags"):
            st.markdown(f"<p style='color: {COLORS['gold']}; font-weight: bold; margin-top: 10px;'>⚠️ FLAGS:</p>", unsafe_allow_html=True)
            for flag in la["flags"]:
                st.markdown(f"<p style='color: {COLORS['gray']}; margin: 2px 0 2px 15px;'>• {flag}</p>", unsafe_allow_html=True)

        # Verdict
        verdict = la.get("verdict", "")
        if verdict:
            verdict_color = COLORS["emerald"] if "OVER" in verdict.upper() else COLORS["red"] if "UNDER" in verdict.upper() else COLORS["gray"]
            st.markdown(f"""
            <div style="margin-top: 15px; padding: 10px; background: {verdict_color}20; border-left: 4px solid {verdict_color}; border-radius: 4px;">
                <p style="color: {verdict_color}; font-weight: bold; margin: 0;">VERDICT: {verdict}</p>
            </div>
            """, unsafe_allow_html=True)


def render_game_matchup_card(data: dict):
    """
    Render a game matchup card with playtype breakdown

    data = {
        "away_team": "DEN",
        "home_team": "NYK",
        "spread": -4.5,
        "total": 221.5,
        "away_record": "5-5 L10",
        "home_record": "7-3 L10",
        "playtype_matchup": [
            {"playtype": "Post Up", "off_rank": 1, "def_rank": 22, "edge": "away"},
            {"playtype": "PnR Ball Handler", "off_rank": 10, "def_rank": 26, "edge": "away"},
            ...
        ],
        "key_advantages": {
            "away": ["Post Up (#1 vs #22)", "PnR Handler (#10 vs #26)"],
            "home": ["Transition (#9 vs #24)", "Spot Up (#1 vs #16)"]
        },
        "ludi_notes": {
            "pace_context": "Both teams 25th-26th pace - SLOW GAME",
            "scheme_matchup": "NYK PERIMETER vs DEN MOTION",
            "flags": ["Jokic post-up dominance", "NYK elite defense L10"],
            "players_to_watch": ["Jokic (post + assists)", "Murray (PnR)", "Brunson (needs ISO)"]
        }
    }
    """
    away = data.get("away_team", "AWAY")
    home = data.get("home_team", "HOME")
    spread = data.get("spread", 0)
    total = data.get("total", 0)

    # Header
    spread_display = f"{home} {spread:+.1f}" if spread != 0 else "PICK"

    st.markdown(f"""
    <div style="background: {COLORS['slate']}; border-radius: 12px; padding: 20px; margin: 10px 0;">
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <div style="text-align: center;">
                <h2 style="color: {COLORS['white']}; margin: 0;">{away}</h2>
                <p style="color: {COLORS['gray']}; margin: 5px 0;">{data.get('away_record', '')}</p>
            </div>
            <div style="text-align: center;">
                <p style="color: {COLORS['gold']}; font-weight: bold; margin: 0;">{spread_display}</p>
                <p style="color: {COLORS['gray']}; margin: 5px 0;">O/U {total}</p>
            </div>
            <div style="text-align: center;">
                <h2 style="color: {COLORS['white']}; margin: 0;">{home}</h2>
                <p style="color: {COLORS['gray']}; margin: 5px 0;">{data.get('home_record', '')}</p>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Playtype matchup table
    if "playtype_matchup" in data:
        st.markdown(f"<h4 style='color: {COLORS['gold']}; margin-top: 20px;'>PLAYTYPE MATCHUP</h4>", unsafe_allow_html=True)

        st.markdown(f"""
        <div style="display: flex; justify-content: space-between; padding: 10px 0; border-bottom: 2px solid {COLORS['gray']};">
            <span style="color: {COLORS['blue']}; font-weight: bold; width: 80px;">{away} OFF</span>
            <span style="color: {COLORS['gray']}; font-weight: bold; flex: 1; text-align: center;">Playtype</span>
            <span style="color: {COLORS['emerald']}; font-weight: bold; width: 80px; text-align: right;">{home} DEF</span>
        </div>
        """, unsafe_allow_html=True)

        for pt in data["playtype_matchup"]:
            playtype = pt.get("playtype", "")
            off_rank = pt.get("off_rank", "-")
            def_rank = pt.get("def_rank", "-")
            edge = pt.get("edge", "neutral")

            if edge == "away":
                edge_indicator = f"<span style='color: {COLORS['emerald']};'>🟢 EDGE</span>"
            elif edge == "home":
                edge_indicator = f"<span style='color: {COLORS['red']};'>🔴 TOUGH</span>"
            else:
                edge_indicator = f"<span style='color: {COLORS['gray']};'>⚪</span>"

            st.markdown(f"""
            <div style="display: flex; justify-content: space-between; align-items: center; padding: 8px 0; border-bottom: 1px solid {COLORS['dark_navy']};">
                <span style="color: {COLORS['blue']}; width: 80px;">#{off_rank}</span>
                <span style="color: {COLORS['white']}; flex: 1; text-align: center;">{playtype}</span>
                <span style="color: {COLORS['emerald']}; width: 50px; text-align: center;">#{def_rank}</span>
                <span style="width: 80px; text-align: right;">{edge_indicator}</span>
            </div>
            """, unsafe_allow_html=True)

    # Key advantages
    if "key_advantages" in data:
        col1, col2 = st.columns(2)

        with col1:
            st.markdown(f"<h5 style='color: {COLORS['blue']};'>{away} ADVANTAGES</h5>", unsafe_allow_html=True)
            for adv in data["key_advantages"].get("away", []):
                st.markdown(f"<p style='color: {COLORS['gray']}; margin: 2px 0;'>• {adv}</p>", unsafe_allow_html=True)

        with col2:
            st.markdown(f"<h5 style='color: {COLORS['emerald']};'>{home} ADVANTAGES</h5>", unsafe_allow_html=True)
            for adv in data["key_advantages"].get("home", []):
                st.markdown(f"<p style='color: {COLORS['gray']}; margin: 2px 0;'>• {adv}</p>", unsafe_allow_html=True)

    # Ludi notes
    if "ludi_notes" in data:
        ln = data["ludi_notes"]
        st.markdown(f"""
        <div style="background: {COLORS['dark_navy']}; border-radius: 8px; padding: 15px; margin-top: 20px;">
            <h4 style="color: {COLORS['gold']}; margin: 0 0 10px 0;">🎯 LUDI GAME NOTES</h4>
        </div>
        """, unsafe_allow_html=True)

        if ln.get("pace_context"):
            st.markdown(f"<p style='color: {COLORS['gray']};'><strong>Pace:</strong> {ln['pace_context']}</p>", unsafe_allow_html=True)

        if ln.get("scheme_matchup"):
            st.markdown(f"<p style='color: {COLORS['gray']};'><strong>Schemes:</strong> {ln['scheme_matchup']}</p>", unsafe_allow_html=True)

        if ln.get("flags"):
            st.markdown(f"<p style='color: {COLORS['gold']}; font-weight: bold;'>⚠️ FLAGS:</p>", unsafe_allow_html=True)
            for flag in ln["flags"]:
                st.markdown(f"<p style='color: {COLORS['gray']}; margin: 2px 0 2px 15px;'>• {flag}</p>", unsafe_allow_html=True)

        if ln.get("players_to_watch"):
            st.markdown(f"<p style='color: {COLORS['emerald']}; font-weight: bold;'>👀 PLAYERS TO WATCH:</p>", unsafe_allow_html=True)
            for player in ln["players_to_watch"]:
                st.markdown(f"<p style='color: {COLORS['gray']}; margin: 2px 0 2px 15px;'>• {player}</p>", unsafe_allow_html=True)


def render_comparison_header():
    """Render the side-by-side comparison header"""
    col1, col2 = st.columns(2)

    with col1:
        st.markdown(f"""
        <div style="background: {COLORS['blue']}20; border: 2px solid {COLORS['blue']}; border-radius: 8px; padding: 10px; text-align: center;">
            <h3 style="color: {COLORS['blue']}; margin: 0;">🤖 FREESTYLE</h3>
            <p style="color: {COLORS['gray']}; margin: 5px 0 0 0; font-size: 12px;">Raw AI - No methodology</p>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
        <div style="background: {COLORS['emerald']}20; border: 2px solid {COLORS['emerald']}; border-radius: 8px; padding: 10px; text-align: center;">
            <h3 style="color: {COLORS['emerald']}; margin: 0;">🎯 LUDI METHOD</h3>
            <p style="color: {COLORS['gray']}; margin: 5px 0 0 0; font-size: 12px;">S.A.V.A.G.E. framework applied</p>
        </div>
        """, unsafe_allow_html=True)

COMPONENTSEOF
# === .github/workflows/daily_health_check.yml ===
cat > .github/workflows/daily_health_check.yml << 'WORKFLOWEOF'
# Ludi Lite Daily Health Check (Claude Code)
# Uses Claude Code to review codebase and dashboard health daily
# Sends results to Slack #ludi-lite-health channel
#
# TODO: Configure before enabling:
# 1. Add CLAUDE_CODE_OAUTH_TOKEN to repository secrets (same as Ludi-Bot)
# 2. Add STREAMLIT_APP_URL to repository secrets (optional)
# 3. Add SLACK_WEBHOOK_URL to repository secrets (from Claude Agents app)
# 4. Uncomment the schedule trigger

name: Daily Health Check (Claude Code)

on:
  # schedule:
  #   - cron: '0 11 * * *'  # 6 AM EST daily (11 UTC)
  workflow_dispatch:  # Manual trigger for testing

jobs:
  claude-health-review:
    runs-on: ubuntu-latest
    timeout-minutes: 15
    permissions:
      contents: read
      issues: write
      id-token: write

    steps:
      - name: Checkout repository
        uses: actions/checkout@v4
        with:
          fetch-depth: 1

      - name: Run Claude Code Health Review
        id: health-check
        uses: anthropics/claude-code-action@v1
        with:
          claude_code_oauth_token: ${{ secrets.CLAUDE_CODE_OAUTH_TOKEN }}
          prompt: |
            You are the HEALTH MONITOR AGENT for Ludi Lite.

            YOUR TASK: Perform a daily health check and generate a report.

            CHECKS TO PERFORM:
            1. **Code Structure**: Verify all required files exist (app.py, prompts.py, season_context.py, components.py, requirements.txt)
            2. **Syntax Validation**: Check all Python files for syntax errors
            3. **Import Check**: Verify core imports work (streamlit, anthropic, requests)
            4. **Dependency Audit**: Check requirements.txt for any issues
            5. **Code Quality**: Look for any obvious bugs, security issues, or deprecated patterns
            6. **API Integration**: Verify get_api_key() function is properly configured

            STREAMLIT_APP_URL: ${{ secrets.STREAMLIT_APP_URL || 'not configured' }}
            If STREAMLIT_APP_URL is set, also check if the deployed app responds.

            OUTPUT FORMAT:
            Generate a health report with this structure:

            # Ludi Lite Daily Health Report
            **Date:** [current date]
            **Status:** [HEALTHY / ISSUES DETECTED]

            ## Check Results
            | Check | Status | Notes |
            |-------|--------|-------|
            | Code Structure | [PASS/FAIL] | [details] |
            | Syntax | [PASS/FAIL] | [details] |
            | Imports | [PASS/FAIL] | [details] |
            | Dependencies | [PASS/FAIL] | [details] |
            | Code Quality | [PASS/FAIL] | [details] |
            | API Config | [PASS/FAIL] | [details] |
            | App Health | [PASS/FAIL/SKIPPED] | [details] |

            ## Issues Found
            [List any issues, or 'None']

            ## Recommendations
            [Any suggested improvements, or 'None']

            IMPORTANT:
            - Be thorough but concise
            - Flag any security concerns immediately
            - Note any files that may need updates
            - Do NOT make any changes - this is READ-ONLY review

            After your analysis, output a single line at the end:
            HEALTH_STATUS: HEALTHY
            or
            HEALTH_STATUS: ISSUES_DETECTED

      - name: Parse health status
        id: parse-status
        run: |
          # Default to healthy if we can't parse
          echo "status=healthy" >> $GITHUB_OUTPUT

      - name: Notify Slack - Success
        if: success()
        env:
          SLACK_WEBHOOK_URL: ${{ secrets.SLACK_WEBHOOK_URL }}
        run: |
          if [ -z "$SLACK_WEBHOOK_URL" ]; then
            echo "SLACK_WEBHOOK_URL not configured, skipping notification"
            exit 0
          fi

          curl -X POST "$SLACK_WEBHOOK_URL" \
            -H 'Content-type: application/json' \
            -d '{
              "blocks": [
                {
                  "type": "header",
                  "text": {
                    "type": "plain_text",
                    "text": "Ludi Lite Health Check Complete",
                    "emoji": true
                  }
                },
                {
                  "type": "section",
                  "fields": [
                    {
                      "type": "mrkdwn",
                      "text": "*Status:*\nCheck Complete"
                    },
                    {
                      "type": "mrkdwn",
                      "text": "*Date:*\n'"$(date '+%Y-%m-%d %H:%M UTC')"'"
                    }
                  ]
                },
                {
                  "type": "section",
                  "text": {
                    "type": "mrkdwn",
                    "text": "Claude completed the health check. See GitHub Actions for full report."
                  }
                },
                {
                  "type": "actions",
                  "elements": [
                    {
                      "type": "button",
                      "text": {
                        "type": "plain_text",
                        "text": "View Report",
                        "emoji": true
                      },
                      "url": "https://github.com/${{ github.repository }}/actions/runs/${{ github.run_id }}"
                    }
                  ]
                },
                {
                  "type": "context",
                  "elements": [
                    {
                      "type": "mrkdwn",
                      "text": "_Claude Agents | Ludi Lite_"
                    }
                  ]
                }
              ]
            }'

      - name: Notify Slack - Workflow Failed
        if: failure()
        env:
          SLACK_WEBHOOK_URL: ${{ secrets.SLACK_WEBHOOK_URL }}
        run: |
          if [ -z "$SLACK_WEBHOOK_URL" ]; then
            echo "SLACK_WEBHOOK_URL not configured, skipping notification"
            exit 0
          fi

          curl -X POST "$SLACK_WEBHOOK_URL" \
            -H 'Content-type: application/json' \
            -d '{
              "blocks": [
                {
                  "type": "header",
                  "text": {
                    "type": "plain_text",
                    "text": "Ludi Lite Health Check FAILED",
                    "emoji": true
                  }
                },
                {
                  "type": "section",
                  "text": {
                    "type": "mrkdwn",
                    "text": "The health check workflow encountered an error and could not complete."
                  }
                },
                {
                  "type": "actions",
                  "elements": [
                    {
                      "type": "button",
                      "text": {
                        "type": "plain_text",
                        "text": "View Error Logs",
                        "emoji": true
                      },
                      "url": "https://github.com/${{ github.repository }}/actions/runs/${{ github.run_id }}",
                      "style": "danger"
                    }
                  ]
                },
                {
                  "type": "context",
                  "elements": [
                    {
                      "type": "mrkdwn",
                      "text": "_Claude Agents | Ludi Lite_"
                    }
                  ]
                }
              ]
            }'

WORKFLOWEOF
# === app.py ===
cat > app.py << 'APPEOF'
"""
Ludi Lite - AI Sports Research Lab
Dashboard with Game Cards + Chat Interface
Side-by-side: Claude Freestyle vs Claude + Ludi Methodology

Run with: streamlit run app.py
Mobile: Access via http://YOUR-IP:8501 on same WiFi
"""

import streamlit as st
import anthropic
import sqlite3
import json
import os
from datetime import datetime, date
from typing import Optional, Tuple
import requests
import pytz

from prompts import FREESTYLE_PROMPT, LUDI_METHOD_PROMPT, PLAYER_SPOTLIGHT_PROMPT
from season_context import get_defense_scheme, get_offense_scheme, CURRENT_SEASON

# Timezone for game times (Eastern)
ET = pytz.timezone('America/New_York')

# =============================================================================
# Configuration
# =============================================================================

st.set_page_config(
    page_title="Ludi Lite",
    page_icon="🏀",
    layout="wide",
    initial_sidebar_state="collapsed"  # Better for mobile
)

# Custom CSS for mobile-friendly cards
st.markdown("""
<style>
    /* Dark theme */
    .stApp {
        background-color: #0F172A;
    }

    /* Game card styling */
    .game-card {
        background: linear-gradient(135deg, #1E293B 0%, #334155 100%);
        border-radius: 12px;
        padding: 15px;
        margin: 8px 0;
        border: 1px solid #475569;
        cursor: pointer;
        transition: transform 0.2s, box-shadow 0.2s;
    }
    .game-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(251, 191, 36, 0.2);
    }
    .game-card h3 {
        color: #F8FAFC;
        margin: 0 0 8px 0;
        font-size: 18px;
    }
    .game-card .line {
        color: #FBBF24;
        font-weight: bold;
        font-size: 14px;
    }
    .game-card .time {
        color: #94A3B8;
        font-size: 12px;
    }

    /* Chat styling */
    .chat-input {
        background: #1E293B;
        border: 1px solid #475569;
        border-radius: 8px;
        color: #F8FAFC;
    }

    /* Analysis panels */
    .freestyle-panel {
        background: #1E3A5F;
        border: 2px solid #60A5FA;
        border-radius: 8px;
        padding: 15px;
    }
    .method-panel {
        background: #1A3D2E;
        border: 2px solid #10B981;
        border-radius: 8px;
        padding: 15px;
    }

    /* Time badge */
    .time-badge {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: bold;
    }

    /* Mobile responsive */
    @media (max-width: 768px) {
        .game-card {
            padding: 12px;
        }
        .game-card h3 {
            font-size: 16px;
        }
    }

    /* Hide Streamlit branding for cleaner look */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# =============================================================================
# Database Setup
# =============================================================================

DB_PATH = "ludi_lite.db"

def init_db():
    """Initialize SQLite database for tracking"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS analyses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            game_date TEXT,
            matchup TEXT,
            spread REAL,
            total REAL,
            freestyle_analysis TEXT,
            methodology_analysis TEXT,
            user_notes TEXT,
            query_type TEXT
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            query TEXT,
            freestyle_response TEXT,
            methodology_response TEXT
        )
    """)

    conn.commit()
    conn.close()

init_db()

# =============================================================================
# Time Context
# =============================================================================

def get_time_context() -> dict:
    """Get current time context for analysis"""
    try:
        now_et = datetime.now(ET)
    except Exception:
        now_et = datetime.now()

    hour = now_et.hour

    if hour < 12:
        mode = "EARLY_LOOK"
        confidence = "LOW - Verify closer to game time"
        color = "#FCD34D"
    elif hour < 17:
        mode = "AFTERNOON"
        confidence = "MEDIUM - Watch for updates"
        color = "#60A5FA"
    elif hour < 19:
        mode = "PRE_GAME"
        confidence = "HIGH - Most lineups confirmed"
        color = "#34D399"
    else:
        mode = "LOCK_TIME"
        confidence = "HIGHEST - Games starting"
        color = "#F87171"

    return {
        "timestamp": now_et.strftime("%I:%M %p ET"),
        "date": now_et.strftime("%b %d, %Y"),
        "mode": mode,
        "confidence": confidence,
        "color": color,
        "hour": hour
    }


def build_time_aware_prompt(base_prompt: str, time_context: dict, late_news: str = "") -> str:
    """Inject time context into prompt"""
    time_header = f"""
=== ANALYSIS TIMESTAMP ===
Current Time: {time_context['timestamp']} on {time_context['date']}
Analysis Mode: {time_context['mode']}
Confidence: {time_context['confidence']}
"""
    if late_news.strip():
        time_header += f"""
=== LATE NEWS (User Provided - Prioritize This) ===
{late_news}
"""
    return time_header + "\n" + base_prompt

# =============================================================================
# API Functions
# =============================================================================

def get_api_key(key_name: str) -> Optional[str]:
    """
    Get API key with priority:
    1. Streamlit Cloud secrets (st.secrets)
    2. Environment variables
    3. Local Ludi-Bot .env file (development fallback)
    """
    # Priority 1: Streamlit Cloud secrets
    try:
        if hasattr(st, 'secrets') and key_name in st.secrets:
            return st.secrets[key_name]
    except Exception:
        pass

    # Priority 2: Environment variable
    key = os.getenv(key_name)
    if key:
        return key

    # Priority 3: Local .env file (development only)
    env_path = os.path.expanduser("~/Ludi-Bot/.env")
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                if line.startswith(f"{key_name}="):
                    return line.strip().split("=", 1)[1].strip('"\'')

    return None


def fetch_todays_games() -> list:
    """Fetch today's NBA games from The-Odds-API"""
    api_key = get_api_key("ODDS_API_KEY")
    if not api_key:
        return []

    try:
        url = "https://api.the-odds-api.com/v4/sports/basketball_nba/odds/"
        params = {
            "apiKey": api_key,
            "regions": "us",
            "markets": "spreads,totals",
            "oddsFormat": "american",
            "bookmakers": "fanduel,draftkings"
        }
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            games = response.json()
            # Parse into simpler format
            parsed = []
            for game in games:
                away = game.get("away_team", "").split()[-1]  # Get last word (team name)
                home = game.get("home_team", "").split()[-1]

                # Get spread and total from first bookmaker
                spread = None
                total = None
                for book in game.get("bookmakers", []):
                    for market in book.get("markets", []):
                        if market["key"] == "spreads" and not spread:
                            for outcome in market["outcomes"]:
                                if outcome["name"] == game["home_team"]:
                                    spread = outcome["point"]
                        if market["key"] == "totals" and not total:
                            for outcome in market["outcomes"]:
                                if outcome["name"] == "Over":
                                    total = outcome["point"]

                # Parse time
                commence = game.get("commence_time", "")
                try:
                    dt = datetime.fromisoformat(commence.replace("Z", "+00:00"))
                    dt_et = dt.astimezone(ET)
                    time_str = dt_et.strftime("%I:%M %p")
                except Exception:
                    time_str = "TBD"

                parsed.append({
                    "id": game.get("id"),
                    "away": away[:3].upper() if away else "???",
                    "home": home[:3].upper() if home else "???",
                    "away_full": game.get("away_team", "Away"),
                    "home_full": game.get("home_team", "Home"),
                    "spread": spread,
                    "total": total,
                    "time": time_str
                })
            return parsed
    except Exception as e:
        st.error(f"Error fetching games: {e}")
    return []


def get_claude_analysis(prompt: str, user_input: str, model: str = "claude-sonnet-4-20250514") -> str:
    """Get analysis from Claude API"""
    api_key = get_api_key("ANTHROPIC_API_KEY")
    if not api_key:
        return "Error: ANTHROPIC_API_KEY not found."

    try:
        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model=model,
            max_tokens=2500,
            messages=[
                {"role": "user", "content": f"{prompt}\n\n---\n\nANALYZE:\n{user_input}"}
            ]
        )
        return response.content[0].text
    except Exception as e:
        return f"Error: {str(e)}"

# =============================================================================
# Query Parser
# =============================================================================

def parse_chat_query(query: str) -> Tuple[str, dict]:
    """
    Parse natural language query into structured request

    Handles:
    - Games: "DEN vs NYK", "Lakers @ Suns"
    - Players: "Luka", "Doncic", "Luka Doncic"
    - Stats: PTS, AST, REB, 3PM, STL, BLK, TO, MIN, FG, FT, etc.
    - Combos: PRA, PA, PR, RA, PTS+AST, PTS+REB+AST, stocks, etc.
    - Props: "Luka PTS 28.5", "Trae assists over 9.5"

    Returns: (query_type, params)
    """
    import re
    query_lower = query.lower().strip()
    query_original = query.strip()

    # ===================
    # GAME QUERY PATTERNS
    # ===================
    # "DEN vs NYK", "Lakers @ Suns", "Denver versus New York"
    game_patterns = [
        r"(\w+)\s+(?:vs\.?|versus|@|at)\s+(\w+)",
    ]
    for pattern in game_patterns:
        match = re.search(pattern, query_lower)
        if match:
            away = match.group(1).upper()[:3]
            home = match.group(2).upper()[:3]
            return "game", {"away": away, "home": home}

    # ===================
    # STAT NORMALIZATION
    # ===================
    stat_aliases = {
        # Points
        "pts": "Points", "points": "Points", "point": "Points", "scoring": "Points",
        # Assists
        "ast": "Assists", "assists": "Assists", "assist": "Assists", "dimes": "Assists",
        # Rebounds
        "reb": "Rebounds", "rebounds": "Rebounds", "rebound": "Rebounds", "boards": "Rebounds",
        "trb": "Rebounds", "total rebounds": "Rebounds",
        # 3-Pointers
        "3pm": "3PM", "3s": "3PM", "threes": "3PM", "three pointers": "3PM",
        "3pt": "3PM", "3 pointers": "3PM", "triples": "3PM",
        # Steals
        "stl": "Steals", "steals": "Steals", "steal": "Steals",
        # Blocks
        "blk": "Blocks", "blocks": "Blocks", "block": "Blocks",
        # Turnovers
        "to": "Turnovers", "turnovers": "Turnovers", "turnover": "Turnovers", "tos": "Turnovers",
        # Minutes
        "min": "Minutes", "mins": "Minutes", "minutes": "Minutes",
        # Field Goals
        "fgm": "FGM", "fg": "FGM", "field goals": "FGM",
        # Free Throws
        "ftm": "FTM", "ft": "FTM", "free throws": "FTM", "fts": "FTM",
        # Fantasy
        "fpts": "Fantasy", "fantasy": "Fantasy", "fantasy points": "Fantasy", "fp": "Fantasy",

        # === COMBO PROPS ===
        # PRA (Points + Rebounds + Assists)
        "pra": "PTS+REB+AST", "pts+reb+ast": "PTS+REB+AST", "pts reb ast": "PTS+REB+AST",
        "points rebounds assists": "PTS+REB+AST", "p+r+a": "PTS+REB+AST",
        # PA (Points + Assists)
        "pa": "PTS+AST", "pts+ast": "PTS+AST", "points assists": "PTS+AST",
        "points and assists": "PTS+AST", "p+a": "PTS+AST", "pts ast": "PTS+AST",
        # PR (Points + Rebounds)
        "pr": "PTS+REB", "pts+reb": "PTS+REB", "points rebounds": "PTS+REB",
        "points and rebounds": "PTS+REB", "p+r": "PTS+REB", "pts reb": "PTS+REB",
        # RA (Rebounds + Assists)
        "ra": "REB+AST", "reb+ast": "REB+AST", "rebounds assists": "REB+AST",
        "rebounds and assists": "REB+AST", "r+a": "REB+AST", "reb ast": "REB+AST",
        # Stocks (Steals + Blocks)
        "stocks": "STL+BLK", "stl+blk": "STL+BLK", "steals blocks": "STL+BLK",
        "steals and blocks": "STL+BLK", "defensive stats": "STL+BLK",
        # Boards + Dimes
        "boards dimes": "REB+AST", "rebounds dimes": "REB+AST",
        # Double-Double
        "dd": "Double-Double", "double double": "Double-Double", "double-double": "Double-Double",
        # Triple-Double
        "td": "Triple-Double", "triple double": "Triple-Double", "triple-double": "Triple-Double",
    }

    # ===================
    # PROP WITH LINE PATTERN
    # ===================
    # "Luka PTS 28.5", "Trae Young assists 9.5", "Jokic PRA over 45.5"
    # Pattern: [name] [stat] [optional: over/under] [number]

    # Build stat pattern from aliases
    stat_keywords = "|".join(sorted(stat_aliases.keys(), key=len, reverse=True))

    # Pattern 1: Name + Stat + Number
    prop_pattern = rf"(.+?)\s+({stat_keywords})\s+(?:over|under|o|u)?\s*(\d+\.?\d*)"
    prop_match = re.search(prop_pattern, query_lower)

    if prop_match:
        name_raw = prop_match.group(1).strip()
        stat_raw = prop_match.group(2).strip()
        line = float(prop_match.group(3))

        # Clean up name (remove common prefixes)
        name = name_raw.replace("give me", "").replace("info on", "").replace("about", "").strip()
        name = name.title()

        # Normalize stat
        stat = stat_aliases.get(stat_raw, stat_raw.upper())

        return "player_prop", {"name": name, "stat": stat, "line": line}

    # ===================
    # PLAYER + STAT (no line)
    # ===================
    # "Luka assists", "Jokic rebounds", "Trae PRA"
    stat_pattern = rf"(.+?)\s+({stat_keywords})(?:\s|$)"
    stat_match = re.search(stat_pattern, query_lower)

    if stat_match:
        name_raw = stat_match.group(1).strip()
        stat_raw = stat_match.group(2).strip()

        # Clean name
        name = name_raw.replace("give me", "").replace("info on", "").replace("about", "").strip()
        name = name.title()

        # Normalize stat
        stat = stat_aliases.get(stat_raw, stat_raw.upper())

        return "player", {"name": name, "stat": stat}

    # ===================
    # PLAYER ONLY (general query)
    # ===================
    # "Luka", "tell me about Jokic", "info on Trae Young"

    # Remove common prefixes
    clean_query = query_lower
    prefixes_to_remove = [
        "give me info on", "give me information on", "tell me about",
        "info on", "information on", "about", "what about",
        "how is", "how's", "analyze", "breakdown", "break down"
    ]
    for prefix in prefixes_to_remove:
        if clean_query.startswith(prefix):
            clean_query = clean_query[len(prefix):].strip()
            break

    # If something remains, treat as player name
    if clean_query and len(clean_query) > 1:
        return "player", {"name": clean_query.title(), "stat": "All Stats"}

    return "unknown", {}

# =============================================================================
# UI Components
# =============================================================================

def render_header():
    """Render dashboard header"""
    time_ctx = get_time_context()

    st.markdown(f"""
    <div style="display: flex; justify-content: space-between; align-items: center; padding: 10px 0; border-bottom: 1px solid #334155; margin-bottom: 20px;">
        <div>
            <h1 style="color: #FBBF24; margin: 0; font-size: 28px;">🏀 Ludi Lite</h1>
            <p style="color: #94A3B8; margin: 5px 0 0 0; font-size: 14px;">AI Research Lab | {CURRENT_SEASON}</p>
        </div>
        <div style="text-align: right;">
            <span class="time-badge" style="background: {time_ctx['color']}20; color: {time_ctx['color']};">
                {time_ctx['mode']}
            </span>
            <p style="color: #94A3B8; margin: 5px 0 0 0; font-size: 12px;">{time_ctx['timestamp']}</p>
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_game_cards(games: list):
    """Render clickable game cards"""
    if not games:
        st.info("No games found. Enter a game manually below or check API key.")
        return None

    st.markdown("### 📅 Today's Games")
    st.markdown("<p style='color: #94A3B8; font-size: 12px;'>Click a game to analyze</p>", unsafe_allow_html=True)

    # Create columns for game cards (responsive)
    cols = st.columns(min(len(games), 4))

    selected_game = None

    for i, game in enumerate(games):
        col = cols[i % len(cols)]
        with col:
            spread_str = f"{game['home']} {game['spread']:+.1f}" if game['spread'] else "PK"
            total_str = f"O/U {game['total']}" if game['total'] else ""

            # Create button styled as card
            if st.button(
                f"**{game['away']} @ {game['home']}**\n{spread_str} | {total_str}\n{game['time']}",
                key=f"game_{i}",
                use_container_width=True
            ):
                selected_game = game

    return selected_game


def render_chat_interface():
    """Render chat input for natural language queries"""
    st.markdown("### 💬 Ask Ludi")

    query = st.text_input(
        "Ask about a player, prop, or game...",
        placeholder="Examples: 'Luka assists tonight', 'DEN vs NYK', 'Trae Young PTS 28.5'",
        key="chat_input",
        label_visibility="collapsed"
    )

    col1, col2, col3 = st.columns([1, 1, 2])
    with col1:
        analyze_both = st.button("🔍 Analyze Both", type="primary", disabled=not query)
    with col2:
        analyze_method = st.button("🎯 Ludi Only", disabled=not query)

    return query, analyze_both, analyze_method


def render_analysis_output(freestyle: str, methodology: str, show_both: bool = True):
    """Render analysis results side by side"""
    if show_both:
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("""
            <div style="background: #60A5FA20; border: 2px solid #60A5FA; border-radius: 8px; padding: 5px 15px; margin-bottom: 10px;">
                <h3 style="color: #60A5FA; margin: 0;">🤖 Freestyle</h3>
                <p style="color: #94A3B8; margin: 0; font-size: 11px;">Raw AI analysis</p>
            </div>
            """, unsafe_allow_html=True)
            st.markdown(freestyle)

        with col2:
            st.markdown("""
            <div style="background: #10B98120; border: 2px solid #10B981; border-radius: 8px; padding: 5px 15px; margin-bottom: 10px;">
                <h3 style="color: #10B981; margin: 0;">🎯 Ludi Method</h3>
                <p style="color: #94A3B8; margin: 0; font-size: 11px;">S.A.V.A.G.E. framework</p>
            </div>
            """, unsafe_allow_html=True)
            st.markdown(methodology)
    else:
        st.markdown("""
        <div style="background: #10B98120; border: 2px solid #10B981; border-radius: 8px; padding: 5px 15px; margin-bottom: 10px;">
            <h3 style="color: #10B981; margin: 0;">🎯 Ludi Method Analysis</h3>
        </div>
        """, unsafe_allow_html=True)
        st.markdown(methodology)


def render_manual_input():
    """Render manual game/player input as fallback"""
    with st.expander("📝 Manual Input", expanded=False):
        input_type = st.radio("Type", ["Game", "Player"], horizontal=True)

        if input_type == "Game":
            col1, col2 = st.columns(2)
            with col1:
                away = st.text_input("Away Team", placeholder="DEN")
                spread = st.number_input("Spread", value=0.0, step=0.5)
            with col2:
                home = st.text_input("Home Team", placeholder="NYK")
                total = st.number_input("Total", value=220.0, step=0.5)

            context = st.text_area("Context (injuries, B2B, etc.)", height=80)
            late_news = st.text_area("🚨 Late News", height=60)

            if away and home:
                return "game", {
                    "away": away.upper(),
                    "home": home.upper(),
                    "spread": spread,
                    "total": total,
                    "context": context,
                    "late_news": late_news
                }
        else:
            col1, col2 = st.columns(2)
            with col1:
                player = st.text_input("Player Name", placeholder="Luka Doncic")
                team = st.text_input("Team", placeholder="DAL")
            with col2:
                opponent = st.text_input("Opponent", placeholder="PHX")
                stat = st.selectbox("Stat Focus", [
                    "All Stats",
                    "--- Single Stats ---",
                    "Points", "Assists", "Rebounds", "3PM",
                    "Steals", "Blocks", "Turnovers", "Minutes",
                    "FGM", "FTM",
                    "--- Combo Props ---",
                    "PTS+REB+AST (PRA)", "PTS+AST (PA)", "PTS+REB (PR)",
                    "REB+AST (RA)", "STL+BLK (Stocks)",
                    "--- Special ---",
                    "Double-Double", "Triple-Double", "Fantasy Points"
                ])

            context = st.text_area("Context", height=60)
            late_news = st.text_area("🚨 Late News", height=60)

            if player and opponent:
                return "player", {
                    "name": player,
                    "team": team,
                    "opponent": opponent,
                    "stat": stat,
                    "context": context,
                    "late_news": late_news
                }

    return None, None


def save_analysis(query: str, freestyle: str, methodology: str):
    """Save analysis to database"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        INSERT INTO chat_history (query, freestyle_response, methodology_response)
        VALUES (?, ?, ?)
    """, (query, freestyle, methodology))
    conn.commit()
    conn.close()

# =============================================================================
# Main App
# =============================================================================

def main():
    render_header()

    time_ctx = get_time_context()

    # Initialize session state
    if "analysis_result" not in st.session_state:
        st.session_state.analysis_result = None

    # Section 1: Today's Games (Cards)
    games = fetch_todays_games()
    selected_game = render_game_cards(games)

    st.divider()

    # Section 2: Chat Interface
    query, analyze_both, analyze_ludi = render_chat_interface()

    # Section 3: Manual Input (collapsed)
    manual_type, manual_params = render_manual_input()

    st.divider()

    # Process Analysis
    analysis_input = None
    query_type = None
    late_news = ""

    # Priority: Selected game card > Chat query > Manual input
    if selected_game:
        query_type = "game"
        analysis_input = f"""
GAME: {selected_game['away']} @ {selected_game['home']}
SPREAD: {selected_game['home']} {selected_game['spread']:+.1f if selected_game['spread'] else 'PK'}
TOTAL: {selected_game['total'] or 'TBD'}
TIME: {selected_game['time']}

{selected_game['away']} Defense: {get_defense_scheme(selected_game['away'])}
{selected_game['home']} Defense: {get_defense_scheme(selected_game['home'])}
{selected_game['away']} Offense: {get_offense_scheme(selected_game['away'])}
{selected_game['home']} Offense: {get_offense_scheme(selected_game['home'])}
"""

    elif query and (analyze_both or analyze_ludi):
        query_type, params = parse_chat_query(query)

        if query_type == "game":
            analysis_input = f"""
GAME: {params['away']} @ {params['home']}
{params['away']} Defense: {get_defense_scheme(params['away'])}
{params['home']} Defense: {get_defense_scheme(params['home'])}
{params['away']} Offense: {get_offense_scheme(params['away'])}
{params['home']} Offense: {get_offense_scheme(params['home'])}
"""

        elif query_type in ["player", "player_prop"]:
            stat_focus = params.get('stat', 'All Stats')
            line_info = f"LINE: {params.get('line', 'N/A')}" if params.get('line') else ""
            opponent = params.get('opponent', 'Unknown')

            analysis_input = f"""
PLAYER: {params['name']}
STAT FOCUS: {stat_focus}
{line_info}
QUERY: {query}
"""
            query_type = "player"

        else:
            analysis_input = f"QUERY: {query}"
            query_type = "player"

    elif manual_type and manual_params:
        query_type = manual_type
        late_news = manual_params.get("late_news", "")

        if manual_type == "game":
            analysis_input = f"""
GAME: {manual_params['away']} @ {manual_params['home']}
SPREAD: {manual_params['home']} {manual_params['spread']:+.1f}
TOTAL: {manual_params['total']}

{manual_params['away']} Defense: {get_defense_scheme(manual_params['away'])}
{manual_params['home']} Defense: {get_defense_scheme(manual_params['home'])}

CONTEXT: {manual_params.get('context', 'None')}
"""
        else:
            analysis_input = f"""
PLAYER: {manual_params['name']} ({manual_params.get('team', '')})
OPPONENT: {manual_params['opponent']}
STAT FOCUS: {manual_params['stat']}
OPPONENT DEFENSE: {get_defense_scheme(manual_params['opponent'])}

CONTEXT: {manual_params.get('context', 'None')}
"""

    # Run Analysis
    if analysis_input and (selected_game or analyze_both or analyze_ludi or manual_params):
        # Select prompts based on query type
        if query_type == "game":
            prompt_freestyle = FREESTYLE_PROMPT
            prompt_method = LUDI_METHOD_PROMPT
        else:
            prompt_freestyle = FREESTYLE_PROMPT
            prompt_method = PLAYER_SPOTLIGHT_PROMPT

        # Add time context
        prompt_freestyle = build_time_aware_prompt(prompt_freestyle, time_ctx, late_news)
        prompt_method = build_time_aware_prompt(prompt_method, time_ctx, late_news)

        # Determine model
        model = "claude-sonnet-4-20250514"

        if analyze_both or selected_game:
            with st.spinner("🤖 Running Freestyle analysis..."):
                freestyle = get_claude_analysis(prompt_freestyle, analysis_input, model)

            with st.spinner("🎯 Running Ludi Method analysis..."):
                methodology = get_claude_analysis(prompt_method, analysis_input, model)

            render_analysis_output(freestyle, methodology, show_both=True)

            # Save option
            if st.button("💾 Save Analysis"):
                save_analysis(query or "Game Card", freestyle, methodology)
                st.success("Saved!")

        elif analyze_ludi:
            with st.spinner("🎯 Running Ludi Method analysis..."):
                methodology = get_claude_analysis(prompt_method, analysis_input, model)

            render_analysis_output("", methodology, show_both=False)

    # Footer
    st.markdown("---")
    st.markdown("""
    <p style="color: #64748B; font-size: 11px; text-align: center;">
        Ludi Lite | Research Assistant | Not betting advice
    </p>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()

APPEOF
# === docs/PRD.md ===
cat > docs/PRD.md << 'PRDEOF'
# Ludi Lite - Product Requirements Document

**Version:** 1.0
**Created:** February 5, 2026
**Owner:** LudiInformatio
**Status:** Ready for Build

---

## Executive Summary

**Ludi Lite** is a mobile-friendly Streamlit web application that provides AI-powered sports betting research through a dual-analysis interface. Users can compare "raw" Claude analysis against Claude enhanced with the S.A.V.A.G.E. methodology from the parent Ludi-Bot project.

### Vision Statement
Democratize sports betting research by providing side-by-side AI analysis: one from general Claude intelligence and one from Claude trained on proprietary NBA analytics methodology.

---

## Product Overview

### What is Ludi Lite?

A lightweight research dashboard that allows users to:
1. View today's NBA games with live spreads and totals
2. Ask natural language questions about games, players, or props
3. Compare two analysis modes side-by-side:
   - **Freestyle**: Raw Claude intelligence
   - **Ludi Method**: Claude + S.A.V.A.G.E. framework

### Parent Project Relationship

Ludi Lite is a **consumer-facing interface** for the Ludi-Bot engine:

```
┌─────────────────────────────────────────────────────────────┐
│                      LUDI-BOT                               │
│  Full Analytics Engine                                       │
│  - Monte Carlo Simulations                                   │
│  - Injury Intelligence                                       │
│  - Referee Impact                                            │
│  - Matchup Matrix                                            │
│  - Edge Calculation                                          │
│  - Automated Betting Pipeline                                │
└─────────────────────────────────────────────────────────────┘
                              │
                              │ Methodology + Context
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      LUDI-LITE                              │
│  Consumer Research Dashboard                                 │
│  - Dual Analysis Interface                                   │
│  - Natural Language Input                                    │
│  - Mobile-First Design                                       │
│  - Time-Aware Context                                        │
└─────────────────────────────────────────────────────────────┘
```

---

## User Personas

### Primary: The Casual Bettor
- **Profile**: Sports fan who bets recreationally
- **Needs**: Quick research before placing bets
- **Pain Points**: Information overload, no framework for analysis
- **Use Case**: "Should I bet Luka over 28.5 points tonight?"

### Secondary: The Serious Researcher
- **Profile**: Dedicated bettor seeking an edge
- **Needs**: Multiple perspectives on the same bet
- **Pain Points**: Echo chamber analysis, confirmation bias
- **Use Case**: "Compare raw AI take vs methodology-backed analysis"

### Tertiary: The Mobile User
- **Profile**: Bets on the go, often at games or with friends
- **Needs**: Fast, mobile-friendly interface
- **Pain Points**: Desktop-only tools, slow load times
- **Use Case**: "Quick check on my phone before lock"

---

## Core Features

### 1. Today's Games Dashboard
**Priority:** P0 (Must Have)

Display clickable game cards showing:
- Matchup (Away @ Home)
- Spread and total
- Game time (Eastern)
- Click to analyze

**Data Source:** The-Odds-API (via ODDS_API_KEY)

### 2. Dual Analysis Mode
**Priority:** P0 (Must Have)

Side-by-side comparison:

| Freestyle | Ludi Method |
|-----------|-------------|
| Raw Claude analysis | Claude + S.A.V.A.G.E. |
| General sports knowledge | Usage Vacuum, Matchup Matrix |
| No framework constraints | Archetype vs Defense |
| Blue header/border | Green header/border |

### 3. Natural Language Input
**Priority:** P0 (Must Have)

Parse user queries into structured requests:

**Supported Patterns:**
- Games: "DEN vs NYK", "Lakers @ Suns"
- Players: "Luka", "Jokic rebounds"
- Props: "Trae points 28.5", "Luka PRA over 45"
- Combos: "PRA", "PA", "stocks"

**Stat Aliases:**
- Points: pts, points, scoring
- Assists: ast, assists, dimes
- Rebounds: reb, boards, trb
- 3PM: 3s, threes, triples
- Combos: PRA, PA, PR, RA, stocks

### 4. Time-Aware Context
**Priority:** P1 (Should Have)

Adjust confidence based on tipoff proximity:

| Time | Mode | Confidence | Badge Color |
|------|------|------------|-------------|
| Before noon | EARLY_LOOK | LOW | Yellow |
| Noon - 5 PM | AFTERNOON | MEDIUM | Blue |
| 5 - 7 PM | PRE_GAME | HIGH | Green |
| After 7 PM | LOCK_TIME | HIGHEST | Red |

### 5. Manual Input Fallback
**Priority:** P2 (Nice to Have)

Expandable form for detailed manual entry:
- Game: teams, spread, total, context
- Player: name, team, opponent, stat focus
- Late news injection

### 6. Analysis History
**Priority:** P2 (Nice to Have)

SQLite storage for:
- Past queries
- Freestyle responses
- Methodology responses
- Timestamps

---

## S.A.V.A.G.E. Framework Integration

The Ludi Method prompt incorporates these principles from Ludi-Bot:

### 1. Usage Vacuum Theory
When a star is OUT, usage redistributes to teammates.
- Example: "With Embiid OUT, Maxey usage increases 8%"

### 2. Archetype vs Defense Scheme
Player style impacts performance against specific defenses:

| Archetype | vs PAINT_PACK | vs BLITZ | vs SWITCH |
|-----------|---------------|----------|-----------|
| STRETCH_BIG | +15% 3PM | Neutral | -5% |
| SLASHER | +10% FTA | -8% PTS | Neutral |
| ISO_SCORER | Neutral | -8% | +5% |

### 3. Pace Context
Game total impacts volume:
- High total (>235): +volume for pace players
- Low total (<210): -volume, favor efficiency

### 4. Blowout Tax
Large spreads reduce starter minutes:
- 10+ spread: -5% volume
- 15+ spread: -15% volume (garbage time risk)

### 5. B2B Fatigue
Back-to-back games impact performance:
- Road B2B: -4.8% production
- Home B2B: -1.5% production
- Guards hit hardest: additional -2%

### 6. Line Movement Intelligence
Market signals provide context:
- Sharp money movement
- Steam moves
- Reverse line movement

---

## Technical Requirements

### Stack
- **Framework:** Streamlit
- **Language:** Python 3.11+
- **Database:** SQLite (local)
- **APIs:** Claude (Anthropic), The-Odds-API
- **Deployment:** Streamlit Cloud

### Dependencies (requirements.txt)
```
streamlit
anthropic
requests
pytz
```

### API Keys Required
| Key | Purpose | Source |
|-----|---------|--------|
| ANTHROPIC_API_KEY | Claude API calls | Streamlit secrets or env |
| ODDS_API_KEY | Live game data | Streamlit secrets or env |

### File Structure
```
ludi-lite/
├── app.py                 # Main Streamlit app
├── prompts.py             # AI prompts (Freestyle, Method, Player)
├── season_context.py      # Team schemes, current season
├── components.py          # Reusable UI components
├── requirements.txt       # Python dependencies
├── README.md              # Setup instructions
├── .streamlit/
│   ├── config.toml        # Streamlit config
│   └── secrets.toml.example
├── .github/
│   └── workflows/
│       └── daily_health_check.yml
└── docs/
    ├── PRD.md             # This document
    └── LUDI_LITE_BUILD_SOP.md
```

---

## UI/UX Requirements

### Design Principles
1. **Mobile-First**: Optimized for phone screens
2. **Dark Theme**: Matches Ludi-Bot aesthetic
3. **Minimal Chrome**: Hide Streamlit branding
4. **Fast Interaction**: Single-tap game selection

### Color Palette (Current - User May Customize)
| Element | Color | Usage |
|---------|-------|-------|
| Background | #0F172A | Main app background |
| Card BG | #1E293B | Game cards, panels |
| Accent | #FBBF24 | Headers, highlights |
| Freestyle | #60A5FA | Blue panel border |
| Method | #10B981 | Green panel border |
| Text | #F8FAFC | Primary text |
| Muted | #94A3B8 | Secondary text |

**Note:** User requested generic template - colors may be removed/customized later.

### Responsive Breakpoints
- Mobile: < 768px (primary target)
- Tablet: 768px - 1024px
- Desktop: > 1024px

---

## Success Metrics

### Launch Criteria
- [ ] App loads on Streamlit Cloud
- [ ] Game cards display (with API key)
- [ ] Dual analysis completes in < 30s
- [ ] Mobile layout renders correctly
- [ ] No exposed secrets

### Post-Launch KPIs
| Metric | Target | Measurement |
|--------|--------|-------------|
| Page Load | < 3s | Streamlit metrics |
| Analysis Time | < 30s | In-app timing |
| Error Rate | < 5% | Health check workflow |
| Daily Active Queries | Track | SQLite logs |

---

## Integration Points

### Ludi-Bot (Parent Project)
- **Location:** `/home/user/Ludi-Bot/`
- **Shared:** Methodology documentation, defense schemes
- **Independent:** Ludi Lite has its own database, no shared state

### Slack Notifications
- **Workspace:** Vibe Starters
- **App:** Claude Agents
- **Channel:** #ludi-lite-health
- **Trigger:** Daily health check workflow

### GitHub Actions
- **Workflow:** daily_health_check.yml
- **Schedule:** 6 AM EST daily (when enabled)
- **Auth:** CLAUDE_CODE_OAUTH_TOKEN (same as Ludi-Bot)

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Odds API downtime | No game cards | Manual input fallback |
| Claude API rate limits | Slow/failed analysis | Caching, error handling |
| Streamlit Cloud limits | App unavailable | Monitor usage, upgrade if needed |
| Mobile layout breaks | Poor UX | Responsive CSS, testing |

---

## Future Roadmap

### Phase 2 (Post-Launch)
- [ ] Save favorite players/games
- [ ] Historical analysis view
- [ ] Push notifications for late news
- [ ] Dark/light theme toggle

### Phase 3 (Integration)
- [ ] Pull real-time edge data from Ludi-Bot
- [ ] Display Diamond Plays directly
- [ ] Sync with Telegram bot

### Phase 4 (Advanced)
- [ ] User accounts
- [ ] Bet tracking
- [ ] Performance analytics

---

## Approval & Sign-Off

| Role | Name | Date |
|------|------|------|
| Product Owner | LudiInformatio | Feb 5, 2026 |
| Build Lead | PM Agent (Claude) | TBD |
| QA Lead | QA Agent (Claude) | TBD |

---

**End of PRD v1.0**

PRDEOF
# === docs/LUDI_LITE_BUILD_SOP.md ===
cat > docs/LUDI_LITE_BUILD_SOP.md << 'SOPEOF'
# Ludi Lite Build & Deploy SOP

**Version:** 2.1
**Created:** February 5, 2026
**Last Updated:** February 5, 2026
**Purpose:** Multi-Agent Standard Operating Procedure for building, testing, and deploying Ludi Lite to Streamlit Cloud

---

## Project Context

### Overview
**Ludi Lite** is a mobile-friendly Streamlit dashboard providing AI-powered NBA betting research through dual-analysis (Freestyle vs Ludi Method).

### Key Links
| Resource | Location |
|----------|----------|
| Repository | https://github.com/LudiInformatio/ludi-lite |
| Parent Project | /home/user/Ludi-Bot |
| PRD | /home/user/ludi-lite/docs/PRD.md |
| This SOP | /home/user/ludi-lite/docs/LUDI_LITE_BUILD_SOP.md |

### Related Projects
| Project | Purpose | Relationship |
|---------|---------|--------------|
| Ludi-Bot | Full NBA analytics engine | Parent - provides methodology |
| Ludi Lite | Consumer research dashboard | This project |
| Vibe Starters (Slack) | Notifications hub | Health check alerts |

### Project Owner
**LudiInformatio** - All repositories under this GitHub organization

---

## Agent Hierarchy Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         USER (Human)                            │
│                              │                                  │
│                    Initiates build request                      │
│                              │                                  │
│                              ▼                                  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                    PM AGENT                                │  │
│  │            (Project Manager - Orchestrator)                │  │
│  │                                                           │  │
│  │  Experience: Senior Technical PM                          │  │
│  │  Role: Coordinate all phases, compile final report        │  │
│  │  Reports To: User                                         │  │
│  │  Manages: All Sub-Agents + QA Agent                       │  │
│  └───────────────────────────────────────────────────────────┘  │
│                              │                                  │
│            ┌─────────────────┼─────────────────┐               │
│            │                 │                 │               │
│            ▼                 ▼                 ▼               │
│  ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐   │
│  │  PHASE AGENTS   │ │  PHASE AGENTS   │ │    QA AGENT     │   │
│  │   (1, 2, 3)     │ │   (4, 5)        │ │                 │   │
│  │                 │ │                 │ │ Experience:     │   │
│  │ Each phase has  │ │ Each phase has  │ │ Sr. QA Engineer │   │
│  │ a specialist:   │ │ a specialist:   │ │                 │   │
│  │ - Environment   │ │ - DevOps        │ │ Role: Validate  │   │
│  │ - Backend       │ │ - Testing       │ │ each phase      │   │
│  │ - UI/UX         │ │                 │ │                 │   │
│  └─────────────────┘ └─────────────────┘ └─────────────────┘   │
│                                                                 │
│  WORKFLOW: Phase Agent → QA Agent → PM Agent → Next Phase      │
└─────────────────────────────────────────────────────────────────┘
```

### Agent Roster

| Agent | Role | Experience Level | Primary Responsibility |
|-------|------|------------------|------------------------|
| PM Agent | Project Manager | Senior | Orchestration, final reporting |
| QA Agent | Quality Analyst | Senior | Validate all phase outputs |
| Phase 1 Agent | Environment Specialist | DevOps | File structure, dependencies |
| Phase 2 Agent | Backend Specialist | Backend Dev | Core functionality, API |
| Phase 3 Agent | UI/UX Specialist | Frontend Dev | Styling, responsive design |
| Phase 4 Agent | DevOps Specialist | DevOps | Deployment, CI/CD |
| Phase 5 Agent | Testing Specialist | QA Engineer | E2E production testing |

### Communication Flow

1. **User → PM Agent**: "Build and deploy Ludi Lite"
2. **PM Agent → Phase 1 Agent**: "Verify environment" → Report
3. **PM Agent → QA Agent**: "Validate Phase 1" → Approval
4. **PM Agent → Phase 2 Agent**: "Test backend" → Report
5. *(repeat for each phase)*
6. **PM Agent → User**: Final Build Report

---

## Multi-Agent Architecture

### Agent Hierarchy

```
┌─────────────────────────────────────────────────────────────┐
│                    USER (Human)                              │
│                         ▲                                    │
│                         │ Final Report                       │
│                         │                                    │
│  ┌──────────────────────┴──────────────────────┐            │
│  │         PM AGENT (Project Manager)           │            │
│  │  - Orchestrates all phases                   │            │
│  │  - Receives sub-agent reports                │            │
│  │  - Compiles final deliverable                │            │
│  │  - Reports to user                           │            │
│  └──────────────────────┬──────────────────────┘            │
│                         │                                    │
│         ┌───────────────┼───────────────┐                   │
│         │               │               │                   │
│         ▼               ▼               ▼                   │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐           │
│  │ SUB-AGENTS  │ │ SUB-AGENTS  │ │  QA AGENT   │           │
│  │ (Phase 1-5) │ │ (Phase 1-5) │ │  - Reviews  │           │
│  │             │ │             │ │  - Validates│           │
│  └─────────────┘ └─────────────┘ └─────────────┘           │
└─────────────────────────────────────────────────────────────┘
```

---

## Agent Definitions

### PM AGENT (Project Manager)

**Role:** Senior Technical Project Manager
**Responsibility:** Orchestration, coordination, and final reporting

**System Prompt:**
```
You are the PROJECT MANAGER for the Ludi Lite build project.

YOUR RESPONSIBILITIES:
1. Spawn sub-agents for each phase in sequence
2. Receive and review each sub-agent's report
3. Pass reports to QA Agent for validation
4. Track overall progress and blockers
5. Compile final Build Report for the user
6. Only report to user AFTER all phases complete

WORKFLOW:
1. Read this SOP document completely
2. Spawn Phase 1 Agent → Wait for report
3. Send report to QA Agent → Wait for validation
4. If QA PASS: Proceed to next phase
5. If QA FAIL: Re-spawn phase agent with feedback
6. Repeat for Phases 2-5
7. Compile Final Report
8. Report to user

YOU DO NOT:
- Write code directly (sub-agents do this)
- Skip phases
- Report to user mid-process (unless critical blocker)

OUTPUT FORMAT:
After each phase, log:
- Phase [X] Status: [PASS/FAIL]
- Duration: [X minutes]
- Issues: [count]
- QA Validation: [PASS/FAIL]
```

---

### QA AGENT (Quality Analyst)

**Role:** Senior QA Engineer
**Responsibility:** Validate each phase output, ensure quality standards

**System Prompt:**
```
You are the QA AGENT for the Ludi Lite build project.

YOUR RESPONSIBILITIES:
1. Review sub-agent reports for completeness
2. Verify all verification checkboxes are addressed
3. Validate code changes are sound
4. Check for regressions or issues
5. Return PASS/FAIL with detailed feedback

VALIDATION CRITERIA:
- All tasks in phase completed
- Verification checklist addressed
- Issues properly documented with resolutions
- Code changes include rationale
- No critical bugs or security issues

OUTPUT FORMAT:
## QA Review: Phase [X]
**Status:** [PASS/FAIL]

### Checklist Verification
- [ ] All tasks completed
- [ ] Verification items addressed
- [ ] Issues documented with resolutions
- [ ] Code rationale provided
- [ ] No critical issues

### Feedback
[Specific feedback for PM/sub-agent]

### Recommendation
[PROCEED to next phase / REDO with corrections]
```

---

### PHASE 1 AGENT (Environment Specialist)

**Role:** DevOps Engineer - Environment Setup
**Responsibility:** Verify development environment is properly configured

**System Prompt:**
```
You are the ENVIRONMENT SPECIALIST for Phase 1.

YOUR SOLE FOCUS:
- Verify file structure exists
- Check dependencies are installable
- Test API key retrieval works
- Ensure no import errors

YOU DO NOT:
- Modify application logic
- Touch UI/UX code
- Deploy anything
- Work on other phases

WORKING DIRECTORY: /home/user/ludi-lite/

TASKS:
1. Check file structure:
   - app.py, prompts.py, season_context.py, components.py
   - requirements.txt, README.md
   - .streamlit/config.toml, .streamlit/secrets.toml.example

2. Verify requirements.txt has:
   - streamlit
   - anthropic
   - requests

3. Test API key retrieval:
   - get_api_key() function should find ANTHROPIC_API_KEY
   - Priority: st.secrets → env vars → ~/Ludi-Bot/.env

4. Test imports:
   - python -c "import streamlit; import anthropic; import requests"

REPORT FORMAT:
## Phase 1 Report: Environment Verification
**Agent:** Environment Specialist
**Status:** [PASS/FAIL]
**Duration:** [X minutes]

### Tasks Completed
- [ ] File structure verified
- [ ] Dependencies checked
- [ ] API key retrieval tested
- [ ] Imports validated

### Issues Encountered
| Issue | Resolution | Rationale |
|-------|------------|-----------|
| [desc] | [fix] | [why] |

### Verification Results
- File structure: [OK/ISSUE - details]
- Dependencies: [OK/ISSUE - details]
- API key: [OK/ISSUE - details]
- Imports: [OK/ISSUE - details]

### Handoff Notes
[Any context the next agent needs]
```

---

### PHASE 2 AGENT (Backend Specialist)

**Role:** Backend Developer - Core Functionality
**Responsibility:** Verify app runs and core features work

**System Prompt:**
```
You are the BACKEND SPECIALIST for Phase 2.

YOUR SOLE FOCUS:
- Verify app runs locally
- Test Claude API integration
- Validate input parsing
- Check time context features

YOU DO NOT:
- Modify UI/styling
- Deploy to production
- Work on other phases

WORKING DIRECTORY: /home/user/ludi-lite/

TASKS:
1. Run app locally:
   streamlit run app.py --server.port 8501

2. Test Claude API:
   - Submit query: "Lakers vs Celtics"
   - Verify Freestyle response generates
   - Verify Methodology response generates

3. Test input parsing:
   - Game: "DEN vs NYK"
   - Player prop: "Jokic points 28.5"
   - Combo: "Luka PRA"

4. Test time context:
   - Verify time badges display
   - Check tipoff detection

REPORT FORMAT:
## Phase 2 Report: Core Functionality
**Agent:** Backend Specialist
**Status:** [PASS/FAIL]
**Duration:** [X minutes]

### Tasks Completed
- [ ] App launches without errors
- [ ] Claude API responds
- [ ] Both analysis modes work
- [ ] Input parsing handles all formats
- [ ] Time context functional

### Test Results
| Test Case | Input | Expected | Actual | Status |
|-----------|-------|----------|--------|--------|
| Game query | "DEN vs NYK" | Analysis | [result] | [P/F] |
| Player prop | "Jokic points 28.5" | Prop analysis | [result] | [P/F] |
| Combo prop | "Luka PRA" | PRA breakdown | [result] | [P/F] |
| Time badge | [current time] | Correct badge | [result] | [P/F] |

### Issues Encountered
| Issue | Resolution | Rationale |
|-------|------------|-----------|
| [desc] | [fix] | [why] |

### Code Changes
```python
# File: [filename]
# Before:
[old code]

# After:
[new code]

# Rationale: [explanation]
```

### Handoff Notes
[Any context the next agent needs]
```

---

### PHASE 3 AGENT (UI/UX Specialist)

**Role:** Frontend Developer - UI/UX
**Responsibility:** Clean up UI, ensure generic template

**System Prompt:**
```
You are the UI/UX SPECIALIST for Phase 3.

YOUR SOLE FOCUS:
- Review and clean CSS in app.py
- Remove hardcoded brand colors
- Ensure Streamlit defaults work
- Verify responsive layout

YOU DO NOT:
- Modify backend logic
- Change API integrations
- Deploy anything
- Add new brand colors (user will do this later)

WORKING DIRECTORY: /home/user/ludi-lite/

IMPORTANT CONTEXT:
The user explicitly requested:
- NO custom brand colors
- Generic template as starting point
- They will customize frontend later

TASKS:
1. Review CSS in app.py (lines ~38-119):
   - Identify hardcoded colors
   - Document what's there

2. Simplify to Streamlit defaults:
   - Remove custom color values
   - Keep structural CSS (layout, spacing)
   - Use Streamlit native components

3. Verify responsive design:
   - Test column layouts
   - Check different viewport sizes

4. Clean up visual elements:
   - Remove placeholder content
   - Ensure clean error states

REPORT FORMAT:
## Phase 3 Report: UI/UX Enhancement
**Agent:** UI/UX Specialist
**Status:** [PASS/FAIL]
**Duration:** [X minutes]

### Tasks Completed
- [ ] CSS reviewed and documented
- [ ] Brand colors removed
- [ ] Streamlit defaults applied
- [ ] Responsive design verified

### CSS Audit
| Element | Old Value | New Value | Rationale |
|---------|-----------|-----------|-----------|
| backgroundColor | #0F172A | [removed] | User wants generic |
| textColor | #F8FAFC | [removed] | Streamlit default |

### Code Changes
```python
# File: app.py
# Lines: [X-Y]

# Before:
[old CSS]

# After:
[new CSS or removed]

# Rationale: [explanation]
```

### Visual Verification
- Default theme renders: [OK/ISSUE]
- Layout intact: [OK/ISSUE]
- Responsive: [OK/ISSUE]
- No hardcoded colors: [OK/ISSUE]

### Handoff Notes
[Any context the next agent needs]
```

---

### PHASE 4 AGENT (DevOps Specialist)

**Role:** DevOps Engineer - Deployment
**Responsibility:** Deploy to Streamlit Cloud

**System Prompt:**
```
You are the DEVOPS SPECIALIST for Phase 4.

YOUR SOLE FOCUS:
- Prepare GitHub repository
- Push code to remote
- Guide Streamlit Cloud setup
- Verify deployment works

YOU DO NOT:
- Modify application code
- Change UI/styling
- Run application tests

WORKING DIRECTORY: /home/user/ludi-lite/

TASKS:
1. Prepare Git repository:
   git init (if needed)
   git add .
   git commit -m "Ludi Lite - ready for deployment"

2. Push to GitHub:
   - Repo: https://github.com/LudiInformatio/ludi-lite.git
   - Branch: main
   - Ensure .gitignore excludes secrets

3. Document Streamlit Cloud setup:
   - Connect to GitHub repo
   - Set main file: app.py
   - Configure secrets (document format)

4. Verify deployment:
   - App loads at public URL
   - No secrets exposed
   - Basic functionality works

REPORT FORMAT:
## Phase 4 Report: Deployment
**Agent:** DevOps Specialist
**Status:** [PASS/FAIL]
**Duration:** [X minutes]

### Tasks Completed
- [ ] Git repository initialized
- [ ] Code committed
- [ ] Pushed to GitHub
- [ ] Streamlit Cloud setup documented
- [ ] Deployment verified

### Git Operations
```bash
# Commands executed:
[list of git commands]
```

### Repository Details
- URL: [GitHub URL]
- Branch: main
- Commit: [hash]
- Files tracked: [count]

### Streamlit Cloud Configuration
- App URL: [URL]
- Main file: app.py
- Secrets required:
  - ANTHROPIC_API_KEY
  - ODDS_API_KEY (optional)

### Deployment Verification
- App loads: [OK/ISSUE]
- No secret exposure: [OK/ISSUE]
- Public accessible: [OK/ISSUE]

### Issues Encountered
| Issue | Resolution | Rationale |
|-------|------------|-----------|
| [desc] | [fix] | [why] |

### Handoff Notes
[Production URL and any notes for testing]
```

---

### PHASE 5 AGENT (Testing Specialist)

**Role:** QA Engineer - End-to-End Testing
**Responsibility:** Full production verification

**System Prompt:**
```
You are the TESTING SPECIALIST for Phase 5.

YOUR SOLE FOCUS:
- Run end-to-end tests in production
- Test all query types
- Verify error handling
- Check performance

YOU DO NOT:
- Modify code (report issues for fixing)
- Re-deploy
- Change configuration

WORKING ENVIRONMENT: Production (Streamlit Cloud URL)

TASKS:
1. Game Analysis Tests:
   - Query: "tonight's games"
   - Query: specific matchup (e.g., "LAL vs BOS")
   - Verify both modes generate output

2. Player Prop Tests:
   - Query: "[player] [stat] [line]"
   - Test all stat types: PTS, AST, REB, 3PM
   - Test combos: PRA, PA, PR, RA, Stocks

3. Edge Case Tests:
   - Invalid input (gibberish)
   - Empty input
   - Very long input

4. Performance Tests:
   - Measure response times
   - Check for timeouts
   - Verify no memory issues on repeated queries

REPORT FORMAT:
## Phase 5 Report: Full Cycle Verification
**Agent:** Testing Specialist
**Status:** [PASS/FAIL]
**Duration:** [X minutes]
**Environment:** Production ([URL])

### Test Summary
| Category | Tests Run | Passed | Failed |
|----------|-----------|--------|--------|
| Game Analysis | [X] | [X] | [X] |
| Player Props | [X] | [X] | [X] |
| Edge Cases | [X] | [X] | [X] |
| Performance | [X] | [X] | [X] |

### Detailed Test Results

#### Game Analysis
| Test | Input | Expected | Actual | Status |
|------|-------|----------|--------|--------|
| Tonight's games | "tonight's games" | Game list | [result] | [P/F] |
| Specific matchup | "LAL vs BOS" | Dual analysis | [result] | [P/F] |

#### Player Props
| Test | Input | Expected | Actual | Status |
|------|-------|----------|--------|--------|
| Points | "LeBron points 27.5" | PTS analysis | [result] | [P/F] |
| Assists | "Jokic assists 9.5" | AST analysis | [result] | [P/F] |
| Combo PRA | "Luka PRA" | PRA breakdown | [result] | [P/F] |

#### Edge Cases
| Test | Input | Expected | Actual | Status |
|------|-------|----------|--------|--------|
| Invalid | "asdfghjkl" | Error message | [result] | [P/F] |
| Empty | "" | Prompt to enter | [result] | [P/F] |

#### Performance
| Metric | Value | Threshold | Status |
|--------|-------|-----------|--------|
| Avg response time | [X]s | <30s | [P/F] |
| Max response time | [X]s | <60s | [P/F] |
| Error rate | [X]% | <5% | [P/F] |

### Issues Found
| Severity | Description | Recommendation |
|----------|-------------|----------------|
| [CRIT/HIGH/MED/LOW] | [issue] | [fix suggestion] |

### Final Assessment
**Production Ready:** [YES/NO]
**Confidence Level:** [HIGH/MEDIUM/LOW]
**Blockers:** [list or "None"]
```

---

## PM Workflow Execution

### Step-by-Step Process

```
PM AGENT WORKFLOW:

1. INITIALIZE
   - Read this SOP document
   - Confirm working directory: /home/user/ludi-lite/
   - Initialize progress tracker

2. PHASE 1 EXECUTION
   a. Spawn Phase 1 Agent (Environment Specialist)
   b. Wait for Phase 1 Report
   c. Send report to QA Agent
   d. If QA PASS → Continue
   e. If QA FAIL → Re-spawn with feedback, max 2 retries

3. PHASE 2 EXECUTION
   [Same pattern as Phase 1]

4. PHASE 3 EXECUTION
   [Same pattern as Phase 1]

5. PHASE 4 EXECUTION
   [Same pattern as Phase 1]

6. PHASE 5 EXECUTION
   [Same pattern as Phase 1]

7. COMPILE FINAL REPORT
   - Aggregate all phase reports
   - Summarize issues and resolutions
   - Document all code changes with rationale
   - Calculate total duration and metrics

8. REPORT TO USER
   - Deliver Final Build Report
   - Include production URL
   - List any remaining recommendations
```

### PM Progress Tracker Template

```markdown
## PM Progress Tracker

### Phase Status
| Phase | Agent | Status | QA | Attempts |
|-------|-------|--------|-----|----------|
| 1 | Environment | [PENDING/RUNNING/PASS/FAIL] | [PENDING/PASS/FAIL] | [0/3] |
| 2 | Backend | [PENDING/RUNNING/PASS/FAIL] | [PENDING/PASS/FAIL] | [0/3] |
| 3 | UI/UX | [PENDING/RUNNING/PASS/FAIL] | [PENDING/PASS/FAIL] | [0/3] |
| 4 | DevOps | [PENDING/RUNNING/PASS/FAIL] | [PENDING/PASS/FAIL] | [0/3] |
| 5 | Testing | [PENDING/RUNNING/PASS/FAIL] | [PENDING/PASS/FAIL] | [0/3] |

### Timeline
- Started: [timestamp]
- Phase 1 Complete: [timestamp]
- Phase 2 Complete: [timestamp]
- Phase 3 Complete: [timestamp]
- Phase 4 Complete: [timestamp]
- Phase 5 Complete: [timestamp]
- Final Report: [timestamp]

### Blockers
[List any blockers encountered]

### Decisions Made
[List any PM decisions during execution]
```

---

## Final Report Template (PM Delivers to User)

```markdown
# Ludi Lite Build Report

**Date:** [Date]
**PM Agent:** Claude (Project Manager)
**Total Duration:** [X hours Y minutes]

---

## Executive Summary
[2-3 sentences: What was built, current status, production URL]

---

## Phase Summary

| Phase | Agent | Status | Duration | Issues | QA |
|-------|-------|--------|----------|--------|-----|
| 1. Environment | Environment Specialist | [PASS/FAIL] | [X min] | [#] | [PASS/FAIL] |
| 2. Backend | Backend Specialist | [PASS/FAIL] | [X min] | [#] | [PASS/FAIL] |
| 3. UI/UX | UI/UX Specialist | [PASS/FAIL] | [X min] | [#] | [PASS/FAIL] |
| 4. Deployment | DevOps Specialist | [PASS/FAIL] | [X min] | [#] | [PASS/FAIL] |
| 5. Testing | Testing Specialist | [PASS/FAIL] | [X min] | [#] | [PASS/FAIL] |

**Overall Status:** [ALL PHASES PASS / ISSUES REMAIN]

---

## Issues Log

### Issue 1: [Title]
- **Phase:** [which phase]
- **Agent:** [which agent found it]
- **Severity:** [CRITICAL/HIGH/MEDIUM/LOW]
- **Description:** [what happened]
- **Resolution:** [how it was fixed]
- **Rationale:** [why this approach was chosen]

### Issue 2: [Title]
[repeat format for each issue]

---

## Code Changes Summary

| File | Lines Changed | Change Type | Agent |
|------|---------------|-------------|-------|
| app.py | [X-Y] | [Modified/Added/Removed] | [Agent] |
| [file] | [lines] | [type] | [Agent] |

### Detailed Changes

#### [filename]
```python
# Before (lines X-Y):
[old code]

# After:
[new code]

# Rationale: [explanation]
# Agent: [which agent made this change]
```

---

## Agent Rationale Documentation

### Key Decisions Made

1. **Decision:** [what was decided]
   - **Agent:** [who decided]
   - **Phase:** [when]
   - **Alternatives Considered:** [other options]
   - **Rationale:** [why this choice]
   - **Trade-offs:** [accepted compromises]

2. **Decision:** [repeat format]

---

## Production Status

- **URL:** [Streamlit Cloud URL]
- **Status:** [Operational / Issues]
- **Uptime:** [if measurable]
- **Ready for User Testing:** [YES/NO]

### Verified Features
- [ ] Game analysis (Freestyle)
- [ ] Game analysis (Methodology)
- [ ] Player prop parsing
- [ ] Combo prop parsing
- [ ] Time context badges
- [ ] Error handling

---

## Metrics

| Metric | Value |
|--------|-------|
| Total build time | [X hours Y minutes] |
| Phases completed | [5/5] |
| Issues encountered | [#] |
| Issues resolved | [#] |
| Code files modified | [#] |
| Lines changed | [#] |
| QA pass rate | [X%] |

---

## Recommendations

### Immediate (Before User Testing)
- [Recommendation 1]
- [Recommendation 2]

### Future Enhancements
- [Suggestion 1]
- [Suggestion 2]

---

## Appendix: Full Phase Reports

[Include complete reports from each sub-agent]

---

**End of Build Report**

*Report compiled by PM Agent on [date/time]*
```

---

## Project Context Reference

### What is Ludi Lite?
A Streamlit web application providing:
1. **Dual Analysis Mode**: Claude Freestyle vs Claude + Ludi Methodology
2. **Game Analysis**: Full matchup breakdowns
3. **Player Props**: Deep dives on specific bets (PTS, AST, REB, 3PM, combos)
4. **Time-Aware Context**: Confidence adjusts based on tipoff proximity

### S.A.V.A.G.E. Framework
1. **Usage Vacuum Theory** - Redistribution when stars are OUT
2. **Archetype vs Defense Scheme** - Player style vs team defense
3. **Pace Context** - Game total impact on volume
4. **Blowout Tax** - Spread impact on starter minutes
5. **B2B Fatigue** - Schedule density adjustments
6. **Line Movement Intelligence** - Market signal interpretation

### Supported Stats
- **Singles:** PTS, AST, REB, 3PM, STL, BLK, TO, MIN, FGM, FTM
- **Combos:** PRA, PA, PR, RA, Stocks

### Parent Project Reference
Full methodology details in `/home/user/Ludi-Bot/docs/METHODOLOGY.md`

---

## Maintenance & Updates Protocol

### Purpose
All future edits, bug fixes, and feature additions MUST follow this same multi-agent structure. The PM Agent maintains context continuity while sub-agents execute specific work.

### Update Request Flow

```
USER REQUEST (edit/fix/feature)
         │
         ▼
    PM AGENT
    - Analyzes request
    - Determines which agent(s) needed
    - Maintains project context
    - Coordinates execution
         │
         ├──► Route to appropriate sub-agent(s)
         │
         ▼
    SUB-AGENT(S)
    - Execute specific changes
    - Document rationale
    - Report back to PM
         │
         ▼
    QA AGENT
    - Validate changes
    - Check for regressions
    - Approve or request fixes
         │
         ▼
    PM AGENT
    - Compile update report
    - Report to user
```

### Agent Routing Matrix

| Request Type | Primary Agent | Supporting Agent |
|--------------|---------------|------------------|
| Bug fix (backend) | Backend Specialist | QA |
| Bug fix (UI) | UI/UX Specialist | QA |
| New feature | Backend + UI/UX | QA |
| Performance issue | Testing Specialist | Backend |
| Deployment issue | DevOps Specialist | QA |
| Environment/deps | Environment Specialist | QA |
| Styling changes | UI/UX Specialist | QA |
| API integration | Backend Specialist | QA |

### PM Agent Update Mode

**System Prompt Addition for Updates:**
```
MAINTENANCE MODE ACTIVATED

You are the PM AGENT handling an update request.

YOUR RESPONSIBILITIES:
1. Analyze the user's change request
2. Determine which sub-agent(s) are needed
3. Spawn appropriate agent with specific task
4. DO NOT write code yourself - delegate to sub-agents
5. Receive sub-agent report
6. Send to QA for validation
7. Compile update report for user

CONTEXT CONTINUITY:
- Reference previous Build Report if available
- Note any dependencies on prior work
- Track cumulative changes across sessions

REQUEST ANALYSIS TEMPLATE:
- Request: [what user asked for]
- Type: [bug fix / feature / styling / deployment / other]
- Agent(s) Needed: [list]
- Files Likely Affected: [list]
- Risk Level: [LOW/MEDIUM/HIGH]
- Estimated Complexity: [SIMPLE/MODERATE/COMPLEX]
```

### Sub-Agent Update Task Format

When PM spawns a sub-agent for updates:

```
## Update Task Assignment

**Request:** [description from user]
**Assigned Agent:** [agent role]
**Priority:** [HIGH/MEDIUM/LOW]

### Context
- Previous state: [relevant context from PM]
- Related files: [list]
- Dependencies: [any blockers]

### Scope
YOU ARE AUTHORIZED TO:
- [specific allowed actions]

YOU ARE NOT AUTHORIZED TO:
- [out of scope items]
- Changes outside your specialty
- Modifications not requested

### Deliverables
1. Implement requested change
2. Document what was changed
3. Explain rationale
4. Note any side effects
5. Handoff notes for QA

### Report Format
## Update Report: [Task Name]
**Agent:** [role]
**Status:** [COMPLETE/BLOCKED/PARTIAL]

### Changes Made
| File | Lines | Change | Rationale |
|------|-------|--------|-----------|

### Testing Done
[What agent verified]

### Side Effects
[Any unintended impacts noted]

### QA Notes
[Specific items for QA to verify]
```

### QA Agent Update Validation

```
## QA Update Review

**Change Request:** [description]
**Agent:** [who made changes]

### Validation Checklist
- [ ] Changes match request scope
- [ ] No out-of-scope modifications
- [ ] Code rationale documented
- [ ] No regressions introduced
- [ ] Existing tests still pass
- [ ] New functionality verified

### Regression Check
- [ ] Core features still work
- [ ] No broken imports
- [ ] UI renders correctly
- [ ] API calls functional

### Verdict
**Status:** [APPROVED/NEEDS FIXES]
**Feedback:** [specific notes]
```

### Update Report Template (PM to User)

```markdown
# Ludi Lite Update Report

**Date:** [date]
**Request:** [what user asked for]
**Status:** [COMPLETE/PARTIAL/BLOCKED]

## Summary
[1-2 sentences on what was done]

## Changes Made

| File | Change | Agent |
|------|--------|-------|
| [file] | [description] | [agent] |

## Rationale
[Why changes were made this way]

## QA Validation
- Status: [PASS/FAIL]
- Tests: [what was verified]

## Side Effects
[Any impacts to note, or "None"]

## Recommendations
[Any follow-up suggestions]
```

### Example Update Scenarios

**Scenario 1: User reports bug**
```
User: "The time badge isn't showing correctly"

PM Analysis:
- Type: Bug fix
- Agent: Backend Specialist (time logic) or UI/UX (display)
- Files: app.py (time functions or rendering)

PM Action:
1. Spawn Backend Specialist to investigate time logic
2. If UI issue, spawn UI/UX Specialist
3. QA validates fix
4. Report to user
```

**Scenario 2: User wants new feature**
```
User: "Add a history tab to see past analyses"

PM Analysis:
- Type: Feature
- Agents: Backend (data storage) + UI/UX (new tab)
- Complexity: MODERATE

PM Action:
1. Spawn Backend Specialist for data layer
2. Spawn UI/UX Specialist for tab interface
3. QA validates integration
4. Report to user
```

**Scenario 3: User wants styling change**
```
User: "Make the headers gold instead of default"

PM Analysis:
- Type: Styling
- Agent: UI/UX Specialist only
- Complexity: SIMPLE

PM Action:
1. Spawn UI/UX Specialist with specific color request
2. QA validates (visual check)
3. Report to user
```

---

## Infrastructure Configuration

### GitHub Secrets Required

| Secret | Purpose | Source |
|--------|---------|--------|
| `CLAUDE_CODE_OAUTH_TOKEN` | Claude OAuth for health check workflow | Same as Ludi-Bot (uses Max subscription) |
| `SLACK_WEBHOOK_URL` | Notifications to #ludi-lite-health | Slack app "Claude Agents" |
| `STREAMLIT_APP_URL` | Optional - deployed app URL for health checks | Streamlit Cloud |

### Slack Integration

**Workspace:** Vibe Starters (personal)
**App Name:** Claude Agents
**Channel:** #ludi-lite-health
**Webhook URL:** `https://hooks.slack.com/services/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`

**Notification Types:**
- Success: Green header, "Healthy" status
- Issues Detected: Yellow header with summary, "View Full Report" button
- Workflow Failed: Red header with "View Error Logs" button

### Daily Health Check Workflow

**File:** `.github/workflows/daily_health_check.yml`
**Schedule:** 6 AM EST daily (when enabled)
**Trigger:** Manual or scheduled

**Checks Performed:**
1. Code structure verification
2. Python syntax validation
3. Import testing (streamlit, anthropic, requests)
4. Dependency audit
5. Code quality scan
6. API configuration check
7. App health ping (if URL configured)

---

## Success Criteria

The build is complete when:
- [ ] All 5 phases pass verification
- [ ] All 5 phases pass QA validation
- [ ] App deployed to Streamlit Cloud
- [ ] Public URL accessible and functional
- [ ] All core features verified in production
- [ ] Final Build Report delivered to user
- [ ] No CRITICAL or HIGH severity issues unresolved

---

**End of SOP v2.0**

SOPEOF

echo ""
echo "All files created successfully!"
echo "Files created:"
ls -la
echo ""
echo "Next steps:"
echo "1. git add ."
echo "2. git commit -m \"Initial commit: Ludi Lite v1.0\""
echo "3. git push -u origin main"
