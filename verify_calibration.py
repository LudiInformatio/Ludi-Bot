#!/usr/bin/env python
"""
verify_calibration.py - Module E Verification Tests
Tests archetype matchups, blowout tax, and yak integration

Run: ./venv/bin/python verify_calibration.py
"""

from module_e import LudiCalibrator

def print_comparison(title, before, after, keys):
    """Pretty print before/after comparison"""
    print(f"\n{'='*50}")
    print(f"📋 {title}")
    print(f"{'='*50}")
    
    print(f"\n{'Stat':<15} {'Before':>10} {'After':>10} {'Change':>10}")
    print("-" * 50)
    
    for key in keys:
        b_val = before.get(key, 0)
        a_val = after.get(key, 0)
        if b_val > 0:
            change_pct = ((a_val - b_val) / b_val) * 100
            change_str = f"{change_pct:+.1f}%"
        else:
            change_str = "N/A"
        print(f"{key:<15} {b_val:>10.2f} {a_val:>10.2f} {change_str:>10}")
    
    print(f"\n📝 Notes: {after.get('notes', 'None')}")
    print(f"🏷️ Archetype: {after.get('archetype', 'Not assigned')}")

def test_slasher_vs_hackers():
    """
    Test Case 1: Slasher vs Hackers Defense
    Expected: +20% FTA, +5% PTS boost, "Foul Drawn Magnet" note
    """
    calib = LudiCalibrator()
    
    # Mock a Slasher player (high points, high usage, low 3PM)
    player = {
        'name': 'Anthony Edwards',
        'team': 'MIN',
        'opponent': 'IND',  # Indiana = HACKERS defense
        'base_pts': 28.0,
        'base_reb': 5.5,
        'base_ast': 5.0,
        'base_3pm': 1.5,  # Low 3PM = Slasher
        'base_usg': 0.32,
        'base_stl': 1.2,
        'base_blk': 0.3,
        'base_min': 36.0,
        'proj_pts': 28.0,
        'proj_reb': 5.5,
        'proj_ast': 5.0,
        'proj_fta': 8.0,  # Key stat to watch
        'proj_3pm': 1.5,
        'proj_min': 36.0,
        'odds': {'spread': 5.0, 'total': 228.0},
        'notes': ''
    }
    
    before = player.copy()
    yak_report = {'status': 'ACTIVE', 'note': ''}
    
    result = calib.calibrate_player(player, yak_report)
    
    print_comparison(
        "TEST 1: Slasher vs Hackers (Edwards @ IND)",
        before, result,
        ['proj_pts', 'proj_fta', 'proj_reb', 'proj_ast']
    )
    
    # Validate
    assert result.get('archetype') == 'SLASHER', f"Expected SLASHER, got {result.get('archetype')}"
    assert 'Foul Drawn Magnet' in result.get('notes', ''), f"Expected 'Foul Drawn Magnet' in notes"
    assert result['proj_fta'] > before['proj_fta'], "Expected FTA boost"
    print("\n✅ TEST 1 PASSED")

def test_blowout_tax():
    """
    Test Case 2: Blowout Tax (High Spread)
    Expected: ~6% reduction in projections when spread > 12.5
    """
    calib = LudiCalibrator()
    
    # Mock a player in blowout scenario
    player = {
        'name': 'LeBron James',
        'team': 'LAL',
        'opponent': 'WAS',  # Big favorites
        'base_pts': 25.0,
        'base_reb': 7.0,
        'base_ast': 8.0,
        'base_3pm': 2.0,
        'base_usg': 0.31,
        'base_stl': 1.0,
        'base_blk': 0.5,
        'base_min': 35.0,  # Key: > 30 min triggers blowout logic
        'proj_pts': 25.0,
        'proj_reb': 7.0,
        'proj_ast': 8.0,
        'proj_fta': 6.0,
        'proj_3pm': 2.0,
        'proj_min': 35.0,
        'odds': {'spread': 15.0, 'total': 225.0},  # 15 point spread = blowout
        'notes': ''
    }
    
    before = player.copy()
    yak_report = {'status': 'ACTIVE', 'note': ''}
    
    result = calib.calibrate_player(player, yak_report)
    
    print_comparison(
        "TEST 2: Blowout Tax (LeBron in 15-pt spread game)",
        before, result,
        ['proj_pts', 'proj_reb', 'proj_ast', 'proj_min']
    )
    
    # Validate: expect ~6% reduction (0.94x factor)
    assert 'Blowout Risk' in result.get('notes', ''), "Expected 'Blowout Risk' in notes"
    assert result['proj_pts'] < before['proj_pts'], "Expected PTS reduction"
    
    # Check approximate 6% reduction
    reduction_pct = (before['proj_pts'] - result['proj_pts']) / before['proj_pts'] * 100
    assert 4 < reduction_pct < 8, f"Expected ~6% reduction, got {reduction_pct:.1f}%"
    print("\n✅ TEST 2 PASSED")

def test_minutes_limit():
    """
    Test Case 3: Minutes Limit (Yak Integration)
    Expected: 25% reduction (0.75x factor)
    """
    calib = LudiCalibrator()
    
    # Mock a player on minutes restriction
    player = {
        'name': 'Kawhi Leonard',
        'team': 'LAC',
        'opponent': 'PHX',
        'base_pts': 24.0,
        'base_reb': 6.0,
        'base_ast': 4.0,
        'base_3pm': 2.0,
        'base_usg': 0.29,
        'base_stl': 1.5,
        'base_blk': 0.4,
        'base_min': 32.0,
        'proj_pts': 24.0,
        'proj_reb': 6.0,
        'proj_ast': 4.0,
        'proj_fta': 5.0,
        'proj_3pm': 2.0,
        'proj_min': 32.0,
        'odds': {'spread': 3.0, 'total': 220.0},
        'notes': ''
    }
    
    before = player.copy()
    yak_report = {'status': 'MINUTES_LIMIT', 'note': 'Load management - 24 min cap'}
    
    result = calib.calibrate_player(player, yak_report)
    
    print_comparison(
        "TEST 3: Minutes Limit (Kawhi on 24-min cap)",
        before, result,
        ['proj_pts', 'proj_reb', 'proj_ast', 'proj_min']
    )
    
    # Validate: expect 25% reduction (0.75x factor)
    assert '15-min Update' in result.get('notes', '') or 'Limit' in result.get('notes', ''), \
        "Expected limit note"
    assert result['proj_pts'] < before['proj_pts'], "Expected PTS reduction"
    
    # Check approximate 25% reduction
    reduction_pct = (before['proj_pts'] - result['proj_pts']) / before['proj_pts'] * 100
    assert 20 < reduction_pct < 30, f"Expected ~25% reduction, got {reduction_pct:.1f}%"
    print("\n✅ TEST 3 PASSED")

def test_stretch_big_vs_paint_pack():
    """
    Bonus Test: Stretch Big vs Paint Pack Defense
    Expected: +15% 3PA/3PM boost
    """
    calib = LudiCalibrator()
    
    player = {
        'name': 'Kristaps Porzingis',
        'team': 'BOS',
        'opponent': 'OKC',  # OKC = PAINT_PACK defense
        'base_pts': 20.0,
        'base_reb': 7.5,  # > 6.5 triggers stretch big
        'base_ast': 2.0,
        'base_3pm': 2.5,  # > 1.8 triggers stretch big
        'base_usg': 0.24,
        'base_stl': 0.5,
        'base_blk': 1.8,
        'base_min': 30.0,
        'proj_pts': 20.0,
        'proj_reb': 7.5,
        'proj_ast': 2.0,
        'proj_fta': 3.0,
        'proj_3pm': 2.5,
        'proj_3pa': 6.0,  # Key stat to watch
        'proj_min': 30.0,
        'odds': {'spread': 4.0, 'total': 230.0},
        'notes': ''
    }
    
    before = player.copy()
    yak_report = {'status': 'ACTIVE', 'note': ''}
    
    result = calib.calibrate_player(player, yak_report)
    
    print_comparison(
        "BONUS: Stretch Big vs Paint Pack (Porzingis @ OKC)",
        before, result,
        ['proj_pts', 'proj_3pm', 'proj_3pa', 'proj_reb']
    )
    
    assert result.get('archetype') == 'STRETCH_BIG', f"Expected STRETCH_BIG, got {result.get('archetype')}"
    assert 'Paint Pack' in result.get('notes', ''), "Expected 'Paint Pack' in notes"
    print("\n✅ BONUS TEST PASSED")


if __name__ == "__main__":
    print("\n" + "="*60)
    print("🔬 MODULE E CALIBRATION VERIFICATION")
    print("="*60)
    
    try:
        test_slasher_vs_hackers()
        test_blowout_tax()
        test_minutes_limit()
        test_stretch_big_vs_paint_pack()
        
        print("\n" + "="*60)
        print("🎉 ALL VERIFICATION TESTS PASSED!")
        print("="*60)
        print("\nS.A.V.A.G.E. Engine calibration is verified and ready.")
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
