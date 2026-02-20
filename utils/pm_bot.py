"""
Vibe Starters Assistant — PM Bot (Powered by Ludi)

AGENT INSTRUCTIONS: To send PM bot messages, always use main.py with --mode flag.
This ensures the correct image header + dual Telegram/Slack routing is used.

    Morning brief:   python main.py --mode pm_briefing
    Nightly debrief: python main.py --mode pm_debrief
    Break/pause:     python main.py --mode pm_break

DO NOT call send_message() directly — that sends text only with no image.
DO NOT call utils/pm_bot.py directly — use main.py as the entry point.
"""
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
from utils.slack_notifier import send_slack_message

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

        roadmap = self._parse_roadmap()
        today_str = datetime.datetime.now().strftime('%b %d').upper()

        if mode == "morning":
            # Pre-format tasks to embed directly in prompt
            pending_tasks = roadmap['pending'][:3] if roadmap else []
            task_bullets = "\n".join([f"• {t}" for t in pending_tasks]) or "• No pending tasks found"
            current_phase = roadmap['current_phase'] if roadmap else 'Phase 5 - Production Deployment & Automation'

            header_img = str(self.morning_img)
            prompt = f"""You are the "Vibe Starters Assistant" (Powered by Ludi).

**CRITICAL RULES:**
- DO NOT invent or paraphrase tasks
- DO NOT use generic placeholders
- Output EXACTLY as shown below

**OUTPUT (copy exactly):**

📅 {today_str} | 🟢 ONLINE
──────────────
**THE VISION** 💎
{current_phase}
──────────────
**THE BLUEPRINT** 📐
{task_bullets}
──────────────
**THE INTEL** 🥃
(Add ONE brief insight about NBA analytics or betting markets.)
"""
        else:
            # Pre-format completed tasks and next task
            completed_tasks = roadmap['completed'][:3] if roadmap else []
            wins_bullets = "\n".join([f"• {t}" for t in completed_tasks]) or "• Making progress on current phase"
            next_task = roadmap['pending'][0] if roadmap and roadmap['pending'] else "Continue Phase 5 work"

            header_img = str(self.nightly_img)
            prompt = f"""You are the "Vibe Starters Assistant". End of day protocol.

**CRITICAL RULES:**
- DO NOT invent or paraphrase tasks
- Output EXACTLY as shown below

**OUTPUT (copy exactly):**

📅 {today_str} | 🌙 OFFLINE
──────────────
**THE WINS** 🍾
{wins_bullets}
──────────────
**THE PIVOT** 🥊
Tomorrow's focus: {next_task}
──────────────
**THE VIBE** 🧊
(Add ONE brief motivational closing line.)
"""

        try:
            # New SDK Syntax
            response = self.client.models.generate_content(
                model=self.model_id,
                contents=prompt
            )
            briefing_text = response.text

            # Send to both — Telegram keeps image + formatting, Slack gets text for ops context
            send_slack_message(briefing_text)
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

        roadmap = self._parse_roadmap()
        header_img = str(self.break_img)
        time_str = datetime.datetime.now().strftime('%I:%M %p')

        # Pre-format context - embed actual values
        in_progress = roadmap['in_progress'][0] if roadmap and roadmap['in_progress'] else None
        current_phase = roadmap['current_phase'] if roadmap else "Phase 5 - Production Deployment"
        recent_wins = roadmap['completed'][:2] if roadmap else []
        wins_text = "\n".join([f"• {t}" for t in recent_wins]) if recent_wins else "• Making progress"

        state_text = f"Working on: {in_progress}" if in_progress else f"Current focus: {current_phase}"

        prompt = f"""**OUTPUT (copy exactly):**

🛑 PAUSED | {time_str}
──────────────
**STATE PRESERVED** 📋
{state_text}
──────────────
**QUICK WINS** 🍾
{wins_text}
──────────────
**THE VIBE** 🧊
Go touch grass. Context saved.
"""

        try:
            response = self.client.models.generate_content(
                model=self.model_id,
                contents=prompt
            )
            # Send to both — Telegram keeps image + formatting, Slack gets text for ops context
            send_slack_message(response.text)
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