from typing import Any, Dict, Optional


def build_failure_response(
    error: Exception | str,
    *,
    stage: str,
    context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Build a safe, structured response when a verification stage fails.

    Security principle:
        Any unexpected verification failure is treated as REJECTED.
        The system must never fail open.
    """

    if isinstance(error, Exception):
        error_message = str(error) or error.__class__.__name__
        error_type = error.__class__.__name__
    else:
        error_message = str(error)
        error_type = "VerificationFailure"

    return {
        "valid": False,
        "verified": False,
        "decision": "REJECTED",
        "failure": True,
        "stage": stage,
        "error_type": error_type,
        "error": error_message,
        "summary": (
            f"Verification failed safely at stage '{stage}'. "
            "The proposed operation must not be accepted."
        ),
        "context": context or {},
    }


def validate_verification_result(
    result: Any,
    *,
    stage: str,
) -> Dict[str, Any]:
    """
    Validate the structure returned by a verification component.

    A malformed or incomplete result is rejected instead of being
    trusted by downstream components.
    """

    if not isinstance(result, dict):
        return build_failure_response(
            "Verification component returned a non-dictionary result.",
            stage=stage,
        )

    required_fields = {
        "verified",
        "errors",
    }

    missing_fields = [
        field
        for field in required_fields
        if field not in result
    ]

    if missing_fields:
        return build_failure_response(
            f"Verification result is missing required fields: "
            f"{', '.join(missing_fields)}.",
            stage=stage,
        )

    if not isinstance(result["verified"], bool):
        return build_failure_response(
            "Verification field 'verified' must be a boolean.",
            stage=stage,
        )

    if not isinstance(result["errors"], list):
        return build_failure_response(
            "Verification field 'errors' must be a list.",
            stage=stage,
        )

    return {
        "valid": True,
        "verified": result["verified"],
        "result": result,
        "errors": [],
        "stage": stage,
    }


def safe_execute(
    operation,
    *,
    stage: str,
    context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Execute a verification operation safely.

    Any unexpected exception is converted into a deterministic
    rejection response instead of propagating an unsafe failure.
    """

    try:
        result = operation()

        validation = validate_verification_result(
            result,
            stage=stage,
        )

        if not validation["valid"]:
            return validation

        return {
            "valid": True,
            "verified": validation["verified"],
            "result": result,
            "errors": [],
            "stage": stage,
        }

    except Exception as exc:
        return build_failure_response(
            exc,
            stage=stage,
            context=context,
        )

