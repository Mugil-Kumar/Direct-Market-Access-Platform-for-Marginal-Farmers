from dataclasses import asdict
from typing import Dict, List, Optional

from shared.schemas.schemas import Buyer


class BuyerRegistry:
    """
    In-memory buyer registry for the MVP.
    """

    def __init__(self) -> None:
        self._buyers: Dict[str, Buyer] = {}

    def register(self, buyer: Buyer) -> Buyer:
        if not buyer.id.strip():
            raise ValueError("Buyer ID cannot be empty.")

        if not buyer.name.strip():
            raise ValueError("Buyer name cannot be empty.")

        if not buyer.location.strip():
            raise ValueError("Buyer location cannot be empty.")

        if buyer.id in self._buyers:
            raise ValueError(f"Buyer '{buyer.id}' already exists.")

        self._buyers[buyer.id] = buyer
        return buyer

    def get(self, buyer_id: str) -> Optional[Buyer]:
        return self._buyers.get(buyer_id)

    def list_all(self) -> List[Buyer]:
        return list(self._buyers.values())

    def update_reliability(
        self,
        buyer_id: str,
        reliability_score: float,
    ) -> Buyer:
        buyer = self._buyers.get(buyer_id)

        if buyer is None:
            raise KeyError(f"Buyer '{buyer_id}' not found.")

        if not 0.0 <= reliability_score <= 1.0:
            raise ValueError("Reliability score must be between 0 and 1.")

        buyer.reliability_score = reliability_score
        return buyer

    def exists(self, buyer_id: str) -> bool:
        return buyer_id in self._buyers

    def to_dict(self, buyer_id: str) -> Dict:
        buyer = self.get(buyer_id)

        if buyer is None:
            raise KeyError(f"Buyer '{buyer_id}' not found.")

        return asdict(buyer)