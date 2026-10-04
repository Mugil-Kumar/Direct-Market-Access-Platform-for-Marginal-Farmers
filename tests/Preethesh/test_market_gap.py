from Preethesh.AI_Market_Intelligence.market_gap import (
    analyze_market_gap,
    calculate_market_gap,
    get_market_gap,
)


def test_shortage_is_detected():
    result = calculate_market_gap(
        crop="tomato",
        demand_quantity_kg=500,
        available_supply_quantity_kg=300,
    )

    assert result.crop == "tomato"
    assert result.shortage_quantity_kg == 200
    assert result.surplus_quantity_kg == 0
    assert result.status == "shortage"
    assert result.recommended_additional_supply_kg == 200


def test_surplus_is_detected():
    result = calculate_market_gap(
        crop="onion",
        demand_quantity_kg=300,
        available_supply_quantity_kg=500,
    )

    assert result.shortage_quantity_kg == 0
    assert result.surplus_quantity_kg == 200
    assert result.status == "surplus"


def test_balanced_market():
    result = calculate_market_gap(
        crop="potato",
        demand_quantity_kg=400,
        available_supply_quantity_kg=400,
    )

    assert result.shortage_quantity_kg == 0
    assert result.surplus_quantity_kg == 0
    assert result.status == "balanced"


def test_analyze_multiple_crops():
    demands = [
        {"crop": "tomato", "quantity_kg": 500},
        {"crop": "onion", "quantity_kg": 300},
    ]

    supplies = [
        {"crop": "tomato", "quantity_kg": 200},
        {"crop": "onion", "quantity_kg": 500},
    ]

    results = analyze_market_gap(
        demands=demands,
        supplies=supplies,
    )

    assert len(results) == 2

    tomato = next(
        result for result in results
        if result.crop == "tomato"
    )

    onion = next(
        result for result in results
        if result.crop == "onion"
    )

    assert tomato.status == "shortage"
    assert tomato.shortage_quantity_kg == 300

    assert onion.status == "surplus"
    assert onion.surplus_quantity_kg == 200


def test_counts_and_location():
    result = calculate_market_gap(
        crop="rice",
        demand_quantity_kg=1000,
        available_supply_quantity_kg=800,
        demand_count=3,
        supply_count=5,
        location="Bengaluru",
    )

    assert result.demand_count == 3
    assert result.supply_count == 5
    assert result.location == "Bengaluru"


def test_string_quantities_are_normalized():
    result = calculate_market_gap(
        crop="tomato",
        demand_quantity_kg="500 kg",
        available_supply_quantity_kg="350 kg",
    )

    assert result.demand_quantity_kg == 500
    assert result.available_supply_quantity_kg == 350
    assert result.shortage_quantity_kg == 150


def test_invalid_records_are_ignored():
    demands = [
        {"crop": "", "quantity_kg": 500},
        {"crop": "tomato", "quantity_kg": 0},
        {"crop": "onion", "quantity_kg": 300},
    ]

    supplies = [
        {"crop": "onion", "quantity_kg": 100},
    ]

    results = analyze_market_gap(
        demands=demands,
        supplies=supplies,
    )

    assert len(results) == 1
    assert results[0].crop == "onion"
    assert results[0].shortage_quantity_kg == 200


def test_get_market_gap_alias():
    results = get_market_gap(
        demands=[{"crop": "rice", "quantity_kg": 100}],
        supplies=[{"crop": "rice", "quantity_kg": 100}],
    )

    assert len(results) == 1
    assert results[0].status == "balanced"