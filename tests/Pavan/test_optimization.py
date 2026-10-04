import unittest
from types import SimpleNamespace

from Pavan.Aggregation_Optimization_Supply_Rescue.aggregation import (
    AggregationConstraints,
    aggregate_supplies,
)
from Pavan.Aggregation_Optimization_Supply_Rescue.alternatives import rank_alternatives
from Pavan.Aggregation_Optimization_Supply_Rescue.collective_vs_individual import evaluate_collective_sale
from Pavan.Aggregation_Optimization_Supply_Rescue.net_realization import RealizationCosts, calculate_realization
from Pavan.Aggregation_Optimization_Supply_Rescue.quantity_optimizer import optimize_quantities
from Pavan.Aggregation_Optimization_Supply_Rescue.replanning import replan_after_disruption
from Pavan.Aggregation_Optimization_Supply_Rescue.shortfall import detect_shortfall
from Pavan.Aggregation_Optimization_Supply_Rescue.supply_rescue import rescue_supply


def supply(sid, farmer, crop="tomato", qty=10, price=20, quality="standard",
           distance=10, status="available"):
    return SimpleNamespace(
        id=sid, farmer_id=farmer, crop=crop, quantity_kg=qty,
        location="Mangaluru", available_from=None, available_until=None,
        quality=quality, expected_price_per_kg=price, status=status,
        distance_km=distance,
    )


class TestPavanOptimization(unittest.TestCase):
    def test_aggregation(self):
        items = [supply("S1", "F1", qty=20), supply("S2", "F2", qty=30)]
        groups = aggregate_supplies(
            items,
            AggregationConstraints(min_group_quantity_kg=40),
        )
        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0].total_quantity_kg, 50)

    def test_quantity_optimizer_full_fill(self):
        items = [
            supply("S1", "F1", qty=20, price=18),
            supply("S2", "F2", qty=30, price=19),
        ]
        result = optimize_quantities(items, 40)
        self.assertTrue(result.feasible)
        self.assertAlmostEqual(result.allocated_quantity_kg, 40)
        self.assertAlmostEqual(result.shortfall_kg, 0)

    def test_realization(self):
        result = calculate_realization(
            100, 30,
            RealizationCosts(
                transport_per_kg=1,
                collection_per_kg=0.5,
                packaging_per_kg=0.5,
                spoilage_percent=2,
                platform_fee_percent=2,
            ),
        )
        self.assertGreater(result.net_revenue, 0)
        self.assertAlmostEqual(result.gross_revenue, 3000)

    def test_collective_can_win(self):
        items = [supply("S1", "F1", qty=50, price=20), supply("S2", "F2", qty=50, price=20)]
        decision = evaluate_collective_sale(
            items,
            collective_price_per_kg=24,
            individual_costs=RealizationCosts(transport_per_kg=2),
            collective_costs=RealizationCosts(transport_per_kg=0.5),
        )
        self.assertEqual(decision.recommended_mode, "collective")
        self.assertGreater(decision.collective_gain, 0)

    def test_shortfall(self):
        report = detect_shortfall(100, [supply("S1", "F1", qty=30)])
        self.assertEqual(report.shortfall_kg, 70)
        self.assertTrue(report.critical)

    def test_rescue(self):
        replacements = [
            supply("R1", "F9", qty=30, price=21),
            supply("R2", "F8", qty=30, price=20),
        ]
        plan = rescue_supply(100, 50, replacements, crop="tomato")
        self.assertTrue(plan.recovered)
        self.assertAlmostEqual(plan.recovered_quantity_kg, 50)

    def test_replanning(self):
        items = [
            supply("S1", "F1", qty=50, price=20),
            supply("S2", "F2", qty=60, price=21),
        ]
        decision = replan_after_disruption(
            80,
            items,
            failed_supply_ids=["S1"],
        )
        self.assertEqual(decision.status, "infeasible")
        self.assertAlmostEqual(decision.replacement_quantity_kg, 60)

    def test_alternatives(self):
        items = [supply("A1", "F1", qty=100, price=20, distance=5)]
        result = rank_alternatives(items, crop="tomato", quantity_required_kg=50, top_k=3)
        self.assertEqual(result[0].supply_id, "A1")

    def test_incompatible_price_is_rejected(self):
        items = [supply("S1", "F1", qty=50, price=50)]
        result = optimize_quantities(items, 20)
        self.assertEqual(result.allocated_quantity_kg, 20)  # no price ceiling by default

        result = optimize_quantities(
            items, 20,
            constraints=__import__(
                "Pavan.Aggregation_Optimization_Supply_Rescue.quantity_optimizer",
                fromlist=["OptimizationConstraints"],
            ).OptimizationConstraints(max_price_per_kg=30),
        )
        self.assertFalse(result.feasible)
        self.assertEqual(result.allocated_quantity_kg, 0)

    def test_zero_quantity_is_safe(self):
        result = optimize_quantities([], 0)
        self.assertTrue(result.feasible)
        self.assertEqual(result.fill_ratio, 1.0)


if __name__ == "__main__":
    unittest.main()
