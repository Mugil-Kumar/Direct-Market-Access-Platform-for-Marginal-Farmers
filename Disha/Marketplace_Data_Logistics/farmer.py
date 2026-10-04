from dataclasses import asdict
from typing import Dict, List, Optional

from shared.schemas.schemas import Farmer


class FarmerRegistry:
    """
    In-memory farmer registry for the MVP.

    The registry provides the marketplace with a clean interface for
    registering, retrieving, updating and validating farmers.
    """

    def __init__(self) -> None:
        self._farmers: Dict[str, Farmer] = {}

    def register(self, farmer: Farmer) -> Farmer:
        if not farmer.id.strip():
            raise ValueError("Farmer ID cannot be empty.")

        if not farmer.name.strip():
            raise ValueError("Farmer name cannot be empty.")

        if not farmer.location.strip():
            raise ValueError("Farmer location cannot be empty.")

        if farmer.id in self._farmers:
            raise ValueError(f"Farmer '{farmer.id}' already exists.")

        self._farmers[farmer.id] = farmer
        return farmer

    def get(self, farmer_id: str) -> Optional[Farmer]:
        return self._farmers.get(farmer_id)

    def list_all(self) -> List[Farmer]:
        return list(self._farmers.values())

    def update_reliability(
        self,
        farmer_id: str,
        reliability_score: float,
    ) -> Farmer:
        farmer = self._farmers.get(farmer_id)

        if farmer is None:
            raise KeyError(f"Farmer '{farmer_id}' not found.")

        if not 0.0 <= reliability_score <= 1.0:
            raise ValueError("Reliability score must be between 0 and 1.")

        farmer.reliability_score = reliability_score
        return farmer

    def exists(self, farmer_id: str) -> bool:
        return farmer_id in self._farmers

    def to_dict(self, farmer_id: str) -> Dict:
        farmer = self.get(farmer_id)

        if farmer is None:
            raise KeyError(f"Farmer '{farmer_id}' not found.")

        return asdict(farmer)