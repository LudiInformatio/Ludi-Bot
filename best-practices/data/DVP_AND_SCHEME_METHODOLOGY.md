# DVP Rankings & Defensive Scheme Methodology

**Created:** February 25, 2026
**Source:** Multi-source research (NBA.com, Synergy, BBall Index, Cleaning the Glass, PBP Stats, APBRmetrics)
**Purpose:** Canonical reference for building DVP rankings + scheme classification correctly.
            Feeds: Phase 8.25 (Key Advantage Callout), weekly `classify_archetypes.py` type classifier,
            and future BERT/Claude fine-tuning data quality work.

---

## Part 1: DVP Rankings — Official Methodology

### What DVP Actually Measures

There is no single official NBA formula. Three tiers exist:

| Tier | Used By | Method | Signal Quality |
|------|---------|--------|---------------|
| Raw per-game | RotoWire, FantasyPros | Fantasy pts allowed per game to position vs league avg | Low — pace-inflated, no SOS |
| Adjusted per-100 | Cleaning the Glass, NBAstuffer | Per-possession with garbage time removed | Medium — correct basis |
| Playtype PPP | Synergy / PBP Stats | Points per possession allowed by playtype | High — best for archetype matching |

**For Ludi-Bot:** Use **per-100-possession** at team level + **PPP per playtype** for archetype-specific signals.
Self-computing from `player_game_logs + players.archetype` is viable and preferred over external APIs.

---

### Formulas

**Standard DVP score (DFS-style, weakest):**
```
DVP_score = team's fantasy pts allowed/game to position X
            - league average fantasy pts allowed/game to position X
```
Positive = bad defense. Negative = good defense.

**Per-possession normalization (correct basis):**
```
Pace = (Team Possessions / Team Minutes) * 48
DVP_per100 = (raw_stat_allowed / team_possessions) * 100
```

**MoreyBall% (offensive style classifier):**
```
MoreyBall% = (Rim FGA + FTA * 0.44 + 3PA) / Total FGA
```
- > 65% = analytically aligned (Warriors, BOS style)
- < 50% = mid-range heavy (ATL, PHI style)

---

### Minimum Sample Thresholds

| Window | Use For | Caution |
|--------|---------|---------|
| < 15 games | Do NOT surface as signal | Too noisy |
| 15–29 games | Trend detection only | Flag as early-season |
| 30+ games (season-to-date) | Primary DVP signal | Reliable |
| 500+ possessions | Individual defender metrics | RAPM-level quality |
| 75+ possessions per playtype | Synergy playtype signal | Industry standard (also our module_e.py threshold at line 636) ✅ |

**BERT training data rule:** Only include DVP-backed assertions in training examples when the underlying
sample is ≥30 team-games. Flag early-season rows with `data_confidence='LOW'` in `claude_analysis_log`.

---

### Known Biases — Critical for Training Data Quality

These biases contaminate DVP data and must be accounted for in training examples:

| Bias | Mechanism | Fix |
|------|-----------|-----|
| **Pace inflation** | High-pace teams allow more raw stats per game | Normalize to per-100 possessions |
| **Garbage time** | Bench-vs-bench inflates both offense and defense | Exclude Q4 possessions where spread ≥25pt (approximate with `games.spread > 15` in our DB) |
| **Opponent quality (SOS)** | Easy schedule of weak opponents makes DVP look better | ~1.3 pts/game effect — weight games by opponent offensive rating |
| **Position fluidity** | Switching defenses mean a "PF" may guard a PG; box score DVP by position mislabels | Use archetype-based DVP (our system) — validated by BBall Index who abandoned positional DVP entirely |
| **Assignment bias** | Elite defenders guard opponent's best scorer → their DVP stats look worse than inferior defenders | Do NOT train on raw defender PPP as quality signal without context |
| **Help defense blind spot** | Synergy charges primary defender when rotation fails | Treat Synergy allowed PPP as "system PPP allowed" not "individual defender fault" |
| **Transition/Cut/Putback gap** | Synergy defensive playtype data excludes transition, cuts, putbacks (~25-30% of possessions) | Any "allowed PPP by playtype" training example covers only ~70-75% of real possessions |

---

### Archetype-Based DVP vs Position-Based — Why Ours Is Better

BBall Index abandoned positional DVP entirely in favor of archetype-based because:
- Modern switching defenses mean position labels are wrong 30%+ of the time
- A ROLL_MAN (your archetype) gets defended at rim regardless of position listing
- RotoGrinders built "Defense vs Archetype" as a branded product for this reason

**Our 15-archetype system is already aligned with industry best practice.**
The key is computing it correctly from our own data:

```sql
-- Core DVP-by-archetype query pattern
SELECT
    g.away_team AS opponent_team,
    p.archetype,
    COUNT(DISTINCT pgl.game_id) AS games,
    AVG(pgl.pts) AS avg_pts_allowed,
    AVG(pgl.reb) AS avg_reb_allowed,
    AVG(pgl.ast) AS avg_ast_allowed,
    AVG(pgl.fg3m) AS avg_3pm_allowed,
    -- Delta vs season baseline for this archetype
    AVG(pgl.pts) - (SELECT AVG(pts) FROM player_game_logs pgl2
                    JOIN players p2 ON pgl2.player_name = p2.name
                    WHERE p2.archetype = p.archetype) AS pts_vs_baseline
FROM player_game_logs pgl
JOIN players p ON pgl.player_name = p.name
JOIN games g ON pgl.game_date = g.date AND pgl.team_abbreviation != g.home_team -- they are the visitor
-- ... (or use opponent_team field directly if available)
WHERE pgl.game_date >= '2025-10-01'
  AND p.archetype IS NOT NULL
  AND pgl.minutes >= 15  -- exclude garbage-time DNPs
GROUP BY opponent_team, p.archetype
HAVING games >= 10  -- minimum sample
```

---

## Part 2: Defensive Scheme vs Offensive Style

### Team Defensive Style Classification

No official formula exists. The analytics community uses **allowed shot-zone distribution** as the fingerprint:

| Scheme | Ludi-Bot Label | Statistical Fingerprint |
|--------|---------------|------------------------|
| Drop coverage | PAINT_PACK | `rim_freq_allowed < 30%`, `mid_freq_allowed > 20%`, low corner-3 |
| Hedge/Show | (maps to PAINT_PACK) | Medium rim rate, moderate mid-range |
| Switch-heavy | PERIMETER | `iso_ppp_allowed > 0.90`, high mid-range pull-up rate |
| Blitz/Trap | BLITZ | `corner3_freq_allowed > 12%`, `rim_freq_allowed > 35%`, more TOV forced |
| Funnel | FUNNEL | Forces into paint but has rim protection; mid-range rate skews mid |

**Data-driven classification (upgrade path):**
```python
# From NBA.com opponent shooting dashboard data (or our player_game_tracking aggregate):
if rim_freq_allowed < 0.30 and mid_freq_allowed > 0.20:
    scheme = 'PAINT_PACK'
elif corner3_freq_allowed > 0.12 and rim_freq_allowed > 0.35:
    scheme = 'BLITZ'
elif iso_ppp_allowed > 0.90 and mid_freq_allowed > 0.22:
    scheme = 'FUNNEL'
elif switch_proxy_signal:  # high mismatch hunting by opponents
    scheme = 'PERIMETER'
else:
    scheme = 'NEUTRAL'
```

### Second Spectrum P&R Coverage Types (Industry Labels)

These are the "official" per-possession labels used by NBA teams internally:

| Label | Behavior | Stat Fingerprint |
|-------|----------|-----------------|
| `DROP` | Big drops below screen height | High mid-range %, low rim rate → PAINT_PACK |
| `HEDGE/SHOW` | Big jumps above screen, recovers | Medium rim rate |
| `SWITCH` | Defenders swap assignments | High ISO, more pull-up 2s (mismatch hunting) |
| `BLITZ/TRAP` | Both defenders attack ball handler | High corner-3 (skip passes), high rim (roll man) |
| `ICE/SIDELINE` | Push handler to sideline, big stays | Low middle penetration, more sideline pull-up 2s |

Our PAINT_PACK/BLITZ/PERIMETER/FUNNEL labels correctly map to this vocabulary.

---

### Offensive Team Style Classification

**7-Type K-means Clustering (58 NBA.com categories, validated research):**

| Type | Key Characteristics | NBA Examples |
|------|--------------------|----|
| Analytics Darlings | High drive rate, low mid-range, high 3PA | BOS, MIL, MIN |
| Midrange Maestros | High ISO, 8-24ft heavy | ATL, PHI, PHX |
| Paint Grinders | Post + elbow, high rim volume | DEN, LAL |
| Motion/Screen | High C&S-3, low ISO, screen-pass | GSW pattern |
| Transition-Heavy | Fast pace, high transition % | |
| ISO-Heavy | ISO > 15%, low screens-to-shot | |
| P&R-Dominant | Ball handler + roll man > 35% | |

---

### Validated Matchup Effects (Empirically Documented)

Use these when building BERT training examples — these effects have research backing:

**High confidence (empirically validated):**

| Matchup | Effect | Training Example Use |
|---------|--------|---------------------|
| STRETCH_BIG vs PAINT_PACK (drop) | +12-15% 3PM | Positive edge label |
| ROLL_MAN vs PAINT_PACK (drop) | +10-15% points at rim | Positive edge label |
| SNIPER_ELITE vs PAINT_PACK | +12% 3PM (skip passes) | Positive edge label |
| ISO scorer vs BLITZ | -8-12% PPP, +12% TOV risk | Negative/fade edge label |
| HELIOCENTRIC vs BLITZ | +15-20% AST (passes out of double) | AST prop edge label |
| SWITCH-heavy vs size mismatch | +8-15% efficiency for mismatched player | Mismatch edge label |

**Moderate confidence (theoretically sound):**
- FUNNEL vs TRANSITION scorer → +8% pts (fast-break created via TOV)
- P&R Handler vs ICE/SIDELINE → -5% pts (containment reduces penetration)

**Low confidence / contradicted (do NOT train on these without hedging):**
- BLITZ forcing turnovers: real effect but smaller than expected ("NBA players too skilled to turn it over in trap")
- General Drtg as matchup signal: too aggregated, use archetype-specific signals instead

---

## Part 3: BERT / Claude Training Data Quality Rules

### Rules for `claude_analysis_log` Training Data

These rules ensure that Phase 8.23 Layer 1 collection produces clean training data:

1. **Minimum sample gate:** Only use DVP assertions in training examples when `team_game_count >= 30`.
   Tag early-season examples: `data_confidence = 'LOW'` in `call_type` metadata.

2. **Garbage time filter:** Exclude game log rows where `player_minutes < 15` from DVP aggregations.
   Approximate blowout exclusion: flag games where point differential > 20 in final score.

3. **Archetype quality gate:** Only use archetype-based DVP for players where `archetype != 'GENERALIST'`
   AND player has `>= 10 games` in current season. GENERALIST = insufficient data, not a real archetype.

4. **Per-possession normalization:** Any matchup stat comparison in training examples should note
   the underlying basis (per-game vs per-100). Per-100 comparisons are preferred.
   Never train on raw fantasy-point DVP as ground truth.

5. **Assignment bias awareness:** When using `player_defensive_synergy` data (PPP allowed per defender),
   remember elite defenders face tougher assignments. A 0.90 PPP allowed for a star defender may be
   better than 0.80 for a weak defender who guards nobody.

6. **Two-column classification validation:** Training examples should reinforce that:
   - `archetype` = offensive role (determines usage vacuum and prop direction)
   - `defensive_tag` = defensive role (determines steal/block prop signals)
   - These are independent — a HELIOCENTRIC with PERIMETER_HAWK defensive_tag is valid and common

7. **Playtype coverage gap:** Any training example using Synergy-style PPP data should implicitly
   cover only ~70-75% of possessions (transition/cut/putback are missing from defensive playtype data).
   Do not train the model to treat PPP-by-playtype as total defensive quality.

### Weekly Classifier Training Data Checklist

For `classify_archetypes.py` weekly re-run, check before accepting new archetype assignments:

- [ ] Player has `>= 3 games` in 21-day active window (already implemented)
- [ ] `archetype != 'GENERALIST'` OR player truly has no dominant signal
- [ ] Position gate applied: BIG archetypes blocked for `G/PG/SG/SF` positions
- [ ] SNIPER_ELITE gate: reject if `iso_freq >= 15%` (dual-threat scorers are TWO_LEVEL_SCORER)
- [ ] `defensive_tag` assigned deterministically — never via Claude
- [ ] BERT Pattern 9 negative few-shot: `archetype_in_top3 = 0` examples injected in system prompt
- [ ] Minimum 75 possessions per Synergy playtype before using PPP in classification

### Scheme Classification Data-Driven Upgrade (Future)

Current scheme classification (`team_scheme_cache`) uses static scouting. To make it data-driven:

1. Pull `rim_freq_allowed`, `mid_freq_allowed`, `corner3_freq_allowed` from `player_game_tracking`
   (aggregate WHERE player's team != defending team for last 30 games)
2. Apply fingerprint rules above to classify scheme
3. Cross-validate against `player_defensive_synergy.ppp_allowed` by playtype
4. Update `team_scheme_cache.def_style` and add `last_computed` column
5. Run weekly alongside `classify_archetypes.py`

This makes scheme labels fully automated and evidence-based — same principle as archetype classification.

---

## Related Files

- `best-practices/ai/PROMPT_ENGINEERING_PATTERNS.md` — BERT→Claude analogy map (Patterns 1-9)
- `best-practices/data/CANONICAL_NAME_RESOLUTION.md` — accent handling across APIs
- `utils/claude_logger.py` — Phase 8.23 training data collection
- `classify_archetypes.py` — weekly type classifier (consumes rules above)
- `scripts/sync_team_dvp_by_archetype.py` — LIVE ✅ (self-computed DVP from player_game_logs + players.archetype, per-100-possession normalized, 250 rows in `team_dvp_by_archetype`, runs weekly via `weekly_validation.yml`)
- `team_scheme_cache` table — current static scheme labels (upgrade target)
