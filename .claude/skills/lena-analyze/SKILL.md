---
name: lena-analyze
description: >
  On-demand statistical analysis of Ludi-Bot data. Queries ludi.db for pattern
  mining, archetype performance, B2B resilience, streak regression, scheme x
  archetype win rates, ref tendencies, and line movement correlation. Reports
  with sample sizes, confidence levels, and actionability assessment.
agent: lena
user-invocable: true
---

# Lena Analyze

On-demand statistical analysis powered by Lena's persistent memory and domain expertise.

## Usage
- `/lena-analyze B2B resilience for STRETCH_BIG`
- `/lena-analyze streak persistence for assists props`
- `/lena-analyze ref tendencies for RIM_GUARDIAN archetypes`
- `/lena-analyze scheme x archetype win rates for PAINT_PACK`

## What This Does

Delegates to the Lena agent, who:
1. Parses the analysis topic from `$ARGUMENTS`
2. Queries `ludi.db` using canonical name resolution
3. Computes statistics with proper sample size enforcement (N >= 20)
4. Reports findings with confidence levels (HIGH/MEDIUM/LOW)
5. Assesses actionability for Module E, Module F, and curation

---

## Execution Steps

### Step 1 — Parse Topic

Extract the analysis target from user arguments.
Identify:
- Which tables to query (see Domain Glossary in agent prompt)
- Which archetypes, schemes, or players are referenced
- What time window applies (default: current season)

### Step 2 — Query Database

Run queries against `ludi.db` using `.venv/bin/python` or `sqlite3`.

**Required**: Always use canonical name resolution before player name queries:
```python
from utils.player_id_resolver import resolve_canonical_name
```
**Required**: Use `canonical_games` for date+team JOINs (never JOIN `games` ON date + team).
**Required**: CLV analyses must filter `game_date >= '2026-02-27'` (data floor).
**Required**: Detect B2B via `LAG(game_date)` window function (no b2b column exists).

### Step 3 — Analyze and Report

Use this exact output format:

```
## Lena Analysis — [topic from $ARGUMENTS]

### Findings
[Pattern name] — [N=X games, date range, confidence: HIGH/MEDIUM/LOW]
Win rate: X% | Edge vs line: +X pts avg | Sample: N

### Actionable?
Module E: [yes/no — specific modifier proposed]
Module F: [yes/no — note or tag suggested]
Curation: [yes/no — dossier signal]

### Caveats
[Small sample warnings, survivorship bias notes, seasonal drift concerns]
```

---

## Constraints

- N < 20 = "Insufficient sample" — do not report patterns below this threshold
- No AI training data — every stat must come from `ludi.db` queries
- Every claim references a table — no unverified characterizations
- No bet recommendations — Lena reports patterns, Module F makes bets
- Task: `$ARGUMENTS`