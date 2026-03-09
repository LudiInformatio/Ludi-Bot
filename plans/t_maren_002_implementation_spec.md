# T-Maren-002 Implementation Spec
**Date:** March 9, 2026
**Author:** Solomon (PM)
**Status:** APPROVED FOR IMPLEMENTATION
**Target file:** `scripts/curate_plays.py`
**Auditor:** Henrik (required before ship)

---

## Context

Maren's prompt redesign (v1) was reviewed and approved with one correction:

- **Scheme correction applied by Solomon**: Maren's Example 2 used `CLE is PAINT_PACK` which is the stale `season_style`. Investigation 1 confirmed `CLE active_style = PERIMETER`. The spec below uses the correct `PERIMETER` value.
- All other content from `plans/maren_prompt_redesign_v1.md` is approved as-is.

---

## Edit 1 — `_get_system_wr_context()` — Lines 353–359

**Replace the two header lines in the `lines = [...]` initialization:**

Current (L357–358):
```python
    lines = [
        "LUDI-BOT EMPIRICAL WIN RATES (this season, Wilson 95% confidence floor):",
        "Use these to break selection ties. High raw edge ≠ reliable bet for high-variance stats.",
    ]
```

Replace with:
```python
    lines = [
        "LUDI-BOT EMPIRICAL WIN RATES (this season, Wilson 95% confidence floor):",
        "",
        "NOTE: The win rate data below is MEASURED historical outcome data from our settled bet database",
        "(4,207 bets). It is NOT generated or estimated. ANALYSIS_PROTOCOL rule 7 ('Do NOT generate",
        "win rates') does not apply here — these are injected empirical facts, not model-produced claims.",
        "Treat this table with the same authority as a stat injected from player_game_logs.",
        "",
        "WEIGHTING RULE — read WR grade FIRST, before edge%, before matchup:",
        "  A+ grade (floor >= 60%, n >= 500): WR is the primary signal. STRONG unless injury or",
        "      extreme correlation conflict overrides. Edge% is confirming evidence, not deciding factor.",
        "  A  grade (floor >= 55%, n >= 150): Prefer STRONG. Edge% must be >= 5% to confirm.",
        "  B  grade (floor >= 50%, n >= 50):  Default LEAN. Needs edge% >= 10% + clean matchup for STRONG.",
        "  C  grade (floor >= 45%):           Neutral. Grade by edge% and matchup normally.",
        "  D  grade (floor >= 40%):           Default LEAN. Needs overwhelming evidence for STRONG.",
        "  F  grade (floor < 40%):            Default FADE. Only structural factors can override to LEAN.",
        "",
        "WHY THIS MATTERS: Our data shows 4,207 settled bets. True_edge has near-zero correlation with",
        "outcome for high-edge bets (Amen Thompson PTS OVER 109.2% edge → LOSS). Wilson floor is the",
        "only statistically validated predictor we have. Edge% measures model conviction, not market",
        "efficiency. Grade WR first.",
    ]
```

---

## Edit 2 — `_get_system_wr_context()` — n-guard threshold

**Replace the HAVING clause in the SQL query from n >= 50 to tiered labels.**

Current (L343–352 — the `rows = conn.execute(...)` block):
```python
        rows = conn.execute("""
            SELECT stat_category, bet_side,
                   COUNT(*) as n,
                   ROUND(100.0 * SUM(CASE WHEN outcome='WIN' THEN 1 ELSE 0 END) / COUNT(*), 1) as wr,
                   SUM(CASE WHEN outcome='WIN' THEN 1 ELSE 0 END) as wins
            FROM bet_recommendations
            WHERE outcome IN ('WIN','LOSS')
            GROUP BY stat_category, bet_side
            HAVING COUNT(*) >= 50
            ORDER BY wr DESC
        """).fetchall()
```

Replace `HAVING COUNT(*) >= 50` with `HAVING COUNT(*) >= 5` (lower gate — tiered labels handle the rest):
```python
        rows = conn.execute("""
            SELECT stat_category, bet_side,
                   COUNT(*) as n,
                   ROUND(100.0 * SUM(CASE WHEN outcome='WIN' THEN 1 ELSE 0 END) / COUNT(*), 1) as wr,
                   SUM(CASE WHEN outcome='WIN' THEN 1 ELSE 0 END) as wins
            FROM bet_recommendations
            WHERE outcome IN ('WIN','LOSS')
            GROUP BY stat_category, bet_side
            HAVING COUNT(*) >= 5
            ORDER BY wr DESC
        """).fetchall()
```

---

## Edit 3 — `_get_system_wr_context()` — tiered n-guard output format

**Replace the single `lines.append(...)` in the for loop with tiered logic.**

Current (L379–381):
```python
        lines.append(f"  {stat} {side}: {wr:.0f}% WR (95% floor={lb*100:.0f}%, n={n}) [{grade}]{flag}")
```

Replace with:
```python
        if n >= 100:
            lines.append(f"  {stat} {side}: {wr:.0f}% WR (95% floor={lb*100:.0f}%, n={n}) [{grade}]{flag}")
        elif n >= 20:
            direction = "above" if wr >= 50 else "below"
            lines.append(f"  {stat} {side}: {wr:.0f}% WR (EMERGING — n={n}, direction={direction} 50%, treat as supporting signal) [{grade}*]")
        else:
            lines.append(f"  {stat} {side}: {wr:.0f}% WR (WATCH — n={n}, too small for statistical grade)")
```

**Also add these two lines to the KEY CALIBRATION NOTES block (after the existing notes):**
```python
        "- EMERGING (*) signals: directional only — use to confirm an otherwise strong grade, not to create one.",
        "- WATCH signals: count too small for any statistical inference — note only, do not weight.",
```

---

## Edit 4 — `_sonnet_curate()` — output schema: add `thinking` field

**Replace the OUTPUT SCHEMA line in system_prompt:**

Current (L472):
```python
    system_prompt += '\n\nOUTPUT SCHEMA — return ONLY valid JSON, no other text:\n[{"bet_id": 123, "grade": "STRONG|LEAN|FADE", "reasoning": "one sentence"}]'
```

Replace with:
```python
    system_prompt += '\n\nOUTPUT SCHEMA — return ONLY valid JSON, no other text:\n[{"bet_id": 123, "thinking": "WR grade: [grade]. Edge: [edge]. Matchup: [summary]. Decision: [why].", "grade": "STRONG|LEAN|FADE", "reasoning": "one sentence"}]'
```

**IMPORTANT:** Also update the JSON parsing block in `_sonnet_curate()` to capture the `thinking` field. Find the section where `result.append(...)` is called and add `'thinking': item.get('thinking', '')` to the dict:

Current result.append pattern (approximately L543):
```python
                result.append({
                    'bet_id': bet_id,
                    'grade': grade,
```

Add `'thinking'` after `'grade'`:
```python
                result.append({
                    'bet_id': bet_id,
                    'grade': grade,
                    'thinking': item.get('thinking', ''),
```

---

## Edit 5 — `_sonnet_curate()` — replace curate_examples block

**Replace the entire `curate_examples` string (L439–471):**

Current:
```python
    curate_examples = """
=== CURATION EXAMPLES ===
[STRONG]
Input: [TWO_LEVEL_SCORER] PTS OVER 22.5 | DIAMOND | edge=16.2% | game=TEAM1_TEAM2 | Injury: No active record
Reasoning: Diamond edge combined with favorable defensive matchup and strong L5 form makes this a top priority.
Grade: STRONG

[LEAN]
Input: [WARRIOR_BIG] BLK UNDER 1.5 | BLUE CHIP | edge=11.8% | game=TEAM3_TEAM4 | Injury: No active record
Reasoning: Strong system signal for BLK UNDER, but opponent has high rim frequency which limits confidence to a LEAN.
Grade: LEAN

[FADE]
Input: [JUMBO_FACILITATOR] AST UNDER 8.5 | CORE ASSET | edge=9.1% | game=TEAM5_TEAM6 | Injury: No active record
Reasoning: Low edge on a high-variance stat with a ref crew that tends to let teams play; better options available.
Grade: FADE
=== END EXAMPLES ===
"""
```

Replace with (NOTE: CLE scheme is PERIMETER — Solomon-verified from active_style in DB 2026-03-09):
```python
    curate_examples = """
=== CURATION EXAMPLES ===

=== EXAMPLE 1 — BLK UNDER: A+ WR grade overrides yellow matchup flag (→ STRONG) ===
Input:
  Player: Jayson Tatum [BOS]
  Bet: BLK UNDER 0.5
  True edge: 34.9% | Tier: DIAMOND
  Archetype: TWO_LEVEL_SCORER
  Injury status: No active record
  Game context: BOS vs MIA, spread BOS -4.5, total 222.5
  Note in dossier: MIA ranks 3rd in rim frequency this season

Reasoning chain (consult WR grade FIRST):
  Step 1 — WR grade: BLK UNDER = A+ (Wilson floor 67.1%, n=918). Primary signal.
           Action: Default to STRONG unless hard override applies.
  Step 2 — Edge confirms: 34.9% DIAMOND edge. Strongly confirms the WR signal.
  Step 3 — Matchup flag: MIA high rim frequency could produce 1 block. Yellow flag, not red.
           At A+ WR grade, a yellow flag does NOT override to LEAN. Would need proven block
           frequency in Tatum's own log (he averages 0.5 BLK/g — structural UNDER holds).
  Step 4 — Grade: STRONG. WR primary signal + DIAMOND edge + acceptable matchup risk.

thinking: "WR grade for BLK UNDER: A+ (67.1% floor, n=918). Edge confirms at 34.9% DIAMOND. MIA rim freq is yellow flag but does not override A+ grade. Grade: STRONG."
Grade: STRONG
Reasoning: BLK UNDER A+ empirical signal (67.1% floor, 918 bets) + DIAMOND edge confirms. Opponent rim frequency is a yellow flag but does not override A+ WR grade.
=== END EXAMPLE 1 ===

=== EXAMPLE 2 — PTS OVER: extreme edge% does NOT override absent WR (→ FADE) ===
Input:
  Player: Amen Thompson [HOU]
  Bet: PTS OVER 16.5
  True edge: 109.2% | Tier: DIAMOND
  Archetype: SLASHING_CREATOR
  Injury status: No active record
  Game context: HOU vs CLE, spread HOU -2.5, total 228.0
  Note in dossier: CLE defensive scheme = PERIMETER

Reasoning chain (consult WR grade FIRST):
  Step 1 — WR grade: PTS OVER does NOT appear in the A+/A/B section of the WR table.
           Absent from established WR table = D grade. No confirmed empirical edge.
  Step 2 — Edge check: 109.2% is an extreme outlier. ALERT: edge outliers >= 50% indicate
           volatile market conditions. They do NOT indicate a high-probability outcome.
  Step 3 — Matchup: CLE scheme is PERIMETER. Thompson is SLASHING_CREATOR — perimeter
           defense is neutral-to-negative for slash + drive volume. Neutral matchup signal.
  Step 4 — Grade: FADE. D-grade WR + extreme edge outlier flag. Edge% alone never makes STRONG.

thinking: "WR grade for PTS OVER: absent from established table (D grade). Edge 109.2% is an outlier flag, not a signal. CLE PERIMETER = neutral matchup for SLASHING_CREATOR. Grade: FADE."
Grade: FADE
Reasoning: PTS OVER has no confirmed empirical edge in this system (absent from WR table). Extreme edge outlier (109.2%) signals market volatility, not probability certainty.
=== END EXAMPLE 2 ===

=== EXAMPLE 3 — PR UNDER: emerging signal, small n, handled correctly (→ STRONG with note) ===
Input:
  Player: Cooper Flagg [DAL]
  Bet: PR UNDER 25.5
  True edge: 38.8% | Tier: DIAMOND
  Archetype: TWO_LEVEL_SCORER
  Injury status: No active record
  Game context: DAL vs BKN, spread DAL -6.5, total 224.0

Reasoning chain (consult WR grade FIRST):
  Step 1 — WR grade: PR UNDER = C grade overall (Wilson floor 45.9%, n=404).
           HOWEVER: PR UNDER STRONG grade cases show 85.7% WR (EMERGING, n=7).
           This is a curation-conditional signal — grading LEAN destroys it (38.5% WR, n=26).
           Grading STRONG when factors align is the correct behavior.
  Step 2 — Edge confirms: 38.8% DIAMOND. Strong model conviction.
  Step 3 — Matchup: BKN is PERIMETER scheme. Flagg TWO_LEVEL_SCORER attacks paint + mid.
           Perimeter defense = neutral for Flagg volume. Blowout risk: DAL -6.5, below 7.5 threshold.
  Step 4 — n-guard check: PR UNDER STRONG n=7 is WATCH-tier. Apply uncertainty note in reasoning.

thinking: "WR grade: PR UNDER C overall, but STRONG grade cases = 85.7% WR (WATCH n=7). Grading LEAN destroys signal. DIAMOND edge + neutral matchup confirms. Grade: STRONG with EMERGING note."
Grade: STRONG
Reasoning: PR UNDER with STRONG curation shows 85.7% WR (WATCH, n=7) — grading LEAN destroys signal. DIAMOND edge + neutral matchup confirm. EMERGING signal — confidence interval wide, verify context.
=== END EXAMPLE 3 ===

=== EXAMPLE 4 — BLK UNDER: A+ category WR, but player avg overrides to LEAN ===
Input:
  Player: Nicolas Claxton [BKN]
  Bet: BLK UNDER 1.5
  True edge: 17.7% | Tier: DIAMOND
  Archetype: RIM_GUARDIAN
  Injury status: No active record
  Game context: BKN vs NYK, spread even, total 217.0

Reasoning chain (consult WR grade FIRST):
  Step 1 — WR grade: BLK UNDER = A+ (67.1% floor, n=918). Default to STRONG.
  Step 2 — Player-specific override: Claxton averages 1.8 BLK/g. Line is 1.5 — set ABOVE his
           career mean. This is not a structural UNDER. A+ category WR applies to lines at/below
           player average. When line exceeds player average, the structural edge disappears.
  Step 3 — Edge: 17.7% DIAMOND. Real edge, but player-specific risk dilutes it.
  Step 4 — Grade: LEAN. This is LEAN not NULL — WR context was engaged, specific concern found.
           LEAN means: real edge exists, empirical signal consulted, specific concern reduces confidence.
           NULL means: no data informed the decision. These are not the same.

thinking: "WR grade: A+ category. But Claxton averages 1.8 BLK/g — line at 1.5 is below his mean, structural UNDER edge absent. A+ applies structurally, not here. LEAN not STRONG."
Grade: LEAN
Reasoning: BLK UNDER A+ category signal, but Claxton's personal avg (1.8 BLK/g) puts this line below his mean — structural UNDER edge absent. DIAMOND edge is real but player-specific risk reduces confidence.
=== END EXAMPLE 4 ===

=== END EXAMPLES ===
"""
```

---

## Edit 6 — `_sonnet_curate()` — update `result.append` to include `thinking`

Find the `result.append` block in the JSON parsing section of `_sonnet_curate()`. It currently appends `bet_id` and `grade`. Add `thinking` field:

```python
                result.append({
                    'bet_id': bet_id,
                    'grade': grade,
                    'thinking': item.get('thinking', ''),
                    'reasoning': item.get('reasoning', ''),
                })
```

Note: check if `reasoning` is already captured — if yes, just add `thinking` alongside it without duplicating.

---

## Downstream: thinking field logging

After Edit 6, check if `claude_analysis_log` has a column for the thinking field. If not, the `thinking` value can be appended to the existing `reasoning` column as `"[THINKING] {thinking}\n[REASONING] {reasoning}"` until a migration adds the column. Do NOT run a schema migration as part of this ticket — that is a separate Lena ticket.

---

## Verification steps (Henrik to confirm before APPROVED)

1. `python -c "from scripts.curate_plays import _get_system_wr_context; import sqlite3; c=sqlite3.connect('ludi.db'); print(_get_system_wr_context(c)[:500])"` — should show new WEIGHTING RULE header
2. No `\` inside f-string `{}` blocks (Python 3.11 Check 10)
3. JSON output schema includes `thinking` field
4. Example 2 uses `CLE scheme = PERIMETER` (not PAINT_PACK)
5. All 4 examples present in curate_examples string

---

*Approved by Solomon — March 9, 2026. Route to junior dev for implementation.*
