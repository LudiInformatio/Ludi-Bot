# Debugging Best Practices

**Status:** 📋 Planned (not yet documented)

This category will contain strategies for debugging, troubleshooting, and issue diagnosis.

## Planned Topics

### Silent Failure Detection
- How to find errors that don't raise exceptions
- Audit patterns for `except: pass` and `except: continue`
- Data validation to catch missing/corrupt data early
- Logging strategies that reveal hidden problems

### Logging Strategies
- What to log (and what not to log)
- Log levels and when to use each (DEBUG, INFO, WARNING, ERROR)
- Structured logging patterns
- Performance logging (timing, resource usage)
- Avoiding log spam vs missing critical info

### Performance Profiling
- Identifying bottlenecks (CPU, memory, I/O)
- Database query optimization
- API call profiling (latency, rate limits)
- Memory usage tracking

### Memory Leak Detection
- How to spot memory leaks in Python
- Common causes (unclosed connections, circular references)
- Tools for memory profiling
- Prevention patterns

### Database Debugging
- Query performance analysis (EXPLAIN, indexes)
- Lock contention and timeout debugging
- Data integrity checks (PRAGMA integrity_check)
- Transaction debugging

### API Debugging Workflows
- Request/response logging
- Rate limit detection
- Quota tracking and exhaustion diagnosis
- Timeout vs error vs empty response
- Curl equivalent commands for manual testing

### Production Debugging
- Live system diagnosis without disrupting service
- Log analysis patterns (grep, awk, parsing)
- Correlation between logs and database state
- Rollback procedures when debugging shows critical issue

## Known Debugging Patterns from Ludi-Bot

### Silent Failure Bug (21-day hidden bug)
```python
# ❌ Bug: No visibility into failures
try:
    sync_wowy_data()
except Exception:
    continue

# ✅ Fix: Log errors even when continuing
try:
    sync_wowy_data()
except Exception as e:
    print(f"[ERROR] WOWY sync failed: {e}")
    continue
```

### Database Corruption Detection
```python
# Check integrity before critical operations
result = subprocess.run(['sqlite3', 'ludi.db', 'PRAGMA integrity_check;'],
                       capture_output=True, text=True)
if result.stdout.strip() != 'ok':
    print(f"⚠️ Database corrupted: {result.stdout}")
    # Move corrupted DB, reinitialize
```

## Future Skill

**`/debug-assist`** - Interactive debugging helper
- Guided troubleshooting workflow
- Suggests diagnostic steps based on symptoms
- Runs common debug queries automatically
- Generates: diagnostic report + recommended fixes
