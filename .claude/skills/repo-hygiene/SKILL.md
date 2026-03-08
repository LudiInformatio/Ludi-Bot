---
name: repo-hygiene
description: >
  Run repository hygiene audit. Checks file staleness, archive compliance,
  .gitignore gaps, remote sync health, doc freshness, and size warnings.
  Trigger phrases: "repo hygiene", "audit repo", "run /repo-hygiene", "/repo-hygiene".
agent: kai
user-invocable: true
---

# Repo Hygiene Audit

**Owner:** Kai (Repo Custodian)

## Overview

This skill runs a 6-check repository hygiene audit. Each check uses `git log`, `Bash`, and `Glob` — no text search required. Output is a structured 7-section report surfacing every candidate for human or Silas review.

## When to Use

- Use before major releases or sprints to clear repo debt
- Use when `.gitignore` gaps are suspected (untracked files in `git status`)
- Use when `git status` shows unexpected untracked or modified files
- Do not use for code quality review — that is `/simplify` + `/ludi-audit`

---

## Workflow

Work through all 6 checks in order. Collect findings per section. Output the full 7-section report at the end.

---

### Check 1 — Stale Scripts and Utils (>60 days)

For each `.py` file in `scripts/` and `utils/` (excluding `_archive/` subdirs):

```bash
git log --format="%ci" -- <file> | head -1
```

If the last commit date is > 60 days ago: add to STALE_FILES and evaluate for ARCHIVE_CANDIDATES.

A file is an ARCHIVE_CANDIDATE when ALL three conditions hold:
1. Last commit > 60 days ago
2. Not referenced as a `run:` command in any `.github/workflows/*.yml` file
3. Not in an `_archive/` subdirectory already

---

### Check 2 — Archive Compliance

Scan for `.py` files inside `scripts/_archive/`, `utils/_archive/`, `.github/workflows/_archive/`:

```bash
head -3 <archived_file>
```

- PASS if first or second line contains `# ARCHIVED: YYYY-MM-DD — [reason]`
- FLAG if header is missing — add to ARCHIVE_CANDIDATES with note "missing header"

---

### Check 3 — `.gitignore` Coverage

Check that the following entries exist in `.gitignore`:

| Pattern | Reason |
|---------|--------|
| `.env` | API keys and credentials |
| `ludi.db` | Binary database |
| `ludi.db-wal` | SQLite WAL file |
| `ludi.db-shm` | SQLite shared memory |
| `cache/` | Ephemeral dossier JSON |
| `logs/` | Runtime logs |
| `*.gz` | Compressed backups |
| `archives/data/` | Database backup archives |
| `.venv/` | Virtual environment |
| `__pycache__/` | Python cache |
| `*.pyc` | Python bytecode |
| `tui.json` | Local TUI config |
| `opencode.json*` | Local opencode config |
| `yak_cache.json` | Injury cache file |

For each missing entry: add to GITIGNORE_GAPS.

Also run:
```bash
git status --short
```
Flag any untracked file matching the above patterns that is not already in `.gitignore`.

---

### Check 4 — Remote Sync Health

```bash
git status
git log origin/main..HEAD --oneline
git branch -vv
```

- Flag unpushed commits (count > 0): SYNC_ISSUES
- Flag any local branch with no upstream tracking: SYNC_ISSUES
- Flag diverged branches (`ahead N, behind M`): SYNC_ISSUES

Do NOT run `git push` or `git pull`. Report only.

---

### Check 5 — Doc Freshness (>30 days)

For each `.md` file in `docs/` and `best-practices/`:

```bash
git log --format="%ci" -- <file> | head -1
```

Thresholds:
- `docs/` files: > 30 days without commit → DOC_STALE
- `best-practices/` files: > 45 days without commit → DOC_STALE

Skip: `docs/STATUS_HISTORY.md` (archive file, intentionally static after sprint close)

---

### Check 6 — Size Warnings

```bash
find . \
  -size +5M \
  -not -path "*/.git/*" \
  -not -path "*/.venv/*" \
  -not -path "*/archives/*" \
  -not -name "ludi.db"
```

Flag any result as SIZE_WARNINGS with file path and size in MB.

Also check total repo size (excluding `.git/`, `.venv/`, `archives/`):
```bash
du -sh --exclude='.git' --exclude='.venv' --exclude='archives' .
```
Flag if total > 100 MB.

---

## Output

Produce the full 7-section report in this exact format:

```
## Kai Repo Report — [YYYY-MM-DD]

### STALE_FILES (>60 days untouched)
[file path] — last modified [date], [N] days ago
... or: none

### ARCHIVE_CANDIDATES
[file path] — [reason]
... or: none

### GITIGNORE_GAPS
[pattern] — [missing from .gitignore / found untracked in git status]
... or: none

### SYNC_ISSUES
[description] — [unpushed/orphaned/diverged]
... or: none

### DOC_STALE (>30 days)
[doc path] — last modified [date], [N] days ago
... or: none

### SIZE_WARNINGS
[file path] — [X.X] MB
... or: none

### SUMMARY
Total stale: N | Archive candidates: N | Gitignore gaps: N | Sync issues: N | Docs stale: N | Size warnings: N
```

---

## Escalation Rules

- GITIGNORE_GAPS or SYNC_ISSUES → flag for Silas review
- ARCHIVE_CANDIDATES with code quality concerns → flag for Henrik review
- STALE_FILES and DOC_STALE → log in report, no escalation required

## References

- `employees/kai/SOUL.md` — Kai's identity and responsibilities
- `employees/kai/ONBOARDING.md` — archive conventions, gitignore rules, thresholds
- `.github/workflows/` — source of truth for which scripts are active
