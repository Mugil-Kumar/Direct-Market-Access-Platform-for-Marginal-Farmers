from math import radians, sin, cos, sqrt, atan2


def calculate_net_realization(
    selling_price: float,
    transport_cost: float = 0.0,
    collection_cost: float = 0.0,
    packaging_cost: float = 0.0,
    spoilage_cost: float = 0.0,
    platform_fee: float = 0.0,
) -> float:
    return (
        selling_price
        - transport_cost
        - collection_cost
        - packaging_cost
        - spoilage_cost
        - platform_fee
    )


def calculate_distance_km(
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float,
) -> float:
    earth_radius_km = 6371.0

    lat1_rad = radians(lat1)
    lat2_rad = radians(lat2)

    delta_lat = radians(lat2 - lat1)
    delta_lon = radians(lon2 - lon1)

    a = (
        sin(delta_lat / 2) ** 2
        + cos(lat1_rad)
        * cos(lat2_rad)
        * sin(delta_lon / 2) ** 2
    )

    c = 2 * atan2(sqrt(a), sqrt(1 - a))

    return earth_radius_km * c


def safe_float(value, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def safe_int(value, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default
