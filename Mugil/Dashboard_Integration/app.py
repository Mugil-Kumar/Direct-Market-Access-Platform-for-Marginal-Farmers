import streamlit as st

from Mugil.Verification_Robustness.metrics import VerificationMetrics


st.set_page_config(
    page_title="AGRIWEAVE Command Center",
    page_icon="??",
    layout="wide",
)


def build_dashboard_state(
    verification_result=None,
    recovery_result=None,
    metrics=None,
):
    """
    Convert system results into a dashboard-friendly state.

    The dashboard only displays decisions produced by the
    verification and recovery layers. It does not make decisions.
    """

    verification_result = verification_result or {}
    recovery_result = recovery_result or {}
    metrics = metrics or VerificationMetrics()

    return {
        "match": {
            "decision": verification_result.get(
                "decision",
                "WAITING",
            ),
            "verified": verification_result.get(
                "verified",
                False,
            ),
            "summary": verification_result.get(
                "summary",
                "No match verification has been submitted yet.",
            ),
            "errors": verification_result.get(
                "errors",
                [],
            ),
            "warnings": verification_result.get(
                "warnings",
                [],
            ),
        },
        "recovery": {
            "decision": recovery_result.get(
                "decision",
                "NO RECOVERY",
            ),
            "recovered": recovery_result.get(
                "recovered",
                False,
            ),
            "summary": recovery_result.get(
                "summary",
                "No supply recovery has been attempted.",
            ),
            "errors": recovery_result.get(
                "errors",
                [],
            ),
        },
        "metrics": metrics.snapshot(),
    }


def render_status(label, value):
    st.metric(label=label, value=value)


def render_dashboard(state):
    st.title("?? AGRIWEAVE Command Center")
    st.caption(
        "Intelligent market access and verification "
        "for fragmented agricultural supply."
    )

    match = state["match"]
    recovery = state["recovery"]
    metrics = state["metrics"]

    st.divider()

    # ---------------------------------------------------------
    # TOP-LEVEL SYSTEM STATUS
    # ---------------------------------------------------------

    st.subheader("System Status")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        render_status(
            "Match Decision",
            match["decision"],
        )

    with col2:
        render_status(
            "Recovery",
            recovery["decision"],
        )

    with col3:
        render_status(
            "Verification Rate",
            f"{metrics['verification']['success_rate_percent']}%",
        )

    with col4:
        render_status(
            "Recovery Success",
            f"{metrics['recovery']['success_rate_percent']}%",
        )

    st.divider()

    # ---------------------------------------------------------
    # MATCH VERIFICATION
    # ---------------------------------------------------------

    st.subheader("?? Match Verification")

    if match["verified"]:
        st.success(match["summary"])
    else:
        st.warning(match["summary"])

    col1, col2 = st.columns(2)

    with col1:
        st.write("**Verification Decision**")
        st.code(match["decision"])

    with col2:
        st.write("**Verification Errors**")

        if match["errors"]:
            for error in match["errors"]:
                st.error(error)
        else:
            st.success("No verification errors.")

    if match["warnings"]:
        st.write("**Warnings**")

        for warning in match["warnings"]:
            st.warning(warning)

    st.divider()

    # ---------------------------------------------------------
    # SUPPLY RESCUE
    # ---------------------------------------------------------

    st.subheader("?? Supply Rescue")

    if recovery["recovered"]:
        st.success(recovery["summary"])
    else:
        st.info(recovery["summary"])

    if recovery["errors"]:
        for error in recovery["errors"]:
            st.error(error)

    st.divider()

    # ---------------------------------------------------------
    # OPERATIONAL METRICS
    # ---------------------------------------------------------

    st.subheader("?? Operational Intelligence")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        render_status(
            "Total Matches",
            metrics["verification"]["total"],
        )

    with col2:
        render_status(
            "Verified",
            metrics["verification"]["verified"],
        )

    with col3:
        render_status(
            "Rejected",
            metrics["verification"]["rejected"],
        )

    with col4:
        render_status(
            "Recovery Attempts",
            metrics["recovery"]["total"],
        )

    st.divider()

    # ---------------------------------------------------------
    # FAILURE INTELLIGENCE
    # ---------------------------------------------------------

    st.subheader("?? Failure Intelligence")

    rejection_reasons = metrics["rejection_reasons"]

    if rejection_reasons:
        st.write("**Top Match Rejection Reasons**")

        for reason, count in rejection_reasons.items():
            st.write(f"- {reason} — **{count}**")
    else:
        st.success("No match rejection reasons recorded.")

    recovery_failures = metrics["recovery_failure_reasons"]

    if recovery_failures:
        st.write("**Recovery Failure Reasons**")

        for reason, count in recovery_failures.items():
            st.write(f"- {reason} — **{count}**")
    else:
        st.success("No recovery failures recorded.")

    st.divider()

    st.caption(
        "AGRIWEAVE verification is fail-closed: "
        "unexpected or invalid verification results are never "
        "automatically accepted."
    )


if __name__ == "__main__":
    metrics = VerificationMetrics()

    state = build_dashboard_state(
        metrics=metrics,
    )

    render_dashboard(state)
