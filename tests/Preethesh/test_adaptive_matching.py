from Preethesh.AI_Market_Intelligence.adaptive_matching import (
    adaptive_match,
    filter_available_supplies,
    rerun_adaptive_matching,
)


def make_supply(supply_id, quantity=500):
    return {
        "supply_id": supply_id,
        "farmer_id": f"F_{supply_id}",
        "crop": "tomato",
        "quantity_kg": quantity,
        "location": "Bengaluru",
        "available_from": "2026-10-04T08:00:00",
        "available_until": "2026-10-06T18:00:00",
        "quality": "premium",
        "expected_price_per_kg": 40,
    }


def make_demand():
    return {
        "demand_id": "D1",
        "crop": "tomato",
        "quantity_kg": 400,
        "destination": "Bengaluru",
        "deadline": "2026-10-06T12:00:00",
        "max_price_per_kg": 50,
        "quality_required": "premium",
    }


def test_filter_available_supplies():
    supplies = [
        make_supply("S1"),
        make_supply("S2"),
        make_supply("S3"),
    ]

    result = filter_available_supplies(
        supplies,
        unavailable_supply_ids={"S2"},
    )

    ids = [supply["supply_id"] for supply in result]

    assert ids == ["S1", "S3"]


def test_filter_with_no_unavailable_supplies():
    supplies = [
        make_supply("S1"),
        make_supply("S2"),
    ]

    result = filter_available_supplies(supplies)

    assert len(result) == 2


def test_adaptive_match_returns_pipeline_result():
    supplies = [
        make_supply("S1"),
        make_supply("S2"),
    ]

    result = adaptive_match(
        supplies=supplies,
        demand=make_demand(),
    )

    assert result is not None
    assert result.demand["crop"] == "tomato"


def test_unavailable_supply_is_not_used():
    supplies = [
        make_supply("S1"),
        make_supply("S2"),
    ]

    result = adaptive_match(
        supplies=supplies,
        demand=make_demand(),
        unavailable_supply_ids={"S1"},
    )

    assert all(
        candidate.supply_id != "S1"
        for candidate in result.ranked_candidates
    )


def test_all_supplies_unavailable():
    supplies = [
        make_supply("S1"),
        make_supply("S2"),
    ]

    result = adaptive_match(
        supplies=supplies,
        demand=make_demand(),
        unavailable_supply_ids={"S1", "S2"},
    )

    assert result.ranked_candidates == []
    assert result.best_individual_match is None
    assert result.best_collective_match is None
    assert result.recommendation_type == "none"


def test_rerun_adaptive_matching_matches_public_alias():
    supplies = [
        make_supply("S1"),
        make_supply("S2"),
    ]

    result = rerun_adaptive_matching(
        supplies=supplies,
        demand=make_demand(),
        unavailable_supply_ids={"S2"},
    )

    assert all(
        candidate.supply_id != "S2"
        for candidate in result.ranked_candidates
    )