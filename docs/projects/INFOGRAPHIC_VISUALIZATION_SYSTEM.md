# Infographic & Data Visualization System

**Created:** February 21, 2026
**Status:** PLANNED — Blocked until Phase 8 backend cleanup complete
**Priority:** Medium (frontend sprint, post-backend stabilization)
**Estimated Cost:** $0 (Plotly + Kaleido are free/MIT-licensed)
**Reference:** PaperBanana (arXiv:2601.23265 / github.com/dwzhu-pku/PaperBanana) — AI-assisted illustration framework, code TBD ~March 2026

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

## Chart Catalog (12 Charts, Ranked by Value)

### Tier 1 -- MVP (Phase V1)

| # | Chart | Type | Data Source | Use Case |
|---|-------|------|------------|----------|
| 1 | **Stat Confidence Grade Matrix** | Horizontal bars, colored by grade | `cache/stat_confidence.json` | Morning brief: "here's what's sharp today" |
| 2 | **Daily P&L Waterfall** | Green/red bars + cumulative line | `bet_recommendations` by date | Nightly debrief: "Am I making money?" |

### Tier 2 -- Calibration (Phase V2)

| # | Chart | Type | Data Source | Use Case |
|---|-------|------|------------|----------|
| 3 | **Edge vs Win Rate Scatter** | Scatter + diagonal calibration line | `bet_recommendations` by stat+side | Weekly validation: exposes overconfidence |
| 4 | **Player Trend Sparklines** | Small multiples, mini-lines | `player_trends` + live lines | Ask Ludi: "show me LeBron's PTS trend" |
| 7 | **Confidence Tier Performance** | Grouped bars (WR% + P&L) | `bet_recommendations` by tier | Weekly recap: validates tier system |

### Tier 3 -- Full Catalog (Phase V3)

| # | Chart | Type | Data Source |
|---|-------|------|------------|
| 5 | Scoring Environment Heatmap | Heatmap grid | `scoring_environment.json` + historical |
| 6 | Bet Distribution Treemap | Treemap (size=volume, color=WR) | `bet_recommendations` by stat/side |
| 8 | Rotation Minutes Profile | Stacked horizontal bars | `rotation_profiles` table |
| 9 | Archetype vs Scheme Matrix | Heatmap | `bet_recommendations` + `players.archetype` |
| 10 | Cumulative P&L by Strategy | Multi-line chart | `bet_recommendations` ordered by date |
| 11 | Weekly Recap Dashboard | Multi-panel (subplot grid) | Aggregate from past 7 days |
| 12 | Synergy Playtype Radar | Radar/spider chart | `player_synergy_playtypes` table |

---

## Implementation Phases

### Phase V1: Foundation + 2 MVP Charts

| Step | Task | Files |
|------|------|-------|
| 1 | Add `plotly>=5.24.0` and `kaleido>=0.2.1` to requirements | `requirements.txt` |
| 2 | Create chart engine with brand template + export functions | NEW: `utils/chart_engine.py` |
| 3 | Create chart registry | NEW: `charts/__init__.py` |
| 4 | Build Stat Confidence Grade Matrix | NEW: `charts/stat_confidence.py` |
| 5 | Build Daily P&L Waterfall | NEW: `charts/daily_pnl.py` |
| 6 | Wire Chart 1 into morning brief as follow-up photo | EDIT: `morning_brief.py` |

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
