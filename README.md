# Ludi Lens v2.0 - Day 1 Quick Start

## What You Have Right Now

### 1. `prototype_engine.py` - The Math Validator
**What it does**: Simulates NBA player scoring using Poisson distributions and demonstrates the "Usage Vacuum" effect when a star player is OUT.

**How to run**:
```bash
cd /home/mnprice86/ludi_bot
./venv/bin/python prototype_engine.py
```

**What you'll see**:
- Damian Lillard's projection with Giannis HEALTHY
- Damian Lillard's projection with Giannis OUT (watch his usage % increase!)
- Probability of 30+ point games in each scenario

### 2. `database.py` - The Memory System
**What it does**: Creates and manages the SQLite database (`ludi.db`) that will store all your player data, odds, and simulation results.

**How to test**:
```bash
./venv/bin/python database.py
```

**What you'll see**:
- Database file created at `/home/mnprice86/ludi_bot/ludi.db`
- Test player (Giannis) inserted successfully

---

## Next Steps (After Dependencies Install)

1. **Verify the Math** - Run `prototype_engine.py` and confirm the Usage Vacuum logic makes sense
2. **Check the Database** - Run `database.py` and use SQLite Viewer to see the tables
3. **Build the Ingestor** - Create `ingest_gameline.py` to pull real odds from The-Odds-API

---

## Your Current Stack

- **Language**: Python 3.11
- **Environment**: Virtual environment (`venv/`)
- **Database**: SQLite (`ludi.db`)
- **Math Engine**: NumPy + SciPy (Poisson distributions)
- **Version Control**: Git (initialized)

---

## Files Created So Far

```
ludi_bot/
├── .git/                    # Version control
├── .gitignore              # Protects API keys
├── venv/                   # Python environment
├── prototype_engine.py     # ✅ Day 1 Testing
├── database.py            # ✅ Data persistence
├── ludi.db                # (Created when you run database.py)
└── README.md              # This file
```

---

## The Hybrid Plan

**Phase 1 (This Week)**:
- [x] Git repository initialized
- [x] Virtual environment created
- [x] Prototype simulation engine built
- [x] Database schema designed
- [ ] Dependencies installed (in progress...)
- [ ] Run first simulation test
- [ ] Verify database creation

**Phase 2 (Next Week)**:
- [ ] Connect to The-Odds-API
- [ ] Pull real game lines
- [ ] Store odds in database
- [ ] Run simulations on real data

---

## Questions?

The prototype is **intentionally simple** - it uses hardcoded player stats to prove the math works. Once we verify the logic, we'll connect it to real APIs and automate everything.

**This is the "crawl before you walk" approach.**
