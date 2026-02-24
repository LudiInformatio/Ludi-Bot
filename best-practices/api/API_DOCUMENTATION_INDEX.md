# API Documentation Index

**Central hub for all API-related documentation in Ludi-Bot**

---

## Documentation Files

### 1. API Best Practices Guide
**File:** `docs/API_BEST_PRACTICES.md` (53 KB, 1,847 lines)
**Purpose:** Comprehensive guide for sports analytics API integration
**Audience:** Developers building NBA/WNBA/NFL/MLB analytics systems

**Contents:**
- Authentication & Secrets Management
- Rate Limiting & Quota Management
- Caching Strategies (TTL, file-based, in-memory)
- Error Handling & Retry Logic
- Request & Response Patterns
- Version Management & Breaking Changes
- Testing & Validation
- Monitoring & Alerting
- Multi-API Architecture (primary/fallback patterns)
- Common Pitfalls & Anti-Patterns (with real examples)
- Ludi-Bot Specific Patterns
- Sports API Considerations (real-time vs historical, injuries, schedules)
- Integration Checklist
- Future-Proofing for Other Sports

**Key Features:**
- 50+ code examples
- "Lessons from Ludi-Bot" callout boxes with real mistakes and fixes
- Complete templates for common patterns
- Cross-references to actual Ludi-Bot files

---

### 2. LLM Integration Guide
**File:** `LLM_INTEGRATION.md` (~200 lines)
**Purpose:** Claude/Anthropic integration patterns for Phase 8 AI pipeline
**Audience:** Developers adding Claude calls to the Ludi-Bot pipeline

**Contents:**
- OAuth-first auth chain (CLAUDE_CODE_OAUTH_TOKEN → ~/.claude/config.json → ANTHROPIC_API_KEY)
- Model selection and exact model IDs (Haiku for gates, Sonnet for narratives)
- SDK patterns: lazy import, client-inside-function, `system=` vs `user=` separation
- Context engineering: the 5 ordering rules, ROSTER_RULES block
- Token tracking via `api_monitor.py` extension
- Graceful degradation (always fall back to rule-based logic)
- Anti-patterns: Claude for NBA facts, module-level init, blocking pipeline

**Key Feature:** Kept separate from `API_BEST_PRACTICES.md` — LLMs have different constraints from REST APIs.

---

### 3. API Quick Reference
**File:** `docs/API_QUICK_REFERENCE.md` (7 KB, 1-page cheatsheet)
**Purpose:** Fast lookup for common API patterns
**Audience:** Developers who need quick code snippets

**Contents:**
- The Golden Rules (6 core principles)
- Critical Anti-Patterns (7 mistakes to avoid)
- Ready-to-use templates for:
  - Authentication
  - Rate limiting
  - Caching
  - Retry logic
  - Error handling
  - Fallback chains
  - Monitoring
- Team code normalization
- Cache TTL guidelines
- HTTP status code actions
- Real Ludi-Bot failures & fixes
- Pre-integration checklist

**Use Case:** Print this page and tape it to your monitor.

---

### 3. API Usage Audit
**File:** `docs/API_USAGE_AUDIT.md` (9 KB)
**Purpose:** Inventory of all APIs in use, costs, and capacity
**Audience:** Project managers, cost analysis

**Contents:**
- The-Odds-API (endpoints, credits, monthly cost)
- Tank01 (endpoints, daily quota, usage patterns)
- PBP Stats (free tier, endpoints, caching impact)
- Ball Don't Lie (GOAT tier, v1+v2 endpoints, Labs assessment)
- Redundancy Map (which data has fallback sources)
- Cost Summary ($79.99/mo total)
- Migration path and optimization notes

**Last Updated:** February 14, 2026

---

## How to Use This Documentation

### When Adding a New API
1. Read **Section 13** of `API_BEST_PRACTICES.md` (Integration Checklist)
2. Use templates from `API_QUICK_REFERENCE.md`
3. Add entry to `API_USAGE_AUDIT.md` (costs, quotas)
4. Follow patterns in existing clients (`utils/bdl_client.py`, `utils/pbp_stats_client.py`)

### When Debugging API Issues
1. Check `API_QUICK_REFERENCE.md` for HTTP status code meanings
2. Review **Section 10** of `API_BEST_PRACTICES.md` (Common Pitfalls)
3. Check MEMORY.md for known gotchas

### When Optimizing API Usage
1. Review `API_USAGE_AUDIT.md` for current quotas
2. Read **Section 3** of `API_BEST_PRACTICES.md` (Caching Strategies)
3. Check **Section 2** for rate limiting patterns

### When Expanding to New Sports (WNBA/NFL/MLB)
1. Read **Section 14** of `API_BEST_PRACTICES.md` (Future-Proofing)
2. Use sport-agnostic patterns from the guide
3. Update `API_USAGE_AUDIT.md` with new API costs

---

## Related Documentation

### Internal Project Docs
- `CLAUDE.md` — Critical data rules (never use AI knowledge for rosters/trades)
- `ROADMAP.md` — Current API-related tasks
- `ARCHITECTURE.md` — Module pipeline and API integrations
- `METHODOLOGY.md` — Edge calculation, line shopping, CLV tracking
- `.claude/projects/.../memory/MEMORY.md` — API gotchas and lessons learned

### API Client Files
- `utils/bdl_client.py` — BallDontLie API client (607 lines)
- `utils/pbp_stats_client.py` — PBP Stats API client (796 lines)
- `utils/api_helpers.py` — Retry logic, circuit breaker (308 lines)
- `utils/api_monitor.py` — Quota tracking, alerts (292 lines)
- `module_a.py` — Gatekeeper (odds ingestion with fallback)

### External Resources
- [The-Odds-API Docs](https://the-odds-api.com/liveapi/guides/v4/)
- [BallDontLie API Docs](https://docs.balldontlie.io/)
- [PBP Stats API Docs](https://pbpstats.readthedocs.io/)
- [Tank01 API on RapidAPI](https://rapidapi.com/tank01/api/tank01-fantasy-stats)

---

## Key Lessons from Ludi-Bot

### 1. Silent Failures are the #1 Bug Source
```python
# ❌ This hid a bug for 21 days
except Exception:
    continue

# ✅ Always log before continuing
except Exception as e:
    print(f"Error: {e}")
    continue
```

### 2. Quota Monitoring Prevents Outages
- We hit quota exhaustion on The-Odds-API (Jan 30+)
- No monitoring = 5-day pipeline failure before detection
- Fix: `api_monitor.py` tracks quota, alerts at 80%

### 3. API Changes Break Silently
- Tank01 changed ID format (simple → composite)
- Broke player matching across all modules
- Fix: Canonical ID mapping table (`player_canonical_ids`)

### 4. Caching is Critical for Performance
- PBP Stats API: 120s timeouts common
- File-based caching → **19.4x speedup**
- TTL-based expiration prevents stale data

### 5. Always Have a Fallback
- Primary: The-Odds-API
- Secondary: BallDontLie
- Tertiary: Stale cache
- Result: 99.9% uptime even with API outages

### 6. Distinguish Expected Noise from Real Failures at the Exit Point
- `capture_closing_lines.py` exited `1` every night in Feb when Odds API quota = 0 — triggering false Ops Hub alerts
- Root cause: all `sys.exit(1)` paths fired without checking whether the "failure" was a known expected state
- Fix: check `cache/odds_api_quota.json` before exiting — quota=0 is a known monthly event → `exit(0)`
- **Pattern**: "Expected noise = known state = `exit(0)` with informative log. Unknown failure = `exit(1)` = alert."
- Applied to: `capture_closing_lines.py` (Feb 2026), `morning_brief.py` (Feb 2026)
- Also applies to: any script that runs daily but depends on a monthly-quota API

---

## Quick Decision Tree

**"Which document should I read?"**

```
Need to add a new API?
└─> API_BEST_PRACTICES.md (Section 13)

Adding a Claude/LLM call?
└─> LLM_INTEGRATION.md (full guide)

Need a quick code snippet?
└─> API_QUICK_REFERENCE.md

Debugging an API error?
└─> API_QUICK_REFERENCE.md (HTTP codes)
    └─> API_BEST_PRACTICES.md (Section 10)

Checking quota/costs?
└─> API_USAGE_AUDIT.md

Optimizing performance?
└─> API_BEST_PRACTICES.md (Section 3: Caching)

Expanding to new sport?
└─> API_BEST_PRACTICES.md (Section 14)
```

---

## Maintenance

**Update these docs when:**
- Adding/removing an API → Update `API_USAGE_AUDIT.md`
- Discovering a new pattern → Add to `API_BEST_PRACTICES.md`
- Finding a bug → Add to "Lessons Learned" in `API_BEST_PRACTICES.md`
- Changing quota tiers → Update `API_USAGE_AUDIT.md`

**Review quarterly:** Check if APIs have new features, pricing changes, or better alternatives.

---

## Version History

| File | Version | Last Updated |
|------|---------|--------------|
| API_BEST_PRACTICES.md | 1.0 | 2026-02-17 |
| API_QUICK_REFERENCE.md | 1.0 | 2026-02-17 |
| API_USAGE_AUDIT.md | 2.1 | 2026-02-14 |
| API_DOCUMENTATION_INDEX.md | 1.0 | 2026-02-17 |

---

**Remember:** Good API integration fails loudly, degrades gracefully, and logs everything.
