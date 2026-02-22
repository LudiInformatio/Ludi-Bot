#!/usr/bin/env python3
"""
Phase 2B — Build WOWY Observed (Starter-Filtered Beneficiary Performance)

Computes *empirical* beneficiary stats on nights a star player did NOT start.
This enhances the existing beneficiary_minutes table (789 pairs from build_rotation_profiles.py)
with direct observation — "when LeBron didn't start, Austin Reaves averaged X pts" rather
than estimated correlation.

Output table: player_wowy_observed
  - canonical_id        = beneficiary player
  - star_canonical_id   = star who sat out
  - obs_pts/reb/ast/min = beneficiary averages on star-OUT nights
  - base_pts/min        = beneficiary averages on star-PLAYING nights
  - pts_delta/min_delta = boost/reduction from star absence
  - obs_games           = sample size (quality gate: >= 3 for LOW, >= 5 for MEDIUM, >= 10 for HIGH)

Reads from:
  beneficiary_minutes  — existing (star_id, beneficiary_id, minutes_gained, team_abbreviation)
  player_game_logs     — started field (0/1, from SportsDataIO) + game stats
  player_canonical_ids — for star/beneficiary canonical_id lookup

Requires: started field populated in player_game_logs (Sprint A SportsDataIO enrichment)
          Minimum useful run: after 2024-25 backfill + SportsDataIO enrichment completes.

Wire into data_sync.yml after "Build Rotation Profiles (Phase 8.9)"

Usage:
  python scripts/build_wowy_observed.py          # default: 120-day window
  python scripts/build_wowy_observed.py --days 60
  python scripts/build_wowy_observed.py --min-minutes-gained 3.0
  python scripts/build_wowy_observed.py --dry-run
"""

import argparse
import sqlite3
import os
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'ludi.db')

CONFIDENCE_THRESHOLDS = {
    'HIGH':   10,
    'MEDIUM': 5,
    'LOW':    3,
}

# ── Role families (off/def separated) ───────────────────────────────────────
# Offensive families: scoring vacuums flow within these groups when a star sits out.
OFFENSIVE_FAMILIES = {
    'primary_creator':  {'HELIOCENTRIC_MAESTRO', 'SLASHING_CREATOR', 'ISO_ASSASSIN',
                         'JUMBO_FACILITATOR'},
    'secondary_scorer': {'TWO_LEVEL_SCORER', 'SNIPER_ELITE', 'CONNECTOR',
                         'FACILITATOR', 'GENERALIST'},
    'rim_finisher':     {'ROLL_MAN', 'WARRIOR_BIG', 'ENERGY_BIG', 'CUTTER_SPECIALIST'},
    'stretch_role':     {'STRETCH_BIG', 'HUB_BIG'},
}

# Defensive families — kept for documentation / future analytics reference.
# NOTE (Feb 22 2026): These archetypes no longer appear in players.archetype.
# They live in players.defensive_tag under the hybrid off/def system.
# _role_match_score no longer needs a 0.0 sentinel for these — archetype is always offensive.
DEFENSIVE_FAMILIES = {
    'perimeter_defender': {'PERIMETER_HAWK', 'SWITCHABLE_ANCHOR', 'HUSTLE_DISRUPTOR'},
    'paint_defender':     {'RIM_GUARDIAN'},
}

ALL_FAMILIES = {**OFFENSIVE_FAMILIES, **DEFENSIVE_FAMILIES}
DEFENSIVE_ARCHETYPES = set().union(*DEFENSIVE_FAMILIES.values())
OFFENSIVE_ARCHETYPES = set().union(*OFFENSIVE_FAMILIES.values())

# Adjacent offensive family pairs — partial usage absorption across role groups.
_ADJACENT_PAIRS = {
    ('primary_creator',  'secondary_scorer'),  # creator out → secondary scorer absorbs
    ('secondary_scorer', 'rim_finisher'),       # scorer out → finisher gets putbacks
    ('rim_finisher',     'primary_creator'),    # big out → creator handles more touches
    ('stretch_role',     'secondary_scorer'),   # stretch-4 out → wing shooters benefit
}

# ── Synergy sub-type adjacency (Axis 2) ─────────────────────────────────────
# When star and beneficiary share the same dominant playtype, the beneficiary
# absorbs the *specific* role, not just the general position.
# Scores represent usage-absorption similarity (0.65 = loosely adjacent, 0.85 = near-identical).
PLAYTYPE_ADJACENCY = {
    # Ball-in-hand creation cluster
    ('ISO',            'PR_BALL_HANDLER'): 0.85,
    ('PR_BALL_HANDLER', 'ISO'):            0.85,
    ('ISO',            'HANDOFF'):         0.70,
    # Catch-and-shoot cluster
    ('SPOT_UP',        'OFF_SCREEN'):      0.85,
    ('OFF_SCREEN',     'SPOT_UP'):         0.85,
    # Rim-run cluster
    ('PUTBACK',        'TRANSITION'):      0.75,
    ('TRANSITION',     'PUTBACK'):         0.75,
    ('PR_ROLL_MAN',    'PUTBACK'):         0.80,
    ('PUTBACK',        'PR_ROLL_MAN'):     0.80,
    # Interior big cluster
    ('POST_UP',        'PR_ROLL_MAN'):     0.70,
    ('PR_ROLL_MAN',    'POST_UP'):         0.70,
    # Off-ball movement cluster
    ('CUT',            'TRANSITION'):      0.70,
    ('SPOT_UP',        'CUT'):             0.65,
}

# Position normalization: collapses PG/SG/G-F → G, PF/SF/F-C → F, keeps C
def _norm_pos(p: str | None) -> str | None:
    if not p or p in ('UNK', ''):
        return None
    if p in ('PG', 'SG', 'G-F', 'G'):
        return 'G'
    if p in ('PF', 'SF', 'F-C', 'F'):
        return 'F'
    if p == 'C':
        return 'C'
    return None


def _role_match_score(
    arch_star: str | None, arch_ben: str | None,
    pos_star: str | None = None, pos_ben: str | None = None,
    playtype_star: str | None = None, playtype_ben: str | None = None,
) -> float:
    """
    3-axis role similarity score:
      Axis 1 — Primary archetype family (0.15 / 0.40 / 0.70 / 1.0)
      Axis 2 — Dominant synergy playtype sub-type bonus (+0.00 to +0.20)
      Axis 3 — Position match bonus (+0.10)

    Returns 0.0 (defensive sentinel) or 0.10–1.0 (offensive similarity).
    0.0 sentinel: star is a defensive specialist → Module X skips Tier 0A.
    """
    # ── Axis 1: Primary archetype family ─────────────────────────────────────
    # Hybrid system (Feb 22 2026): arch_star is always an offensive archetype.
    # DEFENSIVE_ARCHETYPES guard kept as safety net — should never fire in production.
    if arch_star in DEFENSIVE_ARCHETYPES:
        return 0.0  # Safety net only — archetype column no longer holds defensive labels

    if not arch_star or not arch_ben:
        archetype_score = 0.4   # Unknown → neutral assumption
    elif arch_star == arch_ben:
        archetype_score = 1.0
    else:
        star_fam = next((f for f, s in ALL_FAMILIES.items() if arch_star in s), None)
        ben_fam  = next((f for f, s in ALL_FAMILIES.items() if arch_ben  in s), None)
        if star_fam and star_fam == ben_fam:
            archetype_score = 0.70
        elif star_fam and ben_fam:
            pair = (star_fam, ben_fam)
            if pair in _ADJACENT_PAIRS or (pair[1], pair[0]) in _ADJACENT_PAIRS:
                archetype_score = 0.40
            else:
                archetype_score = 0.15
        else:
            archetype_score = 0.40  # Unknown family → neutral

    # ── Axis 2: Synergy sub-type bonus (capped at +0.20) ─────────────────────
    playtype_bonus = 0.0
    if playtype_star and playtype_ben:
        if playtype_star == playtype_ben:
            playtype_bonus = 0.20   # Exact sub-type match → strongest signal
        else:
            raw = PLAYTYPE_ADJACENCY.get((playtype_star, playtype_ben), 0.0)
            playtype_bonus = round(raw * 0.15, 2)  # Scale 0.65–0.85 → 0.10–0.13

    # ── Axis 3: Position match bonus (+0.10) ─────────────────────────────────
    position_bonus = 0.0
    ns = _norm_pos(pos_star)
    nb = _norm_pos(pos_ben)
    if ns and nb and ns == nb:
        position_bonus = 0.10

    return round(min(archetype_score + playtype_bonus + position_bonus, 1.0), 2)


def _get_archetype(conn, player_id: str) -> str | None:
    """Look up a player's archetype from the players table."""
    row = conn.execute(
        "SELECT archetype FROM players WHERE player_id = ?", (str(player_id),)
    ).fetchone()
    return row['archetype'] if row else None


def _get_position(conn, player_id: str) -> str | None:
    """Look up a player's position (G/F/C/UNK) from players table."""
    row = conn.execute(
        "SELECT position FROM players WHERE player_id = ?", (str(player_id),)
    ).fetchone()
    return row['position'] if row else None


def _get_dominant_playtype(conn, player_id: str) -> str | None:
    """
    Returns the player's highest-frequency synergy playtype (sub-classification).
    Skips MISC (too generic). Uses player_name join since synergy table is name-keyed.
    """
    name_row = conn.execute(
        "SELECT name FROM players WHERE player_id = ?", (str(player_id),)
    ).fetchone()
    if not name_row:
        return None
    row = conn.execute("""
        SELECT playtype FROM player_synergy_playtypes
        WHERE player_name = ? AND playtype != 'MISC'
          AND season = '2025-26'
        ORDER BY freq_pct DESC LIMIT 1
    """, (name_row['name'],)).fetchone()
    return row['playtype'] if row else None


def _get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def _get_canonical_id(conn, player_id: str) -> str:
    """Return canonical_id for a player.
    beneficiary_minutes IDs are already canonical (same as player_canonical_ids.canonical_id),
    so we just verify and return. Falls back to the input ID if not found."""
    row = conn.execute(
        "SELECT canonical_id FROM player_canonical_ids WHERE canonical_id = ?",
        (str(player_id),)
    ).fetchone()
    return row['canonical_id'] if row else str(player_id)


def _get_pairs(conn, min_minutes_gained: float):
    """Fetch (star_id, beneficiary_id, team, minutes_gained) from beneficiary_minutes.
    Column names: out_player_id, beneficiary_player_id, minutes_delta."""
    rows = conn.execute("""
        SELECT DISTINCT bm.out_player_id          AS star_id,
                        bm.beneficiary_player_id  AS beneficiary_id,
                        bm.team_abbreviation,
                        bm.minutes_delta          AS minutes_gained
        FROM beneficiary_minutes bm
        WHERE bm.minutes_delta >= ?
          AND bm.out_player_id IS NOT NULL
          AND bm.beneficiary_player_id IS NOT NULL
    """, (min_minutes_gained,)).fetchall()
    return rows


def _compute_wowy(conn, star_id: str, ben_id: str, team: str, since_date: str) -> dict | None:
    """
    Compute beneficiary stats on star-OUT vs star-PLAYING nights.
    'OUT' = star has no row in player_game_logs on a team game date,
            OR star was present but started=0.
    """

    # All team game dates in the window where at least one player logged time
    team_dates_rows = conn.execute("""
        SELECT DISTINCT game_date
        FROM player_game_logs
        WHERE team_abbreviation = ?
          AND game_date >= ?
          AND minutes > 0
        ORDER BY game_date
    """, (team, since_date)).fetchall()
    team_dates = [r['game_date'] for r in team_dates_rows]

    if not team_dates:
        return None

    # Dates star was NOT starting (either absent or started=0)
    # A star "started" = has a row with started=1 on that date
    star_starting_dates = set(r['game_date'] for r in conn.execute("""
        SELECT DISTINCT game_date
        FROM player_game_logs
        WHERE player_id = ?
          AND started = 1
          AND game_date >= ?
    """, (str(star_id), since_date)).fetchall())

    out_dates = [d for d in team_dates if d not in star_starting_dates]
    playing_dates = [d for d in team_dates if d in star_starting_dates]

    if not out_dates:
        return None  # star never sat — no signal

    # Beneficiary stats on OUT nights
    def avg_stats_on_dates(dates: list) -> dict | None:
        if not dates:
            return None
        placeholders = ','.join('?' * len(dates))
        row = conn.execute(f"""
            SELECT AVG(pts) as pts, AVG(reb) as reb, AVG(ast) as ast,
                   AVG(minutes) as min, AVG(fga) as fga, COUNT(*) as n
            FROM player_game_logs
            WHERE player_id = ?
              AND game_date IN ({placeholders})
              AND minutes > 0
        """, [str(ben_id)] + dates).fetchone()
        if not row or not row['n']:
            return None
        # Usage proxy: FGA per 36 min (avoids raw USG%)
        usg_proxy = None
        if row['min'] and row['min'] > 0 and row['fga'] is not None:
            usg_proxy = round((row['fga'] / row['min']) * 36, 2)
        return {
            'pts': round(row['pts'], 2) if row['pts'] is not None else None,
            'reb': round(row['reb'], 2) if row['reb'] is not None else None,
            'ast': round(row['ast'], 2) if row['ast'] is not None else None,
            'min': round(row['min'], 2) if row['min'] is not None else None,
            'fga': round(row['fga'], 2) if row['fga'] is not None else None,
            'usg_proxy': usg_proxy,
            'n': row['n'],
        }

    obs = avg_stats_on_dates(out_dates)
    base = avg_stats_on_dates(playing_dates)

    if not obs or obs['n'] < CONFIDENCE_THRESHOLDS['LOW']:
        return None  # Not enough observed games

    obs_games = obs['n']
    if obs_games >= CONFIDENCE_THRESHOLDS['HIGH']:
        confidence = 'HIGH'
    elif obs_games >= CONFIDENCE_THRESHOLDS['MEDIUM']:
        confidence = 'MEDIUM'
    else:
        confidence = 'LOW'

    pts_delta = None
    min_delta = None
    if base and obs['pts'] is not None and base['pts'] is not None:
        pts_delta = round(obs['pts'] - base['pts'], 2)
    if base and obs['min'] is not None and base['min'] is not None:
        min_delta = round(obs['min'] - base['min'], 2)

    return {
        'obs_pts':       obs.get('pts'),
        'obs_reb':       obs.get('reb'),
        'obs_ast':       obs.get('ast'),
        'obs_min':       obs.get('min'),
        'obs_fga':       obs.get('fga'),
        'obs_usg_proxy': obs.get('usg_proxy'),
        'base_pts':      base['pts'] if base else None,
        'base_min':      base['min'] if base else None,
        'pts_delta':     pts_delta,
        'min_delta':     min_delta,
        'obs_games':     obs_games,
        'base_games':    base['n'] if base else 0,
        'confidence':    confidence,
    }


def _check_started_coverage(conn) -> tuple[int, int]:
    """Check how many player_game_logs rows have started populated."""
    total = conn.execute("SELECT COUNT(*) FROM player_game_logs WHERE minutes > 0").fetchone()[0]
    enriched = conn.execute("SELECT COUNT(*) FROM player_game_logs WHERE started IS NOT NULL AND minutes > 0").fetchone()[0]
    return enriched, total


def main():
    parser = argparse.ArgumentParser(description="Build WOWY Observed (Phase 2B)")
    parser.add_argument("--days", type=int, default=120, help="Lookback window in days (default 120)")
    parser.add_argument("--min-minutes-gained", type=float, default=2.0,
                        help="Min minutes_gained threshold for beneficiary pairs (default 2.0)")
    parser.add_argument("--dry-run", action="store_true", help="Print only, no DB writes")
    args = parser.parse_args()

    since_date = (datetime.now() - timedelta(days=args.days)).strftime('%Y-%m-%d')

    print(f"\n{'='*55}")
    print(f"   👥 BUILD WOWY OBSERVED (Phase 2B)")
    print(f"   Window: last {args.days} days (since {since_date})")
    print(f"   Min minutes_gained: {args.min_minutes_gained}")
    print(f"{'='*55}\n")

    conn = _get_conn()

    # Check started field coverage — warn if low
    enriched, total = _check_started_coverage(conn)
    pct = enriched / total * 100 if total else 0
    print(f"📊 started field coverage: {enriched:,}/{total:,} rows ({pct:.1f}%)")
    if pct < 10:
        print("⚠️  WARNING: started field is sparsely populated.")
        print("   Run sync_sportsdata_enrichment.py --backfill first for best results.")
        print("   Proceeding with available data (absent rows treated as star OUT).\n")

    pairs = _get_pairs(conn, args.min_minutes_gained)
    print(f"🔗 Beneficiary pairs to evaluate: {len(pairs)}")

    results = []
    skipped = 0
    errors = 0

    for pair in pairs:
        star_id = str(pair['star_id'])
        ben_id = str(pair['beneficiary_id'])
        team = pair['team_abbreviation']

        try:
            data = _compute_wowy(conn, star_id, ben_id, team, since_date)
            if data is None:
                skipped += 1
                continue

            star_canonical = _get_canonical_id(conn, star_id)
            ben_canonical = _get_canonical_id(conn, ben_id)

            # 3-axis role similarity: archetype family + synergy playtype + position
            star_arch     = _get_archetype(conn, star_canonical)
            ben_arch      = _get_archetype(conn, ben_canonical)
            star_pos      = _get_position(conn, star_canonical)
            ben_pos       = _get_position(conn, ben_canonical)
            star_playtype = _get_dominant_playtype(conn, star_canonical)
            ben_playtype  = _get_dominant_playtype(conn, ben_canonical)
            role_score = _role_match_score(
                star_arch, ben_arch,
                star_pos, ben_pos,
                star_playtype, ben_playtype,
            )

            # Trade-awareness: star's games on current team from rotation_profiles.
            # Filter by team_abbreviation to avoid stale old-team profile rows being
            # returned by LIMIT 1 when a player has changed teams mid-season.
            gon_row = conn.execute("""
                SELECT games_on_current_team FROM rotation_profiles
                WHERE player_id = ? AND team_abbreviation = ? LIMIT 1
            """, (star_canonical, team)).fetchone()
            # None means no rotation profile for this team → treat as 0 (new acquisition).
            # COALESCE(None, 0) < 15 → always downgrade if we have no evidence of tenure.
            games_on_team = gon_row['games_on_current_team'] if gon_row else None
            games_on_team_safe = games_on_team if games_on_team is not None else 0

            # Downgrade confidence one tier if star is a new acquisition (< 15 games on team).
            # Research standard (RealGM/Cleaning the Glass): < 30 games = small sample.
            # TOO_LOW pairs kept in DB for future growth but filtered by Module X.
            confidence = data['confidence']
            tier_map = {'HIGH': 'MEDIUM', 'MEDIUM': 'LOW', 'LOW': 'TOO_LOW'}
            confidence_adjusted = (
                tier_map.get(confidence, confidence)
                if games_on_team_safe < 15
                else confidence
            )

            results.append({
                'canonical_id':        ben_canonical,
                'star_canonical_id':   star_canonical,
                'team_abbreviation':   team,
                'star_games_on_team':  games_on_team,
                'star_archetype':      star_arch,
                'ben_archetype':       ben_arch,
                'role_match_score':    role_score,
                'confidence_adjusted': confidence_adjusted,
                'star_position':       star_pos,
                'ben_position':        ben_pos,
                **data,
            })
        except Exception as e:
            errors += 1
            if errors <= 5:
                print(f"   ⚠️ Error pair {star_id}→{ben_id}: {e}")

    print(f"\n📊 Results: {len(results)} pairs computed | {skipped} skipped (no data) | {errors} errors")

    if not results:
        print("No results to write. Exiting.")
        conn.close()
        return

    # Confidence breakdown
    for level in ('HIGH', 'MEDIUM', 'LOW'):
        n = sum(1 for r in results if r['confidence'] == level)
        print(f"   {level}: {n} pairs")

    # Sample: top BREAKOUT beneficiaries by pts_delta
    top = sorted(
        [r for r in results if r['pts_delta'] is not None and r['pts_delta'] > 0],
        key=lambda x: x['pts_delta'], reverse=True
    )[:5]
    if top:
        print("\n🔥 Top pts_delta beneficiaries:")
        for r in top:
            adj_label = r.get('confidence_adjusted', r['confidence'])
            role_score = r.get('role_match_score', '?')
            print(f"   canonical_id={r['canonical_id']} vs star={r['star_canonical_id']}"
                  f"  pts_delta=+{r['pts_delta']:.1f}  obs={r['obs_games']}g"
                  f"  [{r['confidence']}→{adj_label}]  role={role_score}")

    if args.dry_run:
        print("\n[DRY RUN] No writes performed.")
        conn.close()
        return

    # Write to player_wowy_observed (UPSERT)
    written = 0
    for r in results:
        try:
            conn.execute("""
                INSERT INTO player_wowy_observed
                (canonical_id, star_canonical_id, team_abbreviation,
                 obs_pts, obs_reb, obs_ast, obs_min, obs_fga, obs_usg_proxy,
                 base_pts, base_min,
                 pts_delta, min_delta,
                 obs_games, base_games, confidence,
                 star_games_on_team, star_archetype, ben_archetype,
                 role_match_score, confidence_adjusted,
                 star_position, ben_position, updated_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(canonical_id, star_canonical_id) DO UPDATE SET
                    team_abbreviation    = excluded.team_abbreviation,
                    obs_pts              = excluded.obs_pts,
                    obs_reb              = excluded.obs_reb,
                    obs_ast              = excluded.obs_ast,
                    obs_min              = excluded.obs_min,
                    obs_fga              = excluded.obs_fga,
                    obs_usg_proxy        = excluded.obs_usg_proxy,
                    base_pts             = excluded.base_pts,
                    base_min             = excluded.base_min,
                    pts_delta            = excluded.pts_delta,
                    min_delta            = excluded.min_delta,
                    obs_games            = excluded.obs_games,
                    base_games           = excluded.base_games,
                    confidence           = excluded.confidence,
                    star_games_on_team   = excluded.star_games_on_team,
                    star_archetype       = excluded.star_archetype,
                    ben_archetype        = excluded.ben_archetype,
                    role_match_score     = excluded.role_match_score,
                    confidence_adjusted  = excluded.confidence_adjusted,
                    star_position        = excluded.star_position,
                    ben_position         = excluded.ben_position,
                    updated_at           = excluded.updated_at
            """, (
                r['canonical_id'], r['star_canonical_id'], r['team_abbreviation'],
                r['obs_pts'], r['obs_reb'], r['obs_ast'], r['obs_min'],
                r['obs_fga'], r['obs_usg_proxy'],
                r['base_pts'], r['base_min'],
                r['pts_delta'], r['min_delta'],
                r['obs_games'], r['base_games'], r['confidence'],
                r.get('star_games_on_team'), r.get('star_archetype'), r.get('ben_archetype'),
                r.get('role_match_score'), r.get('confidence_adjusted'),
                r.get('star_position'), r.get('ben_position'),
                datetime.now().isoformat(),
            ))
            written += 1
        except Exception as e:
            print(f"   ⚠️ Write error {r['canonical_id']}/{r['star_canonical_id']}: {e}")

    conn.commit()
    print(f"\n✅ Wrote {written} rows to player_wowy_observed")
    conn.close()
    print("Done.")


if __name__ == '__main__':
    main()
