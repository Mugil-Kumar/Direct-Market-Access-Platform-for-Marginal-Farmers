from pathlib import Path

from Disha.Marketplace_Data_Logistics.api import MarketplaceService
from Disha.Marketplace_Data_Logistics.database import Database
from shared.schemas.schemas import Buyer, Demand, Farmer, Order, Supply


def create_marketplace(tmp_path: Path) -> MarketplaceService:
    """
    Create a fresh marketplace backed by an isolated temporary database.

    Each test gets its own SQLite database so data from one test
    cannot affect another test.
    """
    database = Database(str(tmp_path / "test_agriweave.db"))
    return MarketplaceService(database)


def test_farmer_registration(tmp_path: Path):
    marketplace = create_marketplace(tmp_path)

    farmer = Farmer(
        id="F001",
        name="Ramesh",
        location="Mangaluru",
        phone="9999999999",
    )

    registered_farmer = marketplace.register_farmer(farmer)

    assert registered_farmer.id == "F001"
    assert registered_farmer.name == "Ramesh"
    assert registered_farmer.location == "Mangaluru"

    stored_farmer = marketplace.get_farmer("F001")

    assert stored_farmer.id == "F001"
    assert stored_farmer.name == "Ramesh"


def test_buyer_registration(tmp_path: Path):
    marketplace = create_marketplace(tmp_path)

    buyer = Buyer(
        id="B001",
        name="FreshMart",
        location="Mangaluru",
        phone="8888888888",
    )

    registered_buyer = marketplace.register_buyer(buyer)

    assert registered_buyer.id == "B001"
    assert registered_buyer.name == "FreshMart"
    assert registered_buyer.location == "Mangaluru"

    stored_buyer = marketplace.get_buyer("B001")

    assert stored_buyer.id == "B001"
    assert stored_buyer.name == "FreshMart"


def test_supply_requires_registered_farmer(tmp_path: Path):
    marketplace = create_marketplace(tmp_path)

    supply = Supply(
        id="S001",
        farmer_id="F999",
        crop="Tomato",
        quantity_kg=100.0,
        location="Mangaluru",
        available_from="2026-10-20",
        available_until="2026-10-25",
        quality="Grade A",
        expected_price_per_kg=30.0,
    )

    try:
        marketplace.list_supply(supply)
        assert False, "Expected ValueError for unregistered farmer."
    except ValueError as error:
        assert "not registered" in str(error)


def test_demand_requires_registered_buyer(tmp_path: Path):
    marketplace = create_marketplace(tmp_path)

    demand = Demand(
        id="D001",
        buyer_id="B999",
        crop="Tomato",
        quantity_kg=200.0,
        destination="Mangaluru",
        deadline="2026-10-25",
        max_price_per_kg=35.0,
        quality_required="Grade A",
    )

    try:
        marketplace.create_demand(demand)
        assert False, "Expected ValueError for unregistered buyer."
    except ValueError as error:
        assert "not registered" in str(error)


def test_supply_discovery_by_crop(tmp_path: Path):
    marketplace = create_marketplace(tmp_path)

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
        quantity_kg=100.0,
        location="Mangaluru",
        available_from="2026-10-20",
        available_until="2026-10-25",
        quality="Grade A",
        expected_price_per_kg=30.0,
    )

    banana_supply = Supply(
        id="S002",
        farmer_id="F001",
        crop="Banana",
        quantity_kg=150.0,
        location="Mangaluru",
        available_from="2026-10-20",
        available_until="2026-10-25",
        quality="Grade A",
        expected_price_per_kg=25.0,
    )

    marketplace.list_supply(tomato_supply)
    marketplace.list_supply(banana_supply)

    tomato_supplies = marketplace.find_supply_for_crop("Tomato")

    assert len(tomato_supplies) == 1
    assert tomato_supplies[0].id == "S001"
    assert tomato_supplies[0].crop == "Tomato"


def test_order_reserves_supply_and_updates_demand(tmp_path: Path):
    marketplace = create_marketplace(tmp_path)

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
        quantity_kg=100.0,
        location="Mangaluru",
        available_from="2026-10-20",
        available_until="2026-10-25",
        quality="Grade A",
        expected_price_per_kg=30.0,
    )

    demand = Demand(
        id="D001",
        buyer_id="B001",
        crop="Tomato",
        quantity_kg=100.0,
        destination="Mangaluru",
        deadline="2026-10-25",
        max_price_per_kg=35.0,
        quality_required="Grade A",
    )

    marketplace.list_supply(supply)
    marketplace.create_demand(demand)

    order = Order(
        id="O001",
        demand_id="D001",
        supply_ids=["S001"],
        quantity_kg=100.0,
        selling_price_per_kg=32.0,
    )

    created_order = marketplace.create_order(order)

    assert created_order.id == "O001"
    assert created_order.status == "pending"

    stored_supply = marketplace.supplies.get("S001")
    assert stored_supply is not None
    assert stored_supply.status == "reserved"

    stored_demand = marketplace.demands.get("D001")
    assert stored_demand is not None
    assert stored_demand.status == "fulfilled"


def test_partial_order_marks_demand_partially_matched(tmp_path: Path):
    marketplace = create_marketplace(tmp_path)

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
        quantity_kg=50.0,
        location="Mangaluru",
        available_from="2026-10-20",
        available_until="2026-10-25",
        quality="Grade A",
        expected_price_per_kg=30.0,
    )

    demand = Demand(
        id="D001",
        buyer_id="B001",
        crop="Tomato",
        quantity_kg=100.0,
        destination="Mangaluru",
        deadline="2026-10-25",
        max_price_per_kg=35.0,
        quality_required="Grade A",
    )

    marketplace.list_supply(supply)
    marketplace.create_demand(demand)

    order = Order(
        id="O001",
        demand_id="D001",
        supply_ids=["S001"],
        quantity_kg=50.0,
        selling_price_per_kg=32.0,
    )

    marketplace.create_order(order)

    stored_demand = marketplace.demands.get("D001")

    assert stored_demand is not None
    assert stored_demand.status == "partially_matched"


def test_order_net_realization(tmp_path: Path):
    marketplace = create_marketplace(tmp_path)

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
        quantity_kg=100.0,
        location="Mangaluru",
        available_from="2026-10-20",
        available_until="2026-10-25",
        quality="Grade A",
        expected_price_per_kg=30.0,
    )

    demand = Demand(
        id="D001",
        buyer_id="B001",
        crop="Tomato",
        quantity_kg=100.0,
        destination="Mangaluru",
        deadline="2026-10-25",
        max_price_per_kg=35.0,
        quality_required="Grade A",
    )

    marketplace.list_supply(supply)
    marketplace.create_demand(demand)

    order = Order(
        id="O001",
        demand_id="D001",
        supply_ids=["S001"],
        quantity_kg=100.0,
        selling_price_per_kg=32.0,
        transport_cost=100.0,
        collection_cost=50.0,
        packaging_cost=25.0,
        spoilage_cost=10.0,
        platform_fee=15.0,
    )

    marketplace.create_order(order)

    net_realization = marketplace.calculate_order_net_realization("O001")

    expected_gross_value = 100.0 * 32.0
    expected_cost = 100.0 + 50.0 + 25.0 + 10.0 + 15.0
    expected_net_realization = expected_gross_value - expected_cost

    assert net_realization == expected_net_realization