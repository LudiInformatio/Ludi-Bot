# Communication Protocol
**Last Updated:** March 8, 2026

## Channel Routing Matrix

| Platform | Purpose | Who Posts |
|----------|---------|-----------|
| Telegram | Betting product only — bet cards, P&L, Ask Ludi, morning/evening briefings | Automated pipeline + Ask Ludi bot |
| Slack | Ops/pipeline alerts (automated), PM briefings, daily work notes | Automated workflows, Solomon |
| Discord `#incidents` | Any critical issue needing team attention (P0/P1) | Silas (auto), any employee (manual) |
| Discord `#{employee}` | Employee-specific work + async collaboration | That employee only |
| Discord `#weekly-roundtable` | Solomon's Sunday synthesis | Solomon |
| GitHub Issues | Bugs, feature requests, technical debt | Owner, Henrik |
| GitHub PR comments | Code review | Henrik domain only |

**"Not my channel" rule:** Employees never post in another employee's Discord channel.

---

## Decision Authority Matrix

| Domain | Approver | Fallback | Log required? |
|--------|----------|----------|---------------|
| Modifier changes | Owner | N/A | Yes — ADR entry |
| Prompt / BERT changes | Maren → Owner | — | Yes |
| Code architecture | Henrik → Owner | — | Yes |
| Data model / schema | Lena → Owner | — | Yes |
| Card format / copy | Henrik | Owner | No |
| Routine scripts | Junior dev → Henrik | — | No |

---

## Escalation Paths

### P0 — Pipeline down before 11 AM
Silas detects → posts to Discord `#incidents` → notifies Henrik (if code fix needed) → Owner paged if unresolved after 1 hour

### P1 — Data drift (RMSE > 7.5 for 3+ consecutive days)
Lena detects → posts to Discord `#incidents` → opens GitHub issue → Henrik sprint

### P2 — Security incident (leaked key or credential)
Owner → rotate in provider dashboard immediately → update `.env` → post to `#incidents` → postmortem within 24 hours

---

## Response Time SLAs

| Severity | Response Time | Example |
|----------|--------------|---------|
| P0 | 15 minutes | Pipeline down before briefing |
| P1 | 1 hour | Data staleness, RMSE drift |
| P2 | 24 hours | Security incident postmortem |

---

## Employee Discord Channels

| Employee | Channel | Purpose |
|----------|---------|---------|
| Silas | `#silas` | Infrastructure health reports |
| Henrik | `#henrik` | Code audit findings |
| Lena | `#lena` | Data analysis reports |
| Vera | `#vera` | QA check results |
| Solomon | `#solomon` | PM routing + sprint summaries |
| Maren | `#maren` | Prompt engineering reports |
| Iris | `#iris` | Social intelligence signals |
| Kai | N/A | On-demand only (posts to Silas if escalating) |
| All employees | `#incidents` | P0/P1 issues only |
| All employees | `#weekly-roundtable` | Solomon Sunday synthesis |
