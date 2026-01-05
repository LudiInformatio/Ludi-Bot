# JANUARY 1, 2026 - SHARP PRODUCTION TEST
if __name__ == "__main__":
    from module_f import LudiReporter # Assuming your class is in module_f.py
    rep = LudiReporter()
    
    test_slate = [
        {
            "game_id": "MIA_DET_20260101",
            "players": [
                {
                    "name": "Cade Cunningham", "team": "DET",
                    "proj_min": 36, "proj_pts": 28.2, "proj_ast": 10.1,
                    "sportsbook_props": {"pts": 26.5, "ast": 9.5},
                    "notes": "[BALL_HOG] vs MIA Blitz. Detroit #2 Def Advantage."
                },
                {
                    "name": "Jalen Duren", "team": "DET",
                    "proj_min": 33, "proj_pts": 19.5, "proj_oreb": 4.8,
                    "sportsbook_props": {"pts": 18.1, "oreb": 3.5},
                    "notes": "[RIM_RUNNER] vs Miami Small Ball."
                }
            ]
        },
        {
            "game_id": "UTA_LAC_20260101",
            "players": [
                {
                    "name": "James Harden", "team": "LAC",
                    "proj_min": 35, "proj_pts": 24.1, "proj_ast": 9.2,
                    "sportsbook_props": {"pts": 26.1, "ast": 7.9},
                    "notes": "Mismatch vs UTA Funnel. Market overvaluing PTS, undervaluing AST."
                }
            ]
        }
    ]

    print(rep.generate_report(test_slate))