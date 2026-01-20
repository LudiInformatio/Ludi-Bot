#!/usr/bin/env python3
"""
LUDI INFORMATIO | CYCLIC SYNC SUPERVISOR
========================================
Manages data sync workers with a duty cycle to avoid API rate limits.
Cycle: Run for 15 minutes -> Sleep for 2 minutes -> Repeat

Workers:
  - Worker 0: Chunk 0/2 (Delay: 3.0s)
  - Worker 1: Chunk 1/2 (Delay: 6.0s) - Slower due to timeouts
"""

import subprocess
import time
import signal
import sys
import os
from datetime import datetime

# CONFIGURATION
RUN_DURATION = 15 * 60  # 15 minutes (seconds)
PAUSE_DURATION = 2 * 60  # 2 minutes (seconds)
WORKERS = [
    {
        "cmd": ["python3", "scripts/sync_tracking_parallel.py", 
                "--chunk_index", "0", "--total_chunks", "2", 
                "--season", "2025-26", "--start-date", "2025-11-14", "--end-date", "2026-01-14",
                "--delay", "3.0"],
        "log": "logs/worker_0.log"
    },
    {
        "cmd": ["python3", "scripts/sync_tracking_parallel.py", 
                "--chunk_index", "1", "--total_chunks", "2", 
                "--season", "2025-26", "--start-date", "2025-11-14", "--end-date", "2026-01-14",
                "--delay", "6.0"],
        "log": "logs/worker_1.log"
    }
]

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] [SUPERVISOR] {msg}")

def run_cycle(cycle_num):
    log(f"=== STARTING CYCLE {cycle_num} ===")
    procs = []
    
    # Launch workers
    for i, w in enumerate(WORKERS):
        log(f"Launching Worker {i}...")
        with open(w["log"], "a") as f:
            p = subprocess.Popen(w["cmd"], stdout=f, stderr=f)
            procs.append(p)
    
    log(f"Workers running. Sleeping for {RUN_DURATION/60} minutes...")
    
    # Monitor for duration
    start_time = time.time()
    while time.time() - start_time < RUN_DURATION:
        # Check if workers finished early
        if all(p.poll() is not None for p in procs):
            log("All workers finished early! Exiting.")
            sys.exit(0)
        time.sleep(10)

    # Time up - Terminate
    log("Cycle time up. Terminating workers...")
    for p in procs:
        if p.poll() is None:
            p.terminate()
            try:
                p.wait(timeout=5)
            except subprocess.TimeoutExpired:
                p.kill()
    
    log(f"Workers stopped. Cooldown for {PAUSE_DURATION/60} minutes...")
    time.sleep(PAUSE_DURATION)

def main():
    cycle = 1
    while True:
        try:
            run_cycle(cycle)
            cycle += 1
        except KeyboardInterrupt:
            log("Supervisor stopped by user.")
            break

if __name__ == "__main__":
    main()
