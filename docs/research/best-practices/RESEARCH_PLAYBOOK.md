# Competitive Research Playbook

**Purpose:** How to run a Ludi competitive research sprint. Follow this template for every new platform audit.

---

## Pre-Research Checklist

- [ ] Platform access confirmed (free trial, public, or login ready)
- [ ] Playwright MCP tools loaded (`browser_install` if first time)
- [ ] Target doc created at `docs/research/competitive/[PLATFORM]_RESEARCH_YYYY.md`
- [ ] Research questions written (see template below)
- [ ] 2–3 hour uninterrupted block available for paid tiers; 30–60 min for public

---

## 4-Dimension Audit Framework

Every platform section must be audited across these 4 lenses:

### 1. Feature Inventory
- Screenshot + describe every major section
- For each section: what data is shown, display format, interactions available
- Note: columns, sorting, filtering, time windows

### 2. UX Patterns
- "First thing you see" on login
- How does the user discover value?
- How are high-confidence bets visually distinguished from low?
- What is the primary call-to-action?
- What does the upsell/paywall pitch say?

### 3. Data Signals
- What math/methodology is exposed?
- Is the model shown, hidden, or hinted at?
- What edge/EV formula clues can be reverse-engineered from outputs?
- What sharp books do they use as benchmarks?

### 4. Ludi Action
For every feature: **Build | Already Have | Out of Scope** + Priority (1/2/3)

---

## Research Questions Template

Customize per platform, but always answer:

| Question | Why It Matters |
|----------|----------------|
| How does the EV/edge feed rank/sort bets? | Shows their signal hierarchy |
| Which sharp books are used as benchmarks? | Informs our CLV infrastructure |
| How is edge % displayed (number/tier/grade)? | UI pattern for Ludi Lens |
| Is there a sample-size/confidence indicator? | Stat confidence grade parallel |
| How do they handle injury updates? | Compare to our Module D |
| How are correlated props handled? | SGP risk display patterns |
| What does line movement look like? | Steam move detection UX |
| What's behind the paywall vs free? | Upsell strategy |
| What's their filter system? | Filter UI patterns for Ask Ludi |

---

## Output Format

Match the existing `competitive/BETIQ_TEAMRANKINGS_RESEARCH.md` format exactly:

```markdown
# [Platform] Research Sprint
**Date:** [date]
**Sessions:** [N]
**Access:** [free trial / public / paid subscription]
**Purpose:** [1 line]

---
## Sites Researched
## [Platform] Feature Inventory  (screenshot + table per section)
## Live Data Examples             (real bets captured during session)
## UX Patterns Observed
## Data Signal Analysis
## Feature Gap Analysis           (Feature | Ludi Has? | Priority | Notes)
## Implementation Roadmap         (Tier 1 / 2 / 3 actions)
## Ludi Actions Summary           (3–5 bullets, most impactful first)
```

---

## Session Notes Tips

- Take a screenshot at every major section before clicking away
- For filter panels: document every filter option name and range
- For live bet examples: capture player name, line, book, EV%, probability, Kelly size
- For modals/tooltips: hover over every `ⓘ` info icon to capture methodology hints
- "UI inspiration" section: capture any pattern useful for Ask Ludi bot UX

---

## Post-Research Checklist

- [ ] Doc saved at `docs/research/competitive/`
- [ ] `docs/research/README.md` table updated with platforms + key Ludi actions
- [ ] Top 3 "Ludi Actions" added to `ROADMAP.md` if actionable
- [ ] `CLAUDE.md` reference updated if doc is a primary reference
- [ ] Memory updated with key architectural decisions
