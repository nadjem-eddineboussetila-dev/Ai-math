"""
AI Math Agent - Streamlit Frontend
====================================
Interactive UI that talks to the FastAPI backend.

Run with:
    streamlit run frontend/app.py
"""

import json
import os
import time
from typing import Any, Dict, List, Optional

import requests
import streamlit as st

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

# Operation display names (Arabic + English for accessibility)
OPERATIONS: Dict[str, str] = {
    "auto":      "🔍 Auto-detect (تلقائي)",
    "simplify":  "✨ Simplify (تبسيط)",
    "solve":     "🔑 Solve Equation (حل معادلة)",
    "diff":      "📈 Differentiate (تفاضل)",
    "integrate": "∫  Integrate (تكامل)",
    "limit":     "⟶  Limit (نهايات)",
    "expand":    "📦 Expand (توسيع)",
    "factor":    "🔬 Factor (تحليل)",
    "stats":     "📊 Statistics (إحصاء)",
}

# Example expressions shown in the sidebar
EXAMPLES: List[Dict[str, Any]] = [
    {"label": "Simplify sin²(x)+cos²(x)",  "expr": "sin(x)**2 + cos(x)**2",   "op": "simplify"},
    {"label": "Solve x²-5x+6=0",           "expr": "x**2 - 5*x + 6 = 0",     "op": "solve"},
    {"label": "Differentiate x³·sin(x)",   "expr": "x**3 * sin(x)",           "op": "diff"},
    {"label": "Integrate e^x·cos(x)",      "expr": "exp(x)*cos(x)",            "op": "integrate"},
    {"label": "Limit sin(x)/x as x→0",    "expr": "sin(x)/x",                 "op": "limit",  "limit_point": "0"},
    {"label": "Factor x³-x²-x+1",         "expr": "x**3 - x**2 - x + 1",     "op": "factor"},
    {"label": "Expand (x+y)³",            "expr": "(x+y)**3",                  "op": "expand"},
    {"label": "Stats of [2,4,6,8,10]",    "expr": "stats",                     "op": "stats",  "stats_data": [2,4,6,8,10]},
]

# ---------------------------------------------------------------------------
# Page setup
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="AI Math Agent",
    page_icon="🧮",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Session state initialisation
# ---------------------------------------------------------------------------
if "history" not in st.session_state:
    st.session_state.history: List[Dict[str, Any]] = []

if "prefill" not in st.session_state:
    st.session_state.prefill: Optional[Dict[str, Any]] = None

# ---------------------------------------------------------------------------
# Custom CSS
# ---------------------------------------------------------------------------
st.markdown(
    """
    <style>
    /* ---- Main title ---- */
    .main-title {
        text-align: center;
        font-size: 2.8rem;
        font-weight: 800;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.3rem;
    }
    .sub-title {
        text-align: center;
        color: #888;
        font-size: 1rem;
        margin-bottom: 2rem;
    }
    /* ---- Cards ---- */
    .result-card {
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
        border-radius: 12px;
        padding: 1.5rem;
        margin: 1rem 0;
    }
    .step-card {
        background: #fff;
        border-left: 4px solid #667eea;
        border-radius: 6px;
        padding: 0.7rem 1rem;
        margin: 0.4rem 0;
        box-shadow: 0 1px 4px rgba(0,0,0,0.07);
    }
    .error-card {
        background: #fff5f5;
        border-left: 4px solid #fc8181;
        border-radius: 6px;
        padding: 0.7rem 1rem;
        margin: 0.4rem 0;
    }
    /* ---- History ---- */
    .history-item {
        background: #fafafa;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 0.6rem 0.9rem;
        margin: 0.3rem 0;
        font-size: 0.85rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Sidebar – Examples & History
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown("## 💡 Examples")
    for ex in EXAMPLES:
        if st.button(ex["label"], key=f"ex_{ex['label']}", use_container_width=True):
            st.session_state.prefill = ex

    st.divider()

    st.markdown("## 🕓 History")
    if not st.session_state.history:
        st.caption("No calculations yet.")
    else:
        if st.button("🗑️ Clear history", use_container_width=True):
            st.session_state.history = []
            st.rerun()
        for i, item in enumerate(reversed(st.session_state.history)):
            with st.expander(f"#{len(st.session_state.history)-i}  {item['expr'][:30]}…", expanded=False):
                st.markdown(f"**Operation:** `{item['operation']}`")
                st.markdown(f"**Result:** `{item['result']}`")

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
st.markdown('<p class="main-title">🧮 AI Math Agent</p>', unsafe_allow_html=True)
st.markdown(
    '<p class="sub-title">Exact symbolic mathematics powered by SymPy & NumPy — '
    'وكيل رياضيات دقيق يعتمد على التنفيذ البرمجي لا التنبؤ النصي</p>',
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Input form
# ---------------------------------------------------------------------------
prefill = st.session_state.prefill or {}

col_input, col_opts = st.columns([3, 2])

with col_input:
    expression = st.text_area(
        "✏️ Enter your mathematical expression / أدخل التعبير الرياضي",
        value=prefill.get("expr", ""),
        height=90,
        placeholder="e.g.  x**2 - 5*x + 6 = 0  or  sin(x)**2 + cos(x)**2",
        key="expr_input",
    )

with col_opts:
    # Operation selector
    op_keys = list(OPERATIONS.keys())
    op_labels = list(OPERATIONS.values())
    default_op = prefill.get("op", "auto")
    default_idx = op_keys.index(default_op) if default_op in op_keys else 0

    op_label = st.selectbox(
        "⚙️ Operation / العملية",
        options=op_labels,
        index=default_idx,
        key="op_select",
    )
    operation = op_keys[op_labels.index(op_label)]

    variable = st.text_input(
        "🔤 Variable / المتغير",
        value=prefill.get("variable", "x"),
        key="var_input",
    )

# Extra options shown conditionally
limit_point = None
stats_data: Optional[List[float]] = None

if operation == "limit":
    limit_point = st.text_input(
        "📍 Limit point (e.g. 0, oo, pi)",
        value=prefill.get("limit_point", "0"),
        key="limit_pt",
    )

if operation == "stats":
    raw_stats = st.text_input(
        "📊 Data values (comma-separated) / البيانات مفصولة بفاصلة",
        value=", ".join(str(v) for v in prefill.get("stats_data", [])),
        placeholder="2, 4, 6, 8, 10",
        key="stats_input",
    )
    if raw_stats.strip():
        try:
            stats_data = [float(v.strip()) for v in raw_stats.split(",") if v.strip()]
        except ValueError:
            st.warning("⚠️ Please enter only numeric values separated by commas.")

# Clear prefill so next run starts fresh
st.session_state.prefill = None

# ---------------------------------------------------------------------------
# Solve button
# ---------------------------------------------------------------------------
solve_clicked = st.button("🚀 Solve / حل", type="primary", use_container_width=True)

if solve_clicked:
    if not expression.strip() and operation != "stats":
        st.error("❌ Please enter a mathematical expression.")
    else:
        # Build request payload
        payload: Dict[str, Any] = {
            "expression": expression.strip() or "stats",
            "operation": operation,
            "variable": variable.strip() or "x",
        }
        if limit_point:
            payload["limit_point"] = limit_point.strip()
        if stats_data:
            payload["stats_data"] = stats_data

        # Call the backend
        with st.spinner("⏳ Computing… / جاري الحساب…"):
            try:
                t0 = time.time()
                response = requests.post(
                    f"{BACKEND_URL}/solve",
                    json=payload,
                    timeout=30,
                )
                elapsed = time.time() - t0

                if response.status_code == 200:
                    data: Dict[str, Any] = response.json()

                    # ---- Result card ----
                    st.markdown("---")
                    st.markdown("### ✅ Result / النتيجة")

                    res_col, meta_col = st.columns([2, 1])
                    with res_col:
                        st.markdown(
                            f'<div class="result-card">'
                            f'<b>Expression:</b> <code>{data["input_expression"]}</code><br>'
                            f'<b>Operation:</b> <code>{data["operation"]}</code><br>'
                            f'<b>Result:</b> <span style="font-size:1.3rem;font-weight:700;color:#4a5568">'
                            f'{data["result"]}</span>'
                            f"</div>",
                            unsafe_allow_html=True,
                        )

                    with meta_col:
                        st.metric("⏱ Computation time", f"{elapsed:.3f} s")
                        if data.get("numeric_value"):
                            st.metric("≈ Numeric value", data["numeric_value"])

                    # LaTeX rendering
                    if data.get("latex"):
                        st.markdown("**LaTeX representation:**")
                        st.latex(data["latex"])

                    # ---- Step-by-step ----
                    if data.get("steps"):
                        st.markdown("### 📋 Step-by-step / خطوات الحل")
                        for step in data["steps"]:
                            if step["result"]:
                                st.markdown(
                                    f'<div class="step-card">'
                                    f'<b>Step {step["step"]}:</b> {step["description"]}'
                                    f' → <code>{step["result"]}</code>'
                                    f"</div>",
                                    unsafe_allow_html=True,
                                )
                            else:
                                st.markdown(
                                    f'<div class="step-card">'
                                    f'<b>Step {step["step"]}:</b> {step["description"]}'
                                    f"</div>",
                                    unsafe_allow_html=True,
                                )

                    # Save to history
                    st.session_state.history.append(
                        {
                            "expr": data["input_expression"],
                            "operation": data["operation"],
                            "result": data["result"],
                        }
                    )

                else:
                    # Backend returned an HTTP error
                    try:
                        detail = response.json().get("detail", response.text)
                    except Exception:
                        detail = response.text
                    st.markdown(
                        f'<div class="error-card">❌ <b>Error {response.status_code}:</b> {detail}</div>',
                        unsafe_allow_html=True,
                    )

            except requests.exceptions.ConnectionError:
                st.error(
                    f"🔌 Cannot connect to backend at `{BACKEND_URL}`. "
                    "Make sure the FastAPI server is running (`uvicorn backend.main:app --reload`)."
                )
            except requests.exceptions.Timeout:
                st.error("⏰ The request timed out. Try a simpler expression.")
            except Exception as exc:
                st.error(f"Unexpected error: {exc}")

# ---------------------------------------------------------------------------
# Footer
# ---------------------------------------------------------------------------
st.markdown("---")
st.markdown(
    "<div style='text-align:center;color:#aaa;font-size:0.8rem'>"
    "AI Math Agent · Powered by SymPy, NumPy & FastAPI · "
    "Built with ❤️ using Streamlit"
    "</div>",
    unsafe_allow_html=True,
)
