# Version Monitoring — Release Intelligence

**Owner:** Henrik (Code Auditor)
**Frequency:** Session start — check before reviewing any diffs
**Added:** 2026-03-04

Henrik runs this scan at the top of every Agent Teams session. The goal is to catch
upstream breaking changes *before* they silently break production workflows.

---

## What to Watch

### Anthropic

| Resource | What to check | Why it matters |
|----------|--------------|----------------|
| `anthropics/claude-code-action` releases | New tags, SHA changes to `@v1` | Floating `@v1` auto-updates — a bad bump breaks ALL 4 Claude workflows simultaneously (Mar 4, 2026 incident) |
| `anthropics/claude-code` releases | New CLI versions | Claude Code CLI updates may change command flags, output format, or `settings.json` schema used by Agent Teams |
| `claude.ai/release-notes` | Feature changes, model updates, OAuth changes | Token format or auth flow changes can silently expire `CLAUDE_CODE_OAUTH_TOKEN` behavior |
| `anthropics/anthropic-sdk-python` releases | Breaking changes to `anthropic` package | Pinned in `requirements.txt` — if Claude SDK bumps a major version, `claude_prompts.py` callers may break |

### Google / Gemini

| Resource | What to check | Why it matters |
|----------|--------------|----------------|
| `google-gemini/gemini-cli` releases | New versions, flag changes | We invoke `gemini -p "..." --yolo -m gemini-2.5-pro` as subprocess in writer workflow — flag renames break silent subprocess calls |
| `google-generativeai` PyPI | New versions | Python SDK used in `employees/` scripts + potential future `utils/gemini_client.py`. Breaking changes = import errors at pipeline start |
| Google AI Studio release notes | New model IDs, deprecations | `gemini-2.5-pro` model ID could be renamed or deprecated — agents would silently fall back to a weaker model |

---

## How to Check (Scan Pattern)

```bash
# 1. claude-code-action — check current @v1 SHA vs what we have pinned
gh api repos/anthropics/claude-code-action/git/ref/tags/v1 --jq '.object.sha'
# Compare to SHA in .github/workflows/ (if we're pinned) or note it for monitoring

# 2. Latest claude-code-action release
gh release list --repo anthropics/claude-code-action --limit 3

# 3. Latest Claude Code CLI release
gh release list --repo anthropics/claude-code --limit 3

# 4. anthropic Python SDK — check latest vs requirements.txt
pip index versions anthropic 2>/dev/null | head -1
grep "anthropic" requirements.txt

# 5. google-generativeai — check latest vs requirements.txt
pip index versions google-generativeai 2>/dev/null | head -1
grep "google-generativeai" requirements.txt
```

---

## Red Flags — Escalate to Solomon Immediately

| Signal | Action |
|--------|--------|
| `@v1` SHA changed on `claude-code-action` since last session | Check KNOWN_FIXES.md for prior broken bump pattern. If new bump = likely broken, alert Solomon before any workflows trigger. |
| New `claude-code-action` release is a major/minor bump (e.g. `v1 → v2`, or `v1.1`) | Update all 4 workflows to the new stable tag. This is an **unpin opportunity**. |
| `anthropic` SDK major version bump (e.g. `0.x → 1.x`) | Check changelog for breaking changes. Run: `python -c "import anthropic; print(anthropic.__version__)"` to confirm what's installed in `.venv`. |
| `gemini-cli` flag renamed or removed | Check our Agent Teams scripts in `employees/` for any subprocess calls. |
| Model ID `gemini-2.5-pro` deprecated | Find replacement model ID and update all invocations. |

---

## Crash Signature Reference

If a `claude-code-action` run fails with these signatures — check for a bad `@v1` bump first:

```
is_error: true
total_cost_usd: 0
num_turns: 1
duration_ms: ~300–700ms
```

Logs show minified JS dump (`depsCount`, `dependencies` keyword) — this is the SDK's
error-wrapper function, NOT an AJV bug. Real error is hidden.

**Diagnostic:** Add `show_full_output: true` to the failing step → real error appears above the JS dump.

Full incident writeup: `KNOWN_FIXES.md` → "2026-03-04 — claude-code-action: AJV crash = misleading error"

---

## Monitored Packages in `requirements.txt`

These are the packages where a version bump can silently break the pipeline:

| Package | Risk level | Why |
|---------|-----------|-----|
| `anthropic` | HIGH | All Claude API calls, Agent Teams, `claude_prompts.py` |
| `google-generativeai` | MEDIUM | Gemini writer workflow, future `utils/gemini_client.py` |
| `python-telegram-bot` | MEDIUM | Ask Ludi bot + Solomon bot — async API changes can break handlers |
| `playwright` | LOW | Ghost Protocol scraper — Chromium updates occasionally break selectors |
