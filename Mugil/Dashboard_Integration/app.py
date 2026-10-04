"""
AGRIWEAVE - Judge Ready Command Center

Clean rebuild of the Streamlit dashboard:
- No custom HTML is rendered with st.markdown outside <style>.
- All rich HTML/CSS/JS is rendered with components.html().
- The pipeline is loaded directly from the project file to avoid
  the previous Streamlit import-path collision.
- Supply Rescue calls the real AGRIWEAVE recovery pipeline.
- build_dashboard_state() keeps the existing test contract.
"""

from __future__ import annotations

import importlib.util
import sys
import textwrap
from pathlib import Path
from typing import Any


# ============================================================
# PROJECT ROOT / SAFE IMPORT PATH
# ============================================================

ROOT = Path(__file__).resolve().parents[2]

if str(ROOT) in sys.path:
    sys.path.remove(str(ROOT))

sys.path.insert(0, str(ROOT))


# ============================================================
# EXISTING TEST CONTRACT
# ============================================================

def build_dashboard_state(
    verification_result=None,
    metrics=None,
    recovery_result=None,
    result=None,
    rescue=None,
    **kwargs,
):
    """Build the stable dashboard state consumed by tests."""

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
            "summary": (
                "No recovery operation has been triggered."
            ),
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
        snapshot = metrics.snapshot()
    else:
        snapshot = {
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
        snapshot.get(
            "verification",
            {},
        )
    )

    recovery_metrics = dict(
        snapshot.get(
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
# GENERIC VALUE HELPERS
# ============================================================

def value(obj: Any, key: str, default=None):
    if isinstance(obj, dict):
        return obj.get(key, default)

    return getattr(
        obj,
        key,
        default,
    )


def as_float(value_: Any, default: float = 0.0) -> float:
    try:
        number = float(value_)
        if number != number:
            return default
        return number
    except (TypeError, ValueError):
        return default


def escape_js_string(text_: Any) -> str:
    text_ = str(text_ or "")
    return (
        text_
        .replace("\\", "\\\\")
        .replace("`", "\\`")
        .replace("${", "\\${")
    )


# ============================================================
# LOAD PIPELINE DIRECTLY
# ============================================================

def load_pipeline_class():
    """
    Load integration/agriweave_pipeline.py directly.

    This avoids the previous Streamlit error:
        "'integration' is not a package"
    """

    pipeline_path = (
        ROOT
        / "integration"
        / "agriweave_pipeline.py"
    )

    if not pipeline_path.exists():
        raise FileNotFoundError(
            f"Pipeline not found: {pipeline_path}"
        )

    module_name = (
        "agriweave_pipeline_dashboard_runtime"
    )

    existing = sys.modules.get(module_name)

    if existing is not None:
        return existing.AgriweavePipeline

    spec = importlib.util.spec_from_file_location(
        module_name,
        pipeline_path,
    )

    if spec is None or spec.loader is None:
        raise ImportError(
            f"Could not load pipeline: {pipeline_path}"
        )

    module = importlib.util.module_from_spec(spec)

    sys.modules[module_name] = module

    spec.loader.exec_module(module)

    return module.AgriweavePipeline


# ============================================================
# PIPELINE SETUP
# ============================================================

def create_pipeline():
    from Disha.Marketplace_Data_Logistics.api import (
        MarketplaceService,
    )
    from Disha.Marketplace_Data_Logistics.database import (
        Database,
    )

    AgriweavePipeline = load_pipeline_class()

    marketplace = MarketplaceService(
        database=Database(
            str(
                ROOT
                / "integration_demo.db"
            )
        )
    )

    return AgriweavePipeline(
        marketplace=marketplace,
        dry_run=True,
    )


# ============================================================
# STREAMLIT UI
# ============================================================

def main():

    import streamlit as st
    import streamlit.components.v1 as components

    st.set_page_config(
        page_title=(
            "Direct Market-Access Platform for Marginal Farmers"
        ),
        page_icon="A",
        layout="wide",
        initial_sidebar_state="collapsed",
    )

    # --------------------------------------------------------
    # Minimal global CSS.
    #
    # IMPORTANT:
    # Rich HTML below is NEVER sent through st.markdown().
    # --------------------------------------------------------

    global_css = """
    <style>

    .stApp {
        background:
            radial-gradient(
                circle at 18% 4%,
                rgba(255,40,50,.055),
                transparent 32%
            ),
            radial-gradient(
                circle at 82% 25%,
                rgba(255,184,38,.035),
                transparent 30%
            ),
            #030405;
    }

    .block-container {
        max-width: 1500px;
        padding-top: 1rem;
        padding-bottom: 3rem;
    }

    [data-testid="stMetric"] {
        background:
            linear-gradient(
                145deg,
                #090b10,
                #0c0f15
            );
        border:
            1px solid #272c35;
        border-radius: 14px;
        padding: 14px;
    }

    [data-testid="stMetricLabel"] {
        color: #7f8793;
        font-size: 1.05rem;
    }

    [data-testid="stMetricValue"] {
        color: #ffffff;
        font-size: 2.15rem;
    }


    /* Recovery decision trace */
    [data-testid="stExpander"] {
        border: 1px solid #4a2930 !important;
        border-radius: 14px !important;
        animation: tracePulse 3.4s ease-in-out infinite;
    }

    [data-testid="stExpander"] summary {
        color: #ffc238 !important;
        font-size: 1.15rem !important;
        font-weight: 1000 !important;
        letter-spacing: 1px;
    }

    [data-testid="stExpander"] [data-testid="stMarkdownContainer"] p {
        color: #ffbd7d !important;
        font-size: 1.12rem !important;
        font-weight: 900 !important;
        line-height: 1.7 !important;
    }

    @keyframes tracePulse {
        0%,100% {
            box-shadow: 0 0 0 rgba(255,55,45,0);
        }
        50% {
            box-shadow: 0 0 26px rgba(255,55,45,.13);
        }
    }

    .stButton > button {
        width: 100%;
        min-height: 56px;
        border-radius: 12px;
        border: 1px solid #ff4d4d;
        background:
            linear-gradient(
                135deg,
                #8f1319,
                #d72b31
            );
        color: #ffffff;
        font-weight: 900;
        letter-spacing: 2px;
        box-shadow:
            0 0 20px
            rgba(255,45,45,.16);
    }

    .stButton > button:hover {
        border-color: #ffc02e;
        background:
            linear-gradient(
                135deg,
                #bb2027,
                #f23b31
            );
        color: #ffffff;
        transform: translateY(-1px);
    }

    </style>
    """

    st.markdown(
        textwrap.dedent(global_css),
        unsafe_allow_html=True,
    )

    # --------------------------------------------------------
    # Backend
    # --------------------------------------------------------

    backend_error = None

    try:
        pipeline = create_pipeline()

        data = pipeline.get_market_data(
            crop="Tomato"
        )

        demands = data.get(
            "demands",
            [],
        )

        if not demands:
            raise RuntimeError(
                "No open Tomato demand exists."
            )

        demand = demands[0]

        result = pipeline.run(
            demand=demand
        )

    except Exception as exc:
        pipeline = None
        data = {
            "supplies": [],
            "demands": [],
        }
        demand = None
        result = None
        backend_error = (
            f"{type(exc).__name__}: {exc}"
        )

    # --------------------------------------------------------
    # Normal values
    # --------------------------------------------------------

    demand_kg = as_float(
        value(
            demand,
            "quantity_kg",
            500,
        ),
        500,
    )

    matched_kg = as_float(
        value(
            result,
            "matched_quantity_kg",
            550,
        ),
        550,
    )

    optimized_kg = as_float(
        value(
            result,
            "optimized_quantity_kg",
            500,
        ),
        500,
    )

    supply_ids = list(
        value(
            result,
            "supply_ids",
            [],
        )
        or []
    )

    verification = (
        value(
            result,
            "verification",
            {},
        )
        or {}
    )

    verified = bool(
        verification.get(
            "verified",
            False,
        )
    )

    verification_label = (
        "VERIFIED"
        if verified
        else "REVIEW"
    )

    surplus_kg = max(
        0.0,
        matched_kg - demand_kg,
    )

    # --------------------------------------------------------
    # Hero / whole command center
    # --------------------------------------------------------

    visual = f"""
<!doctype html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport"
      content="width=device-width,initial-scale=1">

<style>

:root {{
    --red:#ff3038;
    --red2:#ff5b43;
    --gold:#ffc238;
    --gold2:#ffe189;
    --green:#3dffa4;
    --blue:#54a8ff;
    --panel:rgba(7,9,13,.88);
    --line:rgba(255,190,40,.20);
}}

* {{
    box-sizing:border-box;
}}

html,
body {{
    margin:0;
    padding:0;
    width:100%;
    min-height:100%;
    overflow-x:hidden;
    background:#030405;
    color:#fff;
    font-family:
        Inter,
        Arial,
        Helvetica,
        sans-serif;
}}

body {{
    padding:10px;
}}

.page {{
    position:relative;
    width:100%;
    min-height:1740px;
    overflow:hidden;
    border-radius:28px;

    background:
        radial-gradient(
            circle at 50% 17%,
            rgba(255,36,35,.11),
            transparent 24%
        ),
        radial-gradient(
            circle at 13% 50%,
            rgba(255,181,38,.035),
            transparent 24%
        ),
        linear-gradient(
            180deg,
            #050607 0%,
            #09080a 35%,
            #030405 100%
        );

    border:
        1px solid rgba(255,180,40,.24);

    box-shadow:
        inset 0 0 130px
        rgba(255,20,20,.035);
}}

#stars {{
    position:absolute;
    inset:0;
    width:100%;
    height:100%;
    z-index:0;
}}

.topbar {{
    position:absolute;
    top:27px;
    left:34px;
    right:34px;
    display:flex;
    align-items:center;
    justify-content:space-between;
    z-index:20;
}}

.brand {{
    font-size:14px;
    font-weight:1000;
    letter-spacing:5px;
}}

.brand .gold {{
    color:var(--gold);
}}

.brand .red {{
    color:var(--red);
}}

.live {{
    display:flex;
    align-items:center;
    gap:10px;
    color:var(--green);
    font-size:9px;
    font-weight:900;
    letter-spacing:3px;
}}

.live-dot {{
    width:9px;
    height:9px;
    border-radius:50%;
    background:var(--green);
    box-shadow:
        0 0 8px var(--green),
        0 0 22px var(--green);
    animation:blink 1.4s infinite;
}}

@keyframes blink {{
    50% {{opacity:.25;}}
}}

.hero {{
    position:absolute;
    top:86px;
    left:0;
    right:0;
    text-align:center;
    z-index:15;
}}

.kicker {{
    color:#7b828d;
    font-size:9px;
    font-weight:900;
    letter-spacing:6px;
}}

.h1 {{
    margin-top:20px;
    color:var(--red);
    font-size:clamp(34px,4.1vw,62px);
    line-height:1.02;
    font-weight:1000;
    letter-spacing:2px;
    text-shadow:
        0 0 16px rgba(255,42,42,.42),
        0 0 55px rgba(255,40,30,.10);
}}

.h2 {{
    margin-top:12px;
    color:var(--gold);
    font-size:clamp(16px,1.8vw,27px);
    line-height:1.15;
    font-weight:900;
    letter-spacing:5px;
}}

.description {{
    width:min(920px,82%);
    margin:20px auto 0;
    color:#949aa4;
    font-size:12px;
    line-height:1.7;
}}

.pill {{
    display:inline-block;
    margin-top:18px;
    padding:8px 14px;
    border:1px solid rgba(255,194,56,.30);
    border-radius:999px;
    color:#d5a933;
    background:rgba(9,10,13,.70);
    font-size:10px;
    font-weight:900;
    letter-spacing:3px;
}}

.core-area {{
    position:absolute;
    left:0;
    right:0;
    top:330px;
    height:760px;
    perspective:1500px;
}}

.floor {{
    position:absolute;
    left:-25%;
    right:-25%;
    bottom:-150px;
    height:430px;

    background-image:
        linear-gradient(
            rgba(255,190,48,.085) 1px,
            transparent 1px
        ),
        linear-gradient(
            90deg,
            rgba(255,190,48,.085) 1px,
            transparent 1px
        );

    background-size:46px 46px;

    transform:
        perspective(520px)
        rotateX(63deg);

    transform-origin:center top;

    opacity:.72;

    animation:
        floorMove 5s linear infinite;
}}

@keyframes floorMove {{
    to {{
        background-position:0 46px;
    }}
}}

.halo {{
    position:absolute;
    left:50%;
    top:42%;
    width:440px;
    height:440px;
    transform:translate(-50%,-50%);
    border-radius:50%;
    background:
        radial-gradient(
            circle,
            rgba(255,46,34,.19),
            transparent 65%
        );
    filter:blur(12px);
    animation:halo 4.5s ease-in-out infinite;
}}

@keyframes halo {{
    50% {{
        transform:
            translate(-50%,-50%)
            scale(1.17);
        opacity:.65;
    }}
}}

.system {{
    position:absolute;
    left:50%;
    top:42%;
    width:380px;
    height:380px;
    transform:
        translate(-50%,-50%);
    transform-style:preserve-3d;
}}

.ring {{
    position:absolute;
    left:50%;
    top:50%;
    border-radius:50%;
    transform-style:preserve-3d;
    border:1px solid rgba(255,190,55,.35);
    box-shadow:
        0 0 16px
        rgba(255,170,40,.08);
}}

.ring.r1 {{
    width:330px;
    height:122px;
    margin-left:-165px;
    margin-top:-61px;
    transform:rotateX(67deg);
    animation:ring1 7s linear infinite;
}}

.ring.r2 {{
    width:430px;
    height:164px;
    margin-left:-215px;
    margin-top:-82px;
    transform:rotateY(65deg);
    animation:ring2 10s linear infinite;
}}

.ring.r3 {{
    width:520px;
    height:205px;
    margin-left:-260px;
    margin-top:-102.5px;
    transform:rotateX(64deg) rotateZ(38deg);
    animation:ring3 14s linear infinite;
}}

@keyframes ring1 {{
    to {{
        transform:
            rotateX(67deg)
            rotateZ(360deg);
    }}
}}

@keyframes ring2 {{
    to {{
        transform:
            rotateY(65deg)
            rotateZ(-360deg);
    }}
}}

@keyframes ring3 {{
    to {{
        transform:
            rotateX(64deg)
            rotateZ(398deg);
    }}
}}

.cube {{
    position:absolute;
    left:50%;
    top:50%;
    width:150px;
    height:150px;
    margin-left:-75px;
    margin-top:-75px;
    transform-style:preserve-3d;
    animation:cubeSpin 13s linear infinite;
}}

.face {{
    position:absolute;
    width:150px;
    height:150px;
    display:flex;
    align-items:center;
    justify-content:center;
    border:
        1px solid rgba(255,193,56,.72);
    background:
        linear-gradient(
            145deg,
            rgba(255,44,46,.25),
            rgba(255,192,48,.07)
        );
    box-shadow:
        inset 0 0 40px
        rgba(255,40,35,.14),
        0 0 26px
        rgba(255,80,40,.10);
    backdrop-filter:blur(9px);
    color:white;
    font-size:10px;
    font-weight:1000;
    letter-spacing:3px;
}}

.front {{transform:translateZ(75px);}}
.back {{transform:rotateY(180deg) translateZ(75px);}}
.right {{transform:rotateY(90deg) translateZ(75px);}}
.left {{transform:rotateY(-90deg) translateZ(75px);}}
.top {{transform:rotateX(90deg) translateZ(75px);}}
.bottom {{transform:rotateX(-90deg) translateZ(75px);}}

@keyframes cubeSpin {{
    from {{
        transform:
            rotateX(0deg)
            rotateY(0deg)
            rotateZ(0deg);
    }}
    to {{
        transform:
            rotateX(360deg)
            rotateY(360deg)
            rotateZ(360deg);
    }}
}}

.node {{
    position:absolute;
    min-width:150px;
    padding:15px 17px;
    border-radius:12px;
    border:1px solid rgba(255,182,45,.34);
    background:
        linear-gradient(
            145deg,
            rgba(11,13,18,.94),
            rgba(4,6,9,.90)
        );
    backdrop-filter:blur(12px);
    box-shadow:
        0 0 30px rgba(255,60,35,.08);
    z-index:20;
    animation:float 4s ease-in-out infinite;
}}

.node .eyebrow {{
    color:#6f7682;
    font-size:9px;
    font-weight:900;
    letter-spacing:3px;
}}

.node .big {{
    margin-top:7px;
    color:#ffffff;
    font-size:13px;
    font-weight:1000;
    letter-spacing:2px;
}}

.node.farmer {{
    left:8%;
    top:38%;
}}

.node.buyer {{
    right:8%;
    top:38%;
    animation-delay:.7s;
}}

.node.logistics {{
    left:18%;
    bottom:20%;
    animation-delay:1.5s;
}}

.node.verify {{
    right:18%;
    bottom:20%;
    animation-delay:2.2s;
}}

@keyframes float {{
    50% {{
        transform:translateY(-10px);
    }}
}}

.connector {{
    position:absolute;
    height:1px;
    background:
        linear-gradient(
            90deg,
            transparent,
            rgba(255,60,45,.62),
            transparent
        );
    box-shadow:
        0 0 9px
        rgba(255,55,40,.30);
    transform-origin:left center;
    z-index:8;
    animation:connectorPulse 2.2s ease-in-out infinite;
}}

.line1 {{
    left:19%;
    top:48%;
    width:250px;
    transform:rotate(3deg);
}}

.line2 {{
    right:19%;
    top:48%;
    width:250px;
    transform:rotate(177deg);
    animation-delay:.6s;
}}

.line3 {{
    left:30%;
    top:66%;
    width:170px;
    transform:rotate(-22deg);
    animation-delay:1.1s;
}}

.line4 {{
    right:30%;
    top:66%;
    width:170px;
    transform:rotate(202deg);
    animation-delay:1.6s;
}}

@keyframes connectorPulse {{
    50% {{opacity:.18;}}
}}

.center-status {{
    position:absolute;
    left:50%;
    top:27%;
    transform:translateX(-50%);
    z-index:30;
    padding:7px 13px;
    border:1px solid rgba(255,193,54,.30);
    border-radius:999px;
    background:rgba(4,6,9,.82);
    color:#ffc33d;
    font-size:11px;
    font-weight:1000;
    letter-spacing:3px;
}}

.bottom-metrics {{
    position:absolute;
    left:7%;
    right:7%;
    bottom:25px;
    display:grid;
    grid-template-columns:
        repeat(4,1fr);
    gap:12px;
    z-index:50;
}}

.metric {{
    padding:15px;
    border-radius:12px;
    background:rgba(5,7,10,.87);
    border:
        1px solid rgba(255,255,255,.08);
    backdrop-filter:blur(10px);
    text-align:center;
}}

.metric .label {{
    color:#717884;
    font-size:9px;
    font-weight:900;
    letter-spacing:3px;
}}

.metric .value {{
    margin-top:6px;
    color:white;
    font-size:20px;
    font-weight:1000;
}}

.metric .gold {{
    color:var(--gold);
}}

.metric .green {{
    color:var(--green);
}}

.section {{
    position:absolute;
    left:7%;
    right:7%;
    z-index:50;
}}

.section.pipeline {{
    top:1110px;
}}

.section.network {{
    top:1345px;
}}

.section-title {{
    color:#ffc03a;
    font-size:16px;
    font-weight:1000;
    letter-spacing:4px;
    text-shadow:0 0 14px rgba(255,192,58,.18);
    animation:headingPulse 3s ease-in-out infinite;
}}

.section-sub {{
    margin-top:8px;
    color:#c5cad3;
    font-size:13px;
    font-weight:1000;
}}

@keyframes headingPulse {{
    0%,100% {{ opacity:1; transform:translateX(0); }}
    50% {{ opacity:.76; transform:translateX(2px); }}
}}

.stage-grid {{
    display:grid;
    grid-template-columns:
        repeat(5,1fr);
    gap:11px;
    margin-top:14px;
}}

.stage {{
    min-height:112px;
    padding:17px;
    border-radius:12px;
    background:
        linear-gradient(
            145deg,
            rgba(10,12,17,.94),
            rgba(5,7,10,.92)
        );
    border:
        1px solid rgba(255,190,45,.16);
    box-shadow:
        inset 0 0 30px
        rgba(255,40,30,.025);
    position:relative;
    overflow:hidden;
}}

.stage {{
    animation:stageFloat 4s ease-in-out infinite;
}}

.stage:nth-child(2) {{ animation-delay:.35s; }}
.stage:nth-child(3) {{ animation-delay:.70s; }}
.stage:nth-child(4) {{ animation-delay:1.05s; }}
.stage:nth-child(5) {{ animation-delay:1.40s; }}

.stage::after {{
    content:"";
    position:absolute;
    left:-20%;
    right:-20%;
    top:0;
    height:1px;
    background:
        linear-gradient(
            90deg,
            transparent,
            rgba(255,54,45,.62),
            transparent
        );
    animation:stageScan 2.8s linear infinite;
}}

@keyframes stageScan {{
    from {{transform:translateX(-70%);}}
    to {{transform:translateX(70%);}}
}}

@keyframes stageFloat {{
    0%,100% {{ transform:translateY(0); }}
    50% {{ transform:translateY(-4px); }}
}}

.stage .num {{
    color:#ffb52f;
    font-size:12px;
    font-weight:1000;
    letter-spacing:3px;
}}

.stage .name {{
    margin-top:10px;
    color:white;
    font-size:15px;
    font-weight:1000;
    letter-spacing:.4px;
}}

.stage .state {{
    margin-top:10px;
    color:var(--green);
    font-size:10px;
    font-weight:1000;
    letter-spacing:2px;
}}

.network-grid {{
    display:grid;
    grid-template-columns:1.3fr .7fr;
    gap:12px;
    margin-top:14px;
}}

.panel {{
    min-height:170px;
    border:
        1px solid rgba(255,255,255,.08);
    border-radius:14px;
    background:
        linear-gradient(
            145deg,
            rgba(9,11,15,.94),
            rgba(4,6,9,.94)
        );
    padding:18px;
    position:relative;
    overflow:hidden;
}}

.panel-title {{
    color:white;
    font-size:16px;
    font-weight:1000;
    letter-spacing:2px;
}}

.panel-line {{
    margin-top:9px;
    color:#bfc5cf;
    font-size:12px;
    font-weight:900;
}}

.supply-list {{
    margin-top:14px;
    display:grid;
    grid-template-columns:
        repeat(3,1fr);
    gap:8px;
}}

.supply {{
    padding:9px;
    border:
        1px solid rgba(255,185,42,.14);
    border-radius:8px;
    background:#07090d;
}}

.supply .id {{
    color:#ffbd32;
    font-size:7px;
    font-weight:900;
}}

.supply .loc {{
    margin-top:4px;
    color:#ff3038;
    font-size:22px;
    font-weight:1000;
}}

    .supply:nth-child(even) .loc {{
    color:#ffc238;
}}

.supply .qty {{
    margin-top:7px;
    color:#ffffff;
    font-size:13px;
    font-weight:1000;
}}

.big-number {{
    margin-top:18px;
    color:var(--gold);
    font-size:46px;
    line-height:1;
    font-weight:1000;
    text-shadow:0 0 18px rgba(255,194,56,.20);
    animation:signalPulse 2.8s ease-in-out infinite;
}}

.green-number {{
    color:var(--green);
}}

@keyframes signalPulse {{
    0%,100% {{ transform:scale(1); }}
    50% {{ transform:scale(1.035); }}
}}

.mini-label {{
    margin-top:8px;
    color:#929aa6;
    font-size:10px;
    font-weight:900;
    letter-spacing:2px;
}}

.badge-row {{
    display:flex;
    flex-wrap:wrap;
    gap:7px;
    margin-top:15px;
}}

.badge {{
    padding:7px 9px;
    border-radius:8px;
    border:1px solid rgba(255,255,255,.07);
    background:#080a0e;
    color:#9aa1ab;
    font-size:7px;
    font-weight:900;
    letter-spacing:1.5px;
}}

@media(max-width:900px) {{
    .page {{
        min-height:2100px;
    }}

    .main {{
        font-size:34px;
    }}

    .node {{
        transform:scale(.82);
    }}

    .stage-grid {{
        grid-template-columns:
            repeat(2,1fr);
    }}

    .network-grid {{
        grid-template-columns:1fr;
    }}

    .section.pipeline {{
        top:1140px;
    }}

    .section.network {{
        top:1515px;
    }}

    .bottom-metrics {{
        left:5%;
        right:5%;
        grid-template-columns:
            repeat(2,1fr);
    }}
}}

</style>
</head>

<body>

<div class="page">

<canvas id="stars"></canvas>

<div class="topbar">
    <div class="brand">
        DEVHACK 2026
        <span class="gold"> / </span>
        <span class="red">AGRIWEAVE</span>
    </div>

    <div class="live">
        <span class="live-dot"></span>
        SYSTEM ONLINE
    </div>
</div>

<div class="hero">

    <div class="kicker">
        PROBLEM STATEMENT 1.2
    </div>

    <div class="h1">
        DIRECT MARKET-ACCESS
    </div>

    <div class="h2">
        PLATFORM FOR MARGINAL FARMERS
    </div>

    <div class="description">
        A demand-driven market network that converts fragmented
        farmer supply into reliable commercial orders while protecting
        quantity, quality, economics and delivery continuity.
    </div>

    <div class="pill">
        AI MARKET INTELLIGENCE • COLLECTIVE SUPPLY • VERIFIED RECOVERY
    </div>

</div>


<div class="core-area">

    <div class="floor"></div>

    <div class="halo"></div>

    <div class="connector line1"></div>
    <div class="connector line2"></div>
    <div class="connector line3"></div>
    <div class="connector line4"></div>

    <div class="node farmer">
        <div class="eyebrow">
            SUPPLY NETWORK
        </div>
        <div class="big">
            {len(supply_ids)} FARMERS
        </div>
    </div>

    <div class="node buyer">
        <div class="eyebrow">
            LIVE DEMAND
        </div>
        <div class="big">
            {demand_kg:.0f} KG
        </div>
    </div>

    <div class="node logistics">
        <div class="eyebrow">
            EXECUTION LAYER
        </div>
        <div class="big">
            LOGISTICS
        </div>
    </div>

    <div class="node verify">
        <div class="eyebrow">
            TRUST LAYER
        </div>
        <div class="big">
            INDEPENDENT CHECK
        </div>
    </div>

    <div class="center-status">
        DEMAND → MATCH → AGGREGATE → OPTIMIZE → VERIFY
    </div>

    <div class="system">

        <div class="ring r1"></div>
        <div class="ring r2"></div>
        <div class="ring r3"></div>

        <div class="cube">

            <div class="face front">
                AI CORE
            </div>

            <div class="face back">
                MATCH
            </div>

            <div class="face right">
                VERIFY
            </div>

            <div class="face left">
                OPTIMIZE
            </div>

            <div class="face top">
                RESCUE
            </div>

            <div class="face bottom">
                MARKET
            </div>

        </div>

    </div>

    <div class="bottom-metrics">

        <div class="metric">
            <div class="label">
                BUYER DEMAND
            </div>
            <div class="value">
                {demand_kg:.0f} KG
            </div>
        </div>

        <div class="metric">
            <div class="label">
                AI MATCHED
            </div>
            <div class="value gold">
                {matched_kg:.0f} KG
            </div>
        </div>

        <div class="metric">
            <div class="label">
                OPTIMIZED ORDER
            </div>
            <div class="value">
                {optimized_kg:.0f} KG
            </div>
        </div>

        <div class="metric">
            <div class="label">
                TRUST STATUS
            </div>
            <div class="value green">
                {verification_label}
            </div>
        </div>

    </div>

</div>


<div class="section pipeline">

    <div class="section-title">
        DECISION PIPELINE
    </div>

    <div class="section-sub">
        Every commercial decision passes through the complete AGRIWEAVE chain.
    </div>

    <div class="stage-grid">

        <div class="stage">
            <div class="num">01</div>
            <div class="name">BUYER DEMAND</div>
            <div class="state">COMPLETE</div>
        </div>

        <div class="stage">
            <div class="num">02</div>
            <div class="name">AI MATCHING</div>
            <div class="state">COMPLETE</div>
        </div>

        <div class="stage">
            <div class="num">03</div>
            <div class="name">AGGREGATION</div>
            <div class="state">COMPLETE</div>
        </div>

        <div class="stage">
            <div class="num">04</div>
            <div class="name">OPTIMIZATION</div>
            <div class="state">COMPLETE</div>
        </div>

        <div class="stage">
            <div class="num">05</div>
            <div class="name">VERIFICATION</div>
            <div class="state">
                {"COMPLETE" if verified else "REVIEW"}
            </div>
        </div>

    </div>

</div>


<div class="section network">

    <div class="section-title">
        MARKET NETWORK
    </div>

    <div class="section-sub">
        Fragmented supply becomes buyer-sized commercial capacity.
    </div>

    <div class="network-grid">

        <div class="panel">

            <div class="panel-title">
                FARMER SUPPLY MATRIX
            </div>

            <div class="panel-line">
                Candidate supplies available to the market engine.
            </div>

            <div class="supply-list">
"""

    for supply in data.get("supplies", []):
        sid = str(
            getattr(
                supply,
                "id",
                "",
            )
        )
        loc = str(
            getattr(
                supply,
                "location",
                "",
            )
        )
        qty = as_float(
            getattr(
                supply,
                "quantity_kg",
                0,
            ),
            0,
        )

        visual += f"""
                <div class="supply">
                    <div class="id">{sid}</div>
                    <div class="loc">{loc}</div>
                    <div class="qty">{qty:.0f} KG AVAILABLE</div>
                </div>
"""

    order = value(
        result,
        "order",
        None,
    )

    order_price = as_float(
        value(
            order,
            "selling_price_per_kg",
            0,
        ),
        0,
    )

    order_value = (
        optimized_kg * order_price
        if order_price > 0
        else 0
    )

    visual += f"""
            </div>

        </div>

        <div class="panel">

            <div class="panel-title">
                COMMERCIAL SIGNAL
            </div>

            <div class="big-number">
                {surplus_kg:.0f}
            </div>

            <div class="mini-label">
                KG SURPLUS AFTER DEMAND COVERAGE
            </div>

            <div class="badge-row">
                <div class="badge">
                    {len(supply_ids)} FARMERS
                </div>

                <div class="badge">
                    {optimized_kg:.0f} KG ALLOCATED
                </div>

                <div class="badge">
                    ₹{order_price:.2f}/KG
                </div>

                <div class="badge">
                    ₹{order_value:,.0f} ORDER VALUE
                </div>
            </div>

        </div>

    </div>

</div>


</div>


<script>

const canvas =
    document.getElementById("stars");

const ctx =
    canvas.getContext("2d");

let W = 1;
let H = 1;

const particles = [];

const COUNT = 105;

function resize() {{

    const rect =
        canvas.getBoundingClientRect();

    W =
        Math.max(
            1,
            Math.floor(rect.width)
        );

    H =
        Math.max(
            1,
            Math.floor(rect.height)
        );

    const dpr =
        Math.min(
            window.devicePixelRatio || 1,
            2
        );

    canvas.width =
        W * dpr;

    canvas.height =
        H * dpr;

    ctx.setTransform(
        dpr,
        0,
        0,
        dpr,
        0,
        0
    );
}}

window.addEventListener(
    "resize",
    resize
);

function makeParticle() {{

    return {{
        x:
            (Math.random() - .5)
            * 1600,

        y:
            (Math.random() - .5)
            * 1200,

        z:
            100 +
            Math.random() * 1500,

        size:
            .6 +
            Math.random() * 2.4,

        speed:
            .25 +
            Math.random() * .65
    }};
}}

for (
    let i = 0;
    i < COUNT;
    i++
) {{
    particles.push(
        makeParticle()
    );
}}

let time = 0;

function frame() {{

    time += .004;

    ctx.clearRect(
        0,
        0,
        W,
        H
    );

    const projected = [];

    for (
        const p of particles
    ) {{

        p.z -= p.speed;

        if (
            p.z < 80
        ) {{
            p.z =
                1550 +
                Math.random() * 500;
        }}

        const c =
            Math.cos(time);

        const s =
            Math.sin(time);

        const x =
            p.x * c -
            p.z * s * .22;

        const z =
            p.x * s * .22 +
            p.z * c;

        if (
            z <= 90
        ) {{
            continue;
        }}

        const focal = 650;

        const scale =
            focal / z;

        projected.push({{
            x:
                W / 2 +
                x * scale,

            y:
                H / 2 +
                p.y * scale,

            z,
            size:
                Math.max(
                    .4,
                    p.size * scale * 1.6
                )
        }});
    }}

    projected.sort(
        (a,b) =>
            b.z - a.z
    );

    for (
        let i = 0;
        i < projected.length;
        i++
    ) {{

        const a =
            projected[i];

        for (
            let j = i + 1;
            j < Math.min(
                projected.length,
                i + 7
            );
            j++
        ) {{

            const b =
                projected[j];

            const dx =
                a.x - b.x;

            const dy =
                a.y - b.y;

            const distance =
                Math.hypot(
                    dx,
                    dy
                );

            if (
                distance > 120
            ) {{
                continue;
            }}

            ctx.beginPath();

            ctx.moveTo(
                a.x,
                a.y
            );

            ctx.lineTo(
                b.x,
                b.y
            );

            const alpha =
                Math.max(
                    0,
                    .22 -
                    distance / 700
                );

            ctx.strokeStyle =
                `rgba(255,175,35,${{alpha}})`;

            ctx.lineWidth =
                .55;

            ctx.stroke();
        }}
    }}

    for (
        const p of projected
    ) {{

        ctx.beginPath();

        ctx.arc(
            p.x,
            p.y,
            p.size,
            0,
            Math.PI * 2
        );

        ctx.fillStyle =
            "rgba(255,190,60,.72)";

        ctx.shadowBlur =
            8;

        ctx.shadowColor =
            "rgba(255,55,40,.48)";

        ctx.fill();

        ctx.shadowBlur =
            0;
    }}

    requestAnimationFrame(
        frame
    );
}}

resize();
frame();

</script>

</body>
</html>
"""

    components.html(
        visual,
        height=1740,
        scrolling=False,
    )

    # --------------------------------------------------------
    # Backend error is shown as normal Streamlit text, never
    # as source code.
    # --------------------------------------------------------

    if backend_error:
        st.warning(
            "Live pipeline connection needs attention: "
            + backend_error
        )

    # --------------------------------------------------------
    # LIVE MARKET CONTROL PANEL
    # --------------------------------------------------------

    st.markdown(
        '<div style="'
        'margin:24px 0 12px 0;'
        'color:#ffbd2e;'
        'font-size:16px;'
        'font-weight:1000;'
        'letter-spacing:4px;'
        '">LIVE MARKET CONTROL</div>',
        unsafe_allow_html=True,
    )

    live_control_html = f"""
<!doctype html>
<html>
<head>
<meta charset="utf-8">
<style>

* {{
    box-sizing:border-box;
}}

html, body {{
    margin:0;
    padding:0;
    background:transparent;
    font-family:Arial,Helvetica,sans-serif;
}}

.grid {{
    display:grid;
    grid-template-columns:repeat(4,1fr);
    gap:12px;
    width:100%;
}}

.card {{
    position:relative;
    overflow:hidden;
    min-height:116px;
    padding:18px 20px;
    border-radius:14px;
    background:
        linear-gradient(
            145deg,
            rgba(9,11,16,.98),
            rgba(5,7,11,.96)
        );
    border:1px solid rgba(255,255,255,.09);
    box-shadow:
        inset 0 0 26px rgba(255,255,255,.018),
        0 0 26px rgba(0,0,0,.12);
}}

.card::before {{
    content:"";
    position:absolute;
    left:-25%;
    top:0;
    width:150%;
    height:1px;
    background:
        linear-gradient(
            90deg,
            transparent,
            var(--accent),
            transparent
        );
    animation:
        sweep 2.7s linear infinite;
}}

@keyframes sweep {{
    0% {{ transform:translateX(-42%); opacity:0; }}
    30% {{ opacity:1; }}
    100% {{ transform:translateX(42%); opacity:0; }}
}}

.card::after {{
    content:"";
    position:absolute;
    right:-18px;
    bottom:-28px;
    width:110px;
    height:110px;
    border-radius:50%;
    background:var(--glow);
    filter:blur(25px);
    opacity:.16;
    animation:
        breathe 3.2s ease-in-out infinite;
}}

@keyframes breathe {{
    50% {{
        transform:scale(1.22);
        opacity:.28;
    }}
}}

.label {{
    color:#b3bac5;
    font-size:12px;
    font-weight:900;
    letter-spacing:2px;
}}

.value {{
    margin-top:12px;
    color:var(--accent);
    font-size:32px;
    line-height:1;
    font-weight:1000;
    letter-spacing:.5px;
    text-shadow:
        0 0 18px var(--text-glow);
    animation:
        valuePulse 2.4s ease-in-out infinite;
}}

@keyframes valuePulse {{
    0%,100% {{
        transform:translateY(0) scale(1);
        filter:brightness(1);
    }}
    50% {{
        transform:translateY(-2px) scale(1.025);
        filter:brightness(1.15);
    }}
}}

.unit {{
    margin-top:7px;
    color:#707986;
    font-size:9px;
    font-weight:800;
    letter-spacing:2px;
}}

.blue {{
    --accent:#58adff;
    --glow:#2187ff;
    --text-glow:rgba(88,173,255,.26);
}}

.gold {{
    --accent:#ffc238;
    --glow:#ffb000;
    --text-glow:rgba(255,194,56,.24);
}}

.red {{
    --accent:#ff6b57;
    --glow:#ff3b35;
    --text-glow:rgba(255,107,87,.24);
}}

.green {{
    --accent:#3dffa4;
    --glow:#1cff88;
    --text-glow:rgba(61,255,164,.24);
}}

@media(max-width:900px) {{
    .grid {{
        grid-template-columns:repeat(2,1fr);
    }}
}}

</style>
</head>

<body>

<div class="grid">

    <div class="card blue">
        <div class="label">BUYER DEMAND</div>
        <div class="value">{demand_kg:.0f} KG</div>
        <div class="unit">LIVE REQUIREMENT</div>
    </div>

    <div class="card gold">
        <div class="label">AI MATCHED</div>
        <div class="value">{matched_kg:.0f} KG</div>
        <div class="unit">INTELLIGENCE OUTPUT</div>
    </div>

    <div class="card red">
        <div class="label">OPTIMIZED ORDER</div>
        <div class="value">{optimized_kg:.0f} KG</div>
        <div class="unit">ALLOCATED CAPACITY</div>
    </div>

    <div class="card green">
        <div class="label">MARKET SURPLUS</div>
        <div class="value">{surplus_kg:.0f} KG</div>
        <div class="unit">AVAILABLE BUFFER</div>
    </div>

</div>

</body>
</html>
"""

    components.html(
        live_control_html,
        height=136,
        scrolling=False,
    )

    # --------------------------------------------------------
    # REAL SUPPLY RESCUE BUTTON
    # --------------------------------------------------------

    st.markdown(
        '<div style="'
        'margin-top:25px;'
        'padding:18px;'
        'border-radius:14px;'
        'border:1px solid #332029;'
        'background:linear-gradient(145deg,#10070a,#08090d);'
        '">'
        '<div style="'
        'color:#ff4d4d;'
        'font-size:15px;'
        'font-weight:1000;'
        'letter-spacing:4px;'
        '">'
        'SUPPLY RESCUE CONTROL'
        '</div>'
        '<div style="'
        'margin-top:7px;'
        'color:#c2c8d1;'
        'font-size:13px;'
        'font-weight:900;'
        '">'
        'Simulate SUP-DEMO-001 becoming unavailable after '
        'the commercial order is planned.'
        '</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    rescue_clicked = st.button(
        "RUN SUPPLY RESCUE",
        type="primary",
    )

    if rescue_clicked:

        if pipeline is None or demand is None:

            st.error(
                "The AGRIWEAVE pipeline is unavailable."
            )

        else:

            try:

                original_supplies = [
                    supply
                    for supply
                    in data.get("supplies", [])
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

                rescue = pipeline.run_supply_rescue(
                    demand=demand,
                    order=order,
                    supplies=selected,
                    optimization=optimization,
                    failed_supply_id="SUP-DEMO-001",
                    replacement_supplies=data.get(
                        "supplies",
                        [],
                    ),
                )

                st.session_state[
                    "agriweave_rescue_result"
                ] = rescue

            except Exception as exc:

                st.error(
                    "Supply rescue execution failed."
                )

                st.write(
                    f"{type(exc).__name__}: {exc}"
                )

    rescue = st.session_state.get(
        "agriweave_rescue_result"
    )

    if rescue is not None:

        recovered = bool(
            value(
                rescue,
                "recovered",
                False,
            )
        )

        decision = str(
            value(
                rescue,
                "decision",
                "UNKNOWN",
            )
        )

        summary = str(
            value(
                rescue,
                "summary",
                value(
                    rescue,
                    "explanation",
                    "",
                ),
            )
            or ""
        )

        shortfall = as_float(
            value(
                rescue,
                "shortfall_quantity_kg",
                value(
                    rescue,
                    "shortfall_kg",
                    0,
                ),
            ),
            0,
        )

        recovered_quantity = as_float(
            value(
                rescue,
                "verified_recovered_quantity_kg",
                value(
                    rescue,
                    "recovered_quantity_kg",
                    0,
                ),
            ),
            0,
        )

        ratio = as_float(
            value(
                rescue,
                "recovery_ratio",
                0,
            ),
            0,
        )

        replacement_ids = list(
            value(
                rescue,
                "replacement_supply_ids",
                [],
            )
            or []
        )

        replacement_text = (
            ", ".join(
                str(x)
                for x in replacement_ids
            )
            if replacement_ids
            else "NONE"
        )

        rescue_status = (
            "RECOVERY VERIFIED"
            if recovered
            else "RECOVERY REJECTED"
        )

        rescue_color = (
            "#3dffa4"
            if recovered
            else "#ff4d4d"
        )

        rescue_html = f"""
<!doctype html>
<html>
<head>
<meta charset="utf-8">
<style>

* {{
    box-sizing:border-box;
}}

body {{
    margin:0;
    padding:8px 4px;
    background:transparent;
    font-family:Arial,Helvetica,sans-serif;
    color:white;
}}

.rescue-shell {{
    position:relative;
    overflow:hidden;
    border-radius:18px;
    padding:24px;
    border:1px solid {rescue_color};
    background:
        radial-gradient(
            circle at 15% 10%,
            rgba(255,55,45,.15),
            transparent 30%
        ),
        linear-gradient(
            145deg,
            #11070a,
            #07090d
        );
    box-shadow:
        0 0 35px
        rgba(255,50,40,.10);
}}

.scan {{
    position:absolute;
    top:0;
    bottom:0;
    left:-20%;
    width:1px;
    background:
        linear-gradient(
            transparent,
            {rescue_color},
            transparent
        );
    box-shadow:
        0 0 18px
        {rescue_color};
    animation:scan 2.4s linear infinite;
}}

@keyframes scan {{
    to {{
        left:120%;
    }}
}}

.eyebrow {{
    color:{rescue_color};
    font-size:12px;
    font-weight:1000;
    letter-spacing:4px;
}}

.status {{
    margin-top:8px;
    font-size:25px;
    font-weight:1000;
    color:white;
    letter-spacing:1px;
}}

.summary {{
    margin-top:8px;
    color:#9299a4;
    font-size:11px;
    line-height:1.6;
}}

.grid {{
    margin-top:18px;
    display:grid;
    grid-template-columns:repeat(4,1fr);
    gap:10px;
}}

.card {{
    padding:15px;
    border-radius:11px;
    background:#07090d;
    border:1px solid rgba(255,255,255,.08);
}}

.label {{
    color:#6c7480;
    font-size:11px;
    letter-spacing:2px;
    font-weight:900;
}}

.value {{
    margin-top:7px;
    color:white;
    font-size:18px;
    font-weight:1000;
}}

.green {{
    color:#3dffa4;
}}

</style>
</head>

<body>

<div class="rescue-shell">

<div class="scan"></div>

<div class="eyebrow">
    SUPPLY DISRUPTION DETECTED
</div>

<div class="status">
    {rescue_status}
</div>

<div class="summary">
    {summary}
</div>

<div class="grid">

    <div class="card">
        <div class="label">
            SHORTFALL
        </div>
        <div class="value">
            {shortfall:.0f} KG
        </div>
    </div>

    <div class="card">
        <div class="label">
            RECOVERED
        </div>
        <div class="value green">
            {recovered_quantity:.0f} KG
        </div>
    </div>

    <div class="card">
        <div class="label">
            RECOVERY RATIO
        </div>
        <div class="value green">
            {ratio * 100:.0f}%
        </div>
    </div>

    <div class="card">
        <div class="label">
            REPLACEMENT
        </div>
        <div class="value">
            {replacement_text}
        </div>
    </div>

</div>

</div>

</body>
</html>
"""

        components.html(
            rescue_html,
            height=260,
            scrolling=False,
        )

        trace = list(
            value(
                rescue,
                "trace",
                [],
            )
            or []
        )

        errors = list(
            value(
                rescue,
                "errors",
                [],
            )
            or []
        )

        warnings = list(
            value(
                rescue,
                "warnings",
                [],
            )
            or []
        )

        if trace or errors or warnings:

            with st.expander(
                "Recovery decision trace"
            ):

                if trace:
                    for item in trace:
                        st.write(
                            item
                        )

                if errors:
                    st.write(
                        "Errors:",
                        errors,
                    )

                if warnings:
                    st.write(
                        "Warnings:",
                        warnings,
                    )

    # --------------------------------------------------------
    # WHY AGRIWEAVE
    # --------------------------------------------------------

    why_html = """
<!doctype html>
<html>
<head>
<meta charset="utf-8">
<style>

body {
    margin:0;
    background:transparent;
    color:white;
    font-family:Arial,Helvetica,sans-serif;
}

.wrap {
    margin-top:22px;
    padding:22px;
    border-radius:16px;
    background:
        linear-gradient(
            145deg,
            #090b10,
            #05070a
        );
    border:1px solid #20252c;
}

.title {
    color:#ffc238;
    font-size:10px;
    font-weight:1000;
    letter-spacing:4px;
}

.grid {
    display:grid;
    grid-template-columns:repeat(3,1fr);
    gap:10px;
    margin-top:15px;
}

.item {
    padding:18px;
    border-radius:12px;
    background:#07090d;
    border:1px solid rgba(255,255,255,.07);
}

.num {
    color:#ff343b;
    font-size:24px;
    font-weight:1000;
}

.name {
    margin-top:7px;
    color:white;
    font-size:12px;
    font-weight:1000;
}

.text {
    margin-top:7px;
    color:#777f8c;
    font-size:12px;
    line-height:1.6;
}

</style>
</head>

<body>

<div class="wrap">

<div class="title">
    WHY AGRIWEAVE
</div>

<div class="grid">

<div class="item">
    <div class="num">01</div>
    <div class="name">DEMAND FIRST</div>
    <div class="text">
        Start from real buyer requirements rather than
        leaving marginal farmers to search for uncertain markets.
    </div>
</div>

<div class="item">
    <div class="num">02</div>
    <div class="name">COLLECTIVE SUPPLY</div>
    <div class="text">
        Combine small farmer quantities into a buyer-sized
        commercial order with transparent allocation.
    </div>
</div>

<div class="item">
    <div class="num">03</div>
    <div class="name">RESILIENT EXECUTION</div>
    <div class="text">
        When a committed supplier fails, identify replacement
        supply and independently verify recovery.
    </div>
</div>

</div>

</div>

</body>
</html>
"""

    components.html(
        why_html,
        height=245,
        scrolling=False,
    )


# ============================================================
# PYTEST SAFETY
# ============================================================

if "pytest" not in sys.modules:
    main()
