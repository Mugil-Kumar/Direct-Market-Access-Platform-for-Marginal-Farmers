from datetime import datetime
from math import isfinite
from typing import Any, Dict

from shared.schemas.schemas import Demand


def _parse_datetime(value: str) -> datetime:
    """Parse an ISO-8601 datetime string."""
    normalized = value.strip()

    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"

    return datetime.fromisoformat(normalized)


def verify_demand(demand: Demand) -> Dict[str, Any]:
    """
    Independently verify whether a Demand record is valid
    and safe to send to the matching pipeline.
    """

    errors = []
    warnings = []

    checks = {
        "identity": False,
        "quantity": False,
        "destination": False,
        "deadline": False,
        "price": False,
        "quality": False,
        "status": False,
    }

    # ---------------------------------------------------------
    # Object validation
    # ---------------------------------------------------------

    if not isinstance(demand, Demand):
        return {
            "verified": False,
            "demand_id": None,
            "checks": checks,
            "errors": ["Input must be a Demand object."],
            "warnings": [],
        }

    # ---------------------------------------------------------
    # Identity validation
    # ---------------------------------------------------------

    if demand.id and demand.buyer_id and demand.crop:
        checks["identity"] = True
    else:
        errors.append(
            "Demand ID, buyer ID, and crop are required."
        )

    # ---------------------------------------------------------
    # Quantity validation
    # ---------------------------------------------------------

    if isinstance(demand.quantity_kg, (int, float)):
        if isfinite(demand.quantity_kg) and demand.quantity_kg > 0:
            checks["quantity"] = True
        else:
            errors.append(
                "Demand quantity must be a finite value greater than 0 kg."
            )
    else:
        errors.append("Demand quantity must be numeric.")

    # ---------------------------------------------------------
    # Destination validation
    # ---------------------------------------------------------

    if (
        isinstance(demand.destination, str)
        and demand.destination.strip()
    ):
        checks["destination"] = True
    else:
        errors.append("Demand destination is required.")

    # ---------------------------------------------------------
    # Quality validation
    # ---------------------------------------------------------

    if (
        isinstance(demand.quality_required, str)
        and demand.quality_required.strip()
    ):
        checks["quality"] = True
    else:
        errors.append("Required quality information is missing.")

    # ---------------------------------------------------------
    # Maximum price validation
    # ---------------------------------------------------------

    if isinstance(demand.max_price_per_kg, (int, float)):
        if (
            isfinite(demand.max_price_per_kg)
            and demand.max_price_per_kg > 0
        ):
            checks["price"] = True
        else:
            errors.append(
                "Maximum price must be a finite value greater than 0."
            )
    else:
        errors.append("Maximum price must be numeric.")

    # ---------------------------------------------------------
    # Status validation
    # ---------------------------------------------------------

    valid_statuses = {
        "open",
        "matched",
        "fulfilled",
        "expired",
        "cancelled",
    }

    if demand.status in valid_statuses:
        if demand.status == "open":
            checks["status"] = True
        else:
            errors.append(
                f"Demand is not open for a new match because its status is '{demand.status}'."
            )
    else:
        errors.append(
            f"Invalid demand status: '{demand.status}'."
        )

    # ---------------------------------------------------------
    # Deadline validation
    # ---------------------------------------------------------

    try:
        deadline = _parse_datetime(demand.deadline)

        checks["deadline"] = True

        # A timezone-naive datetime is accepted because our
        # current shared schema stores deadlines as strings.
        # Future integration can enforce timezone-aware values.
        if deadline.year < 2000:
            warnings.append(
                "Demand deadline appears unusually old."
            )

    except (TypeError, ValueError):
        errors.append(
            "Demand deadline must be a valid ISO-8601 datetime value."
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
        "demand_id": demand.id,
        "checks": checks,
        "errors": errors,
        "warnings": warnings,
    }
