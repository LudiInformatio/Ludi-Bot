import time
import schedule
from datetime import datetime
import pytz
from utils.pm_bot import ProjectManagerBot

def job_morning():
    print(f"⏰ Triggering Morning Brief at {datetime.now()}")
    bot = ProjectManagerBot()
    bot.generate_briefing("morning")

def job_nightly():
    print(f"🌙 Triggering Nightly Brief at {datetime.now()}")
    bot = ProjectManagerBot()
    bot.generate_briefing("nightly")

def main():
    print("🤖 Vibe Starters Bot Loop ONLINE")
    print("📅 Schedule: 8:00 AM EST (Morning) | 8:00 PM EST (Nightly)")
    
    # Set timezone to EST
    est = pytz.timezone('US/Eastern')
    
    # Simple loop to check time every minute
    # We use this instead of 'schedule' library sometimes if we want absolute control
    # But let's try strict scheduling first.
    
    # Since we are in a container, effective timezone management is key.
    # We will run this loop and check the 'EST' time conversion manually to be safe.
    
    last_morning_run = None
    last_nightly_run = None
    
    while True:
        now_utc = datetime.now(pytz.utc)
        now_est = now_utc.astimezone(est)
        
        # Morning Brief: 8:00 AM EST
        if now_est.hour == 8 and now_est.minute == 0:
            today_str = now_est.strftime('%Y-%m-%d')
            if last_morning_run != today_str:
                job_morning()
                last_morning_run = today_str
                
        # Nightly Brief: 8:00 PM EST (20:00) OR 10:00 PM EST (22:00) [One-off Override]
        if (now_est.hour == 20 or now_est.hour == 22) and now_est.minute == 0:
            today_str = now_est.strftime('%Y-%m-%d-%H') # distinct by hour to allow both if needed
            if last_nightly_run != today_str:
                job_nightly()
                last_nightly_run = today_str
                
        # Heartbeat check every 30 seconds
        time.sleep(30)

if __name__ == "__main__":
    main()
