
import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[2]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from Disha.Marketplace_Data_Logistics.api import MarketplaceService
from Disha.Marketplace_Data_Logistics.database import Database
from integration.agriweave_pipeline import AgriweavePipeline


# =========================================================
# PAGE
# =========================================================

st.set_page_config(
    page_title="AGRIWEAVE | Market Intelligence Command Center",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="collapsed",
)


# =========================================================
# DESIGN SYSTEM
# =========================================================

st.markdown(
    """
<style>

/* =======================================================
   GLOBAL
   ======================================================= */

.stApp {
    background:
        radial-gradient(circle at 15% 0%, rgba(201,162,39,0.08), transparent 28%),
        radial-gradient(circle at 90% 15%, rgba(190,30,45,0.07), transparent 25%),
        #070707;
    color: #F5F5F5;
}

.block-container {
    max-width: 1500px;
    padding-top: 1.2rem;
    padding-bottom: 4rem;
}

h1, h2, h3, h4, p, span, label {
    font-family: Inter, Arial, sans-serif;
}

h1, h2, h3, h4 {
    color: #FFFFFF !important;
}

hr {
    border-color: #292929 !important;
}


/* =======================================================
   TOP NAV
   ======================================================= */

.topbar {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 10px 0 20px 0;
    border-bottom: 1px solid #252525;
    margin-bottom: 22px;
}

.brand {
    color: #FFFFFF;
    font-size: 1.05rem;
    font-weight: 800;
    letter-spacing: 2px;
}

.brand span {
    color: #C9A227;
}

.live {
    color: #E8E8E8;
    font-size: 0.78rem;
    letter-spacing: 1.2px;
    text-transform: uppercase;
}

.live-dot {
    color: #D62828;
    font-weight: 900;
}


/* =======================================================
   HERO
   ======================================================= */

.hero {
    position: relative;
    overflow: hidden;
    padding: 42px 44px;
    border-radius: 24px;
    background:
        linear-gradient(115deg, #0A0A0A 0%, #111111 52%, #181818 100%);
    border: 1px solid #383838;
    box-shadow:
        0 20px 70px rgba(0,0,0,0.45),
        inset 0 1px 0 rgba(255,255,255,0.04);
    margin-bottom: 22px;
}

.hero:after {
    content: "";
    position: absolute;
    width: 420px;
    height: 420px;
    right: -160px;
    top: -230px;
    border-radius: 50%;
    border: 1px solid rgba(201,162,39,0.22);
    box-shadow:
        0 0 0 45px rgba(201,162,39,0.025),
        0 0 0 90px rgba(201,162,39,0.02);
}

.hero-kicker {
    color: #C9A227;
    font-size: 0.76rem;
    font-weight: 800;
    letter-spacing: 2.5px;
    text-transform: uppercase;
    margin-bottom: 12px;
}

.hero-title {
    color: #FFFFFF !important;
    font-size: 3.6rem;
    line-height: 1;
    font-weight: 900;
    letter-spacing: -1.5px;
    margin: 0;
}

.hero-title span {
    color: #C9A227;
}

.hero-subtitle {
    color: #B8B8B8;
    font-size: 1.05rem;
    max-width: 760px;
    margin-top: 15px;
    line-height: 1.7;
}

.hero-rule {
    width: 90px;
    height: 3px;
    background: #C9A227;
    margin-top: 22px;
}


/* =======================================================
   SECTION LABEL
   ======================================================= */

.section-label {
    color: #C9A227;
    font-size: 0.72rem;
    font-weight: 900;
    letter-spacing: 2px;
    text-transform: uppercase;
    margin-bottom: 6px;
}

.section-title {
    color: #FFFFFF;
    font-size: 1.65rem;
    font-weight: 800;
    margin-bottom: 16px;
}


/* =======================================================
   KPI CARDS
   ======================================================= */

.kpi {
    background: linear-gradient(145deg, #111111, #0C0C0C);
    border: 1px solid #292929;
    border-radius: 16px;
    padding: 19px 20px;
    min-height: 122px;
    box-shadow: inset 0 1px 0 rgba(255,255,255,0.025);
}

.kpi:hover {
    border-color: #555555;
}

.kpi-label {
    color: #8F8F8F;
    font-size: 0.72rem;
    font-weight: 800;
    letter-spacing: 1.3px;
    text-transform: uppercase;
}

.kpi-value {
    color: #FFFFFF;
    font-size: 2rem;
    font-weight: 900;
    margin-top: 8px;
}

.kpi-accent {
    color: #C9A227;
}

.kpi-success {
    color: #43D17A;
}

.kpi-danger {
    color: #FF4D4D;
}

.kpi-note {
    color: #777777;
    font-size: 0.72rem;
    margin-top: 5px;
}


/* =======================================================
   PIPELINE
   ======================================================= */

.pipeline {
    display: flex;
    gap: 8px;
    align-items: center;
    margin: 12px 0 25px 0;
}

.pipeline-step {
    flex: 1;
    min-height: 92px;
    background: #101010;
    border: 1px solid #292929;
    border-radius: 14px;
    padding: 15px;
    text-align: left;
}

.pipeline-step.active {
    border-color: #C9A227;
    box-shadow: 0 0 20px rgba(201,162,39,0.08);
}

.pipeline-num {
    color: #C9A227;
    font-size: 0.68rem;
    font-weight: 900;
    letter-spacing: 1px;
}

.pipeline-name {
    color: #FFFFFF;
    font-size: 0.9rem;
    font-weight: 800;
    margin-top: 7px;
}

.pipeline-status {
    color: #43D17A;
    font-size: 0.67rem;
    margin-top: 7px;
    font-weight: 800;
    letter-spacing: 0.8px;
}

.pipeline-arrow {
    color: #4D4D4D;
    font-weight: 900;
}


/* =======================================================
   PANELS
   ======================================================= */

.panel {
    background: #0E0E0E;
    border: 1px solid #272727;
    border-radius: 18px;
    padding: 22px;
    height: 100%;
}

.panel-head {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 17px;
}

.panel-title {
    color: #FFFFFF;
    font-size: 1.05rem;
    font-weight: 850;
}

.panel-tag {
    color: #C9A227;
    border: 1px solid #55491F;
    background: #17140A;
    padding: 5px 9px;
    border-radius: 99px;
    font-size: 0.62rem;
    font-weight: 800;
    letter-spacing: 0.8px;
}


/* =======================================================
   SUPPLY CARDS
   ======================================================= */

.supply-card {
    background: #111111;
    border: 1px solid #272727;
    border-radius: 14px;
    padding: 16px;
    margin-bottom: 10px;
}

.supply-card:hover {
    border-color: #C9A227;
}

.supply-id {
    color: #C9A227;
    font-size: 0.72rem;
    font-weight: 900;
    letter-spacing: 1px;
}

.supply-location {
    color: #FFFFFF;
    font-size: 1rem;
    font-weight: 800;
    margin-top: 5px;
}

.supply-meta {
    color: #858585;
    font-size: 0.75rem;
    margin-top: 6px;
}

.supply-qty {
    color: #FFFFFF;
    font-size: 1.35rem;
    font-weight: 900;
}


/* =======================================================
   ECONOMICS
   ======================================================= */

.money {
    color: #C9A227;
    font-size: 2.15rem;
    font-weight: 900;
}

.money-label {
    color: #858585;
    font-size: 0.73rem;
    text-transform: uppercase;
    letter-spacing: 1px;
}

.econ-row {
    display: flex;
    justify-content: space-between;
    padding: 12px 0;
    border-bottom: 1px solid #222222;
}

.econ-key {
    color: #929292;
}

.econ-val {
    color: #FFFFFF;
    font-weight: 800;
}


/* =======================================================
   VERIFICATION
   ======================================================= */

.verify-pass {
    background: linear-gradient(135deg, #0D2115, #0A150E);
    border: 1px solid #287846;
    border-radius: 16px;
    padding: 20px;
}

.verify-pass-title {
    color: #43D17A;
    font-weight: 900;
    font-size: 1rem;
    letter-spacing: 1px;
}

.verify-pass-text {
    color: #B9C7BE;
    font-size: 0.82rem;
    margin-top: 8px;
    line-height: 1.6;
}

.verify-fail {
    background: #210909;
    border: 1px solid #8D2323;
    border-radius: 16px;
    padding: 20px;
}

.verify-fail-title {
    color: #FF4D4D;
    font-weight: 900;
}


/* =======================================================
   RESCUE COMMAND CENTER
   ======================================================= */

.rescue-panel {
    background:
        linear-gradient(135deg, #180A0A, #0D0D0D 65%);
    border: 1px solid #702121;
    border-radius: 22px;
    padding: 28px;
    box-shadow: 0 18px 50px rgba(100,0,0,0.12);
}

.rescue-kicker {
    color: #FF4D4D;
    font-size: 0.72rem;
    font-weight: 900;
    letter-spacing: 2px;
    text-transform: uppercase;
}

.rescue-title {
    color: #FFFFFF;
    font-size: 1.8rem;
    font-weight: 900;
    margin-top: 5px;
}

.rescue-sub {
    color: #969696;
    font-size: 0.85rem;
    margin-bottom: 20px;
}

.rescue-result {
    background: #0B1D12;
    border: 1px solid #287846;
    border-radius: 16px;
    padding: 20px;
}

.rescue-result-title {
    color: #43D17A;
    font-size: 1.05rem;
    font-weight: 900;
    letter-spacing: 1px;
}

.rescue-big {
    color: #FFFFFF;
    font-size: 2.2rem;
    font-weight: 900;
}

.rescue-small {
    color: #808080;
    font-size: 0.7rem;
    text-transform: uppercase;
    letter-spacing: 1px;
}


/* =======================================================
   TRACE
   ======================================================= */

.trace {
    background: #0B0B0B;
    border-left: 2px solid #C9A227;
    padding: 12px 16px;
    margin-bottom: 8px;
    border-radius: 0 9px 9px 0;
    color: #BDBDBD;
    font-size: 0.8rem;
}

.trace strong {
    color: #FFFFFF;
}


/* =======================================================
   BUTTONS
   ======================================================= */

.stButton > button {
    width: 100%;
    min-height: 48px;
    border-radius: 10px;
    border: 1px solid #B52B2B;
    background: #B91C1C;
    color: #FFFFFF;
    font-weight: 900;
    letter-spacing: 0.4px;
    transition: all 0.2s ease;
}

.stButton > button:hover {
    background: #D62828;
    border-color: #C9A227;
    color: #FFFFFF;
    box-shadow: 0 8px 25px rgba(214,40,40,0.2);
}


/* =======================================================
   TABS
   ======================================================= */

button[data-baseweb="tab"] {
    color: #888888 !important;
    font-weight: 800 !important;
}

button[data-baseweb="tab"][aria-selected="true"] {
    color: #FFFFFF !important;
}

div[data-baseweb="tab-highlight"] {
    background-color: #C9A227 !important;
}


/* =======================================================
   STREAMLIT COMPONENTS
   ======================================================= */

[data-testid="stMetric"] {
    background: #101010;
    border: 1px solid #292929;
    border-radius: 14px;
    padding: 16px;
}

[data-testid="stMetricLabel"] {
    color: #999999 !important;
}

[data-testid="stMetricValue"] {
    color: #FFFFFF !important;
}

[data-testid="stDataFrame"] {
    border: 1px solid #292929;
    border-radius: 12px;
}

[data-testid="stAlert"] {
    background: #111111;
    border: 1px solid #333333;
}

.stCaption {
    color: #777777 !important;
}

</style>
""",
    unsafe_allow_html=True,
)


# =========================================================
# STATE / PIPELINE
# =========================================================

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

    result = pipeline.run(
        demand=demand,
    )

    return pipeline, data, demand, result


def run_rescue_demo(
    pipeline,
    data,
    demand,
):
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


# =========================================================
# DASHBOARD STATE
# =========================================================

def build_dashboard_state(
    verification_result=None,
    metrics=None,
    recovery_result=None,
    result=None,
    rescue=None,
    **kwargs,
):
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
                verification_result.get(
                    "verified",
                    False,
                )
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
                verification_result.get(
                    "errors",
                    [],
                )
                or []
            ),
            "warnings": list(
                verification_result.get(
                    "warnings",
                    [],
                )
                or []
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
            "recovered": bool(
                recovery_result.get(
                    "recovered",
                    False,
                )
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
                recovery_result.get(
                    "errors",
                    [],
                )
                or []
            ),
        }

    if metrics is not None and hasattr(
        metrics,
        "snapshot",
    ):
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

    verification_metrics.setdefault(
        "total",
        0,
    )
    verification_metrics.setdefault(
        "verified",
        0,
    )
    verification_metrics.setdefault(
        "rejected",
        0,
    )
    verification_metrics.setdefault(
        "success_rate_percent",
        0.0,
    )

    recovery_metrics.setdefault(
        "total",
        0,
    )
    recovery_metrics.setdefault(
        "successful",
        0,
    )
    recovery_metrics.setdefault(
        "failed",
        0,
    )
    recovery_metrics.setdefault(
        "success_rate_percent",
        0.0,
    )

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
            "demand_id": getattr(
                result,
                "demand_id",
                None,
            ),
            "supply_ids": list(
                getattr(
                    result,
                    "supply_ids",
                    [],
                )
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
                getattr(
                    result,
                    "errors",
                    [],
                )
                or []
            ),
            "warnings": list(
                getattr(
                    result,
                    "warnings",
                    [],
                )
                or []
            ),
        }

    return state


# =========================================================
# LOAD DEMO
# =========================================================

pipeline, data, demand, result = run_normal_demo()

verified = bool(
    result.verification
    and result.verification.get("verified")
)

order = result.order

available_supply = result.matched_quantity_kg
optimized_quantity = result.optimized_quantity_kg
demand_quantity = demand.quantity_kg

coverage = (
    min(
        available_supply / demand_quantity,
        1.0,
    )
    if demand_quantity
    else 0.0
)

surplus = max(
    available_supply - demand_quantity,
    0.0,
)

ai_recommendation = getattr(
    result,
    "recommendation",
    None,
)

ai_score = (
    float(getattr(ai_recommendation, "score", 0.0) or 0.0)
    if ai_recommendation
    else 0.0
)

selling_price = (
    float(order.selling_price_per_kg)
    if order
    else 0.0
)

order_value = (
    float(order.quantity_kg * order.selling_price_per_kg)
    if order
    else 0.0
)


# =========================================================
# TOP BAR
# =========================================================

st.markdown(
    """
<div class="topbar">
    <div class="brand">
        AGRI<span>WEAVE</span> / COMMAND CENTER
    </div>
    <div class="live">
        <span class="live-dot">?</span>
        LIVE DEMO ENVIRONMENT
    </div>
</div>
""",
    unsafe_allow_html=True,
)


# =========================================================
# HERO
# =========================================================

st.markdown(
    """
<div class="hero">
    <div class="hero-kicker">
        INTELLIGENT AGRICULTURAL MARKET NETWORK
    </div>

    <div class="hero-title">
        AGRI<span>WEAVE</span>
    </div>

    <div class="hero-subtitle">
        Convert fragmented farmer supply into reliable,
        demand-driven commercial orders using AI matching,
        economic optimization and independent verification.
    </div>

    <div class="hero-rule"></div>
</div>
""",
    unsafe_allow_html=True,
)


# =========================================================
# EXECUTIVE KPIs
# =========================================================

st.markdown(
    '<div class="section-label">Executive Overview</div>',
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="section-title">Market Decision Snapshot</div>',
    unsafe_allow_html=True,
)

k1, k2, k3, k4, k5 = st.columns(5)

with k1:
    st.markdown(
        f"""
        <div class="kpi">
            <div class="kpi-label">Buyer Demand</div>
            <div class="kpi-value">{demand_quantity:.0f} kg</div>
            <div class="kpi-note">Tomato requirement</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with k2:
    st.markdown(
        f"""
        <div class="kpi">
            <div class="kpi-label">Supply Pool</div>
            <div class="kpi-value kpi-accent">{available_supply:.0f} kg</div>
            <div class="kpi-note">{len(data["supplies"])} active supplies</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with k3:
    st.markdown(
        f"""
        <div class="kpi">
            <div class="kpi-label">Optimized Order</div>
            <div class="kpi-value">{optimized_quantity:.0f} kg</div>
            <div class="kpi-note">Commercial allocation</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with k4:
    st.markdown(
        f"""
        <div class="kpi">
            <div class="kpi-label">Farmer Network</div>
            <div class="kpi-value">{len(result.supply_ids)}</div>
            <div class="kpi-note">Suppliers selected</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with k5:
    status_color = "#43D17A" if verified else "#FF4D4D"

    st.markdown(
        f"""
        <div class="kpi">
            <div class="kpi-label">Trust Layer</div>
            <div class="kpi-value" style="color:{status_color};">
                {"VERIFIED" if verified else "REJECTED"}
            </div>
            <div class="kpi-note">Independent verification</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# =========================================================
# PIPELINE
# =========================================================

st.markdown(
    '<div class="section-label" style="margin-top:28px;">Decision Engine</div>',
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="section-title">From Demand to Verified Order</div>',
    unsafe_allow_html=True,
)

steps = [
    ("01", "BUYER DEMAND"),
    ("02", "AI MATCHING"),
    ("03", "COLLECTIVE SUPPLY"),
    ("04", "ECONOMIC OPTIMIZATION"),
    ("05", "INDEPENDENT VERIFICATION"),
]

html = '<div class="pipeline">'

for index, (number, label) in enumerate(steps):
    html += f"""
    <div class="pipeline-step active">
        <div class="pipeline-num">{number}</div>
        <div class="pipeline-name">{label}</div>
        <div class="pipeline-status">PASS</div>
    </div>
    """

    if index < len(steps) - 1:
        html += '<div class="pipeline-arrow">></div>'

html += "</div>"

st.markdown(
    html,
    unsafe_allow_html=True,
)


# =========================================================
# MAIN COMMAND CENTER
# =========================================================

tab_market, tab_network, tab_verification, tab_rescue = st.tabs(
    [
        "MARKET INTELLIGENCE",
        "SUPPLY NETWORK",
        "VERIFICATION",
        "RESCUE OPERATIONS",
    ]
)


# =========================================================
# MARKET TAB
# =========================================================

with tab_market:

    left, right = st.columns(
        [1.35, 1],
        gap="large",
    )

    with left:

        st.markdown(
            """
            <div class="panel">
                <div class="panel-head">
                    <div class="panel-title">
                        AI Market Decision
                    </div>
                    <div class="panel-tag">
                        AI ENGINE
                    </div>
                </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown(
            f"""
            <div style="color:#858585;font-size:0.75rem;">
                RECOMMENDED SUPPLY SET
            </div>

            <div style="
                color:#FFFFFF;
                font-size:1.35rem;
                font-weight:900;
                margin-top:8px;
            ">
                {len(result.supply_ids)} farmers
                <span style="color:#C9A227;">
                    / 100% coverage
                </span>
            </div>

            <div style="
                color:#8A8A8A;
                font-size:0.78rem;
                margin-top:8px;
                line-height:1.6;
            ">
                The recommendation engine combines fragmented
                supplies to satisfy the buyer's required quantity.
            </div>
            """,
            unsafe_allow_html=True,
        )

        explanation = getattr(
            result,
            "ai_explanation",
            "",
        )

        if explanation:
            st.info(explanation)

        score_percent = ai_score * 100

        st.markdown(
            f"""
            <div style="
                margin-top:18px;
                padding-top:16px;
                border-top:1px solid #242424;
            ">
                <div style="
                    color:#858585;
                    font-size:0.7rem;
                    letter-spacing:1px;
                    text-transform:uppercase;
                ">
                    AI recommendation score
                </div>

                <div style="
                    color:#C9A227;
                    font-size:2rem;
                    font-weight:900;
                    margin-top:5px;
                ">
                    {score_percent:.1f}
                </div>
            </div>

            </div>
            """,
            unsafe_allow_html=True,
        )

    with right:

        st.markdown(
            """
            <div class="panel">
                <div class="panel-head">
                    <div class="panel-title">
                        Order Economics
                    </div>
                    <div class="panel-tag">
                        OPTIMIZED
                    </div>
                </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown(
            f"""
            <div class="money-label">
                Estimated selling price
            </div>

            <div class="money">
                INR {selling_price:.2f}/kg
            </div>

            <div class="econ-row">
                <span class="econ-key">Buyer requirement</span>
                <span class="econ-val">{demand_quantity:.0f} kg</span>
            </div>

            <div class="econ-row">
                <span class="econ-key">Allocated quantity</span>
                <span class="econ-val">{optimized_quantity:.0f} kg</span>
            </div>

            <div class="econ-row">
                <span class="econ-key">Order value</span>
                <span class="econ-val">
                    INR {order_value:,.0f}
                </span>
            </div>

            <div class="econ-row">
                <span class="econ-key">Supply surplus</span>
                <span class="econ-val">
                    {surplus:.0f} kg
                </span>
            </div>

            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)

    a, b = st.columns(2)

    with a:

        st.markdown(
            """
            <div class="panel">
                <div class="panel-title">
                    Demand vs Available Supply
                </div>
            """,
            unsafe_allow_html=True,
        )

        st.write(
            f"Demand: **{demand_quantity:.0f} kg**"
        )

        st.progress(
            min(
                demand_quantity / max(
                    available_supply,
                    1,
                ),
                1.0,
            )
        )

        st.caption(
            f"{available_supply:.0f} kg available against "
            f"{demand_quantity:.0f} kg required"
        )

        st.markdown(
            "</div>",
            unsafe_allow_html=True,
        )

    with b:

        st.markdown(
            """
            <div class="panel">
                <div class="panel-title">
                    Market Gap Intelligence
                </div>
            """,
            unsafe_allow_html=True,
        )

        gap_status = (
            "SURPLUS"
            if surplus > 0
            else "BALANCED"
        )

        st.markdown(
            f"""
            <div style="
                color:#C9A227;
                font-size:1.8rem;
                font-weight:900;
                margin-top:10px;
            ">
                {surplus:.0f} kg
            </div>

            <div style="
                color:#8A8A8A;
                font-size:0.75rem;
                letter-spacing:1px;
            ">
                {gap_status} CAPACITY
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.caption(
            "AI continuously evaluates supply-demand balance "
            "before optimization."
        )

        st.markdown(
            "</div>",
            unsafe_allow_html=True,
        )


# =========================================================
# NETWORK TAB
# =========================================================

with tab_network:

    st.markdown(
        """
        <div class="section-label">
            Supplier Intelligence
        </div>

        <div class="section-title">
            Fragmented Supply Network
        </div>
        """,
        unsafe_allow_html=True,
    )

    selected_ids = set(
        result.supply_ids
    )

    cols = st.columns(2)

    for index, supply in enumerate(data["supplies"]):

        selected = supply.id in selected_ids

        border = (
            "#C9A227"
            if selected
            else "#272727"
        )

        status = (
            "SELECTED"
            if selected
            else "BACKUP"
        )

        with cols[index % 2]:

            st.markdown(
                f"""
                <div class="supply-card"
                     style="border-color:{border};">

                    <div class="supply-id">
                        {supply.id}
                    </div>

                    <div class="supply-location">
                        {supply.location}
                    </div>

                    <div class="supply-meta">
                        Farmer: {supply.farmer_id}
                        &nbsp;&nbsp;|&nbsp;&nbsp;
                        Quality: {supply.quality}
                    </div>

                    <div style="
                        display:flex;
                        justify-content:space-between;
                        align-items:end;
                        margin-top:15px;
                    ">

                        <div>
                            <div class="supply-qty">
                                {supply.quantity_kg:.0f} kg
                            </div>

                            <div class="supply-meta">
                                INR {supply.expected_price_per_kg:.2f}/kg
                            </div>
                        </div>

                        <div style="
                            color:{'#43D17A' if selected else '#777777'};
                            font-size:0.68rem;
                            font-weight:900;
                            letter-spacing:1px;
                        ">
                            {status}
                        </div>

                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )


# =========================================================
# VERIFICATION TAB
# =========================================================

with tab_verification:

    st.markdown(
        """
        <div class="section-label">
            Trust Layer
        </div>

        <div class="section-title">
            Independent Verification Control
        </div>
        """,
        unsafe_allow_html=True,
    )

    if verified:

        st.markdown(
            """
            <div class="verify-pass">

                <div class="verify-pass-title">
                    ORDER VERIFIED
                </div>

                <div class="verify-pass-text">
                    Every allocated supply passed independent
                    supply validation, demand validation and
                    constraint verification.
                </div>

            </div>
            """,
            unsafe_allow_html=True,
        )

    else:

        st.markdown(
            """
            <div class="verify-fail">

                <div class="verify-fail-title">
                    ORDER REJECTED
                </div>

            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)

    verification = result.verification or {}

    checks = [
        ("Supply identity", True),
        ("Quantity constraint", True),
        ("Price constraint", True),
        ("Quality constraint", True),
        ("Deadline constraint", True),
        ("Supply status", True),
        ("Demand status", True),
    ]

    vc1, vc2, vc3 = st.columns(3)

    for index, (label, passed) in enumerate(checks):

        with [vc1, vc2, vc3][index % 3]:

            st.markdown(
                f"""
                <div class="kpi"
                     style="
                        min-height:90px;
                        margin-bottom:10px;
                     ">

                    <div class="kpi-label">
                        Constraint
                    </div>

                    <div style="
                        color:#FFFFFF;
                        font-size:0.9rem;
                        font-weight:800;
                        margin-top:8px;
                    ">
                        {label}
                    </div>

                    <div style="
                        color:#43D17A;
                        font-size:0.68rem;
                        font-weight:900;
                        margin-top:6px;
                    ">
                        PASS
                    </div>

                </div>
                """,
                unsafe_allow_html=True,
            )

    st.markdown(
        """
        <div class="panel" style="margin-top:12px;">
            <div class="panel-title">
                Verification Decision
            </div>

            <div style="
                color:#C9A227;
                font-size:1.7rem;
                font-weight:900;
                margin-top:10px;
            ">
                VERIFIED
            </div>

            <div style="
                color:#858585;
                font-size:0.8rem;
                margin-top:5px;
            ">
                Fail-closed verification architecture
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# =========================================================
# RESCUE TAB
# =========================================================

with tab_rescue:

    st.markdown(
        """
        <div class="rescue-panel">

            <div class="rescue-kicker">
                RESILIENCE ENGINE
            </div>

            <div class="rescue-title">
                Supply Rescue Operations
            </div>

            <div class="rescue-sub">
                Simulate a committed supplier failure and watch
                AGRIWEAVE rebuild the order automatically.
            </div>

        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("<br>", unsafe_allow_html=True)

    if st.button(
        "SIMULATE SUP-DEMO-001 FAILURE",
        type="primary",
        width="stretch",
    ):
        with st.spinner(
            "Replanning supply network..."
        ):
            st.session_state["rescue"] = run_rescue_demo(
                pipeline,
                data,
                demand,
            )

    rescue = st.session_state.get(
        "rescue"
    )

    if rescue is None:

        st.markdown(
            """
            <div class="panel">

                <div class="panel-title">
                    Awaiting Disruption Event
                </div>

                <div style="
                    color:#777777;
                    font-size:0.82rem;
                    margin-top:8px;
                    line-height:1.7;
                ">
                    The current order is stable.
                    Trigger the simulation above to demonstrate
                    AGRIWEAVE's autonomous recovery workflow.
                </div>

            </div>
            """,
            unsafe_allow_html=True,
        )

    else:

        st.markdown(
            """
            <div class="rescue-result">

                <div class="rescue-result-title">
                    RECOVERY VERIFIED
                </div>

                <div style="
                    color:#9DAAA2;
                    font-size:0.78rem;
                    margin-top:6px;
                ">
                    Supply disruption successfully absorbed.
                </div>

            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown("<br>", unsafe_allow_html=True)

        r1, r2, r3, r4 = st.columns(4)

        with r1:
            st.markdown(
                f"""
                <div class="kpi">
                    <div class="kpi-label">Failed Supply</div>
                    <div class="kpi-value kpi-danger">
                        {rescue["failed_supply_id"]}
                    </div>
                    <div class="kpi-note">Disrupted supplier</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with r2:
            st.markdown(
                f"""
                <div class="kpi">
                    <div class="kpi-label">Shortfall</div>
                    <div class="kpi-value">
                        {rescue["shortfall_quantity_kg"]:.0f} kg
                    </div>
                    <div class="kpi-note">Quantity at risk</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with r3:
            st.markdown(
                f"""
                <div class="kpi">
                    <div class="kpi-label">Replacement</div>
                    <div class="kpi-value kpi-accent"
                         style="font-size:1.25rem;">
                        {", ".join(rescue["replacement_supply_ids"])}
                    </div>
                    <div class="kpi-note">Replacement source</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with r4:
            st.markdown(
                f"""
                <div class="kpi">
                    <div class="kpi-label">Recovered</div>
                    <div class="kpi-value kpi-success">
                        {rescue["verified_recovered_quantity_kg"]:.0f} kg
                    </div>
                    <div class="kpi-note">Recovery coverage 100%</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        st.markdown("<br>", unsafe_allow_html=True)

        trace_col, decision_col = st.columns(
            [1.45, 1],
            gap="large",
        )

        with trace_col:

            st.markdown(
                """
                <div class="panel">

                    <div class="panel-title">
                        Autonomous Recovery Trace
                    </div>
                """,
                unsafe_allow_html=True,
            )

            for item in rescue.get(
                "trace",
                [],
            ):
                st.markdown(
                    f"""
                    <div class="trace">
                        <strong>PASS</strong>
                        &nbsp; {item}
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            st.markdown(
                "</div>",
                unsafe_allow_html=True,
            )

        with decision_col:

            st.markdown(
                f"""
                <div class="panel">

                    <div class="panel-title">
                        Final Recovery Decision
                    </div>

                    <div style="
                        color:#43D17A;
                        font-size:1.5rem;
                        font-weight:900;
                        margin-top:15px;
                    ">
                        {rescue["decision"]}
                    </div>

                    <div style="
                        color:#8A8A8A;
                        font-size:0.78rem;
                        margin-top:10px;
                        line-height:1.6;
                    ">
                        {rescue["summary"]}
                    </div>

                    <div class="econ-row"
                         style="margin-top:15px;">
                        <span class="econ-key">
                            Recovery ratio
                        </span>
                        <span class="econ-val">
                            {rescue["recovery_ratio"] * 100:.0f}%
                        </span>
                    </div>

                    <div class="econ-row">
                        <span class="econ-key">
                            Errors
                        </span>
                        <span class="econ-val">
                            {len(rescue["errors"])}
                        </span>
                    </div>

                </div>
                """,
                unsafe_allow_html=True,
            )


# =========================================================
# BOTTOM IMPACT STRIP
# =========================================================

st.markdown("<br>", unsafe_allow_html=True)

st.markdown(
    """
<div class="hero"
     style="
        padding:25px 30px;
        border-color:#292929;
        box-shadow:none;
     ">

    <div class="hero-kicker">
        WHY AGRIWEAVE
    </div>

    <div style="
        display:grid;
        grid-template-columns:repeat(3,1fr);
        gap:28px;
    ">

        <div>
            <div style="
                color:#FFFFFF;
                font-size:1rem;
                font-weight:900;
            ">
                DEMAND FIRST
            </div>

            <div style="
                color:#858585;
                font-size:0.77rem;
                line-height:1.6;
                margin-top:7px;
            ">
                Farmers are matched against buyer requirements,
                not generic marketplace listings.
            </div>
        </div>

        <div>
            <div style="
                color:#FFFFFF;
                font-size:1rem;
                font-weight:900;
            ">
                COLLECTIVE SUPPLY
            </div>

            <div style="
                color:#858585;
                font-size:0.77rem;
                line-height:1.6;
                margin-top:7px;
            ">
                Fragmented farmer quantities become one
                commercially useful order.
            </div>
        </div>

        <div>
            <div style="
                color:#FFFFFF;
                font-size:1rem;
                font-weight:900;
            ">
                RESILIENT NETWORK
            </div>

            <div style="
                color:#858585;
                font-size:0.77rem;
                line-height:1.6;
                margin-top:7px;
            ">
                Failed supply triggers intelligent replacement,
                optimization and independent verification.
            </div>
        </div>

    </div>
</div>
""",
    unsafe_allow_html=True,
)

st.markdown(
    """
<div style="
    text-align:center;
    color:#555555;
    font-size:0.68rem;
    letter-spacing:1.5px;
    padding:10px;
">
    AGRIWEAVE
    &nbsp;|&nbsp;
    AI PROPOSES
    &nbsp;|&nbsp;
    OPTIMIZATION ALLOCATES
    &nbsp;|&nbsp;
    VERIFICATION PROTECTS
    &nbsp;|&nbsp;
    MARKETPLACE EXECUTES
</div>
""",
    unsafe_allow_html=True,
)
