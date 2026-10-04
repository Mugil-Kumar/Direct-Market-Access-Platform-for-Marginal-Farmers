"""Alternative matching and fallback candidate ranking."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Optional


@dataclass
class AlternativeCandidate:
    supply_id: str
    farmer_id: str
    crop: str
    quantity_kg: float
    price_per_kg: float
    distance_km: float
    quality: str
    score: float
    reasons: list[str]


def rank_alternatives(
    supplies: Iterable[Any],
    *,
    crop: str,
    quantity_required_kg: float,
    max_price_per_kg: Optional[float] = None,
    max_distance_km: Optional[float] = None,
    required_quality: Optional[str] = None,
    top_k: int = 10,
) -> list[AlternativeCandidate]:
    """Rank fallback supplies by serviceability, economics and quality."""

    if quantity_required_kg < 0:
        raise ValueError("quantity_required_kg cannot be negative")
    if top_k < 1:
        raise ValueError("top_k must be positive")

    def qrank(v: Any) -> int:
        return {
            "premium": 4, "a": 3, "grade_a": 3,
            "standard": 2, "b": 2, "grade_b": 2,
            "basic": 1, "c": 1, "grade_c": 1,
        }.get(str(v or "").lower(), 0)

    target_quality = qrank(required_quality) if required_quality else 0
    results: list[AlternativeCandidate] = []

    for supply in supplies:
        supply_crop = str(getattr(supply, "crop", "") or "")
        if supply_crop.lower() != crop.lower():
            continue

        qty = max(0.0, float(getattr(supply, "quantity_kg", 0.0)))
        price = max(0.0, float(getattr(supply, "expected_price_per_kg", 0.0)))
        distance = max(0.0, float(getattr(supply, "distance_km", 0.0)))
        quality = str(getattr(supply, "quality", "") or "")
        status = str(getattr(supply, "status", "available") or "").lower()

        if qty <= 0 or status not in {"available", "open", "ready"}:
            continue
        if max_price_per_kg is not None and price > max_price_per_kg:
            continue
        if max_distance_km is not None and distance > max_distance_km:
            continue
        if qrank(quality) < target_quality:
            continue

        capacity_score = min(1.0, qty / max(quantity_required_kg, 1.0))
        price_score = 1.0 if max_price_per_kg in (None, 0) else max(0.0, 1.0 - price / max_price_per_kg)
        distance_score = 1.0 if max_distance_km in (None, 0) else max(0.0, 1.0 - distance / max_distance_km)
        quality_score = qrank(quality) / 4.0

        score = 0.35 * capacity_score + 0.30 * price_score + 0.20 * distance_score + 0.15 * quality_score
        reasons = []
        if qty >= quantity_required_kg:
            reasons.append("single-source capacity")
        if max_price_per_kg is not None:
            reasons.append("within price ceiling")
        if max_distance_km is not None:
            reasons.append("within distance limit")
        if required_quality:
            reasons.append("quality compatible")

        results.append(
            AlternativeCandidate(
                str(getattr(supply, "id", "") or ""),
                str(getattr(supply, "farmer_id", "") or ""),
                supply_crop,
                round(qty, 3),
                round(price, 2),
                round(distance, 3),
                quality,
                round(score, 6),
                reasons,
            )
        )

    return sorted(
        results,
        key=lambda x: (-x.score, -x.quantity_kg, x.price_per_kg, x.distance_km, x.supply_id),
    )[:top_k]
