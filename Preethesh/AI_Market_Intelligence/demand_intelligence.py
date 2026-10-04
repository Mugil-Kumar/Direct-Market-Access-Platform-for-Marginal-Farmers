"""
Buyer demand intelligence for AGRIWEAVE.

This module analyzes normalized buyer demand before candidate
filtering and matching.

It extracts:
- crop requirement
- quantity requirement
- destination
- delivery deadline
- maximum acceptable price
- quality requirement
- urgency
- completeness
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, List, Optional

from Preethesh.AI_Market_Intelligence.normalizer import (
    normalize_crop,
    normalize_datetime,
    normalize_price,
    normalize_quantity,
    normalize_quality,
)


@dataclass
class DemandIntelligence:
    """Intelligence profile generated for one buyer demand."""

    demand_id: str
    buyer_id: str

    crop: str = ""
    quantity_kg: float = 0.0
    destination: str = ""

    deadline: Optional[str] = None

    max_price_per_kg: Optional[float] = None
    quality_required: str = ""

    data_complete: bool = False
    ready_for_matching: bool = False

    quantity_strength: float = 0.0
    price_capacity: float = 0.0
    quality_strength: float = 0.0
    urgency_score: float = 0.0

    intelligence_score: float = 0.0

    warnings: List[str] = field(default_factory=list)


def _parse_datetime(value: Optional[str]) -> Optional[datetime]:
    """Safely parse an ISO datetime string."""

    if not value:
        return None

    try:
        return datetime.fromisoformat(
            value.replace("Z", "+00:00")
        )
    except (TypeError, ValueError):
        return None


def _quantity_strength(quantity_kg: float) -> float:
    """
    Estimate the strength of the requested quantity.

    Larger demand means stronger market pressure, capped at 1.0.
    """

    if quantity_kg <= 0:
        return 0.0

    return min(quantity_kg / 1000.0, 1.0)


def _quality_strength(quality: str) -> float:
    """Convert standardized quality requirements into a score."""

    quality_scores = {
        "premium": 1.0,
        "grade_a": 1.0,
        "grade_b": 0.75,
        "standard": 0.65,
        "grade_c": 0.45,
    }

    return quality_scores.get(
        quality,
        0.5 if quality else 0.0,
    )


def _price_capacity(max_price_per_kg: Optional[float]) -> float:
    """
    Estimate price capacity.

    A buyer's maximum price is not judged as good or bad here.
    The actual price-fit decision belongs to candidate filtering
    and matching, where farmer asking prices are available.

    The value simply indicates whether a usable price constraint
    exists.
    """

    return 1.0 if (
        max_price_per_kg is not None
        and max_price_per_kg >= 0
    ) else 0.0


def _urgency_score(deadline: Optional[str]) -> float:
    """
    Calculate demand urgency from the deadline.

    A deadline that is already close receives a higher urgency
    score than a distant deadline.

    Without a valid deadline, urgency is zero.
    """

    deadline_dt = _parse_datetime(deadline)

    if deadline_dt is None:
        return 0.0

    now = datetime.now(timezone.utc)

    if deadline_dt.tzinfo is None:
        deadline_dt = deadline_dt.replace(
            tzinfo=timezone.utc
        )

    hours_remaining = (
        deadline_dt - now
    ).total_seconds() / 3600.0

    if hours_remaining <= 0:
        return 1.0

    if hours_remaining <= 6:
        return 1.0

    if hours_remaining <= 24:
        return 0.9

    if hours_remaining <= 48:
        return 0.75

    if hours_remaining <= 72:
        return 0.6

    if hours_remaining <= 168:
        return 0.4

    return 0.2


def _data_completeness(
    crop: str,
    quantity_kg: float,
    destination: str,
    deadline: Optional[str],
    max_price_per_kg: Optional[float],
    quality_required: str,
) -> tuple[bool, List[str]]:
    """Validate the essential demand fields."""

    warnings: List[str] = []

    if not crop:
        warnings.append("Missing required crop")

    if quantity_kg <= 0:
        warnings.append(
            "Required quantity must be greater than zero"
        )

    if not destination:
        warnings.append("Missing buyer destination")

    if not deadline:
        warnings.append("Missing delivery deadline")

    if max_price_per_kg is None:
        warnings.append("Missing maximum acceptable price")

    if not quality_required:
        warnings.append("Missing quality requirement")

    return len(warnings) == 0, warnings


def analyze_demand(
    demand: Any,
) -> DemandIntelligence:
    """
    Analyze one buyer demand.

    Accepts either:
    - the shared Demand dataclass
    - a dictionary containing demand fields
    """

    if isinstance(demand, dict):
        get = demand.get
    else:
        get = lambda key, default=None: getattr(
            demand,
            key,
            default,
        )

    demand_id = str(get("id", ""))
    buyer_id = str(get("buyer_id", ""))

    crop = normalize_crop(get("crop"))

    quantity = normalize_quantity(
        get("quantity_kg")
    )
    quantity_kg = (
        quantity
        if quantity is not None
        else 0.0
    )

    destination = str(
        get("destination", "") or ""
    ).strip().lower()

    deadline = normalize_datetime(
        get("deadline")
    )

    max_price = normalize_price(
        get("max_price_per_kg")
    )

    quality_required = normalize_quality(
        get("quality_required")
    )

    complete, warnings = _data_completeness(
        crop=crop,
        quantity_kg=quantity_kg,
        destination=destination,
        deadline=deadline,
        max_price_per_kg=max_price,
        quality_required=quality_required,
    )

    quantity_strength = _quantity_strength(
        quantity_kg
    )

    price_capacity = _price_capacity(
        max_price
    )

    quality_strength = _quality_strength(
        quality_required
    )

    urgency = _urgency_score(deadline)

    intelligence_score = (
        quantity_strength * 0.25
        + price_capacity * 0.20
        + quality_strength * 0.15
        + urgency * 0.40
    )

    ready_for_matching = (
        complete
        and deadline is not None
        and max_price is not None
    )

    return DemandIntelligence(
        demand_id=demand_id,
        buyer_id=buyer_id,
        crop=crop,
        quantity_kg=quantity_kg,
        destination=destination,
        deadline=deadline,
        max_price_per_kg=max_price,
        quality_required=quality_required,
        data_complete=complete,
        ready_for_matching=ready_for_matching,
        quantity_strength=quantity_strength,
        price_capacity=price_capacity,
        quality_strength=quality_strength,
        urgency_score=urgency,
        intelligence_score=round(
            intelligence_score,
            4,
        ),
        warnings=warnings,
    )


def analyze_demand_batch(
    demands: List[Any],
) -> List[DemandIntelligence]:
    """Analyze multiple buyer demands."""

    return [
        analyze_demand(demand)
        for demand in demands
    ]