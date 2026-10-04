from pathlib import Path

from Disha.Marketplace_Data_Logistics.database import Database
from Disha.Marketplace_Data_Logistics.demand import DemandRegistry
from Disha.Marketplace_Data_Logistics.orders import OrderRegistry
from Disha.Marketplace_Data_Logistics.supply import SupplyRegistry
from shared.schemas.schemas import Demand, Order, Supply


def test_database_creates_required_tables(tmp_path: Path):
    db = Database(str(tmp_path / "test_agriweave.db"))

    rows = db.fetch_all(
        "SELECT name FROM sqlite_master WHERE type = 'table'"
    )

    table_names = {row["name"] for row in rows}

    assert "farmers" in table_names
    assert "buyers" in table_names
    assert "supplies" in table_names
    assert "demands" in table_names
    assert "orders" in table_names
    assert "order_supplies" in table_names
    assert "locations" in table_names


def test_database_can_store_and_read_farmer(tmp_path: Path):
    db = Database(str(tmp_path / "test_agriweave.db"))

    db.execute(
        """
        INSERT INTO farmers
        (id, name, location, phone, reliability_score)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            "F001",
            "Test Farmer",
            "Mangaluru",
            "9999999999",
            0.9,
        ),
    )

    farmer = db.fetch_one(
        "SELECT * FROM farmers WHERE id = ?",
        ("F001",),
    )

    assert farmer is not None
    assert farmer["name"] == "Test Farmer"
    assert farmer["location"] == "Mangaluru"
    assert farmer["reliability_score"] == 0.9


def test_supply_persists_to_database(tmp_path: Path):
    db = Database(str(tmp_path / "test_agriweave.db"))
    registry = SupplyRegistry(db)

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

    registry.add(supply)

    stored = db.fetch_one(
        "SELECT * FROM supplies WHERE id = ?",
        ("S001",),
    )

    assert stored is not None
    assert stored["farmer_id"] == "F001"
    assert stored["crop"] == "Tomato"
    assert stored["quantity_kg"] == 100.0
    assert stored["location"] == "Mangaluru"
    assert stored["status"] == "available"


def test_supply_status_persists_to_database(tmp_path: Path):
    db = Database(str(tmp_path / "test_agriweave.db"))
    registry = SupplyRegistry(db)

    supply = Supply(
        id="S002",
        farmer_id="F001",
        crop="Banana",
        quantity_kg=150.0,
        location="Udupi",
        available_from="2026-10-20",
        available_until="2026-10-25",
        quality="Grade A",
        expected_price_per_kg=25.0,
    )

    registry.add(supply)

    registry.reserve("S002")

    stored = db.fetch_one(
        "SELECT status FROM supplies WHERE id = ?",
        ("S002",),
    )

    assert stored is not None
    assert stored["status"] == "reserved"

    registry.release("S002")

    stored = db.fetch_one(
        "SELECT status FROM supplies WHERE id = ?",
        ("S002",),
    )

    assert stored is not None
    assert stored["status"] == "available"


def test_supply_survives_registry_reload(tmp_path: Path):
    db = Database(str(tmp_path / "test_agriweave.db"))

    first_registry = SupplyRegistry(db)

    supply = Supply(
        id="S003",
        farmer_id="F002",
        crop="Coconut",
        quantity_kg=200.0,
        location="Udupi",
        available_from="2026-10-20",
        available_until="2026-10-30",
        quality="Grade A",
        expected_price_per_kg=40.0,
    )

    first_registry.add(supply)

    second_registry = SupplyRegistry(db)

    loaded_supply = second_registry.get("S003")

    assert loaded_supply is not None
    assert loaded_supply.id == "S003"
    assert loaded_supply.crop == "Coconut"
    assert loaded_supply.quantity_kg == 200.0
    assert loaded_supply.location == "Udupi"
    assert loaded_supply.status == "available"


def test_demand_persists_to_database(tmp_path: Path):
    db = Database(str(tmp_path / "test_agriweave.db"))
    registry = DemandRegistry(db)

    demand = Demand(
        id="D001",
        buyer_id="B001",
        crop="Tomato",
        quantity_kg=200.0,
        destination="Mangaluru",
        deadline="2026-10-25",
        max_price_per_kg=35.0,
        quality_required="Grade A",
    )

    registry.add(demand)

    stored = db.fetch_one(
        "SELECT * FROM demands WHERE id = ?",
        ("D001",),
    )

    assert stored is not None
    assert stored["buyer_id"] == "B001"
    assert stored["crop"] == "Tomato"
    assert stored["quantity_kg"] == 200.0
    assert stored["destination"] == "Mangaluru"
    assert stored["deadline"] == "2026-10-25"
    assert stored["max_price_per_kg"] == 35.0
    assert stored["quality_required"] == "Grade A"
    assert stored["status"] == "open"


def test_demand_status_persists_to_database(tmp_path: Path):
    db = Database(str(tmp_path / "test_agriweave.db"))
    registry = DemandRegistry(db)

    demand = Demand(
        id="D002",
        buyer_id="B001",
        crop="Banana",
        quantity_kg=150.0,
        destination="Udupi",
        deadline="2026-10-28",
        max_price_per_kg=30.0,
        quality_required="Grade A",
    )

    registry.add(demand)

    registry.mark_partially_matched("D002")

    stored = db.fetch_one(
        "SELECT status FROM demands WHERE id = ?",
        ("D002",),
    )

    assert stored is not None
    assert stored["status"] == "partially_matched"

    registry.fulfill("D002")

    stored = db.fetch_one(
        "SELECT status FROM demands WHERE id = ?",
        ("D002",),
    )

    assert stored is not None
    assert stored["status"] == "fulfilled"


def test_demand_survives_registry_reload(tmp_path: Path):
    db = Database(str(tmp_path / "test_agriweave.db"))

    first_registry = DemandRegistry(db)

    demand = Demand(
        id="D003",
        buyer_id="B002",
        crop="Coconut",
        quantity_kg=300.0,
        destination="Kundapura",
        deadline="2026-10-30",
        max_price_per_kg=45.0,
        quality_required="Grade A",
    )

    first_registry.add(demand)

    second_registry = DemandRegistry(db)

    loaded_demand = second_registry.get("D003")

    assert loaded_demand is not None
    assert loaded_demand.id == "D003"
    assert loaded_demand.buyer_id == "B002"
    assert loaded_demand.crop == "Coconut"
    assert loaded_demand.quantity_kg == 300.0
    assert loaded_demand.destination == "Kundapura"
    assert loaded_demand.max_price_per_kg == 45.0
    assert loaded_demand.status == "open"


def test_order_persists_to_database(tmp_path: Path):
    db = Database(str(tmp_path / "test_agriweave.db"))
    registry = OrderRegistry(db)

    order = Order(
        id="O001",
        demand_id="D001",
        supply_ids=["S001", "S002"],
        quantity_kg=150.0,
        selling_price_per_kg=32.0,
        transport_cost=100.0,
        collection_cost=50.0,
        packaging_cost=25.0,
        spoilage_cost=10.0,
        platform_fee=15.0,
    )

    registry.create(order)

    stored = db.fetch_one(
        "SELECT * FROM orders WHERE id = ?",
        ("O001",),
    )

    assert stored is not None
    assert stored["demand_id"] == "D001"
    assert stored["quantity_kg"] == 150.0
    assert stored["selling_price_per_kg"] == 32.0
    assert stored["transport_cost"] == 100.0
    assert stored["collection_cost"] == 50.0
    assert stored["packaging_cost"] == 25.0
    assert stored["spoilage_cost"] == 10.0
    assert stored["platform_fee"] == 15.0
    assert stored["status"] == "pending"


def test_order_supply_links_persist_to_database(tmp_path: Path):
    db = Database(str(tmp_path / "test_agriweave.db"))
    registry = OrderRegistry(db)

    order = Order(
        id="O002",
        demand_id="D002",
        supply_ids=["S010", "S011"],
        quantity_kg=200.0,
        selling_price_per_kg=40.0,
    )

    registry.create(order)

    rows = db.fetch_all(
        """
        SELECT supply_id
        FROM order_supplies
        WHERE order_id = ?
        ORDER BY supply_id
        """,
        ("O002",),
    )

    supply_ids = [
        row["supply_id"]
        for row in rows
    ]

    assert supply_ids == ["S010", "S011"]


def test_order_survives_registry_reload(tmp_path: Path):
    db = Database(str(tmp_path / "test_agriweave.db"))

    first_registry = OrderRegistry(db)

    order = Order(
        id="O003",
        demand_id="D003",
        supply_ids=["S020", "S021"],
        quantity_kg=175.0,
        selling_price_per_kg=38.0,
        transport_cost=120.0,
        collection_cost=40.0,
        packaging_cost=20.0,
        spoilage_cost=15.0,
        platform_fee=10.0,
    )

    first_registry.create(order)

    second_registry = OrderRegistry(db)

    loaded_order = second_registry.get("O003")

    assert loaded_order is not None
    assert loaded_order.id == "O003"
    assert loaded_order.demand_id == "D003"
    assert loaded_order.supply_ids == ["S020", "S021"]
    assert loaded_order.quantity_kg == 175.0
    assert loaded_order.selling_price_per_kg == 38.0
    assert loaded_order.transport_cost == 120.0
    assert loaded_order.collection_cost == 40.0
    assert loaded_order.packaging_cost == 20.0
    assert loaded_order.spoilage_cost == 15.0
    assert loaded_order.platform_fee == 10.0
    assert loaded_order.status == "pending"


def test_order_status_persists_to_database(tmp_path: Path):
    db = Database(str(tmp_path / "test_agriweave.db"))
    registry = OrderRegistry(db)

    order = Order(
        id="O004",
        demand_id="D004",
        supply_ids=["S030"],
        quantity_kg=100.0,
        selling_price_per_kg=35.0,
    )

    registry.create(order)

    registry.update_status(
        "O004",
        "confirmed",
    )

    stored = db.fetch_one(
        "SELECT status FROM orders WHERE id = ?",
        ("O004",),
    )

    assert stored is not None
    assert stored["status"] == "confirmed"

    registry.update_status(
        "O004",
        "in_transit",
    )

    stored = db.fetch_one(
        "SELECT status FROM orders WHERE id = ?",
        ("O004",),
    )

    assert stored is not None
    assert stored["status"] == "in_transit"