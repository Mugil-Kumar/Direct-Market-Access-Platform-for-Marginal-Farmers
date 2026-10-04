from dataclasses import asdict
from typing import Dict, List, Optional

from shared.schemas.schemas import Farmer

from .database import Database


class FarmerRegistry:
    """
    Farmer registry for the MVP.

    The registry keeps an in-memory representation for fast marketplace
    operations and optionally persists farmer records to SQLite.
    """

    def __init__(self, database: Optional[Database] = None) -> None:
        self.database = database
        self._farmers: Dict[str, Farmer] = {}

        if self.database is not None:
            self._load_from_database()

    def _load_from_database(self) -> None:
        rows = self.database.fetch_all(
            """
            SELECT id, name, location, phone, reliability_score
            FROM farmers
            ORDER BY id
            """
        )

        for row in rows:
            farmer = Farmer(
                id=row["id"],
                name=row["name"],
                location=row["location"],
                phone=row["phone"],
                reliability_score=row["reliability_score"],
            )
            self._farmers[farmer.id] = farmer

    def register(self, farmer: Farmer) -> Farmer:
        if not farmer.id.strip():
            raise ValueError("Farmer ID cannot be empty.")

        if not farmer.name.strip():
            raise ValueError("Farmer name cannot be empty.")

        if not farmer.location.strip():
            raise ValueError("Farmer location cannot be empty.")

        if farmer.id in self._farmers:
            raise ValueError(f"Farmer '{farmer.id}' already exists.")

        if self.database is not None:
            existing = self.database.fetch_one(
                "SELECT id FROM farmers WHERE id = ?",
                (farmer.id,),
            )

            if existing is not None:
                raise ValueError(f"Farmer '{farmer.id}' already exists.")

            self.database.execute(
                """
                INSERT INTO farmers
                (id, name, location, phone, reliability_score)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    farmer.id,
                    farmer.name,
                    farmer.location,
                    farmer.phone,
                    farmer.reliability_score,
                ),
            )

        self._farmers[farmer.id] = farmer
        return farmer

    def get(self, farmer_id: str) -> Optional[Farmer]:
        farmer = self._farmers.get(farmer_id)

        if farmer is not None:
            return farmer

        if self.database is None:
            return None

        row = self.database.fetch_one(
            """
            SELECT id, name, location, phone, reliability_score
            FROM farmers
            WHERE id = ?
            """,
            (farmer_id,),
        )

        if row is None:
            return None

        farmer = Farmer(
            id=row["id"],
            name=row["name"],
            location=row["location"],
            phone=row["phone"],
            reliability_score=row["reliability_score"],
        )

        self._farmers[farmer.id] = farmer
        return farmer

    def list_all(self) -> List[Farmer]:
        if self.database is not None:
            self._load_from_database()

        return list(self._farmers.values())

    def update_reliability(
        self,
        farmer_id: str,
        reliability_score: float,
    ) -> Farmer:
        farmer = self.get(farmer_id)

        if farmer is None:
            raise KeyError(f"Farmer '{farmer_id}' not found.")

        if not 0.0 <= reliability_score <= 1.0:
            raise ValueError("Reliability score must be between 0 and 1.")

        farmer.reliability_score = reliability_score

        if self.database is not None:
            self.database.execute(
                """
                UPDATE farmers
                SET reliability_score = ?
                WHERE id = ?
                """,
                (reliability_score, farmer_id),
            )

        return farmer

    def exists(self, farmer_id: str) -> bool:
        return self.get(farmer_id) is not None

    def to_dict(self, farmer_id: str) -> Dict:
        farmer = self.get(farmer_id)

        if farmer is None:
            raise KeyError(f"Farmer '{farmer_id}' not found.")

        return asdict(farmer)