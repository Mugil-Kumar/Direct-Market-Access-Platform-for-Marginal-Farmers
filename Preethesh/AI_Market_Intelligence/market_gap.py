"""
AGRIWEAVE market-gap intelligence.

Compares buyer demand with available farmer supply and
identifies shortages, surplus, and supply coverage.
"""

from collections import defaultdict
from typing import Any, Dict, List, Optional

from .models import MarketGapResult
from .normalizer import normalize_crop, normalize_quantity


def _get(record: Any, field: str, default: Any = None) -> Any:
    """Read a field from either a dictionary or an object."""
    if isinstance(record, dict):
        return record.get(field, default)

    return getattr(record, field, default)


def calculate_market_gap(
    crop: str,
    demand_quantity_kg: float,
    available_supply_quantity_kg: float,
    demand_count: int = 0,
    supply_count: int = 0,
    location: Optional[str] = None,
) -> MarketGapResult:
    """
    Calculate shortage, surplus, and supply coverage for one crop.
    """

    demand_normalized = normalize_quantity(demand_quantity_kg)
    supply_normalized = normalize_quantity(available_supply_quantity_kg)

    demand = max(float(demand_normalized or 0.0), 0.0)
    supply = max(float(supply_normalized or 0.0), 0.0)

    shortage = max(demand - supply, 0.0)
    surplus = max(supply - demand, 0.0)

    if shortage > 0:
        status = "shortage"
    elif surplus > 0:
        status = "surplus"
    else:
        status = "balanced"

    return MarketGapResult(
        crop=normalize_crop(crop) or "",
        demand_quantity_kg=round(demand, 2),
        available_supply_quantity_kg=round(supply, 2),
        shortage_quantity_kg=round(shortage, 2),
        surplus_quantity_kg=round(surplus, 2),
        demand_count=int(demand_count or 0),
        supply_count=int(supply_count or 0),
        status=status,
        location=location,
        recommended_additional_supply_kg=round(shortage, 2),
    )


def analyze_market_gap(
    demands: List[Any],
    supplies: List[Any],
    location: Optional[str] = None,
) -> List[MarketGapResult]:
    """
    Calculate market gaps for all crops represented in demand or supply.

    Demand and supply records may be dictionaries or shared dataclass
    objects. Records with invalid or missing crops are ignored.
    """

    demand_totals: Dict[str, float] = defaultdict(float)
    supply_totals: Dict[str, float] = defaultdict(float)

    demand_counts: Dict[str, int] = defaultdict(int)
    supply_counts: Dict[str, int] = defaultdict(int)

    for demand in demands or []:
        crop = normalize_crop(_get(demand, "crop"))
        quantity = normalize_quantity(
            _get(demand, "quantity_kg")
        )

        if crop and quantity is not None and quantity > 0:
            demand_totals[crop] += quantity
            demand_counts[crop] += 1

    for supply in supplies or []:
        crop = normalize_crop(_get(supply, "crop"))
        quantity = normalize_quantity(
            _get(supply, "quantity_kg")
        )

        if crop and quantity is not None and quantity > 0:
            supply_totals[crop] += quantity
            supply_counts[crop] += 1

    crops = sorted(
        set(demand_totals) | set(supply_totals)
    )

    return [
        calculate_market_gap(
            crop=crop,
            demand_quantity_kg=demand_totals[crop],
            available_supply_quantity_kg=supply_totals[crop],
            demand_count=demand_counts[crop],
            supply_count=supply_counts[crop],
            location=location,
        )
        for crop in crops
    ]


def get_market_gap(
    demands: List[Any],
    supplies: List[Any],
    location: Optional[str] = None,
) -> List[MarketGapResult]:
    """Alias for analyze_market_gap."""

    return analyze_market_gap(
        demands=demands,
        supplies=supplies,
        location=location,
    )