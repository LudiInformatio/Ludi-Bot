import logging
import datetime
import sqlite3
import sys
import config
from module_a import Gatekeeper
from module_c import LudiOracle
from module_d import LudiYak
from module_e import LudiCalibrator
from module_f import LudiReporter
from module_g import LudiRefEngine
from module_h_historian import LudiHistorian
from module_x_scenario import ScenarioBuilder
from utils.telegram_notifier import send_message
from utils.claude_client import get_claude_analysis, SONNET_MODEL, HAIKU_MODEL
from utils.claude_prompts import (
    ROSTER_RULES, 
    ANALYSIS_PROTOCOL,
    GAME_NOTES_TEMPLATE, 
    SPOTLIGHT_TEMPLATE,
    GAME_NOTES_EXAMPLE,
    SPOTLIGHT_EXAMPLE
)
import main
from utils.perplexity_client import PerplexityClient
from utils.trend_engine import get_player_trends, get_beneficiary_context, get_stagger_context, format_trend_line, format_minutes_line, get_matchup_analysis
from utils.time_utils import get_time_context, format_time_context_note
from utils.player_id_resolver import resolve_canonical_name
from utils.tag_classifier import calculate_streak_score  # C2: unified streak scorer
from utils.game_notes_cache import (
    load_game_cache, 
    write_game_cache, 
    check_cache_valid, 
    mark_lineup_confirmed,
    get_cache_path
)

# Configure Logging
logging.basicConfig(level=logging.INFO, format="[MORNING-BRIEF] %(message)s")

_MAX_BLOCK_CHARS = {
    'situational_context': 500,
    'injury_intel_block': 600,
    'beneficiary_block': 400,
    'edges_block': 800,
    'schedule_notes': 500,   # expanded from 200 — catches trade/rotation news
    'rotation_block': 300,
    'teammates_context': 150,
}


def _safe_inject(text: str, max_chars: int) -> str:
    """Pre-truncate injected template blocks to prevent silent overflow."""
    if text and len(text) > max_chars:
        return text[:max_chars] + "... [truncated]"
    return text if text else ""


def _build_slate_trends_header(tonight_teams: list, conn) -> str:
    """
    Build a single slate-wide trends header sent ONCE at the top of the brief.

    Covers all teams playing tonight (full slate, not just top-4 games).
    Auto-excludes OUT/DOUBTFUL players daily — futureproofed against injuries.
    GTD and healthy players are included.

    Sections:
    - 3-4 team form signals (off_quality_14d from team_scheme_cache)
    - 4-5 HOT players (largest positive trend_delta — combo props PRA/PA/PR
      surface when they're the dominant signal, bigger than single-stat delta)
    - 4-5 COOLING players (largest negative trend_delta)

    Returns empty string on error or if no notable trends exist.
    """
    if not tonight_teams:
        return ""

    KEY_STATS = ('PTS', 'PRA', 'PA', 'PR', 'REB', 'AST', '3PM')
    # C2: streak score ≥ 2 = HOT (label: ON FIRE=3, HOT=2), ≤ -2 = COOLING (COOLING=-2, ICE COLD=-3)

    try:
        cursor = conn.cursor()
        ph_t = ','.join('?' * len(tonight_teams))
        ph_s = ','.join('?' * len(KEY_STATS))

        # Players to exclude: OUT or DOUBTFUL on any team tonight
        # UNION: catch injuries with blank team_abbreviation via canonical_ids (e.g. Nurkic RSS entries)
        tonight_teams_list = list(tonight_teams)
        ph_t2 = ','.join('?' * len(tonight_teams_list))
        cursor.execute(f"""
            SELECT DISTINCT player_name FROM player_injuries
            WHERE team_abbreviation IN ({ph_t})
              AND resolved_at IS NULL AND status IN ('OUT', 'DOUBTFUL')
              AND snapshot_time >= datetime('now', '-14 days')
            UNION
            SELECT DISTINCT pi.player_name FROM player_injuries pi
            JOIN player_canonical_ids ci ON LOWER(ci.full_name) = LOWER(pi.player_name)
            WHERE (pi.team_abbreviation IS NULL OR pi.team_abbreviation = '')
              AND ci.team IN ({ph_t2})
              AND pi.resolved_at IS NULL AND pi.status IN ('OUT', 'DOUBTFUL')
              AND pi.snapshot_time >= datetime('now', '-14 days')
        """, tonight_teams + tonight_teams_list)
        excluded = {r[0] for r in cursor.fetchall()}

        # Team quality signals (off_quality_14d from OFFENSE rows)
        cursor.execute(f"""
            SELECT team_abbr, off_quality_14d
            FROM team_scheme_cache
            WHERE team_abbr IN ({ph_t}) AND scheme_type = 'OFFENSE'
        """, tonight_teams)
        off_quality = {r[0]: r[1] for r in cursor.fetchall()}

        # Player trends — C2: fetch multi-window averages for calculate_streak_score()
        cursor.execute(f"""
            SELECT player_name, team_abbreviation, stat,
                   l7_avg, l10_avg, l15_avg, season_avg
            FROM player_trends
            WHERE team_abbreviation IN ({ph_t})
              AND stat IN ({ph_s})
              AND season_avg IS NOT NULL AND season_avg > 0
              AND player_name NOT IN (
                  SELECT DISTINCT player_name FROM player_injuries
                  WHERE team_abbreviation IN ({ph_t})
                    AND resolved_at IS NULL
                    AND status IN ('OUT', 'DOUBTFUL')
                    AND snapshot_time >= datetime('now', '-14 days')
              )
        """, tonight_teams + list(KEY_STATS) + tonight_teams)
        rows = cursor.fetchall()

    except Exception:
        return ""

    # Team form (show STRONG/WEAK offense for tonight's teams — up to 4)
    hot_teams, cool_teams = [], []
    for team in tonight_teams:
        q = off_quality.get(team)
        if q == 'STRONG':
            hot_teams.append(team)
        elif q == 'WEAK':
            cool_teams.append(team)

    # Player hot/cool — C2: use calculate_streak_score() with multi-window data
    # One entry per player — best (highest abs score) stat wins
    # Score labels: ON FIRE=+3, HOT=+2, COOLING=-2, ICE COLD=-3
    _SCORE_LABELS = {3: "🔥 ON FIRE", 2: "🔥 HOT", -2: "❄️ COOLING", -3: "❄️ ICE COLD"}
    _player_best: dict = {}  # name → (score, label_str)
    for name, team, stat, l7_avg, l10_avg, l15_avg, season_avg in rows:
        score = calculate_streak_score(l7_avg, l10_avg, l15_avg, season_avg)
        if abs(score) < 2:
            continue
        short = name.split()[-1]
        delta = (l7_avg or 0) - (season_avg or 0)
        sign = "+" if delta >= 0 else ""
        label_str = f"{short} ({team}) {stat} {sign}{delta:.1f}"
        # Keep best absolute score per player across stats
        prev_score, _ = _player_best.get(name, (0, ""))
        if abs(score) > abs(prev_score):
            _player_best[name] = (score, label_str)

    hot_players = [lbl for sc, lbl in _player_best.values() if sc >= 2]
    cool_players = [lbl for sc, lbl in _player_best.values() if sc <= -2]

    if not hot_teams and not cool_teams and not hot_players and not cool_players:
        return ""

    import datetime as _dt
    today = _dt.datetime.now().strftime('%b %-d')
    lines = [f"📊 TONIGHT'S TRENDS · {today}"]

    # Team form block
    team_parts = []
    if hot_teams:
        team_parts.append("🔥 Offenses running hot: " + " | ".join(hot_teams[:4]))
    if cool_teams:
        team_parts.append("❄️ Offenses running cold: " + " | ".join(cool_teams[:3]))
    if team_parts:
        lines.append("\n".join(team_parts))

    # Player blocks
    if hot_players:
        lines.append("🔥 HOT (L7 vs season):\n" + " | ".join(hot_players[:5]))
    if cool_players:
        lines.append("❄️ COOLING (L7 vs season):\n" + " | ".join(cool_players[:4]))

    return "\n\n".join(lines)


def _build_rotation_block(team_abbr: str, out_names: list, cursor) -> str:
    """Return top-8 active rotation players for a team from ludi.db (last 14d).
    Excludes tonight's OUT players so Claude only sees currently available names.
    Prevents Claude from falling back on stale training-data roster knowledge."""
    try:
        if out_names:
            placeholders = ','.join('?' * len(out_names))
            cursor.execute(f"""
                SELECT player_name, ROUND(AVG(minutes), 1) as avg_min
                FROM player_game_logs
                WHERE team_abbreviation = ?
                  AND game_date >= date('now', '-14 days')
                  AND minutes > 0
                  AND player_name NOT IN ({placeholders})
                GROUP BY player_name
                ORDER BY avg_min DESC
                LIMIT 8
            """, [team_abbr] + list(out_names))
        else:
            cursor.execute("""
                SELECT player_name, ROUND(AVG(minutes), 1) as avg_min
                FROM player_game_logs
                WHERE team_abbreviation = ?
                  AND game_date >= date('now', '-14 days')
                  AND minutes > 0
                GROUP BY player_name
                ORDER BY avg_min DESC
                LIMIT 8
            """, (team_abbr,))
        rows = cursor.fetchall()
        if not rows:
            return f"No recent game logs for {team_abbr}."
        return ", ".join(f"{r[0]} ({r[1]}min)" for r in rows)
    except Exception as e:
        return f"Rotation data unavailable ({e})"


def _build_teammates_context(player_name: str, team_abbr: str, out_names: list, cursor) -> str:
    """Return top-3 active teammates by avg minutes for spotlight grounding.
    Prevents Claude from hallucinating lineup context (e.g. mentioning traded players)."""
    try:
        exclude = list(out_names) + [player_name]
        placeholders = ','.join('?' * len(exclude))
        cursor.execute(f"""
            SELECT player_name, ROUND(AVG(minutes), 1) as avg_min
            FROM player_game_logs
            WHERE team_abbreviation = ?
              AND game_date >= date('now', '-14 days')
              AND minutes > 0
              AND player_name NOT IN ({placeholders})
            GROUP BY player_name
            ORDER BY avg_min DESC
            LIMIT 3
        """, [team_abbr] + exclude)
        rows = cursor.fetchall()
        if not rows:
            return "Teammate data unavailable."
        return ", ".join(f"{r[0]} ({r[1]}min)" for r in rows)
    except Exception:
        return "Teammate data unavailable."


def _get_key_advantage_callout(conn, home_team: str, away_team: str) -> str:
    """Phase 8.25 — Surface the #1 exploitable archetype matchup angle for this game."""
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT opponent_team, archetype, pts_vs_baseline, rank_pts,
                   data_confidence, games
            FROM team_dvp_by_archetype
            WHERE opponent_team IN (?, ?)
              AND season = '2025-26'
              AND data_confidence IN ('HIGH', 'MEDIUM')
              AND pts_vs_baseline > 0
            ORDER BY pts_vs_baseline DESC
            LIMIT 1
        """, (home_team, away_team))
        row = cursor.fetchone()
        if not row:
            return ""
        team, archetype, delta, rank, confidence, games = row
        return (
            f"⚡ KEY ANGLE: {archetype} vs {team} — "
            f"+{delta:.1f} pts above avg (rank {rank}/30 · {confidence} · {games}g)"
        )
    except Exception:
        return ""


def _get_team_situation_note(team_abbr, cursor):
    """
    Build a live situational note for a team from team_leverage_profiles + games.
    Replaces the hardcoded _TEAM_SITUATION_NOTES dict.
    """
    notes = []
    try:
        row = cursor.execute("""
            SELECT clutch_factor, garbage_time_boost, overall_ft_rate, overall_oreb_pct
            FROM team_leverage_profiles WHERE team_abbr = ?
        """, (team_abbr,)).fetchone()

        if row:
            clutch, garbage, ft_rate, oreb = row
            if clutch and clutch >= 1.5:
                notes.append(f"Clutch-heavy ({clutch:.1f}x late-game rate)")
            if garbage and garbage >= 1.2:
                notes.append(f"Garbage-time upside ({garbage:.1f}x boost)")
            if ft_rate and ft_rate >= 0.27:
                notes.append(f"High FT rate ({ft_rate:.2f})")
            if oreb and oreb >= 0.30:
                notes.append(f"Strong OREB ({oreb:.2f})")
    except Exception as e:
        print(f"[TAG] Context: {e}")
        pass

    # Win/loss streak from team_current_info (synced daily by sync_team_current_info.py)
    try:
        info_row = cursor.execute("""
            SELECT wins, losses, win_streak, loss_streak
            FROM team_current_info WHERE team_abv = ?
        """, (team_abbr,)).fetchone()
        if info_row:
            wins, losses, win_streak, loss_streak = info_row
            if win_streak and int(win_streak) >= 3:
                notes.append(f"{win_streak}-game win streak")
            elif loss_streak and int(loss_streak) >= 3:
                notes.append(f"{loss_streak}-game skid")
    except Exception as e:
        print(f"[TAG] Context: {e}")
        pass

    return " | ".join(notes) if notes else ""

import argparse

class MorningBriefEngine:
    def __init__(self, target_teams=None, mode="morning", dry_run=False):
        print("\n" + "="*50)
        print(f"   🌅 LUDI {mode.upper()} BRIEF ENGINE")
        print(f"   Status: Production | Visual: V1.0 | Dry Run: {dry_run}")
        print("="*50)
        
        self.target_teams = target_teams
        self.mode = mode
        self.dry_run = dry_run
        
        # Orchestrator helper (The Central Brain)
        self.orch = main.LudiOrchestrator(send_telegram=False) 
        
        # Alias modules from the Orchestrator to ensure shared state
        self.gate = self.orch.gate
        self.yak = self.orch.yak
        self.sim = self.orch.sim
        self.calib = self.orch.calib
        self.zebras = self.orch.zebras
        self.scenario_builder = self.orch.scenario_builder
        self.reporter = self.orch.reporter

    def _notify_no_games(self):
        """Send a brief Telegram message when there are no NBA games today."""
        try:
            date_label = datetime.datetime.now().strftime("%b %-d")
            msg = (
                f"📅 *No NBA games today \\({date_label}\\)*\n\n"
                f"Pipeline sleeping\\. Back when the slate is live\\."
            )
            send_message(msg, parse_mode="MarkdownV2")
        except Exception as e:
            print(f"[TAG] Context: {e}")
            pass  # Never let notification failure crash the briefing

    def _get_db_conn(self):
        """WAL-mode SQLite connection."""
        conn = sqlite3.connect(config.DB_PATH, timeout=30)
        conn.execute("PRAGMA journal_mode=WAL;")
        return conn

    def run(self):
        """
        Main Execution Flow:
        1. Fetch Slate & Refs
        2. Filter for Target Games
        3. Fetch Props
        4. Run Sims
        5. Filter Top 5 Plays
        6. Generate Visual Card
        7. Send to Telegram
        """
        # 1. Fetch Slate & Refs
        self.gate.fetch_live_slate()
        
        # --- FILTER TARGETS ---
        if self.target_teams:
            # Normalize to uppercase
            targets = [t.upper() for t in self.target_teams]
            print(f"🎯 TARGETING SPECIFIC TEAMS: {targets}")
            
            filtered = {}
            for gid, gdata in self.gate.games.items():
                h = self.gate._get_abbr(gdata['home'])
                a = self.gate._get_abbr(gdata['away'])
                
                # Check if EITHER team is in our target list
                if h in targets or a in targets:
                    filtered[gid] = gdata
                    
            self.gate.games = filtered
            
        if not self.gate.games:
            print("📅 No NBA games on today's slate — skipping briefing.")
            self._notify_no_games()
            return

        print(f"✅ Processing {len(self.gate.games)} games.")
        print("🦓 Updating Referee Database...")
        self.zebras.build_ref_database()
        
        # 2. Fetch Props
        print("📊 Fetching Market Data...")
        self.gate.fetch_comprehensive_props(limit_games=len(self.gate.games))
        
        all_bets = []

        # 3. Build & Run Scenarios
        for game_id, game_data in self.gate.games.items():
            if not game_data.get('props'): continue

            # Skip games that tipped off >45 min ago (e.g. 5pm game at 6pm evening lock)
            _start = game_data.get('start_time')
            if _start:
                import pytz as _pytz_skip
                _est_now = datetime.datetime.now(_pytz_skip.timezone('US/Eastern'))
                _start_aware = _start if _start.tzinfo else _start.replace(
                    tzinfo=_pytz_skip.timezone('US/Eastern'))
                if _start_aware < _est_now - datetime.timedelta(minutes=45):
                    print(f"   ⏭️  Skipping {game_data.get('matchup','?')} — tipped off >45min ago")
                    continue
            
            print(f"   > Analyzing {game_data['matchup']}...")
            
            # Reusing Orchestrator Logic for Roster Building
            h_abbr = self.gate._get_abbr(game_data['home'])
            a_abbr = self.gate._get_abbr(game_data['away'])
            
            h_roster = self.orch.get_active_roster(h_abbr)
            a_roster = self.orch.get_active_roster(a_abbr)
            print(f"      ↳ Roster: {len(h_roster)} {h_abbr}, {len(a_roster)} {a_abbr}")
            
            props = self.orch.fetch_props_for_game(game_id)
            print(f"      ↳ Props Available: {len(props)} players")
            
            h_matched = self.orch.match_props_to_roster(props, h_roster)
            a_matched = self.orch.match_props_to_roster(props, a_roster)
            print(f"      ↳ Matched: {len(h_matched)} {h_abbr}, {len(a_matched)} {a_abbr}")
            
            if not h_matched and not a_matched: 
                print("      ⚠️  Skipping: No player props matched to roster.")
                continue

            # Apply Injury Filters (The Yak)
            final_h, final_a = [], []
            for p in h_matched:
                status = self.yak.get_player_status(p['PLAYER_NAME'], h_abbr)
                p['status'] = status['status']
                if status['status'] not in ['OUT', 'DOUBTFUL']: final_h.append(p)
            
            for p in a_matched:
                status = self.yak.get_player_status(p['PLAYER_NAME'], a_abbr)
                p['status'] = status['status']
                if status['status'] not in ['OUT', 'DOUBTFUL']: final_a.append(p)

            print(f"      ↳ Players: {len(final_h)} Home, {len(final_a)} Away")

            # Build Scenario
            base_scenario = self.orch.build_simulation_scenario(game_data, final_h, final_a)
            
            # Run Simulation
            try:
                # Running just the base scenario for the Morning Brief (Speed)
                sim_results = self.sim.run_simulation_batch([base_scenario])
                
                # Analyze Results (Module F Logic locally)
                processed = self.orch.build_reporter_input(sim_results, game_data, self.orch.fetch_props_for_game(game_id))
                
                # Accumulate for Final Report
                if processed:
                    all_bets.extend(processed)
                                
            except Exception as e:
                print(f"⚠️  Analysis failed for {game_id}: {e}")

        # 4. Generate Final Report & Visuals (Delegated to Module F)
        if not all_bets:
            # Check if Odds API quota exhaustion is the cause (expected monthly event, not a bug)
            try:
                import json, pathlib
                # Use absolute path to ensure we find the cache file correctly from any working directory
                _cwd = pathlib.Path(__file__).parent.resolve()
                _quota_cache = _cwd / "cache" / "odds_api_quota.json"
                if _quota_cache.exists():
                    _quota_data = json.loads(_quota_cache.read_text())
                    if _quota_data.get("remaining") == "0" or _quota_data.get("remaining") == 0:
                        print("⚠️  No bets generated — Odds API quota exhausted. BDL fallback had insufficient props.")
                        print("ℹ️  Exiting gracefully — quota resets on the 1st of next month.")
                        sys.exit(0)  # Known quota state — not a workflow failure, no ops-hub alert needed
            except Exception as e:
                print(f"⚠️  Error reading quota cache: {e}")  # Can't read quota cache — fall through to normal exit(1)
            print("⚠️  No data processed. Aborting.")
            sys.exit(1)  # Genuine unexpected failure → triggers ops-hub alert

        print(f"\n💎 Generating Report for {len(all_bets)} games...")
        
        # Determine Title based on Mode
        if self.mode == "evening":
            report_title = "LUDI EVENING LOCK"
            body = "Updated lines and injury adjustments."
        else:
            report_title = "LUDI MORNING BRIEF"
            body = "Top 5 Quality Plays + SGP Targets"
        
        # Module F handles Bet Logging, Tagging, and Image Generation
        # V5.2 Update: Returns processed_bets (list of dicts) as 3rd element
        # Transfer BDL fallback flag so the briefing banner shows when active
        self.reporter._bdl_fallback_active = getattr(self.gate, '_using_bdl_fallback', False)

        try:
            text_report, image_path, processed_bets = self.reporter.generate_report(all_bets, title=report_title)
        except ValueError:
            # Fallback for old Module F signature if not updated
            result = self.reporter.generate_report(all_bets, title=report_title)
            text_report, image_path = result
            processed_bets = [] # Cannot proceed with 8.2/8.3 without this data

        # --- PHASE 8.2: S.A.V.A.G.E. GAME NOTES ---
        if processed_bets:
            print("\n📝 Generating S.A.V.A.G.E. Game Notes...")
            try:
                conn = self._get_db_conn()

                # 1. Group all bets by game_id
                game_groups = {}
                for bet in processed_bets:
                    gid = bet.get('game_id') or bet.get('matchup', 'UNKNOWN')
                    if gid not in game_groups: game_groups[gid] = []
                    game_groups[gid].append(bet)

                # 2. Deterministic game selection — score by tier quality, pick top 4
                # DIAMOND=4.0, BLUE CHIP=2.5, CORE ASSET=1.0, THE STEAL=0.5
                # BENEFICIARY tag bonus=1.0 (usage vacuum games have high narrative value)
                # Top 5 plays (curate_plays.py) are independent and board-wide — not tied to game selection
                MAX_GAME_NOTES = 4
                _tier_weights = {'DIAMOND': 4.0, 'BLUE CHIP': 2.5, 'CORE ASSET': 1.0, 'THE STEAL': 0.5}
                _INJURY_KWS = ["out", "ruled out", "scratch", "game-time", "gtd", "doubtful"]
                _NARRATIVE_KWS = ["revenge", "rivalry", "return", "milestone", "debut"]

                perp_client = None
                game_news_cache = {}
                if getattr(config, 'PERPLEXITY_API_KEY', None):
                    try:
                        perp_client = PerplexityClient()
                        for gid, bets in game_groups.items():
                            first = bets[0] if bets else {}
                            home = first.get('home_team', '')
                            away = first.get('away_team', '')
                            if home and away:
                                # Combined Perplexity query: injuries + lineup + role changes
                                cursor_p = conn.cursor()
                                cursor_p.execute("""
                                    SELECT player_name FROM player_injuries
                                    WHERE team_abbreviation IN (?, ?) AND resolved_at IS NULL AND status = 'OUT'
                                """, (home, away))
                                out_names = [r[0] for r in cursor_p.fetchall()]
                                # Calculate hours_to_game for dynamic Perplexity recency filter
                                _game_start = first.get('start_time')
                                _hours_to_game = 12.0  # default
                                if _game_start:
                                    try:
                                        import pytz as _pytz_perp
                                        _now_est = datetime.datetime.now(_pytz_perp.timezone('US/Eastern'))
                                        _start_aware = _game_start if _game_start.tzinfo else _game_start.replace(tzinfo=_pytz_perp.timezone('US/Eastern'))
                                        _hours_to_game = max(0.0, (_start_aware - _now_est).total_seconds() / 3600)
                                    except Exception:
                                        pass
                                game_news_cache[gid] = perp_client.search_game_context(
                                    home, away, out_names, hours_to_game=_hours_to_game)
                    except Exception as e:
                        print(f"   ℹ️  Perplexity game news fetch failed: {e}")

                def _score_game(bets, gid=""):
                    score = sum(
                        _tier_weights.get(b.get('confidence_tier', 'THE STEAL'), 0.5)
                        + (1.0 if 'BENEFICIARY' in str(b.get('tags', '')) else 0.0)
                        for b in bets
                    )
                    news = game_news_cache.get(gid, "")
                    if news:
                        score_delta = 0.0
                        key_signal = ""
                        try:
                            players = [b['player_name'] for b in bets[:5]]
                            stats = list({b['stat_category'] for b in bets})

                            nsp_system = """You are an NBA news relevance scorer for a sports betting model.
Return ONLY valid JSON: {"score_delta": <-2.0 to +2.0>, "key_signal": "<10 words>"}
Positive score: news boosts confidence. Negative score: news reduces confidence. Zero: irrelevant."""

                            nsp_prompt = f"""BETS IN THIS GAME:
Players: {', '.join(players)}
Stats being bet: {', '.join(stats)}

NEWS (truncated):
{news[:600]}

QUESTION: Does this news change the expected outcome for any of these specific bets?
Return JSON only."""

                            nsp_response = get_claude_analysis(
                                prompt=nsp_prompt,
                                system_prompt=nsp_system,
                                model=HAIKU_MODEL,
                                temperature=0.1,
                                max_tokens=100,
                                call_type='news_sanity',
                            )

                            if nsp_response:
                                import json
                                try:
                                    clean = nsp_response.strip()
                                    if '```' in clean:
                                        clean = clean.split('```')[1]
                                        if clean.startswith('json'):
                                            clean = clean[4:]
                                    clean = clean.strip()
                                    data = json.loads(clean)
                                    score_delta = float(data.get('score_delta', 0.0))
                                    key_signal = str(data.get('key_signal', ''))
                                except (json.JSONDecodeError, ValueError, KeyError):
                                    pass
                        except Exception as e:
                            print(f"[TAG] Context: {e}")
                            pass

                        if score_delta != 0.0:
                            score += score_delta
                        else:
                            news_lower = news.lower()
                            if any(kw in news_lower for kw in _INJURY_KWS):
                                score += 1.5
                            if any(kw in news_lower for kw in _NARRATIVE_KWS):
                                score += 0.5
                    return min(score, 20.0)

                scored_games = sorted(game_groups.items(), key=lambda x: _score_game(x[1], x[0]), reverse=True)
                top_games = scored_games[:MAX_GAME_NOTES]
                skipped = len(scored_games) - len(top_games)
                if skipped > 0:
                    print(f"   ℹ️  {len(scored_games)} games on slate — generating notes for top {len(top_games)}, skipping {skipped} low-value games")

                # Collect all teams on tonight's full slate (ALL scored games, not just top N)
                # Used by slate trends header — ensures teams from lower-ranked games are included
                tonight_teams = list({
                    team
                    for _, bets in scored_games if bets
                    for team in [bets[0].get('home_team', ''), bets[0].get('away_team', '')]
                    if team and team != 'UNK'
                })

                # Send slate-wide trends header ONCE before any per-game notes
                slate_trends = _build_slate_trends_header(tonight_teams, conn)
                if slate_trends:
                    print(f"   📊 Sending slate trends header ({len(tonight_teams)} teams)...")
                    if not self.dry_run:
                        send_message(slate_trends, parse_mode=None)
                    else:
                        print(f"   [DRY RUN] Slate trends:\n{slate_trends}\n")

                for gid, bets in top_games:
                    if not bets: continue
                    
                    # 2. Build Context
                    first = bets[0]
                    home_team = first.get('home_team', 'UNK')
                    away_team = first.get('away_team', 'UNK')
                    spread = first.get('spread', 0)
                    total = first.get('total', 0)
                    home_team_total = first.get('home_team_total', 'N/A')
                    away_team_total = first.get('away_team_total', 'N/A')
                    matchup = first.get('matchup', gid)
                    
                    blowout_risk = "HIGH" if abs(spread) > 10 else "MODERATE"
                    
                    print(f"   > Notes for {matchup}...")
                    
                    # 3. Query Injuries (By Team)
                    # UNION: also catch injuries where team_abbreviation is blank (e.g. Nurkic from RSS)
                    # resolved via player_canonical_ids. Filter days_out < 75 so long-term season
                    # outs (Steven Adams 220d) don't consume Claude's 600-char injury budget.
                    cursor = conn.cursor()
                    cursor.execute("""
                        SELECT player_name, status, days_out, injury_type, team_abbreviation
                        FROM player_injuries
                        WHERE (team_abbreviation = ? OR team_abbreviation = ?)
                          AND resolved_at IS NULL
                          AND status IN ('OUT', 'DOUBTFUL', 'GTD')
                          AND snapshot_time >= datetime('now', '-14 days')
                          AND (days_out IS NULL OR days_out < 75)
                        UNION
                        SELECT pi.player_name, pi.status, pi.days_out, pi.injury_type,
                               ci.team as team_abbreviation
                        FROM player_injuries pi
                        JOIN player_canonical_ids ci ON LOWER(ci.full_name) = LOWER(pi.player_name)
                        WHERE (pi.team_abbreviation IS NULL OR pi.team_abbreviation = '')
                          AND ci.team IN (?, ?)
                          AND pi.resolved_at IS NULL
                          AND pi.status IN ('OUT', 'DOUBTFUL', 'GTD')
                          AND pi.snapshot_time >= datetime('now', '-14 days')
                          AND (pi.days_out IS NULL OR pi.days_out < 75)
                    """, (home_team, away_team, home_team, away_team))
                    injuries = cursor.fetchall()

                    # Deduplicate by player: when ESPN and BDL/Tank01 conflict, keep most severe status.
                    # Status severity: OUT(4) > DOUBTFUL(3) > GTD(2) > PROBABLE(1)
                    STATUS_SEVERITY = {'OUT': 4, 'DOUBTFUL': 3, 'GTD': 2, 'PROBABLE': 1}
                    best_injury = {}
                    for row in injuries:
                        pname, status, days_out, inj_type = row[0], row[1], row[2], row[3]
                        team_abbr = row[4] if len(row) > 4 else ""
                        severity = STATUS_SEVERITY.get(status, 0)
                        if pname not in best_injury or severity > STATUS_SEVERITY.get(best_injury[pname][0], 0):
                            best_injury[pname] = (status, days_out, inj_type, team_abbr)

                    injury_lines = []
                    for pname, (status, days_out, inj_type, team_abbr) in best_injury.items():
                        # Include team label so Claude associates traded players with correct team
                        team_label = f" [{team_abbr}]" if team_abbr else ""
                        injury_lines.append(f"{status}: {pname}{team_label} ({inj_type})")
                    injury_intel_block = "\n".join(injury_lines) if injury_lines else "No major injuries reported."

                    # 3b. Beneficiary context (Phase 8.15)
                    beneficiary_block = get_beneficiary_context(home_team, away_team)

                    # 3c. Team pace + leverage note from team_leverage_profiles
                    matchup_pace_note = "Average"
                    blowout_close_note = ""
                    try:
                        cursor.execute("""
                            SELECT team_abbr, overall_pace, vh_ortg, l_ortg, clutch_factor, garbage_time_boost
                            FROM team_leverage_profiles WHERE team_abbr IN (?, ?)
                        """, (home_team, away_team))
                        pace_rows = cursor.fetchall()
                        if pace_rows:
                            avg_pace = sum(r[1] for r in pace_rows if r[1]) / max(len(pace_rows), 1)
                            if avg_pace >= 101.0:
                                matchup_pace_note = f"FAST (avg {avg_pace:.1f})"
                            elif avg_pace <= 96.0:
                                matchup_pace_note = f"SLOW (avg {avg_pace:.1f})"
                            else:
                                matchup_pace_note = f"Average ({avg_pace:.1f})"
                            
                            for row in pace_rows:
                                team, pace, vh_ortg, l_ortg, clutch, garbage = row
                                if clutch and clutch >= 1.6:
                                    blowout_close_note += f"{team} clutch-heavy. "
                                if garbage and garbage >= 1.3:
                                    blowout_close_note += f"{team} bench upside in blowouts. "
                    except Exception as e:
                        print(f"[TAG] Context: {e}")
                        pass

                    # 4. Opponent Scheme + Intelligence Context
                    # Fix: scheme_type = 'DEFENSE' (not 'DEFENSIVE') to match the DB.
                    # Enriched: also pull team_playtype_allowed for intelligence layer context.
                    schemes = {}        # {team: def_style}
                    off_schemes = {}    # {team: off_style}
                    playtype_ctx = {}   # {team: "allows X drives/g (Yth), Z C&S/g (Wth)"}
                    for tm in [home_team, away_team]:
                        # Defense style
                        cursor.execute("""
                            SELECT active_style FROM team_scheme_cache
                            WHERE team_abbr = ? AND scheme_type = 'DEFENSE'
                        """, (tm,))
                        row = cursor.fetchone()
                        schemes[tm] = row[0] if row else "NEUTRAL"
                        # Offense style
                        cursor.execute("""
                            SELECT active_style FROM team_scheme_cache
                            WHERE team_abbr = ? AND scheme_type = 'OFFENSE'
                        """, (tm,))
                        off_row = cursor.fetchone()
                        off_schemes[tm] = off_row[0] if off_row else "BALANCED"
                        # Playtype allowed context (from intelligence table)
                        cursor.execute("""
                            SELECT ROUND(drives_fga_allowed_pg,2) as drives, drives_rank,
                                   ROUND(cs_3pa_allowed_pg,2) as cs3pa, cs_3pa_rank,
                                   def_quality
                            FROM team_playtype_allowed WHERE team_abbr = ? AND season = '2025-26'
                        """, (tm,))
                        pt_row = cursor.fetchone()
                        if pt_row:
                            playtype_ctx[tm] = (
                                f"allows {pt_row[0]} drives per game (ranked #{pt_row[1]}), "
                                f"{pt_row[2]} catch-and-shoot 3PA per game (ranked #{pt_row[3]}) "
                                f"[{pt_row[4] or 'AVERAGE'} defense]"
                            )

                    # 5. Edges Block (Top 3 bets)
                    # Sort by edge descending
                    sorted_bets = sorted(bets, key=lambda x: x.get('edge', 0), reverse=True)[:3]
                    edges_lines = []
                    for b in sorted_bets:
                        edges_lines.append(
                            f"• {b['name']} {b['stat']} ({b['line']}) — {b['bet_on']} "
                            f"(Edge: {b.get('edge', 0)}%)"
                        )
                    edges_block = "\n".join(edges_lines)

                    # 6. Build Prompt
                    # Handle template placeholders that are for Claude (e.g., {player}) by preserving them
                    # We pass them as literal strings "{key}" so python's .format() keeps them
                    # Keys that Claude fills in — preserved as literal {key} in the template
                    preservation_keys = {
                        k: "{" + k + "}"
                        for k in ["player", "stat", "edge_reason", "edge_pct",
                                  "days_out", "injury_type", "beneficiary",
                                  "boost", "proj", "update_time", "one_sentence"]
                    }
                    
                    # B2: Replace hardcoded _TEAM_SITUATION_NOTES with data-driven version
                    home_situation = _get_team_situation_note(home_team, cursor)
                    away_situation = _get_team_situation_note(away_team, cursor)
                    situational_context = f"{home_team}: {home_situation}" if home_situation else ""
                    if away_situation:
                        situational_context += (f" | {away_team}: {away_situation}" 
                                             if situational_context else f"{away_team}: {away_situation}")
                    if not situational_context:
                        situational_context = "No specific situational flags."
                    
                    env = config.get_scoring_environment()
                    over_rate = env.get('over_hit_rate_14d', 0)
                    env_label = env.get('environment', 'NEUTRAL')
                    env_note = f"{env_label} ({over_rate:.0%} 14d OVER rate)" if over_rate else "Normal"

                    # Time-aware confidence context (EARLY_LOOK / AFTERNOON / PRE_GAME / LOCK_TIME)
                    time_context_note = format_time_context_note()
                    
                    # B3: Append blowout/close context to pace note
                    matchup_pace_note = f"{matchup_pace_note} | {blowout_close_note}".strip(" |") \
                        if blowout_close_note else matchup_pace_note
                    
                    game_news = game_news_cache.get(gid, "")
                    # schedule_notes feeds the {schedule_notes} row — expanded to 500 chars
                    # (was 200) to capture trade/rotation blurbs that were previously cut
                    schedule_notes = game_news if game_news else "Standard rest"

                    # Build current rotation from ludi.db (anti-stale-roster grounding)
                    # OUT players are excluded so Claude only writes about available names
                    out_names_tonight = [r[0] for r in injuries if r[1] == 'OUT']
                    try:
                        away_rotation = _build_rotation_block(away_team, out_names_tonight, cursor)
                        home_rotation = _build_rotation_block(home_team, out_names_tonight, cursor)
                    except Exception as _re:
                        away_rotation = f"Rotation data unavailable ({_re})"
                        home_rotation = f"Rotation data unavailable ({_re})"

                    # Build date label: "TONIGHT · Feb 19" or "TOMORROW · Feb 20"
                    import pytz as _pytz_mb
                    _est_now = datetime.datetime.now(_pytz_mb.timezone('US/Eastern'))
                    _game_date_str = first.get('game_date', '')
                    try:
                        _gd = datetime.datetime.strptime(_game_date_str, '%Y-%m-%d').date() if _game_date_str else _est_now.date()
                        _day = "TONIGHT" if _gd == _est_now.date() else "TOMORROW"
                        game_label = f"{_day} · {_gd.strftime('%b %d').replace(' 0', ' ')}"
                    except Exception as e:
                        print(f"[TAG] Context: {e}")
                        game_label = f"TONIGHT · {_est_now.strftime('%b %d').replace(' 0', ' ')}"

                    # B1: B2B detection — check if either team played yesterday
                    fatigue_flag = "None"
                    try:
                        _game_date = _game_date_str if _game_date_str else _est_now.strftime('%Y-%m-%d')
                        
                        _home_b2b = cursor.execute("""
                            SELECT 1 FROM games
                            WHERE (home_team = ? OR away_team = ?)
                            AND date = date(?, '-1 day')
                            LIMIT 1
                        """, (home_team, home_team, _game_date)).fetchone() is not None

                        _away_b2b = cursor.execute("""
                            SELECT 1 FROM games
                            WHERE (home_team = ? OR away_team = ?)
                            AND date = date(?, '-1 day')
                            LIMIT 1
                        """, (away_team, away_team, _game_date)).fetchone() is not None

                        if _home_b2b and _away_b2b:
                            fatigue_flag = f"BOTH teams on B2B"
                        elif _home_b2b:
                            fatigue_flag = f"{home_team} on B2B (home)"
                        elif _away_b2b:
                            fatigue_flag = f"{away_team} on B2B (road)"
                    except Exception as e:
                        print(f"[TAG] Context: {e}")
                        fatigue_flag = "None"

                    try:
                        prompt = GAME_NOTES_TEMPLATE.format(
                            away_team=away_team,
                            home_team=home_team,
                            game_label=game_label,
                            spread=spread,
                            blowout_risk=blowout_risk,
                            total=total,
                            home_team_total=home_team_total,
                            away_team_total=away_team_total,
                            env_note=env_note,
                            matchup_pace_note=matchup_pace_note,
                            schedule_notes=_safe_inject(schedule_notes, _MAX_BLOCK_CHARS['schedule_notes']),
                            fatigue_flag=fatigue_flag,
                            injury_intel_block=_safe_inject(injury_intel_block, _MAX_BLOCK_CHARS['injury_intel_block']),
                            beneficiary_block=_safe_inject(beneficiary_block, _MAX_BLOCK_CHARS['beneficiary_block']),
                            # Enriched scheme context (fixed 'DEFENSIVE'→'DEFENSE' typo + intelligence layer)
                            # Format: "OFF:MOTION · DEF:PAINT_PACK [WEAK] — allows 1.8 drives/g (#2)"
                            away_archetype_summary=(
                                f"OFF:{off_schemes.get(away_team,'?')} · "
                                f"DEF:{schemes.get(away_team,'NEUTRAL')}"
                                + (f" — {playtype_ctx[away_team]}" if away_team in playtype_ctx else "")
                            ),
                            home_def_scheme=(
                                f"{schemes.get(home_team,'NEUTRAL')}"
                                + (f" · {playtype_ctx[home_team]}" if home_team in playtype_ctx else "")
                            ),
                            home_archetype_summary=(
                                f"OFF:{off_schemes.get(home_team,'?')} · "
                                f"DEF:{schemes.get(home_team,'NEUTRAL')}"
                                + (f" — {playtype_ctx[home_team]}" if home_team in playtype_ctx else "")
                            ),
                            away_def_scheme=(
                                f"{schemes.get(away_team,'NEUTRAL')}"
                                + (f" · {playtype_ctx[away_team]}" if away_team in playtype_ctx else "")
                            ),
                            edges_block=_safe_inject(edges_block, _MAX_BLOCK_CHARS['edges_block']),
                            situational_context=_safe_inject(situational_context, _MAX_BLOCK_CHARS['situational_context']),
                            time_context_note=time_context_note,
                            away_rotation=_safe_inject(away_rotation, _MAX_BLOCK_CHARS['rotation_block']),
                            home_rotation=_safe_inject(home_rotation, _MAX_BLOCK_CHARS['rotation_block']),
                            **preservation_keys
                        )
                        
                        # Phase 8.28: Check cache validity in evening mode
                        game_key = f"{home_team}@{away_team}"
                        cached_notes = None
                        use_cache = False
                        
                        if self.mode == "evening":
                            cache_entry = load_game_cache(game_key)
                            if cache_entry:
                                is_valid, changed_players = check_cache_valid(game_key, conn)
                                if is_valid and cache_entry.get('lineup_confirmed'):
                                    cached_notes = cache_entry.get('notes_text', '')
                                    if cached_notes:
                                        use_cache = True
                                        print(f"      📋 Using cached notes for {matchup} (valid + lineup confirmed)")
                                else:
                                    reason = f"Invalid: injury changes for {changed_players}" if changed_players else "Not lineup confirmed"
                                    print(f"      ℹ️ Cache invalid for {matchup}: {reason} — generating fresh notes")

                        # 7. Call Claude (or use cache)
                        if use_cache and cached_notes:
                            response = cached_notes
                        else:
                            response = get_claude_analysis(
                                prompt=prompt,
                                system_prompt=GAME_NOTES_EXAMPLE + "\n\n" + ROSTER_RULES + "\n\n" + ANALYSIS_PROTOCOL,
                                model=SONNET_MODEL,
                                temperature=0.2,
                                max_tokens=1500,
                                call_type='game_notes',
                            )

                        if response:
                            print(f"      ✅ Notes generated for {matchup}")
                            # Persist game notes to DB (Phase 8.6)
                            try:
                                run_date_str = getattr(self, 'run_date', None) or datetime.datetime.now().strftime('%Y-%m-%d')
                                conn.execute('''
                                    INSERT OR REPLACE INTO game_notes_log (game_id, run_date, notes_text)
                                    VALUES (?, ?, ?)
                                ''', (gid, run_date_str, response))
                                conn.commit()
                                print(f"      💾 Game notes saved to DB for {matchup}")
                            except Exception as e_db:
                                print(f"      ⚠️ Failed to save game notes to DB: {e_db}")
                            
                            # Phase 8.28: Write to game intelligence cache
                            if not use_cache and response:
                                try:
                                    player_snapshots = {}
                                    for pname, (status, days_out, inj_type) in best_injury.items():
                                        player_snapshots[pname] = status
                                    
                                    game_date_str = getattr(self, 'run_date', None) or datetime.datetime.now().strftime('%Y-%m-%d')
                                    start_time_val = first.get('start_time')
                                    tip_time_str = start_time_val.strftime('%H:%M') if start_time_val and hasattr(start_time_val, 'strftime') else '19:00'
                                    
                                    cache_data = {
                                        'game_date': game_date_str,
                                        'tip_time_et': tip_time_str,
                                        'lineup_confirmed': False,
                                        'starters': {},
                                        'key_angle': "",
                                        'injuries': {pname: {'status': s, 'days_out': d, 'type': t} for pname, (s, d, t) in best_injury.items()},
                                        'player_snapshots': player_snapshots,
                                        'notes_text': response,
                                        'projections_summary': {},
                                        'generated_at': datetime.datetime.now().isoformat(),
                                        'refreshed_at': None
                                    }
                                    write_game_cache(game_key, cache_data)
                                    print(f"      💾 Game notes cached for {matchup}")
                                except Exception as e_cache:
                                    print(f"      ⚠️ Failed to cache game notes: {e_cache}")
                            
                            if not self.dry_run:
                                # Truncate + fallback to plain text if Markdown parse fails (400)
                                truncated = response[:4000]
                                # Phase 8.25 — Key Advantage Callout
                                key_angle = _get_key_advantage_callout(conn, home_team, away_team)
                                full_message = f"{key_angle}\n\n{truncated}" if key_angle else truncated
                                if not send_message(full_message, parse_mode="Markdown"):
                                    send_message(full_message, parse_mode=None)
                            else:
                                truncated = response[:4000]
                                key_angle = _get_key_advantage_callout(conn, home_team, away_team)
                                full_message = f"{key_angle}\n\n{truncated}" if key_angle else truncated
                                print(f"      [DRY RUN] Would send:\n{full_message[:100]}...")
                        else:
                            print(f"      ⚠️ No response from Claude for {matchup}")
                            
                    except KeyError as e:
                        print(f"      ❌ Template format error for {matchup}: Missing key {e}")

                conn.close()

            except Exception as e:
                print(f"⚠️ Global Game Notes Error: {e}")
                # Continue to Spotlight phase despite errors

        # --- PHASE 8.3: PLAYER SPOTLIGHT CARDS ---
        print("\n🔦 Generating Player Spotlight Cards...")
        try:
            if processed_bets:
                # 1. Filter for top-tier bets
                top_bets = [b for b in processed_bets if b.get('confidence_tier') in ('DIAMOND', 'BLUE CHIP', 'CORE ASSET')][:5]
                
                if top_bets:
                    conn = self._get_db_conn()
                    
                    for bet in top_bets:
                        try:
                            player_name = bet.get('player_name') or bet.get('name')
                            if not player_name:
                                print(f"   ⏭️  Spotlight skipped: no player_name in bet record")
                                continue
                            team = bet.get('team')
                            opponent = bet.get('opponent')
                            stat_cat = bet.get('stat_category') or bet.get('stat', 'PTS')
                            line = bet.get('line', 0.0)

                            # Resolve to canonical name so Claude receives consistent names
                            # that match what's in injury_intel_block and player_injuries table.
                            # e.g. 'Nikola Jokic' (from Odds API) → 'Nikola Jokić' (canonical)
                            player_name = resolve_canonical_name(conn, player_name)

                            print(f"   > Spotlight analysis for {player_name} ({stat_cat})...")

                            # 2a. Get trend data (Phase 8.15 — replaces _get_l10_for_spotlight)
                            trend_data = get_player_trends(player_name, stat_cat, team, line=line)
                            l10_avg = trend_data.get('l10_avg', 0)
                            hit_rate_l10 = trend_data.get('hit_rate_l10', 0)
                            trend_line_str = format_trend_line(trend_data)
                            minutes_trend_str = format_minutes_line(trend_data)

                            # Streak note
                            streak_line = trend_data.get('streak_vs_line')
                            if streak_line and streak_line != 0:
                                direction = "over" if streak_line > 0 else "under"
                                streak_note = f"{abs(streak_line)}-game {direction} streak vs line"
                            else:
                                streak_note = "No active streak"

                            # 2a2. Stagger context (when teammate is OUT)
                            cursor = conn.cursor()
                            cursor.execute("""
                                SELECT player_name FROM player_injuries
                                WHERE team_abbreviation = ? AND resolved_at IS NULL AND status = 'OUT'
                                  AND snapshot_time >= datetime('now', '-14 days')
                            """, (team,))
                            out_teammates = [r[0] for r in cursor.fetchall()]
                            stagger_note = get_stagger_context(player_name, team, out_teammates) if out_teammates else ""
                            if stagger_note:
                                stagger_note = f"- Stagger: {stagger_note}"

                            # 2b. Get Injury Context
                            cursor.execute("""
                                SELECT status, injury_type, days_out
                                FROM player_injuries
                                WHERE player_name = ? AND status != 'ACTIVE'
                                  AND snapshot_time >= datetime('now', '-14 days')
                                ORDER BY snapshot_time DESC LIMIT 1
                            """, (player_name,))
                            inj_row = cursor.fetchone()
                            injury_context = f"{inj_row[0]} - {inj_row[1]}" if inj_row else "Healthy"

                            # 2c. Get Opponent Scheme
                            cursor.execute("""
                                SELECT active_style FROM team_scheme_cache
                                WHERE team_abbr = ? AND scheme_type = 'DEFENSIVE'
                            """, (opponent,))
                            scheme_row = cursor.fetchone()
                            opp_scheme = scheme_row[0] if scheme_row else "Standard"

                            # 2d. Active teammates for roster grounding (prevents hallucinated lineup refs)
                            active_teammates = _build_teammates_context(
                                player_name, team, out_teammates, cursor
                            )

                            # 2e. Build Prompt
                            prompt = SPOTLIGHT_TEMPLATE.format(
                                player=player_name,
                                team=team,
                                opponent=opponent,
                                stat=stat_cat,
                                line=line,
                                tier=bet.get('confidence_tier'),
                                archetype=bet.get('archetype', 'Unknown'),
                                opp_scheme=opp_scheme,
                                injury_context=injury_context,
                                active_teammates=_safe_inject(active_teammates, _MAX_BLOCK_CHARS['teammates_context']),
                                trend_line=trend_line_str or "No trend data",
                                minutes_trend=minutes_trend_str or "No minutes data",
                                l10_avg=l10_avg,
                                hit_rate_l10=f"{hit_rate_l10:.0f}%" if hit_rate_l10 else "N/A",
                                streak_note=streak_note,
                                stagger_note=stagger_note,
                                edge_pct=round((bet.get('edge', 0)), 1),
                                analysis_block=get_matchup_analysis(
                                    player_name,
                                    opponent,
                                    cursor,
                                    stat_cat
                                ),
                            )
                            
                            # 2e. Call Claude
                            response = get_claude_analysis(
                                prompt=prompt,
                                system_prompt=SPOTLIGHT_EXAMPLE + "\n\n" + ROSTER_RULES + "\n\n" + ANALYSIS_PROTOCOL,
                                model=SONNET_MODEL,
                                temperature=0.2,
                                max_tokens=600,
                                call_type='spotlight',
                                player_name=player_name,
                            )
                            
                            if response:
                                print(f"      ✅ Spotlight generated for {player_name}")
                                if not self.dry_run:
                                    # Truncate to Telegram limit; fall back to plain text if Markdown parse fails
                                    text_out = response[:4000]
                                    if not send_message(text_out, parse_mode="Markdown"):
                                        send_message(text_out, parse_mode=None)
                                else:
                                    print(f"      [DRY RUN] Would send:\n{response[:100]}...")
                            else:
                                print(f"      ⚠️ No response from Claude for {player_name}")
                                
                        except Exception as e:
                            print(f"      ❌ Failed spotlight for {bet.get('name')}: {e}")
                            continue
                            
                    conn.close()
                else:
                    print("   ℹ️ No DIAMOND/BLUE CHIP/CORE ASSET bets for spotlights.")
            else:
                print("   ℹ️ No processed bets available for spotlights.")
                
        except Exception as e:
            print(f"⚠️ Global Spotlight Error: {e}")

        # 5. Send bet list to Telegram as native text (no image card)
        if text_report:
            header = f"*{report_title} | {datetime.date.today().strftime('%b %d')}*\n💎 {body}\n\n"
            full_text = header + text_report
            # Telegram max message size is 4096 chars — split if needed
            MAX_CHARS = 4000
            if not self.dry_run:
                telegram_success = True
                for i in range(0, len(full_text), MAX_CHARS):
                    chunk = full_text[i:i + MAX_CHARS]
                    if not send_message(chunk, parse_mode="Markdown"):
                        print("      ⚠️ Markdown send failed (likely split tag). Retrying as plain text...")
                        if not send_message(chunk, parse_mode=None):
                            print("      ❌ Plain text retry also failed.")
                            telegram_success = False
                
                if telegram_success:
                    print("🚀 Bet list sent to Telegram!")
                else:
                    print("🚨 CRITICAL: Telegram notifications failed. Exiting to trigger Ops Hub.")
                    sys.exit(1)
            else:
                print(f"🚫 [DRY RUN] Would send bet list ({len(full_text)} chars)")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["morning", "evening"], default="morning", help="Report mode")
    parser.add_argument("--dry-run", action="store_true", help="Skip Telegram sends")
    args = parser.parse_args()

    # Process all games on the slate (no hardcoded team filter)
    engine = MorningBriefEngine(target_teams=None, mode=args.mode, dry_run=args.dry_run)
    engine.run()
