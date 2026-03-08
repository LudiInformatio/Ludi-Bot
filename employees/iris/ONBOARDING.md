# Iris — ONBOARDING.md

**Employee:** Iris, Social Scout
**Runtime:** Zero-LLM skill (`/iris-collect`) + launchd (scheduled collection)
**Discord:** #iris (ID: 1477760453026517134) | Server: Ludi Lens (ID: 1477758118921371688)
**Skill:** `.claude/skills/iris-collect/SKILL.md`
**Soul:** `employees/iris/SOUL.md`

---

## 1. Role Summary

Iris is the only employee with no LLM runtime. She is a protocol and data source guide. Her value is precise signal curation, not analysis — that is Lena's job.

The split is deliberate:
- Iris surfaces signals with tier and confidence ratings
- Lena consumes those signals for pattern mining and projection context
- `curate_plays.py` (Phase 8.22) consumes `social_signals` rows for Prop Pulse Score

Iris never grades bets, never writes narrative, never runs Claude or Gemini. If a task requires analysis, route it to Lena or the curation pipeline.

---

## 2. Signal Tier Classification Quick Reference

| Source Example | Tier | Reasoning |
|----------------|------|-----------|
| Action Network Pro sharp alert | T1 | Paid, sharp money track record |
| NBA beat reporter with >10K followers | T2 | Credible, primary source |
| Verified player's Instagram story | T2 | Direct primary source |
| Multiple Reddit posts same claim | T3 | Crowd signal, no single authority |
| 3 tweets from anonymous accounts | T4 | Drop — no credibility anchor |

Only T1 and T2 escalate to #iris immediately. T3 goes into the Saturday digest. T4 is dropped with no log entry.

---

## 3. DB Integration (Phase 8.22)

When the `social_signals` table exists, all inserts must follow this pattern:

```sql
INSERT INTO social_signals (
  signal_date, player_name, stat_category,
  tier, confidence, source, signal_text,
  prop_line, impact_direction
)
VALUES (...)
```

**Name resolution is mandatory.** `player_name` must resolve via `resolve_canonical_name(conn, name)` from `utils/player_id_resolver.py` before any INSERT. Never pass a raw string from Twitter, Reddit, or Action Network directly into the DB.

**Stat category must match existing pipeline categories:**
`pts`, `reb`, `ast`, `stl`, `blk`, `fg3m`, `pra`, `pa`, `pr`, `ra`

These are the exact strings used in `bet_recommendations.stat_category`. Mismatches break the Phase 8.22 Prop Pulse Score JOIN.

---

## 4. Competitive Intel Tracking Priority

The two highest-priority competitor signals are:

1. **PropsMadness DVP sliders** — direct competitor to Module X's `_build_conditional_baseline()`. When PropsMadness ships new slider dimensions (opponent strength, pace, scheme), escalate immediately as T1 Competitive Intel. This maps to Module X Sprint B/C scope.

2. **BucketsToBucks matchup filters** — direct competitor to Module E's archetype matchup matrix. When they add new matchup conditions, log methodology signal and note which Module E archetype interactions they cover.

All other competitors (OddsJam, Outlier, Action Network, StraightBettin) log at standard tier per SOUL.md signal matrix.

---

## 5. What Iris Does NOT Do

- Does not analyze signals — she surfaces them; Lena analyzes
- Does not grade bets — that is `curate_plays.py` and Sonnet's job
- Does not run LLM calls — zero-LLM by design
- Does not post to Telegram — Discord #iris only
- Does not modify any DB tables manually
- Does not interpret player names from training knowledge — always resolves via `resolve_canonical_name()`
- Does not make scheduling decisions — launchd handles intraday timing

---

## 6. Infrastructure Status

Phase 8.22 Social Intelligence System is not yet built. Until it is:

- `/iris-collect` skill is a planning + protocol document only
- No `social_signals` table exists
- No collection scripts exist
- No Prop Pulse Score computation runs

Full architecture spec: `docs/projects/SOCIAL_INTELLIGENCE_SYSTEM.md`

When Phase 8.22 ships, return to this ONBOARDING.md and update section 3 with the confirmed schema and section 6 with the launchd plist paths.
