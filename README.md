# Ludi-Bot

**NBA Player Projections Model**

A Python-based NBA analytics engine that generates player stat projections using Monte Carlo simulations and publicly available data.

---

## Overview

- Monte Carlo simulation engine (Poisson/Normal hybrid)
- Modular data pipeline (odds, stats, injuries, matchups)
- SQLite database with automated daily syncs
- GitHub Actions for scheduling and automation
- Telegram + Slack notification support

## Tech Stack

- **Language:** Python 3.11+
- **Database:** SQLite (WAL mode)
- **Automation:** GitHub Actions (self-hosted runner)
- **Notifications:** Telegram, Slack

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.template .env
# Add your API keys

python database.py   # Initialize schema
python main.py       # Run pipeline
```

## API Requirements

- [The-Odds-API](https://the-odds-api.com/) — Game lines and player props
- [Tank01](https://rapidapi.com/tank01/api/tank01-fantasy-stats) — Rosters, injuries, box scores

Optional: BallDontLie, Perplexity, SportsDataIO

## Documentation

See `docs/` for architecture details, methodology notes, and operational guides.

## License

Private repository — All rights reserved.
