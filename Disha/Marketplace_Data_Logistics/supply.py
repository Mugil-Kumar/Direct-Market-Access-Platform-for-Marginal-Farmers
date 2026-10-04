from dataclasses import asdict
from typing import Dict, List, Optional

from shared.schemas.schemas import Supply

from .database import Database


class SupplyRegistry:
    """
    Marketplace supply registry.

    Tracks farmer-listed produce, keeps an in-memory representation
    for fast access, and optionally persists supply records to SQLite.
    """

    VALID_STATUSES = {
        "available",
        "reserved",
        "fulfilled",
        "cancelled",
    }

    def __init__(self, database: Optional[Database] = None) -> None:
        self.database = database
        self._supplies: Dict[str, Supply] = {}

        if self.database is not None:
            self._load_from_database()

    def _row_to_supply(self, row) -> Supply:
        return Supply(
            id=row["id"],
            farmer_id=row["farmer_id"],
            crop=row["crop"],
            quantity_kg=row["quantity_kg"],
            location=row["location"],
            available_from=row["available_from"],
            available_until=row["available_until"],
            quality=row["quality"],
            expected_price_per_kg=row["expected_price_per_kg"],
            status=row["status"],
        )

    def _load_from_database(self) -> None:
        rows = self.database.fetch_all(
            """
            SELECT
                id,
                farmer_id,
                crop,
                quantity_kg,
                location,
                available_from,
                available_until,
                quality,
                expected_price_per_kg,
                status
            FROM supplies
            ORDER BY id
            """
        )

        for row in rows:
            supply = self._row_to_supply(row)
            self._supplies[supply.id] = supply

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

        if self.database is not None:
            existing = self.database.fetch_one(
                "SELECT id FROM supplies WHERE id = ?",
                (supply.id,),
            )

            if existing is not None:
                raise ValueError(f"Supply '{supply.id}' already exists.")

            self.database.execute(
                """
                INSERT INTO supplies (
                    id,
                    farmer_id,
                    crop,
                    quantity_kg,
                    location,
                    available_from,
                    available_until,
                    quality,
                    expected_price_per_kg,
                    status
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    supply.id,
                    supply.farmer_id,
                    supply.crop,
                    supply.quantity_kg,
                    supply.location,
                    supply.available_from,
                    supply.available_until,
                    supply.quality,
                    supply.expected_price_per_kg,
                    supply.status,
                ),
            )

        self._supplies[supply.id] = supply

        return supply

    def get(self, supply_id: str) -> Optional[Supply]:
        supply = self._supplies.get(supply_id)

        if supply is not None:
            return supply

        if self.database is None:
            return None

        row = self.database.fetch_one(
            """
            SELECT
                id,
                farmer_id,
                crop,
                quantity_kg,
                location,
                available_from,
                available_until,
                quality,
                expected_price_per_kg,
                status
            FROM supplies
            WHERE id = ?
            """,
            (supply_id,),
        )

        if row is None:
            return None

        supply = self._row_to_supply(row)
        self._supplies[supply.id] = supply

        return supply

    def list_all(self) -> List[Supply]:
        if self.database is not None:
            self._load_from_database()

        return list(self._supplies.values())

    def available_for_crop(self, crop: str) -> List[Supply]:
        normalized_crop = crop.strip().lower()

        if self.database is not None:
            rows = self.database.fetch_all(
                """
                SELECT
                    id,
                    farmer_id,
                    crop,
                    quantity_kg,
                    location,
                    available_from,
                    available_until,
                    quality,
                    expected_price_per_kg,
                    status
                FROM supplies
                WHERE LOWER(TRIM(crop)) = ?
                AND status = 'available'
                ORDER BY id
                """,
                (normalized_crop,),
            )

            supplies = []

            for row in rows:
                supply = self._row_to_supply(row)
                self._supplies[supply.id] = supply
                supplies.append(supply)

            return supplies

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

        if self.database is not None:
            self.database.execute(
                """
                UPDATE supplies
                SET status = 'reserved'
                WHERE id = ?
                AND status = 'available'
                """,
                (supply_id,),
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

        if self.database is not None:
            self.database.execute(
                """
                UPDATE supplies
                SET status = 'available'
                WHERE id = ?
                AND status = 'reserved'
                """,
                (supply_id,),
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

        if self.database is not None:
            self.database.execute(
                """
                UPDATE supplies
                SET status = 'fulfilled'
                WHERE id = ?
                AND status = 'reserved'
                """,
                (supply_id,),
            )

        supply.status = "fulfilled"

        return supply

    def to_dict(self, supply_id: str) -> Dict:
        supply = self.get(supply_id)

        if supply is None:
            raise KeyError(f"Supply '{supply_id}' not found.")

        return asdict(supply)