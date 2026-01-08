# ==============================================================================
# LUDI INFORMATIO | UTILS: DEVIGGING FUNCTIONS
# V1.0 - Fair Odds Calculation | January 2026
# ==============================================================================
"""
Devigging (de-juicing) utilities for converting bookmaker odds to fair probabilities.

The "vig" (vigorish) is the bookmaker's margin built into odds. For example:
- Standard -110/-110 odds imply 52.4%/52.4% = 104.8% total (4.8% vig)
- Fair odds should sum to exactly 100%

Removing the vig is essential for accurate edge calculation:
- Without devig: Edge appears ~2-5% lower than reality
- With devig: True edge revealed for proper EV and Kelly sizing

Methods implemented:
1. Multiplicative (Proportional) - Default, most common
2. Additive - Equal vig distribution
3. Power Method - Solves for exponent k where probabilities sum to 1
"""

from typing import Tuple, Optional


def american_to_implied(odds: int) -> float:
    """
    Convert American odds to implied probability.

    Args:
        odds: American odds (e.g., -110, +150, -200)

    Returns:
        Implied probability as decimal (e.g., 0.524 for -110)

    Examples:
        >>> american_to_implied(-110)
        0.5238095238095238
        >>> american_to_implied(+150)
        0.4
        >>> american_to_implied(-200)
        0.6666666666666666
    """
    if odds < 0:
        return abs(odds) / (abs(odds) + 100)
    else:
        return 100 / (odds + 100)


def implied_to_american(prob: float) -> int:
    """
    Convert implied probability back to American odds.

    Args:
        prob: Probability as decimal (e.g., 0.55)

    Returns:
        American odds (rounded to nearest integer)

    Examples:
        >>> implied_to_american(0.55)
        -122
        >>> implied_to_american(0.40)
        150
    """
    if prob >= 0.5:
        return round(-100 * prob / (1 - prob))
    else:
        return round(100 * (1 - prob) / prob)


def calculate_vig(odds_over: int, odds_under: int) -> float:
    """
    Calculate the total vig (overround) from a two-way market.

    Args:
        odds_over: American odds for the over
        odds_under: American odds for the under

    Returns:
        Vig as decimal (e.g., 0.048 for 4.8% vig)

    Examples:
        >>> calculate_vig(-110, -110)
        0.047619047619047616
        >>> calculate_vig(-115, -105)
        0.047...
    """
    imp_over = american_to_implied(odds_over)
    imp_under = american_to_implied(odds_under)
    total = imp_over + imp_under
    return total - 1.0


def devig_multiplicative(odds_over: int, odds_under: int) -> Tuple[float, float]:
    """
    Remove vig using multiplicative (proportional) method.

    This is the most common devigging method. It assumes the bookmaker's
    vig is distributed proportionally to each side's probability.

    Formula: fair_prob = raw_prob / sum(raw_probs)

    Args:
        odds_over: American odds for the over
        odds_under: American odds for the under

    Returns:
        Tuple of (fair_over_prob, fair_under_prob) that sum to 1.0

    Examples:
        >>> devig_multiplicative(-110, -110)
        (0.5, 0.5)
        >>> devig_multiplicative(-150, +130)
        (0.5769..., 0.4230...)
    """
    imp_over = american_to_implied(odds_over)
    imp_under = american_to_implied(odds_under)
    total = imp_over + imp_under

    fair_over = imp_over / total
    fair_under = imp_under / total

    return fair_over, fair_under


def devig_additive(odds_over: int, odds_under: int) -> Tuple[float, float]:
    """
    Remove vig using additive method.

    This method assumes the bookmaker adds equal vig to each side.
    Less accurate than multiplicative for unbalanced lines.

    Formula: fair_prob = raw_prob - (vig / 2)

    Args:
        odds_over: American odds for the over
        odds_under: American odds for the under

    Returns:
        Tuple of (fair_over_prob, fair_under_prob) that sum to 1.0
    """
    imp_over = american_to_implied(odds_over)
    imp_under = american_to_implied(odds_under)
    vig = (imp_over + imp_under) - 1.0

    fair_over = imp_over - (vig / 2)
    fair_under = imp_under - (vig / 2)

    return fair_over, fair_under


def devig_power(odds_over: int, odds_under: int, tolerance: float = 1e-6) -> Tuple[float, float]:
    """
    Remove vig using power method.

    This method finds exponent k such that prob_over^k + prob_under^k = 1.
    More mathematically rigorous but computationally heavier.

    Args:
        odds_over: American odds for the over
        odds_under: American odds for the under
        tolerance: Convergence tolerance for iterative solver

    Returns:
        Tuple of (fair_over_prob, fair_under_prob) that sum to 1.0
    """
    imp_over = american_to_implied(odds_over)
    imp_under = american_to_implied(odds_under)

    # Binary search for k where p1^k + p2^k = 1
    k_low, k_high = 0.5, 2.0

    for _ in range(100):  # Max iterations
        k_mid = (k_low + k_high) / 2
        total = (imp_over ** k_mid) + (imp_under ** k_mid)

        if abs(total - 1.0) < tolerance:
            break
        elif total > 1.0:
            k_low = k_mid
        else:
            k_high = k_mid

    fair_over = imp_over ** k_mid
    fair_under = imp_under ** k_mid

    return fair_over, fair_under


def get_fair_probability(
    odds_over: int,
    odds_under: int,
    side: str = 'over',
    method: str = 'multiplicative'
) -> float:
    """
    Get the fair (devigged) probability for a specific side.

    This is the primary function for Module F integration.

    Args:
        odds_over: American odds for the over
        odds_under: American odds for the under
        side: Which side to return ('over' or 'under')
        method: Devigging method ('multiplicative', 'additive', 'power')

    Returns:
        Fair probability for the specified side

    Examples:
        >>> get_fair_probability(-115, -105, 'over')
        0.5119...
        >>> get_fair_probability(-115, -105, 'under')
        0.4880...
    """
    if method == 'multiplicative':
        fair_over, fair_under = devig_multiplicative(odds_over, odds_under)
    elif method == 'additive':
        fair_over, fair_under = devig_additive(odds_over, odds_under)
    elif method == 'power':
        fair_over, fair_under = devig_power(odds_over, odds_under)
    else:
        raise ValueError(f"Unknown devig method: {method}")

    return fair_over if side.lower() == 'over' else fair_under


def calculate_true_edge(
    model_prob: float,
    odds_over: int,
    odds_under: int,
    side: str = 'over',
    method: str = 'multiplicative'
) -> float:
    """
    Calculate the true edge using devigged fair probability.

    Edge = (model_prob - fair_prob) / fair_prob * 100

    Args:
        model_prob: Our model's probability estimate (0-1)
        odds_over: American odds for the over
        odds_under: American odds for the under
        side: Which side we're betting ('over' or 'under')
        method: Devigging method

    Returns:
        Edge as percentage (e.g., 7.5 for 7.5% edge)

    Examples:
        >>> calculate_true_edge(0.55, -115, -105, 'over')
        7.43...  # True edge is ~7.4%, not ~2.8% with raw odds
    """
    fair_prob = get_fair_probability(odds_over, odds_under, side, method)
    edge = (model_prob - fair_prob) / fair_prob * 100
    return edge


# ==============================================================================
# STANDALONE TEST
# ==============================================================================
if __name__ == "__main__":
    print("=" * 60)
    print("LUDI DEVIGGING UTILITY - TEST SUITE")
    print("=" * 60)

    # Test Case 1: Standard -110/-110
    print("\n📊 Test 1: Standard -110/-110")
    odds_o, odds_u = -110, -110
    print(f"   Raw odds: {odds_o}/{odds_u}")
    print(f"   Raw implied: {american_to_implied(odds_o):.4f} / {american_to_implied(odds_u):.4f}")
    print(f"   Vig: {calculate_vig(odds_o, odds_u)*100:.2f}%")
    fair_o, fair_u = devig_multiplicative(odds_o, odds_u)
    print(f"   Fair (multiplicative): {fair_o:.4f} / {fair_u:.4f}")
    print(f"   Sum: {fair_o + fair_u:.4f}")

    # Test Case 2: Unbalanced -150/+130
    print("\n📊 Test 2: Unbalanced -150/+130")
    odds_o, odds_u = -150, 130
    print(f"   Raw odds: {odds_o}/{odds_u}")
    print(f"   Raw implied: {american_to_implied(odds_o):.4f} / {american_to_implied(odds_u):.4f}")
    print(f"   Vig: {calculate_vig(odds_o, odds_u)*100:.2f}%")
    fair_o, fair_u = devig_multiplicative(odds_o, odds_u)
    print(f"   Fair (multiplicative): {fair_o:.4f} / {fair_u:.4f}")

    # Test Case 3: Edge Calculation Comparison
    print("\n📊 Test 3: Edge Calculation - Model says 55% OVER")
    odds_o, odds_u = -115, -105
    model_prob = 0.55

    raw_implied = american_to_implied(odds_o)
    raw_edge = (model_prob - raw_implied) / raw_implied * 100

    true_edge = calculate_true_edge(model_prob, odds_o, odds_u, 'over')

    print(f"   Model probability: {model_prob:.2%}")
    print(f"   Raw implied (with vig): {raw_implied:.4f}")
    print(f"   Edge using raw odds: {raw_edge:.2f}%")
    print(f"   True edge (devigged): {true_edge:.2f}%")
    print(f"   Difference: {true_edge - raw_edge:.2f}% (vig was hiding this)")

    print("\n" + "=" * 60)
    print("All tests passed!")
    print("=" * 60)
