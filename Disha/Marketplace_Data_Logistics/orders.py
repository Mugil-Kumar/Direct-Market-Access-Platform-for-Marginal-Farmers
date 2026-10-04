from dataclasses import asdict
from typing import Dict, List, Optional

from shared.schemas.schemas import Order


class OrderRegistry:
    """
    Order lifecycle manager for the marketplace.

    An order connects matched supply with buyer demand and tracks
    the commercial costs needed for net-realization calculations.
    """

    VALID_STATUSES = {
        "pending",
        "confirmed",
        "in_transit",
        "delivered",
        "cancelled",
        "failed",
    }

    def __init__(self) -> None:
        self._orders: Dict[str, Order] = {}

    def create(self, order: Order) -> Order:
        if not order.id.strip():
            raise ValueError("Order ID cannot be empty.")

        if not order.demand_id.strip():
            raise ValueError("Demand ID cannot be empty.")

        if not order.supply_ids:
            raise ValueError("An order must contain at least one supply ID.")

        if order.quantity_kg <= 0:
            raise ValueError("Order quantity must be greater than zero.")

        if order.selling_price_per_kg < 0:
            raise ValueError("Selling price cannot be negative.")

        if order.status not in self.VALID_STATUSES:
            raise ValueError(f"Invalid order status: {order.status}")

        if order.id in self._orders:
            raise ValueError(f"Order '{order.id}' already exists.")

        self._orders[order.id] = order
        return order

    def get(self, order_id: str) -> Optional[Order]:
        return self._orders.get(order_id)

    def list_all(self) -> List[Order]:
        return list(self._orders.values())

    def update_status(self, order_id: str, status: str) -> Order:
        order = self.get(order_id)

        if order is None:
            raise KeyError(f"Order '{order_id}' not found.")

        if status not in self.VALID_STATUSES:
            raise ValueError(f"Invalid order status: {status}")

        order.status = status
        return order

    def cancel(self, order_id: str) -> Order:
        return self.update_status(order_id, "cancelled")

    def total_cost(self, order_id: str) -> float:
        order = self.get(order_id)

        if order is None:
            raise KeyError(f"Order '{order_id}' not found.")

        return (
            order.transport_cost
            + order.collection_cost
            + order.packaging_cost
            + order.spoilage_cost
            + order.platform_fee
        )

    def net_realization(self, order_id: str) -> float:
        order = self.get(order_id)

        if order is None:
            raise KeyError(f"Order '{order_id}' not found.")

        gross_value = (
            order.quantity_kg * order.selling_price_per_kg
        )

        return gross_value - self.total_cost(order_id)

    def to_dict(self, order_id: str) -> Dict:
        order = self.get(order_id)

        if order is None:
            raise KeyError(f"Order '{order_id}' not found.")

        return asdict(order)