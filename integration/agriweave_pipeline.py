"""
AGRIWEAVE Central Integration Pipeline

Flow:
    Disha Marketplace
        -> Preethesh AI Market Intelligence
        -> Pavan Aggregation
        -> Pavan Quantity Optimization
        -> Mugil Verification
        -> Disha Order Creation

AI provides recommendations and explanations.
Optimization determines the actual allocation.
Verification independently approves/rejects the allocation.
Marketplace commits only after verification.
"""

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional

from shared.schemas.schemas import Demand, Order, Supply

from Disha.Marketplace_Data_Logistics.api import MarketplaceService
from Disha.Marketplace_Data_Logistics.marketplace_gateway import MarketplaceGateway

from Preethesh.AI_Market_Intelligence.matching_engine import (
    get_best_candidate,
    rank_candidates,
)

from Preethesh.AI_Market_Intelligence.collective_matcher import (
    get_best_collective_match,
    find_collective_matches,
)

from Preethesh.AI_Market_Intelligence.ai_pipeline import (
    run_ai_matching as run_preethesh_ai,
)

from Preethesh.AI_Market_Intelligence.recommendation_engine import (
    build_recommendation,
)

from Preethesh.AI_Market_Intelligence.explanation import (
    explain_recommendation,
)

from Preethesh.AI_Market_Intelligence.market_gap import (
    analyze_market_gap,
)

from Pavan.Aggregation_Optimization_Supply_Rescue.aggregation import (
    aggregate_supplies,
)

from Pavan.Aggregation_Optimization_Supply_Rescue.quantity_optimizer import (
    optimize_quantities,
)

from Mugil.Verification_Robustness.verifier import verify_match


@dataclass
class PipelineResult:
    """Structured result returned by the AGRIWEAVE pipeline."""

    success: bool = False
    stage: str = "not_started"
    message: str = ""

    demand_id: Optional[str] = None
    supply_ids: List[str] = field(default_factory=list)

    matched_quantity_kg: float = 0.0
    optimized_quantity_kg: float = 0.0

    ai_match: Optional[Any] = None
    collective_match: Optional[Any] = None

    ranked_candidates: List[Any] = field(default_factory=list)
    collective_candidates: List[Any] = field(default_factory=list)

    # New Preethesh AI integration
    ai_pipeline_result: Optional[Any] = None
    recommendation: Optional[Any] = None
    ai_explanation: str = ""
    market_gaps: List[Any] = field(default_factory=list)

    aggregation: List[Any] = field(default_factory=list)
    optimization: Optional[Any] = None

    verification: Optional[Dict[str, Any]] = None
    order: Optional[Order] = None

    dry_run: bool = True

    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    trace: List[str] = field(default_factory=list)


class AgriweavePipeline:
    """
    Central coordinator for the complete AGRIWEAVE workflow.

    AI proposes.
    Optimization allocates.
    Verification approves/rejects.
    Marketplace commits only after verification.
    """

    def __init__(
        self,
        marketplace: Optional[MarketplaceService] = None,
        *,
        dry_run: bool = True,
    ) -> None:
        self.marketplace = marketplace or MarketplaceService()
        self.gateway = MarketplaceGateway(self.marketplace)
        self.dry_run = dry_run

    # ------------------------------------------------------------------
    # VALIDATION
    # ------------------------------------------------------------------

    @staticmethod
    def _validate_demand(demand: Demand) -> None:
        """Validate the minimum demand contract."""

        if not isinstance(demand, Demand):
            raise TypeError("demand must be a Demand instance.")

        if not str(demand.id).strip():
            raise ValueError("Demand ID is required.")

        if not str(demand.buyer_id).strip():
            raise ValueError("Buyer ID is required.")

        if not str(demand.crop).strip():
            raise ValueError("Demand crop is required.")

        try:
            quantity = float(demand.quantity_kg)
        except (TypeError, ValueError) as exc:
            raise ValueError("Demand quantity must be numeric.") from exc

        if quantity <= 0:
            raise ValueError("Demand quantity must be greater than zero.")

        if not str(demand.destination).strip():
            raise ValueError("Demand destination is required.")

        if not str(demand.deadline).strip():
            raise ValueError("Demand deadline is required.")

        try:
            max_price = float(demand.max_price_per_kg)
        except (TypeError, ValueError) as exc:
            raise ValueError("Demand maximum price must be numeric.") from exc

        if max_price <= 0:
            raise ValueError(
                "Demand maximum price must be greater than zero."
            )

        if not str(demand.quality_required).strip():
            raise ValueError("Demand quality requirement is required.")

        if str(demand.status).strip().lower() != "open":
            raise ValueError(
                f"Demand {demand.id} is not open for matching."
            )

    # ------------------------------------------------------------------
    # MARKETPLACE INPUT
    # ------------------------------------------------------------------

    def get_market_data(
        self,
        crop: Optional[str] = None,
    ) -> Dict[str, List[Any]]:
        """Retrieve currently available supplies and open demands."""

        supplies = self.gateway.get_available_supply(crop=crop)
        demands = self.gateway.get_open_demands(crop=crop)

        return {
            "supplies": supplies,
            "demands": demands,
        }

    # ------------------------------------------------------------------
    # PREETHESH AI ENRICHMENT
    # ------------------------------------------------------------------

    @staticmethod
    def _supply_to_ai_dict(supply: Supply) -> Dict[str, Any]:
        """Convert shared Supply into the AI pipeline dictionary contract."""

        data = asdict(supply)

        # Keep both common identifier names available.
        data["supply_id"] = supply.id

        return data

    @staticmethod
    def _demand_to_ai_dict(demand: Demand) -> Dict[str, Any]:
        """Convert shared Demand into the AI pipeline dictionary contract."""

        data = asdict(demand)

        # Keep both common identifier names available.
        data["demand_id"] = demand.id

        return data

    def run_enriched_ai(
        self,
        demand: Demand,
        supplies: List[Supply],
        legacy_ai_result: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Run Preethesh's richer AI pipeline.

        This is an enrichment layer:
        failure here does not replace the already-working legacy matcher.
        """

        ai_supplies = [
            self._supply_to_ai_dict(supply)
            for supply in supplies
        ]

        ai_demand = self._demand_to_ai_dict(demand)

        try:
            ai_result = run_preethesh_ai(
                supplies=ai_supplies,
                demand=ai_demand,
            )

            individual_match = getattr(
                ai_result,
                "best_individual_match",
                None,
            )

            collective_match = getattr(
                ai_result,
                "best_collective_match",
                None,
            )

            recommendation = build_recommendation(
                demand_id=demand.id,
                individual_match=individual_match,
                collective_match=collective_match,
                alternatives=getattr(
                    ai_result,
                    "eligible_candidates",
                    [],
                ),
                recommended_quantity_kg=demand.quantity_kg,
                required_quantity_kg=demand.quantity_kg,
            )

            candidate_score = None

            if individual_match is not None:
                candidate_score = getattr(
                    individual_match,
                    "score",
                    None,
                )

            explanation = explain_recommendation(
                recommendation=recommendation,
                candidate_score=candidate_score,
            )

            market_gaps = analyze_market_gap(
                demands=[demand],
                supplies=supplies,
                location=demand.destination,
            )

            return {
                "result": ai_result,
                "recommendation": recommendation,
                "explanation": explanation,
                "market_gaps": market_gaps,
                "warnings": list(
                    getattr(
                        ai_result,
                        "warnings",
                        [],
                    )
                    or []
                ),
            }

        except Exception as exc:
            # The richer AI layer must never disable the proven
            # legacy matching path.
            legacy_ai_result.setdefault("enrichment_warnings", []).append(
                (
                    "Preethesh enriched AI layer was unavailable: "
                    f"{type(exc).__name__}: {exc}"
                )
            )

            return {
                "result": None,
                "recommendation": None,
                "explanation": "",
                "market_gaps": [],
                "warnings": [
                    (
                        "Enriched AI information was unavailable; "
                        "legacy matching remained active."
                    )
                ],
            }

    # ------------------------------------------------------------------
    # AI MATCHING
    # ------------------------------------------------------------------

    def run_ai_matching(
        self,
        demand: Demand,
        supplies: List[Supply],
    ) -> Dict[str, Any]:
        """Run legacy matching plus the new enriched AI intelligence."""

        self._validate_demand(demand)

        if not supplies:
            raise ValueError("No available supplies for AI matching.")

        # Existing proven matching path.
        ranked_candidates = rank_candidates(
            supplies=supplies,
            demand=demand,
        )

        best_candidate = get_best_candidate(
            supplies=supplies,
            demand=demand,
        )

        collective_candidates = find_collective_matches(
            demand=demand,
            supplies=supplies,
        )

        best_collective = get_best_collective_match(
            demand=demand,
            supplies=supplies,
        )

        result = {
            "ranked_candidates": ranked_candidates,
            "best_candidate": best_candidate,
            "collective_candidates": collective_candidates,
            "best_collective": best_collective,
        }

        # New Preethesh intelligence layer.
        enriched = self.run_enriched_ai(
            demand=demand,
            supplies=supplies,
            legacy_ai_result=result,
        )

        result["ai_pipeline_result"] = enriched["result"]
        result["recommendation"] = enriched["recommendation"]
        result["explanation"] = enriched["explanation"]
        result["market_gaps"] = enriched["market_gaps"]
        result["enrichment_warnings"] = enriched["warnings"]

        return result

    # ------------------------------------------------------------------
    # SUPPLY SELECTION
    # ------------------------------------------------------------------

    def select_supply_set(
        self,
        demand: Demand,
        supplies: List[Supply],
        ai_result: Dict[str, Any],
    ) -> List[Supply]:
        """
        Select supplies for aggregation and optimization.

        Legacy collective matching remains the authoritative selection
        path for compatibility with the already-tested pipeline.
        """

        best_collective = ai_result.get("best_collective")

        if best_collective is not None:
            selected_ids = set(
                getattr(best_collective, "supply_ids", []) or []
            )

            selected = [
                supply
                for supply in supplies
                if supply.id in selected_ids
            ]

            if selected:
                return selected

        # If enriched AI produced a recommendation, use it only as a
        # fallback when legacy matching did not select anything.
        recommendation = ai_result.get("recommendation")

        if recommendation is not None:
            recommended_ids = set(
                getattr(
                    recommendation,
                    "recommended_supply_ids",
                    [],
                )
                or []
            )

            selected = [
                supply
                for supply in supplies
                if supply.id in recommended_ids
            ]

            if selected:
                return selected

        best_candidate = ai_result.get("best_candidate")

        if best_candidate is not None:
            supply_id = getattr(best_candidate, "supply_id", None)

            if supply_id:
                selected = [
                    supply
                    for supply in supplies
                    if supply.id == supply_id
                ]

                if selected:
                    return selected

        return []

    # ------------------------------------------------------------------
    # PAVAN AGGREGATION
    # ------------------------------------------------------------------

    def run_aggregation(
        self,
        demand: Demand,
        supplies: List[Supply],
    ) -> List[Any]:
        """Aggregate selected farmer supplies."""

        if not supplies:
            raise ValueError(
                "Cannot aggregate because no supplies were selected."
            )

        groups = aggregate_supplies(
            supplies,
            target_quantity_kg=demand.quantity_kg,
        )

        return list(groups)

    # ------------------------------------------------------------------
    # PAVAN OPTIMIZATION
    # ------------------------------------------------------------------

    def run_optimization(
        self,
        demand: Demand,
        supplies: List[Supply],
    ) -> Any:
        """Optimize the quantity allocation."""

        if not supplies:
            raise ValueError(
                "Cannot optimize because no supplies were selected."
            )

        return optimize_quantities(
            supplies=supplies,
            requested_quantity_kg=demand.quantity_kg,
        )

    # ------------------------------------------------------------------
    # ALLOCATION HELPERS
    # ------------------------------------------------------------------

    @staticmethod
    def _get_allocation_quantity(allocation: Any) -> float:
        """Extract allocated quantity from an optimizer allocation."""

        possible_fields = (
            "allocated_quantity_kg",
            "quantity_kg",
            "allocated_kg",
            "quantity",
        )

        for field_name in possible_fields:
            value = getattr(allocation, field_name, None)

            if value is None:
                continue

            try:
                quantity = float(value)
            except (TypeError, ValueError):
                continue

            if quantity > 0:
                return quantity

        return 0.0

    @staticmethod
    def _get_allocation_supply_id(
        allocation: Any,
    ) -> Optional[str]:
        """Extract supply ID from an optimizer allocation."""

        supply_id = getattr(
            allocation,
            "supply_id",
            None,
        )

        if supply_id is None:
            return None

        supply_id = str(supply_id).strip()

        return supply_id or None

    def _build_allocation_map(
        self,
        optimization: Any,
        supplies: List[Supply],
    ) -> Dict[str, float]:
        """Build supply_id -> positive allocated quantity."""

        allocations = getattr(
            optimization,
            "allocations",
            [],
        ) or {}

        allocation_map: Dict[str, float] = {}

        if isinstance(allocations, dict):
            for supply_id, value in allocations.items():
                try:
                    quantity = float(value)
                except (TypeError, ValueError):
                    continue

                if quantity > 0:
                    allocation_map[str(supply_id)] = quantity

            return allocation_map

        for allocation in allocations:
            supply_id = self._get_allocation_supply_id(
                allocation
            )

            if not supply_id:
                continue

            quantity = self._get_allocation_quantity(
                allocation
            )

            if quantity > 0:
                allocation_map[supply_id] = quantity

        # Defensive fallback.
        if not allocation_map:
            remaining = float(
                getattr(
                    optimization,
                    "allocated_quantity_kg",
                    0.0,
                )
            )

            if remaining > 0:
                for supply in supplies:
                    available = float(
                        supply.quantity_kg
                    )

                    if available <= 0:
                        continue

                    allocated = min(
                        available,
                        remaining,
                    )

                    if allocated > 0:
                        allocation_map[
                            supply.id
                        ] = allocated

                        remaining -= allocated

                    if remaining <= 0:
                        break

        return allocation_map

    # ------------------------------------------------------------------
    # ORDER PROPOSAL
    # ------------------------------------------------------------------

    def build_order(
        self,
        demand: Demand,
        supplies: List[Supply],
        optimization: Any,
    ) -> Order:
        """Convert optimization output into an order proposal."""

        allocation_map = self._build_allocation_map(
            optimization=optimization,
            supplies=supplies,
        )

        supply_ids = [
            supply.id
            for supply in supplies
            if (
                supply.id in allocation_map
                and allocation_map[supply.id] > 0
            )
        ]

        if not supply_ids:
            supply_ids = [
                supply.id
                for supply in supplies
            ]

        allocated_quantity = float(
            getattr(
                optimization,
                "allocated_quantity_kg",
                0.0,
            )
        )

        weighted_price = float(
            getattr(
                optimization,
                "weighted_price_per_kg",
                0.0,
            )
        )

        if allocated_quantity <= 0:
            raise ValueError(
                "Optimization produced zero allocatable quantity."
            )

        if weighted_price <= 0:
            raise ValueError(
                "Optimization produced an invalid selling price."
            )

        return Order(
            id=f"ORD-{demand.id}",
            demand_id=demand.id,
            supply_ids=supply_ids,
            quantity_kg=allocated_quantity,
            selling_price_per_kg=weighted_price,
            transport_cost=0.0,
            collection_cost=0.0,
            packaging_cost=0.0,
            spoilage_cost=0.0,
            platform_fee=0.0,
            status="pending",
        )

    # ------------------------------------------------------------------
    # MUGIL VERIFICATION
    # ------------------------------------------------------------------

    def verify_order(
        self,
        order: Order,
        demand: Demand,
        supplies: List[Supply],
        optimization: Any,
    ) -> Dict[str, Any]:
        """
        Independently verify each allocated supply.

        Fragmented supply is verified against its own allocation slice,
        not against the entire buyer demand.
        """

        allocation_map = self._build_allocation_map(
            optimization=optimization,
            supplies=supplies,
        )

        if not allocation_map:
            return {
                "verified": False,
                "decision": "REJECTED",
                "summary": (
                    "Verification rejected: no positive "
                    "allocations were produced."
                ),
                "order_id": order.id,
                "results": [],
                "errors": [
                    "Optimization produced no verifiable allocations."
                ],
                "warnings": [],
            }

        verification_results: List[Dict[str, Any]] = []

        supply_by_id = {
            supply.id: supply
            for supply in supplies
        }

        total_verified_quantity = 0.0

        for supply_id, allocated_quantity in allocation_map.items():
            supply = supply_by_id.get(supply_id)

            if supply is None:
                return {
                    "verified": False,
                    "decision": "REJECTED",
                    "summary": (
                        "Order rejected because an optimization "
                        "allocation references an unknown supply."
                    ),
                    "order_id": order.id,
                    "results": verification_results,
                    "errors": [
                        (
                            "Unknown supply referenced by optimization: "
                            f"{supply_id}"
                        )
                    ],
                    "warnings": [],
                }

            if allocated_quantity > float(
                supply.quantity_kg
            ):
                return {
                    "verified": False,
                    "decision": "REJECTED",
                    "summary": (
                        "Order rejected because an allocation "
                        "exceeds available farmer supply."
                    ),
                    "order_id": order.id,
                    "results": verification_results,
                    "errors": [
                        (
                            f"Allocation for {supply_id} is "
                            f"{allocated_quantity:.2f} kg but supply "
                            f"only has "
                            f"{float(supply.quantity_kg):.2f} kg."
                        )
                    ],
                    "warnings": [],
                }

            demand_slice = Demand(
                id=f"{demand.id}-ALLOC-{supply_id}",
                buyer_id=demand.buyer_id,
                crop=demand.crop,
                quantity_kg=allocated_quantity,
                destination=demand.destination,
                deadline=demand.deadline,
                max_price_per_kg=demand.max_price_per_kg,
                quality_required=demand.quality_required,
                status="open",
            )

            verification = verify_match(
                supply=supply,
                demand=demand_slice,
            )

            verification_results.append(
                {
                    "supply_id": supply_id,
                    "allocated_quantity_kg": (
                        allocated_quantity
                    ),
                    "result": verification,
                }
            )

            if not verification.get(
                "verified",
                False,
            ):
                return {
                    "verified": False,
                    "decision": "REJECTED",
                    "summary": (
                        "Order rejected because an allocated "
                        "supply failed independent verification."
                    ),
                    "order_id": order.id,
                    "results": verification_results,
                    "errors": list(
                        verification.get(
                            "errors",
                            [],
                        )
                    ),
                    "warnings": list(
                        verification.get(
                            "warnings",
                            [],
                        )
                    ),
                }

            total_verified_quantity += (
                allocated_quantity
            )

        if (
            total_verified_quantity + 1e-9
            < float(order.quantity_kg)
        ):
            return {
                "verified": False,
                "decision": "REJECTED",
                "summary": (
                    "Order rejected because verified allocation "
                    "quantity does not cover the proposed order."
                ),
                "order_id": order.id,
                "results": verification_results,
                "errors": [
                    (
                        f"Verified "
                        f"{total_verified_quantity:.2f} kg but "
                        f"order requires "
                        f"{float(order.quantity_kg):.2f} kg."
                    )
                ],
                "warnings": [],
            }

        return {
            "verified": True,
            "decision": "VERIFIED",
            "summary": (
                "All allocated supplies passed independent "
                "verification and the verified quantity "
                "covers the order."
            ),
            "order_id": order.id,
            "verified_quantity_kg": (
                total_verified_quantity
            ),
            "results": verification_results,
            "errors": [],
            "warnings": [
                warning
                for item in verification_results
                for warning in item["result"].get(
                    "warnings",
                    [],
                )
            ],
        }

    # ------------------------------------------------------------------
    # MARKETPLACE COMMIT
    # ------------------------------------------------------------------

    def create_verified_order(
        self,
        order: Order,
        verification: Dict[str, Any],
    ) -> Order:
        """Create marketplace order only after verification."""

        if not verification.get(
            "verified",
            False,
        ):
            raise ValueError(
                "Order creation blocked: verification failed."
            )

        if self.dry_run:
            return order

        return self.marketplace.create_order(order)

    # ------------------------------------------------------------------
    # SUPPLY RESCUE / DISRUPTION RECOVERY
    # ------------------------------------------------------------------

    def run_supply_rescue(
        self,
        demand: Demand,
        order: Order,
        supplies: List[Supply],
        optimization: Any,
        failed_supply_id: str,
        replacement_supplies: Optional[List[Supply]] = None,
    ) -> Dict[str, Any]:
        """
        Recover a verified order after one allocated farmer supply fails.

        Architecture:
            Preethesh adaptive AI -> Pavan rescue selection -> Mugil
            independent recovery verification.

        The normal run() pipeline is intentionally left unchanged.
        This method is an explicit disruption/recovery workflow.
        """

        # Import at method level so the existing pipeline import surface
        # remains unchanged and the rescue feature stays isolated.
        from Preethesh.AI_Market_Intelligence.adaptive_matching import (
            adaptive_match,
        )
        from Pavan.Aggregation_Optimization_Supply_Rescue import rescue_supply
        from Mugil.Verification_Robustness.recovery_verification import (
            verify_recovery,
        )

        failed_supply_id = str(failed_supply_id).strip()

        if not failed_supply_id:
            raise ValueError("failed_supply_id cannot be empty.")

        supply_by_id = {
            supply.id: supply
            for supply in supplies
        }

        failed_supply = supply_by_id.get(failed_supply_id)

        if failed_supply is None:
            raise ValueError(
                f"Failed supply '{failed_supply_id}' was not found "
                "in the current order supply set."
            )

        allocation_map = self._build_allocation_map(
            optimization=optimization,
            supplies=supplies,
        )

        failed_allocated_quantity = float(
            allocation_map.get(failed_supply_id, 0.0)
        )

        if failed_allocated_quantity <= 0:
            raise ValueError(
                f"Failed supply '{failed_supply_id}' has no positive "
                "allocation in the current order."
            )

        original_order_quantity = float(order.quantity_kg)

        current_available_quantity = max(
            0.0,
            original_order_quantity - failed_allocated_quantity,
        )

        shortfall_quantity = max(
            0.0,
            original_order_quantity - current_available_quantity,
        )

        trace = [
            (
                f"Disruption: supply {failed_supply_id} failed with "
                f"{failed_allocated_quantity:.2f} kg allocated."
            ),
            (
                f"Recovery: {current_available_quantity:.2f} kg remains "
                f"committed; {shortfall_quantity:.2f} kg requires rescue."
            ),
        ]

        # --------------------------------------------------------------
        # 1. Build replacement candidate pool
        # --------------------------------------------------------------

        original_order_supply_ids = set(order.supply_ids or [])

        if replacement_supplies is None:
            marketplace_supplies = self.gateway.get_available_supply(
                crop=demand.crop
            )

            replacement_pool = [
                supply
                for supply in marketplace_supplies
                if supply.id not in original_order_supply_ids
                and supply.id != failed_supply_id
            ]
        else:
            replacement_pool = [
                supply
                for supply in replacement_supplies
                if supply.id not in original_order_supply_ids
                and supply.id != failed_supply_id
            ]

        trace.append(
            "Recovery: excluded failed and already-committed supplies "
            "from the replacement pool."
        )

        # --------------------------------------------------------------
        # 2. Adaptive AI rerouting
        # --------------------------------------------------------------

        ai_supplies = [
            self._supply_to_ai_dict(supply)
            for supply in replacement_pool
        ]

        ai_demand = self._demand_to_ai_dict(demand)

        adaptive_result = adaptive_match(
            supplies=ai_supplies,
            demand=ai_demand,
            unavailable_supply_ids={failed_supply_id},
        )

        trace.append(
            "AI: reran adaptive matching after the supply disruption."
        )

        # --------------------------------------------------------------
        # 3. Pavan rescue selection
        # --------------------------------------------------------------

        rescue_plan = rescue_supply(
            original_quantity_kg=original_order_quantity,
            current_available_quantity_kg=current_available_quantity,
            replacement_supplies=replacement_pool,
            crop=demand.crop,
            required_quality=demand.quality_required,
            max_price_per_kg=demand.max_price_per_kg,
        )

        trace.append(
            "Optimization: selected replacement supply candidates "
            "for the calculated shortfall."
        )

        # --------------------------------------------------------------
        # 4. Independently verify every selected replacement
        # --------------------------------------------------------------

        replacement_by_id = {
            supply.id: supply
            for supply in replacement_pool
        }

        recovery_results: List[Dict[str, Any]] = []
        verified_recovered_quantity = 0.0
        remaining_recovery_quantity = shortfall_quantity

        for replacement_id in rescue_plan.replacement_supply_ids:
            if remaining_recovery_quantity <= 1e-9:
                break

            replacement_supply = replacement_by_id.get(replacement_id)

            if replacement_supply is None:
                recovery_results.append(
                    {
                        "replacement_supply_id": replacement_id,
                        "recovered": False,
                        "decision": "RECOVERY_REJECTED",
                        "errors": [
                            "Rescue plan referenced an unknown "
                            "replacement supply."
                        ],
                        "warnings": [],
                    }
                )
                continue

            replacement_quantity = min(
                float(replacement_supply.quantity_kg),
                remaining_recovery_quantity,
            )

            # Recovery verification expects a demand slice matching the
            # quantity being assigned to this replacement.
            recovery_demand = Demand(
                id=f"{demand.id}-RECOVERY-{replacement_id}",
                buyer_id=demand.buyer_id,
                crop=demand.crop,
                quantity_kg=replacement_quantity,
                destination=demand.destination,
                deadline=demand.deadline,
                max_price_per_kg=demand.max_price_per_kg,
                quality_required=demand.quality_required,
                status="open",
            )

            verification = verify_recovery(
                replacement_supply=replacement_supply,
                demand=recovery_demand,
                failed_supply=failed_supply,
            )

            recovery_results.append(
                {
                    "replacement_supply_id": replacement_id,
                    "allocated_quantity_kg": replacement_quantity,
                    "recovered": bool(
                        verification.get("recovered", False)
                    ),
                    "verification": verification,
                }
            )

            if verification.get("recovered", False):
                verified_recovered_quantity += replacement_quantity
                remaining_recovery_quantity -= replacement_quantity

        recovery_verified = (
            verified_recovered_quantity + 1e-9
            >= shortfall_quantity
        )

        if recovery_verified:
            trace.append(
                "Verification: all replacement allocations passed "
                "independent recovery verification."
            )
        else:
            trace.append(
                "Verification: recovery could not fully cover the "
                "required shortfall."
            )

        recovery_ratio = (
            verified_recovered_quantity / shortfall_quantity
            if shortfall_quantity > 0
            else 1.0
        )

        if recovery_verified:
            summary = (
                f"Supply rescue recovered and independently verified "
                f"{verified_recovered_quantity:.2f} kg of the "
                f"{shortfall_quantity:.2f} kg shortfall."
            )
        else:
            summary = (
                f"Supply rescue verified only "
                f"{verified_recovered_quantity:.2f} kg of the "
                f"{shortfall_quantity:.2f} kg required shortfall."
            )

        return {
            "recovered": recovery_verified,
            "decision": (
                "RECOVERY_VERIFIED"
                if recovery_verified
                else "RECOVERY_REJECTED"
            ),
            "summary": summary,
            "failed_supply_id": failed_supply_id,
            "failed_allocated_quantity_kg": failed_allocated_quantity,
            "original_order_quantity_kg": original_order_quantity,
            "current_available_quantity_kg": current_available_quantity,
            "shortfall_quantity_kg": shortfall_quantity,
            "verified_recovered_quantity_kg": verified_recovered_quantity,
            "recovery_ratio": round(recovery_ratio, 4),
            "replacement_supply_ids": list(
                rescue_plan.replacement_supply_ids
            ),
            "replacement_pool_ids": [
                supply.id
                for supply in replacement_pool
            ],
            "adaptive_ai_result": adaptive_result,
            "rescue_plan": rescue_plan,
            "recovery_results": recovery_results,
            "trace": trace,
            "errors": [],
            "warnings": [],
        }

    # ------------------------------------------------------------------
    # COMPLETE PIPELINE
    # ------------------------------------------------------------------

    def run(
        self,
        demand: Demand,
    ) -> PipelineResult:
        """Execute the complete AGRIWEAVE decision pipeline."""

        result = PipelineResult(
            demand_id=demand.id,
            dry_run=self.dry_run,
        )

        try:
            # ----------------------------------------------------------
            # 1. MARKETPLACE DATA
            # ----------------------------------------------------------

            result.stage = "marketplace_input"

            result.trace.append(
                "Marketplace: retrieving available supplies "
                "and open demand."
            )

            self._validate_demand(demand)

            supplies = self.gateway.get_available_supply(
                crop=demand.crop
            )

            # Demo safety: emergency backup supplies are reserved for
            # disruption recovery and must not enter the initial order plan.
            # Real marketplace flows remain unchanged because this filter
            # only applies to explicitly tagged demo backup supplies.
            if self.dry_run:
                supplies = [
                    supply
                    for supply in supplies
                    if not (
                        str(supply.id).startswith("SUP-DEMO-")
                        and str(supply.id).endswith("004")
                    )
                ]

            if not supplies:
                result.message = (
                    "No available supply found for this crop."
                )
                result.errors.append(result.message)
                return result

            # ----------------------------------------------------------
            # 2. AI MATCHING
            # ----------------------------------------------------------

            result.stage = "ai_matching"

            result.trace.append(
                "AI: ranking individual and collective "
                "supply matches."
            )

            ai_result = self.run_ai_matching(
                demand=demand,
                supplies=supplies,
            )

            result.ai_match = ai_result.get(
                "best_candidate"
            )

            result.collective_match = ai_result.get(
                "best_collective"
            )

            result.ranked_candidates = ai_result.get(
                "ranked_candidates",
                [],
            )

            result.collective_candidates = ai_result.get(
                "collective_candidates",
                [],
            )

            result.ai_pipeline_result = ai_result.get(
                "ai_pipeline_result"
            )

            result.recommendation = ai_result.get(
                "recommendation"
            )

            result.ai_explanation = ai_result.get(
                "explanation",
                "",
            )

            result.market_gaps = ai_result.get(
                "market_gaps",
                [],
            )

            result.warnings.extend(
                ai_result.get(
                    "enrichment_warnings",
                    [],
                )
            )

            if result.recommendation is not None:
                result.trace.append(
                    "AI: generated explainable supply recommendation."
                )

            if result.market_gaps:
                result.trace.append(
                    "AI: calculated crop-level market gap intelligence."
                )

            selected_supplies = self.select_supply_set(
                demand=demand,
                supplies=supplies,
                ai_result=ai_result,
            )

            if not selected_supplies:
                result.message = (
                    "AI matching did not produce an eligible "
                    "supply set."
                )
                result.errors.append(result.message)
                return result

            result.supply_ids = [
                supply.id
                for supply in selected_supplies
            ]

            result.matched_quantity_kg = sum(
                float(supply.quantity_kg)
                for supply in selected_supplies
            )

            # ----------------------------------------------------------
            # 3. AGGREGATION
            # ----------------------------------------------------------

            result.stage = "aggregation"

            result.trace.append(
                "Optimization: aggregating fragmented farmer supply."
            )

            result.aggregation = self.run_aggregation(
                demand=demand,
                supplies=selected_supplies,
            )

            # ----------------------------------------------------------
            # 4. QUANTITY OPTIMIZATION
            # ----------------------------------------------------------

            result.stage = "quantity_optimization"

            result.trace.append(
                "Optimization: calculating feasible allocation."
            )

            result.optimization = self.run_optimization(
                demand=demand,
                supplies=selected_supplies,
            )

            optimization = result.optimization

            feasible = bool(
                getattr(
                    optimization,
                    "feasible",
                    False,
                )
            )

            if not feasible:
                reason = getattr(
                    optimization,
                    "reason",
                    "Optimization was not feasible.",
                )

                result.message = str(reason)
                result.errors.append(result.message)
                return result

            result.optimized_quantity_kg = float(
                getattr(
                    optimization,
                    "allocated_quantity_kg",
                    0.0,
                )
            )

            if result.optimized_quantity_kg <= 0:
                result.message = (
                    "Optimization returned zero quantity."
                )
                result.errors.append(result.message)
                return result

            # ----------------------------------------------------------
            # 5. BUILD ORDER
            # ----------------------------------------------------------

            result.stage = "order_proposal"

            result.trace.append(
                "Marketplace: building a proposed order."
            )

            order = self.build_order(
                demand=demand,
                supplies=selected_supplies,
                optimization=optimization,
            )

            # ----------------------------------------------------------
            # 6. VERIFICATION
            # ----------------------------------------------------------

            result.stage = "verification"

            result.trace.append(
                "Verification: independently checking "
                "each allocated supply."
            )

            verification = self.verify_order(
                order=order,
                demand=demand,
                supplies=selected_supplies,
                optimization=optimization,
            )

            result.verification = verification

            result.warnings.extend(
                verification.get(
                    "warnings",
                    [],
                )
            )

            if not verification.get(
                "verified",
                False,
            ):
                result.message = (
                    "Order rejected by independent verification."
                )

                result.errors.extend(
                    verification.get(
                        "errors",
                        [],
                    )
                )

                return result

            # ----------------------------------------------------------
            # 7. MARKETPLACE COMMIT
            # ----------------------------------------------------------

            result.stage = "order_creation"

            if self.dry_run:
                result.trace.append(
                    "Dry-run: verified order was NOT written "
                    "to marketplace."
                )
            else:
                result.trace.append(
                    "Marketplace: verification passed, "
                    "creating order."
                )

            created_order = self.create_verified_order(
                order=order,
                verification=verification,
            )

            result.order = created_order
            result.success = True

            result.stage = (
                "verified_dry_run"
                if self.dry_run
                else "completed"
            )

            result.message = (
                "AGRIWEAVE pipeline completed successfully."
            )

            return result

        except Exception as exc:
            # Fail closed.
            result.success = False
            result.stage = "failed"

            result.message = (
                "AGRIWEAVE pipeline failed safely."
            )

            result.errors.append(
                f"{type(exc).__name__}: {exc}"
            )

            result.trace.append(
                "Pipeline stopped safely after "
                "an unexpected failure."
            )

            return result


# ----------------------------------------------------------------------
# SIMPLE DEMO HELPERS
# ----------------------------------------------------------------------


def run_demo(
    demand: Demand,
    *,
    dry_run: bool = True,
) -> PipelineResult:
    """Convenience function for dashboard/tests."""

    pipeline = AgriweavePipeline(
        dry_run=dry_run,
    )

    return pipeline.run(demand)
