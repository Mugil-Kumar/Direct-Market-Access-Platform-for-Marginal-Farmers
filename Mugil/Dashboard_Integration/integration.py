from typing import Any, Dict

from shared.schemas.schemas import Supply, Demand

from Mugil.Verification_Robustness.verifier import verify_match


def run_match_verification(
    supply: Supply,
    demand: Demand,
) -> Dict[str, Any]:
    """
    Execute independent verification for a proposed
    supply-demand match and return a dashboard-ready result.

    This integration layer does not make matching decisions.
    It delegates validation to the independent verifier.
    """

    result = verify_match(
        supply=supply,
        demand=demand,
    )

    return {
        "verified": result["verified"],
        "decision": result["decision"],
        "summary": result["summary"],
        "supply_id": result["supply_id"],
        "demand_id": result["demand_id"],
        "errors": list(result["errors"]),
        "warnings": list(result["warnings"]),
        "decision_trace": list(result["decision_trace"]),
        "supply_verification": result["supply_verification"],
        "demand_verification": result["demand_verification"],
        "constraint_verification": result["constraint_verification"],
    }


def build_verification_view(
    result: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Convert a verification result into a compact structure
    suitable for dashboard rendering.

    No verification decision is changed here.
    """

    trace = result.get("decision_trace", [])

    stages = []

    for item in trace:
        stages.append(
            {
                "stage": item.get("stage", "unknown"),
                "passed": bool(item.get("passed", False)),
            }
        )

    return {
        "status": (
            "VERIFIED"
            if result.get("verified", False)
            else "REJECTED"
        ),
        "decision": result.get(
            "decision",
            "UNKNOWN",
        ),
        "summary": result.get(
            "summary",
            "No verification summary available.",
        ),
        "supply_id": result.get("supply_id"),
        "demand_id": result.get("demand_id"),
        "errors": list(result.get("errors", [])),
        "warnings": list(result.get("warnings", [])),
        "stages": stages,
    }


def create_demo_supply() -> Supply:
    """
    Create a deterministic demonstration supply.

    This is intentionally kept separate from production
    marketplace data so the judge demo is repeatable.
    """

    return Supply(
        id="SUP-DEMO-001",
        farmer_id="FARM-DEMO-001",
        crop="Tomato",
        quantity_kg=500.0,
        location="Udupi",
        available_from="2026-11-12T06:00:00",
        available_until="2026-11-13T18:00:00",
        quality="A",
        expected_price_per_kg=28.0,
        status="available",
    )


def create_demo_demand() -> Demand:
    """
    Create a deterministic demonstration demand.
    """

    return Demand(
        id="DEM-DEMO-001",
        buyer_id="BUYER-DEMO-001",
        crop="Tomato",
        quantity_kg=500.0,
        destination="Mangaluru",
        deadline="2026-11-13T18:00:00",
        max_price_per_kg=32.0,
        quality_required="A",
        status="open",
    )


def run_demo_verification() -> Dict[str, Any]:
    """
    Execute one deterministic end-to-end verification
    scenario for the command dashboard.
    """

    supply = create_demo_supply()
    demand = create_demo_demand()

    result = run_match_verification(
        supply=supply,
        demand=demand,
    )

    return build_verification_view(result)
