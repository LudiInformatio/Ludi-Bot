"""
LUDI INFORMATIO | CLAUDE PROMPTS
================================
Context engineering rules:
- Data first, instructions last (Claude reads top-to-bottom)
- Only inject data for players IN THIS GAME (never full DB)
- Pre-format data as clean text blocks (not raw JSON)
- system= holds role + ROSTER_RULES + constraints; user= holds game data + question
- Keep system prompt identical across calls of same type (enables Anthropic caching)

Created: February 2026
Purpose: Phase 8 AI Integration for Ludi-Bot
"""

ROSTER_RULES = """
=== CRITICAL: ROSTER VERIFICATION ===
**BEFORE listing any player, check the injury report above.**
- If a player is listed as OUT, SUSPENDED, DOUBTFUL, or INACTIVE → DO NOT MENTION THEM
- NEVER put injured/suspended players in "Players to Watch"
- Only include players who are ACTIVE or PROBABLE
- If unsure, say "status unclear" instead of assuming healthy
"""

ANALYSIS_PROTOCOL = """
ANALYSIS PROTOCOL (follow in order):
1. VERIFY: Cross-check injury list
2. GROUND: Cite source ("per BDL", "per Tank01", "per Odds-API")
3. REASON: Apply factors step-by-step
4. CONCLUDE: Only claims supported by steps 1-3
5. FLAG: Note uncertainty with "Unverified"

DATA CITATION RULES:
- Stats = "Season avg (BDL): X" or "L10 avg (ludi.db): X"
- Injuries = "Per BDL injury report: OUT" or "Per Tank01 roster: OUT"
- Odds = "Line (Odds-API): -4.5"
- News = "Per Perplexity: [source]"
- IF NO DATA: Say "Data not available" — DO NOT INVENT

BEFORE SUBMITTING, verify:
- No OUT/SUSPENDED players mentioned as active
- No stats cited without a data source
- No references to prior seasons rosters
- All numbers match the injected data above
"""

GAME_NOTES_TEMPLATE = """## {away_team} @ {home_team} | S.A.V.A.G.E.

**Game Context:**
| Factor | Value | Impact |
|--------|-------|--------|
| Spread | {spread} | {blowout_risk} |
| Total | {total} | {pace_context} |
| Schedule | {schedule_notes} | {fatigue_flag} |

**Injury Impact:**
{injury_intel_block}
[Format: "OUT: {player} ({days_out}d {injury_type}) → {beneficiary} +{boost} {stat} proj"]
[Or: "GTD: {player} ({injury_type}) — {update_time} update critical"]

**Scheme Edge:**
- {away_team} ({away_archetype_summary}) vs {home_team} ({home_def_scheme}): {one_sentence}
- {home_team} ({home_archetype_summary}) vs {away_team} ({away_def_scheme}): {one_sentence}

**Key Edges Today:**
{edges_block}
[Format: "{player} {stat} — {edge_reason} ({edge_pct}% above line)"]

---
*S.A.V.A.G.E. analysis - research only*
"""

SPOTLIGHT_TEMPLATE = """## {player} | {team} vs {opponent}

{player} {stat} ({line}) — {tier} tier play vs {opp_scheme} defense.

**Context:**
- Archetype: {archetype}
- Opponent scheme: {opp_scheme}
- Injury status: {injury_context}
- L10 avg: {l10_avg} ({hit_rate_l10} hit rate)
- Edge: {edge_pct}% above line

**Why this play:**
{player} → vs {opponent} {opp_scheme} defense → in this game context.

[STOP HERE if player is OUT/DOUBTFUL — do not analyze further]

{analysis_block}

---
*Player spotlight - research only*
"""
