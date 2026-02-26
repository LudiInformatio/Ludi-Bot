# Competitive Platform Research Sprint — Feb 26, 2026

**Date:** February 26, 2026
**Sessions:** 1 (Feb 26, 2026)
**Access:** OddsJam Sharp Money + Platinum (free trial), Outlier.bet Pro+ (free trial), all others public
**Purpose:** Deep-dive paid-tier access to OddsJam and Outlier.bet to reverse-engineer their EV methodology, UX patterns, and feature set. Identify features to build, steal, or skip for Ludi.

---

## Platforms Researched

| Platform | URL | Access | Tier |
|----------|-----|--------|------|
| OddsJam | oddsjam.com | Sharp Money + Platinum trial | Paid |
| Outlier.bet | outlier.bet | Pro+ trial | Paid |
| BucketsToBucks | buckettobucks.com | Public | Free |
| StraightBettin | straightbettin.com | Public | Free |
| PropsMadness | propsmadness.com | Public | Free |
| Action Network | actionnetwork.com | Public | Free |

---

## OddsJam — Positive EV Feed

### Section Overview
URL: `/betting-tools/positive-ev`
Default view: Pre-Match tab, 221 bets, sorted by +EV% descending

### Column Structure
| Column | Description | Notes |
|--------|-------------|-------|
| +EV% | Edge percentage, green, large font | Primary sort. Range seen: 37.49% down to ~2% |
| EVENT | Game + time + league (Basketball • NBA) | Clickable — goes to game page |
| MARKET | Stat type (Player Assists, Player Rebounds, Player Points, Team Total) | Color-coded purple |
| BOOKS | Player name + line + book logo + odds + Liq $XX | "Liq" = liquidity (how much available at this price) |
| 1-CLICK BET | Blue "BET ↗" (book-specific prop) or green "GAME ↗" (multi-book game line) | Two distinct CTA types |
| PROBABILITY | Model's estimated true probability | Range seen: 37–52% |
| BET SIZE | Kelly-calculated dollar size | Range seen: $10–$40 |

### Live Bet Examples Captured
| EV% | Player/Event | Market | Odds | Liq | Probability | Kelly Size |
|-----|-------------|--------|------|-----|-------------|------------|
| 37.49% | Norman Powell Over 2.5 AST | Player Assists | +223 MIA | $310 | 42.6% | $40 |
| 34.75% | Kawhi Leonard Over 6.5 REB | Player Rebounds | +163 LAC | $10 | 51.2% | $10 |
| 26.52% | Amen Thompson Over 6.5 REB | Player Rebounds | +144 HOU | $22 | 51.9% | $22 |
| 22.48% | Amen Thompson Over 15.5 PTS | Player Points | +156 HOU | $19 | 47.8% | $19 |
| 12.45% | FC Barcelona Under 6.5 Corners | Team Total Corners | +141 | — | 46.7% | $20 |
| 9.69% | Atlanta Hawks Over 128.5 | Team Total | +200 | — | 36.6% | $10 |

### Key UX Observations
- **Two CTA types**: Blue "BET ↗" = direct to book prop page. Green "GAME ↗" = game-level multi-book view
- **Liquidity column**: Dollar amount available at current price before line moves (e.g. "Liq $310"). No Ludi equivalent.
- **Auto-refresh (Platinum)**: Real-time count updates without page reload. "221 Pre-Match" ticker updates live.
- **Row actions** (⋮ menu on right): likely hide/track/alert — not yet captured
- **Star icon**: Bookmark/watchlist functionality
- **Live tab**: Separate in-game +EV feed (not yet explored)
- **Tour message**: "Positive EV is the most sustainable long-term strategy" — educational positioning

### OddsJam Tour Messaging (7 steps captured)
1. +EV feed intro — "cross-book arbitrage to find mispriced lines"
2. Column explanation — EV%, books, probability
3. Liquidity column — "how much you can bet before price moves"
4. 1-Click BET button — direct routing to sportsbook
5. Filters — sport/market/EV threshold
6. Platinum real-time refresh
7. "Book a free 1:1 coaching call" CTA at tour end

### Ludi Actions — Positive EV Feed
| Feature | Ludi Has? | Priority | Notes |
|---------|-----------|----------|-------|
| Liquidity display ($XX available) | No | 2 | Requires Odds API liquidity endpoint — check if available |
| Auto-refresh bet count | No | 3 | Nice-to-have for Ludi Lens dashboard |
| Two CTA types (prop vs game) | No | 3 | Ludi is props-only currently |
| Probability displayed per bet | Yes (internal) | 2 | Surface in Telegram cards |
| Kelly sizing per bet | Yes | ✅ | Already in unit sizing |
| EV% as primary sort | Yes | ✅ | Already sorts by edge |
| Live tab (in-game +EV) | No | 1 | Blocked per ROADMAP until May 2026 |
| Bookmark/watchlist per bet | No | 3 | Future Ludi Lens feature |

---

## OddsJam — Sportsbook Screen

**Screenshot:** `oddsjam/sportsbook-screen-moneylines.jpeg`

Full-slate moneyline comparison table. Columns: game date/time + team name, then one column per book (DraftKings, BetMGM, Caesars, FanDuel, BetRivers, Pinnacle, Novig, etc.) showing the moneyline odds side-by-side. Color coding highlights best available odds per row. Filter tabs: `All` | `Favorites` | `NBA` | `Moneyline ▾` | `Games ▾` | `All ▾` | Sportsbooks selector | Search. Also shows `Main Markets` | `Moneyline` | `Point Spread` | `Total Points` | `1st Quarter Moneyline` | `1st Half Moneyline` | `1st Half Total Points` | `Team Total` tab row.

**Key finding:** OddsJam exposes **1st Quarter Moneyline** and **1st Half Moneyline** as first-class markets alongside full-game lines — confirms quarter/half split betting is mainstream.

### Ludi Actions — Sportsbook Screen
| Feature | Ludi Has? | Priority | Notes |
|---------|-----------|----------|-------|
| Cross-book moneyline comparison table | No | 3 | Game lines only, not props |
| 1Q/1H market tabs | No | 2 | Confirms H1 split props worth tracking in trend engine |

---

## OddsJam — Bet Tracker

**Screenshot:** `oddsjam/bet-tracker-dashboard.jpeg`

**Bet Tracker Dashboard tabs:** `Dashboard` | `Bet Tracker` | `Sweat Station` | `Deposits / Withdrawals Tracker` | `Following` | `Followers` | `Tags`

**Dashboard features:**
- Profile controls: Copy profile link, Public Account toggle, "Only show verified bets" toggle, **CLV Notifications toggle**
- Social proof: Followers count, Following count, Total views
- **Synced Sportsbook Cash Balance** right panel — shows live book balances (BetMGM $126.75, Caesars $1,101.45, WynnBET $54.12). "Sync Sportsbooks" CTA.
- P&L chart: "Past Week" view, share to X button
- **CLV Notifications toggle** — alerts when your bet beats closing line

**Key finding:** OddsJam has a **social layer** (followers/following/public profile) on top of the bet tracker — users can follow sharp bettors and see their verified bets. CLV notifications are built-in at the product level.

### Ludi Actions — Bet Tracker
| Feature | Ludi Has? | Priority | Notes |
|---------|-----------|----------|-------|
| CLV notifications (alert when beat closing) | No | 2 | Ludi tracks CLV in DB — surface as Telegram alert when CLV > 0 |
| Synced sportsbook cash balance | No | 3 | Would require sportsbook API access — not feasible now |
| Social bet tracker (followers/public profile) | No | 3 | Post-Ludi-Lens social feature |
| P&L chart with share-to-X | No | 2 | Phase V1 chart: Daily P&L Waterfall — add share button in Ludi Lens |

---

## OddsJam — Learn Section

**Screenshot:** `oddsjam/learn-overview.jpeg` + `oddsjam/learn-sharp-money-article.jpeg`

Article categories: `All (6)` | `Updates (3)` | `Getting Started (3)`

**Available articles:**
- Deposit Optimizer: Find the most profitable sportsbooks in your state
- ⚙️ Advanced Arbitrage Filters
- Introducing Backup Bets
- How to profit with Sharp Money ← (clicked — see below)
- The Key To Sports Betting Success: Volume
- How Much to Deposit in Each Sportsbook

**"How to profit with Sharp Money" article:**
- Subtitle: "Introducing a new way to profit from data-backed bets: track liquidity from professional bettors and follow their actual positions!"
- Screenshot shows the **liquidity column** in action: Matthew Stafford Under 0.5 rushing yards → $10,713 liquidity circled — "when you see $10,000 of liquidity" the line is real
- Video-based educational content (90s preview shown)
- Key message: liquidity = confirmation of sharp money position

**Key finding:** OddsJam uses **educational content as user acquisition** — "Getting Started" articles teach EV betting fundamentals while demonstrating their own tools. A Ludi Lens web app should have an "Education" or "How This Works" section.

### Ludi Actions — Learn Section
| Feature | Ludi Has? | Priority | Notes |
|---------|-----------|----------|-------|
| Educational content for non-sharp users | No | 2 | Ask Ludi bot could answer "how does Ludi calculate edge?" |
| Liquidity tracking as sharp money signal | No | 2 | Check if Odds API exposes liquidity endpoint |

---

## OddsJam — Platinum Features / Sharp Money

*(Researched at account level — Platinum features confirmed: real-time auto-refresh, CLV notifications, sharp money feed. Sharp Money section itself not screenshotted in detail — accessible via left nav "Sharp Money".)*

---

## Outlier.bet — Premium+ Plan ($29.99/mo)

**Researched:** February 26, 2026 | Access: Premium+ free trial | Sessions: 2

### Tier Architecture

| Tier | Price | What You Get |
|------|-------|--------------|
| Free | $0 | Basic props browsing, limited features |
| Premium+ | $29.99/mo | Insights feed, Popular, Games (full), Props (full filters + alt lines + hit rate) |
| Pro | $79.99/mo | Everything in Premium+ PLUS: EV+, Boosts/Promos, Arbitrage, Middle Betting |

**Paywall language on EV+ gate:**
> "EV+, Boost & Promos, Arbitrage, and Middle Betting features are only available with an Outlier Pro Subscription"

---

### Left Nav Structure

| Section | URL | Tier | Description |
|---------|-----|------|-------------|
| Insights | `/NBA/trending/insights` | Premium+ | Global feed of 1700+ trend cards across all games |
| Popular | `/NBA/trending/picks` | Premium+ | FanDuel trending parlay feed ranked by total bets |
| Games | `/NBA/games` | Premium+ | Date-nav game cards + full Match Details |
| Props | `/NBA/props` | Premium+ | Full props table with alt lines + filter system |
| EV+ | `/pro/ev` | **Pro only** | Positive EV feed (gated) |
| Boosts | `/pro/boosts` | **Pro only** | Sportsbook promos (gated) |
| Arbitrage | `/pro/arbitrage` | **Pro only** | Cross-book arbitrage (gated) |
| Middle Bets | `/pro/middle-bets` | **Pro only** | Middle bet detection (gated) |

---

### Insights Feed (`/NBA/trending/insights`)

**Overview:** Global feed of auto-generated trend cards, 1727/1740 Insights visible today. Multi-sport: NBA | NCAAMB | Soccer | NHL | MLB | NFL | NCAAFB | WNBA.

**Filter bar:**
`Filters` | `Saved` | `Insight Type ▾` | `Games ▾` | `Players ▾` | `Teams ▾` | `Odds ▾` | `Prop` | `Sort ▾`

**Card format — each insight contains:**
1. Team/player photo + name + team badge + game context (opponent, time)
2. Plain-English trend sentence with sample size + rolling window + context qualifier
3. Recommended bet line + hit rate bar (green/red) + best odds + book logo

**Live Insight Examples Captured:**

| Subject | Insight Text | Bet | Hit Rate | Odds |
|---------|-------------|-----|----------|------|
| OKC Thunder (vs DEN) | "The Oklahoma City Thunder are 32-7 (82.1%) in their last 39 games at home" | OKC ML | 82% | -194 Kalshi |
| Milwaukee Bucks (vs NYK) | "The Milwaukee Bucks are 1-4 (20.0%) in their last 5 games vs. top 10 scoring defenses" | NYK ML | 80% | -245 Kalshi |
| Detroit Pistons (vs CLE) | "The Detroit Pistons are 21-6 (77.8%) in their last 27 games at home" | DET ML | 78% | -213 Kalshi |
| Naz Reid (MIN vs LAC) | "Naz Reid has exceeded 0.5 steals in 8 of his last 9 games (1.4 steals/game avg)" | Over 0.5 Steals | 89% | — |
| Ben Sheppard (CHA@IND) | "Ben Sheppard has failed to exceed 8.5 points in 10 of his last 12 vs. top 10 defenses (6.4 pts/g avg)" | Under 8.5 Pts | 83% | -110 |
| Moussa Diabaté (CHA@IND) | "Moussa Diabaté has exceeded 4.5 1H rebounds in 4 of his last 5 games on the road (6.4 reb/g avg)" | Over 4.5 Reb | 80% | -120 |
| Ryan Kalkbrenner (CHA@IND) | "Ryan Kalkbrenner has exceeded 4.5 rebounds in 4 of last 5 vs. bottom 10 defenses (5.6 reb/g avg)" | Over 4.5 Reb | 80% | -113 |
| Kon Knueppel (IND vs CHA) | "Kon Knueppel has exceeded 21.5 points + assists in 7 of his last 8 games (25.9 P+A avg)" | Over 21.5 P+A | 88% | -105 |
| Miles Bridges (CHA@IND) | "Miles Bridges has exceeded 3.5 1Q points in 9 of his last 10 games (5.1 1Q pts avg)" | Over 3.5 Pts | 90% | -110 |

**Key observation:** Insights cover **quarter-split props** (1Q points) and **combo props** (Points + Assists), not just full-game. The narrative template is: `[Player/Team] has [exceeded/failed to exceed] [line] in [X of last N] games [context qualifier] ([avg] avg).`

**Ludi parallel:** This is exactly what Ludi's Spotlight cards do — but Outlier surfaces them as a feed of 1700+ ranked by hit rate, not 3-5 cards per game. The **Prop button** in the filter bar toggles between game-level and player-level insights.

### Ludi Actions — Insights Feed
| Feature | Ludi Has? | Priority | Notes |
|---------|-----------|----------|-------|
| Global trend feed (all games, all players) | Partial (per-game in morning brief) | 1 | **Ask Ludi** could answer "show me best trends today" → query `player_trends` |
| 1700+ daily insights auto-ranked by hit rate | No | 2 | Ludi has `player_trends` table (4500+ rows) — expose via Ask Ludi or Ludi Lens |
| Quarter/half split insights | No | 2 | BDL V2 has H1/H2 data; could add Q1/Q2 to trend engine |
| Combo prop insights (P+A, P+R) | No | 2 | Add to `player_trends` trend engine as new stat categories |
| Plain-English narrative template | Yes (Claude) | ✅ | Ludi's Spotlights already do this — extend to more players |
| "Saved" bookmarking per insight | No | 3 | Future Ludi Lens feature |

---

### Popular Feed (`/NBA/trending/picks`)

**Overview:** Shows the most-bet parlays on FanDuel, ranked by "total bets" (crowd wisdom / social proof signal).

**Card format:**
- Header: "FanDuel Trending Parlay +XXXX" + total bets count + game context
- Legs: Player/line + hit rate bar + best current odds + book logo
- CTA: **"ADD ALL BETS TO BETSLIP"** — 1-click sends all legs to sportsbook

**Live Parlay Examples Captured (Feb 26):**

| Parlay | Odds | Total Bets | Legs |
|--------|------|-----------|------|
| MIN @ LAC | +1248 | 760 | Kawhi Over 29.5 Pts (40%), Ant Over 29.5 Pts (70%), Ant Over 5.5 Reb (50%), Kawhi Over 7.5 Reb (60%) |
| HOU @ ORL | +1657 | 690 | HOU ML (60%), KD Over 24.5 Pts (40%), KD Over 5.5 Reb (40%), KD Over 5.5 Ast (30%) |

**Right panel — My Picks tracker:**
Tracks your picks across **15 sportsbooks**: FanDuel, DraftKings, PrizePicks, BetMGM, ProphetX, Bet365, Novig, Caesars, Sleeper, theScore Bet, BetRivers, Underdog, Fliff, Kalshi, Hard Rock Bet. Share button for social export.

**Key observation:** Popular uses public betting *as content* — the crowd's parlay becomes the feed item. Low-confidence legs (40%) are still shown, suggesting this is pure social signal, not a model endorsement. The total bets count functions as a trust/social-proof metric.

### Ludi Actions — Popular Feed
| Feature | Ludi Has? | Priority | Notes |
|---------|-----------|----------|-------|
| Trending parlay feed (public bets) | No | 2 | Phase 8.22 Social Intelligence — `social_signals` table captures this signal |
| "ADD ALL TO BETSLIP" 1-click | No | 3 | Future Ludi Lens web app feature |
| Pick tracker across 15 books | No | 3 | Ludi tracks vs. NC Legal books only (Tier 2) — by design |
| Public bet % as inverse signal | Partial (in curate logic) | 1 | Prop Pulse Score uses inverse public bet% (20% weight) — already planned |

---

### Games (`/NBA/games`)

**Overview:** Date-navigable game card grid with EV+ badges embedded on specific lines.

**Date nav bar:** "Today" through Mar 18 (3+ weeks ahead). Auto-routes to `?gameFilter=YYYY-MM-DD`.

**Game card structure (4-panel layout):**
- Header: Team logos + matchup + game time
- Panel 1: Moneyline (Home ML | Away ML)
- Panel 2: Spread (favorite + spread number)
- Panel 3: Over (total + over odds)
- Panel 4: Under (total + under odds)
- **EV+ badge** appears on individual panels when that specific line has positive EV vs sharp books
- **PUBLIC BETTING** accordion per card (collapsed by default)

**Live EV+ examples on game cards (Feb 26):**
- IND ML +614 → EV+ badge
- MIA ML +144 → EV+ badge
- BKN ML +500 → EV+ badge
- Under 239.5 (game total) → EV+ badge
- Under 223.5 → EV+ badge

### Ludi Actions — Games Page
| Feature | Ludi Has? | Priority | Notes |
|---------|-----------|----------|-------|
| EV+ badge on game lines | No | 2 | Phase 8.18 game lines modifier — surface EV flag on game-level output |
| Public betting % per game | No | 2 | Phase 8.22 — `social_signals` for public bet% |
| Date-forward nav (3+ weeks) | No | 3 | Ludi is same-day only currently |

---

### Match Details (Game Detail Page)

**URL pattern:** `/NBA/games/{game_id}?marketType=GAMELINE&marketGroup=GAMELINES`

**Two-panel layout:**
- **Left**: Market tabs + props table
- **Right**: Matchup / Lineup / Insights tabs (sticky right panel)

**Market Tabs (left):**
`Gamelines` | `Player props` | `Team props` | `Game props`

**Player Props Market Groups (dropdown):**
`First/Last/Most` | `Offensive` | `Defensive` | `General` | `Fantasy` | `Quarter` | `Half`

**Offensive props URL:** `?marketType=PLAYER_PROP&marketGroup=OFFENSIVE_PROPS`

---

#### Right Panel — Matchup Tab

**Team Rankings (2025)** side-by-side comparison with league ranks for 16+ stats:

| Stat | Notes |
|------|-------|
| Effective Field Goal % | |
| Turnover % | |
| Offensive Rebound % | |
| Free Throw Rate | |
| Points | |
| Field Goal % | |
| 2-Point % | |
| 3-Point % | |
| Free Throws % | |
| Rebounds | |
| Blocks | |
| Steals | |
| Assist-to-Turnover Ratio | |
| Pace Factor | |
| Points in Paint | |
| Fast Break Points | |

Format: `[Team Avg] [League Rank] [Stat Name] [League Rank] [Team Avg]` — direct side-by-side comparison. **Offense ↔ Defense toggle** switches entire panel.

#### Right Panel — Lineup Tab

**"Provided by RotoWire"** attribution header.

**Expected Lineup section:** CHA vs IND starters side-by-side (5v5), player headshots + jersey number + abbreviated name. Injury status badge inline (e.g. "Q" = Questionable next to player name).

**Injuries section:** Team filter tabs (CHA | IND). Each entry:
- Player headshot + team logo + position abbreviation + injury description
- Status button (Out/GTD/Q) + timestamp of when status was last reported (e.g. "Feb 25 5:18 PM") + clickable chevron (→ player prop page)

**Live injury example:** Liam McNeeley #33 (SF, CHA) — Left Ankle Sprain — **Out** — Feb 25 5:18 PM

**Public Betting section** also appears in this tab:
- Money Line: % of Bets + % of Money (separate rows)
- Spread: same format
- Total O/U: Over/Under % of Bets + % of Money

**Live public betting data (CHA @ IND):**
| Market | CHA Bets | CHA Money | IND Bets | IND Money |
|--------|----------|-----------|----------|-----------|
| Money Line | 83% | 64% | 17% | 36% |
| Spread | 51% | 51% | 49% | 49% |
| Total O/U (Over) | 69% bets | 55% money | 31% | 45% |

#### Right Panel — Insights Tab

Auto-generated narrative trend cards (same format as global Insights feed, filtered to this game's players + teams). Scrolls through player cards, then ends with Public Betting repeat.

**Key finding:** The Insights tab surfaces **quarter-split props** inline with full-game props — e.g. "Over 3.5 1Q Points" appears alongside "Over 15.5 Points". This is the same game context, not a separate filter.

### Ludi Actions — Match Details
| Feature | Ludi Has? | Priority | Notes |
|---------|-----------|----------|-------|
| Team rankings side-by-side (16 stats + ranks) | Partial (DVP) | 1 | Ludi has `team_dvp_by_archetype` but not league ranks. Add rank columns to `team_dvp_by_archetype` or new `team_rankings` table |
| Offense ↔ Defense toggle | No | 2 | Phase 8.11 Power Ratings — relevant to this display |
| Lineup provided by RotoWire (with injury badges inline) | No (Module D only) | 1 | Phase 8.27 lineup sync already done — RotoWire lineups are the industry standard display |
| Injury timestamp (last updated) | Partial | 1 | `player_injuries.snapshot_time` exists — surface in morning brief cards |
| Public betting % (bets + money separate) | No | 1 | Phase 8.22 Social Intelligence captures this — also add "% of money" not just "% of bets" |
| Quarter-split props in same context as full-game | No | 2 | Ludi has H1/H2 from BDL but not Q1. Worth tracking for trend engine extension |

---

### Props Table (`/NBA/props`)

**Overview:** Full props table with 5,973 base rows (18,363 total with all alt lines). Multi-sport tabs.

**Show alt lines toggle:**
- Off: 5,973 props (main lines only)
- On: 17,564 props (+11,591 rows from alt line expansion)
- Counted as "1 Filter" in the badge system
- URL encodes filter state as base64 blob: `?filters=N4Iglg...`

**Filter system (each opens a dialog):**
- **Propositions**: Stat type checkboxes (Points, Rebounds, Assists, etc.)
- **Opponent Matchup**: Filter by opponent team
- **Hit Rate**: Dual-handle range slider + time window tabs (L5 | L10 | L20 | H2H | 2025 | 2024)
  - From%/To% number inputs — updates live as you type
  - User-friendly badge: "At least 70%" instead of "Hit Rate: 70%–100%"
  - Trash icon (clear filter) + Done button (confirm)
  - Count updates real-time as filter applies

**Filter badge system:** Each active filter = a colored badge at the top of the table. "X Filters" count badge visible at top.

**Column structure (per prop row):**
- Player name + team badge
- Stat category + line
- Book logos (best available) with odds
- Hit rate bar (green/red segmented) + percentage
- EV+ badge on specific lines where edge exists (not all lines)

**Alt line ladder (Miles Bridges — Points, Feb 26):**

| Line | Direction | Odds | Book | L10 Hit Rate | EV+ |
|------|-----------|------|------|-------------|-----|
| 0.5 | Over | — | — | 100% | — |
| 7.5 | Over | -1500 | DraftKings | 90% | — |
| 9.5 | Over / Under | -620 / +156 | DK / Kalshi | 80% / 20% | — |
| 11.5 | Over | 👿 | PrizePicks | 70% | — |
| 12.5 | Over | 👿 | PrizePicks | 70% | — |
| 13.5 | Over | 👿 | PrizePicks | 70% | — |
| 14.5 | Over / Under | -132 / +125 | DK / theScore | 60% / 40% | — |
| 15.5 | Over / Under | -103 / +105 | DK / BetMGM | 60% / 40% | **EV+** |
| 16.5 | Over / Under | +100 / -130 | theScore | — | — |

**👿/😈 emojis on PrizePicks:** These are "fade" indicators — Outlier is signaling to fade (bet against) the PrizePicks line, presumably because PrizePicks is offering the Over at unfavorable juice relative to other books.

**Books available in Outlier:**
FanDuel, DraftKings, BetRivers, Kalshi, BetMGM, PrizePicks, theScore Bet, Hard Rock Bet, ProphetX, Bet365, Novig, Caesars, Sleeper, Underdog, Fliff

### Ludi Actions — Props Table
| Feature | Ludi Has? | Priority | Notes |
|---------|-----------|----------|-------|
| Alt line ladder (full sequence per player) | No | 1 | Ludi has single main line only. Ask Ludi could surface "best alt line for Player X" |
| Hit rate per specific alt line | No | 1 | `player_trends` has L10 hit rate at main line — extend to alt lines |
| EV+ badge on specific alt lines (not just main) | No | 1 | Phase F alchemist calculates edge at main line — extend to alt line sweep |
| Hit rate filter with time window tabs | Partial (internal) | 2 | Ludi computes L7/L10/L15 — expose as filter in Ask Ludi or Ludi Lens |
| "Fade" signaling on DFS books (👿) | No | 2 | Interesting — DFS vs sportsbook line comparison. No immediate Ludi parallel |
| URL-encoded filter state | No | 3 | Relevant when Ludi Lens web app is built |
| Real-time prop count as filters apply | No | 3 | Nice dashboard UX |

---

## Outlier.bet — Player Prop Detail Page

**Screenshot:** `outlier/player-prop-detail-naz-reid-steals.jpeg`

Accessed by clicking a player from the Insights feed. Full drill-down page for a single player-prop combination.

**Header row:** Player headshot + name + team + game context + game time → Prop title ("Key LAC Steals offense")

**Prop selector row:**
- Current line: "Over 0.5" (pill/badge)
- **ALT LINES** dropdown — switches to full alt line ladder in this view
- Bookmark icon (save this prop)
- Trend chart icon (toggle chart view)
- Over / Under toggle with odds shown

**Stat category tabs (horizontal scrollable):**
`STL` | `PTS` | `1Q PTS` | `1H PTS` | `FGM` | `FTM` | `FTA` | `AST` | `1Q AST` | `PTS+AST` | `3PTM` | `3PTA` | `2PTM`

**Time window tabs:** `L5` | `L10` | `L20` | `H2H` | `2025` | `2024`

**Insight card (below tabs):**
- Primary insight text: "Naz Reid has exceeded 0.5 steals in 8 of his last 9 games (1.4 steals/game average). **89%** In the last 9 games"
- Multi-window breakdown: L5=80%, L10=80%, L20=75%, H2H=60%, 2025=67%, 2024=49%
- Average: 1.44 | Median: 1

**Bar chart:** Individual game result bars (green=hit, red=miss) with game dates on x-axis (1/31 @MEM, 2/02 @MEM, 2/04 @TOR, 2/06 @TOR, 2/08 vs LAC, 2/09 vs ATL, 2/11 vs POR, 2/20 vs DAL, 2/24 @POR). Dashed line at the prop threshold (0.5).

**Supporting Stats section:** Minutes (25.9 avg), Fouls (2.4 avg) — contextual data for the prop

**Right panel — Matchup tab (contextual to this prop):**
- **"Key LAC Steals offense"** header — automatically identifies the most relevant defensive stat
- Position opponent filter tabs: `Overall` | `vs PG` | `vs SG` | `vs SF` | `vs PF` | `vs C`
- Opp. Matchup indicator: **Favorable** (green ✅) / Neutral / Unfavorable
- Steals Allowed: 8.9 avg, **21st rank** (LAC is weak at preventing steals = favorable for MIN stealers)
- Team Rankings (2025) side-by-side — same 16-stat table as Match Details Matchup tab

**Key finding:** The prop-level matchup panel auto-identifies the **relevant defensive stat for this specific prop** ("Key LAC Steals offense") and filters the opponent ranking to that stat. This is very close to what Ludi's DVP callout (Phase 8.25) does — but Outlier surfaces it at the individual prop drill-down level, not just in game notes.

### Ludi Actions — Player Prop Detail
| Feature | Ludi Has? | Priority | Notes |
|---------|-----------|----------|-------|
| Per-prop matchup context (auto-identifies relevant defensive stat) | Partial (Phase 8.25 DVP) | 1 | Ludi's `_get_key_advantage_callout()` already does this — expose in Ask Ludi: "tell me about Naz Reid steals" |
| Multi-window hit rate breakdown in one view (L5/L10/L20/H2H/season/prior season) | No | 1 | `player_trends` has L7/L10/L15 — add H2H + prior season to ask_ludi_db.py handlers |
| Game-by-game result bar chart | No | 2 | Phase Infographic V1: "Hit Streak Tracker" chart is this exact feature |
| Position-specific matchup filter (vs PG/SG/SF/PF/C) | No | 2 | `team_dvp_by_archetype` is archetype-based, not position-based. Position filter would require different data |
| Supporting Stats (minutes avg, fouls avg) inline | Partial (foul splits in Module C) | 1 | Surface `player_foul_splits.min_dampener` context in spotlights |

---

## BucketsToBucks.com

**Researched:** February 26, 2026 | Access: Freemium (free tier explored) | URL: buckettobucks.com

### Tier Architecture

| Tier | What You Get |
|------|--------------|
| Free | Schedule page, basic prop table (player/line/odds visible, hit rates blurred), DVP/DVPT sliders functional |
| Pro (paid) | Full hit rate columns, Injury Impact, Correlation Finder, HitStack Parlay Builder |

### Schedule Page (Free)

Date-navigable tabs. Each game card shows:
- Team logos + L10 record (e.g., "14-6 L10")
- L10 Pts + L10 Opp Pts (scoring pace trend)
- "Matchup Details" expand button (opens matchup overlay)

**Key observation:** L10 team scoring averages are surfaced at the game-card level — context before you even look at a prop.

### Player Props Table (Freemium)

**956 props badge** on today's slate. Filter system uses 4 range sliders:
- **DVP slider** (1–30): Filter by team's defensive rank vs position (1=toughest defense, 30=softest)
- **DVPT slider** (1–30): Filter by defensive rank vs play type
- **L10 Hit Rate slider** (0%–100%)
- **Season Hit Rate slider** (0%–100%)

**Column structure per row:**
| Column | Notes |
|--------|-------|
| Proposition | Player + stat + line |
| Line | Numeric line |
| Odds | Multi-book (DK, FD, BetMGM, etc.) |
| Game | Matchup |
| DVP | Defense vs Position rank (1=toughest) |
| DVPT | Defense vs Play Type rank |
| L5 | Hit rate — **blurred (paywall)** |
| L10 | Hit rate — **blurred (paywall)** |
| Season | Hit rate — **blurred (paywall)** |

**Live examples captured:**
- Coby White Over 16.5 Points @ -115 DraftKings
- Jabari Smith Jr., Jordan Oubre, Vit Krejci, Nikola Vucevic in table view

**Key observation:** The dual DVP/DVPT slider system lets users isolate "soft D vs position" AND "soft D vs play type" independently — a more granular filter than Ludi's single `team_dvp_by_archetype` lookup.

### Injury Impact (Paywalled)

Full paywall with copy: "Unlock Injury Impact Analysis / Upgrade to Pro." Shows injured player count badge per matchup card (visible on schedule page) — the detail is locked.

### Correlation Finder (Paywalled)

Description visible before paywall:
> "When a player hits or misses a prop, see how their teammates perform in those same games"

Interface preview: player search → stat dropdown → Over/Under toggle → line input → Find button.

**Key finding:** This is exactly the Phase 8.26 Correlated Props logic Ludi ships — but BucketsToBucks exposes it as a user-facing search tool. Ludi's version auto-flags correlated pairs in curation; their version lets users query it manually.

### HitStack Parlay Builder (Paywalled)

Smart 2–5 leg parlay generator. Copy: "HitStack uses your selected criteria to generate the smartest parlay possible." No additional detail accessible.

### Ludi Actions — BucketsToBucks
| Feature | Ludi Has? | Priority | Notes |
|---------|-----------|----------|-------|
| Dual DVP/DVPT filter sliders | Partial (DVP only) | 2 | Add DVPT (play-type DVP) as separate column in `team_dvp_by_archetype` |
| L10 scoring averages at game-card level | No | 2 | Add to game notes header before prop cards |
| Correlation Finder as user query | Partial (auto-flag in Phase 8.26) | 2 | Ask Ludi: "when X hits, how do teammates do?" → query `player_correlated_trends` |
| Hit rate by position (DVP) at slider level | Partial (internal) | 2 | Expose DVP rank in Telegram bet cards (already in `team_dvp_by_archetype`) |
| HitStack smart parlay builder | No | 3 | Phase 8.26 SGP flagging is the risk version — an "SGP generator" is the positive version |

---

## StraightBettin

**Researched:** February 26, 2026 | Access: Public | URL: straightbettin.com

### Overview

Educational content site built around a single flagship tool: the **NBA On/Off Data Tool** — a player toggle + WOWY comparison interface. Secondary tools: Funnels, NBA Rotations, Opponent Assisted Basket %, Role Tracker.

### On/Off Tool

**URL:** `/research-tools/on-off-tool` (NBA research tools dropdown)

**Controls:**
- Team dropdown (all 30 teams)
- Games slider (default 60 games)
- Date range filter

**Player Toggle Buttons — key UX details:**
- Each player has a toggle (ON/OFF) displayed as a button with name + status pill inline
- Status pills: 🟡 Questionable | 🔴 Out | 🩷 Doubtful — directly on the button, no separate injury sidebar
- **↗ arrow icon** on recently-acquired players (trades + free agent pickups since season start)
- Toggle updates the stats table live (no page reload)

**Main Stats Table columns:**
`MIN | USG% | PTS | REB | AST | 3PM | 3PA | 3P% | FGM | FGA | FG% | TOV | PRA | PR | PA | RA`

**Comparison Delta Table (bottom panel):**
When a player filter is applied (e.g., "Filter: Johnson ON"), a COMPARISON section renders below:
- Header: "COMPARISON: [Player] ON vs Season Stats"
- Same columns, but values = delta from season average
- Color coding: green = better than season avg, red = worse, intensity = magnitude of change
- Legend visible at bottom: "Significant Better / Better / Average / Worse / Significant Worse"

**Live example captured (ATL Hawks, Jalen Johnson ON):**
- Season REB: 8.0 → WITH Johnson: +2.5 (significant green)
- Season AST: 4.5 → WITH Johnson: -1.5 (red)
- This shows Jalen Johnson's presence draws rebounds but depresses assists flow for teammates

**"How to use" helper text** visible below comparison table — educational copy explaining ON/OFF interpretation.

**Key finding:** StraightBettin's injury status pills on the toggle buttons are a UX innovation — you can see "this player is OUT" directly on the button you'd click to remove them from the lineup. No separate injury lookup required. Ludi's `wowy_calculator.py` is the mathematical equivalent but has no UI equivalent.

### Funnels Tool

**URL:** `/research-tools/funnels` (same research tools dropdown)

Pre-ranked **daily matchup cards** for Catch & Shoot props. Two tabs:
- **OVERS** (17 matchups ranked) — best C&S Overs of the day
- **UNDERS** (18 matchups ranked) — best fades

**Each card contains:**
- Rank + Teams (e.g., "#1 Bulls vs Blazers")
- Metric 1: Catch & Shoot FGM Allowed L10 — absolute count + "vs league median" delta (+33%)
- Metric 2: Catch & Shoot FREQ% Allowed L10 — frequency percentage + delta vs median
- Player list: Top C&S shooters on the offensive team with their individual FREQ%

**Live Funnels OVERS examples (Feb 26):**
| Rank | Matchup | C&S Allowed | vs Median | Key Players |
|------|---------|-------------|-----------|-------------|
| #1 | Bulls(14) vs Blazers | +33% | Best | Krejčí 62.1%, Cissoko 55.5%, Camara 52.1%, Grant 43% |
| #3 | Jazz(37.6%) vs Pelicans | +23% | Very Good | Jones, Peavy, Poole, McGowens |
| #4 | Wizards(13) vs Hawks | +24% | Very Good | Hield 100%, Kispert, Landale, Gueye |
| #5 | 76ers(36.5%) vs Heat | +19% | Good | Fontecchio 59.3%, Jakučionis, Jović, Smith |

**Key finding:** The Funnels tool is Ludi's defensive funneling concept (which drives Spot-Up archetype matchups in Module E) turned into a consumer-facing daily feed. The "C&S FREQ% Allowed" metric maps directly to what Ludi's `team_dvp_by_archetype` captures for SNIPER_ELITE archetypes.

### Other Tools (Observed, Not Fully Explored)

- **NBA Rotations** — lineup rotation tracking
- **Opponent Assisted Basket %** — tracks what % of a team's made baskets are assisted (signals ball movement dependency)
- **Role Tracker** — player role changes over time

### Ludi Actions — StraightBettin
| Feature | Ludi Has? | Priority | Notes |
|---------|-----------|----------|-------|
| Injury status on player toggle button (inline) | No UI | 2 | When Ask Ludi "who should I add if Player X is out?" — return status inline with name |
| ↗ trade/acquisition flag on player toggle | No | 2 | Ludi has `player_game_logs.team_abbreviation` for trade detection — surface in Ask Ludi responses |
| WOWY comparison delta table (vs season avg) | Partial (internal in `wowy_calculator.py`) | 1 | Ask Ludi: "who benefits if Tatum is out?" → return delta table format (name + PTS delta) |
| Funnels feed (C&S matchups ranked daily) | Partial (Module E has C&S logic) | 2 | Surface top C&S matchups as a section in morning brief's game notes — already have data in `team_dvp_by_archetype` |
| Opponent Assisted Basket % tracking | No | 3 | Interesting signal for ball-movement teams — lower priority |
| Color-coded delta by magnitude (significant/avg/worse) | No (text only) | 2 | Ludi Lens Infographic phase: use in Matchup Edge Heatmap chart |

---

## Action Network — Props & Public Betting

**Researched:** February 26, 2026 | Access: Public (free tier) | URL: actionnetwork.com

### Nav Structure (Sport-Level)

| Section | URL | Tier | Description |
|---------|-----|------|-------------|
| Signals | `/nba/sharp-report` | Free/Pro | Formerly "PRO Report" — sharp money alerts |
| Public Betting | `/nba/public-betting` | Free (1 game) / Pro | % of bets + % of money + DIFF |
| Game Projections | `/nba/projections` | Free/Pro | Game-level projections |
| Prop Projections | `/nba/prop-projections` | Mostly Pro | PRO Top Props table |

### Props Section (Expert Picks Feed)

**URL:** `/nba/picks`

**Page:** Expert picks feed, filtered by today's games (tabs: CHA=5 picks, MIA=3, WAS=1, HOU=1).

**Expert card format:**
- Expert name + 30-day record: `W-L-Push` + `+/- units`
- Pick: player name + prop + line + Over/Under
- No odds shown at pick level (links to sportsbook for final odds)

**Live examples captured:**
| Expert | Record | Pick |
|--------|--------|------|
| The Propfessor | 40-43-0 (+4.4u) | — |
| Markus Markets | 28-19-1 (+7.0u) | — |
| Sandy Plashkes | 45-31-5 (+9.7u) | A.Nembhard u17.5 Pts |
| Buckets Podcast | 75-61-4 (+3.8u) | M.Diabate o1.5 Ast |
| Bryan Fonseca | 28-31-1 (-4.3u) | — |

**Prop category sidebar:**
Game Props | Points | Rebounds | Assists | 3pt | Stat Combos | Offensive | Defensive | **Alt Points | Alt Reb | Alt Ast | Alt 3s**

**Key observation:** Alt lines are first-class filter categories in Action Network's prop sidebar — not buried under an "expand" toggle. Users can browse "Alt Points" as its own section directly.

**Right sidebar:** Sportsbook reviews (bet365, Fanatics, BetMGM, DK, Caesars, theScore, Fliff, Kalshi, BetRivers, Underdog — 10+ books listed). Action Network monetizes through affiliate sportsbook reviews.

### Public Betting Page

**URL:** `/public-betting` (global) or `/nba/public-betting` (sport-specific)

**Page title:** "Public Betting & Money Percentages"

**Column structure:**
| Column | Description |
|--------|-------------|
| SCHEDULED | Game time + teams |
| OPEN | Opening spread |
| BEST ODDS | Best current spread + juice |
| % OF BETS | Public ticket percentage |
| % OF MONEY | Dollar-weighted percentage |
| DIFF | % of Money minus % of Bets (sharp lean indicator) |
| BETS | Total ticket count |

**Free tier access:** 1 game visible (top of list), all remaining games paywalled behind "Unlock all money percentages with Action PRO."

**Live example — CHA @ IND (Feb 26, 7:00 PM):**
| Side | % Bets | % Money | DIFF | Total Bets |
|------|--------|---------|------|-----------|
| Hornets | 57% | 67% | **+10%** | 7,502 total |
| Pacers | 43% | 33% | -10% | — |

**DIFF interpretation:** +10% means money% > bets% — sharp money leans toward Hornets despite being spread favorites (vs. public who are on Hornets by count too). Both signals agree here — but when DIFF is opposite sign from bet%, that's the true sharp vs. square divergence signal.

**Paywall upsell copy:** "Unlock all money percentages and more premium betting tools with Action PRO."

### Prop Projections Page

**URL:** `/nba/prop-projections`

**Page:** "PRO Top Props" table with columns: `PLAYER | PICK | PRO | ODDS | EDGE`

| Column | Description |
|--------|-------------|
| PLAYER | Name + team logo + game context |
| PICK | Over/Under + stat category |
| PRO | Composite PRO score (higher = stronger signal) |
| ODDS | Best book line + book logo |
| EDGE | Edge % vs fair line |

**Free tier:** 1 row visible. All others locked.

**Live example — J.Kuminga (WAS @ ATL, 7:30 PM):**
- Pick: **Under Pts**
- PRO Score: **12.04**
- Odds: u18.5 -104 Caesars
- Edge: **45.2%**

**Key observation:** Action Network separates `PRO` (composite rank score) from `EDGE` (probability edge %). Ludi currently only surfaces edge%. The PRO score appears to be a composite of edge + model confidence + sample size — functionally similar to what a "Ludi Confidence Score" would be.

### Ludi Actions — Action Network
| Feature | Ludi Has? | Priority | Notes |
|---------|-----------|----------|-------|
| % of Bets + % of Money displayed separately | No | 1 | Phase 8.22 captures both — also add to morning brief card output |
| DIFF column (Money% - Bets%) as sharp lean indicator | No | 1 | Trivial to compute once both fields captured in `social_signals` |
| Alt lines as first-class sidebar filter category | No | 2 | Module F alt line sweep (Tier 1 roadmap) — once built, expose in Ask Ludi as "alt lines" filter |
| Expert picks feed with verified 30d P&L | No | 3 | Future Ludi Lens "Ludi Experts" section — post Phase 8 |
| Composite score (PRO score) separate from Edge% | No | 2 | Add "Ludi Confidence Score" = edge + hit_rate_l10 + expected_minutes confidence composite |

---

## PropsMadness

**Researched:** February 26, 2026 | Access: Freemium (free tier explored) | URL: propsmadness.com

### Overview

Playtype-and-zone analytics platform. Core features: main player page (shooting zones, defensive matchup, similar players), **Check My Prop** scorecard, and **By Position** tab. Designed as a prop research tool, not a prop betting aggregator.

### Main Player Page

On landing, search finds any player prop. Main page shows:
- Player headshot + team + opponent + game time
- Active prop: Over/Under + line + odds + book logo
- Left panel: Shot zone visual (C&S vs midrange vs rim)
- Tabs: **By PM** | **By Position** — switches similar-player comparison method

### By Position Tab

**Content:** "Similar Players Hit Rate" comparison table, filtered by position. Columns:
- Player name
- L10 hit rate at the current prop line
- Color bar (green/red)

**Opp Defense toggle:** Switches the visual from offensive shooting zones to opponent's defensive zone breakdown (what zones they give up most).

### Check My Prop Feature (a.k.a. "Ask My Player")

**URL trigger:** "Check My Prop" button or search bar on `propsmadness.com/checkmyprop`

Generates a **standalone prop scorecard** for any player × stat × line. Contains 11 data rows in a two-column table (Metric | Value):

| Row | Metric | Luka Example (Over 30.5 Pts @ -107 DK, Feb 26) |
|-----|--------|------------------------------------------------|
| 1 | L15 Average | 30.3 |
| 2 | L15 Hit Rate | 7/15 |
| 3 | H2H (last 2 seasons) | 6/8 |
| 4 | Similar Players Hit Rate (by PM) | 3/4 |
| 5 | Opp D-Rank vs P&R Ball Handler (DPT) | 5th |
| 6 | Opp D-Rank vs Above the Break 3 (DSZ) | 2nd |
| 7 | Opp DefRtg | 9th |
| 8 | Opp D-Rank vs Position | 8th |
| 9 | Similar Players Hit Rate (by Position) | 6/14 |
| 10 | Expected Minutes | 31–41 |
| 11 | L15 Avg Minutes | 33.8 |

**Right column:** Overall % score — **47%** for this Luka prop.

**Bottom buttons:**
- **Copy Image** — shareable social card (the whole scorecard as a JPEG)
- **Deep Dive** — returns to main player page with `?from=checkmyprop` param
- **Surprise Me** — loads a random player prop (dice animation, React loading state)

**Attribution footer:** `propsmadness.com/checkmyprop`

**Key finding:** Row 5 (DPT = Defensive Play Type rank vs P&R Ball Handler) and Row 6 (DSZ = Defensive Shot Zone rank vs Above-the-Break 3) are the most unique data points here. These map directly to what Ludi's `team_dvp_by_archetype` and Phase 8.25 DVP callout already capture — but PropsMadness surfaces them in a clean consumer-facing scorecard. The **11-row scorecard format** with an **overall % score** is the key UX innovation.

**Paywall signal:** "More insights on this player — free today" footer on the card — suggests some rows may be gated on non-free days.

### Ludi Actions — PropsMadness
| Feature | Ludi Has? | Priority | Notes |
|---------|-----------|----------|-------|
| 11-row prop scorecard (L15/H2H/DPT/DSZ/Minutes) | Partial (bet card has L15 + matchup) | 1 | **Ask Ludi: "Check Luka over 30.5"** → return PropsMadness-style scorecard from `player_trends` + `team_dvp_by_archetype` + `player_foul_splits` |
| Overall % score per prop (composite) | No | 2 | Extend "Ludi Confidence Score" concept (see Action Network findings above) |
| DPT (Defensive Play Type rank) | Partial (`team_dvp_by_archetype` by archetype) | 1 | Map archetypes → play types for DPT lookup — same data, different presentation key |
| DSZ (Defensive Shot Zone rank) | No | 2 | Would need zone-specific defensive data (PBP Stats or similar) |
| "Similar Players" hit rate (by PM archetype + by position) | No | 2 | `player_type_profiles` has archetype — compute hit rate for same-archetype players vs same opponent |
| Shareable social card (Copy Image) | No | 2 | Phase Infographic V1 — the "Hit Streak Tracker" chart can be exported as JPEG for Telegram sharing |
| "Surprise Me" random prop button | No | 3 | Fun UX — irrelevant for Ludi's analytics-first positioning |

---

## Cross-Platform UX Patterns

### Patterns Observed (All 6 Platforms)

| Pattern | OddsJam | Outlier | BucketsToBucks | StraightBettin | Action Network | PropsMadness | Ludi Has? | Action |
|---------|---------|---------|----------------|----------------|----------------|--------------|-----------|--------|
| EV% / Edge as primary metric | ✅ | ✅ (EV+ badge) | ❌ | ❌ | ✅ (Edge% col) | ❌ | ✅ | Already done |
| Plain-English trend narrative | ❌ | ✅ (1700+/day) | ❌ | ❌ | ❌ | ❌ | Partial (Spotlights) | Extend via Ask Ludi |
| Alt line ladder per player | ❌ (flat) | ✅ | ❌ | ❌ | ✅ (filter cat.) | ❌ | ❌ | Module F Tier 1 |
| Public bet % of bets | ❌ | ✅ | ❌ | ❌ | ✅ | ❌ | ❌ | Phase 8.22 |
| Public bet % of money | ❌ | ✅ | ❌ | ❌ | ✅ | ❌ | ❌ | Phase 8.22 — add `pct_money` |
| Sharp lean DIFF (money% − bets%) | ❌ | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ | Trivial once both fields captured |
| Injury status inline (timestamp) | ❌ | ✅ | ❌ | ✅ (pills) | ❌ | ❌ | Partial (DB only) | Surface `snapshot_time` in cards |
| DVP / Defensive rank display | ❌ | ✅ (16 stats) | ✅ (2 sliders) | Partial (Funnels) | ❌ | ✅ (DPT/DSZ) | Partial (`team_dvp_by_archetype`) | Add rank column + surface in cards |
| WOWY / On/Off toggle | ❌ | ❌ | ❌ | ✅ (flagship) | ❌ | ❌ | ✅ (`wowy_calculator.py`) | Expose in Ask Ludi replies |
| Defensive funneling (C&S matchups) | ❌ | ❌ | ❌ | ✅ (Funnels) | ❌ | ✅ (DSZ zones) | ✅ (Module E internal) | Surface top C&S matchups in brief |
| Composite score (PRO / overall%) | ❌ | ❌ | ❌ | ❌ | ✅ (PRO score) | ✅ (47% overall) | ❌ | Add "Ludi Confidence Score" |
| Similar players hit rate | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ (by PM + position) | Partial (`player_type_profiles`) | Ask Ludi: "similar players to X tonight" |
| Correlated prop finder | ❌ | ❌ | ✅ (paywalled) | ❌ | ❌ | ❌ | ✅ (Phase 8.26 auto-flag) | Expose as Ask Ludi query |
| Shareable social card (JPEG export) | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ (Copy Image) | ❌ | Phase Infographic V1 |
| Liquidity display | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | Check Odds API endpoint |
| Trending parlay feed | ❌ | ✅ (Popular) | ❌ | ❌ | ❌ | ❌ | ❌ | Low priority — herd signal |
| Multi-sport | ✅ | ✅ | ❌ | ❌ | ✅ | ✅ | ❌ | Out of scope |

### Key UX Differentiation

**OddsJam's edge:** Live liquidity column, real-time auto-refresh, 1-click BET routing to book. Quantitative/trader-style UX.

**Outlier's edge:** Narrative-first Insights feed, Match Details with 3 right-panel tabs, alt line ladder with per-line EV+ badges, social proof via Popular/trending parlays. Consumer-facing UX.

**BucketsToBucks's edge:** Dual DVP/DVPT slider filter system. Correlation Finder concept. L10 team scoring at game-card level.

**StraightBettin's edge:** WOWY On/Off tool with injury status pills inline on toggle buttons. Funnels daily C&S matchup cards. Most transparent about defensive data methodology.

**Action Network's edge:** Public Betting page with % of Bets + % of Money + DIFF (sharp lean). Expert picks feed with verified 30-day P&L. Alt lines as first-class filter category.

**PropsMadness's edge:** 11-row Check My Prop scorecard (L15 + H2H + DPT + DSZ + expected minutes + similar player hit rates). Overall % composite score. Shareable social card.

**Ludi's differentiation:** Monte Carlo projections (not just hit rate), Usage Vacuum redistribution, Foul Intelligence (min dampener), archetype-vs-scheme matchup context (15 archetypes × 5 schemes). No competitor surfaces Usage Vacuum or Foul Intelligence.

---

## Feature Gap Analysis

| Feature | OddsJam | Outlier | BucketsToBucks | StraightBettin | Action Network | PropsMadness | Ludi Has? | Priority | Ludi Action |
|---------|---------|---------|----------------|----------------|----------------|--------------|-----------|----------|-------------|
| Alt line edge sweep | ❌ | ✅ | ❌ | ❌ | ✅ (filter) | ❌ | ❌ | **1** | Module F sweeps ±1.5/±3.0 alt lines per player |
| Hit rate at specific alt line | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | **1** | Extend `player_trends` hit rate to alt lines |
| EV+ on specific alt lines | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | **1** | Module F alt line edge calculation |
| Public bet % of money (not just bets) | ❌ | ✅ | ❌ | ❌ | ✅ | ❌ | ❌ | **1** | Add `pct_money` to Phase 8.22 `social_signals` |
| Sharp lean DIFF (money% − bets%) | ❌ | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ | **1** | Compute in `social_signals` — surface in curate logic |
| Injury timestamp in output cards | ❌ | ✅ | ❌ | ✅ (pills) | ❌ | ❌ | ✅ (DB) | **1** | Surface `player_injuries.snapshot_time` in Telegram cards |
| WOWY beneficiary reply (Ask Ludi) | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ | ✅ (internal) | **1** | Ask Ludi: "who benefits if X is out?" → delta table |
| 11-row prop scorecard (Check My Prop pattern) | ❌ | Partial | ❌ | ❌ | ❌ | ✅ | ❌ | **1** | Ask Ludi: "check [player] [line]" → scorecard reply |
| Team rankings with league ranks | ❌ | ✅ | Partial | ❌ | ❌ | ✅ (DPT/DSZ) | Partial | **1** | Add `rank` column to `team_dvp_by_archetype` |
| C&S Funnels (daily ranked matchup cards) | ❌ | ❌ | ❌ | ✅ | ❌ | ✅ | ✅ (internal) | **2** | Surface top 3 C&S matchups in morning brief header |
| Composite prop score (PRO / Ludi score) | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ | ❌ | **2** | "Ludi Confidence Score" = edge + L10_hit + minutes_conf |
| Plain-English trend feed (all games) | ❌ | ✅ (1700+) | ❌ | ❌ | ❌ | ❌ | Partial (3-5/game) | **2** | Ask Ludi: "show trends for tonight" → `player_trends` query |
| Quarter/half split props + insights | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | **2** | Extend trend engine to H1/Q1 (BDL has H1 data) |
| Combo props (P+A, P+R) in insights | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | **2** | Add P+A / P+R to `player_trends` tracked stats |
| Shareable social card (JPEG export) | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ | ❌ | **2** | Phase Infographic V1 — "Hit Streak Tracker" → JPEG |
| Match Details 3-tab right panel | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | **2** | Ludi Lens MVP design pattern |
| Positive EV feed (cross-book) | ✅ | ✅ (Pro) | ❌ | ❌ | ✅ | ❌ | ✅ | ✅ | Already done |
| Kelly sizing | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ | Already done |
| Correlated prop finder (user query) | ❌ | ❌ | ✅ (paywall) | ❌ | ❌ | ❌ | ✅ (auto-flag) | **2** | Ask Ludi: "when X hits, how do teammates do?" |
| Liquidity column | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | 3 | Check Odds API for liquidity endpoint |
| Trending parlay feed (social) | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | 3 | Phase 8.22 — low weight in Prop Pulse Score |
| Arbitrage detection | ✅ | ✅ (Pro) | ❌ | ❌ | ❌ | ❌ | ❌ | 3 | Future: cross-book arb on NC Legal books |
| Multi-sport coverage | ✅ | ✅ | ❌ | ❌ | ✅ | ✅ | ❌ | Out of scope | NBA-only per product strategy |

---

## Ask Ludi Bot UI Inspiration

**From Outlier Insights feed:**
- **Pattern**: "Show me all players trending over their line tonight" → query `player_trends` WHERE hit_rate_l10 >= 70% and game is tonight → return ranked list
- **Pattern**: "What's the best alt line for Jayson Tatum tonight?" → sweep alt lines from Odds API, calculate edge at each, return top 2-3
- **Pattern**: "Who's injured for tonight?" → query `player_injuries` WHERE game is tonight and status IN (OUT, DOUBTFUL) → Lineup tab format (name + injury + timestamp)

**From Outlier Match Details right panel (3-tab pattern):**
- For per-game queries ("Tell me about Lakers-Warriors tonight"), Ask Ludi could return:
  1. **Matchup** — DVP ranks, archetype-scheme context
  2. **Lineup** — starters + injury status
  3. **Edges** — top 3 props with hit rate + edge%

**From Outlier Popular:**
- "What are people betting on tonight?" → query public bet% from Phase 8.22 `social_signals` → return inverse (fade the crowd) + model alignment

**From PropsMadness Check My Prop (11-row scorecard):**
- **Pattern**: "Check Luka over 30.5" → `ask_ludi_db.py` `edges` intent → query: L15 avg, L15 hit rate, H2H (last 2 seasons), archetype DVP rank, DefRtg rank, expected minutes, similar-archetype player hit rates → return scorecard block
- **Template**: `[Player] [Over/Under] [Line]: L15 avg {avg} | L15 hit {X}/15 | H2H {X}/{Y} | DVP rank {N}th | Minutes {lo}-{hi} | Score: {overall}%`

**From StraightBettin On/Off tool (WOWY delta):**
- **Pattern**: "Who steps up if LeBron is out?" → `ask_ludi_db.py` `injuries` intent → `wowy_calculator.find_beneficiaries(conn, 'LeBron James')` → return top 3 beneficiaries with `+PTS_delta / +USG%_delta` format
- Injury status context: include `player_injuries.status + snapshot_time` inline — "OUT (updated 5:18 PM)"

**From Action Network DIFF column (sharp lean):**
- **Pattern**: "What's sharp money on tonight?" → query `social_signals` WHERE pct_money > pct_bets + 10 (positive DIFF) → return "Sharp: [Team] — {pct_money}% money vs {pct_bets}% tickets" per game

---

## Implementation Roadmap

### Tier 1 — High Impact, Buildable Now (0–4 weeks)

| Item | Source Platform | What to Build | Files Affected | Cost |
|------|----------------|--------------|----------------|------|
| **Alt line edge sweep** | OddsJam + Outlier + AN | Module F sweeps ±1.5/±3.0 alt lines per player. Surface best-value alt line in bet card. | `module_f.py`, `module_a.py` | $0 |
| **Hit rate at alt lines** | Outlier | Extend `player_trends` tracking to capture hit rate at -1.5/+1.5 from main line | `scripts/sync_player_trends.py` | $0 |
| **Injury timestamp in cards** | Outlier + StraightBettin | Surface `player_injuries.snapshot_time` in morning brief — e.g. "OUT (updated 5:18 PM)" | `morning_brief.py` | $0 |
| **Ask Ludi trend query** | Outlier | "show trends tonight" → `player_trends` WHERE hit_rate_l10 >= 70 AND game tonight → ranked reply | `bots/ask_ludi_db.py` | ~$0.001/query |
| **Public bet % of money** | Outlier + Action Network | Add `pct_money` field to Phase 8.22 `social_signals`. Compute DIFF (money%-bets%) as sharp lean signal. | `docs/projects/SOCIAL_INTELLIGENCE_SYSTEM.md`, Phase 8.22 | ~$0/day |
| **Ask Ludi: "Check [player] [line]"** | PropsMadness | `edges` intent handler → query L15 avg/hit/H2H/DVP rank/minutes/similar players → return 11-row scorecard block | `bots/ask_ludi_db.py` | ~$0.001/query |
| **Ask Ludi: "Who benefits if X is out?"** | StraightBettin | `injuries` intent → `wowy_calculator.find_beneficiaries()` → return top 3 with PTS/USG delta | `bots/ask_ludi_db.py` | ~$0.001/query |

### Tier 2 — Medium Term (1–2 months)

| Item | What to Build | Files Affected | Cost |
|------|--------------|----------------|------|
| **League rank columns in DVP** | Add `rank` and `league_avg` to `team_dvp_by_archetype` — enables "T25th in 3-Point %" displays | `scripts/sync_dvp_rankings.py`, `database.py` | $0 |
| **H1 split trends** | Extend `player_trends` to track L10 hit rate for H1 props (BDL already has H1 stats) | `scripts/sync_player_trends.py` | $0 |
| **Combo prop tracking (P+A, P+R)** | Add P+A and P+R to `player_trends` stat categories | `scripts/sync_player_trends.py` | $0 |
| **Ludi Lens Match Details panel** | 3-tab right panel (Matchup / Lineup / Edge) as the core Match Details UX for Ludi Lens | `app.py` (future Streamlit) | $0 |

### Tier 3 — Future / Low Priority

| Item | Notes |
|------|-------|
| Liquidity column | Check if Odds API exposes liquidity endpoint. If yes, easy add to Module A. |
| Trending parlay feed | Social proof signal — only relevant once Ludi Lens is user-facing |
| Multi-book arbitrage | ROADMAP item already; NC Legal books only |
| Quarter (Q1) split tracking | After H1 split is validated — smaller sample sizes, noisier signal |

---

## Ludi Actions Summary

**Top 8 actionable takeaways from this research sprint (all 6 platforms):**

1. **Alt line sweep in Module F** — Both OddsJam and Outlier surface EV at alt lines, not just the main line. Action Network makes alt lines a first-class filter category. Ludi calculates edge only at the main line. Adding a ±1.5/±3.0 alt line sweep to Module F would surface more opportunities with no new API cost. *(ROADMAP Tier 1)*

2. **Public betting % of money, not just % of bets** — Both Outlier and Action Network show `% of bets` + `% of money` as separate columns. Action Network's DIFF column (money% − bets%) is the sharpest signal — when money% > bets%, whales (sharps) are loading the side beyond the ticket count. Phase 8.22 must capture both fields. *(ROADMAP Tier 1)*

3. **Injury timestamp in cards** — Outlier's Lineup tab shows "Out (Feb 25 5:18 PM)". StraightBettin shows injury status inline on player toggle buttons. Ludi's `player_injuries.snapshot_time` already stores this — one-line change in `morning_brief.py`. *(ROADMAP Tier 1)*

4. **Ask Ludi: "Check [Player] [Line]" → PropsMadness-style scorecard** — PropsMadness's Check My Prop 11-row scorecard (L15 avg, L15 hit rate, H2H, DPT rank, DSZ rank, expected minutes, similar player hit rates) is exactly what Ask Ludi Phase 8.13 can return from existing `player_trends` + `team_dvp_by_archetype` + `player_foul_splits` tables. Zero new data required. *(Phase 8.13 intent handler)*

5. **Ask Ludi: "Who benefits if X is out?" → WOWY delta reply** — StraightBettin's On/Off comparison delta table (with color-coded magnitude) is Ludi's `wowy_calculator.py` in UX form. The Phase 8.13 `ask_ludi_db.py` `injuries` intent handler should return a delta table format: `[Player: +PTS_delta / +USG%_delta]` from `find_beneficiaries()`. *(Phase 8.13 intent handler)*

6. **Outlier's Insights feed is Ludi's Spotlights at scale** — 1700+ trend cards daily vs Ludi's 3-5 per game. Ask Ludi closes this gap: "show me best trends tonight" → `player_trends` WHERE hit_rate_l10 >= 70 AND game tonight → ranked reply. Zero Claude calls, zero API cost. *(Phase 8.13 intent handler)*

7. **Team Rankings with league ranks is the standard** — Outlier, BucketsToBucks (DVP/DVPT sliders), and PropsMadness (DPT/DSZ rows) all surface defensive rank numbers. Ludi's `team_dvp_by_archetype` has per-100 possession stats but no rank column. Adding `rank INTEGER` and computing `RANK() OVER (ORDER BY pts_vs_baseline DESC)` per archetype would complete the matchup picture. *(Medium term: `scripts/sync_dvp_rankings.py`)*

8. **C&S Funnels / Defensive Funneling as a daily card** — StraightBettin's Funnels tool (pre-ranked C&S matchup cards with league median delta) and PropsMadness's DSZ zone data confirm that Catch & Shoot funneling is a standard consumer-facing feature. Ludi already computes this internally in Module E for SNIPER_ELITE archetypes. Surface the top 3 C&S matchups of the day as a header card in the morning brief. *(Quick win: `morning_brief.py` one new section)*
