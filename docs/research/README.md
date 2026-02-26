# Ludi-Bot Research Hub

**Purpose:** All competitive intelligence and research methodology lives here. Read before any product/feature planning session.

---

## Folder Structure

```
docs/research/
├── README.md                              ← you are here (index)
├── competitive/                           ← platform-by-platform audits
│   ├── BETIQ_TEAMRANKINGS_RESEARCH.md    ← Feb 20, 2026
│   └── COMPETITIVE_RESEARCH_2026.md      ← Feb 26, 2026 (in progress)
└── best-practices/
    └── RESEARCH_PLAYBOOK.md              ← how to run a research sprint
```

---

## Competitive Research Docs

| File | Date | Platforms Covered | Key Ludi Actions Unlocked |
|------|------|-------------------|--------------------------|
| [BETIQ_TEAMRANKINGS_RESEARCH.md](competitive/BETIQ_TEAMRANKINGS_RESEARCH.md) | Feb 20, 2026 | BetIQ, TeamRankings | Edge type labeling, DVP callout, SGP risk flagging → shipped Phase 8.24/8.25/8.26 |
| [COMPETITIVE_RESEARCH_2026.md](competitive/COMPETITIVE_RESEARCH_2026.md) | Feb 26, 2026 | OddsJam (Platinum), Outlier.bet (Premium+), BucketsToBucks, StraightBettin, PropsMadness, Action Network | Alt line sweep (Module F), public bet% of money + DIFF, Check My Prop scorecard (Ask Ludi), WOWY beneficiary reply (Ask Ludi), injury timestamp display, C&S Funnels in brief, team league ranks. |

---

## Related Docs

| Doc | Purpose |
|-----|---------|
| [`docs/FUTURE_DATA_SOURCES.md`](../FUTURE_DATA_SOURCES.md) | Ask Ludi architecture (§6), competitive patterns (§5.2-B), PBP Stats endpoints (§4.4). Read alongside competitive research to cross-reference planned data sources with competitor signals. |

---

## How To Add Research

1. Run a sprint using `best-practices/RESEARCH_PLAYBOOK.md` as your template
2. Save output to `competitive/[PLATFORM]_RESEARCH_YYYY.md`
3. Update the Competitive Research Docs table above
4. Add top Ludi Actions to `ROADMAP.md` if actionable
