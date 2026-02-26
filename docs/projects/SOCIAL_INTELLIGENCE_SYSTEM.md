# Social Intelligence System
## Market Research, Architecture Plan & Competitive Reverse Engineering

**Created:** February 24, 2026 — 7:48 PM EST
**Updated:** February 24, 2026 — 8:15 PM EST (OpenClaw architecture patterns integrated)
**Status:** Research Complete — Architecture Defined — Ready to Build

---

## Table of Contents

1. [What This Is](#what-this-is)
2. [Market Landscape Research](#market-landscape-research)
3. [Professional Market Viability Audit](#professional-market-viability-audit)
4. [DraftKings NBA Player Pulse — Competitive Intel](#draftkings-nba-player-pulse--competitive-intel)
5. [The Social Intelligence Concept](#the-social-intelligence-concept)
6. [Discord Strategy & Setup](#discord-strategy--setup)
7. [Multi-Agent Team Architecture](#multi-agent-team-architecture)
8. [Market Intelligence Agent](#market-intelligence-agent)
9. [Competitor Reverse Engineering](#competitor-reverse-engineering)
10. [The Prop Pulse Score — Composite Data Model](#the-prop-pulse-score--composite-data-model)
11. [Smart Signal Trigger Conditions](#smart-signal-trigger-conditions)
12. [The BERT / Haiku Modeling Approach](#the-bert--haiku-modeling-approach)
13. [Next Steps & Decision Points](#next-steps--decision-points)

---

## What This Is

A full research and architecture sprint covering:
- Competitive analysis of 8 sports betting YouTube channels
- Professional viability audit of the Ludi brand and content strategy
- Reverse engineering of LunarCrush, Outlier.bet, Rithmm, and Action Network
- A complete multi-agent system design for social intelligence as a model input layer

**The core thesis:** Social sentiment + line movement data creates signals that the model alone cannot see. When the model finds edge that the public hasn't spotted yet, that is the highest-confidence play available. This system detects exactly that condition.

---

## Market Landscape Research

### YouTube Channel Competitive Map

| Channel | Size | Format | Tone | Signal Quality |
|---------|------|--------|------|----------------|
| **Unabated** (Captain Jack Andrews) | ~26K subs | Education + tools | Professional, analytical | Highest — closest analog to Ludi brand |
| **OddsJam** | 131K subs | Tool demos + tutorials | Educational | High — acquired for ~$80-160M |
| **Calling Our Shot** | ~200K subs | Daily picks | Transparent, straight-talking | Medium — personality-driven |
| **Jay Money** | ~24K subs | NBA picks only | Focused | Medium |
| Land Your Bets | Invisible in search | Unknown | Unknown | Low signal |
| Daft Previews | Invisible in search | Unknown | Unknown | Low signal |
| Straight Bettin | Invisible in search | Unknown | Unknown | Low signal |
| Guy Boston Sports | Invisible in search | Unknown | Unknown | Low signal |
| PipsNBA | Invisible in search | NBA props | Unknown | Low signal |
| 925 Sports | Invisible in search | Unknown | Unknown | Low signal |
| MySpariPicks/Edge | Small | +EV tools, PrizePicks | Data-driven | Medium — Patreon model |

**Key finding:** Six of the eight channels researched are effectively invisible to search engines. The sports betting content graveyard is enormous and silent. Breaking through requires either significant production investment, an existing audience to transfer, or a genuine and publicly verifiable information edge.

### The Real Market Structure

Three distinct tiers, rarely overlapping:

- **Top tier:** OddsJam, Action Network, WagerTalk TV — SaaS tools + affiliate + media at scale
- **Mid tier:** Unabated, Calling Our Shot — education + subscription, sharp-leaning audiences
- **Long tail:** Hundreds of channels that never break through

**Unabated is the ceiling, not the floor** for the "professional, data-driven, no gambling slang" positioning. They have verifiable 20+ year professional credentials and built to ~26K subscribers over years. That is the size of this audience segment.

---

## Professional Market Viability Audit

### Summary Ratings

| Dimension | Rating | Notes |
|-----------|--------|-------|
| Technical differentiation | ✅ Strong | Monte Carlo, devigging, CLV, injury intelligence — genuinely rare |
| Brand positioning clarity | ⚠️ Risk | "Pour/toast/frosty" iconography contradicts "professional asset management" voice |
| Differentiation from Unabated | ⚠️ Risk | Unabated owns this lane with verifiable credentials |
| Twitter automation first | ❌ Wrong sequencing | Automation amplifies what you already have. Zero trust → efficiently distributes zero trust |
| Monetization pathway | ❌ Undefined | Brand positioning rejects affiliate + picks selling — commits to hardest path (SaaS) without a product |
| Content gap opportunity | ✅ Real | Methodology-forward content with live model genuinely absent at quality |
| Credibility / trust foundation | ❌ Critical gap | No public track record = no starting point for audience trust |
| Long-term viability as SaaS | ⚠️ Risk | Viable but requires significant resource commitment |

### Critical Issues Identified

1. **No public track record.** The claimed +292u / 55.7% WR is in ludi.db. To an external audience this is indistinguishable from fabricated numbers. Every competitor makes unverified claims.

2. **Brand contradiction.** "Professional, tactical, asset management" voice + "pour, toast, frosty, IYKYK" iconography target two completely different audiences and fully resonate with neither.

3. **Old "Front Office War Room" tagline was a broken metaphor** — NBA front offices don't bet against the house. ✅ Resolved: replaced with *"The Edge, Magnified — NBA Player Props Analytics | AI-Driven | Always On"*. Line 1 on premium surfaces; Line 2 on GitHub/README/social bios.

4. **Automation before trust is backwards.** Right sequence: track record public → methodology content → persona → platform → audience → then automation infrastructure.

5. **Monetization undefined.** The brand rejects the two easiest paths (affiliate, picks). That commits to SaaS — which requires engineering investment and a public-facing product.

### The Correct Positioning Frame (Discovered via DK Research)

> "The Edge, Magnified — the level of analysis the house doesn't want you to have access to."

This frame:
- Creates a natural enemy (the sportsbook producing their own biased content)
- Defines value clearly (independence + no conflict of interest)
- DraftKings structurally cannot co-opt it — they ARE the house
- "The Edge" maps directly to the core math concept (devigging, true edge %)
- "Magnified" connects to the Ludi Lens product name

### The Right Sequence Before Building Content Infrastructure

1. Publish the track record publicly — CapperTek or a public spreadsheet, 60-90 days
2. Lead with methodology education (devigging tutorials, stat confidence framework, CLV)
3. The brand needs a person or consistent persona — not just "Ludi Informatio"
4. Resolve the brand contradiction — kill either the celebration iconography OR the professional voice
5. Define the product (SaaS tool? picks subscription? education?) BEFORE building the funnel
6. If Twitter, then personality and real-time takes — not scheduled model output posts

---

## DraftKings NBA Player Pulse — Competitive Intel

**What it is:** DraftKings' own analyst-led NBA props content operation, published daily inside their social platform.

- 100,000+ member groups inside the DK app
- Daily cadence — every single NBA game day
- Analyst: Garion Thorne (DK Network staff)
- Format: ~165 words, "Most Bet Player Prop" tool highlights trending picks
- Mechanic: One-click tail/fade → direct bet slip integration
- Media arm: `dknetwork.draftkings.com` publishes transcripts daily

**The conflict of interest disclosure buried in every post:**
> *"DraftKings promoters may sometimes play on personal accounts in the games that advice is offered on."*

Their analysts may be betting against the picks they publish. This is a retention and engagement tool, not an analytical service. DraftKings wins when you bet more — not when you win.

**What this means for Ludi:**
- DraftKings' content is structurally biased — they profit from your losses
- Their analysis is popularity-driven ("most bet"), not edge-driven
- 165-word analysis vs. full Monte Carlo pipeline = enormous quality gap they cannot close
- The "Edge, Magnified" positioning is directly defensible against this — DK quantifies nothing

**DraftKings Social as a distribution channel:** 100K+ members in a single NBA props group with direct bet-slip integration. No equivalent engagement density exists on Twitter or YouTube for NBA props. Worth studying whether Ludi content is postable in similar groups as a member.

---

## The Social Intelligence Concept

### The Core Signal

Social sentiment alone tells you what the public *thinks*.
Line movement tells you what the market *did*.
**The gap between those two is where the real signal lives.**

### The LunarCrush Blueprint (Applied to NBA Props)

LunarCrush built social intelligence for crypto:
- Monitors Twitter, Reddit, YouTube, Discord at scale
- Normalizes everything into a composite "Galaxy Score" (0-100)
- Feeds social metrics alongside price/volume data
- Detects when something is overhyped (fade) vs. undernoticed (lean in)

The translation to NBA player props is almost direct:
- "Price" → line movement
- "Asset" → player/prop combination
- "Social volume spike" → public attention before bets are placed

### Why This Is the Leading Indicator

By the time Action Network shows 80% public on an OVER, the line has already moved. Social discussion happens *before* the bets get placed. Monitoring what people are *talking about* is the leading edge of where the line will move next.

---

## Discord Strategy & Setup

### The Personal Token Warning

Using a personal Discord user token to automate reading is **selfbotting** — explicitly against Discord's ToS. Risk: account ban on your main account, losing VIP standing in groups you've built over time. **Do not do this.**

### The Clean Path: Dedicated Lurker Account

| Approach | ToS Safe | Access | Automation |
|----------|----------|--------|------------|
| Personal user token | ❌ Risk | Full | Possible but dangerous |
| Official bot invite | ✅ Yes | Admin-approved only | Full |
| **Dedicated user account** | ✅ Gray area (low risk) | Manual verify once | Safe after setup |
| Screenshot → Vision pipeline | ✅ Yes | Full (your judgment filter) | Semi-manual |

**Recommended approach:**
1. Create a dedicated Discord account (neutral name, not affiliated with Ludi)
2. Manually join each target server using regular invite links
3. Manually pass each verification gate (reaction click, captcha, button) — one time
4. From that point, the account token has full read access to all verified channels
5. Automated data collection runs against this token — not your main account
6. If it ever gets flagged: lose the data account, not your community presence

### Channel Evaluation Framework

When reviewing your Discord channels to identify high-signal sources:

**Keep (High Signal):**
- Props discussion with stat context or reasoning — not just "I love this play"
- People posting their actual record / tracking history
- Discussion of line movement, injuries affecting specific props
- Disagreement and debate (means people are thinking, not hyping)
- Consistent contributors you recognize by name across time

**Cut (Low Signal):**
- General hype / pump posts with no reasoning
- Parlay posting (not useful for individual prop analysis)
- Off-topic sports chat
- Channels primarily used by server owner to promote Patreon/picks service

**Also note per channel:**
- Approximate posts per day
- NBA-specific or all sports mixed
- Whether post-game result tracking exists (gold for calibrating who to weight higher)

### The Screenshot → Vision Pipeline

For VIP or high-signal channels where a bot isn't appropriate:
1. You (or a lightweight local script with permission) saves screenshots to a watched folder
2. A processing agent picks them up, runs through Claude Vision
3. Extracts: player names, prop types, sentiment, statistical claims, confidence level
4. Structured into the same `social_signals` database table as everything else

This is actually *better* for VIP content — your judgment filter acts as a quality gate before anything hits the pipeline.

### Source Priority Ranking

| Source | Signal Type | API/Access | Quality |
|--------|------------|------------|---------|
| Reddit (r/sportsbook, r/nba, r/nbabetting) | Organic public discourse | `old.reddit.com` JSON, no auth | High — reasoning included |
| Action Network public % | Structured bet/money percentages | Scrape public pages | Clean, quantified |
| Discord (dedicated account) | Group sentiment, real-time discussion | Account token | Rich but messy |
| Screenshot pipeline | High-signal curated content | Manual | Highest quality, least volume |
| DraftKings "Most Bet" | What DK audience is piling on | Public-facing | Lagging indicator only |
| Twitter/X | Real-time sentiment | API ($100+/month) | Noisy, expensive |

---

## Multi-Agent Team Architecture

### Design Principles

- **Narrow specialists + PM orchestrator** — same reason Ludi was built as separate modules
- Each agent receives only what it needs for its single job
- No agent does analysis outside its lane
- PM maintains state; specialists operate statelessly per call
- All inter-agent communication happens through `ludi.db` — no custom messaging infrastructure needed
- **Gardener model** (OpenClaw best practice): hot-path collection (Scout writes raw rows, no LLM) is separate from async refinement (Analyst classifies in background). Never block the pipeline waiting for social signal processing.
- **Just-in-time prompt loading**: Analyst Team Haiku prompt loads only when the Analyst step fires — not in every `curate_plays.py` bootstrap. Saves ~3-5K tokens per curation call.

### Full Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                        PM AGENT                             │
│                   (Orchestrator / Router)                   │
│  - Holds daily session context (games, model outputs)       │
│  - Routes tasks to appropriate specialist teams             │
│  - Resolves conflicts between team outputs                  │
│  - Surfaces collision flags to Research Team                │
│  - Never picks plays, never fetches data, never classifies  │
│  Model: Sonnet (tight system prompt, routing logic only)    │
└──────┬─────────────┬──────────────┬──────────────┬──────────┘
       │             │              │              │
       ▼             ▼              ▼              ▼
  ┌─────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────┐
  │  SCOUT  │  │ ANALYST  │  │RESEARCH  │  │  MARKET      │
  │  TEAM   │  │  TEAM    │  │  TEAM    │  │INTELLIGENCE  │
  │         │  │          │  │          │  │   AGENT      │
  │ Reddit  │  │ Haiku    │  │Perplexity│  │              │
  │ Discord │  │ Sentiment│  │ on new   │  │ Line movement│
  │ Action  │  │ classify │  │ info     │  │ Steam detect │
  │ Network │  │ (4 fields│  │ flags    │  │ RLM flag     │
  │ Screenshots│ only)   │  │ Cross-   │  │ Book disagree│
  └────┬────┘  └────┬─────┘  │ check DB │  └──────┬───────┘
       │            │        └────┬─────┘         │
       └────────────┴─────────────┴───────────────┘
                            │
                   ┌────────▼────────┐
                   │   SYNTHESIS     │
                   │     TEAM        │
                   │                 │
                   │ Social Heat +   │
                   │ Market Signal   │
                   │ + Model Edge    │
                   │ = Prop Pulse    │
                   │   Score (0-100) │
                   └────────┬────────┘
                            │
                   ┌────────▼────────┐
                   │ curate_plays.py │
                   │  (already exists│
                   │   + Sonnet)     │
                   │                 │
                   │ Now receives    │
                   │ Prop Pulse Score│
                   │ + conflict flags│
                   └─────────────────┘
```

### Agent Specs

#### Scout Team — Data Collection Only
- **One job:** Collect raw data from sources. No analysis, no opinions.
- **Outputs:** Raw text + source + timestamp → `social_signals` table in ludi.db
- **Model:** No LLM needed. Pure collection scripts. Zero cost at this layer.
- **Runs:** Every 30 min (active hours: 6 AM–midnight EST). Every 2 hours overnight (1–6 AM EST) — don't skip entirely, opening odds/lines/props can drop overnight and early injury news emerges before morning brief.
- **Reddit method:** `old.reddit.com` public JSON endpoints — no PRAW, no OAuth, no API key required. Fetch hot/new/top + comment threads per subreddit. Pattern validated by Reddit Claw v1.1 (OpenClaw community skill). Do NOT install unverified third-party skills — replicate the `old.reddit.com` technique directly in Python.
- **Tool access:** Collection scripts ONLY. No LLM calls, no DB writes outside `social_signals`.
- **`hours_to_tip`:** Calculated at insert time using tonight's game start from `games` table. Stored on every `social_signals` row — powers late-signal detection downstream.
- **Late-signal surge:** Scout script checks if any game tips in <2 hours. If yes, it re-scans all sources immediately regardless of last-run time and sets `late_signal_flag=1` on new rows. Cron stays at :10/:40 — the escalation happens inside the script, not via a new cron.

#### Analyst Team — Classification Only
- **One job:** Classify each piece of Scout Team output. Nothing else.
- **Inputs:** Single message/post from social_signals
- **Outputs:** 4-field JSON: `{direction, confidence_level, reasoning_quality, new_info_flag}`
- **Model:** Haiku — fast, cheap, narrow task
- **BERT-derived prompt pattern:** Few-shot examples + label space defined first + text_a/text_b separation

Haiku prompt structure:
```
Label space: [BULLISH, BEARISH, NEUTRAL]
Reasoning quality: [DATA_BASED, GUT_FEEL, HYPE]
Confidence: [HIGH, MEDIUM, LOW]

Few-shot examples:
text_a (context): Tatum PTS prop set at 27.5
text_b (post): "Tatum been cooking lately, L5 avg 31.4,
                matchup is soft vs Indiana. OVER is a lock"
Output: {direction: BULLISH, confidence: HIGH,
         reasoning: DATA_BASED, new_info: false}

text_a: Same prop
text_b: "LFG Tatum 🔥🔥🔥"
Output: {direction: BULLISH, confidence: LOW,
         reasoning: HYPE, new_info: false}
```

#### Research Team — Context Enrichment Only
- **One job:** When Analyst flags `new_info: true`, go deeper.
- **Trigger:** `new_info_flag = true` from Analyst Team
- **Process:** Perplexity call on the specific claim → cross-check `player_injuries` table
- **Output:** Enriched context block → injected into curation prompt
- **Model:** Existing Perplexity integration (already in pipeline)
- **Note:** Only fires on new information flags — not on every post

#### Market Intelligence Agent — Odds/Lines Monitoring
- **One job:** Track line movement and detect sharp signals.
- **Data source:** The-Odds-API (already paid, already integrated in Module A)
- **New requirement:** `odds_snapshots` table for time-series storage (see data model below)
- **Runs:** 5x per day — overnight open (2:05 AM EST, captures lines as they drop), morning (8:30 AM), midday (12:30 PM), afternoon (4:00 PM), pregame lock (5:45 PM — before Evening Slate Lock at 6 PM)
- **Outputs:** Line delta, steam flag, RLM flag, book disagreement flag, bet/money %

#### Synthesis Team — Heat Index + Score Calculation
- **One job:** Combine all signals into Prop Pulse Score and fire Smart Signals.
- **Inputs:** social_signals + odds_snapshots + model output
- **Outputs:** prop_pulse_score (0-100), smart_signal_flag, power_trend_flag, traffic_light, conflict_flag
- **Model:** Sonnet for conflict resolution; pure math for score calculation

#### PM Agent — Orchestrator
- **One job:** Route, sequence, resolve conflicts.
- **Holds:** Daily session context — which games, which model outputs, pipeline state
- **Routes:** Scout → Analyst → (if new_info) Research → Synthesis → Curation
- **Resolves:** Conflict flags (model says OVER, market says sharps are fading OVER)
- **Never:** Picks plays, fetches data, classifies sentiment, does analysis
- **Model:** Sonnet with tight routing-only system prompt

### Context Discipline Per Agent

```
Each agent receives:
  ✅ Its own narrow system prompt (what it does + what it NEVER does)
  ✅ Only the inputs relevant to its specific task
  ✅ A strict output schema (JSON, defined fields only)

Each agent never receives:
  ❌ Another agent's full conversation history
  ❌ The full pipeline state
  ❌ Anything outside its lane
```

### Inter-Agent Communication Model

Agents communicate exclusively through `ludi.db` — no sockets, no queues, no custom bus. A `social_pipeline_state` table acts as the explicit handoff layer the PM Agent reads to track where each signal is:

```sql
CREATE TABLE social_pipeline_state (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_date TEXT,         -- game_date this session covers
    signal_id INTEGER,         -- FK to social_signals
    stage TEXT,                -- 'scout', 'analyst', 'research', 'synthesis', 'complete'
    status TEXT,               -- 'pending', 'in_progress', 'done', 'error'
    agent TEXT,                -- which agent owns this row
    handoff_note TEXT,         -- brief context passed to the next agent (e.g. "new_info: injury update")
    created_at TEXT DEFAULT (datetime('now'))
);
```

This table is the **working/temporary database** — it holds in-flight state only. Rows are purged after 48 hours (cleanup step in `data_sync.yml`). The PM Agent reads it to decide routing: if `stage='analyst'` and `new_info=true`, it routes to Research Team next. If `stage='synthesis'` and `conflict=true`, it flags for Sonnet conflict resolution.

This also gives you an audit trail: every signal's journey from collection → classification → score is logged. Invaluable for debugging why a play was or wasn't surfaced.

### Token Budget Per Agent (OpenClaw best practice)

| Agent | Token Cap | Rationale |
|-------|-----------|-----------|
| Scout Team | No LLM | Pure collection — $0 |
| Analyst Team (Haiku) | 50K | Narrow classification task |
| Research Team (Perplexity) | 50K | Only fires on `new_info=true` |
| Market Intelligence | No LLM | Pure math signals |
| Synthesis Team | 50K | Score calculation + Sonnet conflict resolution |
| PM Agent (Sonnet) | 80K | Orchestrator — needs more context |
| `curate_plays.py` injection | ≤5K | Prop Pulse block must stay concise — use `_safe_inject()` pattern |

---

## Market Intelligence Agent

### The Four Signal Combinations

```
                ODDS MOVING WITH PUBLIC (line goes way hype says)
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
  HIGH SOCIAL           NEUTRAL             LOW SOCIAL
    HYPE               SOCIAL                 HYPE
        │                    │                    │
        ▼                    ▼                    ▼
  Public piling         Line moving          Sharp action —
  on, book is           but nobody's         no public noise.
  pricing it in.        talking much.        Follow the money.
  Edge probably         Investigate          Highest confidence
  already gone.         further.             signal.

        └── ODDS MOVING AGAINST PUBLIC (reverse line movement)
                             │
                             ▼
               Social loves it BUT line
               moving the wrong way.
               SHARPS ARE ON OTHER SIDE.
               This is the FADE signal.
               Most powerful combination.
```

### New Database Table Required

```sql
CREATE TABLE odds_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    player_id INTEGER,
    prop_type TEXT,           -- 'PTS', 'REB', 'AST', '3PM', etc.
    line REAL,                -- the number (e.g., 28.5)
    over_odds INTEGER,        -- American odds
    under_odds INTEGER,
    book TEXT,                -- 'draftkings', 'fanduel', 'betmgm', etc.
    snapshot_time TEXT,       -- ISO timestamp
    session TEXT              -- 'overnight'(2:05AM), 'open'(8:30AM), 'midday'(12:30PM), 'afternoon'(4PM), 'pregame'(5:45PM)
);
```

### Signals the Agent Calculates

| Signal | Formula | Meaning |
|--------|---------|---------|
| Line delta | current_line - open_line | How much has number moved |
| Juice shift | current_juice - open_juice | Book confidence increasing/decreasing |
| Steam flag | \|delta\| > 0.5 in < 2 hours | Sharp/syndicate action |
| Book disagreement | max(line) - min(line) across books | Market unsettled |
| RLM flag | line moves opposite to public bet % direction | Sharps overriding public |

### Phase Connection

This is the natural evolution of Phase 8.18 (Game Lines Integration — already complete). Once the data flow is stable, adding time-series snapshot collection is the next layer. Steam move detection is also already listed in the ROADMAP future enhancements — this architecture makes it a byproduct of the Market Agent, not a separate feature.

---

## Competitor Reverse Engineering

### LunarCrush — Social Intelligence Data Model

Their Galaxy Score formula (reverse engineered):
```
Galaxy Score (0-100) =
  Price Score        (trend direction from moving average)
  + Social Sentiment (% of posts that are bullish, 0-100)
  + Social Activity  (current volume vs. baseline)
  + Correlation      (how closely social tracks price movement)

Supporting fields:
  social_dominance   = this asset's % of ALL social volume
  altrank            = relative rank vs. all other tracked assets
  social_volume      = raw mention count across platforms
  anomaly_flag       = spike > 50% above 90-day moving average
```

**Ludi translation:** Replace "price score" with "line movement score", replace "asset" with "player/prop", replace "market dominance" with "share of total NBA prop discussion today."

Their API is documented publicly at: [github.com/lunarcrush/api](https://github.com/lunarcrush/api)

---

### Outlier.bet — Player Props Data Model

Their entire feature set mapped to your existing stack:

| Outlier Field | What It Is | Ludi Equivalent | Status |
|---------------|-----------|-----------------|--------|
| Traffic light hit rate | Green ≥65%, Yellow 45-65%, Red <45% | `player_game_logs` hit rate | Already have data |
| L5 / L10 / Season | Hit rate by timeframe | Module B calculations | Already built |
| Opposition Rank | Defense rank vs. prop type | Module E matchup data | Already built |
| Implied Probability | Devigged fair odds | Module F core output | Already built (superior) |
| +EV tab | Edge over fair value | Core model output | Already built |
| Line movement chart | Book comparison over time | Market Intelligence Agent | To build |
| Public betting splits | Bet % per side | Action Network layer | To build |
| Alternate lines | Price comparison across books | The-Odds-API (already integrated) | Already have |

They charge $19.99–$129.99/month for this. You already have the core model. They don't have yours under it.

---

### Rithmm — Smart Signal / Power Trend Model

**Smart Signal (⚡):** High-confidence play flagged automatically when specific conditions align. Full breakdown shown so you know exactly why it's being surfaced.

**Power Trend:** AI-detected *repeatable pattern* under specific conditions — "when these exact conditions appear, this bet type wins at X%."

**Critical insight:** Your stat confidence framework from Phase 8.20 already IS a Power Trends engine. The finding that BLOCKS UNDER has a 68.7% Wilson floor at n=2187 is a Power Trend. It just hasn't been named or surfaced that way in the product.

Rithmm charges $29.99–$99.99/month. They were built by MIT grads. They do not have a live simulation pipeline.

---

### Action Network — Sharp vs. Public Signal Model

The two fields that matter and how to read them:

```
Bet %   = where the PUBLIC TICKETS are (number of individual bets)
Money % = where the DOLLARS are (total cash wagered)

When Bet % >> Money %:
  Lots of small public bets on one side.
  Sharp money is NOT on that side.
  → Fade signal

When Money % >> Bet %:
  Big money on the unpopular side.
  Someone with size is betting against the crowd.
  → Sharp signal

When line moves OPPOSITE to Bet %:
  Reverse Line Movement.
  Sharps came in so heavy they overrode public action.
  → Strongest signal in the entire system.
```

Free public data available at their website. No official API — scrape the public pages.

---

## The Prop Pulse Score — Composite Data Model

### Database Table

```sql
CREATE TABLE prop_intelligence (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    player_id INTEGER,
    prop_type TEXT,
    line REAL,
    game_date TEXT,

    -- SOCIAL LAYER (Scout + Analyst Teams)
    social_heat_score REAL,          -- 0-100 composite
    social_volume INTEGER,           -- mentions in last 4 hours
    social_sentiment_pct REAL,       -- % bullish
    social_spike_flag INTEGER,       -- 1 if >50% above 7-day avg
    social_source_breakdown TEXT,    -- JSON: {reddit, discord, twitter}

    -- MARKET LAYER (Market Intelligence Agent)
    public_bet_pct REAL,             -- % tickets on OVER
    public_money_pct REAL,           -- % dollars on OVER
    bet_money_divergence REAL,       -- gap between the two (sharp signal)
    line_delta REAL,                 -- movement since open
    steam_flag INTEGER,              -- 1 if >0.5pt in <2 hours
    rlm_flag INTEGER,                -- 1 if reverse line movement detected
    book_disagreement REAL,          -- spread across books

    -- MODEL LAYER (existing Ludi output — already built)
    model_edge_pct REAL,
    hit_rate_l5 REAL,
    hit_rate_l10 REAL,
    hit_rate_season REAL,
    opposition_rank INTEGER,
    confidence_tier TEXT,            -- DIAMOND/BLUE CHIP/CORE ASSET/THE STEAL

    -- COMPOSITE OUTPUT (Synthesis Team)
    prop_pulse_score REAL,           -- 0-100 final score
    smart_signal_flag INTEGER,       -- 1 if all 6 conditions met (see below)
    power_trend_flag INTEGER,        -- 1 if repeatable pattern active
    traffic_light TEXT,              -- GREEN/YELLOW/RED
    conflict_flag INTEGER,           -- 1 if agents disagree
    conflict_detail TEXT,            -- what the conflict is

    created_at TEXT DEFAULT (datetime('now'))
);
```

### BERT Training Table

Separate from operational tables. Captures every Analyst Team classification + its eventual outcome for future model fine-tuning. A nightly script joins against `bet_recommendations` + `player_game_logs` to fill `actual_result` after games are settled.

```sql
CREATE TABLE bert_training_signals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    signal_id INTEGER,         -- FK to social_signals (raw text preserved there)
    player_id INTEGER,
    prop_type TEXT,
    line REAL,
    game_date TEXT,

    -- Source context
    source TEXT,               -- 'reddit', 'discord', 'action_network', 'screenshot'
    subreddit TEXT,            -- r/sportsbook, r/nba, etc. (if Reddit)
    hours_to_tip REAL,         -- hours between signal timestamp and game start

    -- Analyst Team classification (labels)
    direction TEXT,            -- BULLISH / BEARISH / NEUTRAL
    confidence_level TEXT,     -- HIGH / MEDIUM / LOW
    reasoning_quality TEXT,    -- DATA_BASED / GUT_FEEL / HYPE
    new_info_flag INTEGER,     -- 1 if Analyst flagged novel information
    late_signal_flag INTEGER,  -- 1 if hours_to_tip < 2 (pre-tip surge window)

    -- Outcome (backfilled nightly by sync_bert_outcomes.py)
    actual_result TEXT,        -- 'OVER_HIT' / 'UNDER_HIT' / 'PUSH' / 'NO_BET'
    direction_correct INTEGER, -- 1 if direction matched actual_result, 0 if not
    was_high_confidence INTEGER, -- 1 if HIGH confidence AND direction_correct

    -- Calibration (updated weekly by scripts/calibrate_social_weights.py)
    source_weight REAL,        -- rolling accuracy weight for this source (default 1.0)

    classified_at TEXT,
    outcome_recorded_at TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);
```

**What this unlocks over time:**
- **14 days (~Mar 10):** First pattern scan — validate collection, check for early signal separation. Not for fine-tuning; for course-correcting Scout configuration if collection is broken.
- **90 days (late May 2026 — offseason):** Full accuracy report per source × reasoning_quality × `hours_to_tip` bucket. Example query: "Reddit DATA_BASED + `hours_to_tip` < 3 + BULLISH → actual OVER_HIT rate?" Fine-tune Haiku Analyst prompt weights from empirical results.
- **Offseason (Jun–Sep 2026):** No live pipeline pressure. Calibrate all weights, evaluate literal BERT fine-tuning (requires n > 500 per class), deploy updated classifier before 2026-27 preseason.

### Prop Pulse Score Formula

```
Prop Pulse Score (0-100) =

  Model Edge Weight    40%  ← your core, highest quality
  + Hit Rate Weight    25%  ← L10 Wilson floor grade
  + Market Signal      20%  ← INVERSE of public bet %
                              (high public = lower score)
                              + RLM bonus: +15 if flagged
  + Social Heat        15%  ← INVERSE of social heat
                              (low public notice = bonus)
                              (high social heat = penalty)
```

**The counterintuitive design:** High public interest *lowers* the Prop Pulse Score. The highest scores go to plays where the model finds edge that the public hasn't spotted yet. This is the direct translation of LunarCrush's "social dominance penalty" into your context.

### Traffic Light Mapping

| Color | Prop Pulse Score | Meaning |
|-------|-----------------|---------|
| 🟢 GREEN | 70-100 | Model edge + low public interest + no steam = pure play |
| 🟡 YELLOW | 45-69 | Some edge but public awareness or line movement present |
| 🔴 RED | 0-44 | Edge likely eroded, high public action, or model/market conflict |

---

## Smart Signal Trigger Conditions

A Smart Signal (⚡) fires when ALL six conditions are simultaneously true:

```
✅ 1. Model edge ≥ 10%            (BLUE CHIP tier or better)
✅ 2. Hit rate L10 ≥ 60%          (Wilson floor ≥ 55%)
✅ 3. Social heat ≤ 5/10          (public hasn't spotted it)
✅ 4. Public bet % ≤ 65%          (not heavily bet down)
✅ 5. No steam flag                (line stable = not already arbitraged)
✅ 6. No adverse RLM               (sharps not fading this direction)
```

When all six align: the model has genuine edge on a play the public doesn't know about yet, the line hasn't moved to price it in, and sharp money is not actively opposing it. This is the play that goes on the card with the ⚡.

---

## The BERT / Haiku Modeling Approach

### Two Distinct Concepts

| Approach | What It Is | Timeline |
|----------|-----------|----------|
| **Literal BERT** | Fine-tuned transformer running locally | Future Phase — needs 6+ months of labeled data first |
| **BERT-derived patterns** | Prompt architecture techniques applied to Haiku/Sonnet | Now — already documented in `best-practices/ai/PROMPT_ENGINEERING_PATTERNS.md` |

### Why Haiku Now, Literal BERT Later

Fine-tuning BERT requires hundreds of labeled examples specific to your domain. You don't have that yet. Once 6+ months of social signal data is collected with known outcomes (did the public-loved prop hit or miss?), you'll have the training data to fine-tune a classifier on your own historical results.

**The training loop:**
1. Collect social signals → classify with Haiku → track outcomes
2. After 3-4 months: labeled dataset of signal + outcome
3. Calibrate Haiku weights — which source, signal type, reasoning quality actually predicts results?
4. Eventually fine-tune a lightweight classifier on your own data
5. That classifier replaces Haiku as the Analyst Team's backbone

This is exactly the LunarCrush model — simple collection first, then training against real outcomes.

### BERT-Derived Patterns Already in Your Stack

From `best-practices/ai/PROMPT_ENGINEERING_PATTERNS.md` (Phase 8.19 research):
- Pattern 1: Few-shot examples in classification prompts
- Pattern 2: Label space defined first in every Haiku call
- Pattern 3: text_a/text_b section separation (context vs. content)
- Pattern 4: NSP gate for news relevance (replaces keyword matching)
- Pattern 5: Pre-truncate injected blocks to prevent silent overflow
- Pattern 6: Parse failure logging for audit trail

Apply all six patterns to the Analyst Team's Haiku classification prompt.

---

## How This Extends the Existing Pipeline

This does NOT replace anything in the existing Ludi pipeline. It runs parallel and feeds into the curation step that already exists:

```
Existing Ludi Pipeline (Modules A → F)
    Outputs: model_edge, confidence_tier, hit_rates, matchup context

Social Intelligence Pipeline (Scout → Analyst → Research → Synthesis)
    Outputs: social_heat, market signals, Prop Pulse Score, Smart Signal flags

Both feed into:
    curate_plays.py (already exists)
    → _get_system_wr_context() already injects domain knowledge into Sonnet
    → Prop Pulse Score becomes another injection block
    → Smart Signal flag becomes a curation priority signal
    → Conflict flags route to Research Team for Perplexity investigation
```

### The Curation Prompt Injection (What Changes)

Current Sonnet system prompt injection:
```
Domain WR: BLOCKS UNDER 63%, UNDER 55%, OVER 42%
```

New injection block added:
```
Prop Intelligence for tonight:

Jayson Tatum PTS OVER 28.5:
  Model Edge: 13.2% | Hit Rate L10: 67% | Tier: BLUE CHIP
  Social Heat: 3.1/10 (low — public hasn't noticed)
  Public Bet %: 54% OVER (mild lean, not extreme)
  Line Movement: +0.5 since open (moderate, no steam)
  RLM: None | Steam: None
  Prop Pulse Score: 74/100 🟢 | Smart Signal: ⚡ YES

  [This play is clean — model edge with low public interest and stable line]
```

---

## Next Steps & Decision Points

### Immediate (Before Building Anything)

- [ ] **Map your Discord channels** — Go through your servers, identify 5-10 highest signal channels using the framework above. This determines Scout Team configuration entirely.
- [ ] **Decide on dedicated Discord account** — Create it, manually join and verify in target servers during one session.
- [ ] **Identify Action Network scraping targets** — Which pages, what fields, what update frequency.

### Workflow Schedule & Conflict Avoidance

All crons are UTC (GitHub Actions). SQLite WAL allows concurrent reads, but avoid heavy-write windows.

**Blocked slots — never schedule here:**

| EST | UTC | Why |
|-----|-----|-----|
| 1:00 AM | `0 6` | DB Backup |
| 3:00 AM | `0 8` | Data Sync — heaviest writer |
| 10:00 AM | `0 15` | Daily Simulation — heavy reads |
| 11:00 AM | `0 16` | Daily Briefing — Claude API burst |
| 6:00 PM | `0 23` | Evening Slate Lock |

**Game-time pattern (6 PM–midnight EST):** Injury Refresh fires at `:02/:22/:42` past each hour. Capture Closing Lines fires at `:25/:55`. Use **`:10` and `:40`** for all game-time Social Intel runs.

**Proposed Social Intelligence cron slots:**

| Workflow | UTC Cron | EST Time | Notes |
|----------|----------|----------|-------|
| Reddit Scout (active) | `10,40 11-23,0,1,2,3,4 * * *` | 6 AM–11 PM, :10/:40 | Avoids :02/:22/:42 injury + :25/:55 closing lines |
| Reddit Scout (overnight) | `0 7 * * *`, `0 9 * * *` | 2 AM, 4 AM | 2 AM = clear; 4 AM = after Data Sync finishes, before Daily Reports |
| Action Network scraper | `0 13 * * *`, `0 19 * * *` | 8 AM, 2 PM | Clean windows both |
| Market Intel snapshots | `5 7 * * *`, `30 13 * * *`, `30 17 * * *`, `0 21 * * *`, `45 22 * * *` | 2:05 AM, 8:30 AM, 12:30 PM, 4 PM, 5:45 PM | 5:45 PM captures pre-game lines before 6 PM Evening Lock |
| Analyst Team Haiku | Within Scout workflow | Same as Scout | Not a separate cron — Analyst runs as the final step of each Scout job |

### Phase 1: Foundation (Social + Market Layers)

- [ ] Create `social_signals` table in ludi.db (include `hours_to_tip`, `late_signal_flag`)
- [ ] Create `odds_snapshots` table in ludi.db
- [ ] Create `prop_intelligence` table in ludi.db
- [ ] Create `social_pipeline_state` table in ludi.db (inter-agent handoff + working state, 48-hr purge)
- [ ] Create `bert_training_signals` table in ludi.db (separate from ops tables — training data only)
- [ ] Build Reddit Scout (`old.reddit.com` JSON polling, r/sportsbook + r/nba + r/nbabetting, 30-min active / 2-hr overnight cron)
- [ ] Build Action Network scraper (public bet %, 2x/day)
- [ ] Build Market Intelligence Agent (odds snapshot collection, 4x/day via existing Odds API)

### Phase 2: Analysis Layer

- [ ] Build Analyst Team Haiku classifier (4-field JSON output, BERT-derived prompt patterns)
- [ ] Build Synthesis Team score calculator (Prop Pulse Score formula)
- [ ] Build Smart Signal trigger logic (6-condition check)
- [ ] Wire `new_info_flag` → Research Team (Perplexity) pathway

### Phase 3: Integration

- [ ] Build PM Agent routing logic
- [ ] Inject Prop Pulse Score into `curate_plays.py` system prompt
- [ ] Add Smart Signal flag to morning brief card format
- [ ] Add traffic light to Telegram output

### Phase 4: Training Loop

- [ ] Build `scripts/sync_bert_outcomes.py` — nightly join of `bert_training_signals` against `bet_recommendations` + `player_game_logs` to backfill `actual_result` + `direction_correct`
- [ ] Build `scripts/calibrate_social_weights.py` — weekly Wilson confidence intervals per source/reasoning_quality combination → updates `source_weight` column

**14-day first scan (~Mar 10, 2026):** Early pattern detection — not enough data for fine-tuning but enough to validate collection is working. Questions to answer:
- Are any sources showing signal above 55% accuracy at 14 days?
- Is `hours_to_tip < 2` (`late_signal_flag=1`) already outperforming earlier signals?
- Is DATA_BASED reasoning quality separating from HYPE at any confidence level?
- Are enough rows in `bert_training_signals` to trust the Wilson floors?

If all four answers are no → investigate Scout Team configuration before continuing. If even one shows signal → collection is working, stay the course.

**90-day window (late May 2026 — offseason):** Regular season ends ~Apr 13. Playoffs through ~Jun 19. The 90-day mark lands squarely in the offseason — ideal timing. No live pipeline pressure, no quota risk from running calibration jobs. Plan:
- [ ] After 90 days: full `bert_training_signals` accuracy report — source × reasoning_quality × `hours_to_tip` bucket → which combinations predict outcomes?
- [ ] Fine-tune Haiku Analyst prompt weights based on empirical accuracy (not assumed)
- [ ] Calibrate Perplexity `hours_to_game` recency filter using `claude_analysis_log` accuracy (Phase 8.23 data)
- [ ] Evaluate literal BERT fine-tuning if labeled dataset is large enough (n > 500 per class)
- [ ] Deploy updated classifier weights before 2026-27 preseason (Oct 2026)

### Decisions to Make Before Phase 1

1. **Which Discord channels?** (Channel list → Scout Team targets)
2. **Confirming vs. Discovery?** Using social to filter existing picks (simpler) or surface new ones (complex)? Start with confirming.
3. **How manual is the screenshot pipeline?** You drop them daily vs. a local watch script?
4. **Twitter/X?** API is now $100+/month. Skip for now, revisit if Discord + Reddit signal proves valuable.

---

## Reference Sources

### Agent Architecture (OpenClaw)
- [OpenClaw GitHub](https://github.com/openclaw/openclaw) — open-source agent runtime; multi-agent routing, AGENTS.md/SOUL.md pattern, Gardener model, token budgeting
- [Multi-Agent Scaling Best Practices — GitHub Issue #4561](https://github.com/openclaw/openclaw/issues/4561) — token budgets, context overflow, handoffs, session isolation
- [OpenClaw BEST_PRACTICES.md](https://github.com/CodeAlive-AI/awesome-openclaw/blob/main/OPENCLAW_BEST_PRACTICES.md) — bootstrap file limits, Gardener model, just-in-time loading
- [Reddit Claw v1.1 — GitHub Discussion](https://github.com/openclaw/openclaw/discussions/21321) — `old.reddit.com` JSON pattern, no API auth required
- [Alex Finn — 3 Things to Build with OpenClaw](https://x.com/AlexFinn/status/2019816560190521563) — competitor monitoring + morning brief workflow reference

### Competitor Intelligence
- [LunarCrush API v4 Documentation](https://github.com/lunarcrush/api)
- [Outlier Prop Finder Help Docs](https://help.outlier.bet/en/articles/6711738-research-player-propositions-with-outlier-s-prop-finder)
- [Rithmm AI Platform](https://www.rithmm.com/)
- [Understanding Betting Splits — RG.org](https://rg.org/guides/sportsbetting-guides/betting-splits)
- [Action Network Social Feature](https://www.actionnetwork.com/legal-online-sports-betting/draftkings-social-feed-engagement-interaction-bettors)
- [DK Network NBA Player Pulse](https://dknetwork.draftkings.com/2026/02/24/nba-best-bets-top-nba-player-pulse-betting-group-picks-for-tuesday-2-24-26-transcript/)
- [Unabated Sports Platform](https://unabated.com/education/the-art-of-sports-betting)
