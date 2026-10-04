"""Quantity allocation optimizer for AGRIWEAVE."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping, Optional


@dataclass(frozen=True)
class OptimizationConstraints:
    max_price_per_kg: Optional[float] = None
    max_distance_km: Optional[float] = None
    min_quality_score: float = 0.0
    minimum_fill_ratio: float = 0.0
    fairness_weight: float = 0.15
    price_weight: float = 0.30
    quality_weight: float = 0.20
    reliability_weight: float = 0.20
    distance_weight: float = 0.15


@dataclass
class AllocationLine:
    supply_id: str
    farmer_id: str
    quantity_kg: float
    unit_price_per_kg: float
    quality: str
    distance_km: float
    reliability_score: float
    line_score: float


@dataclass
class OptimizationResult:
    requested_quantity_kg: float
    allocated_quantity_kg: float
    shortfall_kg: float
    weighted_price_per_kg: float
    fill_ratio: float
    objective_score: float
    feasible: bool
    allocations: list[AllocationLine] = field(default_factory=list)
    reason: str = ""


def _n(value: Any, default: float = 0.0) -> float:
    try:
        result = float(value)
        return result if result == result else default
    except (TypeError, ValueError):
        return default


def _quality_score(value: Any) -> float:
    raw = str(value or "").strip().lower()
    if raw in {"premium", "a"}:
        return 1.0
    if raw in {"grade_a"}:
        return 0.95
    if raw in {"standard", "b", "grade_b"}:
        return 0.75
    if raw in {"basic", "c", "grade_c"}:
        return 0.55
    try:
        return max(0.0, min(1.0, float(raw)))
    except ValueError:
        return 0.5


def _normalise_weights(rules: OptimizationConstraints) -> tuple[float, float, float, float, float]:
    weights = [
        max(0.0, rules.price_weight),
        max(0.0, rules.quality_weight),
        max(0.0, rules.reliability_weight),
        max(0.0, rules.distance_weight),
        max(0.0, rules.fairness_weight),
    ]
    total = sum(weights)
    if total <= 0:
        return 0.3, 0.2, 0.2, 0.15, 0.15
    return tuple(w / total for w in weights)  # type: ignore[return-value]


def optimize_quantities(
    supplies: Iterable[Any],
    requested_quantity_kg: float,
    constraints: OptimizationConstraints | None = None,
    *,
    reliability_by_farmer: Mapping[str, float] | None = None,
) -> OptimizationResult:
    """Allocate the requested quantity using a deterministic marginal-score heuristic.

    The optimizer maximises service quality while respecting price, quality and
    distance constraints. It deliberately spreads allocation across farmers
    when candidates are otherwise comparable.
    """

    if requested_quantity_kg < 0:
        raise ValueError("requested_quantity_kg cannot be negative")

    rules = constraints or OptimizationConstraints()
    if not 0 <= rules.minimum_fill_ratio <= 1:
        raise ValueError("minimum_fill_ratio must be between 0 and 1")

    reliability_by_farmer = reliability_by_farmer or {}
    candidates: list[Any] = []

    for supply in supplies:
        qty = _n(getattr(supply, "quantity_kg", 0.0))
        price = _n(getattr(supply, "expected_price_per_kg", 0.0))
        distance = _n(getattr(supply, "distance_km", 0.0))
        quality = _quality_score(getattr(supply, "quality", ""))
        if qty <= 0:
            continue
        if rules.max_price_per_kg is not None and price > rules.max_price_per_kg:
            continue
        if rules.max_distance_km is not None and distance > rules.max_distance_km:
            continue
        if quality < rules.min_quality_score:
            continue
        candidates.append(supply)

    if requested_quantity_kg == 0:
        return OptimizationResult(0.0, 0.0, 0.0, 0.0, 1.0, 1.0, True, [], "Zero quantity requested.")

    if not candidates:
        return OptimizationResult(
            requested_quantity_kg, 0.0, requested_quantity_kg, 0.0, 0.0, 0.0,
            False, [], "No supply satisfies the optimization constraints."
        )

    weights = _normalise_weights(rules)
    min_price = min(_n(getattr(s, "expected_price_per_kg", 0.0)) for s in candidates)
    max_price = max(_n(getattr(s, "expected_price_per_kg", 0.0)) for s in candidates)
    max_distance = max(
        max(_n(getattr(s, "distance_km", 0.0)) for s in candidates),
        rules.max_distance_km or 1.0,
    )

    scored: list[tuple[float, Any]] = []
    for supply in candidates:
        price = _n(getattr(supply, "expected_price_per_kg", 0.0))
        quality = _quality_score(getattr(supply, "quality", ""))
        distance = _n(getattr(supply, "distance_km", 0.0))
        farmer = str(getattr(supply, "farmer_id", "") or "")
        reliability = max(0.0, min(1.0, _n(reliability_by_farmer.get(farmer, 0.75), 0.75)))

        price_component = 1.0 if max_price == min_price else 1.0 - (price - min_price) / (max_price - min_price)
        distance_component = 1.0 - min(1.0, distance / max_distance)
        base_score = (
            weights[0] * price_component
            + weights[1] * quality
            + weights[2] * reliability
            + weights[3] * distance_component
        )
        scored.append((base_score, supply))

    # Repeatedly choose the best marginal candidate. A small farmer-share bonus
    # prevents a single supplier from absorbing the whole order.
    allocated_by_farmer: dict[str, float] = {}
    remaining = requested_quantity_kg
    allocations: list[AllocationLine] = []

    while remaining > 1e-9:
        best: tuple[float, Any] | None = None
        for base_score, supply in scored:
            farmer = str(getattr(supply, "farmer_id", "") or "")
            available = _n(getattr(supply, "quantity_kg", 0.0)) - sum(
                line.quantity_kg for line in allocations if line.supply_id == str(getattr(supply, "id", ""))
            )
            if available <= 1e-9:
                continue

            farmer_share = allocated_by_farmer.get(farmer, 0.0) / requested_quantity_kg
            fairness_bonus = 1.0 - min(1.0, farmer_share)
            score = base_score + weights[4] * fairness_bonus
            candidate = (score, supply)
            if best is None or candidate[0] > best[0] or (
                candidate[0] == best[0]
                and str(getattr(candidate[1], "id", "")) < str(getattr(best[1], "id", ""))
            ):
                best = candidate

        if best is None:
            break

        score, supply = best
        supply_id = str(getattr(supply, "id", "") or "")
        farmer_id = str(getattr(supply, "farmer_id", "") or "")
        already = sum(line.quantity_kg for line in allocations if line.supply_id == supply_id)
        available = max(0.0, _n(getattr(supply, "quantity_kg", 0.0)) - already)
        take = min(available, remaining)

        allocations.append(
            AllocationLine(
                supply_id=supply_id,
                farmer_id=farmer_id,
                quantity_kg=round(take, 3),
                unit_price_per_kg=_n(getattr(supply, "expected_price_per_kg", 0.0)),
                quality=str(getattr(supply, "quality", "") or ""),
                distance_km=_n(getattr(supply, "distance_km", 0.0)),
                reliability_score=max(0.0, min(1.0, _n(reliability_by_farmer.get(farmer_id, 0.75), 0.75))),
                line_score=round(score, 6),
            )
        )
        allocated_by_farmer[farmer_id] = allocated_by_farmer.get(farmer_id, 0.0) + take
        remaining -= take

    allocated = sum(x.quantity_kg for x in allocations)
    shortfall = max(0.0, requested_quantity_kg - allocated)
    fill_ratio = allocated / requested_quantity_kg if requested_quantity_kg else 1.0
    weighted_price = (
        sum(x.quantity_kg * x.unit_price_per_kg for x in allocations) / allocated
        if allocated else 0.0
    )
    objective = (
        sum(x.quantity_kg * x.line_score for x in allocations) / allocated
        if allocated else 0.0
    )
    feasible = fill_ratio + 1e-9 >= rules.minimum_fill_ratio

    reason = (
        "Fully allocated within constraints."
        if shortfall <= 1e-9
        else f"Partial allocation; {shortfall:.3f} kg remains after applying constraints."
    )

    return OptimizationResult(
        requested_quantity_kg=requested_quantity_kg,
        allocated_quantity_kg=round(allocated, 3),
        shortfall_kg=round(shortfall, 3),
        weighted_price_per_kg=round(weighted_price, 2),
        fill_ratio=round(fill_ratio, 4),
        objective_score=round(objective, 6),
        feasible=feasible,
        allocations=allocations,
        reason=reason,
    )
