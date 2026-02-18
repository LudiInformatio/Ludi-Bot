import logging
import datetime
import sqlite3
import config
from module_a import Gatekeeper
from module_c import LudiOracle
from module_d import LudiYak
from module_e import LudiCalibrator
from module_f import LudiReporter
from module_g import LudiRefEngine
from module_h_historian import LudiHistorian
from module_x_scenario import ScenarioBuilder
from utils.render_full_report import create_briefing_card
from utils.telegram_notifier import send_photo, send_message
from utils.claude_client import get_claude_analysis, SONNET_MODEL
from utils.claude_prompts import (
    ROSTER_RULES, 
    ANALYSIS_PROTOCOL,
    GAME_NOTES_TEMPLATE, 
    SPOTLIGHT_TEMPLATE
)
import main
from utils.perplexity_client import PerplexityClient

# Configure Logging
logging.basicConfig(level=logging.INFO, format="[MORNING-BRIEF] %(message)s")

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

    def _get_db_conn(self):
        """WAL-mode SQLite connection."""
        conn = sqlite3.connect(config.DB_PATH, timeout=30)
        conn.execute("PRAGMA journal_mode=WAL;")
        return conn

    def _get_l10_for_spotlight(self, conn, player_name: str, stat_col: str, line: float) -> dict:
        """Returns {'avg': float, 'hit_rate': float} from player_game_logs last 10 games."""
        stat_col_map = {
            'PTS': 'points', 'REB': 'total_rebounds', 'AST': 'assists',
            '3PM': 'three_pointers_made', 'BLK': 'blocks', 'STL': 'steals'
        }
        db_col = stat_col_map.get(stat_col.upper())
        if not db_col:
            return {'avg': 0, 'hit_rate': 0}
            
        try:
            # Get player_id first (assuming name match)
            cursor = conn.cursor()
            cursor.execute("SELECT player_id FROM players WHERE name = ? LIMIT 1", (player_name,))
            pid_row = cursor.fetchone()
            
            if not pid_row:
                return {'avg': 0, 'hit_rate': 0}
                
            player_id = pid_row[0]
            
            # Query last 10 games from player_game_logs
            # Note: Checking if player_game_logs exists and has date column. 
            # Assuming standard schema: player_id, game_date, [stats]
            query = f"""
                SELECT {db_col} 
                FROM player_game_logs 
                WHERE player_id = ? 
                ORDER BY game_date DESC 
                LIMIT 10
            """
            cursor.execute(query, (player_id,))
            rows = cursor.fetchall()
            
            if not rows:
                return {'avg': 0, 'hit_rate': 0}
                
            values = [r[0] for r in rows if r[0] is not None]
            if not values:
                return {'avg': 0, 'hit_rate': 0}
                
            avg_val = sum(values) / len(values)
            hits = sum(1 for v in values if v > line)
            hit_rate = (hits / len(values)) * 100
            
            return {'avg': round(avg_val, 1), 'hit_rate': round(hit_rate, 1)}
            
        except Exception as e:
            print(f"⚠️ Error getting L10 for {player_name}: {e}")
            return {'avg': 0, 'hit_rate': 0}

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
            print("❌ No matching games found on today's slate. Aborting.")
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
            print("⚠️  No data processed. Aborting.")
            return

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
                                game_news_cache[gid] = perp_client.search_game_news(home, away)
                    except Exception as e:
                        print(f"   ℹ️  Perplexity game news fetch failed: {e}")

                def _score_game(bets, gid=""):
                    score = sum(
                        _tier_weights.get(b.get('confidence_tier', 'THE STEAL'), 0.5)
                        + (1.0 if 'BENEFICIARY' in str(b.get('tags', '')) else 0.0)
                        for b in bets
                    )
                    news = game_news_cache.get(gid, "").lower()
                    if news:
                        if any(kw in news for kw in _INJURY_KWS):
                            score += 1.5
                        if any(kw in news for kw in _NARRATIVE_KWS):
                            score += 0.5
                    return min(score, 20.0)

                scored_games = sorted(game_groups.items(), key=lambda x: _score_game(x[1], x[0]), reverse=True)
                top_games = scored_games[:MAX_GAME_NOTES]
                skipped = len(scored_games) - len(top_games)
                if skipped > 0:
                    print(f"   ℹ️  {len(scored_games)} games on slate — generating notes for top {len(top_games)}, skipping {skipped} low-value games")

                for gid, bets in top_games:
                    if not bets: continue
                    
                    # 2. Build Context
                    first = bets[0]
                    home_team = first.get('home_team', 'UNK')
                    away_team = first.get('away_team', 'UNK')
                    spread = first.get('spread', 0)
                    total = first.get('total', 0)
                    matchup = first.get('matchup', gid)
                    
                    blowout_risk = "HIGH" if abs(spread) > 10 else "MODERATE"
                    
                    print(f"   > Notes for {matchup}...")
                    
                    # 3. Query Injuries (By Team)
                    cursor = conn.cursor()
                    cursor.execute("""
                        SELECT player_name, status, days_out, injury_type 
                        FROM player_injuries 
                        WHERE (team_abbreviation = ? OR team_abbreviation = ?) 
                          AND resolved_at IS NULL
                          AND status IN ('OUT', 'DOUBTFUL', 'GTD')
                    """, (home_team, away_team))
                    injuries = cursor.fetchall()
                    
                    injury_lines = []
                    for row in injuries:
                        injury_lines.append(f"{row[1]}: {row[0]} ({row[3]})")
                    injury_intel_block = "\n".join(injury_lines) if injury_lines else "No major injuries reported."

                    # 4. Opponent Scheme
                    # Fetch for both teams
                    schemes = {}
                    for tm in [home_team, away_team]:
                        cursor.execute("""
                            SELECT active_style FROM team_scheme_cache 
                            WHERE team_abbr = ? AND scheme_type = 'DEFENSIVE'
                        """, (tm,))
                        row = cursor.fetchone()
                        schemes[tm] = row[0] if row else "Standard"

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
                    preservation_keys = {
                        k: "{" + k + "}" 
                        for k in ["player", "stat", "edge_reason", "edge_pct", 
                                  "days_out", "injury_type", "beneficiary", 
                                  "boost", "proj", "update_time", "one_sentence"]
                    }
                    
                    game_news = game_news_cache.get(gid, "")
                    schedule_notes = game_news[:200] if game_news else "Standard rest"

                    # Build date label: "TONIGHT · Feb 19" or "TOMORROW · Feb 20"
                    import pytz as _pytz_mb
                    _est_now = datetime.datetime.now(_pytz_mb.timezone('US/Eastern'))
                    _game_date_str = first.get('game_date', '')
                    try:
                        _gd = datetime.datetime.strptime(_game_date_str, '%Y-%m-%d').date() if _game_date_str else _est_now.date()
                        _day = "TONIGHT" if _gd == _est_now.date() else "TOMORROW"
                        game_label = f"{_day} · {_gd.strftime('%b %d').replace(' 0', ' ')}"
                    except Exception:
                        game_label = f"TONIGHT · {_est_now.strftime('%b %d').replace(' 0', ' ')}"

                    try:
                        prompt = GAME_NOTES_TEMPLATE.format(
                            away_team=away_team,
                            home_team=home_team,
                            game_label=game_label,
                            spread=spread,
                            blowout_risk=blowout_risk,
                            total=total,
                            pace_context="Normal",
                            schedule_notes=schedule_notes,
                            fatigue_flag="None",
                            injury_intel_block=injury_intel_block,
                            away_archetype_summary="Style: " + schemes.get(away_team, "UNK"),
                            home_def_scheme=schemes.get(home_team, "UNK"),
                            home_archetype_summary="Style: " + schemes.get(home_team, "UNK"),
                            away_def_scheme=schemes.get(away_team, "UNK"),
                            edges_block=edges_block,
                            **preservation_keys
                        )
                        
                        # 7. Call Claude
                        response = get_claude_analysis(
                            prompt=prompt,
                            system_prompt=ROSTER_RULES + "\n\n" + ANALYSIS_PROTOCOL,
                            model=SONNET_MODEL,
                            temperature=0.2,
                            max_tokens=1500
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
                            if not self.dry_run:
                                send_message(response, parse_mode="Markdown")
                            else:
                                print(f"      [DRY RUN] Would send:\n{response[:100]}...")
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
                top_bets = [b for b in processed_bets if b.get('confidence_tier') in ('DIAMOND', 'BLUE CHIP')][:5]
                
                if top_bets:
                    conn = self._get_db_conn()
                    
                    for bet in top_bets:
                        try:
                            player_name = bet.get('player_name') or bet.get('name')
                            team = bet.get('team')
                            opponent = bet.get('opponent')
                            stat_cat = bet.get('stat_category') or bet.get('stat', 'PTS')
                            line = bet.get('line', 0.0)
                            
                            print(f"   > Spotlight analysis for {player_name} ({stat_cat})...")

                            # 2a. Get L10 Stats
                            l10_data = self._get_l10_for_spotlight(conn, player_name, stat_cat, line)
                            
                            # 2b. Get Injury Context
                            cursor = conn.cursor()
                            cursor.execute("""
                                SELECT status, injury_type, days_out 
                                FROM player_injuries 
                                WHERE player_name = ? AND status != 'ACTIVE'
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
                            
                            # 2d. Build Prompt
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
                                l10_avg=l10_data['avg'],
                                hit_rate_l10=l10_data['hit_rate'],
                                edge_pct=round((bet.get('edge', 0)), 1), # Edge is already % in module_f? Check. module_f says "edge": edge (float). If >5.0, it's %.
                                analysis_block="" # Let Claude fill this based on system prompt
                            )
                            
                            # 2e. Call Claude
                            response = get_claude_analysis(
                                prompt=prompt,
                                system_prompt=ROSTER_RULES + "\n\n" + ANALYSIS_PROTOCOL,
                                model=SONNET_MODEL,
                                temperature=0.2,
                                max_tokens=600
                            )
                            
                            if response:
                                print(f"      ✅ Spotlight generated for {player_name}")
                                if not self.dry_run:
                                    send_message(response, parse_mode="Markdown")
                                else:
                                    print(f"      [DRY RUN] Would send:\n{response[:100]}...")
                            else:
                                print(f"      ⚠️ No response from Claude for {player_name}")
                                
                        except Exception as e:
                            print(f"      ❌ Failed spotlight for {bet.get('name')}: {e}")
                            continue
                            
                    conn.close()
                else:
                    print("   ℹ️ No DIAMOND/BLUE CHIP bets for spotlights.")
            else:
                print("   ℹ️ No processed bets available for spotlights.")
                
        except Exception as e:
            print(f"⚠️ Global Spotlight Error: {e}")

        if image_path:
            print(f"✅ Visual Card Ready: {image_path}")
            # 5. Send to Telegram (Visual Only)
            
            caption = (
                f"**{report_title} | {datetime.date.today().strftime('%b %d')}**\n"
                f"💎 {body}"
            )
            
            if not self.dry_run:
                send_photo(image_path, caption=caption)
                print("🚀 Sent to Telegram!")
            else:
                print(f"🚫 [DRY RUN] Skipping photo send for {image_path}")
        else:
            print("❌ Failed to generate visual card.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["morning", "evening"], default="morning", help="Report mode")
    parser.add_argument("--dry-run", action="store_true", help="Skip Telegram sends")
    args = parser.parse_args()

    # --- MANUAL WATCHLIST CONFIG ---
    # Jan 13: PHX, MIA, CHI, HOU, SAS, OKC
    # Jan 14: CLE, PHI, NYK, SAC, UTA, CHI (Already in Jan 13 list)
    watchlist = [
        'PHX', 'MIA', 'CHI', 'HOU', 'SAS', 'OKC', # Jan 13
        'CLE', 'PHI', 'NYK', 'SAC', 'UTA'         # Jan 14
    ]
    
    engine = MorningBriefEngine(target_teams=watchlist, mode=args.mode, dry_run=args.dry_run)
    engine.run()
