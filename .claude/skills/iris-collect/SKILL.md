---
name: iris-collect
description: >
  Social intelligence collection protocol. Collects social signals (player
  props, injury rumors, line movement chatter), competitive intelligence
  (OddsJam, Outlier, PropsMadness, etc.), and audience demand signals.
  Zero-LLM — outputs structured signal cards to Discord #iris channel.
  Trigger phrases: "iris collect", "run /iris-collect", "/iris-collect",
  "collect social signals".
user-invocable: true
phase: 8.22-pending
---

# /iris-collect — Social Intelligence Collection Protocol

## Status

WARNING: **Infrastructure pending** — Phase 8.22 Social Intelligence System. The `social_signals` DB table and collection scripts are not yet built. This skill file defines the protocol for when they are. Full architecture spec: `docs/projects/SOCIAL_INTELLIGENCE_SYSTEM.md`.

---

## Three Missions

### Mission 1: Social Signals (Player Props)

Collect public sentiment on player prop lines — injury rumors, public betting patterns, line movement chatter.

**Sources:**
- Twitter/X: `"[player] tonight" injury OR scratch OR limited`
- Reddit: `r/sportsbook`, `r/nba` — injury/lineup thread monitoring
- Action Network: public betting % and sharp money alerts

**Output format (→ Discord #iris, ID: 1477760453026517134):**
```
SIGNAL — [Player] [Stat] [Line]
Source: Twitter (T2) | Confidence: MEDIUM
Signal: Multiple credible accounts reporting limited minutes
Impact: Consider UNDER if lineup confirmed
```

---

### Mission 2: Competitive Intelligence

Track what analytics platforms are building and shipping.

**Competitors to monitor:** OddsJam, Outlier, Action Network, PropsMadness, BucketsToBucks, StraightBettin

**6 intelligence tiers:**
1. Product launches — new features, new markets
2. Methodology signals — what models/approaches they're highlighting
3. Pricing changes — tier changes, free trials
4. Partnership signals — data source deals, sportsbook integrations
5. Community sentiment — user praise/complaints about features
6. Market positioning — how they frame value vs competitors

**2x2 signal matrix:**
| | High Ludi Impact | Low Ludi Impact |
|---|---|---|
| **Confirmed** | Escalate immediately | Log for weekly |
| **Rumored** | Track & verify | Drop |

---

### Mission 3: Audience Demand

What are bettors asking for that nobody builds?

**Sources:** `r/sportsbook` feature requests, Twitter prop betting community, public sports analytics Discord servers.

**Output:** Weekly digest only — no immediate escalation.

---

## Signal Quality Rules

- Never report raw tweet count — require >3 credible independent sources
- Always include confidence rating: HIGH / MEDIUM / LOW
- Mark anything from paid sources (Action Network Pro) as T1
- Discard automated tweet farms and accounts with <500 followers
- Flag when prop line moves >=0.5 after a social signal (confirms the signal)

---

## Signal Tiers

| Tier | Definition | Escalation |
|------|-----------|-----------|
| T1 | Sharp money (paid sources, sharp book line moves) | Immediate to #iris |
| T2 | Credible source (verified accounts, local beat reporters) | Immediate to #iris |
| T3 | Crowd signal (multiple casual mentions) | Weekly digest only |
| T4 | Noise (single source, <500 followers, no corroboration) | Drop |

---

## Saturday Digest Format (→ #weekly-roundtable)

```
## Iris Weekly Digest — Week of [date]
Signals collected: [N total] (T1: [N], T2: [N], T3: dropped)
Top 2-3 trends flagged: [brief]
Competitor moves worth noting: [brief]
Audience demand themes: [brief]
```

---

## Full Signal Message Format

```
IRIS SIGNAL — 2026-03-01 14:30 EST
Type: Social (Mission 1) | Tier: T2 | Confidence: HIGH
Player: [Name] | Market: Points O/U 28.5
Signal: Action Network showing 72% money on OVER (sharp line move -3 to -1.5)
Recommended action: Flag OVER — steam move candidate
```

---

## When Built: Implementation Notes

- DB table: `social_signals` (Phase 8.22) — schema TBD in `docs/projects/SOCIAL_INTELLIGENCE_SYSTEM.md`
- Downstream consumer: `scripts/curate_plays.py` Phase 8.22 Prop Pulse Score
- Discord webhook: #iris channel (server ID: 1477758118921371688)
- Scheduling: launchd for intraday collection (no GH Actions — too slow for social signals)
- Reference table: `prop_line_snapshots` — cross-reference signal timing vs line movement
