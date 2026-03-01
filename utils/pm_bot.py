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

from utils.telegram_notifier import send_photo, send_message, send_solomon_photo
from utils.slack_notifier import send_slack_message

# Domain guardrail — prepended to every Gemini prompt (BERT Pattern 1: label space first).
# Prevents sport-context drift when sprint names contain non-NBA trigger words
# (e.g. "referee" → Mbappé/Real Madrid without this constraint).
_NBA_DOMAIN_GUARDRAIL = (
    "NBA ONLY. You are writing for an NBA basketball analytics platform called Ludi-Bot. "
    "Every reference, athlete, team, and sport must be NBA basketball. "
    "Never mention soccer, football, tennis, baseball, MLS, EPL, La Liga, or any non-NBA "
    "league, athlete, or competition. "
    "If the context mentions referees, officials, or crew assignments, keep it NBA/basketball "
    "only (e.g., Tony Brothers, Scott Foster, Joey Crawford). "
    "If in doubt, stay NBA.\n\n"
)

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
            - current_phase: str (from **Current Phase:** header line)
            - pending: list (- [ ] items from High/Medium Priority sections)
            - in_progress: list (**Active Work:** header line — primary source)
            - completed: list (last 3 sprints from **Completed:** header line)

        NOTE: ROADMAP.md uses a 6-line header block for current state tracking
        (**Current Phase:**, **Active Work:**, **Completed:**) and table format
        for Phase 8 sub-phases. The parser reads the header block first, which
        is always up-to-date, then falls back to - [-] checkboxes if they exist.
        """
        import re
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

        # Track which sections we're in
        in_sprint_section = False       # ### Current Sprint block
        in_tasks_section = False        # ## High/Medium Priority (fallback)
        sprint_pending = []             # - [ ] items from Current Sprint (primary)
        sprint_in_progress = []         # - [-] items from Current Sprint
        all_pending = []                # - [ ] items from all High/Medium (fallback)

        for line in lines:
            # ── PRIMARY: Parse header block ────────────────────────────────────
            # **Active Work:**, **Completed:**, **Current Phase:** are maintained
            # as the single source of truth and always read first.

            if line.startswith('**Current Phase:**'):
                current_phase = line.replace('**Current Phase:**', '').strip()

            elif line.startswith('**Active Work:**'):
                # Split multi-item active work (separated by ' + ') into
                # distinct in_progress items so PM bot shows the first one cleanly.
                active_str = line.replace('**Active Work:**', '').strip()
                if active_str:
                    parts = active_str.split(' + ')
                    for part in parts:
                        clean = part.strip().replace('**', '').strip()
                        if clean:
                            in_progress.append(clean)

            elif line.startswith('**Completed:**'):
                # Last 3 ` + ` segments = most recently completed items
                completed_str = line.replace('**Completed:**', '').strip()
                parts = completed_str.split(' + ')
                for part in parts[-3:]:
                    clean = part.strip().replace('**', '').replace('✅', '').strip()
                    clean = re.sub(r'\s+', ' ', clean).strip()
                    if clean:
                        completed.append(clean)

            # ── SECTION TRACKING ───────────────────────────────────────────────

            if '### Current Sprint' in line:
                in_sprint_section = True
            elif line.startswith('### ') and in_sprint_section:
                in_sprint_section = False  # Moved past Current Sprint

            if '## High Priority' in line or '## Medium Priority' in line:
                in_tasks_section = True
            elif '## Low Priority' in line or '## Archive' in line:
                in_tasks_section = False

            # ── TASK COLLECTION ────────────────────────────────────────────────
            # Primary: ### Current Sprint **Next Actions:** block
            # Fallback: all - [ ] in High/Medium Priority (only if sprint empty)

            if in_sprint_section:
                if '- [ ]' in line:
                    task = line.replace('- [ ]', '').strip().replace('`', '')
                    if task:
                        sprint_pending.append(task)
                elif '- [-]' in line:
                    task = line.replace('- [-]', '').strip().replace('`', '')
                    task = task.split('🏗️')[0].strip() if '🏗️' in task else task
                    if task and task not in in_progress:
                        sprint_in_progress.append(task)
            elif in_tasks_section:
                if '- [ ]' in line:
                    task = line.replace('- [ ]', '').strip().replace('`', '')
                    if task:
                        all_pending.append(task)
                elif '- [-]' in line:
                    task = line.replace('- [-]', '').strip().replace('`', '')
                    if task and task not in in_progress:
                        in_progress.append(task)

        # Sprint items take priority — fall back to general pending only if none found
        pending = sprint_pending if sprint_pending else all_pending

        # Sprint in_progress supplements header-sourced in_progress
        for t in sprint_in_progress:
            if t not in in_progress:
                in_progress.append(t)

        return {
            'current_phase': current_phase,
            'pending': pending[:10],
            'in_progress': in_progress[:5],
            'completed': completed[:5],
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
            active_items = roadmap['in_progress'][:2] if roadmap else []
            active_bullets = "\n".join([f"• {t}" for t in active_items]) or f"• {current_phase}"

            header_img = str(self.morning_img)
            prompt = f"""You are the "Vibe Starters Assistant" (Powered by Ludi).
Generate a morning briefing with the exact format below. Use real tasks from the data provided.

📅 {today_str} | 🟢 ONLINE
──────────────
**THE VISION** 💎
{current_phase}
──────────────
**THE BLUEPRINT** 📐
{task_bullets}
──────────────
**THE INTEL** 🥃
Active sprint: {active_bullets}
(Write ONE sharp sentence grounded in the active sprint above — no generic NBA trivia, reference the actual work in progress.)
"""
        elif mode == "session":
            # Session debrief — end-of-work break, uses recharging break graphic
            completed_tasks = roadmap['completed'][:3] if roadmap else []
            wins_bullets = "\n".join([f"• {t}" for t in completed_tasks]) or "• Making progress on current phase"
            next_task = roadmap['pending'][0] if roadmap and roadmap['pending'] else "Continue Phase 5 work"
            current_phase = roadmap['current_phase'] if roadmap else 'Phase 8'
            active_items = roadmap['in_progress'][:1] if roadmap else []
            todays_focus = active_items[0] if active_items else current_phase

            header_img = str(self.break_img)
            prompt = f"""You are the "Vibe Starters Assistant". End of session — recharging break.
Generate a session debrief with the exact format below. Use real tasks from the data provided.

📅 {today_str} | ⚡ RECHARGING
──────────────
**THE WINS** 🍾
{wins_bullets}
──────────────
**THE PIVOT** 🥊
Today's sprint: {todays_focus}
Tomorrow: {next_task}
──────────────
**THE VIBE** 🧊
(ONE closing line — reflect on the sprint above specifically, not generic motivation.)
"""
        else:
            # Automated nightly debrief — P&L / settlement summary, uses nightly graphic
            completed_tasks = roadmap['completed'][:3] if roadmap else []
            wins_bullets = "\n".join([f"• {t}" for t in completed_tasks]) or "• Making progress on current phase"
            next_task = roadmap['pending'][0] if roadmap and roadmap['pending'] else "Continue Phase 5 work"
            current_phase = roadmap['current_phase'] if roadmap else 'Phase 8'
            active_items = roadmap['in_progress'][:1] if roadmap else []
            todays_focus = active_items[0] if active_items else current_phase

            header_img = str(self.nightly_img)
            prompt = f"""You are the "Vibe Starters Assistant". End of day protocol.
Generate a nightly debrief with the exact format below. Use real tasks from the data provided.

📅 {today_str} | 🌙 OFFLINE
──────────────
**THE WINS** 🍾
{wins_bullets}
──────────────
**THE PIVOT** 🥊
Today's sprint: {todays_focus}
Tomorrow: {next_task}
──────────────
**THE VIBE** 🧊
(ONE closing line — reflect on the sprint above specifically, not generic motivation.)
"""

        try:
            # New SDK Syntax — domain guardrail prepended (BERT Pattern 1: label space first)
            response = self.client.models.generate_content(
                model=self.model_id,
                contents=_NBA_DOMAIN_GUARDRAIL + prompt
            )
            briefing_text = response.text

            # Send to both — Solomon Bot 2 for Telegram (PM/ops channel), Slack for ops context
            send_slack_message(briefing_text)
            return send_solomon_photo(header_img, caption=briefing_text, parse_mode=None)

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

        prompt = f"""You are the "Vibe Starters Assistant". Break/pause protocol.

OUTPUT ONLY the formatted card below — no prose, no intro, no explanation.
The card is pre-filled. Your ONLY job is to replace [VIBE] with ONE sharp sentence
that references the specific sprint work in STATE PRESERVED above. No generic motivation.
No "go touch grass". Name the actual feature or file being built.

🛑 PAUSED | {time_str}
──────────────
**STATE PRESERVED** 📋
{state_text}
──────────────
**QUICK WINS** 🍾
{wins_text}
──────────────
**THE VIBE** 🧊
[VIBE]
"""

        try:
            # Domain guardrail prepended (BERT Pattern 1: label space first)
            response = self.client.models.generate_content(
                model=self.model_id,
                contents=_NBA_DOMAIN_GUARDRAIL + prompt
            )
            # Send to both — Solomon Bot 2 for Telegram (PM/ops channel), Slack for ops context
            send_slack_message(response.text)
            return send_solomon_photo(header_img, caption=response.text, parse_mode=None)
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