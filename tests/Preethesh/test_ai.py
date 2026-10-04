from Preethesh.AI_Market_Intelligence.models import (
    CandidateScore,
    CollectiveCandidate,
    MatchRecommendation,
    MarketGapResult,
    MatchingContext,
    MatchingResult,
    MatchingWeights,
)


def test_candidate_score():
    score = CandidateScore(
        supply_id="SUP-001",
        demand_id="DEM-001",
        quantity_score=0.9,
        price_score=0.8,
        total_score=0.85,
    )

    assert score.supply_id == "SUP-001"
    assert score.demand_id == "DEM-001"
    assert score.total_score == 0.85
    assert score.eligible is True


def test_collective_candidate():
    candidate = CollectiveCandidate(
        demand_id="DEM-001",
        supply_ids=["SUP-001", "SUP-002"],
        total_quantity_kg=80.0,
        required_quantity_kg=100.0,
        quantity_coverage_percent=80.0,
        farmer_count=2,
    )

    assert len(candidate.supply_ids) == 2
    assert candidate.total_quantity_kg == 80.0
    assert candidate.farmer_count == 2


def test_matching_weights():
    weights = MatchingWeights()

    assert weights.total() == 1.0
    assert weights.quantity == 0.25
    assert weights.price == 0.20


def test_matching_context():
    context = MatchingContext()

    assert context.farmers == []
    assert context.buyers == []
    assert context.supplies == []
    assert context.demands == []
    assert context.max_distance_km == 100.0


def test_matching_result():
    result = MatchingResult()

    assert result.recommendations == []
    assert result.matches == []
    assert result.market_gaps == []
    assert result.unmatched_demand_ids == []


def test_market_gap_result():
    gap = MarketGapResult(
        crop="tomato",
        demand_quantity_kg=1000.0,
        available_supply_quantity_kg=650.0,
        shortage_quantity_kg=350.0,
        status="shortage",
    )

    assert gap.crop == "tomato"
    assert gap.shortage_quantity_kg == 350.0
    assert gap.status == "shortage"


def test_match_recommendation():
    recommendation = MatchRecommendation(
        demand_id="DEM-001",
        recommended_supply_ids=["SUP-001", "SUP-002"],
        recommended_quantity_kg=100.0,
        required_quantity_kg=100.0,
        coverage_percent=100.0,
        score=0.91,
    )

    assert recommendation.demand_id == "DEM-001"
    assert recommendation.coverage_percent == 100.0
    assert recommendation.score == 0.91
from Preethesh.AI_Market_Intelligence.normalizer import (
    normalize_crop,
    normalize_quality,
    normalize_quantity,
    normalize_price,
    normalize_reliability,
    normalize_supply_data,
    normalize_demand_data,
)


def test_normalize_crop():
    assert normalize_crop(" TOMATO ") == "tomato"
    assert normalize_crop("tomatoes") == "tomato"
    assert normalize_crop("POTATO") == "potato"


def test_normalize_quality():
    assert normalize_quality("Grade A") == "grade_a"
    assert normalize_quality(" PREMIUM ") == "premium"


def test_normalize_quantity():
    assert normalize_quantity("50 kg") == 50.0
    assert normalize_quantity("1.5 tonnes") == 1500.0
    assert normalize_quantity("1000 g") == 1.0
    assert normalize_quantity("invalid") is None


def test_normalize_price():
    assert normalize_price("₹25") == 25.0
    assert normalize_price("25/kg") == 25.0
    assert normalize_price("invalid") is None


def test_normalize_reliability():
    assert normalize_reliability(0.85) == 0.85
    assert normalize_reliability(85) == 0.85
    assert normalize_reliability(120) == 1.0


def test_normalize_supply_data():
    raw = {
        "farmer_id": "F001",
        "crop": " TOMATOES ",
        "quantity_kg": "1.5 tonnes",
        "location": "  Mangalore  ",
        "available_from": "2026-10-05",
        "available_until": "2026-10-08",
        "quality": "Grade A",
        "expected_price_per_kg": "₹25",
    }

    result = normalize_supply_data(raw)

    assert result["crop"] == "tomato"
    assert result["quantity_kg"] == 1500.0
    assert result["location"] == "mangalore"
    assert result["quality"] == "grade_a"
    assert result["expected_price_per_kg"] == 25.0


def test_normalize_demand_data():
    raw = {
        "buyer_id": "B001",
        "crop": "tomatoes",
        "quantity_kg": "500 kg",
        "destination": "  MANGALORE ",
        "deadline": "2026-10-10",
        "max_price_per_kg": "₹30",
        "quality_required": "Grade A",
    }

    result = normalize_demand_data(raw)

    assert result["crop"] == "tomato"
    assert result["quantity_kg"] == 500.0
    assert result["destination"] == "mangalore"
    assert result["quality_required"] == "grade_a"
    assert result["max_price_per_kg"] == 30.0
from Preethesh.AI_Market_Intelligence.supply_intelligence import (
    analyze_supply,
    analyze_supply_batch,
    summarize_supply_intelligence,
)


def test_analyze_supply():
    supply = {
        "id": "SUP-001",
        "farmer_id": "F001",
        "crop": " TOMATOES ",
        "quantity_kg": "150 kg",
        "location": " Mangalore ",
        "available_from": "2026-10-05 08:00",
        "available_until": "2026-10-06 08:00",
        "quality": "Grade A",
        "expected_price_per_kg": "₹25",
    }

    result = analyze_supply(
        supply,
        farmer_reliability=0.9,
    )

    assert result.supply_id == "SUP-001"
    assert result.farmer_id == "F001"
    assert result.crop == "tomato"
    assert result.quantity_kg == 150.0
    assert result.location == "mangalore"
    assert result.quality == "grade_a"
    assert result.expected_price_per_kg == 25.0

    assert result.data_complete is True
    assert result.ready_for_matching is True

    assert result.quantity_strength > 0
    assert result.quality_strength == 1.0
    assert result.availability_strength == 1.0
    assert result.reliability_strength == 0.9

    assert 0 < result.intelligence_score <= 1


def test_analyze_invalid_supply():
    supply = {
        "id": "SUP-002",
        "farmer_id": "F002",
        "crop": "",
        "quantity_kg": "invalid",
        "location": "",
        "available_from": None,
        "available_until": None,
        "quality": "",
        "expected_price_per_kg": None,
    }

    result = analyze_supply(supply)

    assert result.data_complete is False
    assert result.ready_for_matching is False
    assert result.quantity_kg == 0.0
    assert result.warnings


def test_analyze_supply_batch():
    supplies = [
        {
            "id": "SUP-001",
            "farmer_id": "F001",
            "crop": "tomato",
            "quantity_kg": "100 kg",
            "location": "Mangalore",
            "available_from": "2026-10-05",
            "available_until": "2026-10-06",
            "quality": "Grade A",
            "expected_price_per_kg": "25",
        },
        {
            "id": "SUP-002",
            "farmer_id": "F002",
            "crop": "onions",
            "quantity_kg": "200 kg",
            "location": "Udupi",
            "available_from": "2026-10-05",
            "available_until": "2026-10-07",
            "quality": "Grade B",
            "expected_price_per_kg": "30",
        },
    ]

    results = analyze_supply_batch(
        supplies,
        farmer_reliability={
            "F001": 0.9,
            "F002": 0.8,
        },
    )

    assert len(results) == 2
    assert results[0].crop == "tomato"
    assert results[1].crop == "onion"
    assert results[0].reliability_score == 0.9
    assert results[1].reliability_score == 0.8


def test_summarize_supply_intelligence():
    supplies = [
        {
            "id": "SUP-001",
            "farmer_id": "F001",
            "crop": "tomato",
            "quantity_kg": "100 kg",
            "location": "Mangalore",
            "available_from": "2026-10-05",
            "available_until": "2026-10-06",
            "quality": "Grade A",
            "expected_price_per_kg": "25",
        },
        {
            "id": "SUP-002",
            "farmer_id": "F002",
            "crop": "tomatoes",
            "quantity_kg": "150 kg",
            "location": "Udupi",
            "available_from": "2026-10-05",
            "available_until": "2026-10-07",
            "quality": "Grade B",
            "expected_price_per_kg": "27",
        },
    ]

    profiles = analyze_supply_batch(
        supplies,
        farmer_reliability={
            "F001": 0.9,
            "F002": 0.8,
        },
    )

    summary = summarize_supply_intelligence(profiles)

    assert summary["supply_count"] == 2
    assert summary["total_quantity_kg"] == 250.0
    assert summary["ready_for_matching_count"] == 2
    assert summary["crop_totals_kg"]["tomato"] == 250.0
from Preethesh.AI_Market_Intelligence.demand_intelligence import (
    analyze_demand,
    analyze_demand_batch,
)


def test_analyze_demand():
    demand = {
        "id": "DEM-001",
        "buyer_id": "B001",
        "crop": " TOMATOES ",
        "quantity_kg": "500 kg",
        "destination": " MANGALORE ",
        "deadline": "2099-10-10",
        "max_price_per_kg": "₹30",
        "quality_required": "Grade A",
    }

    result = analyze_demand(demand)

    assert result.demand_id == "DEM-001"
    assert result.buyer_id == "B001"
    assert result.crop == "tomato"
    assert result.quantity_kg == 500.0
    assert result.destination == "mangalore"
    assert result.max_price_per_kg == 30.0
    assert result.quality_required == "grade_a"

    assert result.data_complete is True
    assert result.ready_for_matching is True

    assert result.quantity_strength > 0
    assert result.price_capacity == 1.0
    assert result.quality_strength == 1.0
    assert 0 <= result.urgency_score <= 1
    assert 0 < result.intelligence_score <= 1


def test_analyze_urgent_demand():
    demand = {
        "id": "DEM-002",
        "buyer_id": "B002",
        "crop": "onion",
        "quantity_kg": "800 kg",
        "destination": "Udupi",
        "deadline": "2000-01-01",
        "max_price_per_kg": "40",
        "quality_required": "Grade B",
    }

    result = analyze_demand(demand)

    assert result.urgency_score == 1.0
    assert result.data_complete is True


def test_analyze_invalid_demand():
    demand = {
        "id": "DEM-003",
        "buyer_id": "B003",
        "crop": "",
        "quantity_kg": "invalid",
        "destination": "",
        "deadline": None,
        "max_price_per_kg": None,
        "quality_required": "",
    }

    result = analyze_demand(demand)

    assert result.data_complete is False
    assert result.ready_for_matching is False
    assert result.quantity_kg == 0.0
    assert result.warnings


def test_analyze_demand_batch():
    demands = [
        {
            "id": "DEM-001",
            "buyer_id": "B001",
            "crop": "tomato",
            "quantity_kg": "500 kg",
            "destination": "Mangalore",
            "deadline": "2099-10-10",
            "max_price_per_kg": "30",
            "quality_required": "Grade A",
        },
        {
            "id": "DEM-002",
            "buyer_id": "B002",
            "crop": "onions",
            "quantity_kg": "700 kg",
            "destination": "Udupi",
            "deadline": "2099-10-11",
            "max_price_per_kg": "35",
            "quality_required": "Grade B",
        },
    ]

    results = analyze_demand_batch(demands)

    assert len(results) == 2
    assert results[0].crop == "tomato"
    assert results[1].crop == "onion"
    assert results[0].quantity_kg == 500.0
    assert results[1].quantity_kg == 700.0
from Preethesh.AI_Market_Intelligence.candidate_filter import (
    filter_candidate,
    filter_candidates,
    get_eligible_candidates,
)


def _valid_supply(
    supply_id="SUP-001",
    crop="tomato",
    quantity="500 kg",
    available_from="2026-10-05 08:00",
    available_until="2026-10-06 18:00",
    quality="Grade A",
    price="25",
):
    return {
        "id": supply_id,
        "farmer_id": "F001",
        "crop": crop,
        "quantity_kg": quantity,
        "location": "Mangalore",
        "available_from": available_from,
        "available_until": available_until,
        "quality": quality,
        "expected_price_per_kg": price,
    }


def _valid_demand(
    demand_id="DEM-001",
    crop="tomato",
    quantity="400 kg",
    deadline="2026-10-06 12:00",
    max_price="30",
    quality="Grade A",
):
    return {
        "id": demand_id,
        "buyer_id": "B001",
        "crop": crop,
        "quantity_kg": quantity,
        "destination": "Mangalore",
        "deadline": deadline,
        "max_price_per_kg": max_price,
        "quality_required": quality,
    }


def test_filter_valid_candidate():
    result = filter_candidate(
        _valid_supply(),
        _valid_demand(),
    )

    assert result.eligible is True
    assert result.data_valid is True
    assert result.crop_match is True
    assert result.quantity_match is True
    assert result.availability_match is True
    assert result.deadline_match is True
    assert result.price_match is True
    assert result.quality_match is True
    assert result.rejection_reasons == []


def test_filter_wrong_crop():
    result = filter_candidate(
        _valid_supply(crop="onion"),
        _valid_demand(crop="tomato"),
    )

    assert result.eligible is False
    assert result.crop_match is False
    assert any(
        "Wrong crop" in reason
        for reason in result.rejection_reasons
    )


def test_filter_insufficient_quantity():
    result = filter_candidate(
        _valid_supply(quantity="100 kg"),
        _valid_demand(quantity="500 kg"),
    )

    assert result.eligible is False
    assert result.quantity_match is False
    assert "Insufficient supply quantity" in result.rejection_reasons


def test_filter_late_supply():
    result = filter_candidate(
        _valid_supply(
            available_from="2026-10-07 08:00",
        ),
        _valid_demand(
            deadline="2026-10-06 12:00",
        ),
    )

    assert result.eligible is False
    assert result.availability_match is False


def test_filter_price_violation():
    result = filter_candidate(
        _valid_supply(price="40"),
        _valid_demand(max_price="30"),
    )

    assert result.eligible is False
    assert result.price_match is False
    assert (
        "Supply price exceeds buyer maximum price"
        in result.rejection_reasons
    )


def test_filter_quality_mismatch():
    result = filter_candidate(
        _valid_supply(quality="Grade C"),
        _valid_demand(quality="Grade A"),
    )

    assert result.eligible is False
    assert result.quality_match is False


def test_filter_invalid_data():
    supply = _valid_supply(
        crop="",
        quantity="invalid",
        quality="",
        price="invalid",
    )

    result = filter_candidate(
        supply,
        _valid_demand(),
    )

    assert result.eligible is False
    assert result.data_valid is False
    assert len(result.rejection_reasons) >= 4


def test_filter_multiple_candidates():
    supplies = [
        _valid_supply(
            supply_id="SUP-001",
            quantity="500 kg",
        ),
        _valid_supply(
            supply_id="SUP-002",
            crop="onion",
            quantity="500 kg",
        ),
        _valid_supply(
            supply_id="SUP-003",
            quantity="100 kg",
        ),
    ]

    results = filter_candidates(
        supplies,
        _valid_demand(),
    )

    assert len(results) == 3
    assert results[0].eligible is True
    assert results[1].eligible is False
    assert results[2].eligible is False


def test_get_eligible_candidates():
    supplies = [
        _valid_supply(
            supply_id="SUP-001",
            quantity="500 kg",
        ),
        _valid_supply(
            supply_id="SUP-002",
            crop="onion",
            quantity="500 kg",
        ),
    ]

    eligible = get_eligible_candidates(
        supplies,
        _valid_demand(),
    )

    assert len(eligible) == 1
    assert eligible[0].supply_id == "SUP-001"
from Preethesh.AI_Market_Intelligence.matching_engine import (
    calculate_quantity_score,
    calculate_price_score,
    calculate_distance_score,
    calculate_deadline_score,
    calculate_quality_score,
    calculate_reliability_score,
    calculate_weighted_score,
    score_candidate,
    rank_candidates,
    get_best_candidate,
)


def test_quantity_score():
    assert calculate_quantity_score(
        100,
        100,
    ) == 1.0

    assert calculate_quantity_score(
        50,
        100,
    ) == 0.0

    assert (
        calculate_quantity_score(
            120,
            100,
        )
        > 0.9
    )


def test_price_score():
    assert (
        calculate_price_score(
            25,
            30,
        )
        > 0.5
    )

    assert calculate_price_score(
        30,
        30,
    ) == 0.5

    assert calculate_price_score(
        40,
        30,
    ) == 0.0


def test_distance_score():
    assert calculate_distance_score(
        0,
        100,
    ) == 1.0

    assert calculate_distance_score(
        50,
        100,
    ) == 0.5

    assert calculate_distance_score(
        100,
        100,
    ) == 0.0

    assert calculate_distance_score(
        None,
        100,
    ) == 0.5


def test_deadline_score():
    assert (
        calculate_deadline_score(
            "2026-10-05 08:00",
            "2026-10-08 08:00",
        )
        == 1.0
    )

    assert (
        calculate_deadline_score(
            "2026-10-06 08:00",
            "2026-10-06 12:00",
        )
        == 0.3
    )


def test_quality_score():
    assert calculate_quality_score(
        "Grade A",
        "Grade A",
    ) == 1.0

    assert (
        calculate_quality_score(
            "Premium",
            "Grade A",
        )
        >= 0.75
    )

    assert calculate_quality_score(
        "Grade C",
        "Grade A",
    ) == 0.0


def test_reliability_score():
    assert calculate_reliability_score(
        0.9
    ) == 0.9

    assert calculate_reliability_score(
        90
    ) == 0.9


def test_weighted_score():
    score = calculate_weighted_score(
        quantity_score=1.0,
        price_score=1.0,
        distance_score=1.0,
        deadline_score=1.0,
        quality_score=1.0,
        reliability_score=1.0,
    )

    assert score == 1.0


def test_score_candidate():
    supply = _valid_supply(
        supply_id="SUP-001",
        quantity="500 kg",
        price="25",
        quality="Grade A",
    )

    demand = _valid_demand(
        quantity="400 kg",
        max_price="30",
        quality="Grade A",
    )

    score = score_candidate(
        supply=supply,
        demand=demand,
        reliability=0.9,
        distance_km=20,
    )

    assert score.eligible is True
    assert score.supply_id == "SUP-001"
    assert score.demand_id == "DEM-001"

    assert score.quantity_score > 0
    assert score.price_score > 0
    assert score.distance_score > 0
    assert score.deadline_score > 0
    assert score.quality_score == 1.0
    assert score.reliability_score == 0.9

    assert 0 < score.total_score <= 1


def test_ineligible_candidate_keeps_reasons():
    supply = _valid_supply(
        crop="onion",
    )

    demand = _valid_demand(
        crop="tomato",
    )

    score = score_candidate(
        supply=supply,
        demand=demand,
        reliability=0.9,
    )

    assert score.eligible is False
    assert score.total_score == 0.0
    assert score.rejection_reasons


def test_rank_candidates():
    supplies = [
        _valid_supply(
            supply_id="SUP-001",
            quantity="400 kg",
            price="30",
        ),
        _valid_supply(
            supply_id="SUP-002",
            quantity="450 kg",
            price="25",
        ),
        _valid_supply(
            supply_id="SUP-003",
            quantity="100 kg",
            price="20",
        ),
    ]

    demand = _valid_demand(
        quantity="400 kg",
        max_price="30",
    )

    ranked = rank_candidates(
        supplies=supplies,
        demand=demand,
        reliability_map={
            "F001": 0.9,
        },
        distance_map={
            "SUP-001": 40,
            "SUP-002": 10,
            "SUP-003": 5,
        },
    )

    assert len(ranked) == 2

    assert ranked[0].rank == 1
    assert ranked[1].rank == 2

    assert ranked[0].score.total_score >= (
        ranked[1].score.total_score
    )


def test_get_best_candidate():
    supplies = [
        _valid_supply(
            supply_id="SUP-001",
            quantity="400 kg",
            price="29",
        ),
        _valid_supply(
            supply_id="SUP-002",
            quantity="450 kg",
            price="24",
        ),
    ]

    demand = _valid_demand(
        quantity="400 kg",
        max_price="30",
    )

    best = get_best_candidate(
        supplies=supplies,
        demand=demand,
        reliability_map={
            "F001": 0.9,
        },
        distance_map={
            "SUP-001": 50,
            "SUP-002": 10,
        },
    )

    assert best is not None
    assert best.rank == 1
    assert best.supply_id == "SUP-002"
from Preethesh.AI_Market_Intelligence.collective_matcher import (
    find_collective_matches,
    get_best_collective_match,
)
def test_find_collective_matches():
    """Multiple marginal farmers should collectively satisfy demand."""

    demand = _valid_demand(
        demand_id="DEM-COLLECTIVE",
        quantity="500 kg",
    )

    supplies = [
        _valid_supply(
            supply_id="SUP-A",
            quantity="180 kg",
        ),
        _valid_supply(
            supply_id="SUP-B",
            quantity="170 kg",
        ),
        _valid_supply(
            supply_id="SUP-C",
            quantity="200 kg",
        ),
    ]

    matches = find_collective_matches(
        demand,
        supplies,
        max_farmers=3,
    )

    assert matches

    best = matches[0]

    assert best.total_quantity_kg >= 500
    assert best.quantity_coverage_percent == 100.0
    assert best.farmer_count >= 2


def test_best_collective_match():
    """Best collective match should cover the buyer's requirement."""

    demand = _valid_demand(
        demand_id="DEM-BEST",
        quantity="500 kg",
    )

    supplies = [
        _valid_supply(
            supply_id="SUP-1",
            quantity="150 kg",
        ),
        _valid_supply(
            supply_id="SUP-2",
            quantity="200 kg",
        ),
        _valid_supply(
            supply_id="SUP-3",
            quantity="250 kg",
        ),
    ]

    best = get_best_collective_match(
        demand,
        supplies,
        max_farmers=3,
    )

    assert best is not None
    assert best.feasible is True
    assert best.total_quantity_kg >= 500
    assert best.quantity_coverage_percent == 100.0
    assert len(best.supply_ids) >= 2


def test_collective_match_when_no_single_farmer_can_fulfill():
    """Multiple farmers should combine to satisfy a large demand."""

    demand = _valid_demand(
        demand_id="DEM-FRAGMENTED",
        quantity="600 kg",
    )

    supplies = [
        _valid_supply(
            supply_id="SUP-A",
            quantity="200 kg",
        ),
        _valid_supply(
            supply_id="SUP-B",
            quantity="180 kg",
        ),
        _valid_supply(
            supply_id="SUP-C",
            quantity="250 kg",
        ),
    ]

    best = get_best_collective_match(
        demand,
        supplies,
        max_farmers=3,
    )

    assert best is not None
    assert best.feasible is True
    assert best.total_quantity_kg >= 600
    assert best.farmer_count == 3


def test_collective_match_returns_none_when_supply_is_insufficient():
    """No match should be returned when total supply is insufficient."""

    demand = _valid_demand(
        demand_id="DEM-SHORT",
        quantity="1000 kg",
    )

    supplies = [
        _valid_supply(
            supply_id="SUP-A",
            quantity="200 kg",
        ),
        _valid_supply(
            supply_id="SUP-B",
            quantity="250 kg",
        ),
    ]

    best = get_best_collective_match(
        demand,
        supplies,
        max_farmers=3,
    )

    assert best is None