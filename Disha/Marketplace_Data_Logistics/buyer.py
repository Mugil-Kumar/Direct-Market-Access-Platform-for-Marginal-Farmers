from dataclasses import asdict
from typing import Dict, List, Optional

from shared.schemas.schemas import Buyer

from .database import Database


class BuyerRegistry:
    """
    Buyer registry for the MVP.

    The registry keeps an in-memory representation for fast marketplace
    operations and optionally persists buyer records to SQLite.
    """

    def __init__(self, database: Optional[Database] = None) -> None:
        self.database = database
        self._buyers: Dict[str, Buyer] = {}

        if self.database is not None:
            self._load_from_database()

    def _load_from_database(self) -> None:
        rows = self.database.fetch_all(
            """
            SELECT id, name, location, phone, reliability_score
            FROM buyers
            ORDER BY id
            """
        )

        for row in rows:
            buyer = Buyer(
                id=row["id"],
                name=row["name"],
                location=row["location"],
                phone=row["phone"],
                reliability_score=row["reliability_score"],
            )

            self._buyers[buyer.id] = buyer

    def register(self, buyer: Buyer) -> Buyer:
        if not buyer.id.strip():
            raise ValueError("Buyer ID cannot be empty.")

        if not buyer.name.strip():
            raise ValueError("Buyer name cannot be empty.")

        if not buyer.location.strip():
            raise ValueError("Buyer location cannot be empty.")

        if buyer.id in self._buyers:
            raise ValueError(f"Buyer '{buyer.id}' already exists.")

        if self.database is not None:
            existing = self.database.fetch_one(
                "SELECT id FROM buyers WHERE id = ?",
                (buyer.id,),
            )

            if existing is not None:
                raise ValueError(f"Buyer '{buyer.id}' already exists.")

            self.database.execute(
                """
                INSERT INTO buyers
                (id, name, location, phone, reliability_score)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    buyer.id,
                    buyer.name,
                    buyer.location,
                    buyer.phone,
                    buyer.reliability_score,
                ),
            )

        self._buyers[buyer.id] = buyer

        return buyer

    def get(self, buyer_id: str) -> Optional[Buyer]:
        buyer = self._buyers.get(buyer_id)

        if buyer is not None:
            return buyer

        if self.database is None:
            return None

        row = self.database.fetch_one(
            """
            SELECT id, name, location, phone, reliability_score
            FROM buyers
            WHERE id = ?
            """,
            (buyer_id,),
        )

        if row is None:
            return None

        buyer = Buyer(
            id=row["id"],
            name=row["name"],
            location=row["location"],
            phone=row["phone"],
            reliability_score=row["reliability_score"],
        )

        self._buyers[buyer.id] = buyer

        return buyer

    def list_all(self) -> List[Buyer]:
        if self.database is not None:
            self._load_from_database()

        return list(self._buyers.values())

    def update_reliability(
        self,
        buyer_id: str,
        reliability_score: float,
    ) -> Buyer:
        buyer = self.get(buyer_id)

        if buyer is None:
            raise KeyError(f"Buyer '{buyer_id}' not found.")

        if not 0.0 <= reliability_score <= 1.0:
            raise ValueError("Reliability score must be between 0 and 1.")

        buyer.reliability_score = reliability_score

        if self.database is not None:
            self.database.execute(
                """
                UPDATE buyers
                SET reliability_score = ?
                WHERE id = ?
                """,
                (reliability_score, buyer_id),
            )

        return buyer

    def exists(self, buyer_id: str) -> bool:
        return self.get(buyer_id) is not None

    def to_dict(self, buyer_id: str) -> Dict:
        buyer = self.get(buyer_id)

        if buyer is None:
            raise KeyError(f"Buyer '{buyer_id}' not found.")

        return asdict(buyer)