from Preethesh.AI_Market_Intelligence.explanation import (
    explain_candidate,
    explain_recommendation,
    explain_rejections,
)

from Preethesh.AI_Market_Intelligence.models import (
    CandidateScore,
    MatchRecommendation,
)


def test_explain_eligible_candidate():
    score = CandidateScore(
        supply_id="S1",
        demand_id="D1",
        quantity_score=0.9,
        price_score=0.8,
        distance_score=0.7,
        deadline_score=0.6,
        quality_score=0.9,
        reliability_score=0.8,
        total_score=0.81,
        eligible=True,
    )

    result = explain_candidate(score)

    assert "S1" in result
    assert "0.81" in result
    assert "quality" in result


def test_explain_rejected_candidate():
    score = CandidateScore(
        supply_id="S2",
        demand_id="D1",
        eligible=False,
        rejection_reasons=["Insufficient quantity"],
    )

    result = explain_candidate(score)

    assert "S2" in result
    assert "rejected" in result
    assert "Insufficient quantity" in result


def test_explain_individual_recommendation():
    recommendation = MatchRecommendation(
        demand_id="D1",
        recommended_supply_ids=["S1"],
        recommended_quantity_kg=100.0,
        required_quantity_kg=100.0,
        coverage_percent=100.0,
        score=0.85,
    )

    result = explain_recommendation(recommendation)

    assert "S1" in result
    assert "0.85" in result
    assert "100.0%" in result


def test_explain_collective_recommendation():
    recommendation = MatchRecommendation(
        demand_id="D1",
        recommended_supply_ids=["S1", "S2"],
        recommended_quantity_kg=180.0,
        required_quantity_kg=200.0,
        coverage_percent=90.0,
        score=0.88,
    )

    result = explain_recommendation(recommendation)

    assert "2 farmers" in result
    assert "90.0%" in result
    assert "0.88" in result


def test_explain_no_recommendation():
    recommendation = MatchRecommendation(
        demand_id="D1",
        recommended_supply_ids=[],
    )

    result = explain_recommendation(recommendation)

    assert "No feasible supply recommendation" in result


def test_explain_rejections():
    result = explain_rejections(
        ["Wrong crop", "Insufficient quantity"]
    )

    assert "Wrong crop" in result
    assert "Insufficient quantity" in result


def test_explain_empty_rejections():
    result = explain_rejections([])

    assert "No rejection reasons" in result