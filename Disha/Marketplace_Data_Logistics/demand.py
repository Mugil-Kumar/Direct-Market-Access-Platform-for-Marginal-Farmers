from dataclasses import asdict
from typing import Dict, List, Optional

from shared.schemas.schemas import Demand


class DemandRegistry:
    """
    Buyer demand registry for the marketplace.
    """

    VALID_STATUSES = {
        "open",
        "partially_matched",
        "fulfilled",
        "cancelled",
    }

    def __init__(self) -> None:
        self._demands: Dict[str, Demand] = {}

    def create(self, demand: Demand) -> Demand:
        if not demand.id.strip():
            raise ValueError("Demand ID cannot be empty.")

        if not demand.buyer_id.strip():
            raise ValueError("Buyer ID cannot be empty.")

        if not demand.crop.strip():
            raise ValueError("Crop cannot be empty.")

        if demand.quantity_kg <= 0:
            raise ValueError("Demand quantity must be greater than zero.")

        if demand.max_price_per_kg < 0:
            raise ValueError("Maximum price cannot be negative.")

        if demand.status not in self.VALID_STATUSES:
            raise ValueError(f"Invalid demand status: {demand.status}")

        if demand.id in self._demands:
            raise ValueError(f"Demand '{demand.id}' already exists.")

        self._demands[demand.id] = demand
        return demand

    def get(self, demand_id: str) -> Optional[Demand]:
        return self._demands.get(demand_id)

    def list_all(self) -> List[Demand]:
        return list(self._demands.values())

    def open_for_crop(self, crop: str) -> List[Demand]:
        normalized_crop = crop.strip().lower()

        return [
            demand
            for demand in self._demands.values()
            if demand.crop.strip().lower() == normalized_crop
            and demand.status in {"open", "partially_matched"}
        ]

    def mark_partially_matched(self, demand_id: str) -> Demand:
        demand = self.get(demand_id)

        if demand is None:
            raise KeyError(f"Demand '{demand_id}' not found.")

        if demand.status != "open":
            raise ValueError(
                f"Demand '{demand_id}' is not open."
            )

        demand.status = "partially_matched"
        return demand

    def fulfill(self, demand_id: str) -> Demand:
        demand = self.get(demand_id)

        if demand is None:
            raise KeyError(f"Demand '{demand_id}' not found.")

        if demand.status not in {"open", "partially_matched"}:
            raise ValueError(
                f"Demand '{demand_id}' cannot be fulfilled "
                f"from status '{demand.status}'."
            )

        demand.status = "fulfilled"
        return demand

    def cancel(self, demand_id: str) -> Demand:
        demand = self.get(demand_id)

        if demand is None:
            raise KeyError(f"Demand '{demand_id}' not found.")

        if demand.status == "fulfilled":
            raise ValueError("A fulfilled demand cannot be cancelled.")

        demand.status = "cancelled"
        return demand

    def to_dict(self, demand_id: str) -> Dict:
        demand = self.get(demand_id)

        if demand is None:
            raise KeyError(f"Demand '{demand_id}' not found.")

        return asdict(demand)