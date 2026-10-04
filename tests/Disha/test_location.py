from pathlib import Path

import pytest

from Disha.Marketplace_Data_Logistics.database import Database
from Disha.Marketplace_Data_Logistics.location import LocationService
from shared.schemas.schemas import Location


def create_service(tmp_path: Path) -> LocationService:
    db = Database(str(tmp_path / "location_test.db"))
    return LocationService(db)


def test_save_and_get_farmer_location(tmp_path: Path):
    service = create_service(tmp_path)

    location = Location(
        entity_type="farmer",
        entity_id="F001",
        latitude=13.3409,
        longitude=74.7421,
        address="Udupi",
    )

    service.save_location(location)

    loaded = service.get_location("farmer", "F001")

    assert loaded is not None
    assert loaded.entity_type == "farmer"
    assert loaded.entity_id == "F001"
    assert loaded.latitude == 13.3409
    assert loaded.longitude == 74.7421
    assert loaded.address == "Udupi"


def test_save_and_get_buyer_location(tmp_path: Path):
    service = create_service(tmp_path)

    location = Location(
        entity_type="buyer",
        entity_id="B001",
        latitude=12.9141,
        longitude=74.8560,
        address="Mangaluru",
    )

    service.save_location(location)

    loaded = service.get_location("buyer", "B001")

    assert loaded is not None
    assert loaded.entity_type == "buyer"
    assert loaded.entity_id == "B001"
    assert loaded.latitude == 12.9141
    assert loaded.longitude == 74.8560


def test_location_persists_across_service_reload(tmp_path: Path):
    db = Database(str(tmp_path / "location_test.db"))

    first_service = LocationService(db)

    location = Location(
        entity_type="farmer",
        entity_id="F002",
        latitude=13.0,
        longitude=74.8,
        address="Kundapura",
    )

    first_service.save_location(location)

    second_service = LocationService(db)

    loaded = second_service.get_location(
        "farmer",
        "F002",
    )

    assert loaded is not None
    assert loaded.latitude == 13.0
    assert loaded.longitude == 74.8
    assert loaded.address == "Kundapura"


def test_location_update_replaces_existing_coordinates(tmp_path: Path):
    service = create_service(tmp_path)

    original = Location(
        entity_type="farmer",
        entity_id="F003",
        latitude=13.0,
        longitude=74.0,
        address="Old Address",
    )

    updated = Location(
        entity_type="farmer",
        entity_id="F003",
        latitude=13.5,
        longitude=74.5,
        address="New Address",
    )

    service.save_location(original)
    service.save_location(updated)

    loaded = service.get_location("farmer", "F003")

    assert loaded is not None
    assert loaded.latitude == 13.5
    assert loaded.longitude == 74.5
    assert loaded.address == "New Address"


def test_invalid_latitude_is_rejected(tmp_path: Path):
    service = create_service(tmp_path)

    location = Location(
        entity_type="farmer",
        entity_id="F004",
        latitude=91.0,
        longitude=74.0,
    )

    with pytest.raises(ValueError, match="Latitude"):
        service.save_location(location)


def test_invalid_longitude_is_rejected(tmp_path: Path):
    service = create_service(tmp_path)

    location = Location(
        entity_type="farmer",
        entity_id="F005",
        latitude=13.0,
        longitude=181.0,
    )

    with pytest.raises(ValueError, match="Longitude"):
        service.save_location(location)


def test_invalid_entity_type_is_rejected(tmp_path: Path):
    service = create_service(tmp_path)

    location = Location(
        entity_type="unknown",
        entity_id="X001",
        latitude=13.0,
        longitude=74.0,
    )

    with pytest.raises(ValueError, match="Invalid entity type"):
        service.save_location(location)


def test_empty_entity_id_is_rejected(tmp_path: Path):
    service = create_service(tmp_path)

    location = Location(
        entity_type="farmer",
        entity_id="",
        latitude=13.0,
        longitude=74.0,
    )

    with pytest.raises(ValueError, match="Entity ID"):
        service.save_location(location)


def test_distance_calculation(tmp_path: Path):
    service = create_service(tmp_path)

    origin = Location(
        entity_type="farmer",
        entity_id="F006",
        latitude=13.3409,
        longitude=74.7421,
    )

    destination = Location(
        entity_type="buyer",
        entity_id="B006",
        latitude=12.9141,
        longitude=74.8560,
    )

    distance = service.calculate_distance(
        origin,
        destination,
    )

    assert distance > 0
    assert distance < 100


def test_distance_between_persisted_entities(tmp_path: Path):
    service = create_service(tmp_path)

    service.save_location(
        Location(
            entity_type="farmer",
            entity_id="F007",
            latitude=13.3409,
            longitude=74.7421,
        )
    )

    service.save_location(
        Location(
            entity_type="buyer",
            entity_id="B007",
            latitude=12.9141,
            longitude=74.8560,
        )
    )

    distance = service.calculate_distance_between_entities(
        "farmer",
        "F007",
        "buyer",
        "B007",
    )

    assert distance > 0
    assert distance < 100


def test_missing_origin_location_is_rejected(tmp_path: Path):
    service = create_service(tmp_path)

    service.save_location(
        Location(
            entity_type="buyer",
            entity_id="B008",
            latitude=13.0,
            longitude=74.0,
        )
    )

    with pytest.raises(KeyError, match="Location not found"):
        service.calculate_distance_between_entities(
            "farmer",
            "F008",
            "buyer",
            "B008",
        )


def test_missing_destination_location_is_rejected(tmp_path: Path):
    service = create_service(tmp_path)

    service.save_location(
        Location(
            entity_type="farmer",
            entity_id="F009",
            latitude=13.0,
            longitude=74.0,
        )
    )

    with pytest.raises(KeyError, match="Location not found"):
        service.calculate_distance_between_entities(
            "farmer",
            "F009",
            "buyer",
            "B009",
        )


def test_travel_time_estimation(tmp_path: Path):
    service = create_service(tmp_path)

    travel_time = service.estimate_travel_time(
        70.0,
        "mini_truck",
    )

    assert travel_time == pytest.approx(2.0)


def test_transport_cost_estimation(tmp_path: Path):
    service = create_service(tmp_path)

    cost = service.estimate_transport_cost(
        10.0,
        "mini_truck",
    )

    assert cost == pytest.approx(280.0)


def test_unknown_vehicle_is_rejected(tmp_path: Path):
    service = create_service(tmp_path)

    with pytest.raises(ValueError, match="Unknown vehicle type"):
        service.estimate_travel_time(
            10.0,
            "unknown_vehicle",
        )


def test_negative_distance_is_rejected(tmp_path: Path):
    service = create_service(tmp_path)

    with pytest.raises(ValueError, match="Distance cannot be negative"):
        service.estimate_transport_cost(
            -1.0,
            "mini_truck",
        )


def test_route_estimate_contains_logistics_information(tmp_path: Path):
    service = create_service(tmp_path)

    service.save_location(
        Location(
            entity_type="farmer",
            entity_id="F010",
            latitude=13.3409,
            longitude=74.7421,
            address="Udupi",
        )
    )

    service.save_location(
        Location(
            entity_type="buyer",
            entity_id="B010",
            latitude=12.9141,
            longitude=74.8560,
            address="Mangaluru",
        )
    )

    route = service.estimate_route(
        "farmer",
        "F010",
        "buyer",
        "B010",
        "mini_truck",
    )

    assert route.origin_entity_type == "farmer"
    assert route.origin_entity_id == "F010"
    assert route.destination_entity_type == "buyer"
    assert route.destination_entity_id == "B010"
    assert route.distance_km > 0
    assert route.estimated_travel_time_hours > 0
    assert route.estimated_transport_cost > 0
    assert route.vehicle_type == "mini_truck"


def test_route_estimate_supports_different_vehicle_types(tmp_path: Path):
    service = create_service(tmp_path)

    service.save_location(
        Location(
            entity_type="farmer",
            entity_id="F011",
            latitude=13.3409,
            longitude=74.7421,
        )
    )

    service.save_location(
        Location(
            entity_type="buyer",
            entity_id="B011",
            latitude=12.9141,
            longitude=74.8560,
        )
    )

    mini_truck_route = service.estimate_route(
        "farmer",
        "F011",
        "buyer",
        "B011",
        "mini_truck",
    )

    truck_route = service.estimate_route(
        "farmer",
        "F011",
        "buyer",
        "B011",
        "truck",
    )

    assert truck_route.vehicle_type == "truck"
    assert mini_truck_route.distance_km == pytest.approx(
        truck_route.distance_km
    )
    assert truck_route.estimated_transport_cost > (
        mini_truck_route.estimated_transport_cost
    )


def test_location_to_dict(tmp_path: Path):
    service = create_service(tmp_path)

    location = Location(
        entity_type="farmer",
        entity_id="F012",
        latitude=13.0,
        longitude=74.0,
        address="Udupi",
    )

    result = service.to_dict(location)

    assert result["entity_type"] == "farmer"
    assert result["entity_id"] == "F012"
    assert result["latitude"] == 13.0
    assert result["longitude"] == 74.0
    assert result["address"] == "Udupi"