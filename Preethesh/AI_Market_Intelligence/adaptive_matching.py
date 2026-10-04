"""
AGRIWEAVE adaptive matching.

Re-runs the existing AI matching pipeline when the available
farmer supply changes.
"""

from typing import Any, Dict, List, Optional, Set

from .ai_pipeline import AIPipelineResult, run_ai_matching
from .models import MatchingWeights


def filter_available_supplies(
    supplies: List[Dict[str, Any]],
    unavailable_supply_ids: Optional[Set[str]] = None,
) -> List[Dict[str, Any]]:
    """
    Remove supplies that are no longer available.
    """

    unavailable = unavailable_supply_ids or set()

    return [
        supply
        for supply in supplies
        if supply.get("supply_id") not in unavailable
    ]


def rerun_adaptive_matching(
    supplies: List[Dict[str, Any]],
    demand: Dict[str, Any],
    unavailable_supply_ids: Optional[Set[str]] = None,
    reliability_map: Optional[Dict[str, float]] = None,
    distance_map: Optional[Dict[str, float]] = None,
    max_distance_km: float = 100.0,
    max_farmers: int = 5,
    weights: Optional[MatchingWeights] = None,
) -> AIPipelineResult:
    """
    Re-run AI matching after supply availability changes.
    """

    available_supplies = filter_available_supplies(
        supplies=supplies,
        unavailable_supply_ids=unavailable_supply_ids,
    )

    return run_ai_matching(
        supplies=available_supplies,
        demand=demand,
        reliability_map=reliability_map,
        distance_map=distance_map,
        max_distance_km=max_distance_km,
        max_farmers=max_farmers,
        weights=weights,
    )


def adaptive_match(
    supplies: List[Dict[str, Any]],
    demand: Dict[str, Any],
    unavailable_supply_ids: Optional[Set[str]] = None,
    reliability_map: Optional[Dict[str, float]] = None,
    distance_map: Optional[Dict[str, float]] = None,
    max_distance_km: float = 100.0,
    max_farmers: int = 5,
    weights: Optional[MatchingWeights] = None,
) -> AIPipelineResult:
    """
    Public alias for adaptive matching.
    """

    return rerun_adaptive_matching(
        supplies=supplies,
        demand=demand,
        unavailable_supply_ids=unavailable_supply_ids,
        reliability_map=reliability_map,
        distance_map=distance_map,
        max_distance_km=max_distance_km,
        max_farmers=max_farmers,
        weights=weights,
    )