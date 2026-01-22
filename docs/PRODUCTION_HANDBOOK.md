# Ludi-Bot Production Handbook

**Version:** 1.0  
**Created:** January 21, 2026  
**Purpose:** Complete guide for production deployment and operation of the Ludi-Bot system.

---

## Table of Contents

1. [System Overview](#system-overview)
2. [Production Architecture](#production-architecture)
3. [Deployment Workflow](#deployment-workflow)
4. [Monitoring & Alerting](#monitoring--alerting)
5. [Maintenance Procedures](#maintenance-procedures)
6. [Troubleshooting Guide](#troubleshooting-guide)
7. [Performance Validation](#performance-validation)
8. [Emergency Procedures](#emergency-procedures)

---

## System Overview

### Core Components

**Ludi-Bot v2.0** is an NBA analytics platform that generates betting recommendations using:

- **Engine:** S.A.V.A.G.E. Protocol (Hybrid Poisson/Normal Simulations)
- **Data Pipeline:** 9 specialized modules (A-H + X)
- **Output:** Daily betting recommendations via Telegram + visual cards
- **Validation:** Automated backtesting and drift monitoring

### Key Features

- **Line Shopping:** NC Legal book integration (FanDuel, DK, BetMGM, etc.)
- **Fatigue Modeling:** B2B adjustments with research-backed modifiers
- **Matchup Intelligence:** 14+ archetype vs defense scheme modifiers
- **Real-time Monitoring:** System health checks with Telegram alerts
- **Automated Validation:** Weekly backtests for drift detection

---

## Production Architecture

### Infrastructure

**Self-Hosted Runner** (macOS Intel x64):
- **Location:** Local machine for WAF bypass
- **Container:** `ludi-core:latest` Docker image
- **Persistence:** Project root bind-mounted to `/app`

### Database

**SQLite (`ludi.db`)**:
- **Location:** Project root
- **Mode:** WAL (Write-Ahead Logging) enabled
- **Backups:** Automated 7-day rotation
- **Key Tables:** `player_game_logs`, `games`, `bet_recommendations`, etc.

### API Integrations

| Service | Tier | Quota | Purpose |
|---------|-------|-------|---------|
| The-Odds-API | PAID | 20K/mo | Game lines, player props |
| Tank01 | PAID | 1K/day | Rosters, injuries, box scores |
| PBP Stats | FREE | Unlimited | Shot quality, WOWY data |

---

## Deployment Workflow

### 1. Initial Setup

```bash
# Clone repository
git clone https://github.com/LudiInformatio/Ludi-Bot.git
cd Ludi-Bot

# Setup environment
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Configure secrets
cp .env.template .env
# Edit .env with API keys

# Initialize database
python database.py
```

### 2. Production Dry Run

**Always test before deployment:**

```bash
# Quick test (1 game)
./scripts/run_production_dry_run.sh --quick

# Full pipeline test
./scripts/run_production_dry_run.sh --verbose
```

**Expected Output:**
- ✅ Pipeline SUCCESS
- ✅ Health check PASSED  
- Visual cards generated
- No critical errors

### 3. GitHub Actions Activation

**Manual Trigger (Recommended First Time):**

1. Go to GitHub → Actions → Daily Production Pipeline
2. Click "Run workflow" 
3. Select test_mode: `false` (full run)
4. Monitor execution logs

**Scheduled Execution:**
- **Daily Pipeline:** 11:00 AM EST (Monday-Friday)
- **Weekly Validation:** Tuesday 4:00 AM EST
- **Data Sync:** 5:00 AM EST (daily)
- **Referee Sync:** 9:30 AM EST (daily)

---

## Monitoring & Alerting

### System Health Monitor

**Script:** `scripts/monitor_system_health.py`

**Checks Performed:**
- **Data Integrity:** Table updates in last 24h
- **Model Drift:** Projection variance > ±3.0 pts
- **Module Output:** Activity detection per module
- **API Health:** Quota usage monitoring

**Alert Levels:**
- 🚨 **Critical:** System failure, data corruption
- ⚠️ **Warning:** Performance degradation, approaching limits
- 📊 **Info:** Status updates, maintenance notices

### Production Metrics Dashboard

**Daily Summary (Telegram):**
```
📊 PROD SUMMARY 2026-01-21
🏀 Games: 8
💎 Bets: 24
❌ Errors: 0
⏰ Completed: 11:15:32
```

### Weekly Validation Report

**Backtest Results:**
- 21-day B2B fatigue validation
- 14-day playtype trends analysis
- Modifier drift detection (> ±1.5 pts)
- System health summary

---

## Maintenance Procedures

### Daily (Automated)

1. **Data Sync** (5:00 AM EST)
   - Fetch latest game results
   - Update player statistics
   - Sync injury reports

2. **Production Pipeline** (11:00 AM EST)
   - Run full simulation pipeline
   - Generate betting recommendations
   - Send visual cards to Telegram

3. **Health Monitoring**
   - Post-pipeline health check
   - API quota verification
   - Error alerting if needed

### Weekly (Automated)

**Tuesday 4:00 AM EST:**
- Run 21-day B2B fatigue backtest
- Run 14-day playtype trends backtest  
- Generate weekly validation report
- Check for modifier drift

### Monthly (Manual)

1. **Log Cleanup**
   ```bash
   python scripts/cleanup_old_logs.py --dry-run  # Preview
   python scripts/cleanup_old_logs.py             # Execute
   ```

2. **Database Maintenance**
   ```bash
   # Check database size and health
   sqlite3 ludi.db "PRAGMA integrity_check;"
   sqlite3 ludi.db "VACUUM;"
   ```

3. **Performance Review**
   - Review monthly hit rates and ROI
   - Analyze new patterns/trends
   - Plan system improvements

---

## Performance Validation

### Baseline Metrics (Phase 4)

**60-Day Backtest Results:**
- **Mean Error:** +1.22 pts (target: +0.56 pts) ✅
- **B2B vs Normal Rest:** 0.9 pts difference ✅
- **Sample Size:** 7,214 player-games
- **Status:** PRODUCTION READY

### Acceptable Thresholds

| Metric | Target | Alert Threshold |
|--------|--------|-----------------|
| Mean Error (PTS) | ±1.0 pts | ±3.0 pts |
| Hit Rate | > 52% | < 48% |
| ROI | > +2% | < -1% |
| API Quota | < 80% | > 90% |
| Module Activity | > 0 outputs | = 0 outputs |

### Weekly Validation Success Criteria

- **B2B Differential:** Within ±1.5 pts
- **Hit Rate:** > 52% overall
- **ROI:** > +2% 
- **No Critical Alerts:** System stability maintained

---

## Troubleshooting Guide

### Common Issues

#### 1. Pipeline Fails to Start

**Symptoms:** No games processed, early exit

**Check:**
```bash
# Verify environment
source .venv/bin/activate
python -c "import config; print('Config OK')"

# Check database
sqlite3 ludi.db "SELECT COUNT(*) FROM games;"

# Verify API keys
python -c "from utils.telegram_notifier import send_message; send_message('Test')"
```

**Common Causes:**
- Missing/invalid API keys in `.env`
- Database corruption or missing
- Network connectivity issues

#### 2. No Bets Generated

**Symptoms:** Pipeline runs but 0 betting recommendations

**Check:**
```bash
# Check odds fetching
python -c "from module_a import Gatekeeper; g = Gatekeeper(); print(len(g.fetch_live_slate()))"

# Check simulation output
python main.py --limit-games 1 --verbose | grep "💎"
```

**Common Causes:**
- No active games today
- Odds API issues
- Edge calculation thresholds too strict

#### 3. Telegram Notifications Missing

**Symptoms:** No visual cards or alerts

**Check:**
```bash
# Test Telegram connection
python -c "from utils.telegram_notifier import send_message; send_message('Test message')"

# Check bot configuration
curl "https://api.telegram.org/bot$TELEGRAM_TOKEN/getMe"
```

**Common Causes:**
- Invalid bot token
- Wrong chat ID
- Bot permissions revoked

### Debug Mode

**Enable verbose logging:**
```bash
export DEBUG_LOG=true
python main.py --verbose --limit-games 1
```

**Check specific modules:**
```bash
# Test Module A (Odds)
python -c "from module_a import Gatekeeper; print(Gatekeeper().fetch_live_slate())"

# Test Module D (Injuries) 
python -c "from module_d import LudiYak; print(LudiYak().get_injuries())"

# Test Module G (Referees)
python -c "from module_g import LudiRefEngine; print(LudiRefEngine().get_daily_assignments())"
```

---

## Emergency Procedures

### Critical System Failure

**Immediate Actions:**
1. **Check GitHub Actions status** - Identify failure point
2. **Run manual health check** - `python scripts/monitor_system_health.py`
3. **Test core functionality** - `./scripts/run_production_dry_run.sh --quick`
4. **Notify stakeholders** - Send alert via alternative channel

### Data Corruption Recovery

**Symptoms:** Database errors, missing data

**Recovery Steps:**
1. **Stop all automated workflows** (disable in GitHub Actions)
2. **Assess damage** - `sqlite3 ludi.db "PRAGMA integrity_check;"`
3. **Restore from backup** if needed:
   ```bash
   cp backups/database/ludi_db_YYYYMMDD.db ludi.db
   ```
4. **Verify recovery** - Run dry run test
5. **Resume operations** - Re-enable workflows

### API Quota Exhaustion

**Prevention:**
- Monitor usage in daily health checks
- Set alerts at 80% quota usage
- Implement request throttling if needed

**Response:**
1. **Check quota status** - Review API usage logs
2. **Identify cause** - Unexpected traffic, inefficient queries
3. **Temporary mitigation** - Switch to backup data sources
4. **Long-term fix** - Optimize API usage, increase quota

### Security Incident

**If secrets compromised:**
1. **Immediately rotate** all API keys in `.env`
2. **Review access logs** for unauthorized usage
3. **Update permissions** on all integrations
4. **Audit all credentials** - Change passwords as needed
5. **Monitor closely** for suspicious activity

---

## Appendices

### A. Configuration Files

**`.env` Variables:**
```
ODDS_API_KEY=your_the_odds_api_key
ODDS_API_TIER=paid
TANK01_KEY=your_tank01_key  
TANK01_TIER=paid
TELEGRAM_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
```

**Production Flags:**
```
IS_PRODUCTION=true
DEBUG_LOG=false
IS_SELF_HOSTED=true
```

### B. Useful Commands

**Database Queries:**
```sql
-- Recent games
SELECT * FROM games WHERE game_date >= date('now', '-7 days');

-- Active players  
SELECT COUNT(*) FROM players WHERE status = 'Active';

-- Recent bets
SELECT * FROM bet_recommendations 
WHERE created_at >= date('now', '-1 day')
ORDER BY edge_pct DESC;
```

**System Information:**
```bash
# Disk usage
du -sh . logs/ backups/

# Memory usage  
ps aux | grep python

# Network connectivity
curl -I https://api.the-odds-api.com/v4/sports/basketball_nba/scores
```

### C. Contact Information

**System Administrator:** [Contact details]
**GitHub Repository:** https://github.com/LudiInformatio/Ludi-Bot
**Documentation:** `CLAUDE.md`, `UPDATED_STATUS_AND_NEXT_STEPS.md`

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-01-21 | Initial production deployment handbook |

---

**This handbook is a living document. Update after any system changes or procedure modifications.**