
import os
import datetime
from pathlib import Path
import google.generativeai as genai
from config import GEMINI_API_KEY, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID
from utils.telegram_notifier import send_photo, send_message

class ProjectManagerBot:
    def __init__(self):
        print("📒 Initializing Vibe Starters Assistant (Powered by Ludi)...")
        
        # Assets Paths (Relative for Cloud/GitHub Actions compatibility)
        # We assume the script is running from repo root or utils/
        # Best practice: Resolve paths relative to this file
        base_dir = Path(__file__).resolve().parent.parent
        self.assets_dir = base_dir / "assets"
        
        # FINAL UI: Clean Vector "Vibe V10" Assets
        self.morning_img = self.assets_dir / "header_morning.png"
        self.nightly_img = self.assets_dir / "header_nightly.png"
        self.break_img = self.assets_dir / "header_break.png"

        if not GEMINI_API_KEY:
            print("❌ GEMINI_API_KEY not found! Cannot generate AI briefing.")
            self.model = None
        else:
            try:
                genai.configure(api_key=GEMINI_API_KEY)
                self.model = genai.GenerativeModel('gemini-2.0-flash')
            except Exception as e:
                print(f"⚠️ Error configuring Gemini: {e}")
                self.model = None

    def _read_file_safe(self, filepath):
        try:
            if os.path.exists(filepath):
                with open(filepath, 'r', encoding='utf-8') as f:
                    return f.read()
            return ""
        except Exception as e:
            print(f"⚠️ Could not read {filepath}: {e}")
            return ""

    def _get_context(self, mode="morning"):
        """
        Retrieves WORK context from project files (task.md, status logs).
        Focuses on the User's Development Journey.
        """
        try:
            # Resolve paths relative to repo root
            base_dir = Path(__file__).resolve().parent.parent
            task_file = base_dir / "task.md"
            status_file = base_dir / "UPDATED_STATUS_AND_NEXT_STEPS.md"
            
            context_str = f"Date: {datetime.datetime.now().strftime('%Y-%m-%d')}\n"

            if task_file.exists():
                context_str += "\n=== CURRENT TASKS (The Blueprint) ===\n"
                with open(task_file, 'r') as f:
                    # simplistic read of the first 25 lines to capture active tasks
                    lines = f.readlines()
                    context_str += "".join([line for line in lines[:25] if '- [' in line])
            else:
                context_str += "\n(Note: task.md not found in cloud env)\n"
            
            if status_file.exists():
                context_str += "\n=== PROJECT STATUS (The Vision) ===\n"
                with open(status_file, 'r') as f:
                     # Read the top summary
                     context_str += f.read(1000)

            return context_str

        except Exception as e:
            return f"Error retrieving work context: {e}. Defaulting to generic prod mode."

    def generate_briefing(self, mode="morning"):
        """
        Generates the briefing using Gemini and sends it via Telegram.
        """
        if not self.model:
            return False

        context = self._get_context()
        today_str = datetime.datetime.now().strftime('%b %d').upper()
        
        if mode == "morning":
            header_img = str(self.morning_img)
            prompt = f"""
            You are the "Vibe Starters Assistant" (Powered by Ludi).
            Your persona is the "Smart Creative" - efficient, low-key, professional but casual.
            
            **OBJECTIVE:** 
            Generate a "Morning Brief" for the user.
            
            **CONTEXT:**
            {context}
            
            **FORMATTING RULES (The Vibe Starters Code):**
            1. **METADATA:** `📅 {today_str} | 🟢 ONLINE`
            2. **SEPARATORS:** `──────────────`
            3. **ICONS (IYKYK Edition):**
               - Vision: 💎 (The Diamond/Sharp)
               - Blueprint: 📐 (The Angle)
               - Intel: 🥃 (The Pour/Straight Up)
            
            **STRUCTURE:**
            `──────────────`
            **THE VISION** 💎
            (One single sentence goal.)
            
            `──────────────`
            **THE BLUEPRINT** 📐
            (3 bullet points on key tasks.)
            
            `──────────────`
            **THE INTEL** 🥃
            (One smart insight or market nugget.)
            """
        else: # Nightly
            header_img = str(self.nightly_img)
            prompt = f"""
            You are the "Vibe Starters Assistant". End of day protocol.
            
            **FORMATTING RULES:**
            1. **METADATA:** `📅 {today_str} | 🌙 OFFLINE`
            2. **SEPARATORS:** `──────────────`
            3. **ICONS (IYKYK Edition):**
               - Wins: 🍾 (The Toast)
               - Pivot: 🥊 (The Counter-Punch)
               - Vibe: 🧊 (Stay Frosty)
            
            **STRUCTURE:**
            `──────────────`
            **THE WINS** 🍾
            (Highlight 2-3 wins.)
            
            `──────────────`
            **THE PIVOT** 🥊
            (One adjustment for tomorrow.)
            
            `──────────────`
            **THE VIBE** 🧊
            (Closing energy check.)
            """

        try:
            response = self.model.generate_content(prompt)
            briefing_text = response.text
            
            # Send Header + Briefing
            from utils.telegram_notifier import send_photo, send_message
            
            # 1. Send the visual header
            send_photo(header_img)
            
            # 2. Send the text briefing
            return send_message(briefing_text)
            
        except Exception as e:
            print(f"❌ Error generating briefing: {e}")
            return False

    def send_break_message(self):
        """
        Sends a one-off 'Break/State Preservation' message.
        """
        if not self.model:
            return False

        header_img = str(self.break_img)
        time_str = datetime.datetime.now().strftime('%I:%M %p')
        
        prompt = f"""
        You are the user's "Vibe Starters" assistant.
        Generate a "State Preservation" card.
        
        **FORMAT:**
        `⏸️ PAUSED | {time_str}`
        `──────────────`
        
        **ICONS:**
        - Use 🛑 (Hard Stop) or 🥃 (Relax)
        
        **CONTENT:**
        1. "System Idle. Context Saved."
        2. "Go touch grass." (Or similar vibe).
        """
        
        try:
            print("☕ Generating Break Message...")
            response = self.model.generate_content(prompt)
            break_text = response.text
            
            from utils.telegram_notifier import send_photo, send_message
            send_photo(header_img)
            # Replaced "briefing_text" with "break_text" to match
            return send_message(break_text)
            
        except Exception as e:
            print(f"❌ Error sending break message: {e}")
            return False

if __name__ == "__main__":
    # Test run
    bot = ProjectManagerBot()
    bot.generate_briefing(mode="morning")
