# Ludi Bot - Setup and Execution Instructions

## ✅ Status: Ready to Run

All dependencies have been installed and the system is configured. You just need to add your API keys.

## Prerequisites Installed

- ✅ Python 3.12.3
- ✅ All required dependencies from `requirements.txt`
- ✅ Basic `.env` file created

## Required API Keys

To run the system, you need to obtain and configure these API keys in the `.env` file:

### 1. The-Odds-API Key (REQUIRED)
- **Purpose**: Fetches game lines and player props
- **Get key**: https://the-odds-api.com/
- **Pricing**: Free tier (500 credits/month) or Paid ($30/mo for 20K credits)
- **Add to `.env`**: Replace `your_odds_api_key_here` with your actual key

### 2. Tank01 API Key (REQUIRED)
- **Purpose**: Player rosters, injuries, and box scores
- **Get key**: https://rapidapi.com/tank01/api/tank01-fantasy-stats
- **Pricing**: Free tier (1K/month) or Paid ($10/mo for 1K/day)
- **Add to `.env`**: Replace `your_tank01_key_here` with your actual key

## How to Run

### Basic Usage
```bash
# Run the full daily pipeline
python3 main.py

# Run for specific teams only
python3 main.py --games CLE SAC

# Send results to Telegram (if configured)
python3 main.py --send-telegram

# Show help and all options
python3 main.py --help
```

### Available Modes
```bash
# Standard simulation mode (default)
python3 main.py --mode interactive

# Generate PM morning briefing
python3 main.py --mode pm_briefing

# Generate PM nightly debrief
python3 main.py --mode pm_debrief
```

## What the System Does

When you run `main.py`, it will:

1. **Fetch Game Slate** - Pull today's NBA games and betting lines
2. **Load Player Props** - Get player prop markets from sportsbooks
3. **Build Rosters** - Query database for active players
4. **Check Injuries** - Fetch latest injury reports (Module D - Yak)
5. **Run Simulations** - Execute Monte Carlo simulations (5,000 iterations per scenario)
6. **Calculate Edge** - Apply devigging and edge calculation (Module F - Alchemist)
7. **Generate Report** - Create daily betting briefing
8. **Output Results** - Save to `daily_briefing.txt`

## Output

After running, you'll find:
- **daily_briefing.txt** - Full betting recommendations report
- Console output showing the entire process

## Troubleshooting

### "Missing REQUIRED API keys" Error
- Open `.env` file and replace placeholder values with actual API keys
- Ensure no quotes around the key values
- Save the file and try again

### "No games found" Message
- System might be running on a day with no NBA games
- Try using `--games TEAM1 TEAM2` to target specific teams
- Check if it's the NBA off-season

### Import Errors
- Run: `python3 -m pip install -r requirements.txt`
- Ensure you're using Python 3.12 or compatible version

## Project Documentation

For more details, see:
- **CLAUDE.md** - Full architecture and development guide
- **README.md** - Project overview
- **UPDATED_STATUS_AND_NEXT_STEPS.md** - Current project status

## Support

For issues or questions, refer to the project documentation or check the GitHub repository issues.
