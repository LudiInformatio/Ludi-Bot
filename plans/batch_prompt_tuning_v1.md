# Batch Archetype Prompt Tuning — v1 Draft

**Date:** March 10, 2026
**Authors:** Maren (prompt design) + Lena (data review)
**Status:** FIRST DRAFT — pending Henrik implementation review
**Goal:** Close GENERALIST inflation gap — batch mode 40% vs per-player 20%. Target: below 35%.

---

## Root Cause Analysis (Maren)

Current `build_team_batch_prompt()` has three structural problems:

1. **Star anchoring**: The prompt sends all players on one team in a flat list. Claude anchors
   reasoning on the star player's stat block (largest numbers) and uses that as the reference
   frame. Role players look sparse by comparison → GENERALIST is the safe hedge.

2. **No per-player reasoning step before committing**: The output format is `"Player Name": "ARCHETYPE"` —
   one label per player, no reasoning trace. Claude is forced to classify 12-15 players in one
   pass without CoT (Pattern 10). For roster fringe players with thin stat blocks, the fastest
   path is GENERALIST.

3. **Missing label anchoring per player**: The valid label list is shown once at the top of the
   batch, but not re-anchored per player block. For the 8th player in the list, the label space
   reminder is ~500 tokens away. Pattern 1 (label space first) is violated at the per-player level.

---

## Gate 2 Rejection Profile (Lena)

The 6 dry-run Gate 2 rejections share a clear pattern:

| Player | Team | Current DB | L21 PTS | AST | REB | MIN | Games | Profile |
|--------|------|-----------|---------|-----|-----|-----|-------|---------|
| Ace Bailey | UTA | GENERALIST | 17.4 | 1.3 | 4.9 | 30.7 | 7 | Rookie, decent scoring, thin synergy |
| Amari Williams | BOS | CUTTER_SPECIALIST | 0.0 | 0.3 | 0.3 | 2.0 | 3 | Deep bench, extreme low-minute outlier |
| Amen Thompson | HOU | SLASHING_CREATOR | 17.7 | 4.6 | 8.4 | 36.0 | 9 | Two-way wing — DB is already correct |
| Ariel Hukporti | NYK | GENERALIST | 1.0 | 0.3 | 2.4 | 6.8 | 8 | Backup big, sparse stats |
| Ausar Thompson | DET | GENERALIST | 8.9 | 3.9 | 4.6 | 22.1 | 9 | Athletic wing, low usage context |
| Bilal Coulibaly | WAS | GENERALIST | 12.5 | 2.5 | 3.9 | 24.0 | 10 | Wing, moderate stats, no clear role |

**Pattern identified:** 4 of 6 rejections are legitimately sparse players (low minutes OR extreme
outlier stats). These are the highest-risk players to send in a team batch — they anchor on the
star and receive GENERALIST by default.

**Lena recommendation:** Pre-filter players with `MIN < 10` OR `games < 4` to per-player fallback
BEFORE building the batch prompt. These players are the primary source of GENERALIST inflation.
The per-player path already handles them correctly (Gate 1 + system prompt negative examples fire).

**Stat threshold for pre-filter:**
```python
# Skip to per-player fallback if player is too sparse for reliable batch classification
if l10_data is None or l10_data.get('minutes', 0) < 10 or game_count < 4:
    # route to _fallback_single_player() — do not include in batch
```

This alone would remove Amari Williams (2.0 MIN) and Ariel Hukporti (6.8 MIN) from the batch.
Ace Bailey (7 games, 30.7 MIN) and the Thompson brothers are borderline — Lena signs off on
using `MIN < 12` as the cutoff based on the current data distribution.

---

## Revised `build_team_batch_prompt()` — v1 Draft (Maren)

Key design decisions applied:
- **Pattern 10 (CoT)**: Added `"thinking"` field to JSON schema — forces per-player reasoning
  before label commitment. Claude must articulate the archetype signal before assigning.
- **Pattern 1 (label space)**: Valid archetypes re-stated INSIDE each player block header,
  not just once at the top.
- **Anti-anchoring**: Explicit instruction to evaluate each player on their OWN stat profile,
  not relative to teammates. Star player block de-prioritized (appears last, not first).
- **Pattern 4 (token budget)**: Essential fields only — USG%, FTA/FGA, 3PA/FGA, top-2 synergy.
  Full l10 block retained (it's the primary signal), shot data dropped from batch (too sparse
  for most role players, adds noise).

```python
def build_team_batch_prompt(players_data: list) -> str:
    """Build a single user prompt classifying all players on one team.

    v1 tuned prompt — March 10, 2026.
    Changes vs prior version:
      - CoT thinking field added (Pattern 10) — forces per-player reasoning trace
      - Label space re-stated per player block (Pattern 1 at player level)
      - Anti-anchoring instruction: evaluate each player independently, not vs star
      - Star player sorted last (reduces anchoring on high-number stat block)
      - Shot data dropped from batch (sparse for role players, adds noise)
      - USG% promoted to primary classification signal
      - Sparse players (MIN < 12, games < 4) pre-filtered before this call

    Token budget per batch (15 players):
        - Per-player data block: ~140 tokens (slightly higher for CoT schema)
        - 15 players: ~2,100 tokens input
        - Output with thinking: ~120 tokens per player → ~1,800 tokens
        - Total: ~3,900 tokens — within Haiku budget
    """
    valid_labels = (
        "HELIOCENTRIC_MAESTRO, SLASHING_CREATOR, JUMBO_FACILITATOR, SNIPER_ELITE, "
        "TWO_LEVEL_SCORER, ISO_ASSASSIN, WARRIOR_BIG, STRETCH_BIG, ROLL_MAN, "
        "HUB_BIG, ENERGY_BIG, CUTTER_SPECIALIST, CONNECTOR, FACILITATOR, GENERALIST"
    )

    lines = [
        f"Classify each NBA player's OFFENSIVE archetype. Return JSON only — no prose.\n"
        f"\n"
        f"OUTPUT FORMAT (one object per player, include 'thinking' before 'archetype'):\n"
        f'{{"PlayerName": {{"thinking": "<one sentence: the key stat that determines archetype>", '
        f'"archetype": "<ARCHETYPE>"}}, ...}}\n'
        f"\n"
        f"VALID ARCHETYPES: {valid_labels}\n"
        f"\n"
        f"CRITICAL RULES:\n"
        f"  - Evaluate each player on THEIR OWN stat profile. Do NOT compare to teammates.\n"
        f"  - A player with USG% > 24% and high AST is not GENERALIST.\n"
        f"  - A player with FTA/FGA > 0.40 and drive synergy is not GENERALIST.\n"
        f"  - GENERALIST = no clear dominant role. Only assign when no other label fits.\n"
        f"  - Use DB:{'{'}current_archetype{'}'} as a prior — only change if stats clearly contradict it.\n"
        f"\n"
        "PLAYERS:"
    ]

    # Sort: lower-usage players first, star last — reduces anchoring on high-number blocks
    sorted_players = sorted(
        players_data,
        key=lambda pd: pd.get('season_data', {}).get('usg_pct') or 0.0
    )

    for pd in sorted_players:
        name       = pd['name']
        position   = pd.get('position') or 'UNK'
        team       = pd.get('team') or 'UNK'
        current_a  = pd.get('current_archetype') or 'NULL'
        synergy    = pd.get('synergy_data') or []
        l10        = pd.get('l10_data') or {}
        season     = pd.get('season_data') or {}

        # Primary signal: USG% (most reliable archetype discriminator)
        usg_str = ""
        if season.get('usg_pct') is not None:
            usg_str = f"USG {season['usg_pct']:.1%}"

        ast_str = ""
        if season.get('ast_pct') is not None:
            ast_str = f"AST% {season['ast_pct']:.1%}"

        # Top-2 synergy only in batch mode (Pattern 4 token discipline)
        syn_line = ""
        if synergy:
            parts = [f"{r[0]}: {r[1]:.0f}%" for r in synergy[:2]]
            syn_line = "Syn: " + " | ".join(parts)

        # Core l10 block — retained in full (primary classification signal)
        l10_line = ""
        if l10:
            fga = max(l10.get('fga', 1) or 1, 1)
            l10_line = (
                f"L21: PTS {l10.get('pts', 0):.1f} AST {l10.get('ast', 0):.1f} "
                f"REB {l10.get('reb', 0):.1f} FGA {fga:.1f} MIN {l10.get('minutes', 0):.0f} "
                f"FTA/FGA {l10.get('fta', 0)/fga:.2f} 3PA/FGA {l10.get('fg3a', 0)/fga:.2f}"
            )

        # Player block: label space reminder embedded in header
        player_block = (
            f"\n{name} | {position} | {team} | DB:{current_a}"
            f"{' | ' + usg_str if usg_str else ''}"
            f"{' ' + ast_str if ast_str else ''}"
        )
        if l10_line:   player_block += f"\n  {l10_line}"
        if syn_line:   player_block += f"\n  {syn_line}"

        lines.append(player_block)

    return "\n".join(lines)
```

---

## Pre-Filter Recommendation (Lena, signed off)

Add this block in the batch grouping loop BEFORE calling `build_team_batch_prompt()`:

```python
# Pre-filter sparse players to per-player fallback before batch
SPARSE_MIN_THRESHOLD = 12.0   # players under 12 MIN/game → per-player
SPARSE_GAME_THRESHOLD = 4     # players under 4 games → per-player

batch_eligible = []
sparse_players = []

for player_data in team_players:
    l10 = player_data.get('l10_data') or {}
    game_count = player_data.get('game_count', 0)  # needs to be added to prefetch
    if (l10.get('minutes', 0) < SPARSE_MIN_THRESHOLD
            or game_count < SPARSE_GAME_THRESHOLD):
        sparse_players.append(player_data)
    else:
        batch_eligible.append(player_data)

# Run batch on eligible players
if batch_eligible:
    batch_prompt = build_team_batch_prompt(batch_eligible)
    # ... existing batch call ...

# Run per-player on sparse players
for player_data in sparse_players:
    result = _fallback_single_player(player_data, system_prompt, args)
    # ... existing per-player handling ...
```

**Lena note:** `game_count` is not currently included in the pre-fetch dict. Needs to be added
to the player data prefetch loop alongside the existing `l10_data`, `synergy_data`, etc.
Quick fix: add `COUNT(DISTINCT pgl.game_id) as game_count` to `get_player_l10()` or a
separate count query in the prefetch block.

---

## Expected Impact

| Change | Expected GENERALIST reduction |
|--------|------------------------------|
| Pre-filter MIN < 12 / games < 4 | -5 to -8 percentage points |
| CoT thinking field (Pattern 10) | -3 to -6 percentage points |
| Anti-anchoring instruction | -2 to -4 percentage points |
| Star sorted last | -1 to -2 percentage points |
| **Total projected** | **-11 to -20 points** |

Current batch rate: 40%. Projected post-tuning: 20-29%. Target: below 35%. **Expected to clear.**

---

## What Maren Did NOT Change

- System prompt (`ARCHETYPE_SYSTEM_PROMPT`) — unchanged. Negative examples in system prompt
  are the strongest existing signal; don't touch.
- Gate 1 / Gate 2 validation logic — unchanged. These catch hallucinations regardless of prompt.
- `temperature=0.0` — unchanged. Classification tasks must be deterministic.
- Output schema key structure — JSON keyed by player name is correct. Only added `thinking` field
  as a nested object (breaking change: parse logic in `_validate_and_write_archetype()` needs update).

---

## Implementation Notes for Henrik

1. **Parse logic change**: Current code does `batch_result.get(name)` and expects a string.
   New schema returns `{"thinking": "...", "archetype": "..."}`. Parse as:
   ```python
   player_result = batch_result.get(name, {})
   proposed_archetype = player_result.get('archetype') if isinstance(player_result, dict) else player_result
   thinking_trace = player_result.get('thinking', '') if isinstance(player_result, dict) else ''
   ```
   Backward compatible: if batch returns old string format (no `thinking`), `isinstance` check
   handles it gracefully — no crash, just empty thinking trace.

2. **`game_count` in prefetch**: Add to player data dict before the batch grouping loop.

3. **Pre-filter thresholds are configurable**: Put `SPARSE_MIN_THRESHOLD = 12.0` and
   `SPARSE_GAME_THRESHOLD = 4` at module top with `# tunable` comment.

4. **Dry-run required before production ship**: Run with `--dry-run --per-player` vs
   `--dry-run` (batch tuned) on same date. Compare GENERALIST rates. Must be below 35% before
   removing `--per-player` flag from `weekly_validation.yml`.

---

## Joint Sign-Off

- **Maren** — prompt structure, CoT reasoning, anti-anchoring, Pattern 1/4/10 application: APPROVED
- **Lena** — stat fields correct (USG%, FTA/FGA, 3PA/FGA are the key discriminators), pre-filter
  thresholds validated against current DB distribution (MIN < 12 covers bottom quartile of
  active players), game_count gap flagged: APPROVED WITH NOTE (game_count prefetch fix required)

**Next step:** Route to Henrik for implementation review and junior dev assignment.
