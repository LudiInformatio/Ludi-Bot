# Data Modeling Best Practices

**Status:** 📋 Planned (not yet documented)

This category will contain patterns for database design, schema management, and data quality.

## Planned Topics

### Schema Design Principles
- Table design patterns
- Column naming conventions
- Primary key strategies
- Foreign key relationships
- When to normalize vs denormalize

### Index Optimization
- When to create indexes
- Composite indexes vs single-column
- Index maintenance (rebuild, analyze)
- Query plan analysis (EXPLAIN)
- Index overhead considerations

### Data Normalization
- Normal forms (1NF, 2NF, 3NF)
- When to denormalize for performance
- Lookup tables vs inline values
- Reducing data duplication

### Canonical ID Systems
- ID resolution patterns
- Multi-source ID mapping (Tank01, NBA, BDL)
- Name normalization for matching
- Handling ID format changes
- Fallback matching strategies

### ETL Pipeline Patterns
- Extract, Transform, Load workflows
- Incremental vs full refresh
- Data validation before insert
- Deduplication strategies
- Error handling in pipelines

### Data Validation Strategies
- Schema validation on ingestion
- Data quality checks (integrity, completeness)
- Constraint enforcement (UNIQUE, NOT NULL, CHECK)
- Referential integrity
- Data type validation

### Migration Patterns
- Schema change procedures
- Backward compatibility
- Data backfill strategies
- Testing migrations
- Rollback procedures

### Performance Optimization
- Query optimization techniques
- Batch operations vs individual inserts
- Transaction management
- Connection pooling
- Cache-aside pattern

## Data Modeling Patterns from Ludi-Bot

### Canonical ID Mapping
```sql
CREATE TABLE player_canonical_ids (
    input_id TEXT PRIMARY KEY,
    canonical_id INTEGER NOT NULL,
    source TEXT NOT NULL,
    confidence REAL DEFAULT 1.0
);
```

### Deduplication Before UNIQUE Index
```sql
-- CRITICAL: Deduplicate FIRST
DELETE FROM player_game_logs
WHERE rowid NOT IN (
    SELECT MIN(rowid)
    FROM player_game_logs
    GROUP BY game_id, player_id
);

-- THEN create UNIQUE index
CREATE UNIQUE INDEX idx_player_game_logs_unique
ON player_game_logs(game_id, player_id);
```

### Composite Index for Common Queries
```sql
-- Optimized for: SELECT * FROM player_game_logs WHERE player_id = ? AND game_date = ?
CREATE INDEX idx_player_game_logs_player_date
ON player_game_logs(player_id, game_date);
```

### Auto-Healing ID Resolution
```python
# Database.py pattern: resolve dirty IDs before insert
def insert_player(self, player_data):
    # Resolve Tank01 composite IDs to canonical NBA IDs
    canonical_id = self.id_resolver.resolve(player_data['id'])
    player_data['id'] = canonical_id
    # Now insert with clean ID
```

### Data Validation on Ingestion
```python
# Validate before insert prevents corrupt data
def validate_game_log(row):
    assert row['minutes'] >= 0, "Negative minutes"
    assert row['points'] >= 0, "Negative points"
    assert row['game_date'] <= datetime.now().date(), "Future date"
    # Only insert if all validations pass
```

## Known Data Quality Issues

### Tank01 ID Format Change (Jan 2026)
**Problem:** Tank01 changed from 7-digit NBA IDs to 11-digit composite IDs
**Impact:** 271+ duplicate player records
**Fix:** Canonical ID mapping table + database-level resolution

### BDL Team Abbreviation Mismatch
**Problem:** BDL uses GS/NO/NY/PHO/SA vs our GSW/NOP/NYK/PHX/SAS
**Fix:** Normalization layer in `bdl_client.py`

### Accent Mismatches (Dončić vs Doncic)
**Problem:** Tank01 returns ASCII, NBA API returns UTF-8
**Fix:** Name normalization strips accents before matching

## Future Skill

**`/schema-audit`** - Database design review
- Analyzes schema for optimization opportunities
- Checks: missing indexes, redundant data, constraint violations
- Suggests: normalization improvements, index additions
- Generates: schema health report + migration recommendations
