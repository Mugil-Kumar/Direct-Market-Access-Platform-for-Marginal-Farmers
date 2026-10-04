from shared.schemas.schemas import (
    Buyer,
    Demand,
    Farmer,
    Order,
    Supply,
)

from Disha.Marketplace_Data_Logistics.api import MarketplaceService


def create_marketplace() -> MarketplaceService:
    return MarketplaceService()


def test_farmer_registration():
    marketplace = create_marketplace()

    farmer = Farmer(
        id="F001",
        name="Ramesh",
        location="Mangaluru",
        phone="9876543210",
    )

    registered = marketplace.register_farmer(farmer)

    assert registered.id == "F001"
    assert marketplace.get_farmer("F001").name == "Ramesh"


def test_buyer_registration():
    marketplace = create_marketplace()

    buyer = Buyer(
        id="B001",
        name="FreshMart",
        location="Mangaluru",
        phone="9876500000",
    )

    registered = marketplace.register_buyer(buyer)

    assert registered.id == "B001"
    assert marketplace.get_buyer("B001").name == "FreshMart"


def test_supply_requires_registered_farmer():
    marketplace = create_marketplace()

    supply = Supply(
        id="S001",
        farmer_id="UNKNOWN",
        crop="Tomato",
        quantity_kg=100,
        location="Mangaluru",
        available_from="2026-10-05",
        available_until="2026-10-07",
        quality="A",
        expected_price_per_kg=30,
    )

    try:
        marketplace.list_supply(supply)
        assert False, "Expected ValueError"
    except ValueError as error:
        assert "not registered" in str(error)


def test_demand_requires_registered_buyer():
    marketplace = create_marketplace()

    demand = Demand(
        id="D001",
        buyer_id="UNKNOWN",
        crop="Tomato",
        quantity_kg=100,
        destination="Mangaluru",
        deadline="2026-10-07",
        max_price_per_kg=40,
        quality_required="A",
    )

    try:
        marketplace.create_demand(demand)
        assert False, "Expected ValueError"
    except ValueError as error:
        assert "not registered" in str(error)


def test_supply_discovery_by_crop():
    marketplace = create_marketplace()

    farmer = Farmer(
        id="F001",
        name="Ramesh",
        location="Mangaluru",
    )

    marketplace.register_farmer(farmer)

    tomato_supply = Supply(
        id="S001",
        farmer_id="F001",
        crop="Tomato",
        quantity_kg=100,
        location="Mangaluru",
        available_from="2026-10-05",
        available_until="2026-10-07",
        quality="A",
        expected_price_per_kg=30,
    )

    onion_supply = Supply(
        id="S002",
        farmer_id="F001",
        crop="Onion",
        quantity_kg=150,
        location="Mangaluru",
        available_from="2026-10-05",
        available_until="2026-10-07",
        quality="A",
        expected_price_per_kg=25,
    )

    marketplace.list_supply(tomato_supply)
    marketplace.list_supply(onion_supply)

    tomato_results = marketplace.find_supply_for_crop("tomato")

    assert len(tomato_results) == 1
    assert tomato_results[0].id == "S001"


def test_order_reserves_supply_and_updates_demand():
    marketplace = create_marketplace()

    farmer = Farmer(
        id="F001",
        name="Ramesh",
        location="Mangaluru",
    )

    buyer = Buyer(
        id="B001",
        name="FreshMart",
        location="Mangaluru",
    )

    marketplace.register_farmer(farmer)
    marketplace.register_buyer(buyer)

    supply = Supply(
        id="S001",
        farmer_id="F001",
        crop="Tomato",
        quantity_kg=100,
        location="Mangaluru",
        available_from="2026-10-05",
        available_until="2026-10-07",
        quality="A",
        expected_price_per_kg=30,
    )

    demand = Demand(
        id="D001",
        buyer_id="B001",
        crop="Tomato",
        quantity_kg=80,
        destination="Mangaluru",
        deadline="2026-10-07",
        max_price_per_kg=40,
        quality_required="A",
    )

    marketplace.list_supply(supply)
    marketplace.create_demand(demand)

    order = Order(
        id="O001",
        demand_id="D001",
        supply_ids=["S001"],
        quantity_kg=80,
        selling_price_per_kg=35,
        transport_cost=200,
        collection_cost=50,
        packaging_cost=30,
        spoilage_cost=20,
        platform_fee=10,
    )

    created_order = marketplace.create_order(order)

    assert created_order.id == "O001"
    assert marketplace.supplies.get("S001").status == "reserved"
    assert marketplace.demands.get("D001").status == "fulfilled"


def test_partial_order_marks_demand_partially_matched():
    marketplace = create_marketplace()

    farmer = Farmer(
        id="F001",
        name="Ramesh",
        location="Mangaluru",
    )

    buyer = Buyer(
        id="B001",
        name="FreshMart",
        location="Mangaluru",
    )

    marketplace.register_farmer(farmer)
    marketplace.register_buyer(buyer)

    supply = Supply(
        id="S001",
        farmer_id="F001",
        crop="Tomato",
        quantity_kg=50,
        location="Mangaluru",
        available_from="2026-10-05",
        available_until="2026-10-07",
        quality="A",
        expected_price_per_kg=30,
    )

    demand = Demand(
        id="D001",
        buyer_id="B001",
        crop="Tomato",
        quantity_kg=100,
        destination="Mangaluru",
        deadline="2026-10-07",
        max_price_per_kg=40,
        quality_required="A",
    )

    marketplace.list_supply(supply)
    marketplace.create_demand(demand)

    order = Order(
        id="O001",
        demand_id="D001",
        supply_ids=["S001"],
        quantity_kg=50,
        selling_price_per_kg=35,
    )

    marketplace.create_order(order)

    assert marketplace.demands.get("D001").status == "partially_matched"


def test_order_net_realization():
    marketplace = create_marketplace()

    farmer = Farmer(
        id="F001",
        name="Ramesh",
        location="Mangaluru",
    )

    buyer = Buyer(
        id="B001",
        name="FreshMart",
        location="Mangaluru",
    )

    marketplace.register_farmer(farmer)
    marketplace.register_buyer(buyer)

    supply = Supply(
        id="S001",
        farmer_id="F001",
        crop="Tomato",
        quantity_kg=100,
        location="Mangaluru",
        available_from="2026-10-05",
        available_until="2026-10-07",
        quality="A",
        expected_price_per_kg=30,
    )

    demand = Demand(
        id="D001",
        buyer_id="B001",
        crop="Tomato",
        quantity_kg=50,
        destination="Mangaluru",
        deadline="2026-10-07",
        max_price_per_kg=40,
        quality_required="A",
    )

    marketplace.list_supply(supply)
    marketplace.create_demand(demand)

    order = Order(
        id="O001",
        demand_id="D001",
        supply_ids=["S001"],
        quantity_kg=50,
        selling_price_per_kg=40,
        transport_cost=100,
        collection_cost=50,
        packaging_cost=25,
        spoilage_cost=10,
        platform_fee=15,
    )

    marketplace.create_order(order)

    # Gross = 50 * 40 = 2000
    # Costs = 100 + 50 + 25 + 10 + 15 = 200
    # Net realization = 1800
    net = marketplace.calculate_order_net_realization("O001")

    assert net == 1800