"""
Surge pricing calculator.

Determines the surge multiplier based on the ratio of ride demand
to driver supply in a given zone.

# TODO: Customize the surge formula based on your pricing strategy.
#   - A more aggressive formula ramps up faster, increasing revenue per ride
#     but potentially driving riders to competitors.
#   - A more conservative formula keeps prices stable, retaining riders
#     but potentially under-compensating drivers in high-demand periods.
#
# Consider:
#   - Your market's price sensitivity (urban vs suburban)
#   - Competitor pricing behavior
#   - Regulatory caps on surge pricing (some cities limit to 2x or 3x)
#   - Time-of-day adjustments (airport, events, weather)
#
# The current formula is a balanced default suitable for most markets.
"""


def calculate_surge(demand_count: int, supply_count: int) -> float:
    """
    Calculate surge multiplier from demand/supply counts.

    Args:
        demand_count: Number of ride requests in the zone
        supply_count: Number of available drivers in the zone

    Returns:
        Surge multiplier (minimum 1.0, capped at 5.0)

    Examples:
        - Equal demand/supply → 1.0 (no surge)
        - 2x demand vs supply → ~1.5x surge
        - 5x demand vs supply → ~3.0x surge
        - No supply → max surge (5.0)
    """
    # No demand = no surge
    if demand_count <= 0:
        return 1.0

    # No supply = maximum surge
    if supply_count <= 0:
        return 5.0

    ratio = demand_count / supply_count

    # If demand <= supply, no surge needed
    if ratio <= 1.0:
        return 1.0

    # Logarithmic scaling: surge grows slower as ratio increases
    # This prevents extreme spikes while still incentivizing drivers
    import math
    multiplier = 1.0 + math.log2(ratio)

    # Cap at 5.0x to prevent price gouging
    return round(min(multiplier, 5.0), 2)
