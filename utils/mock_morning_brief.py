from utils.render_full_report import create_briefing_card

# Mock Data representing a "Morning Brief" (Aggregated Top Plays)
# We hijack the 'matchup' field to create Section Headers

mock_morning_data = [
    # --- SECTION 1: DIAMOND TIER (The Lock List) ---
    {
        "matchup": "💎 DIAMOND TIER (Top Edge)", 
        "name": "Jamal Murray (DEN)",
        "bet_on": "OVER",
        "line": 8.5,
        "stat": "AST",
        "proj": 13.4,
        "ev": 90,
        "note": "🚀 VACUUM: Jokic OUT"
    },
    {
        "matchup": "💎 DIAMOND TIER (Top Edge)",
        "name": "Jalen Williams (OKC)",
        "bet_on": "UNDER",
        "line": 24.5,
        "stat": "PTS",
        "proj": 15.6,
        "ev": 82,
        "tags": "[\"📉 Blowout\"]"
    },
    {
        "matchup": "💎 DIAMOND TIER (Top Edge)", 
        "name": "Giannis Antetokounmpo",
        "bet_on": "UNDER",
        "line": 30.5,
        "stat": "PTS",
        "proj": 24.7,
        "ev": 64,
        "note": "⚖️ Ref Drag (-1.5x)"
    },

    # --- SECTION 2: SGP OPPORTUNITY (High Correlation) ---
    {
        "matchup": "🔥 CORRELATED SET (UTA @ CLE)",
        "name": "Donovan Mitchell",
        "bet_on": "OVER",
        "line": 28.5,
        "stat": "PTS",
        "proj": 33.0,
        "ev": 18,
        "note": "Game Stack w/ Mobley"
    },
    {
        "matchup": "🔥 CORRELATED SET (UTA @ CLE)",
        "name": "Evan Mobley",
        "bet_on": "OVER",
        "line": 10.5,
        "stat": "REB",
        "proj": 12.1,
        "ev": 15,
        "note": ""
    }
]

if __name__ == "__main__":
    print("Generating Morning Brief Mockup...")
    output = create_briefing_card(mock_morning_data)
    print(f"✅ Generated: {output}")
