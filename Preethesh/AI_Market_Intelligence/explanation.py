"""
AGRIWEAVE explainable AI helpers.

Converts matching scores into short, human-readable explanations.
"""

from typing import Any, List, Optional


def explain_candidate(score: Any) -> str:
    """
    Explain why an individual supply candidate received its score.
    """

    if score is None:
        return "No candidate score is available."

    if not getattr(score, "eligible", True):
        reasons = getattr(score, "rejection_reasons", []) or []

        if reasons:
            return (
                f"Candidate {score.supply_id} was rejected because "
                + "; ".join(reasons)
                + "."
            )

        return f"Candidate {score.supply_id} was rejected."

    components = {
        "quantity": float(getattr(score, "quantity_score", 0.0)),
        "price": float(getattr(score, "price_score", 0.0)),
        "distance": float(getattr(score, "distance_score", 0.0)),
        "deadline": float(getattr(score, "deadline_score", 0.0)),
        "quality": float(getattr(score, "quality_score", 0.0)),
        "reliability": float(getattr(score, "reliability_score", 0.0)),
    }

    highest_score = max(components.values())

    strongest = [
        name
        for name, value in components.items()
        if value == highest_score
    ]

    strongest_text = ", ".join(strongest)

    return (
        f"Candidate {score.supply_id} is eligible with an overall "
        f"score of {float(score.total_score):.2f}. "
        f"Its strongest matching factor(s) are "
        f"{strongest_text} ({highest_score:.2f})."
    )


def explain_recommendation(
    recommendation: Any,
    candidate_score: Optional[Any] = None,
) -> str:
    """
    Build a human-readable explanation for a final recommendation.
    """

    if recommendation is None:
        return "No recommendation is available."

    supply_ids = getattr(
        recommendation,
        "recommended_supply_ids",
        [],
    ) or []

    coverage = float(
        getattr(recommendation, "coverage_percent", 0.0)
    )

    score = float(
        getattr(recommendation, "score", 0.0)
    )

    if not supply_ids:
        return "No feasible supply recommendation was found."

    if len(supply_ids) > 1:
        explanation = (
            f"A collective recommendation using {len(supply_ids)} "
            f"farmers was selected with a score of {score:.2f} "
            f"and {coverage:.1f}% quantity coverage."
        )
    else:
        explanation = (
            f"Supply {supply_ids[0]} was recommended with a "
            f"score of {score:.2f} and {coverage:.1f}% quantity coverage."
        )

    if candidate_score is not None:
        candidate_explanation = explain_candidate(candidate_score)
        explanation += f" {candidate_explanation}"

    return explanation


def explain_rejections(
    rejection_reasons: Optional[List[str]],
) -> str:
    """
    Convert rejection reasons into a readable sentence.
    """

    reasons = rejection_reasons or []

    if not reasons:
        return "No rejection reasons were recorded."

    return "Rejected because: " + "; ".join(reasons) + "."