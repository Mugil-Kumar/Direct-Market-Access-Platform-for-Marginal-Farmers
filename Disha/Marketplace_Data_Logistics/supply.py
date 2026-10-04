from dataclasses import asdict
from typing import Dict, List, Optional

from shared.schemas.schemas import Supply


class SupplyRegistry:
    """
    Marketplace supply registry.

    Tracks farmer-listed produce and provides safe interfaces for
    reserving, releasing and fulfilling supply.
    """

    VALID_STATUSES = {
        "available",
        "reserved",
        "fulfilled",
        "cancelled",
    }

    def __init__(self) -> None:
        self._supplies: Dict[str, Supply] = {}

    def add(self, supply: Supply) -> Supply:
        if not supply.id.strip():
            raise ValueError("Supply ID cannot be empty.")

        if not supply.farmer_id.strip():
            raise ValueError("Farmer ID cannot be empty.")

        if not supply.crop.strip():
            raise ValueError("Crop cannot be empty.")

        if supply.quantity_kg <= 0:
            raise ValueError("Supply quantity must be greater than zero.")

        if supply.expected_price_per_kg < 0:
            raise ValueError("Expected price cannot be negative.")

        if supply.status not in self.VALID_STATUSES:
            raise ValueError(f"Invalid supply status: {supply.status}")

        if supply.id in self._supplies:
            raise ValueError(f"Supply '{supply.id}' already exists.")

        self._supplies[supply.id] = supply
        return supply

    def get(self, supply_id: str) -> Optional[Supply]:
        return self._supplies.get(supply_id)

    def list_all(self) -> List[Supply]:
        return list(self._supplies.values())

    def available_for_crop(self, crop: str) -> List[Supply]:
        normalized_crop = crop.strip().lower()

        return [
            supply
            for supply in self._supplies.values()
            if supply.crop.strip().lower() == normalized_crop
            and supply.status == "available"
        ]

    def reserve(self, supply_id: str) -> Supply:
        supply = self.get(supply_id)

        if supply is None:
            raise KeyError(f"Supply '{supply_id}' not found.")

        if supply.status != "available":
            raise ValueError(
                f"Supply '{supply_id}' cannot be reserved because "
                f"its status is '{supply.status}'."
            )

        supply.status = "reserved"
        return supply

    def release(self, supply_id: str) -> Supply:
        supply = self.get(supply_id)

        if supply is None:
            raise KeyError(f"Supply '{supply_id}' not found.")

        if supply.status != "reserved":
            raise ValueError(
                f"Supply '{supply_id}' cannot be released because "
                f"its status is '{supply.status}'."
            )

        supply.status = "available"
        return supply

    def fulfill(self, supply_id: str) -> Supply:
        supply = self.get(supply_id)

        if supply is None:
            raise KeyError(f"Supply '{supply_id}' not found.")

        if supply.status != "reserved":
            raise ValueError(
                f"Supply '{supply_id}' cannot be fulfilled because "
                f"its status is '{supply.status}'."
            )

        supply.status = "fulfilled"
        return supply

    def to_dict(self, supply_id: str) -> Dict:
        supply = self.get(supply_id)

        if supply is None:
            raise KeyError(f"Supply '{supply_id}' not found.")

        return asdict(supply)