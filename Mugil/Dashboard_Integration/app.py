
import json
import sys
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components


ROOT = Path(__file__).resolve().parents[2]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


from Disha.Marketplace_Data_Logistics.api import MarketplaceService
from Disha.Marketplace_Data_Logistics.database import Database
from integration.agriweave_pipeline import AgriweavePipeline


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="PS 1.2 | Direct Market-Access Platform",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="collapsed",
)


# ============================================================
# STREAMLIT CONTROL CSS
# ============================================================

st.markdown(
    """
<style>

.stApp {
    background: #050505;
}

.block-container {
    max-width: 1550px;
    padding-top: 0.5rem;
    padding-bottom: 2rem;
}

.stButton > button {
    width: 100%;
    min-height: 52px;

    background:
        linear-gradient(
            90deg,
            #8f101f,
            #d21f38
        );

    color: white !important;

    border: 1px solid #ff3048 !important;
    border-radius: 11px !important;

    font-weight: 900 !important;
    letter-spacing: 1px !important;

    box-shadow:
        0 0 25px rgba(255,48,72,.12);

    transition: all .2s ease;
}

.stButton > button:hover {
    background:
        linear-gradient(
            90deg,
            #b9152b,
            #ff3048
        );

    border-color: #d8aa32 !important;

    box-shadow:
        0 0 35px rgba(255,48,72,.22);
}

[data-testid="stHeader"] {
    background: rgba(5,5,5,.92);
}

footer {
    display: none;
}

</style>
""",
    unsafe_allow_html=True,
)


# ============================================================
# DASHBOARD STATE CONTRACT
# KEEPING EXISTING TEST CONTRACT
# ============================================================

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


    if (
        metrics is not None
        and hasattr(metrics, "snapshot")
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


# ============================================================
# PIPELINE
# ============================================================

@st.cache_resource
def get_pipeline():

    marketplace = MarketplaceService(
        database=Database(
            "integration_demo.db"
        )
    )

    return AgriweavePipeline(
        marketplace=marketplace,
        dry_run=True,
    )


def run_normal_demo():

    pipeline = get_pipeline()

    data = pipeline.get_market_data(
        crop="Tomato"
    )

    demand = data["demands"][0]

    result = pipeline.run(
        demand=demand
    )

    return (
        pipeline,
        data,
        demand,
        result,
    )


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


# ============================================================
# BUILD FRONTEND PAYLOAD
# ============================================================

def build_payload(
    pipeline,
    data,
    demand,
    result,
    rescue=None,
):

    order = result.order

    demand_quantity = float(
        demand.quantity_kg
    )

    available_supply = float(
        result.matched_quantity_kg
    )

    optimized_quantity = float(
        result.optimized_quantity_kg
    )

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

    recommendation = getattr(
        result,
        "recommendation",
        None,
    )

    ai_score = (
        float(
            getattr(
                recommendation,
                "score",
                0.0,
            )
            or 0.0
        )
        if recommendation
        else 0.0
    )

    explanation = getattr(
        result,
        "ai_explanation",
        "",
    )

    selling_price = (
        float(
            order.selling_price_per_kg
        )
        if order
        else 0.0
    )

    order_value = (
        float(
            order.quantity_kg
            * order.selling_price_per_kg
        )
        if order
        else 0.0
    )


    supplies = []

    for supply in data["supplies"]:

        supplies.append(
            {
                "id": supply.id,
                "farmer_id": supply.farmer_id,
                "location": supply.location,
                "quantity": float(
                    supply.quantity_kg
                ),
                "price": float(
                    supply.expected_price_per_kg
                ),
                "quality": supply.quality,
                "status": supply.status,
            }
        )


    payload = {
        "demand_quantity": demand_quantity,

        "available_supply": available_supply,

        "optimized_quantity": optimized_quantity,

        "farmer_count": len(
            result.supply_ids
        ),

        "verified": bool(
            result.verification
            and result.verification.get(
                "verified"
            )
        ),

        "selected_ids": list(
            result.supply_ids
        ),

        "ai_score": ai_score,

        "explanation": explanation,

        "selling_price": selling_price,

        "order_value": order_value,

        "surplus": surplus,

        "coverage": coverage,

        "supplies": supplies,

        "rescue": rescue,
    }

    return payload


# ============================================================
# RENDER HTML
# ============================================================

def render_command_center(payload):

    template_path = (
        Path(__file__).resolve().parent
        / "assets"
        / "command_center.html"
    )

    template = template_path.read_text(
        encoding="utf-8"
    )

    payload_json = json.dumps(
        payload,
        ensure_ascii=False,
    )

    payload_json = payload_json.replace(
        "</",
        "<\\/",
    )

    html = template.replace(
        "__PAYLOAD__",
        payload_json,
    )

    components.html(
        html,
        height=1850,
        scrolling=True,
    )


# ============================================================
# RUN
# ============================================================

pipeline, data, demand, result = (
    run_normal_demo()
)


# ============================================================
# RESCUE CONTROL
# ============================================================

st.markdown(
    """
<div style="
    max-width:1550px;
    margin:0 auto;
    padding:0 4px 10px 4px;
">
""",
    unsafe_allow_html=True,
)


rescue = st.session_state.get(
    "agriweave_rescue"
)


if st.button(
    "SIMULATE SUP-DEMO-001 FAILURE",
    type="primary",
    width="stretch",
):

    with st.spinner(
        "AI recovery engine is replanning the supply network..."
    ):

        rescue = run_rescue_demo(
            pipeline,
            data,
            demand,
        )

        st.session_state[
            "agriweave_rescue"
        ] = rescue


st.markdown(
    "</div>",
    unsafe_allow_html=True,
)


# ============================================================
# RENDER
# ============================================================

payload = build_payload(
    pipeline=pipeline,
    data=data,
    demand=demand,
    result=result,
    rescue=rescue,
)

render_command_center(
    payload
)
