from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Farmer:
    id: str
    name: str
    location: str
    phone: Optional[str] = None
    reliability_score: float = 0.0


@dataclass
class Buyer:
    id: str
    name: str
    location: str
    phone: Optional[str] = None
    reliability_score: float = 0.0


@dataclass
class Supply:
    id: str
    farmer_id: str
    crop: str
    quantity_kg: float
    location: str
    available_from: str
    available_until: str
    quality: str
    expected_price_per_kg: float
    status: str = "available"


@dataclass
class Demand:
    id: str
    buyer_id: str
    crop: str
    quantity_kg: float
    destination: str
    deadline: str
    max_price_per_kg: float
    quality_required: str
    status: str = "open"


@dataclass
class Match:
    demand_id: str
    supply_ids: List[str] = field(default_factory=list)
    total_quantity_kg: float = 0.0
    estimated_price_per_kg: float = 0.0
    estimated_distance_km: float = 0.0
    score: float = 0.0
    explanation: str = ""


@dataclass
class Order:
    id: str
    demand_id: str
    supply_ids: List[str] = field(default_factory=list)
    quantity_kg: float = 0.0
    selling_price_per_kg: float = 0.0
    transport_cost: float = 0.0
    collection_cost: float = 0.0
    packaging_cost: float = 0.0
    spoilage_cost: float = 0.0
    platform_fee: float = 0.0
    status: str = "pending"


@dataclass
class RescueResult:
    order_id: str
    original_quantity_kg: float
    shortfall_kg: float
    replacement_supply_ids: List[str] = field(default_factory=list)
    recovered_quantity_kg: float = 0.0
    recovered: bool = False
    explanation: str = ""


@dataclass
class Location:
    """
    Geographic information associated with a marketplace entity.
    """

    entity_type: str
    entity_id: str
    latitude: float
    longitude: float
    address: Optional[str] = None


@dataclass
class RouteEstimate:
    """
    Estimated movement between a supply origin and buyer destination.
    """

    origin_entity_type: str
    origin_entity_id: str
    destination_entity_type: str
    destination_entity_id: str
    distance_km: float
    estimated_travel_time_hours: float
    estimated_transport_cost: float
    vehicle_type: str
