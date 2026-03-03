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

When refreshing the CLAUDE_CODE_OAUTH_TOKEN:
1. Go to claude.ai in Chrome → open DevTools (`Cmd+Option+I`) → Application → Cookies → `claude.ai`
   - Look for `sessionKey` cookie → copy value (`sk-ant-sid01-...`)
   - **Note:** `claude auth login` opens a browser flow but has no `token` print command — cookie grab is the reliable method
2. Paste the `sk-ant-sid01-...` value into GitHub Secrets: `CLAUDE_CODE_OAUTH_TOKEN`
3. Update GitHub **Variable** (not Secret): `CLAUDE_TOKEN_EXPIRES_AT` = new expiry date (YYYY-MM-DD)
   - New tokens are valid for ~30 days from issue date
   - Example: token issued Mar 3, 2026 → expires ~Apr 3, 2026

The daily expiry check in `claude-ops-hub.yml` will send Slack warnings 3 days before expiry.
