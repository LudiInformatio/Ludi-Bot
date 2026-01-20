#!/bin/bash
# LUDI INFORMATIO | DAILY CRON MASTER
# Module G Automation Pipeline

# Defined paths
PROJECT_ROOT="/Users/flyprice/Desktop/Ludi Informatio/Projects/Ludi-Bot"
VENV_PYTHON="python3"
LOG_FILE="$PROJECT_ROOT/logs/ludi_cron.log"

# Ensure log directory exists
mkdir -p "$PROJECT_ROOT/logs"

echo "==========================================" >> "$LOG_FILE"
echo "LUDI DAILY CRON: $(date)" >> "$LOG_FILE"
echo "==========================================" >> "$LOG_FILE"

cd "$PROJECT_ROOT" || exit 1

# 1. Update Referee Trends (Daily Learning)
echo "[1/3] Running Daily Trends Learning..." >> "$LOG_FILE"
$VENV_PYTHON scripts/learn_daily_trends.py >> "$LOG_FILE" 2>&1

# 2. Analyze Star Bias (Forward Learning)
echo "[2/3] Analyzing Star Player Bias..." >> "$LOG_FILE"
$VENV_PYTHON scripts/analyze_star_bias.py >> "$LOG_FILE" 2>&1

# 3. Generate Morning Brief (Report + Visuals)
echo "[3/3] Generating Morning Brief..." >> "$LOG_FILE"
$VENV_PYTHON scripts/generate_morning_brief.py >> "$LOG_FILE" 2>&1

echo "LUDI DAILY CRON COMPLETE: $(date)" >> "$LOG_FILE"
echo "==========================================" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"
