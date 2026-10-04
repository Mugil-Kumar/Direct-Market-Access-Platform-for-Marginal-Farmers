"""
Candidate filtering for AGRIWEAVE.

This module removes impossible supply-demand combinations before
the scoring and matching engine runs.

Every rejected candidate receives explicit reasons so that later
modules can provide explainable AI decisions.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, List, Optional

from Preethesh.AI_Market_Intelligence.normalizer import (
    normalize_crop,
    normalize_datetime,
    normalize_price,
    normalize_quantity,
    normalize_quality,
)


@dataclass
class CandidateFilterResult:
    """Result of evaluating one supply against one demand."""

    supply_id: str
    demand_id: str

    eligible: bool = False

    crop_match: bool = False
    quantity_match: bool = False
    availability_match: bool = False
    deadline_match: bool = False
    price_match: bool = False
    quality_match: bool = False
    data_valid: bool = False

    rejection_reasons: List[str] = field(
        default_factory=list
    )


def _get(record: Any, key: str, default=None):
    """Read a field from either a dictionary or an object."""

    if isinstance(record, dict):
        return record.get(key, default)

    return getattr(record, key, default)


def _parse_datetime(value: Optional[str]) -> Optional[datetime]:
    """Safely parse an ISO datetime."""

    if not value:
        return None

    try:
        return datetime.fromisoformat(
            value.replace("Z", "+00:00")
        )
    except (TypeError, ValueError):
        return None


def _quality_rank(quality: str) -> int:
    """
    Convert quality into a comparable rank.

    Higher rank means better quality.
    """

    return {
        "grade_c": 1,
        "standard": 2,
        "grade_b": 3,
        "grade_a": 4,
        "premium": 5,
    }.get(quality, 0)


def _validate_supply(
    supply: Any,
) -> tuple[bool, List[str]]:
    """Validate essential supply fields."""

    reasons: List[str] = []

    crop = normalize_crop(_get(supply, "crop"))
    quantity = normalize_quantity(
        _get(supply, "quantity_kg")
    )
    location = str(
        _get(supply, "location", "") or ""
    ).strip()

    available_from = normalize_datetime(
        _get(supply, "available_from")
    )

    available_until = normalize_datetime(
        _get(supply, "available_until")
    )

    quality = normalize_quality(
        _get(supply, "quality")
    )

    price = normalize_price(
        _get(supply, "expected_price_per_kg")
    )

    if not crop:
        reasons.append("Invalid or missing supply crop")

    if quantity is None or quantity <= 0:
        reasons.append(
            "Invalid or missing supply quantity"
        )

    if not location:
        reasons.append(
            "Invalid or missing supply location"
        )

    if not available_from:
        reasons.append(
            "Invalid or missing supply availability start"
        )

    if not available_until:
        reasons.append(
            "Invalid or missing supply availability end"
        )

    if not quality:
        reasons.append(
            "Invalid or missing supply quality"
        )

    if price is None:
        reasons.append(
            "Invalid or missing supply expected price"
        )

    if available_from and available_until:
        start = _parse_datetime(available_from)
        end = _parse_datetime(available_until)

        if start and end and end <= start:
            reasons.append(
                "Supply availability window is invalid"
            )

    return len(reasons) == 0, reasons


def _validate_demand(
    demand: Any,
) -> tuple[bool, List[str]]:
    """Validate essential demand fields."""

    reasons: List[str] = []

    crop = normalize_crop(_get(demand, "crop"))

    quantity = normalize_quantity(
        _get(demand, "quantity_kg")
    )

    destination = str(
        _get(demand, "destination", "") or ""
    ).strip()

    deadline = normalize_datetime(
        _get(demand, "deadline")
    )

    max_price = normalize_price(
        _get(demand, "max_price_per_kg")
    )

    quality = normalize_quality(
        _get(demand, "quality_required")
    )

    if not crop:
        reasons.append("Invalid or missing demand crop")

    if quantity is None or quantity <= 0:
        reasons.append(
            "Invalid or missing demand quantity"
        )

    if not destination:
        reasons.append(
            "Invalid or missing demand destination"
        )

    if not deadline:
        reasons.append(
            "Invalid or missing demand deadline"
        )

    if max_price is None:
        reasons.append(
            "Invalid or missing demand maximum price"
        )

    if not quality:
        reasons.append(
            "Invalid or missing demand quality requirement"
        )

    return len(reasons) == 0, reasons


def filter_candidate(
    supply: Any,
    demand: Any,
) -> CandidateFilterResult:
    """
    Determine whether one supply can potentially satisfy one demand.

    Filtering is intentionally strict. Candidates that violate
    hard constraints are rejected before scoring.
    """

    supply_id = str(
        _get(supply, "id", "")
    )

    demand_id = str(
        _get(demand, "id", "")
    )

    result = CandidateFilterResult(
        supply_id=supply_id,
        demand_id=demand_id,
    )

    supply_valid, supply_errors = _validate_supply(
        supply
    )

    demand_valid, demand_errors = _validate_demand(
        demand
    )

    result.data_valid = (
        supply_valid and demand_valid
    )

    if not supply_valid:
        result.rejection_reasons.extend(
            supply_errors
        )

    if not demand_valid:
        result.rejection_reasons.extend(
            demand_errors
        )

    if not result.data_valid:
        return result

    supply_crop = normalize_crop(
        _get(supply, "crop")
    )

    demand_crop = normalize_crop(
        _get(demand, "crop")
    )

    result.crop_match = (
        supply_crop == demand_crop
    )

    if not result.crop_match:
        result.rejection_reasons.append(
            f"Wrong crop: supply={supply_crop}, "
            f"demand={demand_crop}"
        )

    supply_quantity = normalize_quantity(
        _get(supply, "quantity_kg")
    )

    demand_quantity = normalize_quantity(
        _get(demand, "quantity_kg")
    )

    result.quantity_match = (
        supply_quantity is not None
        and demand_quantity is not None
        and supply_quantity >= demand_quantity
    )

    if not result.quantity_match:
        result.rejection_reasons.append(
            "Insufficient supply quantity"
        )

    supply_start = _parse_datetime(
        normalize_datetime(
            _get(supply, "available_from")
        )
    )

    supply_end = _parse_datetime(
        normalize_datetime(
            _get(supply, "available_until")
        )
    )

    deadline = _parse_datetime(
        normalize_datetime(
            _get(demand, "deadline")
        )
    )

    result.availability_match = (
        supply_start is not None
        and supply_end is not None
        and deadline is not None
        and supply_start <= deadline
    )

    if not result.availability_match:
        result.rejection_reasons.append(
            "Supply is not available before demand deadline"
        )

    result.deadline_match = (
        result.availability_match
        and supply_end is not None
        and deadline is not None
        and supply_start <= deadline
    )

    if supply_start and supply_end and deadline:
        if supply_end < supply_start:
            result.deadline_match = False

    supply_price = normalize_price(
        _get(supply, "expected_price_per_kg")
    )

    demand_max_price = normalize_price(
        _get(demand, "max_price_per_kg")
    )

    result.price_match = (
        supply_price is not None
        and demand_max_price is not None
        and supply_price <= demand_max_price
    )

    if not result.price_match:
        result.rejection_reasons.append(
            "Supply price exceeds buyer maximum price"
        )

    supply_quality = normalize_quality(
        _get(supply, "quality")
    )

    demand_quality = normalize_quality(
        _get(demand, "quality_required")
    )

    result.quality_match = (
        _quality_rank(supply_quality)
        >= _quality_rank(demand_quality)
        and _quality_rank(demand_quality) > 0
    )

    if not result.quality_match:
        result.rejection_reasons.append(
            "Supply quality does not satisfy buyer requirement"
        )

    result.eligible = (
        result.data_valid
        and result.crop_match
        and result.quantity_match
        and result.availability_match
        and result.deadline_match
        and result.price_match
        and result.quality_match
    )

    return result


def filter_candidates(
    supplies: List[Any],
    demand: Any,
) -> List[CandidateFilterResult]:
    """
    Filter a list of supplies against one demand.

    Returns a result for every candidate, including rejected
    candidates. This is useful for explainability and debugging.
    """

    return [
        filter_candidate(
            supply,
            demand,
        )
        for supply in supplies
    ]


def get_eligible_candidates(
    supplies: List[Any],
    demand: Any,
) -> List[CandidateFilterResult]:
    """Return only candidates that pass every hard constraint."""

    results = filter_candidates(
        supplies,
        demand,
    )

    return [
        result
        for result in results
        if result.eligible
    ]