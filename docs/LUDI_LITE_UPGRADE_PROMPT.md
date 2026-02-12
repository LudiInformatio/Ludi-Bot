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
git commit -m "feat: Add API caching + fix prompt leakage + UX improvements

CRITICAL: Add @st.cache_data to prevent API credit burn
- app.py: Cache fetch_todays_games (1 credit/call)
- app.py: Cache fetch_player_props (10 credits/call!)
- app.py: Cache get_claude_analysis (cost savings)
- perplexity_client.py: Cache all 3 search functions

Bug Fixes:
- clean_ai_response() strips leaked ROSTER_RULES
- Games sorted by commence_time (chronological)
- TODAY/TOMORROW section headers added

Expected savings: 80-90% API credit reduction

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

**CREDIT BURN BREAKDOWN:**
| Action | API Calls | Credits Burned |
|--------|-----------|----------------|
| Page load | `fetch_todays_games()` | 1 credit |
| Click game | `fetch_player_props()` | **10 credits** |
| Analysis | `get_claude_analysis()` x2 | ~$0.006 |
| Search | `search_game_context()` + `search_late_news()` x2 | Perplexity usage |
| **Total per analysis** | | **~11 credits + API calls** |

---

#### File 1: `app.py` (The-Odds-API + Claude)

**Add cache to `fetch_todays_games()` (line 477):**
```python
@st.cache_data(ttl=300, show_spinner=False)  # 5 minute cache - saves 1 credit per refresh
def fetch_todays_games() -> list:
    """Fetch today's NBA games from The-Odds-API"""
    # ... existing code unchanged (lines 478-550)
```

**Add cache to `fetch_player_props()` (line 296):**
```python
@st.cache_data(ttl=300, show_spinner=False)  # 5 minute cache - saves 10 credits per click!
def fetch_player_props(game_id: str) -> dict:
    """
    Fetch player props for a specific game from The-Odds-API.
    CRITICAL: This costs 10 credits per uncached call!
    """
    # ... existing code unchanged (lines 297-389)
```

**Add cache to `get_claude_analysis()` (line 553):**
```python
@st.cache_data(ttl=1800, show_spinner=False)  # 30 minute cache for identical prompts
def get_claude_analysis(prompt: str, user_input: str, model: str = "claude-sonnet-4-20250514") -> str:
    """Get analysis from Claude API - cached to prevent duplicate calls"""
    # ... existing code unchanged (lines 554-570)
```

---

#### File 2: `perplexity_client.py`

**NOTE:** This file already has `import streamlit as st` at line 3, so no new import needed.

**Add cache to `search_game_context()` (line 51):**
```python
@st.cache_data(ttl=1800, show_spinner=False)  # 30 minute cache
def search_game_context(away_team: str, home_team: str, hours_to_game: int = 12) -> str:
    """
    Search for real-time context about a game matchup.
    Cached for 30 minutes - game context doesn't change rapidly.
    """
    # ... existing code unchanged (lines 52-120)
```

**Add cache to `search_player_context()` (line 123):**
```python
@st.cache_data(ttl=1800, show_spinner=False)  # 30 minute cache
def search_player_context(player_name: str, opponent: str = "", hours_to_game: int = 12) -> str:
    """
    Search for real-time context about a specific player.
    Cached for 30 minutes.
    """
    # ... existing code unchanged (lines 124-192)
```

**Add cache to `search_late_news()` (line 195):**
```python
@st.cache_data(ttl=300, show_spinner=False)  # 5 minute cache - needs freshness
def search_late_news(team_abbr: str) -> str:
    """
    Search for ONLY the most recent news (last hour) for late-breaking info.
    Shorter cache (5 min) because this is time-sensitive.
    """
    # ... existing code unchanged (lines 196-249)
```

---

#### Already Cached (No Changes Needed):

**`tank01_client.py`** - All 8 functions already have `@st.cache_data`:
- `get_team_roster()` - TTL 300s ✅
- `get_injury_list()` - TTL 300s ✅
- `get_all_teams_with_rosters()` - TTL 300s ✅
- `get_todays_games()` - TTL 60s ✅
- `get_depth_chart()` - TTL 300s ✅
- `get_box_score()` - TTL 300s ✅
- `get_player_recent_games()` - TTL 600s ✅
- `get_team_recent_record()` - TTL 300s ✅
---

#### Verification Steps:

1. **Confirm decorators added:**
```bash
# Check app.py has cache decorators
grep -n "@st.cache_data" app.py

# Expected output:
# 296:@st.cache_data(ttl=300, show_spinner=False)
# 477:@st.cache_data(ttl=300, show_spinner=False)
# 553:@st.cache_data(ttl=1800, show_spinner=False)
```

2. **Check perplexity_client.py:**
```bash
grep -n "@st.cache_data" perplexity_client.py

# Expected output:
# 51:@st.cache_data(ttl=1800, show_spinner=False)
# 123:@st.cache_data(ttl=1800, show_spinner=False)
# 195:@st.cache_data(ttl=300, show_spinner=False)
```

3. **Syntax check:**
```bash
python -m py_compile app.py
python -m py_compile perplexity_client.py
echo "Syntax OK"
```

4. **Test app runs:**
```bash
streamlit run app.py --server.headless true &
sleep 5
curl -s http://localhost:8501 | head -20
pkill -f streamlit
```

---

#### Cache TTL Strategy:

| File | Function | TTL | Credits Saved |
|------|----------|-----|---------------|
| `app.py` | `fetch_todays_games()` | 300s (5 min) | 1 credit/refresh |
| `app.py` | `fetch_player_props()` | 300s (5 min) | **10 credits/click** |
| `app.py` | `get_claude_analysis()` | 1800s (30 min) | ~$0.003/call |
| `perplexity_client.py` | `search_game_context()` | 1800s (30 min) | API usage |
| `perplexity_client.py` | `search_player_context()` | 1800s (30 min) | API usage |
| `perplexity_client.py` | `search_late_news()` | 300s (5 min) | API usage |

---

#### Expected Credit Savings:

**Before (no caching):**
```
Page load:     1 credit
Click game:    10 credits + Perplexity + Claude
Click same:    10 credits + Perplexity + Claude (AGAIN!)
10 clicks:     101+ credits burned
```

**After (with caching):**
```
Page load:     1 credit (cached for 5 min)
Click game:    10 credits (cached per game_id)
Click same:    0 credits (served from cache!)
10 clicks:     ~11 credits total (90% savings)
```

**Monthly Impact:**
- 20K credit limit → Without caching: burned in days
- With caching: ~2-3K credits/month actual usage

**Report back:**
- Confirm 6 functions have `@st.cache_data` decorators
- Confirm grep output matches expected
- Confirm syntax checks pass
- Confirm no runtime errors

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
