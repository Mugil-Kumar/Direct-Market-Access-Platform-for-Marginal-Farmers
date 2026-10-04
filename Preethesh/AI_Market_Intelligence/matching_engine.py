"""
Explainable AI matching engine for AGRIWEAVE.

This module ranks already-feasible farmer supplies against a
buyer demand using multiple factors:

- quantity fit
- price fit
- distance
- deadline urgency
- quality
- farmer reliability

Hard constraints are handled by candidate_filter.py.
This module focuses on ranking the candidates that survived.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from Preethesh.AI_Market_Intelligence.candidate_filter import (
    filter_candidate,
)
from Preethesh.AI_Market_Intelligence.models import (
    CandidateScore,
    MatchingWeights,
)
from Preethesh.AI_Market_Intelligence.normalizer import (
    normalize_datetime,
    normalize_price,
    normalize_quantity,
    normalize_quality,
    normalize_reliability,
)


@dataclass
class RankedCandidate:
    """A feasible candidate with its explainable score."""

    supply_id: str
    demand_id: str

    score: CandidateScore

    rank: int = 0


def _get(record: Any, key: str, default=None):
    """Read a field from a dictionary or object."""

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
    """Return comparable quality rank."""

    return {
        "grade_c": 1,
        "standard": 2,
        "grade_b": 3,
        "grade_a": 4,
        "premium": 5,
    }.get(quality, 0)


def calculate_quantity_score(
    supply_quantity_kg: float,
    demand_quantity_kg: float,
) -> float:
    """
    Score quantity fit.

    A candidate that exactly satisfies the demand receives 1.0.
    Extra available quantity is useful, but excessive unused
    quantity receives slightly less preference.

    Examples:

        supply 100 / demand 100 -> 1.0
        supply 120 / demand 100 -> 0.95
        supply 200 / demand 100 -> 0.75
    """

    if supply_quantity_kg <= 0 or demand_quantity_kg <= 0:
        return 0.0

    if supply_quantity_kg < demand_quantity_kg:
        return 0.0

    ratio = supply_quantity_kg / demand_quantity_kg

    if ratio <= 1.0:
        return 1.0

    excess_ratio = ratio - 1.0

    return max(
        1.0 - (excess_ratio * 0.25),
        0.5,
    )


def calculate_price_score(
    supply_price_per_kg: float,
    buyer_max_price_per_kg: float,
) -> float:
    """
    Score price fit.

    Lower farmer price within the buyer's limit is preferred.

    At the buyer's maximum price -> 0.5
    Significantly below maximum -> closer to 1.0
    Above maximum -> 0.0
    """

    if (
        supply_price_per_kg < 0
        or buyer_max_price_per_kg <= 0
    ):
        return 0.0

    if supply_price_per_kg > buyer_max_price_per_kg:
        return 0.0

    ratio = (
        supply_price_per_kg
        / buyer_max_price_per_kg
    )

    return round(
        1.0 - (0.5 * ratio),
        4,
    )


def calculate_distance_score(
    distance_km: Optional[float],
    max_distance_km: float = 100.0,
) -> float:
    """
    Convert distance into a normalized score.

    Distance is supplied by the integration layer when geographic
    coordinates or a logistics service are available.

    A missing distance is treated neutrally rather than inventing
    geographic information.
    """

    if distance_km is None:
        return 0.5

    if distance_km < 0:
        return 0.0

    if max_distance_km <= 0:
        return 0.0

    if distance_km >= max_distance_km:
        return 0.0

    return round(
        1.0 - (
            distance_km / max_distance_km
        ),
        4,
    )


def calculate_deadline_score(
    available_from: Optional[str],
    deadline: Optional[str],
) -> float:
    """
    Score delivery timing based on the time available between
    supply becoming available and the buyer's deadline.

    A larger feasible time window gives the matching engine more
    flexibility for collection and delivery.

    Hard deadline feasibility is already handled by
    candidate_filter.py.
    """

    supply_start = _parse_datetime(
        available_from
    )

    demand_deadline = _parse_datetime(
        deadline
    )

    if not supply_start or not demand_deadline:
        return 0.0

    seconds_available = (
        demand_deadline - supply_start
    ).total_seconds()

    if seconds_available < 0:
        return 0.0

    hours_available = (
        seconds_available / 3600.0
    )

    if hours_available >= 72:
        return 1.0

    if hours_available >= 48:
        return 0.9

    if hours_available >= 24:
        return 0.75

    if hours_available >= 12:
        return 0.6

    if hours_available >= 6:
        return 0.45

    return 0.3


def calculate_quality_score(
    supply_quality: str,
    demand_quality: str,
) -> float:
    """
    Score quality fit.

    Exact or higher-quality supply receives a strong score.
    """

    supply_rank = _quality_rank(
        normalize_quality(supply_quality)
    )

    demand_rank = _quality_rank(
        normalize_quality(demand_quality)
    )

    if supply_rank <= 0 or demand_rank <= 0:
        return 0.0

    if supply_rank < demand_rank:
        return 0.0

    difference = supply_rank - demand_rank

    if difference == 0:
        return 1.0

    return max(
        0.85 - (difference * 0.05),
        0.75,
    )


def calculate_reliability_score(
    reliability: Any,
) -> float:
    """Normalize farmer reliability to [0, 1]."""

    return normalize_reliability(
        reliability
    )


def calculate_weighted_score(
    quantity_score: float,
    price_score: float,
    distance_score: float,
    deadline_score: float,
    quality_score: float,
    reliability_score: float,
    weights: Optional[MatchingWeights] = None,
) -> float:
    """
    Calculate the final weighted match score.

    Weights are normalized automatically, allowing future tuning
    without accidentally changing the score scale.
    """

    weights = weights or MatchingWeights()

    weight_map = weights.as_dict()

    total_weight = sum(
        weight_map.values()
    )

    if total_weight <= 0:
        return 0.0

    score = (
        quantity_score
        * weight_map["quantity"]
        + price_score
        * weight_map["price"]
        + distance_score
        * weight_map["distance"]
        + deadline_score
        * weight_map["deadline"]
        + quality_score
        * weight_map["quality"]
        + reliability_score
        * weight_map["reliability"]
    )

    return round(
        score / total_weight,
        4,
    )


def score_candidate(
    supply: Any,
    demand: Any,
    reliability: Any = 0.0,
    distance_km: Optional[float] = None,
    max_distance_km: float = 100.0,
    weights: Optional[MatchingWeights] = None,
) -> CandidateScore:
    """
    Filter and score one supply-demand pair.

    Ineligible candidates receive a score of zero and retain the
    exact rejection reasons from candidate_filter.py.
    """

    supply_id = str(
        _get(supply, "id", "")
    )

    demand_id = str(
        _get(demand, "id", "")
    )

    filter_result = filter_candidate(
        supply,
        demand,
    )

    if not filter_result.eligible:
        return CandidateScore(
            supply_id=supply_id,
            demand_id=demand_id,
            eligible=False,
            rejection_reasons=(
                filter_result.rejection_reasons
            ),
        )

    supply_quantity = normalize_quantity(
        _get(supply, "quantity_kg")
    ) or 0.0

    demand_quantity = normalize_quantity(
        _get(demand, "quantity_kg")
    ) or 0.0

    supply_price = normalize_price(
        _get(supply, "expected_price_per_kg")
    ) or 0.0

    buyer_max_price = normalize_price(
        _get(demand, "max_price_per_kg")
    ) or 0.0

    quantity_score = calculate_quantity_score(
        supply_quantity,
        demand_quantity,
    )

    price_score = calculate_price_score(
        supply_price,
        buyer_max_price,
    )

    distance_score = calculate_distance_score(
        distance_km,
        max_distance_km,
    )

    deadline_score = calculate_deadline_score(
    normalize_datetime(
        _get(supply, "available_from")
    ),
    normalize_datetime(
        _get(demand, "deadline")
    ),
)

    quality_score = calculate_quality_score(
        _get(supply, "quality"),
        _get(demand, "quality_required"),
    )

    reliability_score = calculate_reliability_score(
        reliability
    )

    total_score = calculate_weighted_score(
        quantity_score=quantity_score,
        price_score=price_score,
        distance_score=distance_score,
        deadline_score=deadline_score,
        quality_score=quality_score,
        reliability_score=reliability_score,
        weights=weights,
    )

    return CandidateScore(
        supply_id=supply_id,
        demand_id=demand_id,
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


def rank_candidates(
    supplies: List[Any],
    demand: Any,
    reliability_map: Optional[Dict[str, float]] = None,
    distance_map: Optional[Dict[str, float]] = None,
    max_distance_km: float = 100.0,
    weights: Optional[MatchingWeights] = None,
    eligible_only: bool = True,
) -> List[RankedCandidate]:
    """
    Score and rank all supplies for one demand.

    Results are ordered from strongest to weakest match.
    """

    reliability_map = reliability_map or {}
    distance_map = distance_map or {}

    ranked: List[RankedCandidate] = []

    for supply in supplies:
        supply_id = str(
            _get(supply, "id", "")
        )

        farmer_id = str(
            _get(supply, "farmer_id", "")
        )

        score = score_candidate(
            supply=supply,
            demand=demand,
            reliability=reliability_map.get(
                farmer_id,
                0.0,
            ),
            distance_km=distance_map.get(
                supply_id
            ),
            max_distance_km=max_distance_km,
            weights=weights,
        )

        if eligible_only and not score.eligible:
            continue

        ranked.append(
            RankedCandidate(
                supply_id=supply_id,
                demand_id=str(
                    _get(demand, "id", "")
                ),
                score=score,
            )
        )

    ranked.sort(
        key=lambda candidate: (
            candidate.score.total_score,
            candidate.score.quality_score,
            candidate.score.reliability_score,
            candidate.score.quantity_score,
        ),
        reverse=True,
    )

    for index, candidate in enumerate(
        ranked,
        start=1,
    ):
        candidate.rank = index

    return ranked


def get_best_candidate(
    supplies: List[Any],
    demand: Any,
    reliability_map: Optional[Dict[str, float]] = None,
    distance_map: Optional[Dict[str, float]] = None,
    max_distance_km: float = 100.0,
    weights: Optional[MatchingWeights] = None,
) -> Optional[RankedCandidate]:
    """Return the highest-ranked feasible candidate."""

    ranked = rank_candidates(
        supplies=supplies,
        demand=demand,
        reliability_map=reliability_map,
        distance_map=distance_map,
        max_distance_km=max_distance_km,
        weights=weights,
    )

    return ranked[0] if ranked else None