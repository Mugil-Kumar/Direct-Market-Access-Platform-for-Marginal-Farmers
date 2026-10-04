"""Supply Rescue engine.

Finds replacement supply for a failed/short shipment without silently
pretending the original plan succeeded.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping, Optional


@dataclass
class RescueCandidate:
    supply_id: str
    farmer_id: str
    quantity_kg: float
    price_per_kg: float
    quality: str
    distance_km: float
    compatibility_score: float
    reason: str


@dataclass
class SupplyRescuePlan:
    original_quantity_kg: float
    shortfall_kg: float
    recovered_quantity_kg: float
    recovery_ratio: float
    recovered: bool
    replacement_supply_ids: list[str] = field(default_factory=list)
    candidates: list[RescueCandidate] = field(default_factory=list)
    explanation: str = ""


def _quality_rank(value: Any) -> int:
    return {
        "premium": 4, "a": 3, "grade_a": 3,
        "standard": 2, "b": 2, "grade_b": 2,
        "basic": 1, "c": 1, "grade_c": 1,
    }.get(str(value or "").strip().lower(), 0)


def rescue_supply(
    original_quantity_kg: float,
    current_available_quantity_kg: float,
    replacement_supplies: Iterable[Any],
    *,
    crop: Optional[str] = None,
    required_quality: Optional[str] = None,
    max_price_per_kg: Optional[float] = None,
    max_distance_km: Optional[float] = None,
    reliability_by_farmer: Mapping[str, float] | None = None,
) -> SupplyRescuePlan:
    if original_quantity_kg < 0 or current_available_quantity_kg < 0:
        raise ValueError("quantities cannot be negative")

    shortfall = max(0.0, original_quantity_kg - current_available_quantity_kg)
    if shortfall <= 1e-9:
        return SupplyRescuePlan(
            original_quantity_kg, 0.0, 0.0, 1.0, True, [], [], "No rescue was required."
        )

    reliability_by_farmer = reliability_by_farmer or {}
    candidates: list[RescueCandidate] = []

    for supply in replacement_supplies:
        qty = max(0.0, float(getattr(supply, "quantity_kg", 0.0)))
        price = max(0.0, float(getattr(supply, "expected_price_per_kg", 0.0)))
        distance = max(0.0, float(getattr(supply, "distance_km", 0.0)))
        status = str(getattr(supply, "status", "available") or "").lower()
        quality = str(getattr(supply, "quality", "") or "")
        farmer = str(getattr(supply, "farmer_id", "") or "")
        supply_crop = str(getattr(supply, "crop", "") or "")

        if qty <= 0 or status not in {"available", "open", "ready"}:
            continue
        if crop and supply_crop.lower() != crop.lower():
            continue
        if required_quality and _quality_rank(quality) < _quality_rank(required_quality):
            continue
        if max_price_per_kg is not None and price > max_price_per_kg:
            continue
        if max_distance_km is not None and distance > max_distance_km:
            continue

        reliability = max(0.0, min(1.0, float(reliability_by_farmer.get(farmer, 0.75))))
        price_score = 1.0 if max_price_per_kg in (None, 0) else max(0.0, 1.0 - price / max_price_per_kg)
        distance_score = 1.0 if max_distance_km in (None, 0) else max(0.0, 1.0 - distance / max_distance_km)
        quality_score = min(1.0, _quality_rank(quality) / 4.0)

        score = 0.35 * reliability + 0.25 * price_score + 0.20 * distance_score + 0.20 * quality_score
        candidates.append(
            RescueCandidate(
                str(getattr(supply, "id", "") or ""),
                farmer,
                qty,
                price,
                quality,
                distance,
                round(score, 6),
                "Compatible replacement candidate.",
            )
        )

    candidates.sort(key=lambda x: (-x.compatibility_score, x.price_per_kg, x.distance_km, x.supply_id))

    remaining = shortfall
    chosen: list[str] = []
    recovered = 0.0
    for candidate in candidates:
        if remaining <= 1e-9:
            break
        take = min(candidate.quantity_kg, remaining)
        recovered += take
        remaining -= take
        chosen.append(candidate.supply_id)

    ratio = recovered / shortfall if shortfall else 1.0
    success = recovered + 1e-9 >= shortfall
    explanation = (
        f"Recovered {recovered:.3f} kg of {shortfall:.3f} kg shortfall."
        if success
        else f"Only {recovered:.3f} kg of {shortfall:.3f} kg shortfall could be rescued."
    )

    return SupplyRescuePlan(
        original_quantity_kg=round(original_quantity_kg, 3),
        shortfall_kg=round(shortfall, 3),
        recovered_quantity_kg=round(recovered, 3),
        recovery_ratio=round(ratio, 4),
        recovered=success,
        replacement_supply_ids=chosen,
        candidates=candidates,
        explanation=explanation,
    )
