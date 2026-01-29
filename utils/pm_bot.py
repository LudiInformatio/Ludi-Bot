import os
import datetime
from pathlib import Path
from google import genai

try:
    from config import GEMINI_API_KEY, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID
except ModuleNotFoundError:
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
    TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

from utils.telegram_notifier import send_photo, send_message

class ProjectManagerBot:
    """
    Vibe Starters Assistant - Powered by Ludi

    Reads from ROADMAP.md (single source of truth) to generate:
    - Morning briefs (pending tasks, current phase)
    - Nightly debriefs (completed tasks, wins)
    - Break messages (current task context preserved)
    """
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

    def _parse_roadmap(self):
        """
        Parse ROADMAP.md into structured sections.

        Returns dict with:
            - current_phase: str (from header)
            - pending: list ([ ] items from High/Medium Priority)
            - in_progress: list ([-] items)
            - completed: list ([x] items from Recently Completed)
        """
        base_dir = Path(__file__).resolve().parent.parent
        roadmap_file = base_dir / "ROADMAP.md"

        if not roadmap_file.exists():
            print(f"⚠️ ROADMAP.md not found at {roadmap_file}")
            return None

        with open(roadmap_file, 'r') as f:
            content = f.read()

        pending = []
        in_progress = []
        completed = []
        current_phase = ""

        lines = content.split('\n')
        current_section = None

        for line in lines:
            # Detect current phase from header
            if line.startswith('**Current Phase:**'):
                current_phase = line.replace('**Current Phase:**', '').strip()

            # Detect sections
            if '## High Priority' in line or '## Medium Priority' in line:
                current_section = 'tasks'
            elif '## Recently Completed' in line:
                current_section = 'completed'
            elif '## Low Priority' in line:
                current_section = 'low'  # Skip low priority for briefs
            elif line.startswith('## ') and current_section:
                current_section = None

            # Extract tasks based on section
            if current_section == 'tasks':
                if '- [ ]' in line:
                    task = line.replace('- [ ]', '').strip()
                    # Clean up markdown backticks but keep the content
                    task = task.replace('`', '')
                    if task:
                        pending.append(task)
                elif '- [-]' in line:
                    task = line.replace('- [-]', '').strip()
                    # Remove timestamp emoji if present, clean backticks
                    task = task.split('🏗️')[0].strip() if '🏗️' in task else task
                    task = task.replace('`', '')
                    if task:
                        in_progress.append(task)
            elif current_section == 'completed':
                if '- [x]' in line:
                    task = line.replace('- [x]', '').strip()
                    # Remove timestamp emoji if present
                    task = task.split('✅')[0].strip() if '✅' in task else task
                    if task:
                        completed.append(task)

        return {
            'current_phase': current_phase,
            'pending': pending[:10],      # Limit to top 10
            'in_progress': in_progress[:5],
            'completed': completed[:5]     # Most recent 5 wins
        }

    def _get_context(self, mode="morning"):
        """
        Build context string from ROADMAP.md for Gemini prompts.

        Args:
            mode: "morning" | "nightly" | "break"

        Returns:
            Formatted context string with tasks and phase info.
        """
        try:
            context_str = f"Date: {datetime.datetime.now().strftime('%Y-%m-%d')}\n"

            # Parse ROADMAP.md (single source of truth)
            roadmap = self._parse_roadmap()

            if roadmap:
                # Current Phase (The Vision)
                if roadmap['current_phase']:
                    context_str += f"\n=== CURRENT PHASE (The Vision) ===\n"
                    context_str += f"{roadmap['current_phase']}\n"

                # In Progress Tasks (actively working on)
                if roadmap['in_progress']:
                    context_str += f"\n=== IN PROGRESS ===\n"
                    for task in roadmap['in_progress']:
                        context_str += f"- [-] {task}\n"

                # Pending Tasks (The Blueprint)
                if roadmap['pending']:
                    context_str += f"\n=== PENDING TASKS (The Blueprint) ===\n"
                    for task in roadmap['pending'][:5]:  # Top 5 for briefs
                        context_str += f"- [ ] {task}\n"

                # Completed Tasks (The Wins) - only for nightly and break
                if mode in ["nightly", "break"] and roadmap['completed']:
                    context_str += f"\n=== RECENTLY COMPLETED (The Wins) ===\n"
                    for task in roadmap['completed']:
                        context_str += f"- [x] {task}\n"
            else:
                context_str += "\n⚠️ ROADMAP.md not found - using fallback context.\n"
                context_str += "Update ROADMAP.md to enable task tracking.\n"

            return context_str
        except Exception as e:
            return f"Error retrieving work context: {e}"

    def generate_briefing(self, mode="morning"):
        if not self.client:
            return False

        context = self._get_context(mode=mode)
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
            (Use the CURRENT PHASE from context as the one-sentence goal. Keep it punchy.)
            ──────────────
            **THE BLUEPRINT** 📐
            (List 3 key tasks from PENDING TASKS. Use the exact task names from context.)
            ──────────────
            **THE INTEL** 🥃
            (One smart insight or market nugget related to the project.)
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
            (Highlight 2-3 items from RECENTLY COMPLETED. Use the exact task names from context.)
            ──────────────
            **THE PIVOT** 🥊
            (Suggest the next task from PENDING TASKS as tomorrow's focus.)
            ──────────────
            **THE VIBE** 🧊
            (Closing energy check - keep it brief and motivating.)
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
        """
        Send a "State Preservation" break message with current task context.

        Includes:
        - Current phase
        - In-progress tasks (what you were working on)
        - Recently completed (quick wins summary)
        """
        if not self.client:
            return False

        header_img = str(self.break_img)
        time_str = datetime.datetime.now().strftime('%I:%M %p')
        context = self._get_context(mode="break")

        prompt = f"""
        You are the "Vibe Starters Assistant". Break time protocol.
        **CONTEXT:** {context}

        **OBJECTIVE:** Generate a "State Preservation" card for when the user takes a break.

        **FORMATTING RULES:**
        1. **METADATA:** `🛑 PAUSED | {time_str}`
        2. **SEPARATORS:** `──────────────`
        3. **ICONS:** Pause: 🛑 | Context: 📋 | Vibe: 🧊

        **STRUCTURE:**
        ──────────────
        **STATE PRESERVED** 📋
        (1-2 sentences summarizing what was IN PROGRESS from context. If nothing in progress, mention the current phase.)
        ──────────────
        **QUICK WINS** 🍾
        (If there are RECENTLY COMPLETED items, list 1-2. Otherwise skip this section.)
        ──────────────
        **THE VIBE** 🧊
        (Short break message - "Go touch grass" energy. Keep it to one line.)
        """

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
    import argparse
    parser = argparse.ArgumentParser(description="Vibe Starters Assistant")
    parser.add_argument("--mode", choices=["morning", "nightly", "break"], default="morning",
                        help="Briefing mode: morning, nightly, or break")
    args = parser.parse_args()

    bot = ProjectManagerBot()

    if args.mode == "break":
        bot.send_break_message()
    else:
        bot.generate_briefing(mode=args.mode)