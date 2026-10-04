"""Decision engine comparing individual sale with collective aggregation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Mapping

from .net_realization import RealizationCosts, calculate_realization


@dataclass
class CollectiveDecision:
    individual_net_revenue: float
    collective_net_revenue: float
    collective_gain: float
    collective_gain_percent: float
    individual_net_per_kg: float
    collective_net_per_kg: float
    recommended_mode: str
    reason: str
    participating_farmer_ids: list[str]


def evaluate_collective_sale(
    supplies: Iterable[Any],
    *,
    collective_price_per_kg: float,
    individual_costs: RealizationCosts | None = None,
    collective_costs: RealizationCosts | None = None,
    farmer_cost_overrides: Mapping[str, RealizationCosts] | None = None,
) -> CollectiveDecision:
    items = list(supplies)
    if collective_price_per_kg < 0:
        raise ValueError("collective_price_per_kg cannot be negative")

    overrides = farmer_cost_overrides or {}
    total_quantity = sum(max(0.0, float(getattr(s, "quantity_kg", 0.0))) for s in items)
    if total_quantity <= 0:
        return CollectiveDecision(
            0, 0, 0, 0, 0, 0, "none",
            "No positive supply quantity is available.",
            [],
        )

    individual_total = 0.0
    farmer_ids: list[str] = []
    for supply in items:
        qty = max(0.0, float(getattr(supply, "quantity_kg", 0.0)))
        farmer_id = str(getattr(supply, "farmer_id", "") or "")
        farmer_ids.append(farmer_id)
        result = calculate_realization(
            qty,
            float(getattr(supply, "expected_price_per_kg", 0.0)),
            overrides.get(farmer_id, individual_costs),
        )
        individual_total += result.net_revenue

    collective = calculate_realization(
        total_quantity,
        collective_price_per_kg,
        collective_costs,
    )
    gain = collective.net_revenue - individual_total
    individual_per_kg = individual_total / total_quantity
    collective_per_kg = collective.net_per_kg
    gain_percent = (gain / individual_total * 100) if individual_total else (100.0 if gain > 0 else 0.0)

    if gain > 0.005:
        mode = "collective"
        reason = "Collective sale increases expected net farmer realization."
    elif gain < -0.005:
        mode = "individual"
        reason = "Individual selling preserves more expected net realization."
    else:
        mode = "tie"
        reason = "The two strategies are economically equivalent within the tolerance."

    return CollectiveDecision(
        round(individual_total, 2),
        round(collective.net_revenue, 2),
        round(gain, 2),
        round(gain_percent, 2),
        round(individual_per_kg, 2),
        round(collective_per_kg, 2),
        mode,
        reason,
        sorted(set(farmer_ids)),
    )
