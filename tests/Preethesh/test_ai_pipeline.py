from Preethesh.AI_Market_Intelligence.ai_pipeline import (
    AIPipelineResult,
    run_ai_matching,
)


def _supply(
    supply_id="SUP-001",
    quantity="500 kg",
    crop="tomato",
    price="25",
):
    return {
        "id": supply_id,
        "farmer_id": "F001",
        "crop": crop,
        "quantity_kg": quantity,
        "location": "Mangalore",
        "available_from": "2026-10-05 08:00",
        "available_until": "2026-10-06 18:00",
        "quality": "Grade A",
        "expected_price_per_kg": price,
    }


def _demand(
    demand_id="DEM-001",
    quantity="400 kg",
    crop="tomato",
    max_price="30",
):
    return {
        "id": demand_id,
        "buyer_id": "B001",
        "crop": crop,
        "quantity_kg": quantity,
        "destination": "Mangalore",
        "deadline": "2026-10-06 12:00",
        "max_price_per_kg": max_price,
        "quality_required": "Grade A",
    }


def test_ai_pipeline_returns_result():
    result = run_ai_matching(
        supplies=[_supply()],
        demand=_demand(),
    )

    assert isinstance(result, AIPipelineResult)


def test_ai_pipeline_normalizes_supply_and_demand():
    result = run_ai_matching(
        supplies=[
            _supply(quantity="500 kg"),
        ],
        demand=_demand(quantity="400 kg"),
    )

    assert result.demand["quantity_kg"] == 400.0
    assert result.normalized_supplies[0]["quantity_kg"] == 500.0


def test_ai_pipeline_generates_intelligence():
    result = run_ai_matching(
        supplies=[_supply()],
        demand=_demand(),
    )

    assert result.supply_intelligence
    assert result.demand_intelligence is not None


def test_ai_pipeline_finds_eligible_candidate():
    result = run_ai_matching(
        supplies=[_supply()],
        demand=_demand(),
    )

    assert result.eligible_candidates


def test_ai_pipeline_finds_individual_match():
    result = run_ai_matching(
        supplies=[_supply()],
        demand=_demand(),
    )

    assert result.best_individual_match is not None
    assert result.recommendation_type == "individual"


def test_ai_pipeline_finds_collective_match():
    supplies = [
        _supply(
            supply_id="SUP-A",
            quantity="180 kg",
        ),
        _supply(
            supply_id="SUP-B",
            quantity="170 kg",
        ),
        _supply(
            supply_id="SUP-C",
            quantity="200 kg",
        ),
    ]

    result = run_ai_matching(
        supplies=supplies,
        demand=_demand(quantity="500 kg"),
        max_farmers=3,
    )

    assert result.best_collective_match is not None
    assert result.best_collective_match.feasible is True
    assert result.best_collective_match.total_quantity_kg >= 500


def test_ai_pipeline_handles_no_supplies():
    result = run_ai_matching(
        supplies=[],
        demand=_demand(),
    )

    assert result.best_individual_match is None
    assert result.best_collective_match is None
    assert "No farmer supplies were provided." in result.warnings


def test_ai_pipeline_handles_no_match():
    result = run_ai_matching(
        supplies=[
            _supply(crop="tomato"),
        ],
        demand=_demand(crop="onion"),
    )

    assert result.best_individual_match is None
    assert result.best_collective_match is None
    assert result.recommendation_type == "none"


def test_ai_pipeline_ranked_candidates_exist():
    result = run_ai_matching(
        supplies=[
            _supply(
                supply_id="SUP-A",
                quantity="500 kg",
            ),
            _supply(
                supply_id="SUP-B",
                quantity="300 kg",
            ),
        ],
        demand=_demand(),
    )

    assert result.ranked_candidates
    assert result.ranked_candidates[0].supply_id in {
        "SUP-A",
        "SUP-B",
    }