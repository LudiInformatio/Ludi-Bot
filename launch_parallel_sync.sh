#!/bin/bash
# launch_parallel_sync.sh - Parallel tracking data sync (NBA API)
# Launches 4 workers, each processing different player chunks

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PYTHON="${SCRIPT_DIR}/.venv/bin/python"
SYNC_SCRIPT="${SCRIPT_DIR}/scripts/sync_tracking_parallel.py"
LOG_DIR="${SCRIPT_DIR}/logs"
PID_FILE="${LOG_DIR}/parallel_sync_pids.txt"

# Configuration (reduced to 2 workers to avoid NBA.com rate limits)
TOTAL_CHUNKS=2
SEASON="2025-26"
START_DATE="2025-11-14"
END_DATE="2026-01-14"

mkdir -p "$LOG_DIR"
> "$PID_FILE"

echo "=========================================="
echo "  Ludi Bot - Parallel Tracking Sync"
echo "  (NBA API - Shot Quality + Difficulty)"
echo "=========================================="
echo "Season: $SEASON"
echo "Date Range: $START_DATE to $END_DATE"
echo "Workers: $TOTAL_CHUNKS"
echo ""

for i in $(seq 0 $((TOTAL_CHUNKS - 1))); do
    LOG_FILE="${LOG_DIR}/worker_${i}.log"
    
    echo "Starting Worker $i -> $LOG_FILE"
    
    nohup "$PYTHON" "$SYNC_SCRIPT" \
        --chunk_index "$i" \
        --total_chunks "$TOTAL_CHUNKS" \
        --season "$SEASON" \
        --start-date "$START_DATE" \
        --end-date "$END_DATE" \
        > "$LOG_FILE" 2>&1 &
    
    PID=$!
    echo "$PID" >> "$PID_FILE"
    echo "  PID: $PID"
done

echo ""
echo "All workers launched!"
echo "Monitor: tail -f logs/worker_*.log"
