import unittest

from Mugil.Dashboard_Integration.app import (
    build_dashboard_state,
)

from Mugil.Verification_Robustness.metrics import (
    VerificationMetrics,
)


class TestDashboardIntegration(unittest.TestCase):

    def test_empty_dashboard_state(self):
        metrics = VerificationMetrics()

        state = build_dashboard_state(
            metrics=metrics,
        )

        self.assertEqual(
            state["match"]["decision"],
            "WAITING",
        )

        self.assertEqual(
            state["recovery"]["decision"],
            "NO RECOVERY",
        )

        self.assertEqual(
            state["metrics"]["verification"]["total"],
            0,
        )

    def test_verified_match_is_displayed(self):
        metrics = VerificationMetrics()

        verification_result = {
            "verified": True,
            "decision": "VERIFIED",
            "summary": "Match passed verification.",
            "errors": [],
            "warnings": [],
        }

        metrics.record_verification(
            verification_result
        )

        state = build_dashboard_state(
            verification_result=verification_result,
            metrics=metrics,
        )

        self.assertTrue(
            state["match"]["verified"]
        )

        self.assertEqual(
            state["match"]["decision"],
            "VERIFIED",
        )

        self.assertEqual(
            state["metrics"]["verification"]["verified"],
            1,
        )

    def test_rejected_match_is_displayed(self):
        metrics = VerificationMetrics()

        verification_result = {
            "verified": False,
            "decision": "REJECTED",
            "summary": "Match rejected.",
            "errors": [
                "Price constraint failed."
            ],
            "warnings": [],
        }

        metrics.record_verification(
            verification_result
        )

        state = build_dashboard_state(
            verification_result=verification_result,
            metrics=metrics,
        )

        self.assertFalse(
            state["match"]["verified"]
        )

        self.assertEqual(
            state["match"]["decision"],
            "REJECTED",
        )

        self.assertEqual(
            len(state["match"]["errors"]),
            1,
        )

    def test_recovery_success_is_displayed(self):
        metrics = VerificationMetrics()

        recovery_result = {
            "recovered": True,
            "decision": "RECOVERY_VERIFIED",
            "summary": "Replacement verified.",
            "errors": [],
        }

        metrics.record_recovery(
            recovery_result
        )

        state = build_dashboard_state(
            recovery_result=recovery_result,
            metrics=metrics,
        )

        self.assertTrue(
            state["recovery"]["recovered"]
        )

        self.assertEqual(
            state["recovery"]["decision"],
            "RECOVERY_VERIFIED",
        )

        self.assertEqual(
            state["metrics"]["recovery"]["successful"],
            1,
        )

    def test_recovery_failure_is_displayed(self):
        metrics = VerificationMetrics()

        recovery_result = {
            "recovered": False,
            "decision": "RECOVERY_REJECTED",
            "summary": "Replacement rejected.",
            "errors": [
                "Replacement quantity insufficient."
            ],
        }

        metrics.record_recovery(
            recovery_result
        )

        state = build_dashboard_state(
            recovery_result=recovery_result,
            metrics=metrics,
        )

        self.assertFalse(
            state["recovery"]["recovered"]
        )

        self.assertEqual(
            state["recovery"]["decision"],
            "RECOVERY_REJECTED",
        )

        self.assertEqual(
            state["metrics"]["recovery"]["failed"],
            1,
        )

    def test_dashboard_uses_metrics_snapshot(self):
        metrics = VerificationMetrics()

        for _ in range(4):
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

        state = build_dashboard_state(
            metrics=metrics,
        )

        self.assertEqual(
            state["metrics"]["verification"]["total"],
            5,
        )

        self.assertEqual(
            state["metrics"]["verification"]["verified"],
            4,
        )

        self.assertEqual(
            state["metrics"]["verification"]["rejected"],
            1,
        )

        self.assertEqual(
            state["metrics"]["verification"]["success_rate_percent"],
            80.0,
        )


if __name__ == "__main__":
    unittest.main()
