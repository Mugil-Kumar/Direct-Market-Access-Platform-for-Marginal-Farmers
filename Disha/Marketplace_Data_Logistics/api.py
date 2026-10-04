from typing import List

from shared.schemas.schemas import (
    Buyer,
    Demand,
    Farmer,
    Order,
    Supply,
)

from .buyer import BuyerRegistry
from .database import Database
from .demand import DemandRegistry
from .farmer import FarmerRegistry
from .orders import OrderRegistry
from .supply import SupplyRegistry


class MarketplaceService:
    """
    Main marketplace service for AGRIWEAVE.

    Coordinates farmer registration, buyer registration, supply,
    demand, and order state while keeping persistent marketplace
    data backed by SQLite.
    """

    def __init__(
        self,
        database: Database | None = None,
    ) -> None:
        self.database = database or Database()

        self.farmers = FarmerRegistry(self.database)
        self.buyers = BuyerRegistry(self.database)
        self.supplies = SupplyRegistry(self.database)
        self.demands = DemandRegistry(self.database)
        self.orders = OrderRegistry(self.database)

    # ------------------------------------------------------------------
    # Farmer operations
    # ------------------------------------------------------------------

    def register_farmer(
        self,
        farmer: Farmer,
    ) -> Farmer:
        return self.farmers.register(farmer)

    def get_farmer(
        self,
        farmer_id: str,
    ) -> Farmer:
        farmer = self.farmers.get(farmer_id)

        if farmer is None:
            raise KeyError(
                f"Farmer '{farmer_id}' not found."
            )

        return farmer

    # ------------------------------------------------------------------
    # Buyer operations
    # ------------------------------------------------------------------

    def register_buyer(
        self,
        buyer: Buyer,
    ) -> Buyer:
        return self.buyers.register(buyer)

    def get_buyer(
        self,
        buyer_id: str,
    ) -> Buyer:
        buyer = self.buyers.get(buyer_id)

        if buyer is None:
            raise KeyError(
                f"Buyer '{buyer_id}' not found."
            )

        return buyer

    # ------------------------------------------------------------------
    # Supply operations
    # ------------------------------------------------------------------

    def list_supply(
        self,
        supply: Supply,
    ) -> Supply:
        if not self.farmers.exists(supply.farmer_id):
            raise ValueError(
                f"Cannot list supply: farmer "
                f"'{supply.farmer_id}' is not registered."
            )

        return self.supplies.add(supply)

    def get_supply(
        self,
        supply_id: str,
    ) -> Supply:
        supply = self.supplies.get(supply_id)

        if supply is None:
            raise KeyError(
                f"Supply '{supply_id}' not found."
            )

        return supply

    def find_supply_for_crop(
        self,
        crop: str,
    ) -> List[Supply]:
        return self.supplies.available_for_crop(crop)

    # ------------------------------------------------------------------
    # Demand operations
    # ------------------------------------------------------------------

    def create_demand(
        self,
        demand: Demand,
    ) -> Demand:
        if not self.buyers.exists(demand.buyer_id):
            raise ValueError(
                f"Cannot create demand: buyer "
                f"'{demand.buyer_id}' is not registered."
            )

        return self.demands.create(demand)

    def get_demand(
        self,
        demand_id: str,
    ) -> Demand:
        demand = self.demands.get(demand_id)

        if demand is None:
            raise KeyError(
                f"Demand '{demand_id}' not found."
            )

        return demand

    def find_demand_for_crop(
        self,
        crop: str,
    ) -> List[Demand]:
        return self.demands.open_for_crop(crop)

    # ------------------------------------------------------------------
    # Order operations
    # ------------------------------------------------------------------

    def create_order(
        self,
        order: Order,
    ) -> Order:
        demand = self.demands.get(order.demand_id)

        if demand is None:
            raise ValueError(
                f"Cannot create order: demand "
                f"'{order.demand_id}' does not exist."
            )

        if demand.status in {
            "fulfilled",
            "cancelled",
        }:
            raise ValueError(
                f"Cannot create order for demand "
                f"'{demand.id}' because its status is "
                f"'{demand.status}'."
            )

        if order.quantity_kg <= 0:
            raise ValueError(
                "Order quantity must be greater than zero."
            )

        if order.quantity_kg > demand.quantity_kg:
            raise ValueError(
                "Order quantity cannot exceed demand quantity."
            )

        if order.selling_price_per_kg > demand.max_price_per_kg:
            raise ValueError(
                "Selling price cannot exceed buyer's maximum price."
            )

        for supply_id in order.supply_ids:
            supply = self.supplies.get(supply_id)

            if supply is None:
                raise ValueError(
                    f"Cannot create order: supply "
                    f"'{supply_id}' does not exist."
                )

            if supply.status != "available":
                raise ValueError(
                    f"Supply '{supply_id}' is not available."
                )

            if supply.crop.strip().lower() != demand.crop.strip().lower():
                raise ValueError(
                    f"Supply '{supply_id}' crop does not match "
                    f"demand '{demand.id}'."
                )

            if supply.quality.strip().lower() != demand.quality_required.strip().lower():
                raise ValueError(
                    f"Supply '{supply_id}' quality does not satisfy "
                    f"demand '{demand.id}'."
                )

        total_supply_quantity = sum(
            self.supplies.get(supply_id).quantity_kg
            for supply_id in order.supply_ids
        )

        if total_supply_quantity < order.quantity_kg:
            raise ValueError(
                "Selected supplies do not contain enough quantity "
                "for this order."
            )

        # Validate the complete order before changing supply state.
        created_order = self.orders.create(order)

        try:
            for supply_id in order.supply_ids:
                self.supplies.reserve(supply_id)
        except Exception:
            # Keep the persistent order from remaining in a misleading
            # state if supply reservation unexpectedly fails.
            self.database.execute(
                "DELETE FROM order_supplies WHERE order_id = ?",
                (order.id,),
            )
            self.database.execute(
                "DELETE FROM orders WHERE id = ?",
                (order.id,),
            )
            self.orders._orders.pop(order.id, None)
            raise

        if order.quantity_kg >= demand.quantity_kg:
            self.demands.fulfill(demand.id)
        else:
            self.demands.mark_partially_matched(
                demand.id
            )

        return created_order

    def get_order(
        self,
        order_id: str,
    ) -> Order:
        order = self.orders.get(order_id)

        if order is None:
            raise KeyError(
                f"Order '{order_id}' not found."
            )

        return order

    def list_orders(self) -> List[Order]:
        return self.orders.list_all()

    def update_order_status(
        self,
        order_id: str,
        status: str,
    ) -> Order:
        return self.orders.update_status(
            order_id,
            status,
        )

    # ------------------------------------------------------------------
    # Financial calculation
    # ------------------------------------------------------------------

    def calculate_order_net_realization(
        self,
        order_id: str,
    ) -> float:
        order = self.get_order(order_id)

        gross_value = (
            order.quantity_kg
            * order.selling_price_per_kg
        )

        total_cost = (
            order.transport_cost
            + order.collection_cost
            + order.packaging_cost
            + order.spoilage_cost
            + order.platform_fee
        )

        return gross_value - total_cost