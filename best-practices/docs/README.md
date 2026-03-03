# Documentation Maintenance Best Practices

**Status:** ✅ Complete (March 2, 2026)

This guide codifies how all project docs are maintained — not just `MEMORY.md`. It is the single reference for "how do we keep docs clean?" across the whole project.

---

## Quick Reference

| Rule | Summary |
|------|---------|
| README ≠ STATUS_HISTORY | Implementation details → STATUS_HISTORY.md; README shows what, not how |
| ROADMAP ≠ git log | Ops notes are event logs; remove after resolved |
| MEMORY.md ≠ comprehensive notes | Newest entries at top; detailed notes go in topic files |
| `[x]` tasks don't age well | Remove from active lists within 1 session of completion |
| One truth per doc | If ROADMAP.md has it, README.md should reference it, not duplicate it |

---

## Permanent Sections (never trim or delete)

These sections must survive all future sessions — agents should never trim them as "bloat."

| Doc | Section | Reason |
|-----|---------|--------|
| `README.md` | `## Project Vision` | Institutional memory — project origin, thesis, current state, direction |
| `CLAUDE.md` | `## Known Gotchas` | Active safety rules that prevent recurring bugs |
| `CLAUDE.md` | `## Automation Schedule` | Ground truth for all workflow timing |
| `ROADMAP.md` | `**Agent Template Contract**` | PM bot parser contract — breaking it breaks Telegram messages |

**Protection pattern for README.md Project Vision:**
```html
<!-- PERMANENT SECTION — DO NOT REMOVE OR MOVE. Update content periodically, never delete. -->
## Project Vision
```

---

## Auto-Maintained Sections (agent-written, not human-written)

| Doc | Section | Owner | Frequency |
|-----|---------|-------|-----------|
| `memory/MEMORY.md` | All entries | Any session | Every session |
| `best-practices/ops-hub/KNOWN_FIXES.md` | All entries | `claude-ops-hub.yml` | On every workflow diagnosis |

---

## Trim Triggers (when content should be removed)

| Doc | Trim When |
|-----|-----------|
| `ROADMAP.md` Ops Notes | >7 days old with no ongoing relevance |
| `ROADMAP.md` `[x]` Next Actions | Task verified complete + appears in `**Completed:**` header |
| `README.md` Phase 8 completions table `Infra` rows | Any single row has >1 sentence of prose detail |
| `memory/MEMORY.md` | Any entry that would push the file past 200 lines |
| `docs/STATUS_HISTORY.md` | Never — it's the archive; append only, never trim |

---

## Line Limits

| Doc | Limit | What to do when over |
|-----|-------|---------------------|
| `memory/MEMORY.md` | 200 lines (hard cap) | Compress multi-bullet entries; push old entries to topic files under `memory/` |
| `README.md` Phase 8 table | ~30 rows | Trim inline prose to 1 sentence max per row |
| `ROADMAP.md` Next Actions | ~8 active bullets | Remove `[x]` items; archive completed sprints to STATUS_HISTORY.md |

---

## Update Frequency by Doc

| Doc | How often | Trigger |
|-----|-----------|---------|
| `ROADMAP.md` header | Every session | `/session-debrief` Step 3 |
| `README.md` Status section | Every major phase completion | New sub-phase ships |
| `README.md` Project Vision | Quarterly or major evolution | Manually when direction changes |
| `CLAUDE.md` Known Gotchas | When new gotcha discovered | During or after debugging |
| `best-practices/` category docs | When new pattern confirmed | After second occurrence of the pattern |
| `docs/STATUS_HISTORY.md` | Append only | End of major sprints |

---

## Anti-Bloat Rules

1. **README ≠ STATUS_HISTORY** — Implementation details belong in STATUS_HISTORY.md; README shows what, not how
2. **ROADMAP ≠ git log** — Ops notes are event logs; remove after resolved
3. **MEMORY.md ≠ comprehensive notes** — Newest entries at top; detailed notes go in topic files under `memory/`
4. **`[x]` tasks don't age well** — Remove from active lists within 1 session of completion
5. **One truth per doc** — If ROADMAP.md has it, README.md should reference it, not duplicate it

---

## README.md Phase 8 Table Format Standard

Each `Infra` or feature row: **one sentence max.** The sentence should capture *what shipped*, not *how it was implemented*.

```
✅ Good:  | Infra | Module Audit Sprint (A–F) — pre-load pattern enforced; zero-DB sim loop; USG_PCT key fix |
❌ Bad:   | Infra | Module Audit Sprint (A–F) — `LudiOracle` 8 pre-load dicts + zero-DB 10K sim loop; `LudiCalibrator` bulk pre-loads (DVP, B2B splits, archetype matrix); `LudiYak` news_agent + INJURY_RETURN edge type; `USG_PCT` key fix; `LudiReporter` avg_ev fix + `_STAT_COL_MAP` short-form aliases + L5/L10/L15 hit rates |
```

Full implementation details live in `docs/STATUS_HISTORY.md`. The README row is a pointer, not a document.

---

**Last Updated:** March 2, 2026
