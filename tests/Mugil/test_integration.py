import unittest

from shared.schemas.schemas import Supply, Demand

from Mugil.Dashboard_Integration.integration import (
    build_verification_view,
    create_demo_demand,
    create_demo_supply,
    run_demo_verification,
    run_match_verification,
)


class TestDashboardIntegration(unittest.TestCase):

    def test_demo_supply_is_valid_schema(self):
        supply = create_demo_supply()

        self.assertIsInstance(supply, Supply)
        self.assertEqual(supply.id, "SUP-DEMO-001")
        self.assertEqual(supply.crop, "Tomato")
        self.assertEqual(supply.quantity_kg, 500.0)
        self.assertEqual(supply.status, "available")

    def test_demo_demand_is_valid_schema(self):
        demand = create_demo_demand()

        self.assertIsInstance(demand, Demand)
        self.assertEqual(demand.id, "DEM-DEMO-001")
        self.assertEqual(demand.crop, "Tomato")
        self.assertEqual(demand.quantity_kg, 500.0)
        self.assertEqual(demand.status, "open")

    def test_valid_match_reaches_verifier(self):
        supply = create_demo_supply()
        demand = create_demo_demand()

        result = run_match_verification(
            supply,
            demand,
        )

        self.assertIn(
            result["decision"],
            {"VERIFIED", "REJECTED"},
        )

        self.assertEqual(
            result["supply_id"],
            supply.id,
        )

        self.assertEqual(
            result["demand_id"],
            demand.id,
        )

        self.assertIn(
            "decision_trace",
            result,
        )

    def test_verification_view_has_required_fields(self):
        supply = create_demo_supply()
        demand = create_demo_demand()

        result = run_match_verification(
            supply,
            demand,
        )

        view = build_verification_view(result)

        required_fields = {
            "status",
            "decision",
            "summary",
            "supply_id",
            "demand_id",
            "errors",
            "warnings",
            "stages",
        }

        self.assertTrue(
            required_fields.issubset(view.keys())
        )

    def test_verification_view_preserves_decision(self):
        supply = create_demo_supply()
        demand = create_demo_demand()

        result = run_match_verification(
            supply,
            demand,
        )

        view = build_verification_view(result)

        self.assertEqual(
            view["decision"],
            result["decision"],
        )

        self.assertEqual(
            view["errors"],
            result["errors"],
        )

        self.assertEqual(
            view["warnings"],
            result["warnings"],
        )

    def test_decision_trace_is_preserved(self):
        result = run_demo_verification()

        self.assertGreaterEqual(
            len(result["stages"]),
            3,
        )

        stage_names = [
            stage["stage"]
            for stage in result["stages"]
        ]

        self.assertIn(
            "supply_verification",
            stage_names,
        )

        self.assertIn(
            "demand_verification",
            stage_names,
        )

        self.assertIn(
            "final_decision",
            stage_names,
        )

    def test_demo_verification_is_deterministic(self):
        first = run_demo_verification()
        second = run_demo_verification()

        self.assertEqual(
            first["status"],
            second["status"],
        )

        self.assertEqual(
            first["decision"],
            second["decision"],
        )

        self.assertEqual(
            first["supply_id"],
            second["supply_id"],
        )

        self.assertEqual(
            first["demand_id"],
            second["demand_id"],
        )


if __name__ == "__main__":
    unittest.main()
