#!/usr/bin/env python
"""
audit_roster.py - Archetype Census (Player Classification Audit)

Purpose:
Query ludi.db for 2025-26 season averages, classify every player using Module E,
and generate a report to verify if tags (Slasher, Sniper, etc.) match reality.
"""

import sqlite3
import argparse
from collections import defaultdict
from module_e import LudiCalibrator

class ArchetypeAuditor:
    def __init__(self):
        self.calib = LudiCalibrator()
        self.db_path = 'ludi.db'
        self.season_start = '2025-10-21'

    def fetch_player_averages(self, limit=300, days=None):
        """
        Fetch season averages for top players by minutes.
        If days is provided, fetches stats for the last N days.
        """
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        date_clause = f"game_date >= '{self.season_start}'"
        if days:
            date_clause = f"game_date >= date('now', '-{days} days')"

        query = f"""
        SELECT 
            player_name,
            team_abbreviation,
            AVG(pts) as avg_pts,
            AVG(reb) as avg_reb,
            AVG(ast) as avg_ast,
            AVG(fg3m) as avg_3pm,
            AVG(stl) as avg_stl,
            AVG(blk) as avg_blk,
            AVG(minutes) as avg_min,
            AVG(fga) as avg_fga,
            AVG(fta) as avg_fta,
            AVG(tov) as avg_tov,
            COUNT(*) as games_played
        FROM player_game_logs
        WHERE {date_clause}
        GROUP BY player_name, team_abbreviation
        HAVING COUNT(*) >= {3 if days else 10}
        ORDER BY AVG(minutes) DESC
        LIMIT ?
        """
        
        c.execute(query, (limit,))
        data = c.fetchall()
        conn.close()
        return data

    def calculate_usage(self, fga, fta, tov, mins):
        if mins <= 0: return 0.0
        # Simple Usage Estimate: (Possessions Used / Minutes) / Team Pace Factor (~2.1)
        possessions = fga + (0.44 * fta) + tov
        return round((possessions / mins) / 2.1, 3)

    def validate_tag(self, archetype, stats):
        """
        Returns a warning string if the stats don't pass a "smell test" for the tag.
        """
        warnings = []
        pts = stats['base_pts']
        reb = stats['base_reb']
        ast = stats['base_ast']
        tpm = stats['base_3pm']
        usg = stats['base_usg']

        if archetype == "SNIPER_ELITE" and tpm < 2.0:
            warnings.append(f"Low 3PM ({tpm:.1f})")

        if archetype == "ROLL_MAN" and reb < 6.0:
            warnings.append(f"Low REB ({reb:.1f})")

        if archetype == "HELIOCENTRIC_MAESTRO" and usg < 0.25:
            warnings.append(f"Low USG ({usg:.2f})")

        if archetype == "SLASHING_CREATOR" and pts < 18.0:
            warnings.append(f"Low PTS ({pts:.1f})")

        if archetype == "FACILITATOR" and ast < 4.0:
            warnings.append(f"Low AST ({ast:.1f})")

        return ", ".join(warnings)

    def run_census(self):
        print("\n" + "="*60)
        print("🕵️  LUDI ARCHETYPE CENSUS (2025-26 SEASON)")
        print(f"    Since: {self.season_start} | Top 300 Players")
        print("    Feature: Trend Watch (Last 15 Days) + Secondary Archetypes")
        print("="*60)

        # 1. Fetch Recent Data (Trend Baseline)
        recent_data = self.fetch_player_averages(limit=350, days=15)
        recent_map = {}
        for row in recent_data:
            (name, team, pts, reb, ast, tpm, stl, blk, mins, fga, fta, tov, games) = row
            usg = self.calculate_usage(fga or 0, fta or 0, tov or 0, mins or 0)
            pkt = {'name': name, 'base_pts': pts, 'base_reb': reb, 'base_ast': ast, 
                   'base_3pm': tpm, 'base_stl': stl, 'base_blk': blk, 'base_usg': usg}
            arch, _ = self.calib._assign_archetype(pkt)
            recent_map[name] = arch

        # 2. Fetch Season Data
        raw_data = self.fetch_player_averages()
        census = defaultdict(list)
        
        for row in raw_data:
            (name, team, pts, reb, ast, tpm, stl, blk, mins, fga, fta, tov, games) = row
            
            # Build Player Packet
            usg = self.calculate_usage(fga or 0, fta or 0, tov or 0, mins or 0)
            
            player_packet = {
                'name': name,
                'team': team,
                'base_pts': pts or 0,
                'base_reb': reb or 0,
                'base_ast': ast or 0,
                'base_3pm': tpm or 0,
                'base_stl': stl or 0,
                'base_blk': blk or 0,
                'base_min': mins or 0,
                'base_usg': usg
            }
            
            # Assign Archetype (Primary + Secondary)
            archetype, secondary = self.calib._assign_archetype(player_packet)
            
            # Validate
            warning = self.validate_tag(archetype, player_packet)
            
            # Trend Check
            trend_note = ""
            recent_arch = recent_map.get(name)
            if recent_arch and recent_arch != archetype:
                trend_note = f" (Trending: ➚ {recent_arch})"

            # Store
            entry = {
                'name': name,
                'team': team,
                'stats': player_packet,
                'secondary': secondary,
                'warning': warning,
                'trend': trend_note
            }
            census[archetype].append(entry)

        # 3. Print Report
        total_players = sum(len(v) for v in census.values())
        sorted_keys = sorted(census.keys())
        
        for arch in sorted_keys:
            players = census[arch]
            count = len(players)
            pct = (count / total_players) * 100
            
            print(f"\n🏷️  {arch} ({count} players | {pct:.1f}%)")
            print("-" * 75)
            
            # Sort players by key stat
            if arch in ['SNIPER_ELITE', 'STRETCH_BIG', 'ISO_ASSASSIN']:
                players.sort(key=lambda x: x['stats']['base_3pm'], reverse=True)
                stat_fmt = "3PM: {base_3pm:.1f} | PTS: {base_pts:.1f}"
            elif arch in ['ROLL_MAN', 'HUB_BIG', 'JUMBO_FACILITATOR']:
                players.sort(key=lambda x: x['stats']['base_reb'], reverse=True)
                stat_fmt = "REB: {base_reb:.1f} | AST: {base_ast:.1f}"
            elif arch in ['HELIOCENTRIC_MAESTRO', 'FACILITATOR']:
                players.sort(key=lambda x: x['stats']['base_ast'], reverse=True)
                stat_fmt = "AST: {base_ast:.1f} | USG: {base_usg:.2f}"
            else: # GENERALIST, TWO_LEVEL_SCORER, SLASHING_CREATOR
                players.sort(key=lambda x: x['stats']['base_pts'], reverse=True)
                stat_fmt = "PTS: {base_pts:.1f} | 3PM: {base_3pm:.1f}"

            for p in players:
                stats_str = stat_fmt.format(**p['stats'])
                sec_str = f" / {p['secondary']}" if p['secondary'] else ""
                warn_str = f" ⚠️ {p['warning']}" if p['warning'] else ""
                
                # Format: Name (Team) | Stats [Secondary] (Trend)
                print(f"   {p['name']:<20} ({p['team']}) | {stats_str:<22}{sec_str:<18}{p['trend']}")

if __name__ == "__main__":
    auditor = ArchetypeAuditor()
    auditor.run_census()
