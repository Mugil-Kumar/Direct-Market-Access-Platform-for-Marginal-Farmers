from dataclasses import asdict
from typing import Dict, Optional

from shared.schemas.schemas import Location, RouteEstimate
from shared.utilities.helpers import calculate_distance_km

from .database import Database


class LocationService:
    """
    Persistent location and logistics service for AGRIWEAVE.

    Responsibilities:
    - Store farmer/buyer coordinates.
    - Validate geographic coordinates.
    - Retrieve persisted locations.
    - Calculate straight-line distance.
    - Estimate travel time.
    - Estimate transport cost.
    - Produce a structured RouteEstimate for downstream modules.
    """

    DEFAULT_VEHICLE_TYPE = "mini_truck"
    DEFAULT_AVERAGE_SPEED_KMPH = 35.0
    DEFAULT_COST_PER_KM = 18.0
    DEFAULT_LOADING_COST = 100.0

    VALID_ENTITY_TYPES = {
        "farmer",
        "buyer",
        "collection_center",
        "market",
    }

    VEHICLE_PROFILES = {
        "mini_truck": {
            "average_speed_kmph": 35.0,
            "cost_per_km": 18.0,
            "loading_cost": 100.0,
        },
        "truck": {
            "average_speed_kmph": 40.0,
            "cost_per_km": 28.0,
            "loading_cost": 200.0,
        },
        "tempo": {
            "average_speed_kmph": 30.0,
            "cost_per_km": 14.0,
            "loading_cost": 75.0,
        },
    }

    def __init__(self, database: Optional[Database] = None) -> None:
        self.database = database or Database()

    @staticmethod
    def _validate_coordinates(latitude: float, longitude: float) -> None:
        if not -90.0 <= latitude <= 90.0:
            raise ValueError("Latitude must be between -90 and 90.")

        if not -180.0 <= longitude <= 180.0:
            raise ValueError("Longitude must be between -180 and 180.")

    @classmethod
    def _validate_entity(
        cls,
        entity_type: str,
        entity_id: str,
    ) -> None:
        if entity_type not in cls.VALID_ENTITY_TYPES:
            raise ValueError(
                f"Invalid entity type: {entity_type}. "
                f"Expected one of {sorted(cls.VALID_ENTITY_TYPES)}."
            )

        if not entity_id or not entity_id.strip():
            raise ValueError("Entity ID cannot be empty.")

    def save_location(self, location: Location) -> Location:
        """
        Create or update a persistent location.
        """

        self._validate_entity(
            location.entity_type,
            location.entity_id,
        )

        self._validate_coordinates(
            location.latitude,
            location.longitude,
        )

        self.database.execute(
            """
            INSERT INTO locations (
                entity_type,
                entity_id,
                latitude,
                longitude,
                address
            )
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(entity_type, entity_id)
            DO UPDATE SET
                latitude = excluded.latitude,
                longitude = excluded.longitude,
                address = excluded.address
            """,
            (
                location.entity_type,
                location.entity_id,
                location.latitude,
                location.longitude,
                location.address,
            ),
        )

        return location

    def get_location(
        self,
        entity_type: str,
        entity_id: str,
    ) -> Optional[Location]:
        """
        Retrieve a persisted location.
        """

        self._validate_entity(entity_type, entity_id)

        row = self.database.fetch_one(
            """
            SELECT
                entity_type,
                entity_id,
                latitude,
                longitude,
                address
            FROM locations
            WHERE entity_type = ?
            AND entity_id = ?
            """,
            (entity_type, entity_id),
        )

        if row is None:
            return None

        if row["latitude"] is None or row["longitude"] is None:
            return None

        return Location(
            entity_type=row["entity_type"],
            entity_id=row["entity_id"],
            latitude=float(row["latitude"]),
            longitude=float(row["longitude"]),
            address=row["address"],
        )

    def calculate_distance(
        self,
        origin: Location,
        destination: Location,
    ) -> float:
        """
        Calculate straight-line geographic distance in kilometres.
        """

        self._validate_coordinates(
            origin.latitude,
            origin.longitude,
        )

        self._validate_coordinates(
            destination.latitude,
            destination.longitude,
        )

        return calculate_distance_km(
            origin.latitude,
            origin.longitude,
            destination.latitude,
            destination.longitude,
        )

    def calculate_distance_between_entities(
        self,
        origin_entity_type: str,
        origin_entity_id: str,
        destination_entity_type: str,
        destination_entity_id: str,
    ) -> float:
        """
        Calculate distance between two persisted entities.
        """

        origin = self.get_location(
            origin_entity_type,
            origin_entity_id,
        )

        if origin is None:
            raise KeyError(
                f"Location not found for "
                f"{origin_entity_type}:{origin_entity_id}."
            )

        destination = self.get_location(
            destination_entity_type,
            destination_entity_id,
        )

        if destination is None:
            raise KeyError(
                f"Location not found for "
                f"{destination_entity_type}:{destination_entity_id}."
            )

        return self.calculate_distance(origin, destination)

    def estimate_travel_time(
        self,
        distance_km: float,
        vehicle_type: str = DEFAULT_VEHICLE_TYPE,
    ) -> float:
        """
        Estimate travel time in hours.

        This is an MVP operational estimate rather than a live traffic
        navigation result.
        """

        if distance_km < 0:
            raise ValueError("Distance cannot be negative.")

        profile = self.VEHICLE_PROFILES.get(vehicle_type)

        if profile is None:
            raise ValueError(
                f"Unknown vehicle type: {vehicle_type}. "
                f"Available vehicles: {sorted(self.VEHICLE_PROFILES)}."
            )

        speed = profile["average_speed_kmph"]

        if speed <= 0:
            raise ValueError("Vehicle average speed must be positive.")

        return distance_km / speed

    def estimate_transport_cost(
        self,
        distance_km: float,
        vehicle_type: str = DEFAULT_VEHICLE_TYPE,
    ) -> float:
        """
        Estimate one-way transport cost.
        """

        if distance_km < 0:
            raise ValueError("Distance cannot be negative.")

        profile = self.VEHICLE_PROFILES.get(vehicle_type)

        if profile is None:
            raise ValueError(
                f"Unknown vehicle type: {vehicle_type}. "
                f"Available vehicles: {sorted(self.VEHICLE_PROFILES)}."
            )

        return (
            distance_km * profile["cost_per_km"]
            + profile["loading_cost"]
        )

    def estimate_route(
        self,
        origin_entity_type: str,
        origin_entity_id: str,
        destination_entity_type: str,
        destination_entity_id: str,
        vehicle_type: str = DEFAULT_VEHICLE_TYPE,
    ) -> RouteEstimate:
        """
        Generate a structured route estimate for downstream modules.
        """

        distance_km = self.calculate_distance_between_entities(
            origin_entity_type,
            origin_entity_id,
            destination_entity_type,
            destination_entity_id,
        )

        travel_time_hours = self.estimate_travel_time(
            distance_km,
            vehicle_type,
        )

        transport_cost = self.estimate_transport_cost(
            distance_km,
            vehicle_type,
        )

        return RouteEstimate(
            origin_entity_type=origin_entity_type,
            origin_entity_id=origin_entity_id,
            destination_entity_type=destination_entity_type,
            destination_entity_id=destination_entity_id,
            distance_km=distance_km,
            estimated_travel_time_hours=travel_time_hours,
            estimated_transport_cost=transport_cost,
            vehicle_type=vehicle_type,
        )

    def to_dict(self, location: Location) -> Dict:
        """
        Convert a Location dataclass to a dictionary.
        """

        return asdict(location)