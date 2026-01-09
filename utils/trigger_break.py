import sys
import os

# Ensure project root is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.pm_bot import ProjectManagerBot

def main():
    print("🧪 Testing Break Message Trigger...")
    bot = ProjectManagerBot()
    if bot.send_break_message():
        print("✅ Break message sent successfully!")
    else:
        print("❌ Failed to send break message.")

if __name__ == "__main__":
    main()
