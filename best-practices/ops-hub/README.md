# Ops Hub — Knowledge Base

This folder is the institutional memory of `claude-ops-hub.yml`.

It is maintained automatically by the Claude Ops Hub workflow — each time Claude
diagnoses a failure and takes action (Tier 1 auto-fix, Tier 2 PR, or Tier 3 issue),
it appends an entry to `KNOWN_FIXES.md` and commits it.

---

## Files

| File | Purpose |
|------|---------|
| `KNOWN_FIXES.md` | Running log of every failure diagnosed + action taken. Claude reads this FIRST on every run. |
| `DOMAIN_PATTERNS.md` | Few-shot diagnosis chain examples per workflow domain (Settlement, Pipeline, Data Sync, etc.). |
| `VERSION_MONITORING.md` | Henrik's release-watch checklist — Anthropic + Gemini upstream packages that can silently break production. |

---

## How This Works

### Reading (before diagnosis)
At the start of every ops-hub run, Claude reads both files for context. Known patterns
allow instant diagnosis without re-investigation. This mirrors the few-shot examples
pattern from `best-practices/ai/PROMPT_ENGINEERING_PATTERNS.md` (Pattern 3 + Pattern 7).

### Writing (after every action)
After diagnosing + acting, Claude appends a structured entry to `KNOWN_FIXES.md` and commits:
```bash
git add best-practices/ops-hub/KNOWN_FIXES.md
git commit -m "chore(ops-hub): log diagnosis for [workflow name]"
git push
```

### Issue lifecycle
- **Tier 3 (issue only)**: GitHub issue created for human review
- **Tier 1/2 (fix applied)**: Claude comments on the open issue with fix details, then closes it

---

## Maintaining This Folder

- **KNOWN_FIXES.md** is auto-updated — do not edit manually
- **DOMAIN_PATTERNS.md** can be updated manually to add new worked examples or update
  domain-specific patterns as the codebase evolves
- When you add a new workflow to the ops-hub monitoring list, add a domain section to
  `DOMAIN_PATTERNS.md`

---

## OAuth Token Refresh Procedure

**Token type:** OAT (OAuth Access Token) — prefix `sk-ant-oat01-...`. Valid for 1 year.

When refreshing the CLAUDE_CODE_OAUTH_TOKEN:
1. Run `claude auth login` → follow browser prompts → token printed once at the end
   - Store immediately — the token cannot be retrieved later
   - Token format: `sk-ant-oat01-...` (1-year validity)
2. Set in **two places:**
   - **GitHub Secret:** `gh secret set CLAUDE_CODE_OAUTH_TOKEN` (paste value)
   - **GitHub Variable** (not Secret): `CLAUDE_TOKEN_EXPIRES_AT` = expiry in `YYYY-MM-DD`
3. **Verify the secret is actually populated** — `gh secret list` only shows names, not values:
   ```bash
   gh workflow run claude-qa-check.yml --field scope=full
   # Watch the run — if it passes auth (runs >30s), the secret is good
   ```
4. Optionally set in local `.env` for development

**Common mistake:** `CLAUDE_TOKEN_EXPIRES_AT` stored as a Secret (write-only) instead of a Variable (readable). The ops-hub expiry check needs to READ the date — it must be a Variable.

The daily expiry check in `claude-ops-hub.yml` will send Slack warnings 3 days before expiry.

---

## Issue Close Protocol

An ops-hub or daily-qa issue should be closed when ONE of these conditions is met:

| Tier | Close When |
|------|-----------|
| TIER 1 (auto-fix) | Auto-closed by Ops Hub after commit is verified |
| TIER 2 (PR) | Closed after PR is merged and Henrik APPROVED |
| TIER 3 (issue-only) | Closed after: (a) root cause identified, (b) fix implemented via standard pipeline (junior dev → Henrik), (c) fix verified in next pipeline run |

**Who can close:**
- Ops Hub closes TIER 1 automatically
- Solomon closes TIER 2 after Henrik's PR review is merged
- Solomon closes TIER 3 after fix is verified

**Stale issues:** Auto-labeled `stale` after 14 days inactivity. Auto-closed after 30 days. Critical issues exempt.

**Never close without:**
- Confirming the root cause is resolved (not just the symptom)
- Verifying the fix in at least one subsequent pipeline run
- Logging the fix in `KNOWN_FIXES.md` (Ops Hub does this automatically for TIER 1/2)
