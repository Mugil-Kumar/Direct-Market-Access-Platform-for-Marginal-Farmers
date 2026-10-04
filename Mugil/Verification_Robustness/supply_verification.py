from datetime import datetime
from math import isfinite
from typing import Any, Dict

from shared.schemas.schemas import Supply


def _parse_datetime(value: str) -> datetime:
    """Parse an ISO-8601 datetime string."""
    normalized = value.strip()

    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"

    return datetime.fromisoformat(normalized)


def verify_supply(supply: Supply) -> Dict[str, Any]:
    """
    Independently verify whether a Supply record is valid and usable.

    Returns a structured verification result containing:
    - verified: overall verification status
    - supply_id: verified supply identifier
    - checks: individual validation results
    - errors: blocking problems
    - warnings: non-blocking concerns
    """

    errors = []
    warnings = []

    checks = {
        "identity": False,
        "quantity": False,
        "location": False,
        "availability": False,
        "quality": False,
        "price": False,
        "status": False,
    }

    # ---------------------------------------------------------
    # Basic object validation
    # ---------------------------------------------------------

    if not isinstance(supply, Supply):
        return {
            "verified": False,
            "supply_id": None,
            "checks": checks,
            "errors": ["Input must be a Supply object."],
            "warnings": [],
        }

    # ---------------------------------------------------------
    # Identity validation
    # ---------------------------------------------------------

    if supply.id and supply.farmer_id and supply.crop:
        checks["identity"] = True
    else:
        errors.append(
            "Supply ID, farmer ID, and crop are required."
        )

    # ---------------------------------------------------------
    # Quantity validation
    # ---------------------------------------------------------

    if isinstance(supply.quantity_kg, (int, float)):
        if isfinite(supply.quantity_kg) and supply.quantity_kg > 0:
            checks["quantity"] = True
        else:
            errors.append(
                "Supply quantity must be a finite value greater than 0 kg."
            )
    else:
        errors.append("Supply quantity must be numeric.")

    # ---------------------------------------------------------
    # Location validation
    # ---------------------------------------------------------

    if isinstance(supply.location, str) and supply.location.strip():
        checks["location"] = True
    else:
        errors.append("Supply location is required.")

    # ---------------------------------------------------------
    # Quality validation
    # ---------------------------------------------------------

    if isinstance(supply.quality, str) and supply.quality.strip():
        checks["quality"] = True
    else:
        errors.append("Supply quality information is required.")

    # ---------------------------------------------------------
    # Price validation
    # ---------------------------------------------------------

    if isinstance(supply.expected_price_per_kg, (int, float)):
        if (
            isfinite(supply.expected_price_per_kg)
            and supply.expected_price_per_kg >= 0
        ):
            checks["price"] = True
        else:
            errors.append(
                "Expected price must be a finite value greater than or equal to 0."
            )
    else:
        errors.append("Expected price must be numeric.")

    # ---------------------------------------------------------
    # Status validation
    # ---------------------------------------------------------

    valid_statuses = {
        "available",
        "reserved",
        "sold",
        "expired",
        "cancelled",
    }

    if supply.status in valid_statuses:
        if supply.status == "available":
            checks["status"] = True
        else:
            errors.append(
                f"Supply is not available for a new match because its status is '{supply.status}'."
            )
    else:
        errors.append(
            f"Invalid supply status: '{supply.status}'."
        )

    # ---------------------------------------------------------
    # Availability window validation
    # ---------------------------------------------------------

    try:
        available_from = _parse_datetime(supply.available_from)
        available_until = _parse_datetime(supply.available_until)

        if available_until < available_from:
            errors.append(
                "Availability end time cannot be earlier than start time."
            )
        else:
            checks["availability"] = True

    except (TypeError, ValueError):
        errors.append(
            "Availability dates must be valid ISO-8601 datetime values."
        )

    # ---------------------------------------------------------
    # Final decision
    # ---------------------------------------------------------

    verified = (
        not errors
        and all(checks.values())
    )

    return {
        "verified": verified,
        "supply_id": supply.id,
        "checks": checks,
        "errors": errors,
        "warnings": warnings,
    }

