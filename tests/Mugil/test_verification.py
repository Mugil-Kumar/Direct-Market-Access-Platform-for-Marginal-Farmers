import unittest

from shared.schemas.schemas import Supply, Demand

from Mugil.Verification_Robustness.supply_verification import verify_supply
from Mugil.Verification_Robustness.demand_verification import verify_demand
from Mugil.Verification_Robustness.constraint_verification import (
    verify_constraints,
)
from Mugil.Verification_Robustness.verifier import verify_match


class TestSupplyVerification(unittest.TestCase):

    def create_valid_supply(self):
        return Supply(
            id="SUP-001",
            farmer_id="FARM-001",
            crop="Tomato",
            quantity_kg=500.0,
            location="Udupi",
            available_from="2026-11-12T06:00:00",
            available_until="2026-11-13T18:00:00",
            quality="Grade A",
            expected_price_per_kg=32.0,
            status="available",
        )

    def test_valid_supply_is_verified(self):
        supply = self.create_valid_supply()
        result = verify_supply(supply)

        self.assertTrue(result["verified"])
        self.assertEqual(result["errors"], [])
        self.assertEqual(result["supply_id"], "SUP-001")

    def test_zero_quantity_is_rejected(self):
        supply = self.create_valid_supply()
        supply.quantity_kg = 0

        result = verify_supply(supply)

        self.assertFalse(result["verified"])
        self.assertTrue(
            any("quantity" in error.lower() for error in result["errors"])
        )

    def test_negative_price_is_rejected(self):
        supply = self.create_valid_supply()
        supply.expected_price_per_kg = -10

        result = verify_supply(supply)

        self.assertFalse(result["verified"])
        self.assertTrue(
            any("price" in error.lower() for error in result["errors"])
        )

    def test_invalid_availability_window_is_rejected(self):
        supply = self.create_valid_supply()
        supply.available_from = "2026-11-14T18:00:00"
        supply.available_until = "2026-11-13T06:00:00"

        result = verify_supply(supply)

        self.assertFalse(result["verified"])
        self.assertTrue(
            any("availability" in error.lower() for error in result["errors"])
        )

    def test_invalid_status_is_rejected(self):
        supply = self.create_valid_supply()
        supply.status = "fake_status"

        result = verify_supply(supply)

        self.assertFalse(result["verified"])
        self.assertTrue(
            any("status" in error.lower() for error in result["errors"])
        )

    def test_non_supply_input_is_rejected(self):
        result = verify_supply({"id": "SUP-001"})

        self.assertFalse(result["verified"])
        self.assertIn(
            "Input must be a Supply object.",
            result["errors"],
        )

    def test_non_available_supply_is_rejected(self):
        supply = self.create_valid_supply()
        supply.status = "reserved"

        result = verify_supply(supply)

        self.assertFalse(result["verified"])
        self.assertTrue(
            any("not available" in error.lower() for error in result["errors"])
        )

    def test_missing_location_is_rejected(self):
        supply = self.create_valid_supply()
        supply.location = ""

        result = verify_supply(supply)

        self.assertFalse(result["verified"])
        self.assertTrue(
            any("location" in error.lower() for error in result["errors"])
        )


class TestDemandVerification(unittest.TestCase):

    def create_valid_demand(self):
        return Demand(
            id="DEM-001",
            buyer_id="BUY-001",
            crop="Tomato",
            quantity_kg=500.0,
            destination="Mangaluru",
            deadline="2026-11-13T18:00:00",
            max_price_per_kg=35.0,
            quality_required="Grade A",
            status="open",
        )

    def test_valid_demand_is_verified(self):
        demand = self.create_valid_demand()
        result = verify_demand(demand)

        self.assertTrue(result["verified"])
        self.assertEqual(result["errors"], [])
        self.assertEqual(result["demand_id"], "DEM-001")

    def test_zero_demand_quantity_is_rejected(self):
        demand = self.create_valid_demand()
        demand.quantity_kg = 0

        result = verify_demand(demand)

        self.assertFalse(result["verified"])
        self.assertTrue(
            any("quantity" in error.lower() for error in result["errors"])
        )

    def test_missing_destination_is_rejected(self):
        demand = self.create_valid_demand()
        demand.destination = ""

        result = verify_demand(demand)

        self.assertFalse(result["verified"])
        self.assertTrue(
            any("destination" in error.lower() for error in result["errors"])
        )

    def test_invalid_deadline_is_rejected(self):
        demand = self.create_valid_demand()
        demand.deadline = "not-a-date"

        result = verify_demand(demand)

        self.assertFalse(result["verified"])
        self.assertTrue(
            any("deadline" in error.lower() for error in result["errors"])
        )

    def test_negative_max_price_is_rejected(self):
        demand = self.create_valid_demand()
        demand.max_price_per_kg = -5

        result = verify_demand(demand)

        self.assertFalse(result["verified"])
        self.assertTrue(
            any("price" in error.lower() for error in result["errors"])
        )

    def test_closed_demand_is_rejected(self):
        demand = self.create_valid_demand()
        demand.status = "matched"

        result = verify_demand(demand)

        self.assertFalse(result["verified"])
        self.assertTrue(
            any("not open" in error.lower() for error in result["errors"])
        )

    def test_non_demand_input_is_rejected(self):
        result = verify_demand({"id": "DEM-001"})

        self.assertFalse(result["verified"])
        self.assertIn(
            "Input must be a Demand object.",
            result["errors"],
        )


class TestConstraintVerification(unittest.TestCase):

    def create_valid_supply(self):
        return Supply(
            id="SUP-001",
            farmer_id="FARM-001",
            crop="Tomato",
            quantity_kg=600.0,
            location="Udupi",
            available_from="2026-11-12T06:00:00",
            available_until="2026-11-13T18:00:00",
            quality="Grade A",
            expected_price_per_kg=32.0,
            status="available",
        )

    def create_valid_demand(self):
        return Demand(
            id="DEM-001",
            buyer_id="BUY-001",
            crop="Tomato",
            quantity_kg=500.0,
            destination="Mangaluru",
            deadline="2026-11-13T12:00:00",
            max_price_per_kg=35.0,
            quality_required="Grade A",
            status="open",
        )

    def test_valid_supply_demand_pair_passes(self):
        result = verify_constraints(
            self.create_valid_supply(),
            self.create_valid_demand(),
        )

        self.assertTrue(result["verified"])
        self.assertEqual(result["errors"], [])
        self.assertEqual(result["details"]["shortfall_kg"], 0.0)

    def test_crop_mismatch_is_rejected(self):
        supply = self.create_valid_supply()
        demand = self.create_valid_demand()
        demand.crop = "Onion"

        result = verify_constraints(supply, demand)

        self.assertFalse(result["verified"])
        self.assertFalse(result["checks"]["crop_match"])

    def test_insufficient_quantity_is_rejected(self):
        supply = self.create_valid_supply()
        demand = self.create_valid_demand()
        supply.quantity_kg = 300.0

        result = verify_constraints(supply, demand)

        self.assertFalse(result["verified"])
        self.assertFalse(result["checks"]["quantity_constraint"])
        self.assertEqual(result["details"]["shortfall_kg"], 200.0)

    def test_price_above_buyer_limit_is_rejected(self):
        supply = self.create_valid_supply()
        demand = self.create_valid_demand()
        supply.expected_price_per_kg = 40.0

        result = verify_constraints(supply, demand)

        self.assertFalse(result["verified"])
        self.assertFalse(result["checks"]["price_constraint"])

    def test_quality_mismatch_is_rejected(self):
        supply = self.create_valid_supply()
        demand = self.create_valid_demand()
        demand.quality_required = "Grade A+"

        result = verify_constraints(supply, demand)

        self.assertFalse(result["verified"])
        self.assertFalse(result["checks"]["quality_constraint"])

    def test_deadline_constraint_is_rejected(self):
        supply = self.create_valid_supply()
        demand = self.create_valid_demand()
        supply.available_until = "2026-11-13T10:00:00"

        result = verify_constraints(supply, demand)

        self.assertFalse(result["verified"])
        self.assertFalse(result["checks"]["deadline_constraint"])

    def test_reserved_supply_is_rejected(self):
        supply = self.create_valid_supply()
        demand = self.create_valid_demand()
        supply.status = "reserved"

        result = verify_constraints(supply, demand)

        self.assertFalse(result["verified"])
        self.assertFalse(result["checks"]["supply_status"])

    def test_closed_demand_is_rejected(self):
        supply = self.create_valid_supply()
        demand = self.create_valid_demand()
        demand.status = "matched"

        result = verify_constraints(supply, demand)

        self.assertFalse(result["verified"])
        self.assertFalse(result["checks"]["demand_status"])

    def test_excess_supply_generates_warning(self):
        supply = self.create_valid_supply()
        demand = self.create_valid_demand()
        supply.quantity_kg = 800.0

        result = verify_constraints(supply, demand)

        self.assertTrue(result["verified"])
        self.assertTrue(result["warnings"])
        self.assertTrue(
            any("exceeds" in warning.lower() for warning in result["warnings"])
        )

    def test_invalid_input_types_are_rejected(self):
        result = verify_constraints(
            {"id": "SUP-001"},
            {"id": "DEM-001"},
        )

        self.assertFalse(result["verified"])
        self.assertEqual(len(result["errors"]), 2)


class TestMatchVerifier(unittest.TestCase):

    def create_valid_supply(self):
        return Supply(
            id="SUP-001",
            farmer_id="FARM-001",
            crop="Tomato",
            quantity_kg=600.0,
            location="Udupi",
            available_from="2026-11-12T06:00:00",
            available_until="2026-11-13T18:00:00",
            quality="Grade A",
            expected_price_per_kg=32.0,
            status="available",
        )

    def create_valid_demand(self):
        return Demand(
            id="DEM-001",
            buyer_id="BUY-001",
            crop="Tomato",
            quantity_kg=500.0,
            destination="Mangaluru",
            deadline="2026-11-13T12:00:00",
            max_price_per_kg=35.0,
            quality_required="Grade A",
            status="open",
        )

    def test_valid_match_is_verified(self):
        result = verify_match(
            self.create_valid_supply(),
            self.create_valid_demand(),
        )

        self.assertTrue(result["verified"])
        self.assertEqual(result["decision"], "VERIFIED")
        self.assertEqual(result["errors"], [])
        self.assertEqual(len(result["decision_trace"]), 4)

    def test_invalid_supply_rejects_match(self):
        supply = self.create_valid_supply()
        demand = self.create_valid_demand()

        supply.quantity_kg = 0

        result = verify_match(supply, demand)

        self.assertFalse(result["verified"])
        self.assertEqual(result["decision"], "REJECTED")
        self.assertFalse(result["supply_verification"]["verified"])

    def test_invalid_demand_rejects_match(self):
        supply = self.create_valid_supply()
        demand = self.create_valid_demand()

        demand.max_price_per_kg = -1

        result = verify_match(supply, demand)

        self.assertFalse(result["verified"])
        self.assertEqual(result["decision"], "REJECTED")
        self.assertFalse(result["demand_verification"]["verified"])

    def test_constraint_failure_rejects_match(self):
        supply = self.create_valid_supply()
        demand = self.create_valid_demand()

        supply.expected_price_per_kg = 50.0

        result = verify_match(supply, demand)

        self.assertFalse(result["verified"])
        self.assertEqual(result["decision"], "REJECTED")
        self.assertFalse(result["constraint_verification"]["verified"])

    def test_decision_trace_records_all_stages(self):
        result = verify_match(
            self.create_valid_supply(),
            self.create_valid_demand(),
        )

        stages = [
            item["stage"]
            for item in result["decision_trace"]
        ]

        self.assertEqual(
            stages,
            [
                "supply_verification",
                "demand_verification",
                "constraint_verification",
                "final_decision",
            ],
        )


if __name__ == "__main__":
    unittest.main()
