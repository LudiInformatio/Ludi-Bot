#!/bin/bash
# LUDI INFORMATIO | SYNC MONITOR
# ================================
# Monitor tracking data sync progress

echo "========================================"
echo "TRACKING SYNC MONITOR"
echo "$(date '+%Y-%m-%d %H:%M:%S')"
echo "========================================"
echo ""

# Check process
if ps aux | grep -E "[s]ync_tracking" | grep -v grep > /dev/null 2>&1; then
    echo "✅ Sync process: RUNNING"
    ps aux | grep -E "[s]ync_tracking" | grep python | awk '{print "   PID:", $2, "| CPU:", $3"%", "| Runtime:", $10}'
else
    echo "❌ Sync process: NOT RUNNING"
fi

echo ""
echo "=== DATABASE RECORDS ==="
python3 -c "
import sqlite3
conn = sqlite3.connect('ludi.db')
c = conn.cursor()

c.execute('SELECT COUNT(*) FROM player_game_tracking')
tracking = c.fetchone()[0]

c.execute('SELECT COUNT(DISTINCT player_name) FROM player_game_tracking')
players = c.fetchone()[0]

c.execute('SELECT COUNT(*) FROM player_speed_stats')
speed = c.fetchone()[0]

print(f'  player_game_tracking: {tracking:,} records')
print(f'  unique players: {players}')
print(f'  player_speed_stats: {speed}')

if players > 0:
    print(f'  avg games/player: {tracking/players:.1f}')

# Latest synced player
c.execute('''
    SELECT player_name, game_date, synced_at 
    FROM player_game_tracking 
    ORDER BY synced_at DESC 
    LIMIT 1
''')
latest = c.fetchone()
if latest:
    print(f'')
    print(f'  Latest: {latest[0]} ({latest[1]})')
    print(f'  Synced at: {latest[2][:19]}')

conn.close()
"

echo ""
echo "=== PROGRESS FILE ==="
if [ -f logs/tracking_sync_progress.json ]; then
    python3 -c "
import json
with open('logs/tracking_sync_progress.json') as f:
    prog = json.load(f)
synced = len(prog.get('players_synced', []))
speed_done = prog.get('speed_synced', False)
print(f'  Players in progress: {synced}')
print(f'  Speed stats synced: {speed_done}')
"
else
    echo "  No progress file found"
fi

echo ""
echo "=== SYNC LOGS ==="
for log in logs/worker_*.log; do
    if [ -f "$log" ]; then
        echo "--- $log ---"
        tail -n 5 "$log"
    fi
done

if [ ! -f logs/worker_0.log ]; then
    if [ -f logs/tracking_sync.log ]; then
        echo "--- logs/tracking_sync.log ---"
        tail -n 5 logs/tracking_sync.log
    fi
fi

echo ""
echo "========================================"
