from typing import Any, Dict, Optional

from shared.schemas.schemas import Supply, Demand

from Mugil.Verification_Robustness.supply_verification import verify_supply
from Mugil.Verification_Robustness.demand_verification import verify_demand
from Mugil.Verification_Robustness.constraint_verification import (
    verify_constraints,
)


def verify_recovery(
    replacement_supply: Supply,
    demand: Demand,
    failed_supply: Optional[Supply] = None,
) -> Dict[str, Any]:
    """
    Independently verify a replacement supply after a supply failure.

    This function does not choose the replacement.
    It verifies whether the replacement selected by the rescue/
    replanning system is actually safe to accept.

    Recovery passes only when:
        1. Replacement supply is valid.
        2. Demand is valid.
        3. Replacement satisfies all constraints.
        4. Replacement is not the failed supplier.

    Returns a structured recovery decision suitable for the
    dashboard and decision timeline.
    """

    errors = []
    warnings = []

    # ---------------------------------------------------------
    # Basic input validation
    # ---------------------------------------------------------

    if not isinstance(replacement_supply, Supply):
        return {
            "recovered": False,
            "decision": "RECOVERY_REJECTED",
            "replacement_supply_id": None,
            "failed_supply_id": getattr(failed_supply, "id", None),
            "errors": ["Replacement supply must be a Supply object."],
            "warnings": [],
            "verification": {},
        }

    if not isinstance(demand, Demand):
        return {
            "recovered": False,
            "decision": "RECOVERY_REJECTED",
            "replacement_supply_id": replacement_supply.id,
            "failed_supply_id": getattr(failed_supply, "id", None),
            "errors": ["Demand must be a Demand object."],
            "warnings": [],
            "verification": {},
        }

    # ---------------------------------------------------------
    # Prevent accidental reuse of failed supply
    # ---------------------------------------------------------

    failed_supply_id = getattr(failed_supply, "id", None)

    if (
        failed_supply_id is not None
        and replacement_supply.id == failed_supply_id
    ):
        errors.append(
            "Replacement supply cannot be the same supply that failed."
        )

    # ---------------------------------------------------------
    # Independently verify replacement supply
    # ---------------------------------------------------------

    supply_result = verify_supply(replacement_supply)

    # ---------------------------------------------------------
    # Independently verify demand
    # ---------------------------------------------------------

    demand_result = verify_demand(demand)

    # ---------------------------------------------------------
    # Verify replacement against demand
    # ---------------------------------------------------------

    if supply_result["verified"] and demand_result["verified"]:
        constraint_result = verify_constraints(
            replacement_supply,
            demand,
        )
    else:
        constraint_result = {
            "verified": False,
            "checks": {},
            "errors": [
                "Recovery constraint verification skipped because "
                "replacement supply or demand validation failed."
            ],
            "warnings": [],
            "details": {},
        }

    # ---------------------------------------------------------
    # Collect results
    # ---------------------------------------------------------

    errors.extend(supply_result["errors"])
    errors.extend(demand_result["errors"])
    errors.extend(constraint_result["errors"])

    warnings.extend(supply_result["warnings"])
    warnings.extend(demand_result["warnings"])
    warnings.extend(constraint_result["warnings"])

    # ---------------------------------------------------------
    # Final recovery decision
    # ---------------------------------------------------------

    recovered = (
        not errors
        and supply_result["verified"]
        and demand_result["verified"]
        and constraint_result["verified"]
    )

    if recovered:
        decision = "RECOVERY_VERIFIED"
        summary = (
            "Replacement supply passed independent verification "
            "and can safely replace the failed supply."
        )
    else:
        decision = "RECOVERY_REJECTED"
        summary = (
            "Replacement supply failed recovery verification "
            "and must not replace the failed supply."
        )

    # ---------------------------------------------------------
    # Recovery decision trace
    # ---------------------------------------------------------

    decision_trace = [
        {
            "stage": "replacement_supply_verification",
            "passed": supply_result["verified"],
        },
        {
            "stage": "demand_verification",
            "passed": demand_result["verified"],
        },
        {
            "stage": "replacement_constraint_verification",
            "passed": constraint_result["verified"],
        },
        {
            "stage": "recovery_decision",
            "passed": recovered,
        },
    ]

    return {
        "recovered": recovered,
        "decision": decision,
        "summary": summary,
        "replacement_supply_id": replacement_supply.id,
        "failed_supply_id": failed_supply_id,
        "demand_id": demand.id,
        "errors": errors,
        "warnings": warnings,
        "verification": {
            "replacement_supply": supply_result,
            "demand": demand_result,
            "constraints": constraint_result,
        },
        "decision_trace": decision_trace,
    }
