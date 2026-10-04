from datetime import datetime
from math import isfinite
from typing import Any, Dict

from shared.schemas.schemas import Supply, Demand


def _parse_datetime(value: str) -> datetime:
    """Parse an ISO-8601 datetime string."""
    normalized = value.strip()

    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"

    return datetime.fromisoformat(normalized)


def _normalize_quality(value: str) -> str:
    """Normalize quality labels for comparison."""
    return " ".join(value.strip().lower().split())


def verify_constraints(
    supply: Supply,
    demand: Demand,
) -> Dict[str, Any]:
    """
    Verify whether a specific supply can satisfy a specific demand.

    This does not decide which farmer is the best.
    It only performs an independent feasibility check.

    Returns:
        verified:
            True only when all blocking constraints pass.

        checks:
            Individual constraint results.

        errors:
            Blocking constraint violations.

        warnings:
            Non-blocking observations.

        details:
            Useful values for dashboards and later decision tracing.
    """

    errors = []
    warnings = []

    checks = {
        "crop_match": False,
        "quantity_constraint": False,
        "price_constraint": False,
        "quality_constraint": False,
        "deadline_constraint": False,
        "supply_status": False,
        "demand_status": False,
    }

    details = {
        "supply_id": None,
        "demand_id": None,
        "available_quantity_kg": None,
        "requested_quantity_kg": None,
        "shortfall_kg": 0.0,
        "supply_price_per_kg": None,
        "buyer_max_price_per_kg": None,
    }

    # ---------------------------------------------------------
    # Input validation
    # ---------------------------------------------------------

    if not isinstance(supply, Supply):
        errors.append("Supply input must be a Supply object.")

    if not isinstance(demand, Demand):
        errors.append("Demand input must be a Demand object.")

    if errors:
        return {
            "verified": False,
            "checks": checks,
            "errors": errors,
            "warnings": warnings,
            "details": details,
        }

    details["supply_id"] = supply.id
    details["demand_id"] = demand.id
    details["available_quantity_kg"] = supply.quantity_kg
    details["requested_quantity_kg"] = demand.quantity_kg
    details["supply_price_per_kg"] = supply.expected_price_per_kg
    details["buyer_max_price_per_kg"] = demand.max_price_per_kg

    # ---------------------------------------------------------
    # Crop compatibility
    # ---------------------------------------------------------

    supply_crop = supply.crop.strip().lower()
    demand_crop = demand.crop.strip().lower()

    if supply_crop and demand_crop and supply_crop == demand_crop:
        checks["crop_match"] = True
    else:
        errors.append(
            f"Crop mismatch: supply is '{supply.crop}' "
            f"but demand requires '{demand.crop}'."
        )

    # ---------------------------------------------------------
    # Quantity constraint
    # ---------------------------------------------------------

    if (
        isinstance(supply.quantity_kg, (int, float))
        and isinstance(demand.quantity_kg, (int, float))
        and isfinite(supply.quantity_kg)
        and isfinite(demand.quantity_kg)
        and supply.quantity_kg > 0
        and demand.quantity_kg > 0
    ):
        if supply.quantity_kg >= demand.quantity_kg:
            checks["quantity_constraint"] = True
        else:
            shortfall = demand.quantity_kg - supply.quantity_kg
            details["shortfall_kg"] = shortfall

            errors.append(
                f"Insufficient quantity: supply has "
                f"{supply.quantity_kg} kg but demand requires "
                f"{demand.quantity_kg} kg."
            )
    else:
        errors.append(
            "Supply and demand quantities must be finite values greater than 0."
        )

    # ---------------------------------------------------------
    # Price constraint
    # ---------------------------------------------------------

    if (
        isinstance(supply.expected_price_per_kg, (int, float))
        and isinstance(demand.max_price_per_kg, (int, float))
        and isfinite(supply.expected_price_per_kg)
        and isfinite(demand.max_price_per_kg)
        and supply.expected_price_per_kg >= 0
        and demand.max_price_per_kg > 0
    ):
        if supply.expected_price_per_kg <= demand.max_price_per_kg:
            checks["price_constraint"] = True
        else:
            errors.append(
                f"Price constraint failed: supply asks "
                f"{supply.expected_price_per_kg:.2f}/kg but buyer maximum is "
                f"{demand.max_price_per_kg:.2f}/kg."
            )
    else:
        errors.append("Supply and demand price values are invalid.")

    # ---------------------------------------------------------
    # Quality constraint
    # ---------------------------------------------------------

    supply_quality = _normalize_quality(supply.quality)
    demand_quality = _normalize_quality(demand.quality_required)

    if supply_quality and demand_quality:
        if supply_quality == demand_quality:
            checks["quality_constraint"] = True
        else:
            errors.append(
                f"Quality mismatch: supply is '{supply.quality}' "
                f"but demand requires '{demand.quality_required}'."
            )
    else:
        errors.append("Supply quality and required demand quality are required.")

    # ---------------------------------------------------------
    # Supply status
    # ---------------------------------------------------------

    if supply.status == "available":
        checks["supply_status"] = True
    else:
        errors.append(
            f"Supply cannot be used for a new match because its status is "
            f"'{supply.status}'."
        )

    # ---------------------------------------------------------
    # Demand status
    # ---------------------------------------------------------

    if demand.status == "open":
        checks["demand_status"] = True
    else:
        errors.append(
            f"Demand cannot accept a new match because its status is "
            f"'{demand.status}'."
        )

    # ---------------------------------------------------------
    # Deadline / availability constraint
    # ---------------------------------------------------------

    try:
        available_from = _parse_datetime(supply.available_from)
        available_until = _parse_datetime(supply.available_until)
        deadline = _parse_datetime(demand.deadline)

        if available_until < available_from:
            errors.append(
                "Supply availability window is invalid."
            )
        elif available_until >= deadline:
            checks["deadline_constraint"] = True
        else:
            errors.append(
                "Supply is not available until the buyer's required deadline."
            )

    except (TypeError, ValueError):
        errors.append(
            "Supply availability and demand deadline must use valid ISO-8601 dates."
        )

    # ---------------------------------------------------------
    # Non-blocking observations
    # ---------------------------------------------------------

    if (
        checks["quantity_constraint"]
        and supply.quantity_kg > demand.quantity_kg
    ):
        excess = supply.quantity_kg - demand.quantity_kg

        warnings.append(
            f"Supply exceeds this demand by {excess:.2f} kg."
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
        "checks": checks,
        "errors": errors,
        "warnings": warnings,
        "details": details,
    }
