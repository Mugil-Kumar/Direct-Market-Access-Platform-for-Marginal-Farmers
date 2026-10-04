from Preethesh.AI_Market_Intelligence.models import (
    CandidateScore,
    CollectiveCandidate,
)
from Preethesh.AI_Market_Intelligence.matching_engine import RankedCandidate
from Preethesh.AI_Market_Intelligence.recommendation_engine import (
    build_recommendation,
    get_recommendation,
)


def _individual(
    supply_id="SUP-001",
    demand_id="DEM-001",
    score=0.85,
):
    return RankedCandidate(
        supply_id=supply_id,
        demand_id=demand_id,
        score=CandidateScore(
            supply_id=supply_id,
            demand_id=demand_id,
            quantity_score=0.90,
            price_score=0.90,
            distance_score=0.80,
            deadline_score=0.90,
            quality_score=1.00,
            reliability_score=0.80,
            total_score=score,
        ),
        rank=1,
    )


def _collective(
    supply_ids=None,
    score=0.90,
):
    supply_ids = supply_ids or ["SUP-A", "SUP-B"]

    return CollectiveCandidate(
        demand_id="DEM-001",
        supply_ids=supply_ids,
        total_quantity_kg=500.0,
        required_quantity_kg=500.0,
        quantity_coverage_percent=100.0,
        estimated_price_per_kg=25.0,
        estimated_distance_km=10.0,
        farmer_count=len(supply_ids),
        total_score=score,
        feasible=True,
    )


def test_build_individual_recommendation():
    result = build_recommendation(
        demand_id="DEM-001",
        individual_match=_individual(),
        recommended_quantity_kg=400.0,
        required_quantity_kg=400.0,
    )

    assert result.demand_id == "DEM-001"
    assert result.recommended_supply_ids == ["SUP-001"]
    assert result.recommended_quantity_kg == 400.0
    assert result.required_quantity_kg == 400.0
    assert result.coverage_percent == 100.0
    assert result.score == 0.85


def test_build_collective_recommendation_when_score_is_higher():
    result = build_recommendation(
        demand_id="DEM-001",
        individual_match=_individual(score=0.70),
        collective_match=_collective(score=0.90),
    )

    assert result.recommended_supply_ids == [
        "SUP-A",
        "SUP-B",
    ]
    assert result.recommended_quantity_kg == 500.0
    assert result.required_quantity_kg == 500.0
    assert result.coverage_percent == 100.0
    assert result.score == 0.90


def test_single_farmer_collective_does_not_replace_individual():
    result = build_recommendation(
        demand_id="DEM-001",
        individual_match=_individual(score=0.70),
        collective_match=_collective(
            supply_ids=["SUP-A"],
            score=0.95,
        ),
    )

    assert result.recommended_supply_ids == ["SUP-001"]
    assert result.score == 0.70


def test_no_match_returns_warning():
    result = build_recommendation(
        demand_id="DEM-001",
    )

    assert result.recommended_supply_ids == []
    assert "No feasible recommendation was found." in result.warnings


def test_get_recommendation_alias():
    result = get_recommendation(
        demand_id="DEM-001",
        individual_match=_individual(),
        recommended_quantity_kg=400.0,
        required_quantity_kg=400.0,
    )

    assert result.recommended_supply_ids == ["SUP-001"]