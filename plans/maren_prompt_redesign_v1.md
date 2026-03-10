# Maren Prompt Redesign — Curation Pipeline v1
**Date:** March 9, 2026
**Author:** Maren (Content Strategist & Prompt Engineer)
**Status:** DESIGN ONLY — awaiting Solomon approval before any implementation
**Routed by:** Solomon (T-Maren-001)

---

## Key Decisions (Summary)

- **WR grade is PRIMARY, not a tiebreaker.** Current framing ("Use these to break selection ties") inverts the signal hierarchy. The Wilson floor data is the most reliable predictor we have. Edge% is secondary.
- **ANALYSIS_PROTOCOL conflicts with the WR injection.** Rule 7 says "Do NOT generate edge percentages or win rates." The WR context block injects exactly that. One bridge sentence resolves the contradiction.
- **All three curation examples use generic placeholders.** They teach the model wrong reasoning chain (edge → matchup → grade). Replacing with real Tatum/Flagg/Thompson data fixes the chain ordering.
- **n=50 gate is binary and incorrect.** PR UNDER has an 85.7% STRONG WR at n=7 — the signal exists at small n, the model just needs calibrated uncertainty labels, not hard suppression.
- **CoT (Pattern 10) is the most direct fix for LEAN/NULL convergence.** Forcing a `thinking` field before the grade breaks the anchoring-on-edge% pattern that collapses LEAN to NULL-level behavior.

---

## Section A — New WR Weighting Instruction

**Current text (lines 357-358 in `curate_plays.py`):**
```
"LUDI INFORMATIO EMPIRICAL WIN RATES (this season, Wilson 95% confidence floor):",
"Use these to break selection ties. High raw edge ≠ reliable bet for high-variance stats.",
```

**Problem:** "Break selection ties" positions WR as a tiebreaker. The model reads edge% first (it's in the bet block), anchors on it, then checks WR only when two bets are otherwise equal. This is the root cause of LEAN/NULL convergence — LEAN bets are graded by edge, not by WR grade.

**Replacement text:**

```
LUDI-BOT EMPIRICAL WIN RATES (this season, Wilson 95% confidence floor):

WEIGHTING RULE — read WR grade FIRST, before edge%, before matchup:
  A+ grade (floor >= 60%, n >= 500): WR is the primary signal. STRONG unless injury or
      extreme correlation conflict overrides. Edge% is confirming evidence, not deciding factor.
  A  grade (floor >= 55%, n >= 150): Prefer STRONG. Edge% must be >= 5% to confirm.
  B  grade (floor >= 50%, n >= 50):  Default LEAN. Needs edge% >= 10% + clean matchup for STRONG.
  C  grade (floor >= 45%):           Neutral. Grade by edge% and matchup normally.
  D  grade (floor >= 40%):           Default LEAN. Needs overwhelming evidence for STRONG.
  F  grade (floor < 40%):            Default FADE. Only structural factors (clear injury context)
                                      can override to LEAN. Never STRONG.

WHY THIS MATTERS: Our data shows 4,207 settled bets. True_edge has near-zero correlation with
outcome for high-edge bets (Amen Thompson PTS OVER 109.2% edge → LOSS). Wilson floor is the
only statistically validated predictor we have. Edge% measures model conviction, not market
efficiency. Grade WR first.
```

**Grade-to-floor mapping (based on actual data):**

| Grade | Wilson Floor | Example Stat | n    | Real WR |
|-------|-------------|--------------|------|---------|
| A+    | >= 67%      | BLK UNDER    | 918  | 70.2%   |
| A     | 57-66%      | 3PM UNDER    | 810  | 60.2%   |
| B+    | 54-56%      | STL UNDER    | 559  | 58.5%   |
| B     | 52-53%      | REB UNDER    | 837  | 55.4%   |
| C     | 47-51%      | RA OVER      | 454  | 52.2%   |
| D     | 42-46%      | (LEAN zone)  |      |         |
| F     | < 42%       | (FADE zone)  |      |         |

---

## Section B — ANALYSIS_PROTOCOL Bridge Instruction

**The conflict:**
`ANALYSIS_PROTOCOL` line 7 (current):
> "Do NOT generate edge percentages or win rates. These come only from the pipeline."

The WR context block injects win rates into the system prompt. The model encounters both rules and the conservative rule wins — it discounts the WR table as potentially "generated" data it should not use.

**Fix — add one line at the top of the WR context block (before the table rows):**

```
NOTE: The win rate data below is MEASURED historical outcome data from our settled bet database
(4,207 bets). It is NOT generated or estimated. ANALYSIS_PROTOCOL rule 7 ("Do NOT generate
win rates") does not apply here — these are injected empirical facts, not model-produced claims.
Treat this table with the same authority as a stat injected from player_game_logs.
```

**Placement:** This line goes at the very top of the string returned by `_get_system_wr_context()`, before the table rows. It is a one-time clarifier, not repeated per row.

---

## Section C — Revised Curation Examples

**Current examples:** All three use TEAM1/TEAM2/TEAM3 placeholders and generic player archetypes. They teach: edge → matchup → grade. Wrong chain.

**Required chain:** WR grade → edge confirms → matchup → grade.

---

### Example 1 — BLK UNDER: A+ WR grade overrides moderate concern (→ STRONG)

```
=== CURATION EXAMPLE 1 ===
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
           frequency in Tatum's own log (he averages 0.5 BLK/g — lines set at 0.5 are
           razor thin, structural UNDER edge holds regardless of opponent rim profile).
  Step 4 — Grade: STRONG. WR primary signal + DIAMOND edge + acceptable matchup risk.

Grade: STRONG
Reasoning: BLK UNDER A+ empirical signal (67.1% floor, 918 bets) + DIAMOND edge confirms.
           Opponent rim frequency is a yellow flag but does not override A+ WR grade.
=== END EXAMPLE 1 ===
```

---

### Example 2 — PTS OVER: extreme edge% does NOT override D-grade WR (→ FADE)

```
=== CURATION EXAMPLE 2 ===
Input:
  Player: Amen Thompson [HOU]
  Bet: PTS OVER 16.5
  True edge: 109.2% | Tier: DIAMOND
  Archetype: SLASHING_CREATOR
  Injury status: No active record
  Game context: HOU vs CLE, spread HOU -2.5, total 228.0
  curation_grade: NULL (pre-curation)

Reasoning chain (consult WR grade FIRST):
  Step 1 — WR grade: PTS OVER does NOT appear in the top-10 Wilson floor table (n >= 50).
           This means either n < 50 for this direction, or WR is below neutral (C/D range).
           When stat/side is absent from the A+/A/B table, treat as D grade — no confirmed edge.
  Step 2 — Edge check: 109.2% is an extreme outlier. ALERT: edge outliers >= 50% indicate
           a volatile market condition or model confidence gap — they do NOT indicate a
           high-probability outcome. The model's 10k simulations can be directionally
           correct but the market line correction may not have occurred yet.
  Step 3 — Matchup: CLE scheme is PAINT_PACK (A+ defense). Thompson is SLASHING_CREATOR —
           paint-pack schemes suppress slash + drive volume. Negative matchup signal.
  Step 4 — Grade: FADE. D-grade WR + extreme edge outlier flag + negative matchup.
           Edge% alone does not make a STRONG bet. The empirical WR table shows PTS OVER
           is not a reliable market edge in this system — the model overstates edge by 18-21%
           on PTS OVER category (see KEY CALIBRATION NOTES).

Grade: FADE
Reasoning: PTS OVER has no confirmed empirical edge in this system (absent from WR table).
           Extreme edge outlier (109.2%) signals market volatility, not probability certainty.
           Matchup vs PAINT_PACK defense is negative for SLASHING_CREATOR archetype.
=== END EXAMPLE 2 ===
```

---

### Example 3 — PR UNDER: emerging signal, small n, handled with calibrated uncertainty (→ STRONG with note)

```
=== CURATION EXAMPLE 3 ===
Input:
  Player: Cooper Flagg [DAL]
  Bet: PR UNDER 25.5
  True edge: 38.8% | Tier: DIAMOND
  Archetype: TWO_LEVEL_SCORER
  Injury status: No active record
  Game context: DAL vs BKN, spread DAL -6.5, total 224.0
  curation_grade: STRONG (actual outcome: WIN, 2026-03-08)

Reasoning chain (consult WR grade FIRST):
  Step 1 — WR grade: PR UNDER = Wilson floor 45.9% (n=404) → C grade overall.
           HOWEVER: when this system grades PR UNDER as STRONG, WR = 85.7% (n=7, EMERGING).
           This is a CURATION-CONDITIONAL signal — the grade CREATES the edge, it doesn't
           just reflect it. LEAN curation degrades PR UNDER to 38.5% WR (n=26).
           Interpretation: When the bet has strong underlying factors, STRONG grade is correct.
           When it doesn't, LEAN actively destroys the signal.
  Step 2 — Edge confirms: 38.8% DIAMOND. Strong model conviction.
  Step 3 — Matchup: BKN is PERIMETER scheme. Flagg as TWO_LEVEL_SCORER attacks paint + mid.
           BKN perimeter defense = neutral to positive for Flagg volume (not actively capped).
           Blowout risk: DAL -6.5, not extreme (< 7.5 threshold for blowout tax).
  Step 4 — n-guard check: PR UNDER STRONG n=7 is EMERGING. Apply uncertainty note, not
           grade downgrade. Uncertainty note format: "(EMERGING signal — n=7 STRONG cases,
           85.7% WR directionally strong but confidence interval wide)".

Grade: STRONG
Reasoning: PR UNDER with STRONG curation shows 85.7% WR (EMERGING, n=7) — grading this
           LEAN would destroy the signal (LEAN PR UNDER = 38.5% WR). DIAMOND edge + neutral
           matchup confirm. Note: emerging signal, verify against matchup context.
=== END EXAMPLE 3 ===
```

---

## Section D — n-guard Redesign (Tiered Labels)

**Current system:** Flat n >= 50 gate. Everything below 50 is excluded from the WR table entirely. PR UNDER STRONG (n=7, 85.7% WR) is invisible to the model.

**Problem:** Binary suppression hides emerging signals. The model is flying blind on stats with genuine but small-sample evidence.

**Proposed tiered label system:**

| Tier | Threshold | Label format | Behavior |
|------|-----------|-------------|----------|
| ESTABLISHED | n >= 100 | `{stat} {side}: {wr}% WR (95% floor={floor}%, n={n}) [{grade}]{flag}` | Full trust. Grade-to-action applies. |
| EMERGING | n = 20-99 | `{stat} {side}: {wr}% WR (EMERGING — n={n}, treat as directional only) [{grade}*]` | Directional only. Grade with asterisk. Use with caution instruction in header. |
| WATCH | n < 20 | `{stat} {side}: {wr}% WR (WATCH — n={n}, too small for grade)` | Count + direction only. No grade letter. No grade-to-action mapping. |

**Actual format strings for implementation:**

```python
# ESTABLISHED (n >= 100)
lines.append(f"  {stat} {side}: {wr:.0f}% WR (95% floor={lb*100:.0f}%, n={n}) [{grade}]{flag}")

# EMERGING (n = 20-99)
lines.append(f"  {stat} {side}: {wr:.0f}% WR (EMERGING — n={n}, direction={direction}, treat as supporting signal) [{grade}*]")

# WATCH (n < 20)
lines.append(f"  {stat} {side}: {wr:.0f}% WR (WATCH — n={n}, too small for statistical grade)")
```

**Header addition to WR context block:**
```
EMERGING (*) signals: directional only — use to confirm an otherwise strong grade, not to create one.
WATCH signals: count too small for any statistical inference — note only, do not weight.
```

**n-guard thresholds rationale:**
- n=100: minimum for 95% CI to be tight enough for A/B/C grade reliability (margin of error ~9.8%)
- n=20: minimum to establish a directional signal (50% heads/tails needs ~15 flips to confirm bias)
- Below 20: noise territory — listing is informational only

**Specific fix for PR UNDER STRONG:** Under the current n=50 gate, the 85.7% WR at n=7 is invisible. Under the new system, PR UNDER STRONG n=7 appears as a WATCH signal. Combined with the new curation examples showing the correct reasoning chain, the model now has both the data and the instruction to handle it correctly.

---

## Section E — LLM Research: What Fixes LEAN/NULL Convergence

**The problem:** LEAN WR = 50.3%, NULL WR = 48.4%. The LEAN grade is adding no predictive value. LEAN is converging to the base rate — which means the model is not differentiating between "has a minor concern" and "is otherwise similar to an ungraded bet."

**Two methodologies from `LLM_TRAINING_METHODOLOGIES_LANDSCAPE.md` apply directly:**

---

### Methodology 1: Chain-of-Thought (Pattern 10, Wei et al. 2022)

**Relevant passage (from the doc, "Not Yet Used — High Potential" table):**
> "Chain-of-Thought | Wei et al. 2022 | Show reasoning traces before answer | Curation grades — force explicit reasoning"

**And from Pattern 10 section:**
> "Force the model to show its reasoning trace BEFORE committing to an output. Adding 'Let's think step by step' or requiring a `thinking` field before the answer improves classification accuracy by 12-15%."

**Mapping to LEAN/NULL convergence:**

The root cause of convergence is anchoring. The model sees edge=12% → anchors on "this is a decent bet" → LEAN is the path of least resistance when no strong signal pushes either direction. LEAN becomes the default for "nothing obviously wrong, nothing obviously strong."

CoT forces explicit WR consultation before grade assignment. The model cannot produce a grade without first generating a reasoning chain. If the reasoning chain starts with WR grade (as the new examples require), the model must engage with the empirical data before anchoring on edge%.

**Specific fix:** Add `thinking` field to the output schema:
```json
{"bet_id": 123, "thinking": "WR grade for BLK UNDER: A+ (67.1% floor). Edge confirms at 17.7%. Matchup: BKN PERIMETER scheme, neutral for big. No injury. A+ WR + confirming edge = STRONG.", "grade": "STRONG", "reasoning": "one sentence"}
```

The `thinking` field is not used downstream for grading — it is logged to `claude_analysis_log` for audit. But it forces the model to engage the WR table BEFORE writing the grade. That breaks the anchoring pattern.

---

### Methodology 2: DPO (Rafailov et al. 2023) / ELECTRA negative examples lesson

**Relevant passage:**
> "DPO — Direct optimization on preferred/dispreferred pairs, no reward model. Simpler, more stable."

And from the ELECTRA row in the Pre-Training Objectives table:
> "Replaced Token Detection | ELECTRA | Discriminator classifies every token as real/fake. 4x sample-efficient. Lesson: negative examples are more efficient."

**Mapping to LEAN/NULL convergence:**

The current curation examples show one STRONG, one LEAN, one FADE. The LEAN example (BLK UNDER WARRIOR_BIG with a generic concern) does not contrast LEAN against NULL. The model has no example of "this would be NULL without curation — here's what makes it LEAN."

DPO/ELECTRA lesson: preferred/dispreferred pairs teach boundary conditions more efficiently than a single label. For LEAN specifically, we need a "this was graded LEAN not NULL because X" and a "this was graded STRONG not LEAN because WR grade A+ overrode the concern" pair.

**Specific fix:** The new examples (Section C above) already implement this partially — Example 1 shows "yellow flag does not override A+ WR" (LEAN→STRONG distinction), Example 3 shows "emerging signal handled with uncertainty note not grade downgrade" (WATCH→STRONG distinction). Adding one explicit LEAN-not-NULL example would complete the set:

```
=== CURATION EXAMPLE 4 (LEAN vs NULL distinction) ===
Input: Nicolas Claxton [BKN], BLK UNDER 1.5, true_edge=17.7%, DIAMOND, Archetype: RIM_GUARDIAN
WR grade check: BLK UNDER = A+ (67.1% floor). BUT: line is 1.5, not 0.5. Claxton averages
1.8 BLK/g. Line is set near his mean — not a structural UNDER. Specific player data overrides
category-level WR grade.
Reasoning: Category WR is A+, but Claxton's personal average (1.8 BLK/g) makes 1.5 a
vulnerable line, not a structural UNDER. DIAMOND edge is real, but player-specific risk
exists. This is LEAN (category A+ + personal avg concern) not NULL (no grade = no data
informed the decision).
Grade: LEAN
```

This teaches the model that LEAN is not "nothing obviously wrong." LEAN is "WR context engaged, specific concern found, not strong enough for STRONG but not random."

---

## Implementation Notes for Solomon

**Files requiring changes (design only — implementation by junior dev after Henrik audit):**

1. `scripts/curate_plays.py`
   - `_get_system_wr_context()`: Replace header lines (Section A), add bridge note (Section B), add tiered n-guard logic (Section D)
   - `_sonnet_curate()`: Replace `curate_examples` block (Section C), add `thinking` field to output schema (Section E)

2. No changes required to `utils/claude_prompts.py` — the `ANALYSIS_PROTOCOL` conflict is resolved by the bridge instruction in `_get_system_wr_context()`, not by editing the protocol itself.

**Confidence levels per decision:**

| Decision | Confidence | Rationale |
|----------|-----------|-----------|
| WR as PRIMARY not tiebreaker | HIGH | Direct data evidence: LEAN WR = NULL WR, STRONG WR > NULL. Tiebreaker framing is provably wrong. |
| CoT thinking field | HIGH | Pattern 10 already designed for this exact use case. 12-15% classification improvement in literature. Near-zero implementation cost. |
| Bridge instruction for ANALYSIS_PROTOCOL conflict | HIGH | Conflict is demonstrable from the two text blocks. One sentence resolves it cleanly without touching ANALYSIS_PROTOCOL itself. |
| Tiered n-guard (100/20 thresholds) | MEDIUM | Thresholds are statistically defensible but somewhat arbitrary. The 100/20 split is a starting point — Lena should validate after one week of production. |
| New curation examples with real data | HIGH | All examples use verified DB data (queried 2026-03-09). Reasoning chains are consistent with calibration findings. |
| LEAN vs NULL distinction example (Section E, Example 4) | MEDIUM | The Claxton example is constructed from today's unsettled data. Outcome unknown. Pattern is correct but the specific example should be replaced with a settled LEAN bet once available. |

**Follow-up query needed from Lena before finalizing:**
- Settled LEAN bets where the LEAN grade was demonstrably correct (WR > 52% for LEAN subset on specific stat/side combo). Currently no such segment identified in the data. If LEAN is not adding signal on any stat, the grade itself may need redesign rather than just prompt fixes — but that is a separate, larger question.
- PR UNDER breakdown by curation grade with player-level data: which specific players drive the LEAN WR degradation to 38.5%? If it is dominated by one high-volume player (e.g., Barnes repeatedly graded LEAN), the problem may be player-level not category-level.

---

*Maren — Design complete. No production files were modified. Awaiting Solomon approval to route to junior dev for implementation.*
