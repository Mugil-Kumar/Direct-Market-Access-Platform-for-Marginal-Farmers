"""
Farmer supply intelligence for AGRIWEAVE.

This module analyzes normalized farmer supply records before they
reach candidate filtering and matching.

It does not decide the final buyer match. Its job is to turn raw
supply data into useful intelligence:
- readiness
- quantity strength
- availability
- quality
- price position
- reliability
- completeness
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from Preethesh.AI_Market_Intelligence.normalizer import (
    normalize_crop,
    normalize_datetime,
    normalize_price,
    normalize_quantity,
    normalize_quality,
    normalize_reliability,
)


@dataclass
class SupplyIntelligence:
    """
    Intelligence profile generated for one farmer supply record.
    """

    supply_id: str
    farmer_id: str

    crop: str = ""
    quantity_kg: float = 0.0
    location: str = ""

    available_from: Optional[str] = None
    available_until: Optional[str] = None

    quality: str = ""
    expected_price_per_kg: Optional[float] = None

    reliability_score: float = 0.0

    data_complete: bool = False
    ready_for_matching: bool = False

    quantity_strength: float = 0.0
    price_position: float = 0.0
    quality_strength: float = 0.0
    availability_strength: float = 0.0
    reliability_strength: float = 0.0

    intelligence_score: float = 0.0

    warnings: List[str] = field(default_factory=list)


def _parse_datetime(value: Optional[str]) -> Optional[datetime]:
    """Safely convert an ISO timestamp into datetime."""

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
    Estimate how strong the available quantity is.

    The score is capped at 1.0 so exceptionally large farms do not
    completely dominate every other intelligence factor.

    0 kg      -> 0.0
    100 kg    -> 0.5
    200 kg+   -> 1.0
    """

    if quantity_kg <= 0:
        return 0.0

    return min(quantity_kg / 200.0, 1.0)


def _quality_strength(quality: str) -> float:
    """Convert standardized quality into a normalized strength."""

    quality_scores = {
        "premium": 1.0,
        "grade_a": 1.0,
        "grade_b": 0.75,
        "standard": 0.65,
        "grade_c": 0.45,
    }

    return quality_scores.get(quality, 0.5 if quality else 0.0)


def _availability_strength(
    available_from: Optional[str],
    available_until: Optional[str],
) -> float:
    """
    Score the quality of an availability window.

    A valid availability interval is stronger than incomplete or
    invalid timing information.
    """

    start = _parse_datetime(available_from)
    end = _parse_datetime(available_until)

    if not start or not end:
        return 0.0

    if end <= start:
        return 0.0

    duration_hours = (
        end - start
    ).total_seconds() / 3600.0

    # A 24-hour or longer valid window receives full strength.
    return min(duration_hours / 24.0, 1.0)


def _data_completeness(
    crop: str,
    quantity_kg: float,
    location: str,
    available_from: Optional[str],
    available_until: Optional[str],
    quality: str,
    expected_price_per_kg: Optional[float],
) -> tuple[bool, List[str]]:
    """
    Determine whether the supply record contains enough
    information to safely enter matching.
    """

    warnings: List[str] = []

    if not crop:
        warnings.append("Missing crop")

    if quantity_kg <= 0:
        warnings.append("Quantity must be greater than zero")

    if not location:
        warnings.append("Missing location")

    if not available_from:
        warnings.append("Missing availability start time")

    if not available_until:
        warnings.append("Missing availability end time")

    if not quality:
        warnings.append("Missing quality")

    if expected_price_per_kg is None:
        warnings.append("Missing expected price")

    complete = len(warnings) == 0

    return complete, warnings


def analyze_supply(
    supply: Any,
    farmer_reliability: float = 0.0,
) -> SupplyIntelligence:
    """
    Analyze one supply record.

    The function accepts either:
    - the shared Supply dataclass, or
    - a dictionary containing supply fields.

    Farmer reliability is supplied separately because the shared
    Supply schema does not store farmer reliability directly.
    """

    if isinstance(supply, dict):
        get = supply.get
    else:
        get = lambda key, default=None: getattr(
            supply,
            key,
            default,
        )

    supply_id = str(get("id", ""))
    farmer_id = str(get("farmer_id", ""))

    crop = normalize_crop(get("crop"))

    quantity = normalize_quantity(
        get("quantity_kg")
    )
    quantity_kg = quantity if quantity is not None else 0.0

    location = str(
        get("location", "") or ""
    ).strip().lower()

    available_from = normalize_datetime(
        get("available_from")
    )

    available_until = normalize_datetime(
        get("available_until")
    )

    quality = normalize_quality(
        get("quality")
    )

    expected_price = normalize_price(
        get("expected_price_per_kg")
    )

    reliability = normalize_reliability(
        farmer_reliability
    )

    complete, warnings = _data_completeness(
        crop=crop,
        quantity_kg=quantity_kg,
        location=location,
        available_from=available_from,
        available_until=available_until,
        quality=quality,
        expected_price_per_kg=expected_price,
    )

    quantity_strength = _quantity_strength(
        quantity_kg
    )

    quality_strength = _quality_strength(
        quality
    )

    availability_strength = _availability_strength(
        available_from,
        available_until,
    )

    reliability_strength = reliability

    # Price position is intentionally neutral at this stage.
    #
    # A price cannot be judged as "good" or "bad" until a buyer
    # demand and its maximum acceptable price are known.
    price_position = 0.5 if expected_price is not None else 0.0

    intelligence_score = (
        quantity_strength * 0.25
        + price_position * 0.15
        + quality_strength * 0.15
        + availability_strength * 0.20
        + reliability_strength * 0.25
    )

    ready_for_matching = (
        complete
        and availability_strength > 0.0
        and reliability_strength >= 0.0
    )

    return SupplyIntelligence(
        supply_id=supply_id,
        farmer_id=farmer_id,
        crop=crop,
        quantity_kg=quantity_kg,
        location=location,
        available_from=available_from,
        available_until=available_until,
        quality=quality,
        expected_price_per_kg=expected_price,
        reliability_score=reliability,
        data_complete=complete,
        ready_for_matching=ready_for_matching,
        quantity_strength=quantity_strength,
        price_position=price_position,
        quality_strength=quality_strength,
        availability_strength=availability_strength,
        reliability_strength=reliability_strength,
        intelligence_score=round(
            intelligence_score,
            4,
        ),
        warnings=warnings,
    )


def analyze_supply_batch(
    supplies: List[Any],
    farmer_reliability: Optional[Dict[str, float]] = None,
) -> List[SupplyIntelligence]:
    """
    Analyze multiple supply records.

    farmer_reliability maps farmer IDs to reliability scores.
    """

    reliability_map = farmer_reliability or {}

    results: List[SupplyIntelligence] = []

    for supply in supplies:
        if isinstance(supply, dict):
            farmer_id = str(
                supply.get("farmer_id", "")
            )
        else:
            farmer_id = str(
                getattr(supply, "farmer_id", "")
            )

        reliability = reliability_map.get(
            farmer_id,
            0.0,
        )

        results.append(
            analyze_supply(
                supply,
                farmer_reliability=reliability,
            )
        )

    return results


def summarize_supply_intelligence(
    profiles: List[SupplyIntelligence],
) -> Dict[str, Any]:
    """
    Produce an aggregate intelligence summary for a group of
    farmer supplies.
    """

    total_quantity = sum(
        profile.quantity_kg
        for profile in profiles
    )

    ready_count = sum(
        profile.ready_for_matching
        for profile in profiles
    )

    incomplete_count = sum(
        not profile.data_complete
        for profile in profiles
    )

    crop_totals: Dict[str, float] = {}

    for profile in profiles:
        if profile.crop:
            crop_totals[profile.crop] = (
                crop_totals.get(profile.crop, 0.0)
                + profile.quantity_kg
            )

    average_score = (
        sum(
            profile.intelligence_score
            for profile in profiles
        ) / len(profiles)
        if profiles
        else 0.0
    )

    return {
        "supply_count": len(profiles),
        "total_quantity_kg": round(
            total_quantity,
            2,
        ),
        "ready_for_matching_count": ready_count,
        "incomplete_count": incomplete_count,
        "crop_totals_kg": crop_totals,
        "average_intelligence_score": round(
            average_score,
            4,
        ),
    }