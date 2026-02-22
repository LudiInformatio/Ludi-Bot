# 2024-25 Season Historical Backfill Project

**Status:** 📋 PLANNED — Ready to execute
**Last Updated:** February 22, 2026
**Roadmap Reference:** See ROADMAP.md → Database Architecture Strategy → Phase 2
**Priority:** MEDIUM — Doubles historical dataset; improves trend windows and archetype stability
**Estimated Duration:** ~6 nights (automated, no manual intervention after setup)

---

## Why This Matters

`player_game_logs` currently contains only the 2025-26 season (~18,400 rows, Oct 2025–present).
Adding the full 2024-25 season would:

| Benefit | Detail |
|---------|--------|
| **2× dataset** | ~18,000 additional game logs → ~36,000 total |
| **Longer trend windows** | L50/L75/L100 rolling windows now have data (currently capped at Oct 2025) |
| **Archetype stability** | Weekly classifier has 100+ games/player instead of 30-40 |
| **Better Monte Carlo baselines** | Reduces recency bias on outlier hot/cold streaks |
| **SportsDataIO enrichment** | `started`, DK/FD fantasy pts, home/away auto-fill on 2024-25 rows |
| **BDL advanced stats** | Per-game ratings/hustle/tracking backfill for 2024-25 (same scripts, no changes) |

---

## Data Sources — Verified

| Source | 2024-25 Coverage | Cost |
|--------|-----------------|------|
| **Tank01** (primary) | ✅ Full season box scores via `get_box_score(game_id)` | ~1,200 req (200/day budget) |
| **BDL V2 advanced** | ✅ `sync_bdl_advanced_stats.py --backfill` auto-detects new dates | 600 req/min (no concern) |
| **SportsDataIO** | ✅ Confirmed live — free tier covers 2024-25 | 100 calls/day (2-day fill after logs imported) |

**Note:** SportsDataIO free tier covering 2024-25 was verified live on Feb 22, 2026. The docstring in `sync_sportsdata_enrichment.py` saying "prior season only" was incorrect and has been noted for correction.

---

## Scope

**2024-25 Regular Season:**
- Start: `2024-10-22` (Oct 22, 2024)
- End: `2025-04-13` (Apr 13, 2025)
- Game dates: ~173 dates
- Est. player-game rows: ~18,000

**2024-25 Playoffs (optional — Phase 2):**
- Start: `2025-04-19`
- End: `2025-06-22` (approx)
- ~45 additional dates
- Useful but lower priority (smaller rosters, unusual minutes)

---

## Cross-Season Player Movement

**Not a data integrity concern.** `player_game_logs` stores `team_abbreviation` per row — every 2024-25 row will reflect the team the player was on that night. Players who were traded (e.g., Klay Thompson: GSW in 2024-25 → DAL in 2025-26) will have correct historical team context automatically.

The model already uses `player_game_logs.team_abbreviation` as historical truth per CLAUDE.md. The `players` table (current snapshot) is the only place we need to be careful, and it's not touched by this backfill.

---

## Implementation Plan

### Phase 1: Generate Audit File (5 minutes, manual)

Create `cache/pending_sync_dates.json` with the full 2024-25 regular season date range:

```bash
source .venv/bin/activate
python3 -c "
import json
from datetime import date, timedelta

start = date(2024, 10, 22)
end   = date(2025, 4, 13)
dates = []
d = start
while d <= end:
    dates.append(d.isoformat())
    d += timedelta(days=1)

# Write audit file (Module H Priority 2 mode)
with open('cache/pending_sync_dates.json', 'w') as f:
    json.dump({'dates_to_sync': dates}, f, indent=2)

print(f'Wrote {len(dates)} dates to cache/pending_sync_dates.json')
print(f'Range: {dates[0]} → {dates[-1]}')
"
```

**Note:** This includes ALL calendar days Oct 22–Apr 13. Module H skips dates with no games automatically (Tank01 returns empty for non-game dates).

### Phase 2: Module H Auto-Backfill (6 nights, fully automatic)

Module H detects `cache/pending_sync_dates.json` at startup (Priority 2 mode — takes precedence over incremental).

```
Daily 3 AM run → module_h_historian.py
  → Detects audit file
  → Processes ~28-35 dates (200 req / 6-7 games/date)
  → Saves state to cache/historian_sync_state.json if budget exhausted
  → Next run resumes from saved state (Priority 1 mode)
  → Telegram alert on completion
```

**No workflow changes needed.** `data_sync.yml` already runs `module_h_historian.py` daily.

Budget math:
| Variable | Value |
|----------|-------|
| Dates in range | ~173 game days |
| Avg games/night | ~7 |
| Tank01 calls/date | ~7 |
| Total calls needed | ~1,210 |
| Daily Module H budget | 200 req/day |
| Estimated days | **6–7 nights** |

### Phase 3: Automatic Enrichment (runs itself)

After game logs are imported, the existing daily pipeline auto-enriches:

| Script | Trigger | Action |
|--------|---------|--------|
| `sync_sportsdata_enrichment.py` | Next 3 AM run | 3-day rolling picks up new NULL `started` rows — runs ~45 days |
| `sync_bdl_advanced_stats.py` | Next 3 AM run | `--backfill` auto-detects new dates in `player_game_advanced` |
| `sync_bdl_plus_minus.py` | Next 3 AM run | Fills any remaining NULL `plus_minus` |

For faster enrichment (optional manual runs the day after Phase 2 completes):
```bash
# BDL advanced + hustle (no rate limit concern)
python3 scripts/sync_bdl_advanced_stats.py --backfill

# SportsDataIO — 100/day, need ~18 days for full 2024-25 coverage
# OR: one-shot --limit 100 for one day, then rolling default fills the rest
python3 scripts/sync_sportsdata_enrichment.py --backfill --limit 100
```

---

## Budget Summary

| API | Calls Needed | Budget | Impact |
|-----|-------------|--------|--------|
| Tank01 | ~1,210 | 200/day (Module H dedicated) | 6 nights, no pipeline conflict |
| SportsDataIO | ~173 (one per date) | 100/day | 2 nights after logs imported |
| BDL advanced | ~1,200 API calls | 600/min (no daily limit) | ~2 minutes |
| BDL plus_minus | ~0 (mostly covered by BDL adv) | — | Negligible |

---

## Verification Checklist

After Phase 2 completes:

```sql
-- Confirm 2024-25 rows imported
SELECT COUNT(*), MIN(game_date), MAX(game_date)
FROM player_game_logs
WHERE game_date < '2025-10-01';

-- Check coverage per month
SELECT strftime('%Y-%m', game_date) as month, COUNT(*) as rows
FROM player_game_logs
WHERE game_date < '2025-10-01'
GROUP BY month ORDER BY month;

-- Spot-check a known player's 2024-25 season
SELECT player_name, game_date, pts, team_abbreviation
FROM player_game_logs
WHERE player_name = 'LeBron James' AND game_date < '2025-10-01'
ORDER BY game_date LIMIT 5;
```

After Phase 3 (enrichment):
```sql
-- Confirm started fill rate on 2024-25 rows
SELECT COUNT(*), SUM(CASE WHEN started IS NOT NULL THEN 1 ELSE 0 END) as enriched
FROM player_game_logs WHERE game_date < '2025-10-01';
```

---

## Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| Tank01 returns different player IDs for 2024-25 | `player_canonical_ids` resolver handles this; UPSERT on `(game_id, player_id)` prevents duplicates |
| Some 2024-25 dates have no games (preseason gaps) | Module H skips empty dates automatically |
| `historian_sync_state.json` gets corrupted mid-run | Delete state file → re-run with audit file; UPSERT is idempotent |
| SportsDataIO 2024-25 enrichment takes 2+ days | Rolling 3-day default eventually covers all; no urgency |
| Audit file conflicts with daily incremental sync | Priority 1 (state) > Priority 2 (audit) > Priority 3 (incremental) — no conflict |

---

## Files Involved

| File | Action |
|------|--------|
| `cache/pending_sync_dates.json` | **CREATE** — audit file triggers Module H backfill mode |
| `module_h_historian.py` | No changes needed — already supports audit file mode |
| `scripts/sync_bdl_advanced_stats.py` | No changes — `--backfill` flag already handles new dates |
| `scripts/sync_sportsdata_enrichment.py` | Minor: fix incorrect docstring re: "prior season only" |
| `scripts/sync_bdl_plus_minus.py` | No changes needed |
| `data_sync.yml` | No changes needed |

---

## Execution Checklist

- [ ] Create `cache/pending_sync_dates.json` (Phase 1 command above)
- [ ] Verify audit file written correctly: `python3 -c "import json; d=json.load(open('cache/pending_sync_dates.json')); print(len(d['dates_to_sync']), d['dates_to_sync'][0], d['dates_to_sync'][-1])"`
- [ ] Monitor `data_sync.yml` run at 3 AM — confirm Module H picks up audit file
- [ ] Check Telegram for Module H completion alert (~6 nights)
- [ ] Run verification queries above
- [ ] Optional: manual BDL advanced backfill for faster enrichment
- [ ] Fix `sync_sportsdata_enrichment.py` docstring (minor cleanup)
- [ ] Update this doc status to ✅ COMPLETE
