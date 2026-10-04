"""
AGRIWEAVE AI matching pipeline.

Orchestrates the completed AI Market Intelligence modules:

1. Normalize farmer supplies
2. Normalize buyer demand
3. Analyze supply intelligence
4. Analyze demand intelligence
5. Filter eligible candidates
6. Rank individual candidates
7. Find the best individual match
8. Find the best collective farmer match

Recommendation, explanation, and market-gap stages will be
added once their dedicated modules are implemented.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .candidate_filter import get_eligible_candidates
from .collective_matcher import get_best_collective_match
from .demand_intelligence import analyze_demand
from .matching_engine import get_best_candidate, rank_candidates
from .models import CollectiveCandidate, MatchingWeights
from .normalizer import normalize_demand_data, normalize_supply_data
from .supply_intelligence import analyze_supply


@dataclass
class AIPipelineResult:
    """Complete result produced by the currently implemented AI pipeline."""

    demand: Dict[str, Any] = field(default_factory=dict)

    normalized_supplies: List[Dict[str, Any]] = field(
        default_factory=list
    )

    supply_intelligence: List[Any] = field(
        default_factory=list
    )

    demand_intelligence: Optional[Any] = None

    eligible_candidates: List[Any] = field(
        default_factory=list
    )

    ranked_candidates: List[Any] = field(
        default_factory=list
    )

    best_individual_match: Optional[Any] = None

    best_collective_match: Optional[CollectiveCandidate] = None

    recommendation_type: str = "none"

    warnings: List[str] = field(
        default_factory=list
    )


def run_ai_matching(
    supplies: List[Dict[str, Any]],
    demand: Dict[str, Any],
    reliability_map: Optional[Dict[str, float]] = None,
    distance_map: Optional[Dict[str, float]] = None,
    max_distance_km: float = 100.0,
    max_farmers: int = 5,
    weights: Optional[MatchingWeights] = None,
) -> AIPipelineResult:
    """
    Run the completed AI matching pipeline.

    The function keeps normalization, intelligence analysis,
    filtering, individual matching, and collective matching
    in one predictable orchestration flow.
    """

    warnings: List[str] = []

    if not supplies:
        warnings.append("No farmer supplies were provided.")

    if not demand:
        warnings.append("No buyer demand was provided.")

    normalized_demand = normalize_demand_data(demand)

    normalized_supplies = [
        normalize_supply_data(supply)
        for supply in supplies
    ]

    demand_intelligence = None

    if normalized_demand:
        demand_intelligence = analyze_demand(
            normalized_demand
        )

    supply_intelligence = []

    for supply in normalized_supplies:
        farmer_id = supply.get("farmer_id")

        reliability = 0.0

        if reliability_map and farmer_id:
            reliability = reliability_map.get(
                farmer_id,
                0.0,
            )

        supply_intelligence.append(
            analyze_supply(
                supply,
                farmer_reliability=reliability,
            )
        )

    if not normalized_supplies or not normalized_demand:
        return AIPipelineResult(
            demand=normalized_demand,
            normalized_supplies=normalized_supplies,
            supply_intelligence=supply_intelligence,
            demand_intelligence=demand_intelligence,
            warnings=warnings,
        )

    eligible_results = get_eligible_candidates(
        normalized_supplies,
        normalized_demand,
    )

    ranked_candidates = rank_candidates(
        normalized_supplies,
        normalized_demand,
        reliability_map=reliability_map,
        distance_map=distance_map,
        max_distance_km=max_distance_km,
        weights=weights,
        eligible_only=True,
    )

    best_individual_match = get_best_candidate(
        normalized_supplies,
        normalized_demand,
        reliability_map=reliability_map,
        distance_map=distance_map,
        max_distance_km=max_distance_km,
        weights=weights,
    )

    best_collective_match = get_best_collective_match(
        normalized_demand,
        normalized_supplies,
        weights=weights,
        max_farmers=max_farmers,
    )

    recommendation_type = "none"

    if best_individual_match is not None:
        recommendation_type = "individual"

    if best_collective_match is not None:
        if (
            len(best_collective_match.supply_ids) > 1
            and (
                best_individual_match is None
                or best_collective_match.total_score
                > best_individual_match.score.total_score
            )
        ):
            recommendation_type = "collective"

    if recommendation_type == "none":
        warnings.append(
            "No feasible individual or collective match was found."
        )

    return AIPipelineResult(
        demand=normalized_demand,
        normalized_supplies=normalized_supplies,
        supply_intelligence=supply_intelligence,
        demand_intelligence=demand_intelligence,
        eligible_candidates=eligible_results,
        ranked_candidates=ranked_candidates,
        best_individual_match=best_individual_match,
        best_collective_match=best_collective_match,
        recommendation_type=recommendation_type,
        warnings=warnings,
    )