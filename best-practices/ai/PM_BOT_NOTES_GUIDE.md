# PM Bot Notes Guide — Writing ROADMAP Context for Gemini

**Created:** February 27, 2026
**Purpose:** How to write `ROADMAP.md` header lines so the PM bot generates specific, grounded messages instead of generic NBA trivia.

---

## Why Note Quality Determines Message Quality

The PM bot injects your ROADMAP lines directly into Gemini prompts. Gemini can only be as specific as what you wrote — it has no access to the codebase, DB, or history. This is the same grounding principle from BERT Pattern 3 (few-shot proxy): **the context you provide is the fine-tuning signal.**

| You write vague notes | You write specific notes |
|---|---|
| "Working on module audit" | "Module F Audit (`LudiReporter`, `module_f.py`) — devigging + edge calc → alt line sweep next" |
| Gemini invents NBA trivia | Gemini references actual sprint work |

---

## The Three Injected Fields

### 1. `**Active Work:**` → THE INTEL (morning) + THE PIVOT (nightly)

This is the most important line. It becomes the sprint context Gemini uses to write THE INTEL insight and THE VIBE closing.

**Formula:**
```
[Module/Feature] ([file or class]) — [what specifically] → [next milestone]
```

**Bad examples:**
```
**Active Work:** Module audit + backfill
**Active Work:** Working on F
**Active Work:** Sprint ongoing
```

**Good examples:**
```
**Active Work:** Module F Audit (`LudiReporter`, `module_f.py`) — devigging + edge calc + alt line sweep
**Active Work:** Module F Audit (`LudiReporter`) — alt line sweep (±1.5/±3.0) next + edge_type labels
**Active Work:** Phase 8.22 Social Intel — `social_signals` schema + Prop Pulse Score pipeline
```

**Multi-item format** (separate with ` + `):
```
**Active Work:** Module F Audit (`LudiReporter`) — devigging review + Phase 8.23 Layer 1 collecting (~Mar 10)
```
The PM bot reads the first segment as `in_progress[0]` for break messages. Keep the primary sprint item first.

---

### 2. `**Completed:**` → THE WINS (nightly)

These become the bullet points under THE WINS. Three most recent items, separated by ` + `.

**Formula:**
```
[Module/Feature] ([key sub-items in parens]) ✅
```

**Bad:**
```
**Completed:** Module E done + Module D fixed + Module C audit
```

**Good:**
```
**Completed:** Module E Calibrator Audit (bulk pre-loads, DVP, B2B splits) ✅ + Module D Yak Audit (news_agent, INJURY_RETURN, ghost resolve) ✅ + Module C Oracle Audit (Tiers A-F + G1-G4) ✅
```

**Rule:** Keep exactly 3 segments — the PM bot parser reads `parts[-3:]`. Never collapse into one.

---

### 3. `- [ ]` bullets under `**Next Actions:**` → THE BLUEPRINT (morning)

Morning THE BLUEPRINT shows `pending[:3]`. These bullets should be actionable and specific enough to give Gemini context about *what kind of work* is happening.

**Formula:**
```
[Action verb] [specific target] in `[file]` — [what exactly changes]
```

**Bad:**
```
- [ ] Fix module f
- [ ] Add alt lines
- [ ] Research follow-up
```

**Good:**
```
- [ ] Alt line edge sweep in `module_f.py` — sweep ±1.5/±3.0 per player, surface best-value alt in bet card
- [ ] Surface `player_injuries.snapshot_time` in `morning_brief.py` — "OUT (updated 5:18 PM)" format
- [ ] Add `edges` intent to `bots/ask_ludi_db.py` — "Check [Player] [Line]" returns 11-row scorecard
```

---

## Quick Reference: What Gets Injected Where

| ROADMAP field | PM bot reads it as | Injected into |
|---|---|---|
| `**Active Work:**` first segment | `in_progress[0]` | Morning THE INTEL + Nightly THE PIVOT + Break STATE |
| `**Active Work:**` first 2 segments | `in_progress[:2]` | Morning THE INTEL `active_bullets` |
| `**Completed:**` last 3 ` + ` segments | `completed[:3]` | Nightly THE WINS bullets |
| `**Next Actions:** - [ ]` top 3 | `pending[:3]` | Morning THE BLUEPRINT bullets |
| `**Next Actions:** - [ ]` top 1 | `pending[0]` | Nightly THE PIVOT "Tomorrow:" |
| `**Current Phase:**` | `current_phase` | Morning THE VISION (fallback for active_bullets if empty) |

---

## The BERT Principle Applied

In BERT, the model can't learn from vague training labels. "positive/negative" with no examples = random output. Same here: Gemini can't produce sprint-specific insights from vague input.

**BERT fine-tuning rule → Note-writing rule:**

| BERT | Notes |
|---|---|
| Define label space before data | State module/file name before the description |
| Few-shot examples = highest ROI | Specific names (class, file, feature) are the "examples" |
| `text_a` (history) + `text_b` (context) | Past sprint (Completed) + active sprint (Active Work) |
| `max_seq_length` truncation | Keep Active Work under ~200 chars per segment |

---

## Updating ROADMAP at Session End

At the end of each session (or when running `/session-debrief`):

1. **Active Work** → update to reflect what's actually in progress right now, not what was in progress yesterday
2. **Completed** → move finished items here immediately (rotate out the oldest)
3. **Next Actions** → add specific `- [ ]` bullets for what's next, not just phases

The PM bot reads these live every time it runs — stale lines = stale messages.
