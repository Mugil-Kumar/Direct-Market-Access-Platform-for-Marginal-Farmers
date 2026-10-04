"""AGRIWEAVE supply aggregation engine.

Combines compatible farmer supplies into execution-ready supply groups while
preserving traceability, quality constraints, price ceilings, freshness,
distance, reliability, and farmer-diversification preferences.

No third-party dependencies are required.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from math import inf
from typing import Any, Iterable, Mapping, Optional, Sequence


@dataclass(frozen=True)
class AggregationConstraints:
    """Business rules used when forming an aggregation group."""

    max_price_per_kg: Optional[float] = None
    required_quality: Optional[str] = None
    max_distance_km: Optional[float] = None
    max_age_hours: Optional[float] = None
    max_suppliers: int = 25
    min_supplier_quantity_kg: float = 0.0
    allow_partial_supply: bool = True
    min_group_quantity_kg: float = 0.0


@dataclass
class AggregatedSupply:
    """Execution-ready view of a group of compatible farmer supplies."""

    group_id: str
    crop: str
    location: str
    supply_ids: list[str]
    farmer_ids: list[str]
    total_quantity_kg: float
    weighted_price_per_kg: float
    quality: str
    supplier_count: int
    average_distance_km: float = 0.0
    freshness_score: float = 1.0
    reliability_score: float = 1.0
    concentration_penalty: float = 0.0
    aggregation_score: float = 0.0
    traceability: dict[str, dict[str, Any]] = field(default_factory=dict)


def _text(value: Any) -> str:
    return str(value or "").strip()


def _number(value: Any, default: float = 0.0) -> float:
    try:
        result = float(value)
        return result if result == result else default
    except (TypeError, ValueError):
        return default


def _parse_time(value: Any) -> Optional[datetime]:
    if isinstance(value, datetime):
        dt = value
    elif not value:
        return None
    else:
        raw = str(value).strip().replace("Z", "+00:00")
        try:
            dt = datetime.fromisoformat(raw)
        except ValueError:
            return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _quality_rank(value: str) -> int:
    ranks = {
        "premium": 4,
        "a": 3,
        "grade_a": 3,
        "standard": 2,
        "b": 2,
        "grade_b": 2,
        "basic": 1,
        "c": 1,
    }
    return ranks.get(_text(value).lower(), 0)


def _compatible_quality(actual: str, required: Optional[str]) -> bool:
    if not required:
        return True
    if not actual:
        return False
    return _quality_rank(actual) >= _quality_rank(required)


def _freshness_score(supply: Any, now: datetime) -> float:
    available_from = _parse_time(getattr(supply, "available_from", None))
    available_until = _parse_time(getattr(supply, "available_until", None))
    if not available_from or not available_until:
        return 0.75
    total = max((available_until - available_from).total_seconds(), 1.0)
    remaining = (available_until - now).total_seconds()
    return max(0.0, min(1.0, remaining / total))


def _normalise_location(value: Any) -> str:
    return " ".join(_text(value).lower().split())


def _group_key(supply: Any) -> tuple[str, str, str]:
    return (
        _text(getattr(supply, "crop", "")).lower(),
        _normalise_location(getattr(supply, "location", "")),
        _text(getattr(supply, "quality", "")).lower(),
    )


def _distance_from_group(supply: Any, group: Sequence[Any]) -> float:
    # If a caller has attached a precomputed distance, use it.
    if hasattr(supply, "distance_km"):
        return _number(getattr(supply, "distance_km"), 0.0)
    if not group:
        return 0.0
    values = [_number(getattr(x, "distance_km", 0.0), 0.0) for x in group]
    return sum(values) / len(values)


def aggregate_supplies(
    supplies: Iterable[Any],
    constraints: AggregationConstraints | None = None,
    *,
    reliability_by_farmer: Mapping[str, float] | None = None,
    target_quantity_kg: Optional[float] = None,
    now: Optional[datetime] = None,
) -> list[AggregatedSupply]:
    """Create deterministic compatible aggregation groups.

    Supplies are filtered first, then ordered by price, freshness and
    reliability. Groups are capped by max_suppliers and can stop early once
    target_quantity_kg is satisfied.
    """

    rules = constraints or AggregationConstraints()
    if rules.max_suppliers < 1:
        raise ValueError("max_suppliers must be at least 1")
    if rules.min_supplier_quantity_kg < 0 or rules.min_group_quantity_kg < 0:
        raise ValueError("quantity constraints cannot be negative")
    if target_quantity_kg is not None and target_quantity_kg < 0:
        raise ValueError("target_quantity_kg cannot be negative")

    clock = now or datetime.now(timezone.utc)
    reliability_by_farmer = reliability_by_farmer or {}

    candidates: list[Any] = []
    for supply in supplies:
        qty = _number(getattr(supply, "quantity_kg", 0.0))
        price = _number(getattr(supply, "expected_price_per_kg", 0.0))
        status = _text(getattr(supply, "status", "available")).lower()
        if qty <= 0 or qty < rules.min_supplier_quantity_kg:
            continue
        if status not in {"available", "open", "ready"}:
            continue
        if rules.max_price_per_kg is not None and price > rules.max_price_per_kg:
            continue
        if not _compatible_quality(_text(getattr(supply, "quality", "")), rules.required_quality):
            continue
        freshness = _freshness_score(supply, clock)
        if rules.max_age_hours is not None:
            available_from = _parse_time(getattr(supply, "available_from", None))
            if available_from:
                age_hours = max(0.0, (clock - available_from).total_seconds() / 3600)
                if age_hours > rules.max_age_hours:
                    continue
        if freshness <= 0:
            continue
        candidates.append(supply)

    groups: dict[tuple[str, str, str], list[Any]] = {}
    for supply in candidates:
        groups.setdefault(_group_key(supply), []).append(supply)

    result: list[AggregatedSupply] = []
    for key, members in sorted(groups.items()):
        members.sort(
            key=lambda s: (
                _number(getattr(s, "expected_price_per_kg", 0.0)),
                -_freshness_score(s, clock),
                -_number(reliability_by_farmer.get(_text(getattr(s, "farmer_id", "")), 0.75), 0.75),
                _text(getattr(s, "id", "")),
            )
        )

        chosen: list[Any] = []
        accumulated = 0.0
        for supply in members:
            if len(chosen) >= rules.max_suppliers:
                break
            chosen.append(supply)
            accumulated += _number(getattr(supply, "quantity_kg", 0.0))
            if target_quantity_kg is not None and accumulated >= target_quantity_kg:
                break

        if accumulated < rules.min_group_quantity_kg:
            continue

        total = sum(_number(getattr(s, "quantity_kg", 0.0)) for s in chosen)
        if total <= 0:
            continue

        weighted_price = sum(
            _number(getattr(s, "quantity_kg", 0.0))
            * _number(getattr(s, "expected_price_per_kg", 0.0))
            for s in chosen
        ) / total

        farmer_ids = [_text(getattr(s, "farmer_id", "")) for s in chosen]
        reliabilities = [
            max(0.0, min(1.0, _number(reliability_by_farmer.get(fid, 0.75), 0.75)))
            for fid in farmer_ids
        ]
        reliability = sum(reliabilities) / len(reliabilities) if reliabilities else 0.0

        freshness_values = [_freshness_score(s, clock) for s in chosen]
        freshness = sum(freshness_values) / len(freshness_values)

        distances = [_distance_from_group(s, chosen) for s in chosen]
        average_distance = sum(distances) / len(distances) if distances else 0.0

        # Penalise concentration: one farmer should not dominate a collective.
        quantities_by_farmer: dict[str, float] = {}
        for s in chosen:
            fid = _text(getattr(s, "farmer_id", ""))
            quantities_by_farmer[fid] = quantities_by_farmer.get(fid, 0.0) + _number(
                getattr(s, "quantity_kg", 0.0)
            )
        largest_share = max(quantities_by_farmer.values(), default=0.0) / total
        concentration_penalty = max(0.0, largest_share - (1.0 / max(len(quantities_by_farmer), 1)))

        quality = max(
            (_text(getattr(s, "quality", "")) for s in chosen),
            key=_quality_rank,
            default="",
        )

        score = (
            0.30 * min(1.0, len(chosen) / max(rules.max_suppliers, 1))
            + 0.25 * reliability
            + 0.20 * freshness
            + 0.15 * max(0.0, 1.0 - concentration_penalty)
            + 0.10 * max(0.0, 1.0 - min(average_distance / max(rules.max_distance_km or 100.0, 1.0), 1.0))
        )

        group_id = "AGG-" + "-".join(
            part.upper().replace(" ", "_")[:16] or "NA" for part in key
        )

        traceability = {
            _text(getattr(s, "id", "")): {
                "farmer_id": _text(getattr(s, "farmer_id", "")),
                "quantity_kg": _number(getattr(s, "quantity_kg", 0.0)),
                "price_per_kg": _number(getattr(s, "expected_price_per_kg", 0.0)),
                "quality": _text(getattr(s, "quality", "")),
                "location": _text(getattr(s, "location", "")),
            }
            for s in chosen
        }

        result.append(
            AggregatedSupply(
                group_id=group_id,
                crop=_text(getattr(chosen[0], "crop", "")),
                location=_text(getattr(chosen[0], "location", "")),
                supply_ids=[_text(getattr(s, "id", "")) for s in chosen],
                farmer_ids=farmer_ids,
                total_quantity_kg=round(total, 3),
                weighted_price_per_kg=round(weighted_price, 2),
                quality=quality,
                supplier_count=len(chosen),
                average_distance_km=round(average_distance, 3),
                freshness_score=round(freshness, 4),
                reliability_score=round(reliability, 4),
                concentration_penalty=round(concentration_penalty, 4),
                aggregation_score=round(score, 4),
                traceability=traceability,
            )
        )

    return sorted(result, key=lambda x: (-x.aggregation_score, x.weighted_price_per_kg, x.group_id))


def flatten_aggregation(groups: Iterable[AggregatedSupply]) -> list[str]:
    """Return unique supply IDs while preserving group ranking order."""
    seen: set[str] = set()
    output: list[str] = []
    for group in groups:
        for supply_id in group.supply_ids:
            if supply_id and supply_id not in seen:
                seen.add(supply_id)
                output.append(supply_id)
    return output