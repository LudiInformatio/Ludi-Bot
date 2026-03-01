# Prop Card & Odds Widget Research

**Created:** February 28, 2026
**Status:** Design Phase — Implementation deferred to Ludi Lens / Frontend Sprint
**Priority:** MEDIUM — No new data needed, all sources already in `ludi.db`

---

## Overview

Two related but independent features:

1. **PropsMadness-Style Player Card** — Single-player bet card showing projection, hit rates, DVP rank, alt line, status. Deliverable as PIL PNG (Telegram) or HTML component (Streamlit).
2. **The-Odds-API Widget** — Embeddable iframe for game lines display (h2h/spreads/totals only). Free Starter plan active (500 req/month, started Feb 10 2026).

---

## 1. The-Odds-API Widget

### Account Status
- **Plan:** Starter (Free)
- **Quota:** 500 requests/month
- **Reset:** 1st of each month at 12AM UTC
- **Widget API Key:** Separate from main `ODDS_API_KEY` — stored as `ODDS_WIDGET_KEY` in `.env`
- **Builder URL:** https://the-odds-api.com/widget/v1/builder.html

### Embed Code Structure
```html
<iframe
  title="Sports Odds Widget"
  style="width: 20rem; height: 25rem; border: 1px solid black;"
  src="https://widget.the-odds-api.com/v1/sports/{sport}/events/{event_id}/?
    accessKey={ODDS_WIDGET_KEY}
    &bookmakerKeys=draftkings,fanduel,betmgm,williamhill_us,fanatics
    &oddsFormat=american
    &markets=h2h,spreads,totals
    &marketNames=h2h:Moneyline,spreads:Spread,totals:Total"
>
</iframe>
```

### Parameters
| Param | Values | Notes |
|-------|--------|-------|
| `accessKey` | Widget API key (separate from data key) | Required |
| `sport` | `basketball_nba` | 100+ sports available |
| `events` | Leave blank = all events | Or filter to `{event_id}` |
| `bookmakerKeys` | Comma-separated sportsbook keys | Use NC Legal book keys |
| `oddsFormat` | `american` or `decimal` | Use `american` |
| `markets` | `h2h,spreads,totals` | **Player props NOT supported** |
| `marketNames` | Custom labels | e.g. `h2h:Moneyline` |

### What It Can/Cannot Do
| Feature | Widget | Our Stack |
|---------|--------|-----------|
| Game moneylines | ✅ | ✅ |
| Spreads / Totals | ✅ | ✅ |
| Team totals | ❌ | ✅ (per-event endpoint, fixed Feb 28) |
| **Player props** | ❌ | ✅ Full coverage |
| Alt lines | ❌ | ✅ Sprint 4 (Feb 28) |
| Edge / EV calc | ❌ | ✅ Module F |
| Projections | ❌ | ✅ Module C |
| Hit rates | ❌ | ✅ Module B |

### Where It Fits in Ludi Stack

**Streamlit (Ludi Lens):** Embed as a **game context sidebar panel** — shows live game lines without us building that display component. Player props section stays custom-built from `_all_books` data.

```
┌──────────────────┬───────────────────────────┐
│  GAME LINES      │  EDGE PLAYS               │
│  [Widget iframe] │  [Custom prop cards]       │
│  h2h/spread/total│  LeBron PTS OVER 27.5 +18%│
│  from widget     │  Alt: 26.5 @ +102 DK      │
└──────────────────┴───────────────────────────┘
```

**Telegram:** iframes not supported — widget cannot be used here.

**500 req/month:** At ~5 games/night × 30 days = 150 game-level loads. Fine for personal use. Will hit limits if Ludi Lens goes multi-user.

### Next Step to Explore
Use the free API key to inspect the full rendered widget — check CSS/layout patterns that could inform our own card design.
```bash
# Test embed — load in browser with your ODDS_WIDGET_KEY
https://widget.the-odds-api.com/v1/sports/basketball_nba/events/?accessKey=YOUR_WIDGET_KEY&bookmakerKeys=draftkings,fanduel&oddsFormat=american&markets=h2h,spreads,totals
```

---

## 2. PropsMadness-Style Player Card

### Inspiration
PropsMadness "Check My Prop" scorecard — 11-row display per player/line covering:
- DPT (P&R Ball Handler defensive rank)
- DSZ (Above Break 3 zone rank)
- Expected minutes range
- Similar-player hit rates
- Overall % composite score

Full platform research: `docs/research/competitive/COMPETITIVE_RESEARCH_2026.md`

### Proposed Card Design

```
┌──────────────────────────────────────────────────┐
│  LEBRON JAMES  •  LAL  •  HELIOCENTRIC_MAESTRO   │
│  PTS OVER 27.5  @  -108  FanDuel  •  1.0u        │
├──────────────────────────────────────────────────┤
│  PROJECTION    28.9  (+1.4 over line)             │
│  EDGE          +18.2%  •  BLUE CHIP               │
├──────────────────────────────────────────────────┤
│  HIT RATES                                        │
│  L5:  4/5 (80%)   L10:  7/10 (70%)               │
│  L15: 10/15 (67%) vs NEUTRAL defense: 71%         │
│  H2H vs GSW (last 4): 3/4 hit                    │
├──────────────────────────────────────────────────┤
│  DVP RANK   GSW allows 117.2 pts/100 possession  │
│             vs HELIOCENTRIC_MAESTRO  •  Rank 24/30│
├──────────────────────────────────────────────────┤
│  ALT LINE   OVER 26.5 @ +102 DK  (EV: +22.1%)   │
│  STATUS     ✅ ACTIVE  •  Avg mins: 36.2          │
│  MATCHUP    vs NEUTRAL defense  •  No DVP concern │
└──────────────────────────────────────────────────┘
```

### Data Sources (All Existing — Zero New APIs)

| Card Row | DB Source | Query |
|----------|-----------|-------|
| Projection / Edge | Module F output / `bet_recommendations` | `edge_pct`, `proj_value` |
| Tier / Units | `bet_recommendations.tier`, `units` | Direct read |
| L5/L10/L15 hit rates | Module B `hit_rates_by_market` | Pre-loaded per player/stat |
| vs scheme hit rate | Module B `vs_scheme_cache` | Pre-loaded per player/stat/scheme |
| H2H vs opponent | `player_game_logs` | Last 4-6 games vs `opponent` |
| DVP rank | `team_dvp_by_archetype` | `rank_pts` where `data_confidence IN ('HIGH','MEDIUM')` |
| Alt line | `game['alt_props']` (Sprint 4) | `game.get('alt_props',{}).get(stat,{}).get(player,{})` |
| Status / minutes | `player_injuries` + `rotation_profiles` | `snapshot_time`, `projected_minutes` |
| Archetype / matchup | `players.archetype` + Module E notes | `calibrated['notes']` |

### Implementation Plan

**Phase 1 — PIL PNG for Telegram** (1 session build)
- File: `utils/card_engine.py`
- Function: `generate_player_prop_card(bet_dict, conn) -> PIL.Image`
- Style: Dark Navy `#0F172A` bg, Gold `#FBBF24` headers, Emerald `#10B981` positive values
- Size: 800×500px (landscape, matches existing morning brief cards)
- Wire into: `morning_brief.py` (one card per DIAMOND/BLUE CHIP), `bots/ask_ludi_handlers.py` (edges intent)

**Phase 2 — HTML Component for Streamlit** (Ludi Lens sprint)
- File: `app/components/prop_card.py`
- Render via `st.html()` or custom Streamlit component
- Right panel of two-column layout (widget iframe left, prop cards right)

**Phase 3 — PropsMadness Composite Score** (optional enhancement)
- `_prop_pulse_score(bet_dict, conn) -> int` (0–100)
- Blend: Edge% (40%) + L10 hit rate (25%) + DVP rank (20%) + alt line EV delta (15%)
- Display as a single score bar on the card

### PIL Pattern Reference
Existing PIL card generation: `utils/render_full_report.py` — reuse font loading, color constants, and image composition patterns. The player prop card is a focused single-player version.

```python
# Minimal skeleton
from PIL import Image, ImageDraw, ImageFont

NAVY = (15, 23, 42)       # #0F172A
GOLD = (251, 191, 36)     # #FBBF24
EMERALD = (16, 185, 129)  # #10B981
RED = (239, 68, 68)       # #EF4444

def generate_player_prop_card(bet: dict, conn) -> Image.Image:
    img = Image.new('RGB', (800, 500), NAVY)
    draw = ImageDraw.Draw(img)
    # ... draw header, rows, dividers
    return img
```

---

## Implementation Blockers / Dependencies

| Blocker | Status |
|---------|--------|
| Hit rates in bet_recommendations | ✅ Module B `hit_rates_by_market` pre-loaded |
| Alt lines in game dict | ✅ Sprint 4 (Feb 28) |
| DVP rankings | ✅ `team_dvp_by_archetype` populated |
| H2H query pattern | ⬜ New query needed (simple `player_game_logs` filter) |
| PIL font assets | ✅ Existing in `assets/fonts/` |
| Widget API key in .env | ⬜ Add `ODDS_WIDGET_KEY` to `.env` + `.env.template` |

---

## Deferred To

- **Ludi Lens Dashboard Sprint** (post-Phase 8) — HTML component + widget iframe integration
- **Frontend Sprint** — Full card catalog per `docs/projects/INFOGRAPHIC_VISUALIZATION_SYSTEM.md`

The PIL PNG version for Telegram can ship independently as a 1-session build whenever prioritized.
