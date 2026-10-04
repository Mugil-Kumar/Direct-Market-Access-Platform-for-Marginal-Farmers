"""
Collective farmer matching engine.

Finds strong combinations of multiple farmer supplies that can
collectively satisfy a buyer's demand.

Unlike normal individual matching, a farmer does NOT need to
individually satisfy the full buyer quantity. Multiple marginal
farmers can contribute partial quantities to one collective match.
"""

from itertools import combinations
from typing import List, Optional

from shared.schemas.schemas import Supply, Demand

from .candidate_filter import filter_candidate
from .matching_engine import (
    calculate_deadline_score,
    calculate_distance_score,
    calculate_price_score,
    calculate_quality_score,
    calculate_reliability_score,
)
from .models import CandidateScore, CollectiveCandidate, MatchingWeights
from .normalizer import normalize_quantity


def _get(item, field, default=None):
    """Read a field from either a dataclass or dictionary."""

    if isinstance(item, dict):
        return item.get(field, default)

    return getattr(item, field, default)


def _safe_float(value, default=0.0):
    """
    Safely convert numeric values or quantity strings to float.

    Examples:
        500       -> 500.0
        "500"     -> 500.0
        "500 kg"  -> 500.0
        "1 tonne" -> 1000.0
    """

    try:
        if isinstance(value, str):
            quantity = normalize_quantity(value)

            if quantity is not None:
                return float(quantity)

        return float(value)

    except (TypeError, ValueError):
        return default


def _partial_quantity_score(
    supply_quantity: float,
    demand_quantity: float,
) -> float:
    """
    Score how much of the buyer's demand this farmer can contribute.

    Unlike normal individual matching, partial quantity is valid here.
    """

    if demand_quantity <= 0:
        return 0.0

    return min(
        supply_quantity / demand_quantity,
        1.0,
    )


def _score_partial_candidate(
    supply,
    demand,
    weights: MatchingWeights,
) -> CandidateScore:
    """
    Score a farmer as a partial contributor to a collective match.

    Quantity is intentionally treated as a partial contribution.
    Other hard constraints still have to pass.
    """

    filter_result = filter_candidate(
        supply,
        demand,
    )

    # Candidate is allowed into collective matching when the only
    # rejection reason is insufficient individual quantity.
    non_quantity_rejections = [
        reason
        for reason in filter_result.rejection_reasons
        if "Insufficient supply quantity" not in reason
    ]

    if non_quantity_rejections:
        return CandidateScore(
            supply_id=_get(supply, "id", ""),
            demand_id=_get(demand, "id", ""),
            eligible=False,
            rejection_reasons=non_quantity_rejections,
        )

    supply_quantity = _safe_float(
        _get(supply, "quantity_kg")
    )

    demand_quantity = _safe_float(
        _get(demand, "quantity_kg")
    )

    quantity_score = _partial_quantity_score(
        supply_quantity,
        demand_quantity,
    )

    price_score = calculate_price_score(
        _safe_float(
            _get(supply, "expected_price_per_kg")
        ),
        _safe_float(
            _get(demand, "max_price_per_kg")
        ),
    )

    distance_score = calculate_distance_score(
        None,
        100.0,
    )

    deadline_score = calculate_deadline_score(
        _get(supply, "available_from"),
        _get(demand, "deadline"),
    )

    quality_score = calculate_quality_score(
        _get(supply, "quality"),
        _get(demand, "quality_required"),
    )

    reliability_score = calculate_reliability_score(
        _get(supply, "reliability_score", 0.0)
    )

    total_score = (
        quantity_score * weights.quantity
        + price_score * weights.price
        + distance_score * weights.distance
        + deadline_score * weights.deadline
        + quality_score * weights.quality
        + reliability_score * weights.reliability
    )

    return CandidateScore(
        supply_id=_get(supply, "id", ""),
        demand_id=_get(demand, "id", ""),
        quantity_score=quantity_score,
        price_score=price_score,
        distance_score=distance_score,
        deadline_score=deadline_score,
        quality_score=quality_score,
        reliability_score=reliability_score,
        total_score=total_score,
        eligible=True,
        rejection_reasons=[],
    )


def _get_collective_eligible_supplies(
    supplies,
    demand,
):
    """
    Return supplies that can contribute partially to the demand.

    Individual quantity insufficiency is allowed.
    Other constraints remain strict.
    """

    eligible = []

    for supply in supplies:
        result = filter_candidate(
            supply,
            demand,
        )

        non_quantity_rejections = [
            reason
            for reason in result.rejection_reasons
            if "Insufficient supply quantity" not in reason
        ]

        if not non_quantity_rejections:
            eligible.append(supply)

    return eligible


def _calculate_combination_score(
    candidates,
    total_quantity: float,
    required_quantity: float,
    weights: MatchingWeights,
) -> float:
    """
    Calculate the overall score of a collective farmer combination.
    """

    if not candidates:
        return 0.0

    average_score = sum(
        candidate.total_score
        for candidate in candidates
    ) / len(candidates)

    if required_quantity <= 0:
        coverage_score = 0.0
    else:
        coverage_score = min(
            total_quantity / required_quantity,
            1.0,
        )

    return (
        average_score * 0.8
        + coverage_score * 0.2
    )


def _calculate_average_price(
    combination,
) -> float:
    """Calculate quantity-weighted average farmer price."""

    total_quantity = 0.0
    total_value = 0.0

    for supply in combination:
        quantity = _safe_float(
            _get(supply, "quantity_kg")
        )

        price = _safe_float(
            _get(supply, "expected_price_per_kg")
        )

        total_quantity += quantity
        total_value += quantity * price

    if total_quantity <= 0:
        return 0.0

    return total_value / total_quantity


def _calculate_average_distance(
    candidates,
) -> float:
    """Convert average distance score into an estimated distance."""

    if not candidates:
        return 0.0

    average_score = sum(
        candidate.distance_score
        for candidate in candidates
    ) / len(candidates)

    return max(
        0.0,
        (1.0 - average_score) * 100.0,
    )


def _build_collective_candidate(
    demand,
    combination,
    weights,
) -> CollectiveCandidate:
    """Build a scored collective candidate."""

    required_quantity = _safe_float(
        _get(demand, "quantity_kg")
    )

    total_quantity = sum(
        _safe_float(
            _get(supply, "quantity_kg")
        )
        for supply in combination
    )

    scored_candidates = [
        _score_partial_candidate(
            supply,
            demand,
            weights,
        )
        for supply in combination
    ]

    total_score = _calculate_combination_score(
        scored_candidates,
        total_quantity,
        required_quantity,
        weights,
    )

    if required_quantity > 0:
        coverage = min(
            total_quantity / required_quantity * 100.0,
            100.0,
        )
    else:
        coverage = 0.0

    return CollectiveCandidate(
        demand_id=_get(demand, "id", ""),
        supply_ids=[
            _get(supply, "id", "")
            for supply in combination
        ],
        total_quantity_kg=total_quantity,
        required_quantity_kg=required_quantity,
        quantity_coverage_percent=coverage,
        estimated_price_per_kg=_calculate_average_price(
            combination
        ),
        estimated_distance_km=_calculate_average_distance(
            scored_candidates
        ),
        farmer_count=len(combination),
        total_score=total_score,
        feasible=total_quantity >= required_quantity,
    )


def find_collective_matches(
    demand,
    supplies: List[Supply],
    weights: Optional[MatchingWeights] = None,
    max_farmers: int = 5,
) -> List[CollectiveCandidate]:
    """
    Find and rank feasible combinations of marginal farmer supplies.
    """

    if weights is None:
        weights = MatchingWeights()

    if not supplies:
        return []

    eligible_supplies = _get_collective_eligible_supplies(
        supplies,
        demand,
    )

    if not eligible_supplies:
        return []

    max_farmers = max(
        1,
        min(
            max_farmers,
            len(eligible_supplies),
        ),
    )

    results = []

    for farmer_count in range(
        1,
        max_farmers + 1,
    ):
        for combination in combinations(
            eligible_supplies,
            farmer_count,
        ):
            candidate = _build_collective_candidate(
                demand,
                combination,
                weights,
            )

            if candidate.feasible:
                results.append(candidate)

    results.sort(
        key=lambda candidate: (
            candidate.total_score,
            candidate.quantity_coverage_percent,
            -candidate.farmer_count,
        ),
        reverse=True,
    )

    return results


def get_best_collective_match(
    demand,
    supplies: List[Supply],
    weights: Optional[MatchingWeights] = None,
    max_farmers: int = 5,
) -> Optional[CollectiveCandidate]:
    """Return the strongest feasible collective farmer combination."""

    matches = find_collective_matches(
        demand,
        supplies,
        weights=weights,
        max_farmers=max_farmers,
    )

    if not matches:
        return None

    return matches[0]