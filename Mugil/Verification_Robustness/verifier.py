from typing import Any, Dict

from shared.schemas.schemas import Supply, Demand

from Mugil.Verification_Robustness.supply_verification import verify_supply
from Mugil.Verification_Robustness.demand_verification import verify_demand
from Mugil.Verification_Robustness.constraint_verification import (
    verify_constraints,
)


def verify_match(
    supply: Supply,
    demand: Demand,
) -> Dict[str, Any]:
    """
    Perform an independent end-to-end verification of a proposed
    supply-demand match.

    The verifier does not choose the best match.
    It checks whether the proposed match is actually valid.

    Returns a structured decision containing:
    - final verification status
    - supply verification
    - demand verification
    - constraint verification
    - combined errors and warnings
    - decision trace
    """

    supply_result = verify_supply(supply)
    demand_result = verify_demand(demand)

    # Constraint verification should only be treated as meaningful
    # when both records have passed their individual validation.
    if supply_result["verified"] and demand_result["verified"]:
        constraint_result = verify_constraints(supply, demand)
    else:
        constraint_result = {
            "verified": False,
            "checks": {},
            "errors": [
                "Constraint verification skipped because "
                "supply or demand validation failed."
            ],
            "warnings": [],
            "details": {},
        }

    errors = []
    warnings = []

    errors.extend(supply_result["errors"])
    errors.extend(demand_result["errors"])
    errors.extend(constraint_result["errors"])

    warnings.extend(supply_result["warnings"])
    warnings.extend(demand_result["warnings"])
    warnings.extend(constraint_result["warnings"])

    verified = (
        supply_result["verified"]
        and demand_result["verified"]
        and constraint_result["verified"]
        and not errors
    )

    if verified:
        decision = "VERIFIED"
        summary = (
            "Proposed supply-demand match passed independent "
            "supply, demand, and constraint verification."
        )
    else:
        decision = "REJECTED"
        summary = (
            "Proposed supply-demand match failed verification "
            "and must not be accepted as a valid match."
        )

    decision_trace = [
        {
            "stage": "supply_verification",
            "passed": supply_result["verified"],
        },
        {
            "stage": "demand_verification",
            "passed": demand_result["verified"],
        },
        {
            "stage": "constraint_verification",
            "passed": constraint_result["verified"],
        },
        {
            "stage": "final_decision",
            "passed": verified,
        },
    ]

    return {
        "verified": verified,
        "decision": decision,
        "summary": summary,
        "supply_id": getattr(supply, "id", None),
        "demand_id": getattr(demand, "id", None),
        "supply_verification": supply_result,
        "demand_verification": demand_result,
        "constraint_verification": constraint_result,
        "errors": errors,
        "warnings": warnings,
        "decision_trace": decision_trace,
    }
