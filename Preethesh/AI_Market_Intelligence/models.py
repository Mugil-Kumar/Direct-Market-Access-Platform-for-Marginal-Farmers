"""
AI Market Intelligence data models.

This module defines AI-specific result models used by the
market intelligence and matching pipeline.

Core marketplace entities such as Farmer, Buyer, Supply and
Demand are imported from the shared schema so that all team
members use the same data contracts.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from shared.schemas.schemas import (
    Farmer,
    Buyer,
    Supply,
    Demand,
    Match,
)


@dataclass
class CandidateScore:
    """
    Score assigned to one supply candidate for a demand.

    Each component is kept separately so the final decision
    remains explainable rather than being a black-box number.
    """

    supply_id: str
    demand_id: str

    quantity_score: float = 0.0
    price_score: float = 0.0
    distance_score: float = 0.0
    deadline_score: float = 0.0
    quality_score: float = 0.0
    reliability_score: float = 0.0

    total_score: float = 0.0

    eligible: bool = True
    rejection_reasons: List[str] = field(default_factory=list)


@dataclass
class CollectiveCandidate:
    """
    Represents a combination of multiple farmers considered
    for fulfilling one buyer demand.
    """

    demand_id: str

    supply_ids: List[str] = field(default_factory=list)

    total_quantity_kg: float = 0.0
    required_quantity_kg: float = 0.0

    quantity_coverage_percent: float = 0.0

    estimated_price_per_kg: float = 0.0
    estimated_distance_km: float = 0.0

    farmer_count: int = 0

    total_score: float = 0.0

    feasible: bool = False

    rejection_reasons: List[str] = field(default_factory=list)


@dataclass
class MatchRecommendation:
    """
    Final AI recommendation presented to the application layer.

    Contains the strongest match, alternatives and the reasoning
    behind the recommendation.
    """

    demand_id: str

    recommended_supply_ids: List[str] = field(default_factory=list)

    recommended_quantity_kg: float = 0.0
    required_quantity_kg: float = 0.0

    coverage_percent: float = 0.0

    score: float = 0.0

    alternatives: List[CollectiveCandidate] = field(
        default_factory=list
    )

    explanation: str = ""

    warnings: List[str] = field(default_factory=list)


@dataclass
class MarketGapResult:
    """
    Describes a shortage or surplus detected for a crop.
    """

    crop: str

    demand_quantity_kg: float = 0.0
    available_supply_quantity_kg: float = 0.0

    shortage_quantity_kg: float = 0.0
    surplus_quantity_kg: float = 0.0

    demand_count: int = 0
    supply_count: int = 0

    status: str = "balanced"

    location: Optional[str] = None

    recommended_additional_supply_kg: float = 0.0


@dataclass
class MatchingWeights:
    """
    Configurable weights for the matching engine.

    All weights are normalized by the matching engine before
    calculating the final candidate score.
    """

    quantity: float = 0.25
    price: float = 0.20
    distance: float = 0.15
    deadline: float = 0.15
    quality: float = 0.10
    reliability: float = 0.15

    def as_dict(self) -> Dict[str, float]:
        """Return weights as a dictionary."""

        return {
            "quantity": self.quantity,
            "price": self.price,
            "distance": self.distance,
            "deadline": self.deadline,
            "quality": self.quality,
            "reliability": self.reliability,
        }

    def total(self) -> float:
        """Return the sum of all configured weights."""

        return sum(self.as_dict().values())


@dataclass
class MatchingContext:
    """
    Context passed through the AI matching pipeline.

    Keeps the original marketplace data together with matching
    configuration so each stage works from the same snapshot.
    """

    farmers: List[Farmer] = field(default_factory=list)
    buyers: List[Buyer] = field(default_factory=list)

    supplies: List[Supply] = field(default_factory=list)
    demands: List[Demand] = field(default_factory=list)

    weights: MatchingWeights = field(
        default_factory=MatchingWeights
    )

    max_distance_km: float = 100.0


@dataclass
class MatchingResult:
    """
    Complete output of the AI matching pipeline.
    """

    recommendations: List[MatchRecommendation] = field(
        default_factory=list
    )

    matches: List[Match] = field(
        default_factory=list
    )

    market_gaps: List[MarketGapResult] = field(
        default_factory=list
    )

    unmatched_demand_ids: List[str] = field(
        default_factory=list
    )

    processing_warnings: List[str] = field(
        default_factory=list
    )