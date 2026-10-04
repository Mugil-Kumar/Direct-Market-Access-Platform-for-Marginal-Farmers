import unittest

from shared.schemas.schemas import Supply, Demand

from Mugil.Verification_Robustness.recovery_verification import (
    verify_recovery,
)


class TestRecoveryVerification(unittest.TestCase):

    def create_failed_supply(self):
        return Supply(
            id="SUP-FAILED",
            farmer_id="FARM-001",
            crop="Tomato",
            quantity_kg=500.0,
            location="Udupi",
            available_from="2026-11-12T06:00:00",
            available_until="2026-11-13T18:00:00",
            quality="Grade A",
            expected_price_per_kg=32.0,
            status="cancelled",
        )

    def create_replacement_supply(self):
        return Supply(
            id="SUP-REPLACEMENT",
            farmer_id="FARM-002",
            crop="Tomato",
            quantity_kg=600.0,
            location="Kundapura",
            available_from="2026-11-12T08:00:00",
            available_until="2026-11-13T18:00:00",
            quality="Grade A",
            expected_price_per_kg=33.0,
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

    def test_valid_recovery_is_verified(self):
        result = verify_recovery(
            self.create_replacement_supply(),
            self.create_valid_demand(),
            self.create_failed_supply(),
        )

        self.assertTrue(result["recovered"])
        self.assertEqual(
            result["decision"],
            "RECOVERY_VERIFIED",
        )
        self.assertEqual(result["errors"], [])

    def test_same_failed_supply_is_rejected(self):
        failed = self.create_failed_supply()
        demand = self.create_valid_demand()

        # Make the failed supply appear available to isolate
        # the replacement identity check.
        failed.status = "available"

        result = verify_recovery(
            failed,
            demand,
            failed,
        )

        self.assertFalse(result["recovered"])
        self.assertEqual(
            result["decision"],
            "RECOVERY_REJECTED",
        )
        self.assertTrue(
            any(
                "same supply" in error.lower()
                for error in result["errors"]
            )
        )

    def test_replacement_with_insufficient_quantity_is_rejected(self):
        replacement = self.create_replacement_supply()
        demand = self.create_valid_demand()

        replacement.quantity_kg = 300.0

        result = verify_recovery(
            replacement,
            demand,
            self.create_failed_supply(),
        )

        self.assertFalse(result["recovered"])
        self.assertFalse(
            result["verification"]["constraints"]["verified"]
        )

    def test_replacement_above_buyer_price_limit_is_rejected(self):
        replacement = self.create_replacement_supply()
        demand = self.create_valid_demand()

        replacement.expected_price_per_kg = 50.0

        result = verify_recovery(
            replacement,
            demand,
            self.create_failed_supply(),
        )

        self.assertFalse(result["recovered"])
        self.assertFalse(
            result["verification"]["constraints"]["verified"]
        )

    def test_replacement_with_wrong_crop_is_rejected(self):
        replacement = self.create_replacement_supply()
        demand = self.create_valid_demand()

        replacement.crop = "Onion"

        result = verify_recovery(
            replacement,
            demand,
            self.create_failed_supply(),
        )

        self.assertFalse(result["recovered"])
        self.assertFalse(
            result["verification"]["constraints"]["verified"]
        )

    def test_unavailable_replacement_is_rejected(self):
        replacement = self.create_replacement_supply()
        demand = self.create_valid_demand()

        replacement.status = "reserved"

        result = verify_recovery(
            replacement,
            demand,
            self.create_failed_supply(),
        )

        self.assertFalse(result["recovered"])
        self.assertFalse(
            result["verification"]["replacement_supply"]["verified"]
        )

    def test_invalid_demand_rejects_recovery(self):
        replacement = self.create_replacement_supply()
        demand = self.create_valid_demand()

        demand.quantity_kg = 0

        result = verify_recovery(
            replacement,
            demand,
            self.create_failed_supply(),
        )

        self.assertFalse(result["recovered"])
        self.assertFalse(
            result["verification"]["demand"]["verified"]
        )

    def test_invalid_replacement_type_is_rejected(self):
        result = verify_recovery(
            {"id": "SUP-REPLACEMENT"},
            self.create_valid_demand(),
            self.create_failed_supply(),
        )

        self.assertFalse(result["recovered"])
        self.assertEqual(
            result["decision"],
            "RECOVERY_REJECTED",
        )

    def test_decision_trace_contains_recovery_stages(self):
        result = verify_recovery(
            self.create_replacement_supply(),
            self.create_valid_demand(),
            self.create_failed_supply(),
        )

        stages = [
            item["stage"]
            for item in result["decision_trace"]
        ]

        self.assertEqual(
            stages,
            [
                "replacement_supply_verification",
                "demand_verification",
                "replacement_constraint_verification",
                "recovery_decision",
            ],
        )


if __name__ == "__main__":
    unittest.main()
