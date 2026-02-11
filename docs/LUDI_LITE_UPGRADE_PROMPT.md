# Ludi Lite Upgrade Implementation Prompt

**Copy this entire prompt and send to your local Claude Code agent.**

---

## PROMPT START

You are the PM Agent for implementing Ludi Lite upgrades. Your job is to orchestrate sub-agents to complete each task, verify their work, and ensure all changes are committed and pushed.

**Repository:** https://github.com/LudiInformatio/Ludi-Lite.git
**Branch:** main (or create feature branch if preferred)

---

## TASK OVERVIEW

Implement the following upgrades to Ludi Lite:

### Phase 1: Fix Prompt Leakage (HIGH Priority)
System instructions like "ROSTER VERIFICATION" and "BEFORE listing any player" are appearing in AI output. Add post-processing to clean responses.

### Phase 2: UX Improvements (MEDIUM Priority)
- Games should be sorted chronologically (by tipoff time)
- Add "TODAY" and "TOMORROW" section headers

### Phase 3: Future Session Documentation
Document planned future enhancements for reference.

### Phase 4: API Caching (CRITICAL Priority)
Multiple APIs are being called WITHOUT caching, burning through credits rapidly:
- **The-Odds-API**: 0% cache coverage (costs 1-10 credits per call)
- **Perplexity API**: 0% cache coverage
- **Claude API**: 0% cache coverage

---

## SUB-AGENT ASSIGNMENTS

### Sub-Agent 1: Response Cleaner
**Task:** Add `clean_ai_response()` function to strip leaked instructions

**File:** `ui_components.py`

**Implementation:**
```python
import re

def clean_ai_response(response: str) -> str:
    """
    Remove leaked system instructions from AI output.
    These patterns come from ROSTER_RULES in prompts.py that sometimes
    echo back in Claude's response.
    """
    if not response:
        return response

    leak_patterns = [
        # Full ROSTER_RULES block
        r"=== CRITICAL: ROSTER VERIFICATION ===.*?(?=\n\n|\n##|\n\*\*[A-Z]|\Z)",
        # Individual instruction lines
        r"\*\*BEFORE listing any player.*?(?=\n\n|\n-|\Z)",
        r"- If a player is listed as OUT.*?\n",
        r"- NEVER put injured/suspended players.*?\n",
        r"- Only include players who are ACTIVE.*?\n",
        r"- If unsure, say \"status unclear\".*?\n",
        # Internal markers
        r"\[INTERNAL.*?\].*?\n",
        r"\[DO NOT OUTPUT\].*?\n",
        # Common instruction echoes
        r"(?i)always name.*?top.*?players.*?\n",
        r"(?i)check the injury report above.*?\n",
        r"(?i)use ONLY the rosters/injuries from.*?\n",
    ]

    cleaned = response
    for pattern in leak_patterns:
        cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE | re.DOTALL)

    # Clean up resulting extra whitespace
    cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
    cleaned = re.sub(r'^\s*\n', '', cleaned)  # Leading blank lines

    return cleaned.strip()
```

**Integration:** Update `render_analysis_output()` to call this function on both `freestyle` and `methodology` before rendering.

**Report back:** Confirm function added and integrated. Show the updated `render_analysis_output()` function signature.

---

### Sub-Agent 2: Game Sorting
**Task:** Sort games chronologically and preserve timestamp

**File:** `api_clients.py`
**Function:** `fetch_todays_games()` (around line 243)

**Changes Required:**

1. **Add `commence_time` to parsed dict** (around line 301):
```python
parsed.append({
    "id": game.get("id"),
    "commence_time": commence,  # ADD THIS LINE - raw ISO timestamp for sorting
    "away": away,
    "home": home,
    "away_full": away_full or "Away",
    "home_full": home_full or "Home",
    "spread": spread,
    "total": total,
    "home_ml": home_ml,
    "away_ml": away_ml,
    "time": time_str
})
```

2. **Sort before return** (add after the for loop, before `return parsed`):
```python
# Sort games chronologically (earliest tipoff first)
parsed.sort(key=lambda g: g.get('commence_time', '9999-12-31T23:59:59Z'))
return parsed
```

**Report back:** Confirm both changes made. Show the updated code block.

---

### Sub-Agent 3: Date Headers
**Task:** Add TODAY/TOMORROW section headers to game cards

**File:** `ui_components.py`
**Function:** `render_game_cards()` (around line 31)

**Full Replacement Implementation:**
```python
from datetime import datetime, timedelta
import pytz

ET = pytz.timezone('America/New_York')


def render_game_cards(games: list):
    """
    Render clickable game cards grouped by date.
    Shows TODAY and TOMORROW sections with games sorted chronologically.
    """
    if not games:
        st.info("📭 No games scheduled. Check back later!")
        return None

    # Group games by date
    today = datetime.now(ET).date()
    tomorrow = today + timedelta(days=1)

    today_games = []
    tomorrow_games = []
    other_games = []

    for game in games:
        try:
            commence = game.get('commence_time', '')
            if commence:
                game_dt = datetime.fromisoformat(
                    commence.replace('Z', '+00:00')
                ).astimezone(ET).date()

                if game_dt == today:
                    today_games.append(game)
                elif game_dt == tomorrow:
                    tomorrow_games.append(game)
                else:
                    other_games.append(game)
            else:
                other_games.append(game)
        except Exception:
            other_games.append(game)

    selected_game = None

    # Render TODAY section
    if today_games:
        st.markdown("#### 🏀 TODAY")
        selected = _render_game_section(today_games, "today")
        if selected:
            selected_game = selected

    # Render TOMORROW section
    if tomorrow_games:
        st.markdown("#### 📆 TOMORROW")
        selected = _render_game_section(tomorrow_games, "tomorrow")
        if selected:
            selected_game = selected

    # Render OTHER section (future games beyond tomorrow)
    if other_games and not today_games and not tomorrow_games:
        st.markdown("#### 📅 UPCOMING")
        selected = _render_game_section(other_games, "other")
        if selected:
            selected_game = selected

    return selected_game


def _render_game_section(games: list, prefix: str):
    """
    Render a section of game cards in a responsive grid.
    Returns the selected game if user clicks one.
    """
    # Responsive columns: max 4 on desktop, wraps on mobile
    num_cols = min(len(games), 4)
    cols = st.columns(num_cols)
    selected = None

    for i, game in enumerate(games):
        col = cols[i % num_cols]
        with col:
            # Format spread
            spread = game.get('spread')
            if spread is not None:
                try:
                    spread_str = f"{game['home']} {float(spread):+.1f}"
                except (ValueError, TypeError):
                    spread_str = "PK"
            else:
                spread_str = "PK"

            # Format total
            total = game.get('total')
            total_str = f"O/U {total}" if total else ""

            # Create button with game info
            button_text = f"**{game['away']} @ {game['home']}**\n{spread_str} | {total_str}\n🕐 {game.get('time', 'TBD')}"

            if st.button(
                button_text,
                key=f"game_{prefix}_{i}_{game.get('id', i)}",
                use_container_width=True
            ):
                selected = game

    return selected
```

**Note:** Make sure to add the `import` statements at the top of the file if not already present.

**Report back:** Confirm function replaced. Confirm imports added.

---

### Sub-Agent 4: Documentation
**Task:** Create future enhancements documentation

**File:** Create new file `docs/FUTURE_ENHANCEMENTS.md`

**Content:**
```markdown
# Ludi Lite - Future Enhancements

**Last Updated:** February 9, 2026
**Status:** Documented for future sessions

---

## Planned Features (Not Yet Implemented)

These features were identified during competitive research and user testing.
They are documented here for future implementation when priorities allow.

---

### UI/UX Enhancements

| Feature | Description | Inspiration | Priority |
|---------|-------------|-------------|----------|
| **Accordion Cards** | Only one game expanded at a time, others collapse | LandYourBets | MEDIUM |
| **Auto-Run on Expand** | Trigger analysis automatically when user clicks a game | Sharp Hunter | MEDIUM |
| **Hit Rate Dots** | Visual ●●●○○ indicator for L5 performance | LandYourBets | LOW |
| **Line vs Proj Display** | Show +/- differential with color coding (green/red) | LandYourBets | MEDIUM |
| **BOOST Tags** | Badges like "MATCHUP PTS", "MATCHUP AST" for edges | LandYourBets | MEDIUM |

---

### Data Display Features

| Feature | Description | Data Source | Priority |
|---------|-------------|-------------|----------|
| **L15 Games Table** | Last 15 games with DATE, OPP, MIN, USG, FGA, PTS, REB, AST, +/- | Tank01 Box Scores | MEDIUM |
| **Usage Trends** | Recent Min vs Season Min with Diff | player_game_logs | LOW |
| **Injury Impact Panel** | Expandable cards showing who's OUT and beneficiaries | Tank01 + S.A.V.A.G.E. | MEDIUM |
| **INTEL Section** | Soft news like "Coach wants him to shoot more" | Perplexity/RotoWire | LOW |
| **Team Projections Table** | Full roster with MIN, PTS, REB, AST projections | Module C Oracle | HIGH |

---

### Backend/Model Enhancements

| Feature | Description | Implementation | Priority |
|---------|-------------|----------------|----------|
| **Module D AI Upgrade** | Use Perplexity for injury nuance detection | Enhance season_context.py | HIGH |
| **Post-Sim Sanity Check** | AI reviews projections for obvious errors | Add validation layer | MEDIUM |
| **Confidence Scoring** | Signal strength display (Strong/Medium/Speculative) | Edge calculation | LOW |
| **Historical Tracking** | Log picks and results over time | SQLite expansion | MEDIUM |

---

### Competitor Research Sources

- **LandYourBets/Swishland** - Data-first approach with projections tables
- **Sharp Hunter** - Chat-first AI interface with suggested prompts
- **Showstone.io** - AI sports analysis
- **Foxtail Sports** - AI betting assistant

---

## Implementation Notes

1. **Accordion cards** require Streamlit session state management
2. **L15 games table** needs Tank01 historical box score iteration
3. **BOOST tags** map directly to S.A.V.A.G.E. archetype vs scheme logic
4. **Team projections** would require Module C Oracle integration

---

## API Strategy & Fallbacks

### Current APIs
| API | Tier | Usage | Monthly Limit |
|-----|------|-------|---------------|
| The-Odds-API | PAID | Game lines, player props | 20K credits |
| Tank01 | PAID | Rosters, injuries, box scores | 1K/day |
| Perplexity | PAID | Real-time search/context | Unlimited |
| Claude API | PAID | AI analysis | Token-based |

### Future Fallback: Ball Don't Lie API
**Status:** Not yet implemented
**Tier:** FREE
**Limit:** 60 requests/minute
**Use Cases:**
- Player stats (season averages, recent games)
- Team stats
- Game schedules
- Reduce dependency on paid APIs

**Documentation:** https://docs.balldontlie.io/
**Implementation Priority:** HIGH (All-Star break project)

---

## Current 2025-26 Season Context

When implementing any features, remember:
- **LAC roster**: Kawhi Leonard, James Harden, Norman Powell, Ivica Zubac (NOT Paul George)
- **Recent trades**: Track NBA trade deadline (Feb 6, 2026) impacts
- Tank01 API is source of truth for current rosters
```

**Report back:** Confirm file created with full content.

---

### Sub-Agent 5: Verification & Commit
**Task:** Verify all changes work, then commit and push

**Verification Steps:**

1. **Syntax Check:**
```bash
python -m py_compile ui_components.py
python -m py_compile api_clients.py
```

2. **Import Check:**
```bash
python -c "from ui_components import clean_ai_response, render_game_cards; print('OK')"
python -c "from api_clients import fetch_todays_games; print('OK')"
```

3. **Function Test:**
```bash
python -c "
from ui_components import clean_ai_response
test = '=== CRITICAL: ROSTER VERIFICATION ===\nTest\n\n**BEFORE listing any player, check injury.**\n\nActual content here.'
result = clean_ai_response(test)
assert 'ROSTER VERIFICATION' not in result
assert 'BEFORE listing' not in result
assert 'Actual content' in result
print('clean_ai_response: PASS')
"
```

**Commit and Push:**
```bash
git add -A
git commit -m "feat: Fix prompt leakage + add chronological sorting + date headers

Phase 1: Add clean_ai_response() to strip leaked system instructions
Phase 2.1: Sort games by commence_time (earliest first)
Phase 2.2: Add TODAY/TOMORROW section headers
Phase 3: Document future enhancements

Fixes:
- ROSTER_RULES no longer appears in AI output
- Games sorted by tipoff time, not alphabetically
- Clear date grouping for multi-day slates

https://claude.ai/code"

git push origin main
```

**Report back:**
- Confirm all syntax checks pass
- Confirm all import checks pass
- Confirm function test passes
- Confirm commit hash
- Confirm push successful

---

### Sub-Agent 6: API Caching (CRITICAL)
**Task:** Add Streamlit caching to ALL uncached API calls to prevent credit burn

**Context:**
- Current cache coverage: 40% (only Tank01 is cached)
- The-Odds-API: 0% cached (costs 1-10 credits per call)
- Perplexity: 0% cached
- Claude API: 0% cached
- Every page refresh/button click = new API calls = wasted credits

---

#### File 1: `api_clients.py`

**Add cache to `fetch_todays_games()` (around line 243):**
```python
@st.cache_data(ttl=300, show_spinner=False)  # 5 minute cache
def fetch_todays_games() -> list:
    """
    Fetch today's NBA games with spreads and totals.
    Cached for 5 minutes to prevent credit burn.
    """
    # ... existing code unchanged
```

**Add cache to `fetch_player_props()` (around line 62):**
```python
@st.cache_data(ttl=300, show_spinner=False)  # 5 minute cache
def fetch_player_props(game_id: str) -> dict:
    """
    Fetch player props for a specific game.
    Cached for 5 minutes - costs 10 credits per uncached call!
    """
    # ... existing code unchanged
```

**Add cache to `get_claude_analysis()` (around line 156):**
```python
import hashlib

def _hash_prompt(prompt: str) -> str:
    """Create deterministic hash for prompt caching."""
    return hashlib.md5(prompt.encode()).hexdigest()[:16]

@st.cache_data(ttl=1800, show_spinner=False)  # 30 minute cache
def get_claude_analysis(
    system_prompt: str,
    user_prompt: str,
    _prompt_hash: str = None  # Underscore prefix = not part of cache key
) -> str:
    """
    Get analysis from Claude API.
    Cached for 30 minutes with prompt hash for identical queries.
    """
    # ... existing code unchanged
```

**Update the call site for Claude** (where `get_claude_analysis` is called):
```python
# Before calling get_claude_analysis, generate hash
prompt_hash = _hash_prompt(system_prompt + user_prompt)
result = get_claude_analysis(system_prompt, user_prompt, _prompt_hash=prompt_hash)
```

---

#### File 2: `perplexity_client.py`

**Add cache to `search_game_context()` (around line 15):**
```python
import streamlit as st

@st.cache_data(ttl=1800, show_spinner=False)  # 30 minute cache
def search_game_context(
    home_team: str,
    away_team: str,
    recency_filter: str = "day"
) -> str:
    """
    Search for game context via Perplexity.
    Cached for 30 minutes - same game context rarely changes.
    """
    # ... existing code unchanged
```

**Add cache to `search_player_context()` (around line 45):**
```python
@st.cache_data(ttl=1800, show_spinner=False)  # 30 minute cache
def search_player_context(
    player_name: str,
    team: str,
    recency_filter: str = "day"
) -> str:
    """
    Search for player-specific context via Perplexity.
    Cached for 30 minutes.
    """
    # ... existing code unchanged
```

**Add cache to `search_late_news()` (around line 75):**
```python
@st.cache_data(ttl=300, show_spinner=False)  # 5 minute cache (shorter for late news)
def search_late_news(team: str) -> str:
    """
    Search for late-breaking news close to tipoff.
    Cached for 5 minutes only - needs to stay fresh.
    """
    # ... existing code unchanged
```

---

#### File 3: `injury_verification.py`

**Add cache to `get_official_nba_injuries()` (if implemented):**
```python
@st.cache_data(ttl=900, show_spinner=False)  # 15 minute cache
def get_official_nba_injuries(game_date: str = None) -> list:
    """
    Fetch official NBA injury report.
    Cached for 15 minutes to align with NBA reporting window.
    """
    # ... existing code unchanged
```

---

#### Verification Steps:

1. **Confirm imports exist:**
```python
# At top of api_clients.py
import streamlit as st
import hashlib

# At top of perplexity_client.py
import streamlit as st
```

2. **Test caching works:**
```python
# In Python REPL or test script
import streamlit as st

# Mock streamlit cache for testing outside Streamlit
if not hasattr(st, 'cache_data'):
    st.cache_data = lambda **kwargs: lambda f: f

# Import and verify decorators applied
from api_clients import fetch_todays_games, fetch_player_props
print(hasattr(fetch_todays_games, '__wrapped__'))  # Should be True with cache
```

3. **Log cache hits (optional debugging):**
```python
# Add to any cached function for debugging
import logging
logger = logging.getLogger(__name__)

@st.cache_data(ttl=300)
def fetch_todays_games() -> list:
    logger.info("CACHE MISS: fetch_todays_games called")
    # ... rest of function
```

---

#### Cache TTL Strategy:

| Function | TTL | Rationale |
|----------|-----|-----------|
| `fetch_todays_games()` | 300s (5 min) | Game schedules rarely change intraday |
| `fetch_player_props()` | 300s (5 min) | Props refresh frequently but not every second |
| `get_claude_analysis()` | 1800s (30 min) | Same prompt = same analysis |
| `search_game_context()` | 1800s (30 min) | Game narrative changes slowly |
| `search_player_context()` | 1800s (30 min) | Player context changes slowly |
| `search_late_news()` | 300s (5 min) | Late news needs freshness |
| `get_official_nba_injuries()` | 900s (15 min) | Aligns with NBA 15-min reporting rule |

---

#### Expected Credit Savings:

**Before (no caching):**
- Page load: 1 credit
- Click game: 10 credits
- 10 clicks in session: 101 credits

**After (with caching):**
- Page load: 1 credit (first only, then cached)
- Click game: 10 credits (first only per game)
- 10 clicks same game: 10 credits total (90% savings)
- Session savings: ~80-90% credit reduction

**Report back:**
- Confirm all 7 functions have `@st.cache_data` decorators
- Confirm imports added to each file
- Confirm TTL values match strategy table
- Confirm no syntax errors

---

## PM AGENT ORCHESTRATION

Execute sub-agents in this order:

1. **Clone/pull latest** from Ludi-Lite repo
2. **Sub-Agent 6** (API Caching) → **FIRST - prevents credit burn during testing**
3. **Sub-Agent 1** (Response Cleaner) → Wait for report
4. **Sub-Agent 2** (Game Sorting) → Wait for report
5. **Sub-Agent 3** (Date Headers) → Wait for report
6. **Sub-Agent 4** (Documentation) → Wait for report
7. **Sub-Agent 5** (Verification & Commit) → Wait for report

After all sub-agents report success, provide a final summary:

```
## IMPLEMENTATION COMPLETE

### Changes Made:

**API Caching (CRITICAL):**
- [ ] @st.cache_data added to fetch_todays_games() - TTL 300s
- [ ] @st.cache_data added to fetch_player_props() - TTL 300s
- [ ] @st.cache_data added to get_claude_analysis() - TTL 1800s
- [ ] @st.cache_data added to search_game_context() - TTL 1800s
- [ ] @st.cache_data added to search_player_context() - TTL 1800s
- [ ] @st.cache_data added to search_late_news() - TTL 300s

**Bug Fixes:**
- [ ] clean_ai_response() added to ui_components.py
- [ ] render_analysis_output() updated to use cleaner
- [ ] commence_time added to game parsing
- [ ] Games sorted chronologically

**UX Improvements:**
- [ ] TODAY/TOMORROW headers added

**Documentation:**
- [ ] FUTURE_ENHANCEMENTS.md created

### Commit: [hash]
### Push: SUCCESS/FAILED

### Verification Results:
- Syntax: PASS/FAIL
- Imports: PASS/FAIL
- Function Test: PASS/FAIL
- Cache Decorators: PASS/FAIL

### Expected Impact:
- API Credit Savings: ~80-90% reduction
- No more Telegram quota alerts
```

---

## IMPORTANT NOTES

1. **Do NOT modify prompts.py** - Keep ROSTER_RULES there, just clean output
2. **Preserve existing functionality** - Don't break Perplexity integration, props display, etc.
3. **Test before commit** - All verification steps must pass
4. **Use correct 2025-26 context** - No PG13 on Clippers, Luka on Lakers, etc.
5. **API Caching is CRITICAL** - Do Sub-Agent 6 FIRST to prevent credit burn during testing
6. **Ball Don't Lie API** - Future fallback option (free tier, 60 req/min) - document in FUTURE_ENHANCEMENTS.md

---

## PROMPT END
