---
description: Run Henrik's 11-point Ludi-specific code audit checklist (P0/P1/P2)
---

Activate the ludi-audit skill. Run the 11-point Ludi-specific gotcha checklist on the specified file(s). Check P0 pipeline breakers first (BDL abbrevs, canonical_games joins, DB connections in sim loops, bet_recommendations schema sync, Tank01 composite IDs), then P1 data quality, then P2 technical debt. Return verdict: APPROVED | APPROVED_WITH_NOTES | REVIEW_REQUIRED.

$ARGUMENTS
