"""
Smart Blowout Tax Utility

Context-aware blowout tax calculator that considers:
- Favorite vs underdog status
- Starter vs bench player
- Game spread magnitude
- Base minutes per game

Replaces old flat blowout tax that double-taxed in Module E + F.

Tax logic:
- Favorites get taxed (starts at 10+ spread)
- Underdogs get neutral/boosted (bench gets boost in blowouts)
- Bench gets +boost in massive blowouts (starters rest early)
- Tax kicks in at 10+ points, scales up with spread

Author: Ludi Informatio
Date: January 2026
"""

import argparse
import sys


def calculate_blowout_tax(spread: float, is_favorite: bool, is_starter: bool, base_min: float) -> float:
    """
    Calculate context-aware blowout tax multiplier.
    
    Args:
        spread: Point spread (positive = favorite, negative = underdog)
        is_favorite: True if player's team is favored
        is_starter: True if player is starter (base_min >= 28)
        base_min: Player's average minutes per game
        
    Returns:
        Multiplier (1.0 = no tax, 0.9 = -10% tax, 1.1 = +10% boost)
        
    Examples:
        Favorite starter, 15-point spread: 0.90 (-10% tax)
        Favorite bench, 15-point spread: 1.05 (+5% boost - garbage time)
        Underdog starter, 15-point spread: 1.00 (neutral - keep fighting)
        Underdog bench, 15-point spread: 1.00 (neutral)
    """
    abs_spread = abs(spread)
    
    # No tax for close games (<10 points)
    if abs_spread < 10.0:
        return 1.0
    
    # Calculate tax magnitude based on spread
    # 10 points = 0%, 15 points = -10%/-5%, 20 points = -20%/-10%
    spread_tax = (abs_spread - 10.0) * 0.02  # 2% per point over 10
    
    # Favorites (team expected to win big)
    if is_favorite:
        if is_starter:
            # Starters sit early in blowouts
            # 10pt: 0%, 15pt: -10%, 20pt: -20%, 25pt: -30%
            return max(0.7, 1.0 - spread_tax)  # Floor at 70% (30% max tax)
        else:
            # Bench gets garbage time
            # 10pt: 0%, 15pt: +5%, 20pt: +10%, 25pt: +15%
            return min(1.2, 1.0 + (spread_tax * 0.5))  # Cap at 120% (20% max boost)
    
    # Underdogs (team expected to lose big)
    else:
        if is_starter:
            # Starters keep fighting - no tax
            return 1.0
        else:
            # Bench neutral (may get garbage time but team losing)
            return 1.0


def generate_tax_table() -> str:
    """
    Generate formatted table showing tax rates for different scenarios.
    
    Returns:
        Markdown-formatted table string
    """
    spreads = [5, 10, 12, 15, 18, 20, 25]
    scenarios = [
        ("Favorite Starter", True, True, 32.0),
        ("Favorite Bench", True, False, 18.0),
        ("Underdog Starter", False, True, 32.0),
        ("Underdog Bench", False, False, 18.0),
    ]
    
    # Table header
    lines = [
        "",
        "Smart Blowout Tax Table",
        "=" * 80,
        "",
    ]
    
    # Spread row
    spread_row = "Spread    |" + "|".join(f" {s:>3}pt " for s in spreads) + "|"
    lines.append(spread_row)
    lines.append("-" * len(spread_row))
    
    # Scenario rows
    for scenario_name, is_fav, is_start, base_min in scenarios:
        row_values = []
        for spread in spreads:
            tax = calculate_blowout_tax(spread, is_fav, is_start, base_min)
            pct_change = (tax - 1.0) * 100
            
            # Color code: negative = red (tax), positive = green (boost), zero = white
            if pct_change < 0:
                row_values.append(f"{pct_change:>+5.0f}%")
            elif pct_change > 0:
                row_values.append(f"{pct_change:>+5.0f}%")
            else:
                row_values.append("   0% ")
        
        row = f"{scenario_name:<14}|" + "|".join(f" {val} " for val in row_values) + "|"
        lines.append(row)
    
    lines.append("")
    lines.append("Legend:")
    lines.append("  Negative % = Tax (volume reduction)")
    lines.append("  Positive % = Boost (garbage time opportunity)")
    lines.append("  0% = Neutral (no adjustment)")
    lines.append("")
    
    return "\n".join(lines)


def main():
    """CLI entry point for testing and demonstration."""
    parser = argparse.ArgumentParser(
        description="Calculate smart blowout tax for NBA props",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Show tax table for all scenarios
  python blowout_tax.py --table
  
  # Calculate tax for specific scenario
  python blowout_tax.py --spread 15 --favorite --starter --minutes 32
  python blowout_tax.py --spread -12 --minutes 18
  
Interpretation:
  - Multiplier < 1.0: Tax applied (reduce projections)
  - Multiplier > 1.0: Boost applied (increase projections)
  - Multiplier = 1.0: Neutral (no adjustment)
        """
    )
    
    parser.add_argument('--table', action='store_true',
                        help='Display full tax table')
    parser.add_argument('--spread', type=float,
                        help='Point spread (positive = favorite, negative = underdog)')
    parser.add_argument('--favorite', action='store_true',
                        help='Player is on favored team')
    parser.add_argument('--starter', action='store_true',
                        help='Player is a starter')
    parser.add_argument('--minutes', type=float, default=25.0,
                        help='Player base minutes per game (default: 25.0)')
    
    args = parser.parse_args()
    
    # Display table
    if args.table:
        print(generate_tax_table())
        return
    
    # Calculate specific scenario
    if args.spread is None:
        print("Error: --spread required (or use --table)")
        parser.print_help()
        sys.exit(1)
    
    # Determine if favorite based on spread sign
    if args.spread > 0:
        is_favorite = True
        spread_display = f"+{args.spread}"
    else:
        is_favorite = False
        spread_display = str(args.spread)
    
    # Override if --favorite flag explicitly set
    if args.favorite:
        is_favorite = True
    
    # Determine if starter based on minutes
    is_starter = args.starter or args.minutes >= 28.0
    
    # Calculate tax
    tax = calculate_blowout_tax(args.spread, is_favorite, is_starter, args.minutes)
    pct_change = (tax - 1.0) * 100
    
    # Display result
    print("\nBlowout Tax Calculation")
    print("=" * 60)
    print(f"Spread:       {spread_display} ({'Favorite' if is_favorite else 'Underdog'})")
    print(f"Role:         {'Starter' if is_starter else 'Bench'} ({args.minutes:.1f} mpg)")
    print(f"Multiplier:   {tax:.3f}")
    print(f"Impact:       {pct_change:+.1f}%")
    print()
    
    if tax < 1.0:
        print(f"💡 Interpretation: {abs(pct_change):.0f}% volume reduction (starters sit early)")
    elif tax > 1.0:
        print(f"💡 Interpretation: {pct_change:.0f}% volume boost (garbage time opportunity)")
    else:
        print("💡 Interpretation: No adjustment (competitive game or underdog fighting)")
    print()


if __name__ == "__main__":
    main()
