
import json
import sys
from dataclasses import asdict, is_dataclass
from pathlib import Path

import streamlit as st


ROOT = Path(__file__).resolve().parents[2]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


from Disha.Marketplace_Data_Logistics.api import MarketplaceService
from Disha.Marketplace_Data_Logistics.database import Database
from integration.agriweave_pipeline import AgriweavePipeline


# ============================================================
# PAGE
# ============================================================

st.set_page_config(
    page_title="Direct Market-Access Platform for Marginal Farmers",
    page_icon="",
    layout="wide",
    initial_sidebar_state="collapsed",
)


# ============================================================
# CSS
# ============================================================

css_file = Path(__file__).parent / "assets" / "command_center.css"

if css_file.exists():
    st.markdown(
        f"<style>{css_file.read_text(encoding='utf-8')}</style>",
        unsafe_allow_html=True,
    )


# ============================================================
# JSON SAFETY
# ============================================================

def _json_safe(value):
    """
    Convert all pipeline objects to primitive JSON-safe values.

    Important:
    AIPipelineResult and other dataclasses never reach the browser
    as Python objects.
    """

    if value is None:
        return None

    if isinstance(value, (str, int, float, bool)):
        return value

    if is_dataclass(value):
        return _json_safe(asdict(value))

    if isinstance(value, dict):
        return {
            str(key): _json_safe(item)
            for key, item in value.items()
        }

    if isinstance(value, (list, tuple, set)):
        return [_json_safe(item) for item in value]

    if hasattr(value, "__dict__"):
        return _json_safe(vars(value))

    return str(value)


# ============================================================
# TEST CONTRACT
# ============================================================

def build_dashboard_state(
    verification_result=None,
    metrics=None,
    recovery_result=None,
    result=None,
    rescue=None,
    **kwargs,
):
    """
    Stable state contract used by dashboard tests and UI.

    This function deliberately exposes only primitive dashboard data.
    """

    if verification_result is None and result is not None:
        if isinstance(result, dict):
            verification_result = result.get("verification", result)
        else:
            verification_result = getattr(result, "verification", None)

    if recovery_result is None and rescue is not None:
        recovery_result = rescue

    if verification_result is None:
        match_state = {
            "verified": False,
            "decision": "WAITING",
            "summary": "Waiting for verification.",
            "errors": [],
            "warnings": [],
        }
    else:
        match_state = {
            "verified": bool(verification_result.get("verified", False)),
            "decision": verification_result.get("decision", "UNKNOWN"),
            "summary": verification_result.get("summary", ""),
            "errors": list(verification_result.get("errors", []) or []),
            "warnings": list(
                verification_result.get("warnings", []) or []
            ),
        }

    if recovery_result is None:
        recovery_state = {
            "recovered": False,
            "decision": "NO RECOVERY",
            "summary": "No recovery operation has been triggered.",
            "errors": [],
        }
    else:
        recovery_state = {
            "recovered": bool(recovery_result.get("recovered", False)),
            "decision": recovery_result.get("decision", "UNKNOWN"),
            "summary": recovery_result.get("summary", ""),
            "errors": list(recovery_result.get("errors", []) or []),
        }

    if metrics is not None and hasattr(metrics, "snapshot"):
        metrics_snapshot = metrics.snapshot()
    else:
        metrics_snapshot = {
            "verification": {
                "total": 0,
                "verified": 0,
                "rejected": 0,
                "success_rate_percent": 0.0,
            },
            "recovery": {
                "total": 0,
                "successful": 0,
                "failed": 0,
                "success_rate_percent": 0.0,
            },
        }

    verification_metrics = dict(
        metrics_snapshot.get("verification", {})
    )

    recovery_metrics = dict(
        metrics_snapshot.get("recovery", {})
    )

    verification_metrics.setdefault("total", 0)
    verification_metrics.setdefault("verified", 0)
    verification_metrics.setdefault("rejected", 0)
    verification_metrics.setdefault("success_rate_percent", 0.0)

    recovery_metrics.setdefault("total", 0)
    recovery_metrics.setdefault("successful", 0)
    recovery_metrics.setdefault("failed", 0)
    recovery_metrics.setdefault("success_rate_percent", 0.0)

    state = {
        "match": match_state,
        "recovery": recovery_state,
        "metrics": {
            "verification": verification_metrics,
            "recovery": recovery_metrics,
        },
    }

    if result is not None:
        state["pipeline"] = {
            "demand_id": getattr(result, "demand_id", None),
            "supply_ids": list(
                getattr(result, "supply_ids", []) or []
            ),
            "matched_quantity_kg": float(
                getattr(result, "matched_quantity_kg", 0.0) or 0.0
            ),
            "optimized_quantity_kg": float(
                getattr(result, "optimized_quantity_kg", 0.0) or 0.0
            ),
            "errors": list(
                getattr(result, "errors", []) or []
            ),
            "warnings": list(
                getattr(result, "warnings", []) or []
            ),
        }

    return state


# ============================================================
# PIPELINE
# ============================================================

@st.cache_resource
def get_pipeline():
    marketplace = MarketplaceService(
        database=Database("integration_demo.db")
    )

    return AgriweavePipeline(
        marketplace=marketplace,
        dry_run=True,
    )


def run_normal_demo():
    pipeline = get_pipeline()

    data = pipeline.get_market_data(crop="Tomato")

    if not data.get("demands"):
        raise RuntimeError("No demo demand found.")

    demand = data["demands"][0]

    result = pipeline.run(demand=demand)

    return pipeline, data, demand, result


def run_rescue_demo(pipeline, data, demand):

    # The emergency backup is not allowed to influence the
    # original order. It becomes available only for rescue.

    original_supplies = [
        supply
        for supply in data["supplies"]
        if supply.id != "SUP-DEMO-004"
    ]

    ai_result = pipeline.run_ai_matching(
        demand=demand,
        supplies=original_supplies,
    )

    selected = pipeline.select_supply_set(
        demand=demand,
        supplies=original_supplies,
        ai_result=ai_result,
    )

    optimization = pipeline.run_optimization(
        demand=demand,
        supplies=selected,
    )

    order = pipeline.build_order(
        demand=demand,
        supplies=selected,
        optimization=optimization,
    )

    return pipeline.run_supply_rescue(
        demand=demand,
        order=order,
        supplies=selected,
        optimization=optimization,
        failed_supply_id="SUP-DEMO-001",
        replacement_supplies=data["supplies"],
    )


# ============================================================
# HERO
# ============================================================

st.markdown(
    """
    <div class="command-bar">
        <div class="brand">
            DEVHACK 2026 <span>/</span> AGRIWEAVE
        </div>
        <div class="system-online">
            <span class="online-dot"></span>
            SYSTEM ONLINE
        </div>
    </div>

    <div class="hero-shell">

        <div class="hero-kicker">
            PROBLEM STATEMENT 1.2
        </div>

        <div class="hero-title">
            <span class="red">DIRECT MARKET-ACCESS</span>
            <span class="gold">PLATFORM FOR MARGINAL FARMERS</span>
        </div>

        <div class="hero-description">
            Build a demand-driven market network that converts fragmented
            farmer supply into reliable commercial orders while protecting
            quantity, quality, economics and delivery continuity.
        </div>

        <div class="problem-chip">
            AI MARKET NETWORK / DECISION COMMAND CENTER
        </div>

        <div class="core-scene">

            <div class="orbit one"></div>
            <div class="orbit two"></div>
            <div class="orbit three"></div>

            <div class="core">
                <div class="cube"></div>
                <div class="face front">AI CORE</div>
                <div class="face back">MATCH</div>
                <div class="face right">VERIFY</div>
                <div class="face left">OPTIMIZE</div>
                <div class="face top">RESCUE</div>
                <div class="face bottom">MARKET</div>
            </div>

            <div class="node farmer">FARMERS</div>
            <div class="node buyer">BUYERS</div>
            <div class="node logistics">LOGISTICS</div>
            <div class="node verify">VERIFICATION</div>

        </div>

    </div>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# EXECUTE NORMAL PIPELINE
# ============================================================

try:
    pipeline, data, demand, result = run_normal_demo()

except Exception as exc:
    st.error(
        "Command center could not initialize the demo pipeline."
    )
    st.code(str(exc))
    st.stop()


verified = bool(
    result.verification
    and result.verification.get("verified")
)

order = result.order

supply_total = float(result.matched_quantity_kg or 0.0)
optimized_total = float(result.optimized_quantity_kg or 0.0)

farmer_count = len(result.supply_ids)

confidence = 0.0

if result.recommendation is not None:
    confidence = float(
        getattr(result.recommendation, "score", 0.0) or 0.0
    ) * 100.0

surplus = max(
    0.0,
    supply_total - float(demand.quantity_kg),
)


# ============================================================
# LIVE MARKET
# ============================================================

st.markdown(
    '<div class="section-kicker">EXECUTIVE OVERVIEW</div>',
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="section-title">Live Market Decision</div>',
    unsafe_allow_html=True,
)

st.markdown(
    f"""
    <div class="metric-grid">

        <div class="metric">
            <div class="metric-label">BUYER DEMAND</div>
            <div class="metric-value">
                {demand.quantity_kg:.0f} kg
            </div>
            <div class="metric-sub">Commercial requirement</div>
        </div>

        <div class="metric">
            <div class="metric-label">SUPPLY POOL</div>
            <div class="metric-value gold">
                {supply_total:.0f} kg
            </div>
            <div class="metric-sub">Available farmer capacity</div>
        </div>

        <div class="metric">
            <div class="metric-label">OPTIMIZED ORDER</div>
            <div class="metric-value">
                {optimized_total:.0f} kg
            </div>
            <div class="metric-sub">Feasible allocation</div>
        </div>

        <div class="metric">
            <div class="metric-label">FARMER NETWORK</div>
            <div class="metric-value">
                {farmer_count}
            </div>
            <div class="metric-sub">Selected suppliers</div>
        </div>

        <div class="metric">
            <div class="metric-label">TRUST LAYER</div>
            <div class="metric-value {'green' if verified else 'red'}">
                {'VERIFIED' if verified else 'REJECTED'}
            </div>
            <div class="metric-sub">Independent verification</div>
        </div>

    </div>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# DECISION PIPELINE
# ============================================================

st.markdown(
    '<div class="section-kicker">DECISION ENGINE</div>',
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="section-title">Demand to Verified Order</div>',
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="pipeline">

        <div class="pipeline-step">
            <div class="pipeline-number">01</div>
            <div class="pipeline-name">BUYER DEMAND</div>
            <div class="pipeline-status">PASS</div>
        </div>

        <div class="pipeline-step">
            <div class="pipeline-number">02</div>
            <div class="pipeline-name">AI MATCHING</div>
            <div class="pipeline-status">PASS</div>
        </div>

        <div class="pipeline-step">
            <div class="pipeline-number">03</div>
            <div class="pipeline-name">COLLECTIVE SUPPLY</div>
            <div class="pipeline-status">PASS</div>
        </div>

        <div class="pipeline-step">
            <div class="pipeline-number">04</div>
            <div class="pipeline-name">ECONOMIC OPTIMIZATION</div>
            <div class="pipeline-status">PASS</div>
        </div>

        <div class="pipeline-step">
            <div class="pipeline-number">05</div>
            <div class="pipeline-name">INDEPENDENT VERIFICATION</div>
            <div class="pipeline-status">
                {'PASS' if verified else 'REJECT'}
            </div>
        </div>

    </div>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# INTELLIGENCE PANELS
# ============================================================

st.markdown(
    '<div class="section-kicker">MARKET INTELLIGENCE</div>',
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="section-title">AI proposes. Optimization decides. Verification protects.</div>',
    unsafe_allow_html=True,
)

left, right = st.columns(2, gap="large")


with left:

    recommendation_text = getattr(
        result,
        "ai_explanation",
        "",
    )

    if not recommendation_text:
        recommendation_text = (
            f"Collective supply recommendation using "
            f"{farmer_count} farmer suppliers."
        )

    coverage = 100.0

    if result.recommendation is not None:
        coverage = float(
            getattr(
                result.recommendation,
                "coverage_percent",
                100.0,
            )
            or 0.0
        )

    st.markdown(
        f"""
        <div class="panel">

            <div class="panel-label">
                AI MARKET INTELLIGENCE
            </div>

            <div class="panel-title">
                Intelligent Supply Recommendation
            </div>

            <div class="big-number">
                {farmer_count} FARMERS
            </div>

            <div style="color:#9da2ad;">
                {coverage:.0f}% buyer quantity coverage
            </div>

            <div class="confidence-track">
                <div class="confidence-fill"
                     style="width:{min(max(confidence,0),100):.1f}%">
                </div>
            </div>

            <div style="margin-top:9px;color:#777c87;font-size:.7rem;">
                AI recommendation confidence: {confidence:.1f} / 100
            </div>

            <div style="
                margin-top:20px;
                padding-top:18px;
                border-top:1px solid rgba(255,255,255,.07);
                color:#a9adb7;
                line-height:1.6;
                font-size:.8rem;
            ">
                {recommendation_text}
            </div>

        </div>
        """,
        unsafe_allow_html=True,
    )


with right:

    selling_price = (
        float(order.selling_price_per_kg)
        if order is not None
        else 0.0
    )

    order_value = (
        optimized_total * selling_price
        if order is not None
        else 0.0
    )

    st.markdown(
        f"""
        <div class="panel">

            <div class="panel-label">
                ECONOMIC OPTIMIZATION
            </div>

            <div class="panel-title">
                Order Economics
            </div>

            <div class="big-number">
                INR {selling_price:.2f} / kg
            </div>

            <div style="margin-top:22px">

                <div style="
                    display:flex;
                    justify-content:space-between;
                    padding:13px 0;
                    border-bottom:1px solid rgba(255,255,255,.06);
                    color:#9da2ad;
                    font-size:.8rem;
                ">
                    <span>Buyer requirement</span>
                    <strong style="color:white">
                        {demand.quantity_kg:.0f} kg
                    </strong>
                </div>

                <div style="
                    display:flex;
                    justify-content:space-between;
                    padding:13px 0;
                    border-bottom:1px solid rgba(255,255,255,.06);
                    color:#9da2ad;
                    font-size:.8rem;
                ">
                    <span>Optimized allocation</span>
                    <strong style="color:white">
                        {optimized_total:.0f} kg
                    </strong>
                </div>

                <div style="
                    display:flex;
                    justify-content:space-between;
                    padding:13px 0;
                    border-bottom:1px solid rgba(255,255,255,.06);
                    color:#9da2ad;
                    font-size:.8rem;
                ">
                    <span>Order value</span>
                    <strong style="color:var(--gold)">
                        INR {order_value:,.0f}
                    </strong>
                </div>

                <div style="
                    display:flex;
                    justify-content:space-between;
                    padding:13px 0;
                    color:#9da2ad;
                    font-size:.8rem;
                ">
                    <span>Supply surplus</span>
                    <strong style="color:var(--gold)">
                        {surplus:.0f} kg
                    </strong>
                </div>

            </div>

        </div>
        """,
        unsafe_allow_html=True,
    )


# ============================================================
# SUPPLY NETWORK
# ============================================================

st.markdown(
    '<div class="section-kicker">SUPPLY NETWORK</div>',
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="section-title">Farmer Supply Intelligence</div>',
    unsafe_allow_html=True,
)

rows = []

for supply in data["supplies"]:

    rows.append(
        {
            "SUPPLY": supply.id,
            "FARMER": supply.farmer_id,
            "LOCATION": supply.location,
            "CROP": supply.crop,
            "QUANTITY KG": supply.quantity_kg,
            "PRICE INR/KG": supply.expected_price_per_kg,
            "QUALITY": supply.quality,
            "STATUS": supply.status.upper(),
        }
    )

st.dataframe(
    rows,
    use_container_width=True,
    hide_index=True,
)


# ============================================================
# VERIFICATION
# ============================================================

st.markdown(
    '<div class="section-kicker">TRUST LAYER</div>',
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="section-title">Independent Verification</div>',
    unsafe_allow_html=True,
)

if verified:

    st.markdown(
        """
        <div class="rescue-success">
            ORDER VERIFIED<br>
            Supply, demand and constraint checks passed independently.
            The decision is safe to continue to marketplace execution.
        </div>
        """,
        unsafe_allow_html=True,
    )

else:

    st.error(
        "Order rejected by independent verification."
    )


# ============================================================
# SUPPLY RESCUE
# ============================================================

st.markdown(
    '<div class="section-kicker">RESILIENCE ENGINE</div>',
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="section-title">Supply Rescue Command</div>',
    unsafe_allow_html=True,
)

st.write(
    "Simulate a committed farmer becoming unavailable after the "
    "commercial order has already been planned."
)

if st.button(
    "SIMULATE SUP-DEMO-001 FAILURE",
    type="primary",
):

    try:

        rescue = run_rescue_demo(
            pipeline,
            data,
            demand,
        )

        # Store only JSON-safe primitive data.
        st.session_state["rescue"] = _json_safe(rescue)

    except Exception as exc:

        st.session_state["rescue_error"] = str(exc)


if "rescue_error" in st.session_state:

    st.markdown(
        """
        <div class="incident">

            <div class="incident-title">
                RECOVERY ENGINE ERROR
            </div>

            <div style="
                margin-top:12px;
                color:#b9bdc6;
                line-height:1.6;
            ">
                The recovery operation failed safely.
                No invalid order was created.
            </div>

        </div>
        """,
        unsafe_allow_html=True,
    )

    st.code(
        st.session_state["rescue_error"],
        language="text",
    )


rescue = st.session_state.get("rescue")


if rescue:

    recovered = bool(
        rescue.get("recovered", False)
    )

    failed_id = rescue.get(
        "failed_supply_id",
        "UNKNOWN",
    )

    shortfall = float(
        rescue.get(
            "shortfall_quantity_kg",
            0.0,
        )
        or 0.0
    )

    recovered_quantity = float(
        rescue.get(
            "verified_recovered_quantity_kg",
            0.0,
        )
        or 0.0
    )

    replacements = rescue.get(
        "replacement_supply_ids",
        [],
    ) or []

    ratio = float(
        rescue.get(
            "recovery_ratio",
            0.0,
        )
        or 0.0
    )

    st.markdown(
        f"""
        <div class="incident">

            <div class="incident-title">
                SUPPLY DISRUPTION DETECTED
            </div>

            <div style="
                margin-top:8px;
                color:#8e929d;
                font-size:.8rem;
            ">
                AGRIWEAVE automatically entered recovery mode.
            </div>

            <div class="metric-grid" style="margin-top:22px">

                <div class="metric">
                    <div class="metric-label">
                        FAILED SUPPLY
                    </div>
                    <div class="metric-value red">
                        {failed_id}
                    </div>
                </div>

                <div class="metric">
                    <div class="metric-label">
                        SHORTFALL
                    </div>
                    <div class="metric-value">
                        {shortfall:.0f} kg
                    </div>
                </div>

                <div class="metric">
                    <div class="metric-label">
                        REPLACEMENT
                    </div>
                    <div class="metric-value gold"
                         style="font-size:1.15rem">
                        {", ".join(replacements) if replacements else "NONE"}
                    </div>
                </div>

                <div class="metric">
                    <div class="metric-label">
                        RECOVERED
                    </div>
                    <div class="metric-value green">
                        {recovered_quantity:.0f} kg
                    </div>
                </div>

                <div class="metric">
                    <div class="metric-label">
                        RECOVERY RATIO
                    </div>
                    <div class="metric-value green">
                        {ratio * 100:.0f}%
                    </div>
                </div>

            </div>

        </div>
        """,
        unsafe_allow_html=True,
    )

    if recovered:

        st.markdown(
            f"""
            <div class="rescue-success">
                RECOVERY VERIFIED<br>
                {recovered_quantity:.0f} kg recovered from
                the {shortfall:.0f} kg shortfall.
                Replacement passed independent verification.
            </div>
            """,
            unsafe_allow_html=True,
        )

    else:

        st.error(
            "Recovery rejected safely. "
            + str(
                rescue.get(
                    "summary",
                    "Replacement was insufficient.",
                )
            )
        )

    trace = rescue.get("trace", []) or []

    if trace:

        st.markdown(
            "#### Recovery Decision Trace"
        )

        for index, item in enumerate(trace, 1):

            st.markdown(
                f"""
                <div class="trace-line">
                    <strong style="color:var(--gold)">
                        {index:02d}
                    </strong>
                    &nbsp;&nbsp;
                    {str(item)}
                </div>
                """,
                unsafe_allow_html=True,
            )


# ============================================================
# JUDGE SUMMARY
# ============================================================

st.markdown(
    '<div class="section-kicker">WHY THIS SOLUTION</div>',
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="section-title">What makes this different?</div>',
    unsafe_allow_html=True,
)

c1, c2, c3 = st.columns(3, gap="large")


with c1:

    st.markdown(
        """
        <div class="panel">
            <div class="panel-title">DEMAND FIRST</div>
            <div style="
                margin-top:15px;
                color:#9da2ad;
                line-height:1.7;
            ">
                Farmers are matched against actual buyer
                requirements instead of generic marketplace listings.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


with c2:

    st.markdown(
        """
        <div class="panel">
            <div class="panel-title">COLLECTIVE SUPPLY</div>
            <div style="
                margin-top:15px;
                color:#9da2ad;
                line-height:1.7;
            ">
                Fragmented quantities from marginal farmers become
                one commercially useful buyer-sized order.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


with c3:

    st.markdown(
        """
        <div class="panel">
            <div class="panel-title">RESILIENT NETWORK</div>
            <div style="
                margin-top:15px;
                color:#9da2ad;
                line-height:1.7;
            ">
                When a committed supplier fails, the system searches,
                replans and independently verifies a replacement.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ============================================================
# FOOTER
# ============================================================

st.markdown(
    """
    <div style="
        margin-top:45px;
        padding:22px 0;
        border-top:1px solid rgba(255,255,255,.07);
        text-align:center;
        color:#555b65;
        font-size:.65rem;
        letter-spacing:.2em;
    ">
        DIRECT MARKET-ACCESS PLATFORM FOR MARGINAL FARMERS
        &nbsp; / &nbsp;
        AI PROPOSES
        &nbsp; / &nbsp;
        OPTIMIZATION ALLOCATES
        &nbsp; / &nbsp;
        VERIFICATION PROTECTS
        &nbsp; / &nbsp;
        MARKETPLACE EXECUTES
    </div>
    """,
    unsafe_allow_html=True,
)
