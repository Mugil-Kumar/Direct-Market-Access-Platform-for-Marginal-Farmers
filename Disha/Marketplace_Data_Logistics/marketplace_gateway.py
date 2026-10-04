from typing import Any, Dict, List, Optional

from shared.schemas.schemas import Demand, Supply

from .api import MarketplaceService
from .location import LocationService


class MarketplaceGateway:
    """
    Unified data-access gateway for the AGRIWEAVE system.

    This is the integration boundary between Disha's marketplace
    infrastructure and the AI, optimization, and verification modules.

    The gateway exposes structured, read-focused access to:
    - current available supply
    - current open demand
    - farmer/buyer records
    - locations
    - logistics estimates
    - current marketplace state
    """

    def __init__(
        self,
        marketplace: Optional[MarketplaceService] = None,
        location_service: Optional[LocationService] = None,
    ) -> None:
        self.marketplace = marketplace or MarketplaceService()
        self.location_service = location_service or LocationService(
            self.marketplace.database
        )

    # ------------------------------------------------------------------
    # SUPPLY ACCESS
    # ------------------------------------------------------------------

    def get_available_supply(
        self,
        crop: Optional[str] = None,
    ) -> List[Supply]:
        """
        Return the latest available supply.

        If crop is supplied, only matching crop records are returned.
        """

        if crop:
            return self.marketplace.find_supply_for_crop(crop)

        return [
            supply
            for supply in self.marketplace.supplies.list_all()
            if supply.status == "available"
        ]

    def get_supply(self, supply_id: str) -> Supply:
        """
        Return one current supply record.
        """

        return self.marketplace.get_supply(supply_id)

    # ------------------------------------------------------------------
    # DEMAND ACCESS
    # ------------------------------------------------------------------

    def get_open_demands(
        self,
        crop: Optional[str] = None,
    ) -> List[Demand]:
        """
        Return the latest open buyer demands.

        If crop is supplied, only matching crop demands are returned.
        """

        if crop:
            return self.marketplace.find_demand_for_crop(crop)

        return [
            demand
            for demand in self.marketplace.demands.list_all()
            if demand.status == "open"
        ]

    def get_demand(self, demand_id: str) -> Demand:
        """
        Return one current demand record.
        """

        return self.marketplace.get_demand(demand_id)

    # ------------------------------------------------------------------
    # LOCATION ACCESS
    # ------------------------------------------------------------------

    def get_entity_location(
        self,
        entity_type: str,
        entity_id: str,
    ):
        """
        Return the latest persisted location for an entity.
        """

        return self.location_service.get_location(
            entity_type,
            entity_id,
        )

    # ------------------------------------------------------------------
    # LOGISTICS ACCESS
    # ------------------------------------------------------------------

    def get_route_for_supply_and_demand(
        self,
        supply_id: str,
        demand_id: str,
        vehicle_type: str = "mini_truck",
    ):
        """
        Generate logistics information between a supply location
        and the buyer destination location.

        Supply location is represented by the farmer entity.
        Demand destination is represented by the buyer entity.
        """

        supply = self.get_supply(supply_id)
        demand = self.get_demand(demand_id)

        route = self.location_service.estimate_route(
            origin_entity_type="farmer",
            origin_entity_id=supply.farmer_id,
            destination_entity_type="buyer",
            destination_entity_id=demand.buyer_id,
            vehicle_type=vehicle_type,
        )

        return route

    # ------------------------------------------------------------------
    # AI MATCHING ACCESS
    # ------------------------------------------------------------------

    def get_matching_candidates(
        self,
        crop: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Return structured supply and demand candidates for the
        AI matching engine.

        This method intentionally does not perform AI scoring.
        Preethesh's intelligence layer remains responsible for
        matching and ranking.
        """

        supplies = self.get_available_supply(crop)
        demands = self.get_open_demands(crop)

        return {
            "supplies": [self._supply_to_dict(item) for item in supplies],
            "demands": [self._demand_to_dict(item) for item in demands],
            "supply_count": len(supplies),
            "demand_count": len(demands),
        }

    # ------------------------------------------------------------------
    # OPTIMIZATION ACCESS
    # ------------------------------------------------------------------

    def get_optimization_input(
        self,
        crop: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Return marketplace information required by the optimization
        layer.

        Pavan's optimization logic can use this as its structured
        input boundary.
        """

        supplies = self.get_available_supply(crop)
        demands = self.get_open_demands(crop)

        supply_data = []

        for supply in supplies:
            location = self.get_entity_location(
                "farmer",
                supply.farmer_id,
            )

            supply_data.append(
                {
                    "supply": self._supply_to_dict(supply),
                    "farmer_location": (
                        self._location_to_dict(location)
                        if location is not None
                        else None
                    ),
                }
            )

        demand_data = []

        for demand in demands:
            location = self.get_entity_location(
                "buyer",
                demand.buyer_id,
            )

            demand_data.append(
                {
                    "demand": self._demand_to_dict(demand),
                    "buyer_location": (
                        self._location_to_dict(location)
                        if location is not None
                        else None
                    ),
                }
            )

        return {
            "supplies": supply_data,
            "demands": demand_data,
            "supply_count": len(supplies),
            "demand_count": len(demands),
        }

    # ------------------------------------------------------------------
    # VERIFICATION ACCESS
    # ------------------------------------------------------------------

    def get_verification_snapshot(self) -> Dict[str, Any]:
        """
        Return the current marketplace state required by the
        verification layer.

        Mugil can use this to verify that downstream decisions are
        based on the latest marketplace records.
        """

        supplies = self.marketplace.supplies.list_all()
        demands = self.marketplace.demands.list_all()
        orders = self.marketplace.orders.list_all()

        return {
            "supplies": [
                self._supply_to_dict(supply)
                for supply in supplies
            ],
            "demands": [
                self._demand_to_dict(demand)
                for demand in demands
            ],
            "orders": [
                self._order_to_dict(order)
                for order in orders
            ],
            "supply_count": len(supplies),
            "demand_count": len(demands),
            "order_count": len(orders),
        }

    # ------------------------------------------------------------------
    # FULL MARKETPLACE STATE
    # ------------------------------------------------------------------

    def get_marketplace_snapshot(self) -> Dict[str, Any]:
        """
        Return a complete current-state snapshot.

        This is the primary read interface for other AGRIWEAVE
        modules that need a consistent view of the marketplace.
        """

        farmers = self.marketplace.farmers.list_all()
        buyers = self.marketplace.buyers.list_all()
        supplies = self.marketplace.supplies.list_all()
        demands = self.marketplace.demands.list_all()
        orders = self.marketplace.orders.list_all()

        return {
            "farmers": [
                self._farmer_to_dict(farmer)
                for farmer in farmers
            ],
            "buyers": [
                self._buyer_to_dict(buyer)
                for buyer in buyers
            ],
            "supplies": [
                self._supply_to_dict(supply)
                for supply in supplies
            ],
            "demands": [
                self._demand_to_dict(demand)
                for demand in demands
            ],
            "orders": [
                self._order_to_dict(order)
                for order in orders
            ],
            "counts": {
                "farmers": len(farmers),
                "buyers": len(buyers),
                "supplies": len(supplies),
                "demands": len(demands),
                "orders": len(orders),
            },
        }

    # ------------------------------------------------------------------
    # SERIALIZATION HELPERS
    # ------------------------------------------------------------------

    @staticmethod
    def _farmer_to_dict(farmer) -> Dict[str, Any]:
        return {
            "id": farmer.id,
            "name": farmer.name,
            "location": farmer.location,
            "phone": farmer.phone,
            "reliability_score": farmer.reliability_score,
        }

    @staticmethod
    def _buyer_to_dict(buyer) -> Dict[str, Any]:
        return {
            "id": buyer.id,
            "name": buyer.name,
            "location": buyer.location,
            "phone": buyer.phone,
            "reliability_score": buyer.reliability_score,
        }

    @staticmethod
    def _supply_to_dict(supply: Supply) -> Dict[str, Any]:
        return {
            "id": supply.id,
            "farmer_id": supply.farmer_id,
            "crop": supply.crop,
            "quantity_kg": supply.quantity_kg,
            "location": supply.location,
            "available_from": supply.available_from,
            "available_until": supply.available_until,
            "quality": supply.quality,
            "expected_price_per_kg": supply.expected_price_per_kg,
            "status": supply.status,
        }

    @staticmethod
    def _demand_to_dict(demand: Demand) -> Dict[str, Any]:
        return {
            "id": demand.id,
            "buyer_id": demand.buyer_id,
            "crop": demand.crop,
            "quantity_kg": demand.quantity_kg,
            "destination": demand.destination,
            "deadline": demand.deadline,
            "max_price_per_kg": demand.max_price_per_kg,
            "quality_required": demand.quality_required,
            "status": demand.status,
        }

    @staticmethod
    def _order_to_dict(order) -> Dict[str, Any]:
        return {
            "id": order.id,
            "demand_id": order.demand_id,
            "supply_ids": list(order.supply_ids),
            "quantity_kg": order.quantity_kg,
            "selling_price_per_kg": order.selling_price_per_kg,
            "transport_cost": order.transport_cost,
            "collection_cost": order.collection_cost,
            "packaging_cost": order.packaging_cost,
            "spoilage_cost": order.spoilage_cost,
            "platform_fee": order.platform_fee,
            "status": order.status,
        }

    @staticmethod
    def _location_to_dict(location) -> Optional[Dict[str, Any]]:
        if location is None:
            return None

        return {
            "entity_type": location.entity_type,
            "entity_id": location.entity_id,
            "latitude": location.latitude,
            "longitude": location.longitude,
            "address": location.address,
        }
    