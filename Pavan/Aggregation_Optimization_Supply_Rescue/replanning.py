"""Dynamic replanning coordinator for AGRIWEAVE."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any, Iterable, Mapping, Optional

from .quantity_optimizer import OptimizationConstraints, optimize_quantities
from .shortfall import detect_shortfall
from .supply_rescue import SupplyRescuePlan, rescue_supply


@dataclass
class ReplanDecision:
    status: str
    action: str
    reason: str
    requested_quantity_kg: float
    replacement_quantity_kg: float
    replacement_supply_ids: list[str] = field(default_factory=list)
    optimization: Any = None
    rescue: Optional[SupplyRescuePlan] = None


def replan_after_disruption(
    requested_quantity_kg: float,
    available_supplies: Iterable[Any],
    *,
    failed_supply_ids: Iterable[str] = (),
    max_price_per_kg: Optional[float] = None,
    max_distance_km: Optional[float] = None,
    required_quality: Optional[str] = None,
    reliability_by_farmer: Mapping[str, float] | None = None,
) -> ReplanDecision:
    """Recalculate an executable plan from current state.

    Failed supply IDs are excluded. The optimizer is run again against the
    current environment, so a disruption becomes a new planning observation.
    """

    failed = {str(x) for x in failed_supply_ids}
    current = [
        s for s in available_supplies
        if str(getattr(s, "id", "") or "") not in failed
    ]

    optimization = optimize_quantities(
        current,
        requested_quantity_kg,
        OptimizationConstraints(
            max_price_per_kg=max_price_per_kg,
            max_distance_km=max_distance_km,
            min_quality_score=(
                {"premium": 1.0, "a": 0.75, "standard": 0.5, "b": 0.5, "basic": 0.25}.get(
                    str(required_quality or "").lower(), 0.0
                )
            ),
            minimum_fill_ratio=0.0,
        ),
        reliability_by_farmer=reliability_by_farmer,
    )

    if optimization.shortfall_kg <= 1e-9:
        return ReplanDecision(
            "replanned",
            "execute_replacement_plan",
            "A complete replacement plan was found from the current state.",
            requested_quantity_kg,
            optimization.allocated_quantity_kg,
            [x.supply_id for x in optimization.allocations],
            optimization,
            None,
        )

    allocated_by_supply = {x.supply_id: x.quantity_kg for x in optimization.allocations}
    residual_supplies = []
    for supply in current:
        sid = str(getattr(supply, "id", "") or "")
        original_qty = max(0.0, float(getattr(supply, "quantity_kg", 0.0)))
        residual_qty = original_qty - allocated_by_supply.get(sid, 0.0)
        if residual_qty <= 1e-9:
            continue
        try:
            residual_supplies.append(replace(supply, quantity_kg=residual_qty))
        except TypeError:
            # Works with non-dataclass project objects too.
            import copy
            residual = copy.copy(supply)
            setattr(residual, "quantity_kg", residual_qty)
            residual_supplies.append(residual)

    rescue = rescue_supply(
        requested_quantity_kg,
        optimization.allocated_quantity_kg,
        residual_supplies,
        max_price_per_kg=max_price_per_kg,
        max_distance_km=max_distance_km,
        required_quality=required_quality,
        reliability_by_farmer=reliability_by_farmer,
    )

    if rescue.recovered:
        return ReplanDecision(
            "replanned",
            "execute_rescue_plan",
            "Primary re-optimization left a gap, and Supply Rescue found enough replacement stock.",
            requested_quantity_kg,
            optimization.allocated_quantity_kg + rescue.recovered_quantity_kg,
            [x.supply_id for x in optimization.allocations] + rescue.replacement_supply_ids,
            optimization,
            rescue,
        )

    return ReplanDecision(
        "infeasible",
        "escalate_shortfall",
        "No feasible replacement plan can currently satisfy the requested quantity.",
        requested_quantity_kg,
        optimization.allocated_quantity_kg + rescue.recovered_quantity_kg,
        [x.supply_id for x in optimization.allocations] + rescue.replacement_supply_ids,
        optimization,
        rescue,
    )
