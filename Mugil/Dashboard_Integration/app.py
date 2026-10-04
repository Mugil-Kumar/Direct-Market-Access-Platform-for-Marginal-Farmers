
import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from Disha.Marketplace_Data_Logistics.api import MarketplaceService
from Disha.Marketplace_Data_Logistics.database import Database
from integration.agriweave_pipeline import AgriweavePipeline


st.set_page_config(
    page_title="AGRIWEAVE | Intelligent Farmer Market Network",
    page_icon="",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>

.block-container {
    max-width: 1450px;
    padding-top: 1.5rem;
    padding-bottom: 3rem;
}

/* ---------- MAIN BACKGROUND ---------- */

.stApp {
    background: #080808;
    color: #FFFFFF;
}

/* ---------- HERO ---------- */

.hero {
    padding: 32px 36px;
    border-radius: 18px;
    background: linear-gradient(135deg, #0A0A0A 0%, #171717 55%, #242424 100%);
    color: #FFFFFF;
    border: 1px solid #C9A227;
    margin-bottom: 24px;
    box-shadow: 0 0 25px rgba(201,162,39,0.12);
}

.hero h1 {
    font-size: 3.2rem;
    font-weight: 800;
    color: #FFFFFF !important;
    margin-bottom: 6px;
    letter-spacing: 1px;
}

.hero p {
    color: #D6D6D6 !important;
    font-size: 1.1rem;
}

/* ---------- HEADINGS ---------- */

h1, h2, h3, h4 {
    color: #FFFFFF !important;
}

.stSubheader {
    color: #FFFFFF !important;
}

/* ---------- METRICS ---------- */

[data-testid="stMetric"] {
    background: #111111;
    border: 1px solid #292929;
    border-radius: 14px;
    padding: 18px;
}

[data-testid="stMetricLabel"] {
    color: #BDBDBD !important;
}

[data-testid="stMetricValue"] {
    color: #FFFFFF !important;
}

[data-testid="stMetricDelta"] {
    color: #C9A227 !important;
}

/* ---------- PIPELINE ---------- */

.stage {
    padding: 18px;
    min-height: 82px;
    border-radius: 14px;
    border: 1px solid #333333;
    background: #151515;
    color: #FFFFFF !important;
    text-align: center;
}

.stage strong {
    color: #FFFFFF !important;
}

.stage span {
    color: #C9A227 !important;
    font-weight: 800;
}

.stage.active {
    border: 2px solid #C9A227;
    background: #191919;
    box-shadow: 0 0 14px rgba(201,162,39,0.15);
}

/* ---------- CARDS ---------- */

.metric-card {
    padding: 18px;
    border-radius: 14px;
    background: #111111;
    border: 1px solid #333333;
    color: #FFFFFF;
}

/* ---------- RESCUE ---------- */

.rescue {
    padding: 22px;
    border-radius: 16px;
    background: #210909;
    border: 2px solid #D62828;
    color: #FFFFFF !important;
}

.rescue h3 {
    color: #FF4D4D !important;
}

/* ---------- SUCCESS ---------- */

.success {
    padding: 22px;
    border-radius: 16px;
    background: #0D2115;
    border: 2px solid #2E9B57;
    color: #FFFFFF !important;
}

.success strong {
    color: #FFFFFF !important;
}

/* ---------- INFO BOX ---------- */

[data-testid="stAlert"] {
    color: #FFFFFF !important;
}

[data-testid="stAlert"] p {
    color: #FFFFFF !important;
}

/* ---------- DATAFRAME ---------- */

[data-testid="stDataFrame"] {
    border: 1px solid #333333;
}

/* ---------- BUTTON ---------- */

.stButton > button {
    background: #B91C1C;
    color: #FFFFFF;
    border: 1px solid #FF4D4D;
    border-radius: 10px;
    font-weight: 700;
    min-height: 48px;
}

.stButton > button:hover {
    background: #D62828;
    color: #FFFFFF;
    border-color: #C9A227;
}

/* ---------- GOLD ACCENT ---------- */

.gold-text {
    color: #C9A227 !important;
}

.red-text {
    color: #FF4D4D !important;
}

.white-text {
    color: #FFFFFF !important;
}

/* ---------- CAPTION ---------- */

.stCaption {
    color: #999999 !important;
}

/* ---------- DIVIDER ---------- */

hr {
    border-color: #333333 !important;
}

</style>
""", unsafe_allow_html=True)


def build_dashboard_state(
    verification_result=None,
    metrics=None,
    recovery_result=None,
    result=None,
    rescue=None,
    **kwargs,
):
    """
    Build the dashboard state consumed by the dashboard and tests.

    The state intentionally separates:
      - match decision
      - recovery decision
      - verification metrics
      - recovery metrics
    """

    # ---------------------------------------------------------
    # Backward compatibility aliases
    # ---------------------------------------------------------
    if verification_result is None and result is not None:
        if isinstance(result, dict):
            verification_result = result.get(
                "verification",
                result,
            )
        else:
            verification_result = getattr(
                result,
                "verification",
                None,
            )

    if recovery_result is None and rescue is not None:
        recovery_result = rescue

    # ---------------------------------------------------------
    # Match state
    # ---------------------------------------------------------
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
            "verified": bool(
                verification_result.get("verified", False)
            ),
            "decision": verification_result.get(
                "decision",
                "UNKNOWN",
            ),
            "summary": verification_result.get(
                "summary",
                "",
            ),
            "errors": list(
                verification_result.get("errors", [])
                or []
            ),
            "warnings": list(
                verification_result.get("warnings", [])
                or []
            ),
        }

    # ---------------------------------------------------------
    # Recovery state
    # ---------------------------------------------------------
    if recovery_result is None:
        recovery_state = {
            "recovered": False,
            "decision": "NO RECOVERY",
            "summary": "No recovery operation has been triggered.",
            "errors": [],
        }
    else:
        recovery_state = {
            "recovered": bool(
                recovery_result.get("recovered", False)
            ),
            "decision": recovery_result.get(
                "decision",
                "UNKNOWN",
            ),
            "summary": recovery_result.get(
                "summary",
                "",
            ),
            "errors": list(
                recovery_result.get("errors", [])
                or []
            ),
        }

    # ---------------------------------------------------------
    # Metrics snapshot
    # ---------------------------------------------------------
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

    # Make sure the dashboard always has both metric sections.
    verification_metrics = dict(
        metrics_snapshot.get(
            "verification",
            {},
        )
    )

    recovery_metrics = dict(
        metrics_snapshot.get(
            "recovery",
            {},
        )
    )

    verification_metrics.setdefault("total", 0)
    verification_metrics.setdefault("verified", 0)
    verification_metrics.setdefault("rejected", 0)
    verification_metrics.setdefault(
        "success_rate_percent",
        0.0,
    )

    recovery_metrics.setdefault("total", 0)
    recovery_metrics.setdefault("successful", 0)
    recovery_metrics.setdefault("failed", 0)
    recovery_metrics.setdefault(
        "success_rate_percent",
        0.0,
    )

    # ---------------------------------------------------------
    # Complete dashboard state
    # ---------------------------------------------------------
    state = {
        "match": match_state,
        "recovery": recovery_state,
        "metrics": {
            "verification": verification_metrics,
            "recovery": recovery_metrics,
        },
    }

    # ---------------------------------------------------------
    # Optional pipeline information
    # ---------------------------------------------------------
    if result is not None:
        state["pipeline"] = {
            "demand_id": getattr(
                result,
                "demand_id",
                None,
            ),
            "supply_ids": list(
                getattr(result, "supply_ids", [])
                or []
            ),
            "matched_quantity_kg": float(
                getattr(
                    result,
                    "matched_quantity_kg",
                    0.0,
                )
                or 0.0
            ),
            "optimized_quantity_kg": float(
                getattr(
                    result,
                    "optimized_quantity_kg",
                    0.0,
                )
                or 0.0
            ),
            "errors": list(
                getattr(result, "errors", [])
                or []
            ),
            "warnings": list(
                getattr(result, "warnings", [])
                or []
            ),
        }

    return state


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
    demand = data["demands"][0]
    result = pipeline.run(demand=demand)
    return pipeline, data, demand, result


def run_rescue_demo(pipeline, data, demand):
    original_supplies = [
        s for s in data["supplies"]
        if s.id != "SUP-DEMO-004"
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


st.markdown("""
<div class="hero">
    <h1>AGRIWEAVE</h1>
    <p>Intelligent market access for marginal farmers</p>
    <p>Demand-driven matching | Collective aggregation | Verified recovery</p>
</div>
""", unsafe_allow_html=True)


pipeline, data, demand, result = run_normal_demo()

# ---------------------------------------------------------
# TOP STATUS
# ---------------------------------------------------------
st.subheader("Live Market Decision")

cols = st.columns(5)

with cols[0]:
    st.metric("Buyer Demand", f"{demand.quantity_kg:.0f} kg")

with cols[1]:
    st.metric("Available Supply", f"{result.matched_quantity_kg:.0f} kg")

with cols[2]:
    st.metric("Optimized Order", f"{result.optimized_quantity_kg:.0f} kg")

with cols[3]:
    st.metric("Farmers Matched", len(result.supply_ids))

with cols[4]:
    verified = bool(
        result.verification
        and result.verification.get("verified")
    )
    st.metric("Verification", "PASSED" if verified else "FAILED")


# ---------------------------------------------------------
# FLOW
# ---------------------------------------------------------
st.subheader("Decision Pipeline")

flow = [
    ("1", "Buyer Demand", True),
    ("2", "AI Matching", True),
    ("3", "Aggregation", True),
    ("4", "Optimization", True),
    ("5", "Verification", verified),
]

flow_cols = st.columns(5)

for col, (num, label, passed) in zip(flow_cols, flow):
    with col:
        state = "|" if passed else "|"
        st.markdown(
            f"""
            <div class="stage {'active' if passed else ''}">
                <strong>{num}. {label}</strong><br>
                <span style="font-size:1.5rem">{state}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )


# ---------------------------------------------------------
# MARKET INTELLIGENCE
# ---------------------------------------------------------
st.subheader("AI Market Intelligence")

left, right = st.columns(2)

with left:
    st.markdown("### Recommended Supply")
    st.write(result.supply_ids)

    explanation = getattr(result, "ai_explanation", "")
    if explanation:
        st.info(explanation)
    else:
        st.info(
            f"AI selected {len(result.supply_ids)} farmer supplies "
            f"to satisfy the buyer demand."
        )

with right:
    st.markdown("### Economics")

    order = result.order

    if order:
        st.write(
            f"**Estimated selling price:** |{order.selling_price_per_kg:.2f}/kg"
        )
        st.write(
            f"**Order value:** "
            f"|{order.quantity_kg * order.selling_price_per_kg:,.0f}"
        )

    st.write(
        "**Market gap:** "
        f"{result.matched_quantity_kg - demand.quantity_kg:.0f} kg surplus"
    )


# ---------------------------------------------------------
# FARMER BREAKDOWN
# ---------------------------------------------------------
st.subheader("Farmer Supply Network")

rows = []

for supply in data["supplies"]:
    rows.append({
        "Supply": supply.id,
        "Farmer": supply.farmer_id,
        "Location": supply.location,
        "Crop": supply.crop,
        "Quantity (kg)": supply.quantity_kg,
        "Price (|/kg)": supply.expected_price_per_kg,
        "Quality": supply.quality,
        "Status": supply.status,
    })

st.dataframe(
    rows,
    width='stretch',
    hide_index=True,
)


# ---------------------------------------------------------
# VERIFICATION
# ---------------------------------------------------------
st.subheader("Independent Verification")

if verified:
    st.markdown(
        """
        <div class="success">
        <strong>| ORDER VERIFIED</strong><br>
        Every allocated supply passed independent supply,
        demand and constraint verification.
        </div>
        """,
        unsafe_allow_html=True,
    )
else:
    st.error("Order rejected by independent verification.")


# ---------------------------------------------------------
# SUPPLY RESCUE
# ---------------------------------------------------------
st.divider()
st.subheader(" Supply Rescue Simulation")

st.write(
    "Simulate a committed farmer failing after the order has been planned."
)

if st.button(
    "Simulate SUP-DEMO-001 Failure",
    type="primary",
    width='stretch',
):
    rescue = run_rescue_demo(pipeline, data, demand)

    st.session_state["rescue"] = rescue

rescue = st.session_state.get("rescue")

if rescue:
    st.markdown(
        """
        <div class="rescue">
        <h3>SUPPLY DISRUPTION DETECTED</h3>
        </div>
        """,
        unsafe_allow_html=True,
    )

    r1, r2, r3, r4 = st.columns(4)

    with r1:
        st.metric(
            "Failed Supply",
            rescue["failed_supply_id"],
        )

    with r2:
        st.metric(
            "Shortfall",
            f'{rescue["shortfall_quantity_kg"]:.0f} kg',
        )

    with r3:
        st.metric(
            "Replacement",
            ", ".join(rescue["replacement_supply_ids"]),
        )

    with r4:
        st.metric(
            "Recovered",
            f'{rescue["verified_recovered_quantity_kg"]:.0f} kg',
        )

    if rescue["recovered"]:
        st.success(
            f'RECOVERY VERIFIED | '
            f'{rescue["verified_recovered_quantity_kg"]:.0f} kg recovered '
            f'from the {rescue["shortfall_quantity_kg"]:.0f} kg shortfall.'
        )
    else:
        st.error(
            f'Recovery rejected: {rescue["summary"]}'
        )

    st.markdown("### Recovery Decision Trace")

    for item in rescue.get("trace", []):
        st.write("|", item)

    st.json({
        "decision": rescue["decision"],
        "recovery_ratio": rescue["recovery_ratio"],
        "replacement_supply_ids": rescue["replacement_supply_ids"],
        "errors": rescue["errors"],
        "warnings": rescue["warnings"],
    })


# ---------------------------------------------------------
# JUDGE SUMMARY
# ---------------------------------------------------------
st.divider()

st.subheader("Why AGRIWEAVE|")

a, b, c = st.columns(3)

with a:
    st.markdown("###  Demand First")
    st.write(
        "Farmers are matched against real buyer requirements "
        "instead of waiting for generic marketplace demand."
    )

with b:
    st.markdown("###  Collective Supply")
    st.write(
        "Multiple marginal farmers can combine their fragmented "
        "supply into a buyer-sized commercial order."
    )

with c:
    st.markdown("### | Resilient")
    st.write(
        "If a committed supplier fails, AGRIWEAVE finds, "
        "optimizes and independently verifies a replacement."
    )

st.caption(
    "AGRIWEAVE | AI proposes | Optimization allocates | "
    "Verification protects | Marketplace executes"
)
