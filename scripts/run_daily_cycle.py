#!/usr/bin/env python3
"""
LUDI INFORMATIO | DAILY SYNC SUPERVISOR
=======================================
Wrapper for sync_tracking_daily.py that enforces a duty cycle.
Prevents API bans on large slates (10+ games).

Cycle: Run 15 mins -> Sleep 2 mins -> Resume
"""

import subprocess
import time
import sys
from datetime import datetime
import signal
import os

RUN_DURATION = 15 * 60  # 15 minutes
PAUSE_DURATION = 2 * 60  # 2 minutes
SCRIPT_CMD = ["python", "scripts/sync_tracking_daily.py"]

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] [SUPERVISOR] {msg}")

def run_attempt(attempt_num):
    log(f"=== STARTING ATTEMPT {attempt_num} ===")
    
    # Launch process
    p = subprocess.Popen(SCRIPT_CMD)
    log(f"Process started (PID {p.pid}). Monitoring for {RUN_DURATION/60} mins...")
    
    start_time = time.time()
    while time.time() - start_time < RUN_DURATION:
        # Check if finished
        ret = p.poll()
        if ret is not None:
            if ret == 0:
                log("Sync completed successfully!")
                return True
            else:
                log(f"Sync failed with exit code {ret}")
                sys.exit(ret)
        time.sleep(5)
    
    # Time up
    log("Time limit reached. Terminating process...")
    p.terminate()
    try:
        p.wait(timeout=10)
    except subprocess.TimeoutExpired:
        p.kill()
        
    log(f"Process stopped. Cooling down for {PAUSE_DURATION/60} mins...")
    time.sleep(PAUSE_DURATION)
    return False

def main():
    attempt = 1
    while True:
        completed = run_attempt(attempt)
        if completed:
            break
        attempt += 1

if __name__ == "__main__":
    main()
