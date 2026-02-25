#!/usr/bin/env python3
"""
Archetype Classification Corrector

Data-driven rules that fix archetype mismatches identified by player_type_profiles.
Uses synergy data + position to correct systematic mislabeling.

Philosophy:
  - Archetypes = player IDENTITY (what role they fill on offense)
  - Synergy types = player ACTIONS (what they actually do with the ball)
  - When synergy data strongly contradicts archetype, the data wins
  - When archetype captures role correctly but synergy type differs, keep archetype
    (e.g., Draymond is CONNECTOR even if SPOT_UP is his highest-freq synergy action)

Run modes:
  --dry-run    Show proposed changes without writing to DB (default safe mode)
  --apply      Write corrections to players table
  --rebuild    Also rebuild player_type_profiles after applying
"""

import argparse
import sqlite3
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

DB_PATH = "ludi.db"
SEASON = "2025-26"


# ── Archetype correction rules ────────────────────────────────────────────────
# Each rule: (label, condition_fn, reason)
# condition_fn receives a row dict with all player_type_profiles columns.
# Returns new archetype string or None if rule doesn't apply.

def _apply_rules(row: dict) -> tuple[str | None, str]:
    """
    Apply correction rules to a player row. Returns (new_archetype, reason) or (None, '').
    Rules are ordered — first matching rule wins.
    """
    arch = row['archetype'] or ''
    pos = row['position'] or 'UNK'
    s1 = row['synergy_type_1'] or ''
    s2 = row['synergy_type_2'] or ''
    s3 = row['synergy_type_3'] or ''
    t1 = row['synergy_tag_1'] or ''   # internal translated name
    t2 = row['synergy_tag_2'] or ''
    f1 = row['synergy_freq_1'] or 0.0
    f2 = row['synergy_freq_2'] or 0.0
    f3 = row['synergy_freq_3'] or 0.0
    name = row['player_name']

    # ── Rule 1: Big-man facilitators misclassified as JUMBO_FACILITATOR ──────
    # JUMBO_FACILITATOR = plays like a PG (initiates offense from perimeter)
    # HUB_BIG = facilitates from post/elbow (Jokić, Sengun, Embiid style)
    # C/F-C with JUMBO_FACILITATOR whose synergy is NOT P&R_HANDLER-primary → HUB_BIG
    if (arch == 'JUMBO_FACILITATOR'
            and pos in ('C', 'F-C')
            and t1 != 'P&R_HANDLER'
            and f1 >= 15.0):
        return 'HUB_BIG', f"C/F-C with {s1} ({f1:.0f}%) primary — hub big, not PG-type"

    # ── Rule 2: WARRIOR_BIG spot-up shooters → STRETCH_BIG ──────────────────
    # WARRIOR_BIG = roll man, finisher, physical big
    # STRETCH_BIG = spacing big who primarily catches and shoots
    if (arch == 'WARRIOR_BIG'
            and s1 == 'SPOT_UP'
            and f1 >= 28.0):
        return 'STRETCH_BIG', f"SPOT_UP {f1:.0f}% primary — spacing big, not roll man"

    # ── Rule 3: CONNECTOR with very high SPOT_UP → SNIPER_ELITE ─────────────
    # CONNECTOR = ball-movement wing who passes and plays off-ball
    # If their primary action is catch-and-shoot (40%+ SPOT_UP), they're a sniper.
    # SAFEGUARD: Require f2 > 0 (player has 2+ synergy types with sufficient data).
    # Players like Draymond Green who have only 1 synergy type (SPOT_UP 40%) are
    # role players whose CONNECTOR identity is correct — the SPOT_UP percentage is
    # inflated because it's their ONLY action with the ball, not their true identity.
    if (arch == 'CONNECTOR'
            and s1 == 'SPOT_UP'
            and f1 >= 35.0
            and f2 > 0.0   # Must have a meaningful secondary type
            and t2 not in ('P&R_HANDLER', 'ISO_SCORER', 'TRANSITION')):
        return 'SNIPER_ELITE', f"SPOT_UP dominant ({f1:.0f}%) + {s2} secondary — sniper, not connector"

    # ── Rule 4: TWO_LEVEL_SCORER dominated by SPOT_UP → SNIPER_ELITE ────────
    # TWO_LEVEL_SCORER = creates at multiple levels (rim + midrange + 3)
    # If SPOT_UP dominates and no significant P&R or drive game, → SNIPER_ELITE
    # SAFEGUARD: Require f2 > 0 to ensure sufficient synergy data coverage.
    if (arch == 'TWO_LEVEL_SCORER'
            and s1 == 'SPOT_UP'
            and f1 >= 28.0
            and f2 > 0.0   # Require secondary type to confirm spot-up dominance
            and t2 not in ('P&R_HANDLER', 'ISO_SCORER')):
        return 'SNIPER_ELITE', f"SPOT_UP {f1:.0f}% primary + {s2} {f2:.0f}% — spot-up sniper"

    # ── Rule 5: SNIPER_ELITE with P&R_HANDLER primary → TWO_LEVEL_SCORER ────
    # SNIPER_ELITE = primarily moves without ball, catch-and-shoot
    # If P&R handling is their #1 action, they're a two-level scorer or creator
    if (arch == 'SNIPER_ELITE'
            and t1 == 'P&R_HANDLER'
            and f1 >= 25.0):
        return 'TWO_LEVEL_SCORER', f"PR_BALL_HANDLER {f1:.0f}% primary — creates off P&R, not pure sniper"

    # ── Rule 6: SLASHING_CREATOR without TRANSITION/drive primary → ISO_ASSASSIN
    # SLASHING_CREATOR = attacks off the dribble, transition, drives
    # If their top synergy is SPOT_UP or ISO (not TRANSITION), they're isolation-focused
    if (arch == 'SLASHING_CREATOR'
            and s1 in ('SPOT_UP', 'ISO')
            and t2 in ('ISO_SCORER', 'SPOT_UP', 'P&R_HANDLER')
            and f1 >= 15.0):
        return 'ISO_ASSASSIN', f"{s1} {f1:.0f}% + {s2} {f2:.0f}% — mid-range/ISO artist, not slasher"

    # ── Rule 7: CONNECTOR with TRANSITION primary → keep (it's correct) ──────
    # Connectors who run in transition are doing exactly what connectors do
    # No rule needed — just don't change them

    return None, ''


# ── Synergy dominance tier ────────────────────────────────────────────────────

def _synergy_dominance(f1: float, f2: float, f3: float) -> str:
    """
    Classify how dominated a player's game is by a single synergy type.
    This powers the 'sub-type' display in game notes.

    Examples:
      DOMINANT  → Josh Hart (SPOT_UP 45%) — one type overwhelms
      PRIMARY   → LeBron (TRANSITION 24%) — clear primary with meaningful secondary
      MIXED     → DeRozan (SPOT_UP 20%, ISO 19%) — two nearly equal types
      BALANCED  → Generalist (no type >= 18%)
    """
    if f1 >= 35.0:
        return 'DOMINANT'
    if f1 >= 22.0 and (f2 < 15.0 or f1 - f2 >= 8.0):
        return 'PRIMARY'
    if f1 >= 16.0 and f2 >= 14.0:
        return 'MIXED'
    return 'BALANCED'


def _effective_label(row: dict, corrected_arch: str | None) -> str:
    """
    Build a human-readable effective label for game notes.
    Uses corrected archetype if available, otherwise current.

    Examples:
      Jokić     → "HUB_BIG · POST_UP (23%)"
      Josh Hart → "SNIPER_ELITE · SPOT_UP dominant (45%)"
      LeBron    → "HELIOCENTRIC_MAESTRO · TRANSITION (24%) + P&R (12%)"
      DeRozan   → "ISO_ASSASSIN · SPOT_UP/ISO mixed"
    """
    arch = corrected_arch or row['archetype'] or 'GENERALIST'
    s1 = row['synergy_type_1']
    f1 = row['synergy_freq_1'] or 0
    s2 = row['synergy_type_2']
    f2 = row['synergy_freq_2'] or 0
    dom = _synergy_dominance(f1, f2, row['synergy_freq_3'] or 0)

    if not s1:
        return arch

    if dom == 'DOMINANT':
        return f"{arch} · {s1} dominant ({f1:.0f}%)"
    if dom == 'PRIMARY' and s2:
        return f"{arch} · {s1} ({f1:.0f}%) + {s2} ({f2:.0f}%)"
    if dom == 'MIXED' and s2:
        return f"{arch} · {s1}/{s2} mixed"
    return f"{arch} · {s1} ({f1:.0f}%)"


# ── Main ──────────────────────────────────────────────────────────────────────

def run(apply: bool = False, rebuild: bool = False) -> None:
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # Add synergy_dominance + effective_label columns to player_type_profiles if missing
    for col, coltype in [('synergy_dominance', 'TEXT'), ('effective_label', 'TEXT')]:
        try:
            cur.execute(f"ALTER TABLE player_type_profiles ADD COLUMN {col} {coltype}")
            conn.commit()
        except Exception:
            pass  # Already exists

    # Load all players from player_type_profiles
    cur.execute(
        f"""
        SELECT p.player_name, p.team, p.position, p.archetype, p.defensive_tag,
               p.synergy_type_1, p.synergy_freq_1, p.synergy_ppp_1,
               p.synergy_type_2, p.synergy_freq_2, p.synergy_ppp_2,
               p.synergy_type_3, p.synergy_freq_3, p.synergy_ppp_3,
               p.synergy_tag_1, p.synergy_tag_2, p.synergy_tag_3,
               p.position_synergy_match, p.archetype_in_top3
        FROM player_type_profiles p
        WHERE p.season = '{SEASON}'
        ORDER BY p.synergy_freq_1 DESC
        """
    )
    players = [dict(r) for r in cur.fetchall()]

    corrections = []
    dominance_updates = []

    for row in players:
        new_arch, reason = _apply_rules(row)
        f1 = row['synergy_freq_1'] or 0
        f2 = row['synergy_freq_2'] or 0
        f3 = row['synergy_freq_3'] or 0
        dom = _synergy_dominance(f1, f2, f3)
        eff = _effective_label(row, new_arch)

        dominance_updates.append((dom, eff, row['player_name']))

        if new_arch and new_arch != row['archetype']:
            corrections.append({
                'player_name': row['player_name'],
                'team': row['team'],
                'position': row['position'],
                'old_arch': row['archetype'],
                'new_arch': new_arch,
                'reason': reason,
                'synergy': f"{row['synergy_type_1']} {f1:.0f}% / {row['synergy_type_2'] or '-'} {f2:.0f}%",
            })

    # Print correction proposals
    print(f"\n{'='*70}")
    print(f"ARCHETYPE CORRECTIONS — {len(corrections)} players")
    print(f"{'='*70}")
    if corrections:
        print(f"{'Player':<28} {'Team':<5} {'Pos':<5} {'Old':<22} {'New':<22} {'Synergy #1 / #2'}")
        print('-'*120)
        for c in corrections:
            print(f"{c['player_name']:<28} {(c['team'] or '?'):<5} {(c['position'] or '?'):<5} "
                  f"{c['old_arch']:<22} {c['new_arch']:<22} {c['synergy']}")
            print(f"  └─ {c['reason']}")
    else:
        print("  No corrections needed based on current rules.")

    # Print dominance summary
    from collections import Counter
    dom_counts = Counter(d[0] for d in dominance_updates if d[0])
    print(f"\n{'='*70}")
    print(f"SYNERGY DOMINANCE DISTRIBUTION")
    print(f"{'='*70}")
    for tier, cnt in sorted(dom_counts.items()):
        print(f"  {tier:<12}: {cnt} players")

    # Sample notable labels
    notable = [(d[0], d[1], d[2]) for d in dominance_updates if d[0] == 'DOMINANT'][:10]
    if notable:
        print(f"\n  DOMINANT players (sample):")
        for dom, eff, name in sorted(notable, key=lambda x: -0.0)[:10]:
            print(f"    {name:<28} → {eff}")

    if not apply:
        print(f"\n[DRY RUN] No changes written. Re-run with --apply to commit.")
        conn.close()
        return

    # Apply corrections to players table
    arch_updated = 0
    for c in corrections:
        cur.execute(
            """
            UPDATE players SET archetype = ?, updated_at = datetime('now')
            WHERE name = ?
            """,
            (c['new_arch'], c['player_name'])
        )
        if cur.rowcount:
            arch_updated += 1

    # Update player_type_profiles with corrected archetype + dominance + effective_label
    for c in corrections:
        cur.execute(
            """
            UPDATE player_type_profiles SET archetype = ?
            WHERE player_name = ? AND season = ?
            """,
            (c['new_arch'], c['player_name'], SEASON)
        )

    # Update dominance + effective_label for all players
    for dom, eff, pname in dominance_updates:
        cur.execute(
            """
            UPDATE player_type_profiles
            SET synergy_dominance = ?, effective_label = ?
            WHERE player_name = ? AND season = ?
            """,
            (dom, eff, pname, SEASON)
        )

    conn.commit()
    print(f"\n[APPLIED] {arch_updated} archetype corrections written to players table.")
    print(f"[APPLIED] {len(dominance_updates)} synergy_dominance + effective_label rows updated.")

    if rebuild:
        print("\n[REBUILD] Re-running build_classification_profiles.py...")
        import subprocess
        result = subprocess.run(
            ['python', 'scripts/build_classification_profiles.py'],
            capture_output=True, text=True
        )
        print(result.stdout)
        if result.returncode != 0:
            print(f"  WARNING: {result.stderr}")

    conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Correct archetype classifications based on synergy data")
    parser.add_argument('--apply', action='store_true', help='Write corrections to DB (default: dry-run)')
    parser.add_argument('--rebuild', action='store_true', help='Rebuild player_type_profiles after applying')
    args = parser.parse_args()

    run(apply=args.apply, rebuild=args.rebuild)
