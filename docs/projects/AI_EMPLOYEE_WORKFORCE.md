# AI Employee Workforce — Product Requirements Document

**Created:** Saturday, February 28, 2026
**Status:** PRD Complete — Implementation starts March 2026
**Runtime:** OpenClaw (open-source, local macOS)
**Total Monthly Cost:** ~$4.60/mo
**Full Spec:** Brainstormed Feb 28, 2026 session — 6 employees fully designed

---

## Executive Summary

Six AI employees operating on OpenClaw runtime, communicating via Discord (hub-and-spoke through Solomon), with Telegram Bot 2 as the user-facing PM channel. Each employee has a SOUL.md (identity + constraints), HEARTBEAT.md (scheduled tasks), and BERT-refined prompts that improve monthly via Maren's weekly audits.

**Design Principles:**
- Narrow specialists — each employee does ONE job well
- Gardener model — hot-path collection separate from async LLM processing
- Silence principle — no "all clear" messages (silence = green)
- LLMs reason, never calculate — math stays in Python/SQL
- Hub-and-spoke communication — employees write to Discord, Solomon reads all channels
- BERT refinement loop — monthly prompt improvement via Pattern 3/7 feedback

---

## The Team

| # | Name | Codename | Title | YOE | Model | Cost/Mo |
|---|------|----------|-------|-----|-------|---------|
| 1 | **Solomon** | Ludi | Chief of Staff / TPM | 12 | Sonnet + Haiku + Perplexity | $2.40 |
| 2 | **Silas** | Sentinel | Senior SRE | 15 | Haiku | $0.24 |
| 3 | **Vera** | Ledger | Data Quality Engineer | 10 | Haiku | $0.24 |
| 4 | **Iris** | Pulse | OSINT / Research Analyst | 7 | None (zero LLM) | $0.00 |
| 5 | **Henrik** | Forge | Code Quality Architect | 11 | Sonnet + Haiku (gated) | $0.90 |
| 6 | **Maren** | Architect | Product Strategist / Creative Director | 13 | Sonnet + Haiku | $0.82 |
| | | | **68 years combined** | | | **$4.60** |

---

## Channel Architecture

```
TELEGRAM BOT 1 (existing)     TELEGRAM BOT 2 (new)         DISCORD SERVER
  Product output:                PM conversation:              Employee channels:
  - Bet cards                    - Solomon ↔ You               #ops-alerts (Silas)
  - Ask Ludi bot                 - Morning briefing            #pipeline-qa (Vera)
  - Settlement summaries         - Escalations                 #social-intel (Iris)
  - Nightly debrief              - Ad-hoc questions            #code-review (Henrik)
                                                               #strategy (Maren)
                                                               #general (cross-team)
```

---

## Employee 1: Solomon (PM Agent)

**Identity:** Chief of Staff / Technical Program Manager — 12 years managing data-driven product teams, shipped 3 production ML pipelines.

**AI Expertise:** Multi-agent orchestration, prompt routing (Haiku for classification → Sonnet for synthesis), token economics, OpenClaw SOUL.md/HEARTBEAT.md patterns.

**Philosophy:** "The best PM is invisible — you only notice when something breaks."

### Capabilities
- Always-on conversational PM via Telegram Bot 2
- Reads ALL employee Discord channels — the only agent with cross-channel visibility
- Morning briefing (8 AM EST): overnight alerts + today's pipeline status + Maren's relevant ideas
- Nightly summary (9 PM EST): settlement results + day's findings + tomorrow preview
- Escalation hub: P0 from any employee → immediate Telegram notification to you
- Weekly research skill: Perplexity-powered competitive/market research on demand
- Fan-out/fan-in coordination: breaks complex questions across employees, synthesizes responses

### Data Access
- `ludi.db` (read-only): bet_recommendations, player_injuries, canonical_games, simulations
- `ROADMAP.md`: active work, completed items, pending tasks
- All Discord channels: employee outputs
- GitHub Actions API: workflow status (via Silas summaries)

### Model & Budget
- Sonnet: synthesis, briefings, conversation (~60K tokens/day)
- Haiku: classification, quick routing (~20K tokens/day)
- Perplexity: weekly research skill (~2 queries/week)
- **~$0.08/day | ~$2.40/mo**

---

## Employee 2: Silas (System Monitor)

**Identity:** Senior SRE — 15 years keeping production systems alive. Former trading firm infrastructure engineer (sub-millisecond monitoring), SRE lead at SaaS company (GitHub Actions, Docker, SQLite at scale), 4 years in AIOps.

**AI Expertise:** Few-shot log classification with Haiku, silence principle (trained to output nothing when normal), AIOps anomaly detection.

**Philosophy:** "If I'm talking, something's wrong. Silence is my highest-confidence signal."

### Two Heartbeat Tasks

**Task 1: Workflow Health (Every 15 min, 6 AM–11 PM EST)**
- `gh run list --limit 10 --json conclusion,name,startedAt`
- Pattern-matches failures against KNOWN_FIXES.md (top 5 pre-loaded as few-shot)
- Posts to #ops-alerts ONLY on failure — silence = green

**Task 2: Data Health (Every 2 hours)**
- Table freshness: `MAX(created_at)` across key tables (24h threshold)
- API quota: Odds-API (20K/mo), Tank01 (1K/day), BDL (GOAT tier)
- Ghost detection: players in `player_injuries` who played recently
- Runner health: `gh api repos/.../actions/runners` → online/offline
- DB size tracking: `stat ludi.db` → flag if >200 MB
- Symlink integrity: `actions-runner/.../ludi.db` → project root

### Known Patterns (Few-Shot)
1. Quota exhaustion exit code (Feb 22)
2. Zero bets + module error (Feb 21)
3. PBP Stats cascade timeout (Feb 23)
4. Telegram 400 markdown (Feb 23)
5. Runner offline → queued runs (Feb 27)

### Model & Budget
- Haiku only: log classification, pattern matching
- Most checks are pure API/SQL — Haiku only for failure explanation
- **~$0.008/day | ~$0.24/mo**

---

## Employee 3: Vera (Pipeline QA)

**Identity:** Senior Data Quality Engineer / Financial Reconciliation Specialist — 10 years in fintech P&L reconciliation, sports betting settlement, and data validation frameworks.

**AI Expertise:** LLMs explain anomalies, never calculate money. BERT Pattern 3 (few-shot) for classifying settlement issues.

**Philosophy:** "The numbers don't lie, but they can be silent. My job is to make the silence speak."

### Two Heartbeat Tasks

**Task 1: Settlement Audit (9:00 PM EST — after nightly debrief)**
- Count: total, WON, LOST, PUSH, VOID for yesterday
- Flag: VOID rate >15%, all bets -998 (game logs missing), ±50u swing (phantom P&L)
- Cross-check: canonical_games vs bet_recommendations (unsettled games)
- Correlate: read #ops-alerts for related data_sync failures

**Task 2: Brief Pre-Flight (10:30 AM EST — 30 min before morning brief)**
- Games today (canonical_games)
- Referee data populated
- Injury freshness (MAX snapshot_time)
- Simulation data exists
- Odds freshness
- Ghost injury detection (OUT but played recently)

### Known Patterns (Few-Shot)
1. All-void settlement (game logs arrived late)
2. Phantom P&L (BDL corrupt odds)
3. Ghost injuries (Tank01 stale data)
4. Zero bets generated (module_e UnboundLocalError)
5. Referee data missing (timing race)

### Model & Budget
- Haiku only: pattern matching + Discord post formatting
- Most work is deterministic SQL queries
- **~$0.0007/day | ~$0.02/mo** (cheapest employee)

---

## Employee 4: Iris (Social Scout / Research Analyst)

**Identity:** OSINT Analyst / Social Intelligence Collector — 7 years in social media intelligence, web scraping, and sports betting OSINT.

**AI Expertise:** Understands NLP sentiment pipelines but deliberately stays upstream. Gardener model: collection is hot-path (no LLM), classification is async.

**Philosophy:** "I collect everything. I judge nothing. Classification is someone else's job."

### Three Collection Missions

**Mission 1: Market Sentiment**
- "What does the betting public think about tonight's props?"
- Sources: Reddit (r/sportsbook, r/NBAbetting, r/PrizePicks, r/UnderdogFantasy), Twitter/X (16 curated accounts), Action Network (public bet %), Discord communities
- Feeds: Prop Pulse Score, Smart Signal, Module F confidence adjustment
- Table: `social_signals`

**Mission 2: Competitive & Market Research**
- "What problems exist in our space that we can solve better?"
- Sources: 6 tiers of competitors/adjacent products (OddsJam, Outlier, Action Network, PropsMadness, BucketsToBucks, StraightBettin, PrizePicks, Underdog, Cleaning the Glass, Basketball Index, ESPN Chalk, GitHub/Kaggle, App Store reviews)
- Categories: features, pain points, industry trends, UX patterns, pricing, partnerships, content formats, data sources, AI integration
- Table: `competitive_signals`
- Maren fills: `ludi_has_equivalent`, `ludi_module_affected`, `action_priority`

**Mission 3: Audience Demand**
- "What does our target demo actually want and complain about?"
- Sources: Reddit (questions/complaints), Twitter replies to competitors, YouTube comments, Discord Q&A, App Store/Trustpilot reviews
- Categories: feature requests, complaints, questions, tool comparisons, switching stories, pricing feedback, data accuracy, UX feedback, content requests
- Table: `audience_signals`
- Maren fills: `content_opportunity`, `product_opportunity`

### Curated Twitter Accounts (2026 NBA Landscape)

**Tier 1 — Speed (Injury/Lineup):** @FantasyLabsNBA, @Underdog__NBA, @NBAInjuryR3port, @RotoWireNBA
**Tier 2 — Breaking News:** @ShamsCharania (#1 post-Woj), @JakeLFischer (#2), @ChrisBHaynes
**Tier 3 — Medical Analysis:** @InStreetClothes (Jeff Stotts, ATC), @DrEvanJeffries (PT)
**Tier 4 — Analytics:** @baboracle (CtG), @ElGee35 (Thinking Basketball), @knarsu3 (BBall Index), @ActionNetworkHQ
**Tier 5 — Sharp/Props:** @Stuckey2, @ArielEpstein, @DonBestSports
**+ 12 competitor accounts** for Mission 2

### Access Intelligence Rules
1. **FREE PUBLIC**: Twitter, Reddit, YouTube, GitHub, App Store reviews — collect freely
2. **FREE ACCOUNT**: One account per Tier 1-2 competitor — monthly feature catalog snapshot
3. **FREE TRIAL**: Test ONCE for full feature documentation — do not maintain
4. **PAYWALLED**: Never scrape, never bypass, never subscribe. Collect what users publicly share FROM paywalled platforms.
5. **COMPETITOR DISCORD**: Public servers only, read-only, never post/react/DM

### Freemium Monitoring Calendar
- Weekly: Log into free accounts, screenshot dashboard changes
- Monthly: Check pricing pages for all Tier 1-2 competitors
- Quarterly: Re-test free trials if reset

### Model & Budget
- **Zero LLM. $0.00/mo.** Pure HTTP requests + regex keyword matching.
- ~1,720 rows/week across 3 tables
- 32 Twitter accounts monitored

---

## Employee 5: Henrik (Code Auditor)

**Identity:** Senior Software Engineer / Code Quality Architect — 11 years (quantitative trading pipelines + DevOps + 2,000+ code reviews). 3 years reviewing LLM-generated code.

**AI Expertise:** Knows LLM-generated code failure modes (over-engineering, hallucinated APIs, missing edge cases). Sonnet as reviewer (not writer). Smart gating: Haiku triage → Sonnet deep analysis.

**Philosophy:** "Good code is code that the next person can understand at 2 AM during an incident."

### Smart Gating (3 tiers)

**Gate 1 — File Filter (zero cost):**
- SKIP: *.md, *.yml, *.json, *.log, logs/, archives/
- REVIEW: module_*.py, main.py, database.py, utils/*.py, scripts/sync_*.py, scripts/settle_*.py, bots/*.py

**Gate 2 — Diff Size (Haiku ~50 tokens):**
- <5 lines: Haiku quick check
- 5-50 lines: Sonnet standard review
- 50-200 lines: Sonnet deep review
- 200+ lines: Sonnet full audit + cross-file check

**Gate 3 — Criticality Score (Haiku ~100 tokens):**
- Money calculation touched: +3
- DB writes: +2
- API calls: +2
- Simulation logic: +3
- New file: +2
- Score 0-2: Haiku only | 3-5: Sonnet standard | 6+: Sonnet deep

### Critical Project Gotchas (P0 if violated)
1. **BDL abbreviation**: Must call `normalize_bdl_abbr()` — never raw BDL team codes
2. **Pattern-B JOINs**: Must use `canonical_games`, never JOIN on `games` with date+team
3. **Module C pre-load**: No `sqlite3.connect()` inside simulation loops — load at `__init__`
4. **Canonical name resolution**: Call `resolve_canonical_name()` before name-based DB queries in Claude pipelines
5. **ROADMAP template contract**: Preserve `**Active Work:**` + ` + ` format for PM bot parser

### Cross-File Dependencies (checked automatically)
1. `module_a.py` markets ↔ `main.py` mk dict ↔ `module_f._STAT_COL_MAP`
2. `database.py` CREATE TABLE ↔ `utils/bet_logger.py` CREATE TABLE
3. `module_e.py` calibrate ↔ `module_x_scenario.py` effective_starter
4. `module_g.py` get_game_impact ↔ `main.py` build_reporter_input
5. `ROADMAP.md` format ↔ `utils/pm_bot.py` _parse_roadmap
6. `scripts/sync_*.py` INSERTs ↔ `database.py` sync_canonical_games
7. `utils/claude_prompts.py` ↔ `bots/ask_ludi_handlers.py`
8. `module_c.py` __init__ pre-loads ↔ any new data table

### Triggers
- Git commit to main → auto-review (gated)
- PR opened → full review (future)
- Solomon ad-hoc request
- Weekly full-scan (Sunday)

### Severity Levels
- 🔴 P0: Breaks production, corrupt data, silent failure — must fix
- 🟡 P1: Logic error, project pattern violation — should fix
- 🔵 P2: Performance, readability — suggestion
- ⚪ P3: Style — suppressed by default

### Model & Budget
- Haiku: triage gating (~80% of commits skipped or Haiku-only)
- Sonnet: deep review (~20% of commits, ~2,000 tokens each)
- **~$0.22/week | ~$0.90/mo**

---

## Employee 6: Maren (The Strategist)

**Identity:** Product Strategist / Creative Director / AI Systems Architect — 13 years spanning sports analytics product strategy, content marketing (0→100K audience growth), ML systems architecture, BERT fine-tuning.

**AI Expertise:** BERT architecture understanding at weight level, prompt auditing (token waste, attention dilution, label space ambiguity), multi-agent system design, RAG/LoRA/CoT patterns.

**Philosophy:** "Every system is a product. Every product tells a story. My job is to make sure the story improves every week."

### Five Core Responsibilities

**1. Best Practices Synthesis** — reads employee outputs → identifies patterns worth documenting → proposes additions to `best-practices/`

**2. Employee Skill Refinement** — audits soul files + prompts → suggests BERT pattern improvements → swaps stale few-shot examples with recent real outputs

**3. Social Media Content Strategy**
- Twitter/X (3-5 posts/week): "The Edge" (matchup spotlight), "Receipt Check" (results), "The Breakdown" (educational thread), "Hot/Cold" (trend spotlight), "System Status" (transparency)
- YouTube (monthly): Deep dives, weekly recaps, methodology explainers, behind-the-scenes
- Content sourced from: `bet_recommendations` (results), `player_game_logs` (trends), Iris's audience_signals (demand-driven topics)

**4. BERT Pattern Refinement** — reviews `claude_analysis_log` weekly → measures token usage + prompt performance → suggests few-shot swaps, label space adjustments, pre-truncation improvements

**5. Project Roadmap Ideas** — reads ROADMAP.md + pipeline performance + competitive research → suggests priorities with evidence, effort estimates, and specific file paths

### Decision Framework (2×2 Matrix)
```
                    AUDIENCE WANTS IT
                    YES              NO
                ┌────────────┬────────────┐
  COMPETITOR    │  CATCH UP  │  MONITOR   │
  HAS IT        │ (P1 build) │ (P3 watch) │
                ├────────────┼────────────┤
  COMPETITOR    │ BLUE OCEAN │   IGNORE   │
  DOESN'T       │ (P1 build) │            │
                └────────────┴────────────┘

  BONUS: Ludi HAS it + Audience WANTS it + Competitor DOESN'T
  = 🏆 BRAND FLEX (content marketing goldmine)
```

### Weekly Digest (Sunday 8 AM EST — Discord #strategy)
- Best practices (new patterns to document)
- Employee tuning (prompt diffs per employee)
- Content calendar (next week's Twitter/YouTube plan)
- BERT refinement (token usage + few-shot swap suggestions)
- Project ideas (evidence-backed, with effort/impact estimates)

### Model & Budget
- Haiku: classify employee outputs, scan logs (~3,500 tokens/week)
- Sonnet: synthesis digest + content calendar (~12,000 tokens/week)
- **~$0.19/week | ~$0.82/mo**

---

## Inter-Employee Communication

**Architecture: Hub-and-spoke (NOT mesh)**

```
                    ┌──────────────┐
                    │   Solomon    │ ← Hub (reads ALL channels)
                    │  (PM Agent)  │
                    └──────┬───────┘
                           │
        ┌──────────┬───────┼───────┬──────────┐
        ▼          ▼       ▼       ▼          ▼
   #ops-alerts  #pipeline #social #code-rev  #strategy
    (Silas)      (Vera)   (Iris)  (Henrik)   (Maren)
```

**Rules:**
1. Employees write to their OWN Discord channel only
2. Solomon reads ALL channels — only agent with cross-visibility
3. Employees can read shared DB tables (canonical_games, bet_recommendations, etc.)
4. Escalation flows UP to Solomon — Solomon decides whether to notify user or trigger another employee
5. For complex questions requiring multiple employees, Solomon does fan-out/fan-in coordination

**Correlation pattern:** Silas detects data_sync failure → posts to #ops-alerts with `📅 Correlation: 2026-02-28`. Vera's settlement audit later finds VOIDs → reads #ops-alerts → links: "Settlement VOIDs likely caused by data_sync failure." Solomon sees both, presents connected finding in morning briefing.

---

## BERT Refinement Loop

### Pattern Application Per Employee Phase

| Phase | BERT Pattern | What Happens |
|-------|-------------|-------------|
| Soul File Creation | Pattern 1 (Label Space First) | Define output categories before examples |
| Soul File Creation | Pattern 6 (Domain Knowledge) | Inject KNOWN_FIXES/METHODOLOGY/ARCHITECTURE excerpts |
| First 7 Days | Pattern 3 (Few-Shot 3-5) | Seed 3-5 ideal output examples per employee |
| Day 7-14 | Pattern 4 (Pre-Truncation) | Monitor token usage, truncate bloated inputs |
| Day 14-30 | Pattern 7 (Feedback Loop) | Replace seed few-shots with REAL employee outputs |
| Day 30+ | Pattern 8 (Output Contract) | Tighten output format (JSON schema, severity levels) |
| Ongoing | Pattern 2 (Text A + B) | Structure paired data for attention head comparison |

### Monthly Cycle
- Week 1-2: Collect (claude_analysis_log + Discord outputs + outcomes)
- Week 3: Analyze (Maren identifies stale/underperforming patterns)
- Week 4: Refine (swap few-shots, update domain knowledge, tighten labels)
- YOU approve all prompt changes — no unsupervised self-modification

---

## Smart Caching (4 Layers)

| Layer | What | Savings |
|-------|------|---------|
| **Anthropic prompt cache** | Identical soul file system prompts cached server-side | ~90% on system prompt tokens |
| **Local TTL cache** | Per data source staleness tolerance (injuries=15min, settlement=12hr, odds=1hr) | Skip redundant DB queries |
| **Change detection** | Hash previous check output, skip LLM if unchanged | ~50% of heartbeat calls skipped |
| **Cross-employee shared** | First employee to fetch writes to shared cache; others read | Prevents duplicate API calls |

**Estimated savings:** $9.00/mo without caching → $4.60/mo with caching (49% reduction)

---

## Database Tables (3 new for Iris)

```sql
-- Mission 1: Market Sentiment
CREATE TABLE social_signals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT NOT NULL,
    platform_id TEXT,
    author TEXT,
    content TEXT NOT NULL,
    player_name TEXT,
    team TEXT,
    market_type TEXT,
    direction TEXT,
    engagement_score INTEGER,
    hours_to_tip REAL,
    game_date TEXT,
    account_tier INTEGER,
    medical_grade INTEGER DEFAULT 0,
    collected_at TEXT DEFAULT (datetime('now')),
    classified INTEGER DEFAULT 0,
    UNIQUE(source, platform_id)
);

-- Mission 2: Competitive Research
CREATE TABLE competitive_signals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    competitor TEXT NOT NULL,
    competitor_tier INTEGER,
    source TEXT NOT NULL,
    platform_id TEXT,
    signal_category TEXT NOT NULL,
    content TEXT NOT NULL,
    title TEXT,
    engagement_score INTEGER,
    ludi_has_equivalent INTEGER,
    ludi_module_affected TEXT,
    action_priority TEXT,
    maren_notes TEXT,
    collected_at TEXT DEFAULT (datetime('now')),
    reviewed INTEGER DEFAULT 0,
    UNIQUE(competitor, source, platform_id)
);

-- Mission 3: Audience Demand
CREATE TABLE audience_signals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT NOT NULL,
    subreddit_or_channel TEXT,
    platform_id TEXT,
    signal_type TEXT NOT NULL,
    content TEXT NOT NULL,
    mentioned_competitor TEXT,
    mentioned_feature TEXT,
    mentioned_player TEXT,
    sentiment TEXT,
    engagement_score INTEGER,
    content_opportunity INTEGER,
    product_opportunity INTEGER,
    maren_notes TEXT,
    collected_at TEXT DEFAULT (datetime('now')),
    reviewed INTEGER DEFAULT 0,
    UNIQUE(source, platform_id)
);
```

---

## Weekend Setup Checklist (Mar 1, 2026)

### Telegram Bot 2 (Solomon's Channel)
- [ ] Create new Telegram bot via @BotFather → `SOLOMON_TELEGRAM_TOKEN`
- [ ] Set bot name: "Ludi PM" or "Solomon"
- [ ] Set bot description + profile picture (Ludi branding)
- [ ] Add `SOLOMON_TELEGRAM_TOKEN` and `SOLOMON_CHAT_ID` to `.env`
- [ ] Test: send message from bot to verify connectivity

### Discord Server
- [ ] Create "Ludi Informatio" Discord server (or repurpose existing)
- [ ] Create categories:
  - **EMPLOYEES**: #ops-alerts, #pipeline-qa, #code-review, #strategy, #general
  - **SOCIAL INTELLIGENCE**: #social-intel, #competitive-research, #audience-demand
  - **OPS**: #workflow-logs, #quota-tracking
  - **DEV**: #dev-chat, #testing
- [ ] Create Discord bot application → `DISCORD_BOT_TOKEN`
- [ ] Invite bot to server with read/write permissions
- [ ] Add `DISCORD_BOT_TOKEN` to `.env`
- [ ] Test: bot can post to each channel

### OpenClaw Setup
- [ ] Clone OpenClaw: `gh repo clone openclaw/openclaw`
- [ ] Review getting-started docs
- [ ] Verify macOS local runtime works
- [ ] Understand SOUL.md / HEARTBEAT.md / SKILL.md file patterns

### Project Prep
- [ ] Create `best-practices/openclaw/` folder structure:
  - `README.md` — folder index
  - `EMPLOYEE_ROSTER.md` → link to this doc
  - `SOUL_FILE_PATTERNS.md` — template + rules for writing soul files
  - `ESCALATION_RULES.md` — P0/P1/P2 severity definitions + routing
  - `CACHING_STRATEGY.md` — 4-layer caching implementation notes
  - `BERT_REFINEMENT_PLAYBOOK.md` — monthly cycle + few-shot swap process
- [ ] Add `DISCORD_BOT_TOKEN`, `SOLOMON_TELEGRAM_TOKEN`, `SOLOMON_CHAT_ID` to `.env.template`

### Kimi/Codex Decision
- [ ] Evaluate Codex ($20/mo) vs Kimi K2 ($20/mo) for primary code writing
- [ ] Set up OAuth/API access for chosen tool
- [ ] Test: can the tool read Ludi-Bot repo context?

---

## Monday Implementation Plan

**Day 1 (Mon Mar 2):** Solomon soul file + Telegram Bot 2 integration
**Day 2 (Tue Mar 3):** Silas soul file + heartbeat tasks + KNOWN_FIXES few-shot
**Day 3 (Wed Mar 4):** Vera soul file + settlement audit + brief pre-flight
**Day 4 (Thu Mar 5):** Henrik soul file + smart gating + cross-file dependency map
**Day 5 (Fri Mar 6):** Iris collection scripts (Reddit + Twitter Phase 1)
**Week 2:** Maren soul file + weekly digest + content calendar template

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-28 | Initial PRD — 6 employees fully spec'd |
