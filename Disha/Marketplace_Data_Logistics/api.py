from typing import List

from shared.schemas.schemas import (
    Buyer,
    Demand,
    Farmer,
    Order,
    Supply,
)

from .buyer import BuyerRegistry
from .demand import DemandRegistry
from .farmer import FarmerRegistry
from .orders import OrderRegistry
from .supply import SupplyRegistry


class MarketplaceService:
    """
    Main marketplace service.

    This is the integration boundary for the rest of AGRIWEAVE.

    Other modules should preferably interact with MarketplaceService
    instead of directly modifying the underlying registries.
    """

    def __init__(self) -> None:
        self.farmers = FarmerRegistry()
        self.buyers = BuyerRegistry()
        self.supplies = SupplyRegistry()
        self.demands = DemandRegistry()
        self.orders = OrderRegistry()

    # ------------------------------------------------------------------
    # Farmers
    # ------------------------------------------------------------------

    def register_farmer(self, farmer: Farmer) -> Farmer:
        return self.farmers.register(farmer)

    def get_farmer(self, farmer_id: str) -> Farmer:
        farmer = self.farmers.get(farmer_id)

        if farmer is None:
            raise KeyError(f"Farmer '{farmer_id}' not found.")

        return farmer

    # ------------------------------------------------------------------
    # Buyers
    # ------------------------------------------------------------------

    def register_buyer(self, buyer: Buyer) -> Buyer:
        return self.buyers.register(buyer)

    def get_buyer(self, buyer_id: str) -> Buyer:
        buyer = self.buyers.get(buyer_id)

        if buyer is None:
            raise KeyError(f"Buyer '{buyer_id}' not found.")

        return buyer

    # ------------------------------------------------------------------
    # Supply
    # ------------------------------------------------------------------

    def list_supply(self, supply: Supply) -> Supply:
        if not self.farmers.exists(supply.farmer_id):
            raise ValueError(
                f"Cannot list supply: farmer "
                f"'{supply.farmer_id}' is not registered."
            )

        return self.supplies.add(supply)

    def find_supply_for_crop(self, crop: str) -> List[Supply]:
        return self.supplies.available_for_crop(crop)

    def reserve_supply(self, supply_id: str) -> Supply:
        return self.supplies.reserve(supply_id)

    def release_supply(self, supply_id: str) -> Supply:
        return self.supplies.release(supply_id)

    def fulfill_supply(self, supply_id: str) -> Supply:
        return self.supplies.fulfill(supply_id)

    # ------------------------------------------------------------------
    # Demand
    # ------------------------------------------------------------------

    def create_demand(self, demand: Demand) -> Demand:
        if not self.buyers.exists(demand.buyer_id):
            raise ValueError(
                f"Cannot create demand: buyer "
                f"'{demand.buyer_id}' is not registered."
            )

        return self.demands.create(demand)

    def find_demand_for_crop(self, crop: str) -> List[Demand]:
        return self.demands.open_for_crop(crop)

    # ------------------------------------------------------------------
    # Orders
    # ------------------------------------------------------------------

    def create_order(self, order: Order) -> Order:
        demand = self.demands.get(order.demand_id)

        if demand is None:
            raise ValueError(
                f"Cannot create order: demand "
                f"'{order.demand_id}' does not exist."
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

        for supply_id in order.supply_ids:
            self.supplies.reserve(supply_id)

        created_order = self.orders.create(order)

        if created_order.quantity_kg >= demand.quantity_kg:
            self.demands.fulfill(demand.id)
        else:
            self.demands.mark_partially_matched(demand.id)

        return created_order

    def update_order_status(
        self,
        order_id: str,
        status: str,
    ) -> Order:
        return self.orders.update_status(order_id, status)

    def calculate_order_net_realization(
        self,
        order_id: str,
    ) -> float:
        return self.orders.net_realization(order_id)