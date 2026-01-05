import time

def print_sharp_box_score(player_name, sim_results, l10_context, prop_line=None, prop_type="Points", game_context=None):
    """
    LUDI INFORMATIO | MODULE B | SHARP BOX SCORE DISPLAY
    ----------------------------------------------------
    Renders a full projected box score with GAME CONTEXT (Refs, Spread, Total).
    """
    
    # --- 0. HELPER: PROP KEY MAPPER ---
    key_map = {
        "Points": "PTS", "pts": "PTS",
        "Assists": "AST", "ast": "AST",
        "Rebounds": "REB", "reb": "REB",
        "Threes": "FG3M", "threes": "FG3M",
        "Blocks": "BLK", "blocks": "BLK",
        "Steals": "STL", "steals": "STL",
        "Turnovers": "TOV", "turnovers": "TOV"
    }
    target_key = key_map.get(prop_type, "PTS")

    # --- 1. DERIVED CALCULATIONS ---
    proj_stocks = sim_results.get('STL', 0) + sim_results.get('BLK', 0)
    l10_stocks = l10_context.get('STL', 0) + l10_context.get('BLK', 0)

    if 'REB' in sim_results:
        proj_trb = sim_results['REB']
    else:
        proj_trb = sim_results.get('OREB', 0) + sim_results.get('DREB', 0)

    if 'REB' in l10_context:
        l10_trb = l10_context['REB']
    else:
        l10_trb = l10_context.get('OREB', 0) + l10_context.get('DREB', 0)
    
    # Efficiency Calc
    fga = sim_results.get('FGA', 0)
    if fga > 0:
        proj_fg_pct = (sim_results.get('FGM', 0) / fga) * 100
    else:
        proj_fg_pct = 0.0

    l10_fg_pct = l10_context.get('FG_PCT', 0) * 100
    if l10_fg_pct == 0 and l10_context.get('FGA', 0) > 0:
        l10_fg_pct = (l10_context.get('FGM', 0) / l10_context.get('FGA', 1)) * 100

    # --- 2. HEADER: THE "WHY" (GAME CONTEXT) ---
    print("=" * 65)
    print(f"✅ PLAYER ANALYZED: {player_name.upper()}")
    
    # [NEW] GAME CONTEXT BLOCK
    if game_context:
        # Unpack with defaults
        matchup = game_context.get('matchup', 'N/A')
        spread = game_context.get('spread', 'N/A')
        total = game_context.get('total', 'N/A')
        ref_impact = game_context.get('ref_impact', 1.0)
        
        # Format the Impact Badge
        if ref_impact > 1.0:
            ref_badge = f"🔥 HIGH PACE ({ref_impact}x)"
        elif ref_impact < 1.0:
            ref_badge = f"❄️ LOW PACE ({ref_impact}x)"
        else:
            ref_badge = "⚖️ NEUTRAL"

        print(f"   🏟️  GAME: {matchup}")
        print(f"   📊 VEGAS: Spread {spread} | Total {total}")
        print(f"   🦓 REFS:  {ref_badge}")
        print("-" * 65)
    
    # --- 3. THE BET: EDGE ANALYSIS ---
    if prop_line:
        target_proj = sim_results.get(target_key, 0)
        diff = target_proj - prop_line
        edge_direction = "OVER" if diff > 0 else "UNDER"
        
        # Color code the edge (visual only)
        # In a real GUI, you'd use colors, here we use symbols
        strength = "⚡⚡⚡" if abs(diff) > 2.0 else "⚡"
        
        print(f"   🎯 MARKET: {prop_type} | LINE: {prop_line} | PROJ: {target_proj:.2f}")
        print(f"   ⚖️  EDGE:   {edge_direction} by {abs(diff):.2f} {strength}")
    print("-" * 65)

    # --- 4. THE BOX SCORE ---
    print(f"   {'[OFFENSE]':<12} {'PTS':<8} {'AST':<8} {'TOV':<8} {'FGA':<8} {'FG%':<8}")
    print(f"   {'Model Proj':<12} {sim_results.get('PTS', 0):<8.1f} {sim_results.get('AST', 0):<8.1f} "
          f"{sim_results.get('TOV', 0):<8.1f} {sim_results.get('FGA', 0):<8.1f} {proj_fg_pct:<8.1f}")
    print(f"   {'L10 Avg':<12} {l10_context.get('PTS', 0):<8.1f} {l10_context.get('AST', 0):<8.1f} "
          f"{l10_context.get('TOV', 0):<8.1f} {l10_context.get('FGA', 0):<8.1f} {l10_fg_pct:<8.1f}")
    print("-" * 65)

    print(f"   {'[REBOUNDS]':<12} {'ORB':<8} {'DRB':<8} {'TRB':<8}")
    print(f"   {'Model Proj':<12} {sim_results.get('OREB', 0):<8.1f} {sim_results.get('DREB', 0):<8.1f} {proj_trb:<8.1f}")
    print(f"   {'L10 Avg':<12} {l10_context.get('OREB', 0):<8.1f} {l10_context.get('DREB', 0):<8.1f} {l10_trb:<8.1f}")
    print("-" * 65)

    print(f"   {'[DEFENSE]':<12} {'STL':<8} {'BLK':<8} {'STOCKS':<8}")
    print(f"   {'Model Proj':<12} {sim_results.get('STL', 0):<8.1f} {sim_results.get('BLK', 0):<8.1f} {proj_stocks:<8.2f}")
    print(f"   {'L10 Avg':<12} {l10_context.get('STL', 0):<8.1f} {l10_context.get('BLK', 0):<8.1f} {l10_stocks:<8.2f}")
    
    print("=" * 65)
    print("\n")


# --- EXAMPLE USAGE ---
if __name__ == "__main__":
    
    # 1. MOCK DATA 
    module_a_data = {
        'PTS': 24.5, 'AST': 7.2, 'TOV': 3.1, 
        'OREB': 0.8, 'DREB': 6.5, 'REB': 7.3,
        'STL': 1.1, 'BLK': 0.6,
        'FGA': 19.5, 'FG_PCT': 0.485
    }

    engine_results = {
        'PTS': 28.2, 'AST': 8.5, 'TOV': 2.9,
        'OREB': 1.1, 'DREB': 7.1, 
        'STL': 1.5, 'BLK': 0.9,
        'FGA': 22.5, 'FGM': 11.2 
    }
    
    # 2. [NEW] MOCK GAME CONTEXT (From Gatekeeper)
    mock_game = {
        'matchup': "LAL @ GSW",
        'spread': "-2.5",
        'total': "241.5",
        'ref_impact': 1.04 # High Pace Refs
    }

    # 3. RUN DISPLAY
    print("LUDI INFORMATIO: MODULE B (DISPLAY) ONLINE")
    print("   >>> INTEGRATION TEST: FULL CONTEXT CARD")
    time.sleep(1) 
    
    print_sharp_box_score(
        player_name="LeBron James",
        sim_results=engine_results,
        l10_context=module_a_data,
        prop_line=25.5,
        prop_type="Points",
        game_context=mock_game  # <--- Passing the new context
    )