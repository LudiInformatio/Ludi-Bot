import os
import datetime
from pathlib import Path
from google import genai
from config import GEMINI_API_KEY, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID
from utils.telegram_notifier import send_photo, send_message

class ProjectManagerBot:
    def __init__(self):
        print("📒 Initializing Vibe Starters Assistant (Powered by Ludi)...")
        
        # Assets Paths
        base_dir = Path(__file__).resolve().parent.parent
        self.assets_dir = base_dir / "assets"
        
        self.morning_img = self.assets_dir / "header_morning.png"
        self.nightly_img = self.assets_dir / "header_nightly.png"
        self.break_img = self.assets_dir / "header_break.png"

        if not GEMINI_API_KEY:
            print("❌ GEMINI_API_KEY not found! Cannot generate AI briefing.")
            self.client = None
        else:
            try:
                # google-genai SDK
                self.client = genai.Client(api_key=GEMINI_API_KEY)
                self.model_id = 'gemini-2.0-flash' 
            except Exception as e:
                print(f"⚠️ Error configuring Gemini: {e}")
                self.client = None

    def _get_context(self, mode="morning"):
        try:
            base_dir = Path(__file__).resolve().parent.parent
            task_file = base_dir / "task.md"
            status_file = base_dir / "UPDATED_STATUS_AND_NEXT_STEPS.md"
            
            context_str = f"Date: {datetime.datetime.now().strftime('%Y-%m-%d')}\n"

            if task_file.exists():
                context_str += "\n=== CURRENT TASKS (The Blueprint) ===\n"
                with open(task_file, 'r') as f:
                    lines = f.readlines()
                    context_str += "".join([line for line in lines[:25] if '- [' in line])
            
            if status_file.exists():
                context_str += "\n=== PROJECT STATUS (The Vision) ===\n"
                with open(status_file, 'r') as f:
                     context_str += f.read(1000)

            return context_str
        except Exception as e:
            return f"Error retrieving work context: {e}"

    def generate_briefing(self, mode="morning"):
        if not self.client:
            return False

        context = self._get_context()
        today_str = datetime.datetime.now().strftime('%b %d').upper()
        
        if mode == "morning":
            header_img = str(self.morning_img)
            prompt = f"""
            You are the "Vibe Starters Assistant" (Powered by Ludi).
            Your persona is the "Smart Creative" - efficient, low-key, professional but casual.
            
            **OBJECTIVE:** Generate a "Morning Brief" for the user.
            **CONTEXT:** {context}
            
            **FORMATTING RULES:**
            1. **METADATA:** `📅 {today_str} | 🟢 ONLINE`
            2. **SEPARATORS:** `──────────────`
            3. **ICONS:** Vision: 💎 | Blueprint: 📐 | Intel: 🥃
            
            **STRUCTURE:**
            ──────────────
            **THE VISION** 💎
            (One single sentence goal.)
            ──────────────
            **THE BLUEPRINT** 📐
            (3 bullet points on key tasks.)
            ──────────────
            **THE INTEL** 🥃
            (One smart insight or market nugget.)
            """
        else:
            header_img = str(self.nightly_img)
            prompt = f"""
            You are the "Vibe Starters Assistant". End of day protocol.
            **CONTEXT:** {context}
            
            **FORMATTING RULES:**
            1. **METADATA:** `📅 {today_str} | 🌙 OFFLINE`
            2. **SEPARATORS:** `──────────────`
            3. **ICONS:** Wins: 🍾 | Pivot: 🥊 | Vibe: 🧊
            
            **STRUCTURE:**
            ──────────────
            **THE WINS** 🍾
            (Highlight 2-3 wins based on the context.)
            ──────────────
            **THE PIVOT** 🥊
            (One adjustment for tomorrow.)
            ──────────────
            **THE VIBE** 🧊
            (Closing energy check.)
            """

        try:
            # New SDK Syntax
            response = self.client.models.generate_content(
                model=self.model_id,
                contents=prompt
            )
            briefing_text = response.text
            
            return send_photo(header_img, caption=briefing_text, parse_mode=None)
            
        except Exception as e:
            print(f"❌ Error generating briefing: {e}")
            return False

    def send_break_message(self):
        if not self.client:
            return False

        header_img = str(self.break_img)
        time_str = datetime.datetime.now().strftime('%I:%M %p')
        
        prompt = "Generate a 'State Preservation' card. Format: PAUSED | {time_str}. Icons: 🛑 or 🥃. Content: System Idle. Context Saved. Go touch grass."
        
        try:
            response = self.client.models.generate_content(
                model=self.model_id,
                contents=prompt
            )
            return send_photo(header_img, caption=response.text, parse_mode=None)
        except Exception as e:
            print(f"❌ Error sending break message: {e}")
            return False

if __name__ == "__main__":
    bot = ProjectManagerBot()
    bot.generate_briefing(mode="morning")