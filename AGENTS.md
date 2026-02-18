# AGENTS.md

## Purpose
This file is the central operating guide for Codex agents working in `Ludi-Bot`.

Primary objective:
- Make safe, testable, production-relevant changes that improve the NBA props analytics system without introducing data drift or workflow regressions.

---

## Project Snapshot (Date-Bound)
As of **February 16, 2026**:
- `ROADMAP.md` was last updated **February 15, 2026**
- Current phase (per roadmap): **Phase 7 - All-Star Break Sprint**
- Active work (per roadmap): **Phase 7.9 Backtest Audit**
- Truth source for current priorities: `ROADMAP.md` (not historical completion docs)

If any doc conflicts with `ROADMAP.md`, follow `ROADMAP.md` and note the mismatch in your output.

---

## Source-of-Truth Order
Use this precedence when gathering context:

1. `ROADMAP.md` (active priorities and phase)
2. `docs/ARCHITECTURE.md` (system design)
3. `docs/METHODOLOGY.md` (model logic and edge logic)
4. `docs/PRODUCTION_HANDBOOK.md` (ops behavior)
5. Code + tests (actual behavior)
6. Historical reports in `docs/archive/` and `reports/` (context only)

---

## Non-Negotiable Data Rules
- Never assume current rosters, trades, or team assignments from model memory.
- Use DB/API truth:
  - `ludi.db` tables (`players`, `player_game_logs`, `player_canonical_ids`, etc.)
  - Live sources: Tank01, Ball Don’t Lie, PBP Stats
- Before migrations or bulk update scripts:
  - run backup (`bash scripts/backup_database.sh`)
- Do not commit `ludi.db` or treat git as DB state transport.

---

## Working Style for Codex
For every task, follow this sequence:

1. Inspect
- Read only relevant files first (`rg`, targeted `sed`, focused reads)
- Identify stale-doc risk early

2. Plan
- State intended change scope
- Call out risks/regression vectors

3. Implement
- Make minimal, coherent edits
- Preserve existing architecture unless explicitly asked to refactor

4. Validate
- Run narrow tests first, then broader checks as needed
- Prefer proving changed behavior over running everything blindly

5. Report
- Summarize what changed, what was tested, and residual risk
- Include exact file references

---

## Change Safety Rules
- Never run destructive git/file commands unless explicitly requested.
- Never revert unrelated local changes.
- If unexpected unrelated modifications appear while editing, stop and ask user.
- Keep edits ASCII unless file already requires Unicode.
- Add comments only where logic is non-obvious.

---

## Testing & Verification Standard
Minimum expectation per code change:
- Run at least one targeted verification tied to the changed component.
- If tests cannot be run, explicitly say so and why.
- For pipeline-impacting changes, include a short risk note:
  - data freshness risk
  - workflow schedule risk
  - edge-calculation/regression risk

Preferred commands:
- `source .venv/bin/activate`
- `.venv/bin/python test_pipeline.py`
- `.venv/bin/python -m pytest tests/...` (targeted)
- `.venv/bin/python main.py` (only when appropriate and safe)

---

## Module Map (Quick Reference)
- A: `module_a.py` (`Gatekeeper`)
- B: `module_b.py`
- C: `module_c.py` (`LudiOracle`)
- D: `module_d.py` (`LudiYak`)
- E: `module_e.py` (`LudiCalibrator`)
- F: `module_f.py` (`LudiReporter`)
- G: `module_g.py` (`LudiRefEngine`)
- H: `module_h_historian.py` (`LudiHistorian`)
- X: `module_x_scenario.py` (`ScenarioBuilder`)

---

## Ops Commands (High-Frequency)
- Setup:
  - `python3.11 -m venv .venv`
  - `source .venv/bin/activate`
  - `pip install -r requirements.txt`
- DB:
  - `.venv/bin/python database.py`
  - `bash scripts/backup_database.sh`
  - `bash scripts/restore_database.sh`
- Pipeline:
  - `.venv/bin/python main.py`
  - `.venv/bin/python test_pipeline.py`

---

## Definition of Done
A task is done only if:
- Requested behavior is implemented
- Relevant checks/tests were run (or inability clearly reported)
- No conflict with non-negotiable data rules
- Output includes:
  - files changed
  - why change was made
  - verification performed
  - remaining risks / next step (if any)

---

## Slash Aliases (Repo-Local)
When a user message starts with one of these aliases, treat it as an explicit request to run the mapped skill workflow:

- `/sports-model` -> `.claude/skills/sports-data-model-architect/SKILL.md`
- `/sma` -> `.claude/skills/sports-data-model-architect/SKILL.md`

### How to Invoke (Examples)
Use these aliases by starting your message with the alias and your task in the same line.

- `/sma audit temporal integrity and feature coverage for current pipeline`
- `/sma review schema changes for player_game_opponent integration`
- `/sports-model propose migration-safe fixes for entity resolution drift`

Note:
- These are **repo-local alias instructions** for agents reading `AGENTS.md`.
- They are not guaranteed to appear as native slash commands in every client UI.
- Real command definitions are in `.claude/commands/sma.md` and `.claude/commands/sports-model.md`.
- CLI fallbacks are available: `scripts/sma` and `scripts/sports-model`.

Alias behavior:
- Run the audit-first balanced workflow from the mapped skill.
- Use scripts in `skills/sports-data-model-architect/scripts/` when applicable.
- Return findings first, then implementation snippets and validation checklist.
