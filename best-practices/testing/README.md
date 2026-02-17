# Testing Best Practices

**Status:** 📋 Planned (not yet documented)

This category will contain patterns for testing, validation, and quality assurance.

## Planned Topics

### Unit Testing Patterns
- Test structure and organization
- Mock patterns for external dependencies (APIs, database)
- Test fixture design
- Assertion best practices
- Test naming conventions

### Integration Testing Strategies
- End-to-end pipeline testing
- Database testing patterns
- API integration tests
- Workflow testing (GitHub Actions)

### Backtest Validation Frameworks
- Historical data validation
- Performance metric tracking (RMSE, Brier score, hit rate)
- Drift detection patterns
- Regression testing for model changes

### Mock Data and Fixtures
- Creating realistic test data
- Database fixtures for consistent testing
- API response mocking
- Time-based test data (game dates, seasons)

### Quota-Aware API Testing
- Testing without burning API quota
- Mock API responses for frequent tests
- When to use real API vs mocks
- Test environment API key management

### CI/CD Test Automation
- Automated test runs on push/PR
- Test result reporting
- Fast tests vs comprehensive test suites
- Parallel test execution

### Test Coverage Strategies
- What to test vs what to skip
- Critical path testing
- Edge case identification
- Error condition testing

## Testing Patterns from Ludi-Bot

### Smoke Test Pattern
```python
# Quick validation that module imports and basic function works
python -c "from module_e import LudiCalibrator; print('✅ Module E OK')"
```

### Database Integrity Test
```python
# Verify schema and data quality
python scripts/validate_schema.py --verbose
python scripts/validate_canonical_ids.py
```

### API Integration Test
```python
# Test API without burning quota (use cache)
from utils.nba_api_client import get_nba_client
client = get_nba_client()
splits = client.get_player_shooting_splits(player_id=203507, season="2025-26")
assert splits is not None and len(splits) > 0
```

### Backtest Validation Pattern
```python
# Run 21-day backtest to validate recent performance
python scripts/backtest_fatigue_21day.py --verbose
# Check RMSE < threshold, hit rate > 52%
```

## Future Skill

**`/test-gen`** - Automated test generation
- Analyzes code and generates unit tests
- Creates mock patterns for external dependencies
- Suggests edge cases to test
- Generates: test file templates ready to fill in
