
import os
import datetime
from pathlib import Path
import google.generativeai as genai
from config import GEMINI_API_KEY, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID
from utils.telegram_notifier import send_photo, send_message

class ProjectManagerBot:
    def __init__(self):
        print("📒 Initializing Vibe Starters Assistant (Powered by Ludi)...")
        
        # Assets Paths
        self.artifacts_dir = Path("/home/mnprice86/.gemini/antigravity/brain/f3c2f543-928e-4fe7-81d5-aa672d939a00")
        self.morning_img = self.artifacts_dir / "final_v5_morning_header_subtle_coffee_flag_1767901673300.png"
        self.nightly_img = self.artifacts_dir / "final_v3_nightly_header_1767901352997.png"

        if not GEMINI_API_KEY:
            print("❌ GEMINI_API_KEY not found! Cannot generate AI briefing.")
            self.model = None
        else:
            genai.configure(api_key=GEMINI_API_KEY)
            self.model = genai.GenerativeModel('gemini-2.0-flash')

    def _read_file_safe(self, filepath):
        try:
            if os.path.exists(filepath):
                with open(filepath, 'r', encoding='utf-8') as f:
                    return f.read()
            return ""
        except Exception as e:
            print(f"⚠️ Could not read {filepath}: {e}")
            return ""

    def _get_context(self):
        """Reads key project files to build context."""
        plan = self._read_file_safe("implementation_plan.md")
        claude_md = self._read_file_safe("CLAUDE.md")
        
        context = f"""
        CURRENT DATE: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S EST')}
        
        === FILE: implementation_plan.md (The Current Plan) ===
        {plan[:10000]}
        
        === FILE: CLAUDE.md (Project Context & Commands) ===
        {claude_md[:5000]}
        """
        return context

    def generate_briefing(self, mode="morning"):
        """
        Generates the briefing using Gemini and sends it via Telegram.
        """
        if not self.model:
            return False

        context = self._get_context()
        
        if mode == "morning":
            header_img = str(self.morning_img)
            prompt = f"""
            You are the "Vibe Starters Assistant" (Powered by Ludi).
            Your persona is the "Smart Creative" - efficient, low-key, professional but casual.
            
            OBJECTIVE: Generate a Morning Briefing content.
            
            CONTEXT:
            {context}
            
            INSTRUCTIONS:
            1. Analyze the 'implementation_plan.md' for NEXT STEPS & 'CLAUDE.md' for STATUS.
            2. FORMAT: Use strict Bullet Journal (BuJo) keys:
               • Task (Action item)
               x Completed (Done deal - rare in morning, but possible)
               > Migrated (Moved from yesterday)
               ! Priority (Critical focus)
               - Note (Context/Observation)
            
            3. STRUCTURE (Strictly follow this layout):
               **The Vision 🎯**
               (One single sentence goal for the day. E.g. "Let's ship the logging module.")
               
               **The Blueprint 🛠️**
               (The To-Do list using the BuJo keys above. Focus on today's tangible actions.)
               
               **The Intel 🧠**
               (Any quick alerts, context, or blockers from the logs/context.)

            4. TONE: "Let's cook." Efficient. Use terms like "The Blueprint".
            5. Keep it concise (< 300 words).
            6. Do NOT use a top-level header line (the image handles that).
            """
        else: # Nightly
            header_img = str(self.nightly_img)
            prompt = f"""
            You are the "Vibe Starters Assistant" (Powered by Ludi).
            Your persona is the "Smart Creative" - reflective, satisfied, ready to rest.
            
            OBJECTIVE: Generate a Nightly Debrief content.
            
            CONTEXT:
            {context}
            
            INSTRUCTIONS:
            1. Analyze what was accomplished today based on the logs/context.
            2. FORMAT: Use strict Bullet Journal (BuJo) keys:
               x Completed (What we shipped)
               > Migrated (What moved to tomorrow)
               - Note (Reflection)
            
            3. STRUCTURE (Strictly follow this layout):
               **The Wins 🏆**
               (Bulleted list of completed items 'x'. Celebrate the 'cooked' items.)
               
               **The Pivot ↪️**
               (Items acting as '>' Migrated. No guilt, just facts.)
               
               **The Vibe 🌙**
               (System health check. Burnout check. One sentence reflection.)

            4. TONE: "Great work today." Relaxed. Use terms like "The Wins", "Cooked".
            5. Keep it concise (< 300 words).
            6. Do NOT use a top-level header line (the image handles that).
            """

        try:
            response = self.model.generate_content(prompt)
            briefing_text = response.text
            
            # Send Image First (if available) then Text
            if os.path.exists(header_img):
                print(f"🚀 Sending Header Image: {header_img}")
                send_photo(header_img, caption=briefing_text[:1024]) # Caption limit 1024
                # If text is longer than caption limit, send rest as message
                if len(briefing_text) > 1024:
                    send_message(briefing_text[1024:])
            else:
                print("⚠️ Header image not found, sending text only.")
                send_message(briefing_text)
                
            return True
        except Exception as e:
            print(f"❌ Failed to generate/send briefing: {e}")
            return False

if __name__ == "__main__":
    # Test run
    bot = ProjectManagerBot()
    bot.generate_briefing(mode="morning")
