from collections import Counter
from typing import Any, Dict


class VerificationMetrics:
    """
    Tracks verification and recovery outcomes for AGRIWEAVE.

    This class stores operational metrics only.
    It does not make verification decisions.
    """

    def __init__(self) -> None:
        self.total_verifications = 0
        self.verified_matches = 0
        self.rejected_matches = 0

        self.total_recoveries = 0
        self.successful_recoveries = 0
        self.failed_recoveries = 0

        self.rejection_reasons = Counter()
        self.recovery_failure_reasons = Counter()

    def record_verification(
        self,
        result: Dict[str, Any],
    ) -> None:
        """Record one match-verification result."""

        self.total_verifications += 1

        if result.get("verified") is True:
            self.verified_matches += 1
        else:
            self.rejected_matches += 1

            for error in result.get("errors", []):
                self.rejection_reasons[str(error)] += 1

    def record_recovery(
        self,
        result: Dict[str, Any],
    ) -> None:
        """Record one supply-recovery verification result."""

        self.total_recoveries += 1

        if result.get("recovered") is True:
            self.successful_recoveries += 1
        else:
            self.failed_recoveries += 1

            for error in result.get("errors", []):
                self.recovery_failure_reasons[str(error)] += 1

    @staticmethod
    def _percentage(
        numerator: int,
        denominator: int,
    ) -> float:
        """Safely calculate a percentage."""

        if denominator == 0:
            return 0.0

        return round(
            (numerator / denominator) * 100,
            2,
        )

    @property
    def verification_success_rate(self) -> float:
        return self._percentage(
            self.verified_matches,
            self.total_verifications,
        )

    @property
    def recovery_success_rate(self) -> float:
        return self._percentage(
            self.successful_recoveries,
            self.total_recoveries,
        )

    def snapshot(self) -> Dict[str, Any]:
        """
        Return a dashboard-friendly snapshot of current metrics.
        """

        return {
            "verification": {
                "total": self.total_verifications,
                "verified": self.verified_matches,
                "rejected": self.rejected_matches,
                "success_rate_percent": self.verification_success_rate,
            },
            "recovery": {
                "total": self.total_recoveries,
                "successful": self.successful_recoveries,
                "failed": self.failed_recoveries,
                "success_rate_percent": self.recovery_success_rate,
            },
            "rejection_reasons": dict(
                self.rejection_reasons
            ),
            "recovery_failure_reasons": dict(
                self.recovery_failure_reasons
            ),
        }

    def reset(self) -> None:
        """Reset all metrics."""

        self.total_verifications = 0
        self.verified_matches = 0
        self.rejected_matches = 0

        self.total_recoveries = 0
        self.successful_recoveries = 0
        self.failed_recoveries = 0

        self.rejection_reasons.clear()
        self.recovery_failure_reasons.clear()
