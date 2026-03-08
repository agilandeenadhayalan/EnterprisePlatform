"""
Demo: Dynamic Pricing
=======================

Run: python -m learning.phase_2.src.m10_dynamic_pricing.demo
"""

from .supply_demand import Zone, simulate_day
from .surge import SurgeConfig, SurgeModel, calculate_surge, calculate_fare
from .elasticity import (
    ECONOMY,
    STANDARD,
    PREMIUM,
    simulate_price_change,
    simulate_cross_elasticity,
)


def demo_supply_demand() -> None:
    """Show supply/demand curves over a day."""
    print("\n+------------------------------------------+")
    print("|   Demo: Supply/Demand Over a Day         |")
    print("+------------------------------------------+\n")

    zone = Zone(zone_id="manhattan-midtown", name="Midtown Manhattan",
                base_demand=200, base_supply=150)

    snapshots = simulate_day(zone)

    print(f"  Zone: {zone.name}")
    print(f"  {'Hour':>6} {'Demand':>8} {'Supply':>8} {'Ratio':>7} {'Status':>14}")
    print(f"  {'----':>6} {'------':>8} {'------':>8} {'-----':>7} {'------':>14}")

    for s in snapshots:
        if s.is_undersupplied:
            status = "SURGE"
        elif s.is_oversupplied:
            status = "oversupplied"
        else:
            status = "balanced"
        print(f"  {s.hour:>4}:00 {s.demand:>8.1f} {s.supply:>8.1f} {s.ratio:>7.3f} {status:>14}")


def demo_surge_models() -> None:
    """Compare different surge pricing models."""
    print("\n+------------------------------------------+")
    print("|   Demo: Surge Pricing Models             |")
    print("+------------------------------------------+\n")

    # Test ratios from undersupplied to severe surge
    test_ratios = [0.8, 1.0, 1.2, 1.5, 2.0, 2.5, 3.0, 4.0]

    configs = {
        "Linear":      SurgeConfig(model=SurgeModel.LINEAR, linear_k=1.0),
        "Exponential": SurgeConfig(model=SurgeModel.EXPONENTIAL, exp_k=0.5),
        "Step":        SurgeConfig(model=SurgeModel.STEP),
    }

    print(f"  {'Ratio':>7} | {'Linear':>8} | {'Exponential':>12} | {'Step':>8}")
    print(f"  {'-----':>7} | {'------':>8} | {'-----------':>12} | {'----':>8}")

    for ratio in test_ratios:
        results = {}
        for name, config in configs.items():
            supply = 100.0
            demand = ratio * supply
            results[name] = calculate_surge(demand, supply, config)

        print(f"  {ratio:>7.1f} | {results['Linear']:>7.2f}x | "
              f"{results['Exponential']:>11.2f}x | {results['Step']:>7.2f}x")

    # Show fare impact
    print(f"\n  Fare impact (5km, 15min trip, base=$2.50):")
    for ratio in [1.0, 1.5, 2.0, 3.0]:
        supply, demand = 100, ratio * 100
        surge = calculate_surge(demand, supply, SurgeConfig(model=SurgeModel.LINEAR))
        fare = calculate_fare(2.50, 5.0, 15.0, surge)
        print(f"    Ratio {ratio:.1f}x -> surge {surge:.2f}x -> fare ${fare:.2f}")


def demo_elasticity() -> None:
    """Show how surge pricing affects demand and revenue."""
    print("\n+------------------------------------------+")
    print("|   Demo: Price Elasticity                 |")
    print("+------------------------------------------+\n")

    print("  Effect of 2.0x surge on different vehicle types:\n")
    print(f"  {'Type':>10} | {'Price':>10} | {'Demand':>10} | {'Revenue':>10}")
    print(f"  {'----':>10} | {'-----':>10} | {'------':>10} | {'-------':>10}")

    for vehicle in [ECONOMY, STANDARD, PREMIUM]:
        resp = simulate_price_change(vehicle, surge_multiplier=2.0)
        print(f"  {resp.vehicle_type:>10} | "
              f"${resp.original_price:.0f}->${resp.new_price:.0f} | "
              f"{resp.original_demand:.0f}->{resp.new_demand:.0f} | "
              f"${resp.revenue_before:.0f}->${resp.revenue_after:.0f} ({resp.revenue_change_pct:+.0f}%)")

    print(f"\n  Key insight: Economy (elastic, e=-1.5) LOSES revenue with surge!")
    print(f"  Premium (inelastic, e=-0.3) GAINS revenue because riders stay.")


def demo_cross_elasticity() -> None:
    """Show substitution between vehicle types."""
    print("\n+------------------------------------------+")
    print("|   Demo: Cross-Elasticity (Substitution)  |")
    print("+------------------------------------------+\n")

    print("  Scenario: Standard rides surge to 2.0x")
    print("  Question: How many riders switch to Economy?\n")

    primary_resp, sub_resp = simulate_cross_elasticity(
        primary=STANDARD,
        substitute=ECONOMY,
        cross_elasticity=0.5,   # Positive = substitutes
        primary_surge=2.0,
    )

    print(f"  Standard (surging):")
    print(f"    Price:  ${primary_resp.original_price:.0f} -> ${primary_resp.new_price:.0f} "
          f"({primary_resp.price_change_pct:+.0f}%)")
    print(f"    Demand: {primary_resp.original_demand:.0f} -> {primary_resp.new_demand:.0f} "
          f"({primary_resp.demand_change_pct:+.0f}%)")

    print(f"\n  Economy (absorbing overflow, cross-elasticity=0.5):")
    print(f"    Price:  ${sub_resp.original_price:.0f} (no change)")
    print(f"    Demand: {sub_resp.original_demand:.0f} -> {sub_resp.new_demand:.0f} "
          f"({sub_resp.demand_change_pct:+.0f}%)")
    print(f"    Revenue: ${sub_resp.revenue_before:.0f} -> ${sub_resp.revenue_after:.0f} "
          f"({sub_resp.revenue_change_pct:+.0f}%)")


def main() -> None:
    print("=" * 50)
    print("  Module 10: Dynamic Pricing")
    print("=" * 50)

    demo_supply_demand()
    demo_surge_models()
    demo_elasticity()
    demo_cross_elasticity()

    print("\n[DONE] Module 10 demos complete!\n")


if __name__ == "__main__":
    main()
