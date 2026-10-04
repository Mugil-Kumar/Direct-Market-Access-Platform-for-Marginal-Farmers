from dataclasses import asdict
from typing import Dict, List, Optional

from shared.schemas.schemas import Demand

from .database import Database


class DemandRegistry:
    """
    Marketplace demand registry.

    Tracks buyer requirements, keeps an in-memory representation
    for fast access, and persists demand records to SQLite when
    a Database instance is provided.
    """

    VALID_STATUSES = {
        "open",
        "partially_matched",
        "fulfilled",
        "cancelled",
    }

    def __init__(self, database: Optional[Database] = None) -> None:
        self.database = database
        self._demands: Dict[str, Demand] = {}

        if self.database is not None:
            self._load_from_database()

    def _row_to_demand(self, row) -> Demand:
        return Demand(
            id=row["id"],
            buyer_id=row["buyer_id"],
            crop=row["crop"],
            quantity_kg=row["quantity_kg"],
            destination=row["destination"],
            deadline=row["deadline"],
            max_price_per_kg=row["max_price_per_kg"],
            quality_required=row["quality_required"],
            status=row["status"],
        )

    def _load_from_database(self) -> None:
        rows = self.database.fetch_all(
            """
            SELECT
                id,
                buyer_id,
                crop,
                quantity_kg,
                destination,
                deadline,
                max_price_per_kg,
                quality_required,
                status
            FROM demands
            ORDER BY id
            """
        )

        for row in rows:
            demand = self._row_to_demand(row)
            self._demands[demand.id] = demand

    def add(self, demand: Demand) -> Demand:
        """
        Add a new buyer demand.

        The demand is validated, persisted to SQLite when a database
        is configured, and then stored in the in-memory registry.
        """

        if not demand.id.strip():
            raise ValueError("Demand ID cannot be empty.")

        if not demand.buyer_id.strip():
            raise ValueError("Buyer ID cannot be empty.")

        if not demand.crop.strip():
            raise ValueError("Crop cannot be empty.")

        if demand.quantity_kg <= 0:
            raise ValueError("Demand quantity must be greater than zero.")

        if not demand.destination.strip():
            raise ValueError("Demand destination cannot be empty.")

        if demand.max_price_per_kg < 0:
            raise ValueError("Maximum price cannot be negative.")

        if demand.status not in self.VALID_STATUSES:
            raise ValueError(f"Invalid demand status: {demand.status}")

        if demand.id in self._demands:
            raise ValueError(f"Demand '{demand.id}' already exists.")

        if self.database is not None:
            existing = self.database.fetch_one(
                """
                SELECT id
                FROM demands
                WHERE id = ?
                """,
                (demand.id,),
            )

            if existing is not None:
                raise ValueError(
                    f"Demand '{demand.id}' already exists."
                )

            self.database.execute(
                """
                INSERT INTO demands (
                    id,
                    buyer_id,
                    crop,
                    quantity_kg,
                    destination,
                    deadline,
                    max_price_per_kg,
                    quality_required,
                    status
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    demand.id,
                    demand.buyer_id,
                    demand.crop,
                    demand.quantity_kg,
                    demand.destination,
                    demand.deadline,
                    demand.max_price_per_kg,
                    demand.quality_required,
                    demand.status,
                ),
            )

        self._demands[demand.id] = demand

        return demand

    def create(self, demand: Demand) -> Demand:
        """
        Backward-compatible method used by MarketplaceService.

        This delegates to add() so existing marketplace code continues
        to work while demand persistence remains enabled.
        """
        return self.add(demand)

    def get(self, demand_id: str) -> Optional[Demand]:
        """
        Retrieve a demand by ID.
        """

        demand = self._demands.get(demand_id)

        if demand is not None:
            return demand

        if self.database is None:
            return None

        row = self.database.fetch_one(
            """
            SELECT
                id,
                buyer_id,
                crop,
                quantity_kg,
                destination,
                deadline,
                max_price_per_kg,
                quality_required,
                status
            FROM demands
            WHERE id = ?
            """,
            (demand_id,),
        )

        if row is None:
            return None

        demand = self._row_to_demand(row)
        self._demands[demand.id] = demand

        return demand

    def list_all(self) -> List[Demand]:
        """
        Return all registered demands.
        """

        if self.database is not None:
            self._load_from_database()

        return list(self._demands.values())

    def open_for_crop(self, crop: str) -> List[Demand]:
        """
        Return all currently open demands for a crop.
        """

        normalized_crop = crop.strip().lower()

        if self.database is not None:
            rows = self.database.fetch_all(
                """
                SELECT
                    id,
                    buyer_id,
                    crop,
                    quantity_kg,
                    destination,
                    deadline,
                    max_price_per_kg,
                    quality_required,
                    status
                FROM demands
                WHERE LOWER(TRIM(crop)) = ?
                AND status = 'open'
                ORDER BY id
                """,
                (normalized_crop,),
            )

            demands = []

            for row in rows:
                demand = self._row_to_demand(row)
                self._demands[demand.id] = demand
                demands.append(demand)

            return demands

        return [
            demand
            for demand in self._demands.values()
            if demand.crop.strip().lower() == normalized_crop
            and demand.status == "open"
        ]

    def mark_partially_matched(self, demand_id: str) -> Demand:
        """
        Mark a demand as partially matched.
        """

        demand = self.get(demand_id)

        if demand is None:
            raise KeyError(
                f"Demand '{demand_id}' not found."
            )

        if demand.status not in {
            "open",
            "partially_matched",
        }:
            raise ValueError(
                f"Demand '{demand_id}' cannot be partially matched "
                f"because its status is '{demand.status}'."
            )

        self._update_status(
            demand_id,
            "partially_matched",
        )

        demand.status = "partially_matched"

        return demand

    def fulfill(self, demand_id: str) -> Demand:
        """
        Mark a demand as fulfilled.
        """

        demand = self.get(demand_id)

        if demand is None:
            raise KeyError(
                f"Demand '{demand_id}' not found."
            )

        if demand.status not in {
            "open",
            "partially_matched",
        }:
            raise ValueError(
                f"Demand '{demand_id}' cannot be fulfilled "
                f"because its status is '{demand.status}'."
            )

        self._update_status(
            demand_id,
            "fulfilled",
        )

        demand.status = "fulfilled"

        return demand

    def cancel(self, demand_id: str) -> Demand:
        """
        Cancel an existing demand.
        """

        demand = self.get(demand_id)

        if demand is None:
            raise KeyError(
                f"Demand '{demand_id}' not found."
            )

        if demand.status == "fulfilled":
            raise ValueError(
                f"Demand '{demand_id}' cannot be cancelled "
                f"after fulfillment."
            )

        self._update_status(
            demand_id,
            "cancelled",
        )

        demand.status = "cancelled"

        return demand

    def _update_status(
        self,
        demand_id: str,
        status: str,
    ) -> None:
        """
        Persist a demand status update to SQLite.
        """

        if self.database is not None:
            self.database.execute(
                """
                UPDATE demands
                SET status = ?
                WHERE id = ?
                """,
                (
                    status,
                    demand_id,
                ),
            )

    def to_dict(self, demand_id: str) -> Dict:
        """
        Return a demand as a dictionary.
        """

        demand = self.get(demand_id)

        if demand is None:
            raise KeyError(
                f"Demand '{demand_id}' not found."
            )

        return asdict(demand)