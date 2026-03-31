import json
import sqlite3
from datetime import datetime, date, timedelta
from pathlib import Path
import config
from utils.perplexity_client import PerplexityClient
from utils.player_id_resolver import resolve_canonical_name
from utils.mappings import normalize_bdl_abbr

CACHE_DIR = Path("cache")
MAX_GAME_CONTEXT_CHARS = 400
MAX_PLAYER_SIGNAL_CHARS = 200
MAX_TOTAL_DOSSIER_CHARS = 15000

def load_dossier_cache(run_date: str) -> dict | None:
    """Reads cache/game_dossier_{run_date}.json if it exists and was written today."""
    cache_path = CACHE_DIR / f"game_dossier_{run_date}.json"
    if cache_path.exists():
        # Check if it was written today
        mtime = datetime.fromtimestamp(cache_path.stat().st_mtime).date()
        if mtime == date.today():
            try:
                with open(cache_path, 'r') as f:
                    return json.load(f)
            except Exception:
                return None
    return None

def build_game_dossier(conn: sqlite3.Connection, run_date: str, bets: list) -> dict:
    """Shared dossier builder + cache."""
    # 1. Check cache
    cached = load_dossier_cache(run_date)
    if cached:
        return cached

    dossier = {}
    perplexity = PerplexityClient()
    
    # Group bets by game
    games = {}
    for bet in bets:
        # bet can be a dict or a sqlite3.Row
        gid = bet['game_id']
        if not gid: continue
        if gid not in games:
            games[gid] = {
                'home': bet['home_team'],
                'away': bet['away_team'],
                'bets': []
            }
        games[gid]['bets'].append(bet)

    twelve_days_ago = (datetime.strptime(run_date, '%Y-%m-%d') - timedelta(days=12)).strftime('%Y-%m-%d')

    for gid, game_info in games.items():
        home = game_info['home']
        away = game_info['away']
        
        # A. Perplexity context
        news_text = "No recent news found."
        if getattr(config, 'PERPLEXITY_API_KEY', None):
            news_text = perplexity.search_game_context(home, away)
        
        # B. Team L5 form
        l5_ppg = {}
        for team in [home, away]:
            query_l5 = """
                SELECT AVG(game_pts) FROM (
                    SELECT game_id, SUM(pts) as game_pts
                    FROM player_game_logs
                    WHERE team_abbreviation = ? AND game_date >= ? AND game_date < ?
                    GROUP BY game_id
                )
            """
            row = conn.execute(query_l5, (normalize_bdl_abbr(team), twelve_days_ago, run_date)).fetchone()
            l5_ppg[team] = round(row[0], 1) if row and row[0] else 0.0

        # C. B2B
        rest_notes = {}
        for team in [home, away]:
            query_prev = "SELECT MAX(date) FROM canonical_games WHERE (home_team = ? OR away_team = ?) AND date < ?"
            row = conn.execute(query_prev, (team, team, run_date)).fetchone()
            if row and row[0]:
                last_date = datetime.strptime(row[0], '%Y-%m-%d')
                curr_date = datetime.strptime(run_date, '%Y-%m-%d')
                if (curr_date - last_date).days == 1:
                    rest_notes[team] = "B2B"
                else:
                    rest_notes[team] = "Standard rest"
            else:
                rest_notes[team] = "Standard rest"
        
        # Ref crew
        lead_ref = "Unknown"
        style = "Neutral"
        fouls = "N/A"
        query_ref = "SELECT referee_crew FROM canonical_games WHERE home_team = ? AND away_team = ? AND date = ?"
        row_ref = conn.execute(query_ref, (home, away, run_date)).fetchone()
        if row_ref and row_ref[0]:
            refs = [r.strip() for r in row_ref[0].split(',') if r.strip()]
            if refs:
                lead_ref = refs[0]
                ref_info = conn.execute("SELECT style, avg_fouls_per_game FROM referee_profiles WHERE referee_name = ?", (lead_ref,)).fetchone()
                if ref_info:
                    style, fouls_val = ref_info
                    fouls = round(fouls_val, 1)

        # D. ATS Trends
        ats_stats = {home: "0-0", away: "0-0"}
        for t, side in [(home, 'home'), (away, 'away')]:
            query_ats = f"SELECT {side}_ats_wins, {side}_ats_losses FROM team_betting_trends WHERE team = ?"
            row_ats = conn.execute(query_ats, (t,)).fetchone()
            if row_ats:
                ats_stats[t] = f"{row_ats[0]}-{row_ats[1]}"

        # E. Defense Scheme
        scheme_note = "Unknown"
        quality_note = "N/A"
        row_scheme = conn.execute("SELECT active_style, def_quality_14d FROM team_scheme_cache WHERE team_abbr = ? AND scheme_type = 'DEFENSE'", (home,)).fetchone()
        if row_scheme:
            scheme_note, quality_note = row_scheme

        # Format Game Context
        # === {away} @ {home} ===
        # NEWS: {perplexity text, truncated to 300 chars}
        # {home} L5: {avg_pts} PPG | {away} L5: {avg_pts} PPG
        # REST: {B2B note or "Standard rest"}
        # REF: {lead_ref} ({style}, {fouls}/gm)
        # ATS: {home} home {wins}-{losses} | {away} away {wins}-{losses}
        # SCHEME: {away} offense vs {home} {active_defense_style} defense ({quality})
        
        game_context = (
            f"=== {away} @ {home} ===\n"
            f"NEWS: {news_text[:300]}\n"
            f"{home} L5: {l5_ppg[home]} PPG | {away} L5: {l5_ppg[away]} PPG\n"
            f"REST: {rest_notes[home]} / {rest_notes[away]}\n"
            f"REF: {lead_ref} ({style}, {fouls}/gm)\n"
            f"ATS: {home} home {ats_stats[home]} | {away} away {ats_stats[away]}\n"
            f"SCHEME: {away} offense vs {home} {scheme_note} defense ({quality_note})"
        )
        
        dossier[gid] = {
            'game_context': game_context[:MAX_GAME_CONTEXT_CHARS],
            'players': {}
        }

        # Player Signals
        for bet in game_info['bets']:
            pname = bet['player_name']
            if not pname: continue
            
            cpname = resolve_canonical_name(conn, pname)
            
            # 1. Hot/cold streak
            streak_note = "N/A"
            label = "neutral"
            stat_cat = bet['stat_category'].upper()
            COMPOSITE_STATS = {
                'PRA': '(pts + reb + ast)',
                'PR': '(pts + reb)',
                'PA': '(pts + ast)',
                'RA': '(reb + ast)',
                '3PM': 'fg3m'
            }
            stat_col = COMPOSITE_STATS.get(stat_cat, stat_cat.lower())

            row_trend = conn.execute("SELECT l7_avg, trend_label FROM player_trends WHERE player_name = ? AND stat = ?", (cpname, bet['stat_category'])).fetchone()
            if row_trend:
                l7, label = row_trend
                streak_note = f"L7={round(l7, 1)}"
            else:
                try:
                    row_logs = conn.execute(f"SELECT AVG({stat_col}) FROM player_game_logs WHERE player_name = ? AND game_date < ? ORDER BY game_date DESC LIMIT 7", (cpname, run_date)).fetchone()
                    if row_logs and row_logs[0]:
                        streak_note = f"L7={round(row_logs[0], 1)}"
                except sqlite3.OperationalError:
                    pass

            # 2. Hit rate
            thirty_days_ago = (datetime.strptime(run_date, '%Y-%m-%d') - timedelta(days=30)).strftime('%Y-%m-%d')
            row_hit = conn.execute("""
                SELECT SUM(CASE WHEN outcome = 'WIN' THEN 1 ELSE 0 END), COUNT(*) 
                FROM bet_recommendations 
                WHERE player_name = ? AND stat_category = ? AND bet_side = ?
                AND game_date >= ? AND game_date < ? AND outcome IS NOT NULL
            """, (pname, bet['stat_category'], bet['bet_side'], thirty_days_ago, run_date)).fetchone()
            hit_str = "0/0"
            if row_hit and row_hit[1] > 0:
                hit_str = f"{row_hit[0]}/{row_hit[1]}"

            # 3. Matchup grade
            match_grade = "neutral"
            archetype = "Unknown"
            row_arch = conn.execute("SELECT archetype FROM players WHERE name = ?", (cpname,)).fetchone()
            if row_arch:
                archetype = row_arch[0]
            
            # 4. Ref bias
            ref_bias_note = "No sig. bias data"
            if lead_ref != "Unknown":
                row_bias = conn.execute("""
                    SELECT points_impact_vs_avg 
                    FROM referee_player_bias b
                    JOIN referee_profiles r ON b.referee_id = r.referee_id
                    WHERE r.referee_name = ? AND b.player_name = ? AND b.games_officiated >= 5
                """, (lead_ref, cpname)).fetchone()
                if row_bias:
                    impact = row_bias[0]
                    ref_bias_note = f"{'+' if impact > 0 else ''}{impact} PPG impact with {lead_ref}"

            # 📊 Streak: L7={avg} ({label}) | Hit: {wins}/{total} L30d on {stat} {side}
            # 🎯 Matchup: {archetype} vs {scheme} → {favorable/neutral/unfavorable}
            # 🦓 Ref: {impact note or "No sig. bias data"}
            
            player_signal = (
                f"📊 Streak: {streak_note} ({label}) | Hit: {hit_str} L30d on {bet['stat_category']} {bet['bet_side']}\n"
                f"🎯 Matchup: {archetype} vs {scheme_note} → {match_grade}\n"
                f"🦓 Ref: {ref_bias_note}"
            )
            
            dossier[gid]['players'][pname] = player_signal[:MAX_PLAYER_SIGNAL_CHARS]

    # Save to cache
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_path = CACHE_DIR / f"game_dossier_{run_date}.json"
    try:
        with open(cache_path, 'w') as f:
            json.dump(dossier, f)
    except Exception as e:
        print(f"Error saving dossier cache: {e}")

    return dossier
