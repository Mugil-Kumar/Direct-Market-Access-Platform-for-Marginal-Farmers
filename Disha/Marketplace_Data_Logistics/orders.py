from dataclasses import asdict
from typing import Dict, List, Optional

from shared.schemas.schemas import Order

from .database import Database


class OrderRegistry:
    """
    Marketplace order registry.

    Stores orders in memory for fast access and persists them to
    SQLite when a Database instance is provided.
    """

    VALID_STATUSES = {
        "pending",
        "confirmed",
        "in_transit",
        "delivered",
        "cancelled",
        "failed",
    }

    def __init__(self, database: Optional[Database] = None) -> None:
        self.database = database
        self._orders: Dict[str, Order] = {}

        if self.database is not None:
            self._load_from_database()

    def _row_to_order(self, row) -> Order:
        supply_rows = self.database.fetch_all(
            """
            SELECT supply_id
            FROM order_supplies
            WHERE order_id = ?
            ORDER BY supply_id
            """,
            (row["id"],),
        )

        supply_ids = [
            supply_row["supply_id"]
            for supply_row in supply_rows
        ]

        return Order(
            id=row["id"],
            demand_id=row["demand_id"],
            supply_ids=supply_ids,
            quantity_kg=row["quantity_kg"],
            selling_price_per_kg=row["selling_price_per_kg"],
            transport_cost=row["transport_cost"],
            collection_cost=row["collection_cost"],
            packaging_cost=row["packaging_cost"],
            spoilage_cost=row["spoilage_cost"],
            platform_fee=row["platform_fee"],
            status=row["status"],
        )

    def _load_from_database(self) -> None:
        rows = self.database.fetch_all(
            """
            SELECT
                id,
                demand_id,
                quantity_kg,
                selling_price_per_kg,
                transport_cost,
                collection_cost,
                packaging_cost,
                spoilage_cost,
                platform_fee,
                status
            FROM orders
            ORDER BY id
            """
        )

        for row in rows:
            order = self._row_to_order(row)
            self._orders[order.id] = order

    def create(self, order: Order) -> Order:
        """
        Create and persist a new order.
        """

        if not order.id.strip():
            raise ValueError("Order ID cannot be empty.")

        if not order.demand_id.strip():
            raise ValueError("Demand ID cannot be empty.")

        if not order.supply_ids:
            raise ValueError(
                "At least one supply ID is required."
            )

        if order.quantity_kg <= 0:
            raise ValueError(
                "Order quantity must be greater than zero."
            )

        if order.selling_price_per_kg < 0:
            raise ValueError(
                "Selling price cannot be negative."
            )

        if order.transport_cost < 0:
            raise ValueError(
                "Transport cost cannot be negative."
            )

        if order.collection_cost < 0:
            raise ValueError(
                "Collection cost cannot be negative."
            )

        if order.packaging_cost < 0:
            raise ValueError(
                "Packaging cost cannot be negative."
            )

        if order.spoilage_cost < 0:
            raise ValueError(
                "Spoilage cost cannot be negative."
            )

        if order.platform_fee < 0:
            raise ValueError(
                "Platform fee cannot be negative."
            )

        if order.status not in self.VALID_STATUSES:
            raise ValueError(
                f"Invalid order status: {order.status}"
            )

        if order.id in self._orders:
            raise ValueError(
                f"Order '{order.id}' already exists."
            )

        if self.database is not None:
            existing = self.database.fetch_one(
                """
                SELECT id
                FROM orders
                WHERE id = ?
                """,
                (order.id,),
            )

            if existing is not None:
                raise ValueError(
                    f"Order '{order.id}' already exists."
                )

            self.database.execute(
                """
                INSERT INTO orders (
                    id,
                    demand_id,
                    quantity_kg,
                    selling_price_per_kg,
                    transport_cost,
                    collection_cost,
                    packaging_cost,
                    spoilage_cost,
                    platform_fee,
                    status
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    order.id,
                    order.demand_id,
                    order.quantity_kg,
                    order.selling_price_per_kg,
                    order.transport_cost,
                    order.collection_cost,
                    order.packaging_cost,
                    order.spoilage_cost,
                    order.platform_fee,
                    order.status,
                ),
            )

            for supply_id in order.supply_ids:
                self.database.execute(
                    """
                    INSERT INTO order_supplies (
                        order_id,
                        supply_id
                    )
                    VALUES (?, ?)
                    """,
                    (
                        order.id,
                        supply_id,
                    ),
                )

        self._orders[order.id] = order

        return order

    def get(self, order_id: str) -> Optional[Order]:
        """
        Retrieve an order by ID.
        """

        order = self._orders.get(order_id)

        if order is not None:
            return order

        if self.database is None:
            return None

        row = self.database.fetch_one(
            """
            SELECT
                id,
                demand_id,
                quantity_kg,
                selling_price_per_kg,
                transport_cost,
                collection_cost,
                packaging_cost,
                spoilage_cost,
                platform_fee,
                status
            FROM orders
            WHERE id = ?
            """,
            (order_id,),
        )

        if row is None:
            return None

        order = self._row_to_order(row)
        self._orders[order.id] = order

        return order

    def list_all(self) -> List[Order]:
        """
        Return all registered orders.
        """

        if self.database is not None:
            self._load_from_database()

        return list(self._orders.values())

    def update_status(
        self,
        order_id: str,
        status: str,
    ) -> Order:
        """
        Update and persist an order status.
        """

        if status not in self.VALID_STATUSES:
            raise ValueError(
                f"Invalid order status: {status}"
            )

        order = self.get(order_id)

        if order is None:
            raise KeyError(
                f"Order '{order_id}' not found."
            )

        if order.status == "delivered":
            raise ValueError(
                f"Order '{order_id}' cannot be changed "
                f"after delivery."
            )

        if order.status == "cancelled":
            raise ValueError(
                f"Order '{order_id}' cannot be changed "
                f"after cancellation."
            )

        if self.database is not None:
            self.database.execute(
                """
                UPDATE orders
                SET status = ?
                WHERE id = ?
                """,
                (
                    status,
                    order_id,
                ),
            )

        order.status = status

        return order

    def cancel(self, order_id: str) -> Order:
        """
        Cancel an order.
        """

        return self.update_status(
            order_id,
            "cancelled",
        )

    def to_dict(self, order_id: str) -> Dict:
        """
        Return an order as a dictionary.
        """

        order = self.get(order_id)

        if order is None:
            raise KeyError(
                f"Order '{order_id}' not found."
            )

        return asdict(order)