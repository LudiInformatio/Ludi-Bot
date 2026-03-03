# Workflow Archive

Workflows here are **disabled and not executed** by GitHub Actions.
GitHub Actions only processes `.yml` files in the root of `.github/workflows/`,
not in subdirectories — so files here are safely inert.

## Why archive instead of delete?
- Preserves the file as a dated reference point
- Allows recovery if the workflow needs to be reactivated
- Documents why it was disabled (context lives in git history)

## Archive convention
When disabling a workflow:
1. Move the file here (do NOT delete it)
2. Add a comment at the top: `# ARCHIVED: [date] — [reason]`
3. Update CLAUDE.md automation schedule (remove or add [ARCHIVED] note)