#!/usr/bin/env python3
"""
Weekly Game Notes Retrospective Script

Queries bets from games that had Claude game notes, feeds wins + losses
to Sonnet for pattern analysis. Outputs model-level insights (not picks).

Usage:
    python scripts/weekly_retrospective.py [--week-start YYYY-MM-DD] [--dry-run] [--verbose]

Runs weekly via weekly_validation.yml (Tuesdays after settlement).
Token budget: ~3,000 tokens/week → ~$0.054/week
"""

import argparse
import sqlite3
import sys
import os
from datetime import datetime, timedelta
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def get_week_bets(conn: sqlite3.Connection, week_start: str, week_end: str) -> list:
    """Query settled bets from games that had game notes generated."""
    c = conn.cursor()
    c.execute("""
        SELECT br.id, br.game_id, br.run_date, br.player_name, br.team,
               br.stat_category, br.bet_side, br.line, br.projection,
               br.true_edge, br.confidence_tier, br.outcome, br.actual_result,
               br.profit_loss, br.clv
        FROM bet_recommendations br
        INNER JOIN game_notes_log gnl
            ON br.game_id = gnl.game_id
           AND br.run_date = gnl.run_date
        WHERE br.run_date BETWEEN ? AND ?
          AND br.outcome IS NOT NULL
          AND br.outcome IN ('WIN', 'LOSS', 'PUSH')
        ORDER BY br.run_date, br.game_id, br.outcome
    """, (week_start, week_end))
    columns = [d[0] for d in c.description]
    return [dict(zip(columns, row)) for row in c.fetchall()]


def get_game_notes(conn: sqlite3.Connection, game_ids: list, run_date: str) -> dict:
    """Fetch game notes for a list of game_ids."""
    if not game_ids:
        return {}
    placeholders = ','.join('?' * len(game_ids))
    c = conn.cursor()
    c.execute(f"""
        SELECT game_id, notes_text FROM game_notes_log
        WHERE game_id IN ({placeholders}) AND run_date = ?
    """, game_ids + [run_date])
    return {row[0]: row[1] for row in c.fetchall()}


def build_retrospective_prompt(bets: list, notes_by_game: dict) -> str:
    """Build the batched prompt for Sonnet analysis."""
    # Group bets by game_id
    by_game = {}
    for bet in bets:
        gid = bet['game_id']
        if gid not in by_game:
            by_game[gid] = []
        by_game[gid].append(bet)

    sections = []
    for gid, game_bets in by_game.items():
        run_date = game_bets[0]['run_date']
        notes = notes_by_game.get(gid, 'No notes available.')

        wins = [b for b in game_bets if b['outcome'] == 'WIN']
        losses = [b for b in game_bets if b['outcome'] == 'LOSS']
        pushes = [b for b in game_bets if b['outcome'] == 'PUSH']

        bet_lines = []
        for b in game_bets:
            direction = f"{b['bet_side']} {b['line']}"
            result_str = f"-> {b['outcome']} (actual: {b['actual_result']}, edge: {b['true_edge']}%)"
            bet_lines.append(f"  - {b['player_name']} {b['stat_category']} {direction} {result_str}")

        section = (
            f"[Game: {gid}] ({run_date})\n"
            f"Context:\n{notes}\n\n"
            f"Bets ({len(wins)}W / {len(losses)}L / {len(pushes)}P):\n"
            + "\n".join(bet_lines)
        )
        sections.append(section)

    games_block = "\n\n---\n\n".join(sections)

    prompt = (
        "You are reviewing NBA player prop bets from this past week.\n"
        "Below are the game contexts we had at bet time and the outcomes.\n"
        "Provide TWO sections:\n\n"
        "## WINNING PATTERNS\n"
        "Identify 2-3 GENERAL MODEL-LEVEL patterns across the wins:\n"
        "- What contextual signals in the game notes aligned with the winning outcomes?\n"
        "- Any repeated game-level factors (matchup, pace, scheme, injury vacuum) that held up?\n"
        "- What does this suggest about where the model is finding real edge?\n\n"
        "## LOSS PATTERNS\n"
        "Identify 2-3 GENERAL MODEL-LEVEL patterns across the losses:\n"
        "- What contextual signals were present that may have been underweighted?\n"
        "- Any repeated game-level factors (blowout risk, pace, scheme)?\n"
        "- What general adjustments does this suggest (not specific players)?\n\n"
        "RULES: Do not recalculate odds. Do not suggest new picks.\n"
        "Only reason from the data below. Cite [Game: X] when referencing.\n\n"
        f"{games_block}"
    )
    return prompt


def main():
    parser = argparse.ArgumentParser(description='Weekly game notes retrospective analysis')
    parser.add_argument('--week-start', type=str, default=None,
                        help='Start date for week (YYYY-MM-DD). Defaults to 7 days ago.')
    parser.add_argument('--dry-run', action='store_true',
                        help='Print prompt without calling Claude')
    parser.add_argument('--verbose', action='store_true',
                        help='Print detailed output')
    args = parser.parse_args()

    # Resolve date range
    if args.week_start:
        week_start = args.week_start
    else:
        week_start = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
    week_end = datetime.now().strftime('%Y-%m-%d')

    print("=" * 60)
    print("WEEKLY GAME NOTES RETROSPECTIVE")
    print(f"Period: {week_start} -> {week_end}")
    print("=" * 60)

    if args.dry_run:
        print("WARNING: DRY RUN -- Claude API will NOT be called")

    db_path = project_root / 'ludi.db'
    if not db_path.exists():
        print("ERROR: Database not found -- skipping retrospective")
        sys.exit(0)

    conn = sqlite3.connect(str(db_path))

    # Check game_notes_log table exists
    c = conn.cursor()
    c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='game_notes_log'")
    if not c.fetchone():
        print("WARNING: game_notes_log table not found -- skipping retrospective")
        conn.close()
        sys.exit(0)

    # Fetch bets
    bets = get_week_bets(conn, week_start, week_end)
    if not bets:
        print(f"No settled bets with game notes found for {week_start} -> {week_end}")
        conn.close()
        sys.exit(0)

    print(f"Found {len(bets)} settled bets across {len(set(b['game_id'] for b in bets))} games with notes")

    # Fetch notes per unique (game_id, run_date) -- use run_date from each game's first bet
    notes_by_game = {}
    by_game_dates = {}
    for bet in bets:
        gid = bet['game_id']
        if gid not in by_game_dates:
            by_game_dates[gid] = bet['run_date']

    for gid, run_date in by_game_dates.items():
        notes_map = get_game_notes(conn, [gid], run_date)
        notes_by_game.update(notes_map)

    conn.close()

    # Build prompt
    prompt = build_retrospective_prompt(bets, notes_by_game)

    if args.verbose or args.dry_run:
        print("\n--- PROMPT PREVIEW ---")
        print(prompt[:1000] + ("..." if len(prompt) > 1000 else ""))
        print("--- END PREVIEW ---\n")

    if args.dry_run:
        print(f"Prompt length: {len(prompt)} chars")
        print("Dry run complete")
        sys.exit(0)

    # Call Claude
    print("Calling Sonnet for retrospective analysis...")
    try:
        from utils.claude_client import get_claude_analysis, SONNET_MODEL
        from utils.claude_prompts import ROSTER_RULES, ANALYSIS_PROTOCOL

        system_prompt = ROSTER_RULES + "\n\n" + ANALYSIS_PROTOCOL
        response = get_claude_analysis(
            prompt=prompt,
            system_prompt=system_prompt,
            model=SONNET_MODEL,
            temperature=0.2,
            max_tokens=1000,
            call_type='weekly',
        )

        if response:
            print("\nRETROSPECTIVE ANALYSIS\n")
            print(response)

            # Write to reports/
            reports_dir = project_root / 'reports'
            reports_dir.mkdir(exist_ok=True)
            report_path = reports_dir / f"retrospective_{week_end}.md"
            with open(report_path, 'w') as f:
                f.write(f"# Weekly Retrospective (Win + Loss Analysis) -- {week_start} to {week_end}\n\n")
                f.write(f"*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}*\n\n")
                f.write(response)
            print(f"\nReport saved: {report_path}")
        else:
            print("WARNING: No response from Claude -- retrospective skipped")

    except ImportError as e:
        print(f"WARNING: Claude client not available ({e}) -- skipping retrospective")
        sys.exit(0)
    except Exception as e:
        print(f"WARNING: Retrospective failed: {e} -- skipping silently")
        sys.exit(0)


if __name__ == "__main__":
    main()
