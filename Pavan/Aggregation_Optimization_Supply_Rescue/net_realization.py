"""Farmer net-realization and profitability analysis."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional


@dataclass(frozen=True)
class RealizationCosts:
    transport_per_kg: float = 0.0
    collection_per_kg: float = 0.0
    packaging_per_kg: float = 0.0
    spoilage_percent: float = 0.0
    platform_fee_percent: float = 0.0
    fixed_cost: float = 0.0


@dataclass
class RealizationResult:
    gross_revenue: float
    transport_cost: float
    collection_cost: float
    packaging_cost: float
    spoilage_cost: float
    platform_fee: float
    fixed_cost: float
    total_cost: float
    net_revenue: float
    net_per_kg: float
    effective_sale_quantity_kg: float
    farmer_margin_percent: float


def calculate_realization(
    quantity_kg: float,
    selling_price_per_kg: float,
    costs: RealizationCosts | None = None,
) -> RealizationResult:
    """Calculate transparent farmer economics.

    Spoilage is applied to gross revenue as a value loss and does not mutate
    the physical quantity. This keeps the calculation auditable.
    """

    if quantity_kg < 0 or selling_price_per_kg < 0:
        raise ValueError("quantity and selling price cannot be negative")

    c = costs or RealizationCosts()
    for name, value in vars(c).items():
        if value < 0:
            raise ValueError(f"{name} cannot be negative")
    if c.spoilage_percent > 100 or c.platform_fee_percent > 100:
        raise ValueError("percentage costs cannot exceed 100")

    gross = quantity_kg * selling_price_per_kg
    transport = quantity_kg * c.transport_per_kg
    collection = quantity_kg * c.collection_per_kg
    packaging = quantity_kg * c.packaging_per_kg
    spoilage = gross * c.spoilage_percent / 100.0
    platform_fee = gross * c.platform_fee_percent / 100.0
    total = transport + collection + packaging + spoilage + platform_fee + c.fixed_cost
    net = max(0.0, gross - total)
    effective_qty = quantity_kg * (1.0 - c.spoilage_percent / 100.0)

    return RealizationResult(
        gross_revenue=round(gross, 2),
        transport_cost=round(transport, 2),
        collection_cost=round(collection, 2),
        packaging_cost=round(packaging, 2),
        spoilage_cost=round(spoilage, 2),
        platform_fee=round(platform_fee, 2),
        fixed_cost=round(c.fixed_cost, 2),
        total_cost=round(total, 2),
        net_revenue=round(net, 2),
        net_per_kg=round(net / quantity_kg, 2) if quantity_kg else 0.0,
        effective_sale_quantity_kg=round(effective_qty, 3),
        farmer_margin_percent=round((net / gross) * 100, 2) if gross else 0.0,
    )


def compare_selling_prices(
    quantity_kg: float,
    individual_price_per_kg: float,
    collective_price_per_kg: float,
    individual_costs: RealizationCosts | None = None,
    collective_costs: RealizationCosts | None = None,
) -> dict[str, Any]:
    individual = calculate_realization(quantity_kg, individual_price_per_kg, individual_costs)
    collective = calculate_realization(quantity_kg, collective_price_per_kg, collective_costs)
    gain = collective.net_revenue - individual.net_revenue
    return {
        "individual": individual,
        "collective": collective,
        "collective_gain": round(gain, 2),
        "collective_gain_per_kg": round(gain / quantity_kg, 2) if quantity_kg else 0.0,
        "collective_better": gain > 0.005,
        "decision": "collective" if gain > 0.005 else "individual",
    }
