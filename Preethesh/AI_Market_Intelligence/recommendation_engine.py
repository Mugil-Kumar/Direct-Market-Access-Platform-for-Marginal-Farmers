"""
AGRIWEAVE recommendation engine.

Selects the strongest individual or collective match and
converts it into the application-facing MatchRecommendation.
"""

from typing import Any, List, Optional

from .models import CollectiveCandidate, MatchRecommendation


def build_recommendation(
    demand_id: str,
    individual_match: Optional[Any] = None,
    collective_match: Optional[CollectiveCandidate] = None,
    alternatives: Optional[List[CollectiveCandidate]] = None,
    recommended_quantity_kg: float = 0.0,
    required_quantity_kg: float = 0.0,
) -> MatchRecommendation:

    alternatives = alternatives or []

    supply_ids: List[str] = []
    quantity = float(recommended_quantity_kg or 0.0)
    required = float(required_quantity_kg or 0.0)
    coverage = 0.0
    score = 0.0
    warnings: List[str] = []

    if individual_match is not None:
        supply_ids = [individual_match.supply_id]
        score = float(individual_match.score.total_score)

    use_collective = (
        collective_match is not None
        and collective_match.feasible
        and len(collective_match.supply_ids) > 1
        and (
            individual_match is None
            or collective_match.total_score
            > individual_match.score.total_score
        )
    )

    if use_collective:
        supply_ids = list(collective_match.supply_ids)
        quantity = float(collective_match.total_quantity_kg)
        required = float(collective_match.required_quantity_kg)
        coverage = float(
            collective_match.quantity_coverage_percent
        )
        score = float(collective_match.total_score)

    if not supply_ids:
        warnings.append("No feasible recommendation was found.")

    if required > 0 and coverage == 0.0 and quantity > 0:
        coverage = min(
            100.0,
            (quantity / required) * 100.0,
        )

    return MatchRecommendation(
        demand_id=demand_id,
        recommended_supply_ids=supply_ids,
        recommended_quantity_kg=quantity,
        required_quantity_kg=required,
        coverage_percent=coverage,
        score=score,
        alternatives=alternatives,
        explanation="",
        warnings=warnings,
    )


def get_recommendation(
    demand_id: str,
    individual_match: Optional[Any] = None,
    collective_match: Optional[CollectiveCandidate] = None,
    alternatives: Optional[List[CollectiveCandidate]] = None,
    recommended_quantity_kg: float = 0.0,
    required_quantity_kg: float = 0.0,
) -> MatchRecommendation:

    return build_recommendation(
        demand_id=demand_id,
        individual_match=individual_match,
        collective_match=collective_match,
        alternatives=alternatives,
        recommended_quantity_kg=recommended_quantity_kg,
        required_quantity_kg=required_quantity_kg,
    )