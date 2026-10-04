import unittest

from Mugil.Verification_Robustness.metrics import (
    VerificationMetrics,
)


class TestVerificationMetrics(unittest.TestCase):

    def test_initial_metrics_are_zero(self):
        metrics = VerificationMetrics()

        snapshot = metrics.snapshot()

        self.assertEqual(
            snapshot["verification"]["total"],
            0,
        )
        self.assertEqual(
            snapshot["verification"]["verified"],
            0,
        )
        self.assertEqual(
            snapshot["verification"]["rejected"],
            0,
        )
        self.assertEqual(
            snapshot["recovery"]["total"],
            0,
        )

    def test_verified_match_is_recorded(self):
        metrics = VerificationMetrics()

        metrics.record_verification(
            {
                "verified": True,
                "errors": [],
            }
        )

        snapshot = metrics.snapshot()

        self.assertEqual(
            snapshot["verification"]["total"],
            1,
        )
        self.assertEqual(
            snapshot["verification"]["verified"],
            1,
        )
        self.assertEqual(
            snapshot["verification"]["rejected"],
            0,
        )
        self.assertEqual(
            snapshot["verification"]["success_rate_percent"],
            100.0,
        )

    def test_rejected_match_is_recorded(self):
        metrics = VerificationMetrics()

        metrics.record_verification(
            {
                "verified": False,
                "errors": [
                    "Price constraint failed."
                ],
            }
        )

        snapshot = metrics.snapshot()

        self.assertEqual(
            snapshot["verification"]["rejected"],
            1,
        )
        self.assertEqual(
            snapshot["verification"]["success_rate_percent"],
            0.0,
        )
        self.assertEqual(
            snapshot["rejection_reasons"][
                "Price constraint failed."
            ],
            1,
        )

    def test_multiple_verifications_calculate_rate(self):
        metrics = VerificationMetrics()

        metrics.record_verification(
            {
                "verified": True,
                "errors": [],
            }
        )

        metrics.record_verification(
            {
                "verified": True,
                "errors": [],
            }
        )

        metrics.record_verification(
            {
                "verified": False,
                "errors": [
                    "Quantity constraint failed."
                ],
            }
        )

        metrics.record_verification(
            {
                "verified": False,
                "errors": [
                    "Crop mismatch."
                ],
            }
        )

        snapshot = metrics.snapshot()

        self.assertEqual(
            snapshot["verification"]["total"],
            4,
        )
        self.assertEqual(
            snapshot["verification"]["verified"],
            2,
        )
        self.assertEqual(
            snapshot["verification"]["rejected"],
            2,
        )
        self.assertEqual(
            snapshot["verification"]["success_rate_percent"],
            50.0,
        )

    def test_successful_recovery_is_recorded(self):
        metrics = VerificationMetrics()

        metrics.record_recovery(
            {
                "recovered": True,
                "errors": [],
            }
        )

        snapshot = metrics.snapshot()

        self.assertEqual(
            snapshot["recovery"]["total"],
            1,
        )
        self.assertEqual(
            snapshot["recovery"]["successful"],
            1,
        )
        self.assertEqual(
            snapshot["recovery"]["failed"],
            0,
        )
        self.assertEqual(
            snapshot["recovery"]["success_rate_percent"],
            100.0,
        )

    def test_failed_recovery_is_recorded(self):
        metrics = VerificationMetrics()

        metrics.record_recovery(
            {
                "recovered": False,
                "errors": [
                    "Replacement quantity insufficient."
                ],
            }
        )

        snapshot = metrics.snapshot()

        self.assertEqual(
            snapshot["recovery"]["failed"],
            1,
        )
        self.assertEqual(
            snapshot["recovery"]["success_rate_percent"],
            0.0,
        )
        self.assertEqual(
            snapshot["recovery_failure_reasons"][
                "Replacement quantity insufficient."
            ],
            1,
        )

    def test_multiple_recoveries_calculate_rate(self):
        metrics = VerificationMetrics()

        metrics.record_recovery(
            {
                "recovered": True,
                "errors": [],
            }
        )

        metrics.record_recovery(
            {
                "recovered": True,
                "errors": [],
            }
        )

        metrics.record_recovery(
            {
                "recovered": False,
                "errors": [
                    "Deadline constraint failed."
                ],
            }
        )

        snapshot = metrics.snapshot()

        self.assertEqual(
            snapshot["recovery"]["total"],
            3,
        )
        self.assertEqual(
            snapshot["recovery"]["successful"],
            2,
        )
        self.assertEqual(
            snapshot["recovery"]["failed"],
            1,
        )
        self.assertEqual(
            snapshot["recovery"]["success_rate_percent"],
            66.67,
        )

    def test_repeated_failure_reasons_are_counted(self):
        metrics = VerificationMetrics()

        for _ in range(3):
            metrics.record_verification(
                {
                    "verified": False,
                    "errors": [
                        "Price constraint failed."
                    ],
                }
            )

        snapshot = metrics.snapshot()

        self.assertEqual(
            snapshot["rejection_reasons"][
                "Price constraint failed."
            ],
            3,
        )

    def test_empty_denominator_returns_zero_percent(self):
        metrics = VerificationMetrics()

        self.assertEqual(
            metrics.verification_success_rate,
            0.0,
        )
        self.assertEqual(
            metrics.recovery_success_rate,
            0.0,
        )

    def test_reset_clears_all_metrics(self):
        metrics = VerificationMetrics()

        metrics.record_verification(
            {
                "verified": True,
                "errors": [],
            }
        )

        metrics.record_recovery(
            {
                "recovered": True,
                "errors": [],
            }
        )

        metrics.reset()

        snapshot = metrics.snapshot()

        self.assertEqual(
            snapshot["verification"]["total"],
            0,
        )
        self.assertEqual(
            snapshot["verification"]["verified"],
            0,
        )
        self.assertEqual(
            snapshot["recovery"]["total"],
            0,
        )
        self.assertEqual(
            snapshot["recovery"]["successful"],
            0,
        )
        self.assertEqual(
            snapshot["rejection_reasons"],
            {},
        )
        self.assertEqual(
            snapshot["recovery_failure_reasons"],
            {},
        )


if __name__ == "__main__":
    unittest.main()
