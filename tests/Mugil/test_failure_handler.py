import unittest

from Mugil.Verification_Robustness.failure_handler import (
    build_failure_response,
    validate_verification_result,
    safe_execute,
)


class TestFailureHandler(unittest.TestCase):

    def test_exception_creates_safe_rejection(self):
        result = build_failure_response(
            ValueError("Database unavailable"),
            stage="supply_verification",
        )

        self.assertFalse(result["verified"])
        self.assertEqual(result["decision"], "REJECTED")
        self.assertTrue(result["failure"])
        self.assertEqual(
            result["stage"],
            "supply_verification",
        )
        self.assertEqual(
            result["error_type"],
            "ValueError",
        )

    def test_string_error_is_supported(self):
        result = build_failure_response(
            "Invalid AI response",
            stage="ai_validation",
        )

        self.assertFalse(result["verified"])
        self.assertEqual(result["decision"], "REJECTED")
        self.assertEqual(
            result["error"],
            "Invalid AI response",
        )

    def test_valid_verification_result_is_accepted(self):
        result = validate_verification_result(
            {
                "verified": True,
                "errors": [],
            },
            stage="constraint_verification",
        )

        self.assertTrue(result["valid"])
        self.assertTrue(result["verified"])
        self.assertEqual(result["errors"], [])

    def test_non_dictionary_result_is_rejected(self):
        result = validate_verification_result(
            True,
            stage="constraint_verification",
        )

        self.assertFalse(result["valid"])
        self.assertFalse(result["verified"])
        self.assertEqual(
            result["decision"],
            "REJECTED",
        )

    def test_missing_required_field_is_rejected(self):
        result = validate_verification_result(
            {
                "verified": True,
            },
            stage="demand_verification",
        )

        self.assertFalse(result["valid"])
        self.assertFalse(result["verified"])
        self.assertIn(
            "missing required fields",
            result["error"].lower(),
        )

    def test_invalid_verified_type_is_rejected(self):
        result = validate_verification_result(
            {
                "verified": "yes",
                "errors": [],
            },
            stage="supply_verification",
        )

        self.assertFalse(result["valid"])
        self.assertFalse(result["verified"])

    def test_invalid_errors_type_is_rejected(self):
        result = validate_verification_result(
            {
                "verified": True,
                "errors": "none",
            },
            stage="supply_verification",
        )

        self.assertFalse(result["valid"])
        self.assertFalse(result["verified"])

    def test_safe_execute_success(self):
        def successful_operation():
            return {
                "verified": True,
                "errors": [],
            }

        result = safe_execute(
            successful_operation,
            stage="verification",
        )

        self.assertTrue(result["valid"])
        self.assertTrue(result["verified"])
        self.assertEqual(result["errors"], [])

    def test_safe_execute_rejects_failed_operation(self):
        def failed_operation():
            return {
                "verified": False,
                "errors": ["Price constraint failed."],
            }

        result = safe_execute(
            failed_operation,
            stage="verification",
        )

        self.assertTrue(result["valid"])
        self.assertFalse(result["verified"])
        self.assertEqual(
            result["result"]["errors"],
            ["Price constraint failed."],
        )

    def test_safe_execute_catches_exception(self):
        def crashing_operation():
            raise RuntimeError("Verification service crashed")

        result = safe_execute(
            crashing_operation,
            stage="verification",
        )

        self.assertFalse(result["verified"])
        self.assertEqual(
            result["decision"],
            "REJECTED",
        )
        self.assertTrue(result["failure"])
        self.assertEqual(
            result["error_type"],
            "RuntimeError",
        )

    def test_safe_execute_rejects_malformed_result(self):
        def malformed_operation():
            return {
                "verified": True
            }

        result = safe_execute(
            malformed_operation,
            stage="verification",
        )

        self.assertFalse(result["verified"])
        self.assertFalse(result["valid"])
        self.assertEqual(
            result["decision"],
            "REJECTED",
        )


if __name__ == "__main__":
    unittest.main()
