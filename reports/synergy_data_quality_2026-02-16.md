# Synergy Data Quality Audit

Generated: 2026-02-16 17:29:33
Season: 2025-26

## Summary

- Total rows: 2740
- Significant rows (poss_per_game * games_played >= 75): 561
- Team NULL rows: 110
- Percentile NULL rows: 628

## Playtype Scale Check

| Playtype | Rows | Min | Median | Max | <=1.0 | >1.0 | Mixed Scale Flag |
|---|---:|---:|---:|---:|---:|---:|---|
| CUT | 293 | 1.2000 | 8.0000 | 40.7000 | 0 | 293 | NO |
| HANDOFF | 179 | 1.6000 | 5.8000 | 18.0000 | 0 | 179 | NO |
| ISO | 230 | 1.4000 | 7.1500 | 42.4000 | 0 | 230 | NO |
| MISC | 286 | 2.2000 | 5.7000 | 24.1000 | 0 | 286 | NO |
| OFF_SCREEN | 137 | 1.4000 | 5.2000 | 26.0000 | 0 | 137 | NO |
| POST_UP | 116 | 1.3000 | 6.3000 | 32.8000 | 0 | 116 | NO |
| PR_BALL_HANDLER | 272 | 1.7000 | 14.1000 | 54.8000 | 0 | 272 | NO |
| PR_ROLL_MAN | 213 | 1.2000 | 7.2000 | 36.6000 | 0 | 213 | NO |
| PUTBACK | 248 | 1.1000 | 6.3000 | 53.8000 | 0 | 248 | NO |
| SPOT_UP | 380 | 3.1000 | 29.1500 | 68.6000 | 0 | 380 | NO |
| TRANSITION | 386 | 4.8000 | 18.5000 | 35.8000 | 0 | 386 | NO |

## Notes

- Mixed-scale playtypes should be normalized to canonical 0-100 freq_pct.
- Low/NULL percentile rows should be excluded from percentile-driven rules.
- Team NULL rows reduce team-level style aggregation quality.
