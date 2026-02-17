# Deployment Best Practices

**Status:** 📋 Planned (not yet documented)

This category will contain patterns for CI/CD, production operations, and deployment strategies.

## Planned Topics

### GitHub Actions Workflow Patterns
- Workflow structure and organization
- Job and step design
- Timeout management (workflow + step level)
- Parallel vs sequential execution
- Conditional execution patterns

### Secret Management
- GitHub Actions secrets vs environment variables
- Secret rotation procedures
- Multi-environment secret handling (dev/staging/prod)
- API key separation per project
- Secrets validation and testing

### Environment Configuration
- `.env` file management (local vs CI/CD)
- `IS_SELF_HOSTED` flag pattern
- Multi-environment config strategy
- Feature flags and toggles

### Database Operations in Production
- Backup strategies (automated + manual)
- Migration procedures (schema changes)
- Rollback procedures
- Data integrity verification
- Deduplication before index creation

### Rollback Procedures
- When to rollback vs forward-fix
- Git revert strategies
- Database restore procedures
- Workflow rollback (re-run previous version)
- Communication during rollbacks

### Production Monitoring
- Health check patterns
- Alerting thresholds
- Log aggregation and analysis
- Performance monitoring (API latency, DB query time)
- Error rate tracking

### Deployment Checklist
- Pre-deployment validation
- Deployment steps
- Post-deployment verification
- Smoke tests after deployment

### Workflow Failure Handling
- Telegram failure notifications
- Claude Ops Hub reactive diagnosis
- Manual intervention procedures
- Retry strategies

## Deployment Patterns from Ludi-Bot

### Database Persistence Pattern
```yaml
# CRITICAL: Preserve database between workflow runs
- name: Checkout repository
  uses: actions/checkout@v4
  with:
    clean: false  # Don't delete ludi.db
```

### Database Integrity Before Sync
```yaml
- name: Initialize database if needed
  run: |
    INTEGRITY=$(sqlite3 ludi.db "PRAGMA integrity_check;" 2>&1)
    if [ "$INTEGRITY" != "ok" ]; then
      mv ludi.db ludi.db.corrupted.$(date +%Y%m%d_%H%M%S)
      python3 database.py
    fi
```

### Automatic Deduplication
```yaml
# Deduplicate BEFORE creating UNIQUE indexes
- name: Ensure database indexes
  run: |
    python3 -c "
    DELETE FROM player_game_logs
    WHERE rowid NOT IN (
        SELECT MIN(rowid) FROM player_game_logs
        GROUP BY game_id, player_id
    )
    "
```

### Telegram Failure Alerts
```yaml
- name: Notify on failure
  if: failure()
  run: |
    python3 -c "from utils.telegram_notifier import send_message;
                send_message('❌ WORKFLOW FAILED')"
```

### Git Race Condition Prevention
```bash
# Prevent conflicts from parallel workflows
git pull --rebase
git add .
git commit -m "..."
git push
```

## Future Skill

**`/deploy-check`** - Pre-deployment validation
- Runs all pre-deployment checks automatically
- Validates: tests pass, no uncommitted changes, backups exist
- Checks: workflow syntax, secret availability, resource limits
- Generates: deployment readiness report + go/no-go recommendation
