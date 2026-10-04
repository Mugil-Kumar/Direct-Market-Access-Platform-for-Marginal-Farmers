from pathlib import Path

from Disha.Marketplace_Data_Logistics.api import MarketplaceService
from Disha.Marketplace_Data_Logistics.database import Database
from Disha.Marketplace_Data_Logistics.location import LocationService
from Disha.Marketplace_Data_Logistics.marketplace_gateway import (
    MarketplaceGateway,
)
from shared.schemas.schemas import (
    Buyer,
    Demand,
    Farmer,
    Location,
    Supply,
)


def create_gateway(tmp_path: Path) -> MarketplaceGateway:
    database = Database(
        str(tmp_path / "gateway_test.db")
    )

    marketplace = MarketplaceService(database)
    location_service = LocationService(database)

    return MarketplaceGateway(
        marketplace=marketplace,
        location_service=location_service,
    )


def seed_marketplace(gateway: MarketplaceGateway) -> None:
    gateway.marketplace.register_farmer(
        Farmer(
            id="F001",
            name="Farmer One",
            location="Udupi",
            phone="9999999999",
            reliability_score=0.9,
        )
    )

    gateway.marketplace.register_buyer(
        Buyer(
            id="B001",
            name="Buyer One",
            location="Mangaluru",
            phone="8888888888",
            reliability_score=0.95,
        )
    )

    gateway.marketplace.list_supply(
        Supply(
            id="S001",
            farmer_id="F001",
            crop="Tomato",
            quantity_kg=100.0,
            location="Udupi",
            available_from="2026-10-20",
            available_until="2026-10-25",
            quality="Grade A",
            expected_price_per_kg=30.0,
        )
    )

    gateway.marketplace.create_demand(
        Demand(
            id="D001",
            buyer_id="B001",
            crop="Tomato",
            quantity_kg=80.0,
            destination="Mangaluru",
            deadline="2026-10-25",
            max_price_per_kg=35.0,
            quality_required="Grade A",
        )
    )

    gateway.location_service.save_location(
        Location(
            entity_type="farmer",
            entity_id="F001",
            latitude=13.3409,
            longitude=74.7421,
            address="Udupi",
        )
    )

    gateway.location_service.save_location(
        Location(
            entity_type="buyer",
            entity_id="B001",
            latitude=12.9141,
            longitude=74.8560,
            address="Mangaluru",
        )
    )


def test_gateway_returns_available_supply(tmp_path: Path):
    gateway = create_gateway(tmp_path)
    seed_marketplace(gateway)

    supplies = gateway.get_available_supply()

    assert len(supplies) == 1
    assert supplies[0].id == "S001"
    assert supplies[0].status == "available"


def test_gateway_filters_supply_by_crop(tmp_path: Path):
    gateway = create_gateway(tmp_path)
    seed_marketplace(gateway)

    supplies = gateway.get_available_supply("Tomato")

    assert len(supplies) == 1
    assert supplies[0].crop == "Tomato"


def test_gateway_returns_open_demands(tmp_path: Path):
    gateway = create_gateway(tmp_path)
    seed_marketplace(gateway)

    demands = gateway.get_open_demands()

    assert len(demands) == 1
    assert demands[0].id == "D001"
    assert demands[0].status == "open"


def test_gateway_filters_demands_by_crop(tmp_path: Path):
    gateway = create_gateway(tmp_path)
    seed_marketplace(gateway)

    demands = gateway.get_open_demands("Tomato")

    assert len(demands) == 1
    assert demands[0].crop == "Tomato"


def test_gateway_returns_entity_location(tmp_path: Path):
    gateway = create_gateway(tmp_path)
    seed_marketplace(gateway)

    location = gateway.get_entity_location(
        "farmer",
        "F001",
    )

    assert location is not None
    assert location.entity_id == "F001"
    assert location.latitude == 13.3409
    assert location.longitude == 74.7421


def test_gateway_generates_route_for_supply_and_demand(
    tmp_path: Path,
):
    gateway = create_gateway(tmp_path)
    seed_marketplace(gateway)

    route = gateway.get_route_for_supply_and_demand(
        "S001",
        "D001",
    )

    assert route.origin_entity_type == "farmer"
    assert route.origin_entity_id == "F001"
    assert route.destination_entity_type == "buyer"
    assert route.destination_entity_id == "B001"
    assert route.distance_km > 0
    assert route.estimated_travel_time_hours > 0
    assert route.estimated_transport_cost > 0


def test_gateway_provides_ai_matching_candidates(
    tmp_path: Path,
):
    gateway = create_gateway(tmp_path)
    seed_marketplace(gateway)

    result = gateway.get_matching_candidates("Tomato")

    assert result["supply_count"] == 1
    assert result["demand_count"] == 1
    assert result["supplies"][0]["id"] == "S001"
    assert result["demands"][0]["id"] == "D001"


def test_gateway_matching_candidates_are_structured(
    tmp_path: Path,
):
    gateway = create_gateway(tmp_path)
    seed_marketplace(gateway)

    result = gateway.get_matching_candidates()

    supply = result["supplies"][0]
    demand = result["demands"][0]

    assert supply["farmer_id"] == "F001"
    assert supply["quantity_kg"] == 100.0
    assert supply["status"] == "available"

    assert demand["buyer_id"] == "B001"
    assert demand["quantity_kg"] == 80.0
    assert demand["status"] == "open"


def test_gateway_provides_optimization_input(
    tmp_path: Path,
):
    gateway = create_gateway(tmp_path)
    seed_marketplace(gateway)

    result = gateway.get_optimization_input("Tomato")

    assert result["supply_count"] == 1
    assert result["demand_count"] == 1

    supply_data = result["supplies"][0]
    demand_data = result["demands"][0]

    assert supply_data["supply"]["id"] == "S001"
    assert supply_data["farmer_location"]["entity_id"] == "F001"

    assert demand_data["demand"]["id"] == "D001"
    assert demand_data["buyer_location"]["entity_id"] == "B001"


def test_gateway_provides_verification_snapshot(
    tmp_path: Path,
):
    gateway = create_gateway(tmp_path)
    seed_marketplace(gateway)

    result = gateway.get_verification_snapshot()

    assert result["supply_count"] == 1
    assert result["demand_count"] == 1
    assert result["order_count"] == 0
    assert result["supplies"][0]["id"] == "S001"
    assert result["demands"][0]["id"] == "D001"


def test_gateway_provides_complete_marketplace_snapshot(
    tmp_path: Path,
):
    gateway = create_gateway(tmp_path)
    seed_marketplace(gateway)

    result = gateway.get_marketplace_snapshot()

    assert result["counts"]["farmers"] == 1
    assert result["counts"]["buyers"] == 1
    assert result["counts"]["supplies"] == 1
    assert result["counts"]["demands"] == 1
    assert result["counts"]["orders"] == 0

    assert result["farmers"][0]["id"] == "F001"
    assert result["buyers"][0]["id"] == "B001"
    assert result["supplies"][0]["id"] == "S001"
    assert result["demands"][0]["id"] == "D001"


def test_gateway_reflects_latest_supply_state(
    tmp_path: Path,
):
    gateway = create_gateway(tmp_path)
    seed_marketplace(gateway)

    before = gateway.get_matching_candidates()

    assert before["supply_count"] == 1

    gateway.marketplace.supplies.reserve("S001")

    after = gateway.get_matching_candidates()

    assert after["supply_count"] == 0


def test_gateway_reflects_latest_demand_state(
    tmp_path: Path,
):
    gateway = create_gateway(tmp_path)
    seed_marketplace(gateway)

    before = gateway.get_matching_candidates()

    assert before["demand_count"] == 1

    gateway.marketplace.demands.cancel("D001")

    after = gateway.get_matching_candidates()

    assert after["demand_count"] == 0
    