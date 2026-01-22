#!/bin/bash
# Production Pipeline Dry Run Script
# 
# Usage: ./scripts/run_production_dry_run.sh [--quick] [--verbose]
# 
# Options:
#   --quick   Run with single game limit (fastest test)
#   --verbose Verbose output with detailed logging

set -e  # Exit on any error

# Default settings
QUICK_MODE=false
VERBOSE=false
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --quick)
            QUICK_MODE=true
            shift
            ;;
        --verbose)
            VERBOSE=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [--quick] [--verbose]"
            exit 1
            ;;
    esac
done

echo "🧪 PRODUCTION DRY RUN"
echo "===================="
echo "Mode: $([ "$QUICK_MODE" = true ] && echo "Quick (1 game)" || echo "Full Pipeline")"
echo "Verbose: $([ "$VERBOSE" = true ] && echo "Yes" || echo "No")"
echo "Started at: $(date)"
echo ""

# Change to project root
cd "$PROJECT_ROOT"

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo "❌ Virtual environment not found at .venv"
    echo "Run: python3.11 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt"
    exit 1
fi

# Activate virtual environment
echo "🔄 Activating virtual environment..."
source .venv/bin/activate

# Verify Python and key modules
echo "🔍 Verifying environment..."
python -c "
import sys
print(f'Python: {sys.version}')
try:
    import config
    print('✅ Config loaded')
except Exception as e:
    print(f'❌ Config failed: {e}')
    sys.exit(1)

try:
    import sqlite3
    conn = sqlite3.connect('ludi.db')
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM games')
    games = cursor.fetchone()[0]
    print(f'✅ Database: {games} games')
    conn.close()
except Exception as e:
    print(f'❌ Database failed: {e}')
    sys.exit(1)
"

if [ $? -ne 0 ]; then
    echo "❌ Environment verification failed"
    exit 1
fi

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p logs/production
mkdir -p logs/health
mkdir -p assets/generated
mkdir -p logs/backtest

# Set production environment flags
export IS_PRODUCTION=true
export DEBUG_LOG=false

# Build main.py command
MAIN_CMD="python main.py"
if [ "$QUICK_MODE" = true ]; then
    MAIN_CMD="$MAIN_CMD --limit-games 1"
fi

if [ "$VERBOSE" = true ]; then
    MAIN_CMD="$MAIN_CMD --verbose"
else
    MAIN_CMD="$MAIN_CMD 2>&1 | tee logs/production/dry_run_$(date +%Y%m%d_%H%M%S).log"
fi

echo ""
echo "🚀 Running production pipeline..."
echo "Command: $MAIN_CMD"
echo ""

# Run the pipeline
START_TIME=$(date +%s)
eval $MAIN_CMD
EXIT_CODE=$?
END_TIME=$(date +%s)

# Calculate duration
DURATION=$((END_TIME - START_TIME))
MINUTES=$((DURATION / 60))
SECONDS=$((DURATION % 60))

echo ""
echo "⏱️  Pipeline completed in ${MINUTES}m ${SECONDS}s"

# Check exit code
if [ $EXIT_CODE -eq 0 ]; then
    echo "✅ Pipeline completed successfully"
else
    echo "❌ Pipeline failed with exit code $EXIT_CODE"
fi

# Run system health monitor
echo ""
echo "🏥 Running system health monitor..."
if [ "$VERBOSE" = true ]; then
    python scripts/monitor_system_health.py
else
    python scripts/monitor_system_health.py > /dev/null 2>&1
fi

HEALTH_EXIT_CODE=$?

if [ $HEALTH_EXIT_CODE -eq 0 ]; then
    echo "✅ System health check passed"
else
    echo "⚠️  System health check detected issues"
fi

# Check for generated outputs
echo ""
echo "📊 Checking outputs..."

# Check for visual cards
VISUAL_CARDS=$(find assets/generated -name "*.png" -mtime -1 | wc -l)
echo "   Visual cards generated: $VISUAL_CARDS"

# Check log files
LOG_SIZE=$(du -sh logs/production/dry_run_*.log 2>/dev/null | cut -f1 | sum || echo "0")
echo "   Log files created: $(ls logs/production/dry_run_*.log 2>/dev/null | wc -l)"
echo "   Total log size: ${LOG_SIZE}K"

# Check database changes
if [ -f "ludi.db" ]; then
    DB_SIZE=$(du -sh ludi.db | cut -f1)
    echo "   Database size: $DB_SIZE"
fi

# Summary
echo ""
echo "📋 DRY RUN SUMMARY"
echo "==================="
echo "Status: $([ $EXIT_CODE -eq 0 ] && echo "✅ SUCCESS" || echo "❌ FAILED")"
echo "Health: $([ $HEALTH_EXIT_CODE -eq 0 ] && echo "✅ PASSED" || echo "⚠️  ISSUES")"
echo "Duration: ${MINUTES}m ${SECONDS}s"
echo "Visual Cards: $VISUAL_CARDS"

if [ $EXIT_CODE -eq 0 ] && [ $HEALTH_EXIT_CODE -eq 0 ]; then
    echo ""
    echo "🎉 Production pipeline is READY for deployment!"
    echo ""
    echo "Next steps:"
    echo "1. Test the GitHub Actions workflow manually"
    echo "2. Verify Telegram notifications are working"
    echo "3. Monitor first automated run at 11:00 AM EST"
else
    echo ""
    echo "🔧 Issues found. Review the logs above and fix before deployment."
    echo "Logs: logs/production/dry_run_$(date +%Y%m%d)_*.log"
fi

exit $EXIT_CODE