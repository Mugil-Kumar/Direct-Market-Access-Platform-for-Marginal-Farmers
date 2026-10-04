
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
    page_icon="??",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
.block-container {
    max-width: 1450px;
    padding-top: 1.5rem;
}
.hero {
    padding: 28px 32px;
    border-radius: 18px;
    background: linear-gradient(135deg, #12372A 0%, #1F5D45 55%, #2D7A58 100%);
    color: white;
    margin-bottom: 22px;
}
.hero h1 {
    font-size: 3rem;
    margin-bottom: 4px;
}
.hero p {
    font-size: 1.1rem;
    opacity: 0.9;
}
.stage {
    padding: 16px;
    border-radius: 14px;
    border: 1px solid #d9e4dd;
    background: #f8fbf9;
    text-align: center;
}
.stage.active {
    border: 2px solid #2D7A58;
}
.metric-card {
    padding: 18px;
    border-radius: 14px;
    background: #f8fbf9;
    border: 1px solid #d9e4dd;
}
.rescue {
    padding: 22px;
    border-radius: 16px;
    background: #fff8e8;
    border: 2px solid #e4b84a;
}
.success {
    padding: 22px;
    border-radius: 16px;
    background: #edf8f1;
    border: 2px solid #55a56f;
}
</style>
""", unsafe_allow_html=True)


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
    <h1>?? AGRIWEAVE</h1>
    <p>Intelligent market access for marginal farmers</p>
    <p>Demand-driven matching ? Collective aggregation ? Verified recovery</p>
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
        state = "?" if passed else "?"
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
            f"**Estimated selling price:** ?{order.selling_price_per_kg:.2f}/kg"
        )
        st.write(
            f"**Order value:** "
            f"?{order.quantity_kg * order.selling_price_per_kg:,.0f}"
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
        "Price (?/kg)": supply.expected_price_per_kg,
        "Quality": supply.quality,
        "Status": supply.status,
    })

st.dataframe(
    rows,
    use_container_width=True,
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
        <strong>? ORDER VERIFIED</strong><br>
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
st.subheader("?? Supply Rescue Simulation")

st.write(
    "Simulate a committed farmer failing after the order has been planned."
)

if st.button(
    "Simulate SUP-DEMO-001 Failure",
    type="primary",
    use_container_width=True,
):
    rescue = run_rescue_demo(pipeline, data, demand)

    st.session_state["rescue"] = rescue

rescue = st.session_state.get("rescue")

if rescue:
    st.markdown(
        """
        <div class="rescue">
        <h3>? Supply Disruption Detected</h3>
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
            f'RECOVERY VERIFIED ? '
            f'{rescue["verified_recovered_quantity_kg"]:.0f} kg recovered '
            f'from the {rescue["shortfall_quantity_kg"]:.0f} kg shortfall.'
        )
    else:
        st.error(
            f'Recovery rejected: {rescue["summary"]}'
        )

    st.markdown("### Recovery Decision Trace")

    for item in rescue.get("trace", []):
        st.write("?", item)

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

st.subheader("Why AGRIWEAVE?")

a, b, c = st.columns(3)

with a:
    st.markdown("### ?? Demand First")
    st.write(
        "Farmers are matched against real buyer requirements "
        "instead of waiting for generic marketplace demand."
    )

with b:
    st.markdown("### ?? Collective Supply")
    st.write(
        "Multiple marginal farmers can combine their fragmented "
        "supply into a buyer-sized commercial order."
    )

with c:
    st.markdown("### ??? Resilient")
    st.write(
        "If a committed supplier fails, AGRIWEAVE finds, "
        "optimizes and independently verifies a replacement."
    )

st.caption(
    "AGRIWEAVE ? AI proposes ? Optimization allocates ? "
    "Verification protects ? Marketplace executes"
)
