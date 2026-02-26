# Infographic & Data Visualization System

**Created:** February 21, 2026
**Status:** PLANNED — Blocked until Phase 8 backend cleanup complete
**Priority:** Medium (frontend sprint, post-backend stabilization)
**Estimated Cost:** $0 (Plotly + Kaleido are free/MIT-licensed)
**Reference:** PaperBanana (arXiv:2601.23265 / github.com/dwzhu-pku/PaperBanana) — AI-assisted illustration framework. Key pattern adopted: LLM writes matplotlib code → `exec()` in isolated `ProcessPoolExecutor` subprocess → base64 JPEG. See `_execute_plot_code_worker` in `visualizer_agent.py`. No image-gen API needed for data charts — code execution is always reproducible.

---

## Problem

Ludi-Bot has zero charting or data visualization capability. All output is plain text Markdown via Telegram or a deprecated PIL-based PNG card system (`utils/render_full_report.py`). Rich data exists in `ludi.db` (15,575+ bets, 4,500+ player trends, 396 rotation profiles) but is only consumable as raw numbers or text summaries.

## Goal

Build a shared chart engine that produces:
- **Static PNGs** for Telegram (morning brief, nightly debrief, Ask Ludi bot, weekly recap)
- **Interactive HTML** for the future Ludi Lens Streamlit dashboard (hover, filter, drill-down)
- Both outputs from the **same code** — one `go.Figure`, two export paths

---

## Architecture

### Library: Plotly + Kaleido

| Library | Purpose |
|---------|---------|
| `plotly>=5.24.0` | Chart generation — dual-output (PNG + interactive HTML) from one Figure object |
| `kaleido>=0.2.1` | Static PNG export engine (lightweight C++ binary, no headless Chrome) |

**Why Plotly:** Only library that does dual-output from one codebase. Kaleido runs natively on macOS Intel. Streamlit has native `st.plotly_chart()` support.

### File Structure

```
utils/chart_engine.py          # Brand theme, to_png(), to_html(), for_streamlit()
charts/
  __init__.py                  # Registry + convenience imports
  stat_confidence.py           # Chart 1: Win rate by stat+direction (A+ to F grades)
  daily_pnl.py                 # Chart 2: Daily P&L waterfall + cumulative line
  edge_vs_winrate.py           # Chart 3: Model edge vs actual WR scatter
  player_trend.py              # Chart 4: L7/L10/L15 sparklines with line reference
  scoring_environment.py       # Chart 5: OVER/UNDER hit rate heatmap
  bet_distribution.py          # Chart 6: Bet volume treemap by stat/side
  tier_performance.py          # Chart 7: DIAMOND/BLUE CHIP/etc. grouped bars
  rotation_profile.py          # Chart 8: Minutes by situation (stacked bars)
  matchup_matrix.py            # Chart 9: Archetype vs scheme heatmap
  cumulative_pnl.py            # Chart 10: Rolling P&L by strategy
  weekly_report.py             # Chart 11: Multi-panel weekly recap
  playtype_radar.py            # Chart 12: Synergy PPP radar/spider
```

### Brand Theme (Plotly template, applied globally)

| Element | Color | Hex |
|---------|-------|-----|
| Background | Dark Navy | `#0F172A` |
| Primary accent | Gold | `#FBBF24` |
| Secondary accent | Emerald | `#10B981` |
| Win / positive | Emerald | `#10B981` |
| Loss / negative | Red | `#EF4444` |
| Text | White | `#FFFFFF` |
| Grid lines | Slate-700 | `#334155` |
| Font | Liberation Sans (bundled in `assets/fonts/`) | -- |

### Data Flow

```
chart_engine.py (theme + export)
       |
  charts/*.py (build go.Figure from DB/cache data)
       |
  +---------+-----------+
  |         |           |
to_png()  to_html()  for_streamlit()
  |         |           |
Telegram  Browser    Streamlit app
```

---

## Telegram Output Map

Each chart is designed to live inside a specific Telegram surface. Build charts in order of the surfaces you use most.

| Chart | Telegram Surface | Send Method | Trigger |
|-------|-----------------|-------------|---------|
| Hit Streak Tracker | **Player Card (Spotlight)** | Inline photo before stat block | Any player with L10 ≥ 70% or ≤ 30% |
| Player Trend Sparklines | **Player Card (Spotlight)** | Inline mini-chart (L7/L10/L15 bars) | Every spotlight |
| Playtype Radar | **Player Card (Spotlight)** | Second photo, top-2 playtypes vs opponent | When synergy data available |
| Archetype Leaderboard Top 10/Bottom 10 | **Game Notes** | Photo header before game text block | Every game notes run |
| Matchup Edge Summary | **Game Notes** | Inline heatmap snippet | When DVP rank ≤ 5 or ≥ 26 |
| Stat Confidence Grade Matrix | **Morning Brief** | Follow-up photo after text brief | Daily 11 AM |
| Daily P&L Waterfall | **Nightly Debrief** | Photo attached to settlement summary | Daily 8:30 PM |
| Edge vs Win Rate Scatter | **Weekly Validation** | Attached to weekly report | Tuesdays |
| Confidence Tier Performance | **Weekly Validation** | Second photo in weekly report | Tuesdays |
| Scoring Environment Heatmap | **Morning Brief (evening mode)** | Photo before evening lock text | 6 PM |
| Weekly Recap Dashboard | **PM Bot debrief** | Multi-panel attached weekly | Sundays |
| Synergy Playtype Radar | **Ask Ludi Bot** | On-demand response | "show me X's playtypes" |
| Hot / Cool Players | **Weekly Archetype + Matchup Update** | Photo block — two-panel hot/cold leaderboard | `weekly_validation.yml` run |
| Archetype Leaderboard Top 10/Bottom 10 | **Weekly Archetype + Matchup Update** | Per-archetype hit rate leaderboard | `weekly_validation.yml` run |
| Matchup Edge Summary | **Weekly Archetype + Matchup Update** | Full 15-archetype × 5-scheme heatmap (larger than game notes version) | `weekly_validation.yml` run |

---

## Chart Catalog (12+ Charts, Ranked by Value)

### Tier 1 -- MVP (Phase V1) — Telegram Player Cards + Game Notes

| # | Chart | Type | Data Source | Telegram Surface |
|---|-------|------|------------|-----------------|
| 1 | **Hit Streak Tracker** | Horizontal bars (L5/L10/L15 hit rate), color-coded | `bet_recommendations` by player+stat+side | **Player Card** — shows streak status at a glance |
| 2 | **Archetype Leaderboard Top 10 / Bottom 10** | Two-panel sorted horizontal bars | `players.archetype` + `bet_recommendations` hit rate | **Game Notes** — surfaces best matchup targets |
| 3 | **Matchup Edge Summary** | Small heatmap: archetype rows × defense scheme columns | `team_dvp_by_archetype` + `player_type_profiles` | **Game Notes** — visual version of Phase 8.25 callout |
| 4 | **Stat Confidence Grade Matrix** | Horizontal bars, colored by grade (A+→F) | `cache/stat_confidence.json` | **Morning Brief** header visual |
| 5 | **Hot / Cool Players** | Two-panel bars (L7 delta vs season avg) | `bet_recommendations` settled + `players.archetype` | **Weekly Archetype Update** + Morning Brief slate trends |
| 6 | **Daily P&L Waterfall** | Green/red bars + cumulative line | `bet_recommendations` by date | **Nightly Debrief** |

### Tier 2 -- Calibration (Phase V2) — Validation + Ask Ludi

| # | Chart | Type | Data Source | Telegram Surface |
|---|-------|------|------------|-----------------|
| 6 | **Player Trend Sparklines** | Small multiples, mini-lines (L7/L10/L15) | `player_trends` + live lines | **Player Card** inline + Ask Ludi |
| 7 | **Edge vs Win Rate Scatter** | Scatter + diagonal calibration line | `bet_recommendations` by stat+side | Weekly validation |
| 8 | **Confidence Tier Performance** | Grouped bars (WR% + P&L per tier) | `bet_recommendations` by tier | Weekly recap |

### Tier 3 -- Full Catalog (Phase V3)

| # | Chart | Type | Data Source |
|---|-------|------|------------|
| 9 | Scoring Environment Heatmap | Heatmap grid | `scoring_environment.json` + historical |
| 10 | Bet Distribution Treemap | Treemap (size=volume, color=WR) | `bet_recommendations` by stat/side |
| 11 | Rotation Minutes Profile | Stacked horizontal bars | `rotation_profiles` table |
| 12 | Cumulative P&L by Strategy | Multi-line chart | `bet_recommendations` ordered by date |
| 13 | Weekly Recap Dashboard | Multi-panel (subplot grid) | Aggregate from past 7 days |
| 14 | Synergy Playtype Radar | Radar/spider chart | `player_synergy_playtypes` table |

---

### Chart Specs: New V1 Charts

#### Hit Streak Tracker (`charts/hit_streak.py`)
- **Layout:** Single horizontal bar chart, one bar per player, sorted by L10 hit rate descending
- **Color logic:** ≥70% = Emerald `#10B981` (streak), ≤30% = Red `#EF4444` (cold), else Gold `#FBBF24`
- **Labels:** Player name (left), `L10: 7/10 (70%)` (right), line marker at 55% threshold
- **Data:** `bet_recommendations WHERE player_name=? AND settled=1 ORDER BY game_date DESC LIMIT 10`
- **Context:** Appended as photo inside `format_bet_card()` or Spotlight block when L10 is extreme

#### Archetype Leaderboard Top 10 / Bottom 10 (`charts/archetype_leaderboard.py`)
- **Layout:** Two side-by-side panels — Top 10 (green bars) + Bottom 10 (red bars)
- **Dimensions:** Grouped by archetype label on Y-axis, sorted by `pts_vs_baseline` from `team_dvp_by_archetype`
- **Use case A (game notes):** Top 10 = teams allowing most pts to tonight's archetypes on slate. Bottom 10 = toughest matchups.
- **Use case B (weekly):** Top 10 players by hit rate per archetype bucket
- **Data:** `team_dvp_by_archetype WHERE archetype IN (...) AND data_confidence IN ('HIGH','MEDIUM') ORDER BY pts_vs_baseline DESC LIMIT 10`

#### Matchup Edge Summary (`charts/matchup_heatmap.py`)
- **Layout — Game Notes (compact):** Small heatmap — rows = archetypes (top 6 by bet volume on tonight's slate), columns = defense schemes (5 types)
- **Layout — Weekly Update (full):** All 15 archetypes × 5 schemes, larger figure with value annotations in each cell
- **Cell values:** Mean `pts_vs_baseline` from `player_archetype_vs_defense`
- **Color:** Diverging Emerald→White→Red (positive = exploitable, negative = avoid)
- **Contexts:** (1) Photo header in game notes when DVP rank ≤ 5 or ≥ 26. (2) Weekly archetype update via `weekly_validation.yml`

#### Hot / Cool Players (`charts/hot_cool_players.py`)
- **Layout:** Two-panel split — LEFT = "Heating Up" (top 8 players, L7 hit rate vs season average delta), RIGHT = "Cooling Down" (bottom 8)
- **Bar color:** HOT bars = Emerald `#10B981` gradient with flame indicator. COOL bars = Slate-blue `#475569` with ↓ indicator
- **Labels:** Player name, archetype tag, `L7: X/7 (71%) ↑ vs 52% season`
- **Sort:** By `(L7_hit_rate - season_hit_rate)` delta — biggest positive movers on left, biggest negative on right
- **Data:** `bet_recommendations` settled, joined to `players.archetype`. Minimum 5 settled bets in L7 window
- **Contexts:** (1) Weekly archetype + matchup update (`weekly_validation.yml`). (2) Morning brief slate trends header (existing `_build_slate_trends_header()` already surfaces this data — chart replaces the text version)

---

## Implementation Phases

### Phase V1: Foundation + Player Card + Game Notes Charts

| Step | Task | Files |
|------|------|-------|
| 1 | Add `plotly>=5.24.0` and `kaleido>=0.2.1` to requirements | `requirements.txt` |
| 2 | Create chart engine with brand template + `to_png()` / `to_html()` | NEW: `utils/chart_engine.py` |
| 3 | Create chart registry | NEW: `charts/__init__.py` |
| 4 | Build **Hit Streak Tracker** | NEW: `charts/hit_streak.py` |
| 5 | Build **Archetype Leaderboard Top 10 / Bottom 10** | NEW: `charts/archetype_leaderboard.py` |
| 6 | Build **Matchup Edge Heatmap** | NEW: `charts/matchup_heatmap.py` |
| 7 | Build Stat Confidence Grade Matrix | NEW: `charts/stat_confidence.py` |
| 8 | Build **Hot / Cool Players** | NEW: `charts/hot_cool_players.py` |
| 9 | Build Daily P&L Waterfall | NEW: `charts/daily_pnl.py` |
| 10 | Wire Hit Streak into player spotlight (`format_bet_card()`) | EDIT: `morning_brief.py` |
| 11 | Wire Archetype Leaderboard + Matchup Heatmap into game notes header | EDIT: `morning_brief.py` |
| 12 | Wire Stat Confidence into morning brief as follow-up photo | EDIT: `morning_brief.py` |
| 13 | Wire Hot/Cool + full Matchup Heatmap into `weekly_validation.yml` | EDIT: `weekly_validation.yml` |

**Note on implementation approach (from PaperBanana research):** For complex or one-off charts, use the code-execution pattern: Claude/Haiku writes matplotlib code → `exec()` in isolated subprocess → base64 JPEG. For repeating charts (hit streak, leaderboard) with known schemas, use static Plotly `go.Figure` functions for speed and reliability. Mixed approach = best of both worlds.

### Phase V2: Calibration + Weekly Visuals

| Step | Task | Files |
|------|------|-------|
| 1 | Build Edge vs Win Rate Scatter | NEW: `charts/edge_vs_winrate.py` |
| 2 | Build Player Trend Sparklines | NEW: `charts/player_trend.py` |
| 3 | Build Tier Performance chart | NEW: `charts/tier_performance.py` |
| 4 | Wire into weekly retrospective + nightly debrief | EDIT: scripts |

### Phase V3: Full Catalog

Build remaining charts 5, 6, 8-12. Create `scripts/generate_all_charts.py` convenience script.

### Phase V4: Streamlit Dashboard + AI-Assisted Charts

Replace `app.py` Flask scaffold with Streamlit. Wire all charts via `st.plotly_chart()`. Add filters.

**PaperBanana integration (when code releases):**
- Adopt Retrieve/Plan/Style/Visualize/Critic agent loop for Ask Ludi ad-hoc chart generation
- Haiku picks chart type from user's free-text question, generates Plotly code dynamically
- Self-critique: Claude evaluates chart readability before sending to Telegram

---

## Integration Points

| Integration | Method | Phase |
|-------------|--------|-------|
| Morning Brief | `send_photo(to_png(chart))` after text brief | V1 |
| Nightly Debrief | Daily P&L waterfall in Slack/Telegram | V1 |
| Weekly Validation | Edge/WR scatter + tier chart attached to report | V2 |
| Ask Ludi Bot | Player sparklines inline in responses | V2 (after 8.13) |
| Streamlit | `st.plotly_chart(for_streamlit(fig))` | V4 |

---

## Technical Notes

- **PNG sizing:** 1200x700px at 2x scale (retina quality, survives Telegram compression, ~200KB)
- **Font:** Liberation Sans bundled in `assets/fonts/` (cross-platform consistency)
- **DB access:** Read-only mode (`?mode=ro`) for chart queries — safe for concurrent pipeline runs
- **Kaleido:** Lightweight binary, pip-installable, no system dependencies on macOS Intel
- **Existing `render_full_report.py`:** Can be deprecated once chart engine is production-stable
