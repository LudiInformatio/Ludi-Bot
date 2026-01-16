import time
import subprocess
import os
import sys
from datetime import datetime, timedelta
import pytz

def schedule_workers():
    # Target: Jan 16, 2026 at 1:00 AM EST
    # Current tz is EST (based on logs)
    target_time = datetime(2026, 1, 16, 1, 0, 0)
    now = datetime.now()
    
    if now > target_time:
        print("Target time has passed. Launching immediately...")
    else:
        wait_seconds = (target_time - now).total_seconds()
        print(f"Current time: {now}")
        print(f"Target time:  {target_time}")
        print(f"Waiting {wait_seconds/3600:.2f} hours ({wait_seconds:.0f} seconds)...")
        print("IMPORTANT: Do not close this terminal or put computer to sleep.")
        sys.stdout.flush()
        time.sleep(wait_seconds)

    print("\nDrafting workers...")
    
    # Worker 1: Chunk 0/2, 20s delay
    cmd1 = [
        "./.venv/bin/python", "scripts/sync_tracking_parallel.py",
        "--chunk_index", "0",
        "--total_chunks", "2",
        "--season", "2025-26",
        "--start-date", "2025-11-14",
        "--end-date", "2026-01-14",
        "--delay", "20.0"
    ]
    
    # Worker 2: Chunk 1/2, 240s delay (4 mins)
    cmd2 = [
        "./.venv/bin/python", "scripts/sync_tracking_parallel.py",
        "--chunk_index", "1",
        "--total_chunks", "2",
        "--season", "2025-26",
        "--start-date", "2025-11-14",
        "--end-date", "2026-01-14",
        "--delay", "240.0" 
    ]

    # Clean previous logs
    with open('logs/worker_0.log', 'w') as f: f.write('')
    with open('logs/worker_1.log', 'w') as f: f.write('')

    # Launch in background
    with open('logs/worker_0.log', 'a') as log0:
        p1 = subprocess.Popen(cmd1, stdout=log0, stderr=log0)
        print(f"Launched Worker 0 (20s delay) - PID {p1.pid}")

    with open('logs/worker_1.log', 'a') as log1:
        p2 = subprocess.Popen(cmd2, stdout=log1, stderr=log1)
        print(f"Launched Worker 1 (4m delay)  - PID {p2.pid}")

    # Save PIDs
    with open('logs/parallel_sync_pids.txt', 'w') as f:
        f.write(f"{p1.pid} {p2.pid}")

if __name__ == "__main__":
    schedule_workers()
