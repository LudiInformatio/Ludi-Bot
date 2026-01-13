# 🚀 Ludi Bot - Quick Start Guide

## Current Status: ✅ READY TO RUN

All dependencies are installed and the system is configured. You just need to add your API keys!

---

## Step 1: Get API Keys

### Required Keys

1. **The-Odds-API** (Game lines & player props)
   - Sign up: https://the-odds-api.com/
   - Free: 500 requests/month
   - Paid: $30/mo for 20,000 requests/month

2. **Tank01** (Rosters, injuries, stats)
   - Sign up: https://rapidapi.com/tank01/api/tank01-fantasy-stats
   - Free: 1,000 requests/month
   - Paid: $10/mo for 1,000 requests/day

---

## Step 2: Configure .env File

Open the `.env` file and replace the placeholder values:

```bash
# Before (placeholder)
ODDS_API_KEY=your_odds_api_key_here
TANK01_KEY=your_tank01_key_here

# After (your actual keys)
ODDS_API_KEY=abc123xyz456...
TANK01_KEY=def789uvw012...
```

---

## Step 3: Verify Setup

Run the verification script to check if everything is ready:

```bash
python3 verify_setup.py
```

You should see:
```
✅ All dependencies installed!
✅ .env file exists
✅ ODDS_API_KEY configured
✅ TANK01_KEY configured
✅ System is ready to run!
```

---

## Step 4: Run the Bot

### Basic Usage

```bash
# Run for all games today
python3 main.py

# Run for specific teams only
python3 main.py --games CLE SAC

# Send results to Telegram (if configured)
python3 main.py --send-telegram
```

### View Options

```bash
# See all available commands
python3 main.py --help
```

---

## What Happens When You Run

1. **Fetches Game Slate** - Today's NBA games from The-Odds-API
2. **Loads Props** - Player prop markets from sportsbooks
3. **Checks Injuries** - Latest injury reports from Tank01
4. **Runs Simulations** - 5,000 Monte Carlo iterations per scenario
5. **Calculates Edge** - Devigging + edge calculation
6. **Generates Report** - Saves to `daily_briefing.txt`

---

## Output Files

After running:
- **`daily_briefing.txt`** - Full betting recommendations
- **Console output** - Real-time progress and results

---

## Troubleshooting

### "Missing REQUIRED API keys"
- Make sure you edited `.env` with real API keys (not placeholders)
- Check that there are no quotes around the key values
- Ensure the file is saved

### "No games found"
- System runs on NBA game days only
- Try `--games TEAM1 TEAM2` to target specific teams
- Check if it's the off-season

### Dependencies Issues
```bash
# Reinstall all dependencies
python3 -m pip install -r requirements.txt
```

---

## Additional Documentation

- **SETUP_INSTRUCTIONS.md** - Detailed setup guide
- **CLAUDE.md** - Full architecture documentation
- **README.md** - Project overview

---

## Need Help?

1. Run `python3 verify_setup.py` to diagnose issues
2. Check existing documentation files
3. Review error messages for specific guidance

---

**🎯 System Architecture:** Modular pipeline (A-H modules)  
**📊 Database:** SQLite with 10,000+ historical game logs  
**🧮 Engine:** Hybrid Poisson/Normal Monte Carlo simulation  
**💎 Output:** Diamond-tier betting recommendations

**Ready to run? Just add your API keys and execute `python3 main.py`!**
