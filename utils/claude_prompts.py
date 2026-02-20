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

GAME_NOTES_TEMPLATE = """📅 {game_label}
## {away_team} @ {home_team} | S.A.V.A.G.E.

**Game Context:**
| Factor | Value | Impact |
|--------|-------|--------|
| Spread | {spread} | {blowout_risk} |
| Total | {total} | {env_note} |
| Pace | {matchup_pace_note} | Context |
| Schedule | {schedule_notes} | {fatigue_flag} |

**Situational Intel:**
{situational_context}

**Injury Impact:**
{injury_intel_block}
{beneficiary_block}
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
- Trend: {trend_line}
- Minutes: {minutes_trend}
- L10 avg: {l10_avg} ({hit_rate_l10} hit rate)
- Streak: {streak_note}
- Edge: {edge_pct}% above line
{stagger_note}

**Why this play:**
{player} → vs {opponent} {opp_scheme} defense → in this game context.

[STOP HERE if player is OUT/DOUBTFUL — do not analyze further]

{analysis_block}

---
*Player spotlight - research only*
"""

# ------------------------------------------------------------------
# Module D — Tank01 Injury Blurb Classifier
# Haiku parses raw news blurbs into structured betting-relevant data.
# Used in module_d._ai_parse_blurb() — only fires for GTD/Day-To-Day players.
# Cost: ~$0.01/day (5-15 players, Haiku pricing)
# ------------------------------------------------------------------

INJURY_BLURB_SYSTEM = """You are an NBA injury analyst for a sports betting model.
Your job: extract structured data from raw injury news blurbs.
Focus on TONIGHT's game availability — not long-term prognosis.
Return ONLY a valid JSON object. No explanation, no markdown."""

INJURY_BLURB_PARSE_PROMPT = """Parse this NBA injury report into structured JSON.

=== EXAMPLES ===

Blurb: "Feb 5: Herro (ribs) is not traveling with the Heat for their two-game road trip"
Player: Tyler Herro
Output: {{"body_part": "ribs", "severity": "severe", "games_out_estimate": "2-4 games", "context": "ongoing", "minutes_risk": false, "tonight_available": false}}

Blurb: "Feb 7: Middleton (recently traded) is hoping to make his Mavericks debut Tuesday"
Player: Khris Middleton
Output: {{"body_part": null, "severity": "non_injury", "games_out_estimate": "1-2 games", "context": "recently_traded", "minutes_risk": true, "tonight_available": false}}

Blurb: "Feb 7: Hart (ankle) is listed as questionable for Sunday's game against the Celtics"
Player: Josh Hart
Output: {{"body_part": "ankle", "severity": "moderate", "games_out_estimate": "game_time_decision", "context": "ongoing", "minutes_risk": true, "tonight_available": "uncertain"}}

Blurb: "Feb 12: Marshall (foot) is probable for Thursday's game against the Lakers"
Player: Naji Marshall
Output: {{"body_part": "foot", "severity": "minor", "games_out_estimate": "0 games", "context": "returning_soon", "minutes_risk": true, "tonight_available": true}}

Blurb: "Feb 13: Marshall has been ruled out for the rest of Thursday's game due to a left foot strain. He collected 19 points in 29 minutes."
Player: Naji Marshall
Output: {{"body_part": "foot", "severity": "moderate", "games_out_estimate": "1-2 games", "context": "mid_game_exit", "minutes_risk": false, "tonight_available": false}}

=== YOUR TASK ===

Today's date: {today_date}
Expected return date (from official source): {inj_return_date}
Blurb: "{description}"
Player: {player_name}

STALENESS RULE: The blurb date prefix (e.g. "Jan 31:") is when the news was written.
If the blurb mentions "Saturday's game" or "tonight's game" and that date is BEFORE today → the blurb is stale.
Use the "Expected return date" field as the authoritative timeline, NOT the blurb text.
If expected return date is before today and designation is still Day-To-Day → likely returning soon, set context="returning_soon".

Fields:
- body_part: injury location (e.g. "ankle", "ribs") or null
- severity: "minor" | "moderate" | "severe" | "non_injury"
- games_out_estimate: "0 games" | "1-2 games" | "2-4 games" | "1-2 weeks" | "indefinite" | "game_time_decision"
- context: "fresh_injury" | "ongoing" | "returning_soon" | "recently_traded" | "rest" | "mid_game_exit"
- minutes_risk: true if likely on minutes restriction even if active, false otherwise
- tonight_available: true | false | "uncertain"
- blurb_is_stale: true if blurb date is more than 3 days before today, false otherwise

Return JSON only."""
