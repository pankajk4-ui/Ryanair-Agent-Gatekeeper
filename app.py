"""
Ryanair Agent Gatekeeper - Streamlit Dashboard
Academic simulation for MBA Agentic AI assignment.
Student: Pankaj Kumar Tiwari | Reg No: PGD202564630 | Shoolini University

Stage 2: Full interactive UI featuring:
  1. Professional Dashboard with real-time metrics and Plotly telemetry
  2. Agent Registration with duplicate prevention
  3. Real-Time Request Evaluation enforcing the 7 deterministic rules
  4. Agent Lifecycle Revocation with timestamped non-repudiation
  5. Human-in-the-Loop Customer Approvals for high-value/sensitive actions
  6. Comprehensive About Project architecture & policy documentation
"""

import os
import sqlite3
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
import zoneinfo

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from database import (
    get_agent,
    get_audit_events,
    get_default_db_path,
    get_ist_now_iso,
    init_db,
    list_agents,
    list_approvals,
    list_requests,
    register_agent,
    revoke_agent,
    update_request_approval,
)
from gatekeeper import SUPPORTED_ACTIONS, evaluate_request

# Timezone standard
IST = zoneinfo.ZoneInfo("Asia/Kolkata")

# -----------------------------------------------------------------------------
# PAGE CONFIGURATION
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Ryanair Agent Gatekeeper",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# -----------------------------------------------------------------------------
# CUSTOM CSS & RYANAIR DESIGN SYSTEM
# -----------------------------------------------------------------------------
RYANAIR_CSS = """
<style>
    /* Google Fonts */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }

    /* Top banner */
    .ryanair-header {
        background: linear-gradient(135deg, #00205B 0%, #073590 100%);
        padding: 24px 30px;
        border-radius: 12px;
        color: #FFFFFF;
        margin-bottom: 25px;
        box-shadow: 0 4px 14px rgba(0, 32, 91, 0.15);
        border-bottom: 4px solid #F4C300;
    }
    .ryanair-title {
        font-size: 28px;
        font-weight: 800;
        letter-spacing: -0.5px;
        margin: 0;
        color: #FFFFFF;
        display: flex;
        align-items: center;
        gap: 12px;
    }
    .ryanair-subtitle {
        font-size: 15px;
        color: #F4C300;
        font-weight: 600;
        margin-top: 4px;
        letter-spacing: 0.2px;
    }
    .ryanair-author-tag {
        font-size: 13px;
        color: #DCE5F5;
        margin-top: 8px;
        font-weight: 500;
    }

    /* Metric cards */
    .metric-card {
        background: #FFFFFF;
        border-radius: 10px;
        padding: 18px 20px;
        border: 1px solid #E2E8F0;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
        margin-bottom: 15px;
        transition: transform 0.15s ease, box-shadow 0.15s ease;
    }
    .metric-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 14px rgba(0, 32, 91, 0.08);
    }
    .metric-label {
        font-size: 12px;
        text-transform: uppercase;
        color: #64748B;
        font-weight: 700;
        letter-spacing: 0.5px;
    }
    .metric-value {
        font-size: 26px;
        font-weight: 800;
        color: #00205B;
        margin-top: 4px;
    }
    .metric-sub {
        font-size: 12px;
        color: #94A3B8;
        margin-top: 4px;
    }

    /* Decision cards */
    .decision-card-allow {
        background: linear-gradient(135deg, #ECFDF5 0%, #D1FAE5 100%);
        border: 2px solid #10B981;
        border-radius: 12px;
        padding: 24px;
        color: #065F46;
        box-shadow: 0 4px 12px rgba(16, 185, 129, 0.15);
    }
    .decision-card-ask {
        background: linear-gradient(135deg, #FFFBEB 0%, #FEF3C7 100%);
        border: 2px solid #F59E0B;
        border-radius: 12px;
        padding: 24px;
        color: #92400E;
        box-shadow: 0 4px 12px rgba(245, 158, 11, 0.15);
    }
    .decision-card-block {
        background: linear-gradient(135deg, #FEF2F2 0%, #FEE2E2 100%);
        border: 2px solid #EF4444;
        border-radius: 12px;
        padding: 24px;
        color: #991B1B;
        box-shadow: 0 4px 12px rgba(239, 68, 68, 0.15);
    }

    /* Badges */
    .badge-allow {
        background-color: #10B981;
        color: white;
        padding: 4px 10px;
        border-radius: 9999px;
        font-size: 12px;
        font-weight: 700;
        display: inline-block;
    }
    .badge-ask {
        background-color: #F59E0B;
        color: white;
        padding: 4px 10px;
        border-radius: 9999px;
        font-size: 12px;
        font-weight: 700;
        display: inline-block;
    }
    .badge-block {
        background-color: #EF4444;
        color: white;
        padding: 4px 10px;
        border-radius: 9999px;
        font-size: 12px;
        font-weight: 700;
        display: inline-block;
    }
    .badge-active {
        background-color: #0284C7;
        color: white;
        padding: 3px 8px;
        border-radius: 6px;
        font-size: 11px;
        font-weight: 700;
    }
    .badge-revoked {
        background-color: #64748B;
        color: white;
        padding: 3px 8px;
        border-radius: 6px;
        font-size: 11px;
        font-weight: 700;
    }

    /* Sidebar tweaks */
    .css-1d391kg {
        background-color: #F8FAFD;
    }
</style>
"""
st.markdown(RYANAIR_CSS, unsafe_allow_html=True)


# -----------------------------------------------------------------------------
# HELPER FUNCTIONS
# -----------------------------------------------------------------------------
def get_dashboard_stats() -> Dict[str, Any]:
    """Retrieve actual computed metrics directly from the SQLite database."""
    agents = list_agents()
    requests = list_requests()
    approvals = list_approvals()

    total_agents = len(agents)
    active_agents = sum(1 for a in agents if a["status"] == "ACTIVE")
    revoked_agents = sum(1 for a in agents if a["status"] == "REVOKED")

    total_requests = len(requests)
    allow_count = sum(1 for r in requests if r["decision"] == "ALLOW")
    ask_count = sum(1 for r in requests if r["decision"] == "ASK CUSTOMER")
    block_count = sum(1 for r in requests if r["decision"] == "BLOCK")
    pending_approvals = sum(1 for r in requests if r["status"] == "PENDING APPROVAL")

    return {
        "total_agents": total_agents,
        "active_agents": active_agents,
        "revoked_agents": revoked_agents,
        "total_requests": total_requests,
        "allow_count": allow_count,
        "ask_count": ask_count,
        "block_count": block_count,
        "pending_approvals": pending_approvals,
        "agents": agents,
        "requests": requests,
        "approvals": approvals,
    }


def render_header(title: str, subtitle: str):
    """Render the standard Ryanair-branded banner."""
    st.markdown(
        f"""
        <div class="ryanair-header">
            <div class="ryanair-title">✈️ RYANAIR AGENT GATEKEEPER</div>
            <div class="ryanair-subtitle">{title}</div>
            <div class="ryanair-author-tag">
                {subtitle} &bull; <strong>Student:</strong> Pankaj Kumar Tiwari &bull; <strong>Reg No:</strong> PGD202564630
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# -----------------------------------------------------------------------------
# SIDEBAR NAVIGATION
# -----------------------------------------------------------------------------
with st.sidebar:
    st.markdown(
        """
        <div style="text-align: center; padding: 10px 0 15px 0;">
            <div style="font-size: 32px;">✈️</div>
            <div style="font-size: 18px; font-weight: 800; color: #00205B;">RYANAIR</div>
            <div style="font-size: 11px; font-weight: 700; color: #073590; letter-spacing: 1px;">AGENT GATEKEEPER</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    page = st.radio(
        "Navigation",
        [
            "📊 Dashboard",
            "📝 Register Agent",
            "⚡ Check Agent Request",
            "🚫 Revoke Agent",
            "📋 Customer Approvals",
            "ℹ️ About Project",
        ],
        index=0,
    )

    st.markdown("---")

    # Real-time quick status widget
    stats = get_dashboard_stats()
    st.markdown("### 🛫 Gatekeeper Status")
    st.markdown(f"**Active Agents:** `{stats['active_agents']}` / `{stats['total_agents']}`")
    st.markdown(f"**Total Evaluated:** `{stats['total_requests']}` requests")
    if stats["pending_approvals"] > 0:
        st.warning(f"⚠️ **{stats['pending_approvals']} Pending Approval**")
    else:
        st.success("✅ **Queue Clean** (0 Pending)")

    st.markdown("---")
    st.markdown(
        """
        <div style="font-size: 11px; color: #64748B; line-height: 1.5;">
            <strong>Student:</strong> Pankaj Kumar Tiwari<br>
            <strong>Reg No:</strong> PGD202564630<br>
            <strong>Academic:</strong> MBA Agentic AI<br>
            <strong>University:</strong> Shoolini University<br>
            <strong>Mode:</strong> Simulation Only
        </div>
        """,
        unsafe_allow_html=True,
    )


# =============================================================================
# PAGE 1: DASHBOARD
# =============================================================================
if page == "📊 Dashboard":
    render_header(
        "AI Agent Permission & Transaction Control System",
        "Executive Dashboard & Live Telemetry",
    )

    stats = get_dashboard_stats()

    # Top Metrics Row
    m_col1, m_col2, m_col3, m_col4 = st.columns(4)

    with m_col1:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-label">Total Registered Agents</div>
                <div class="metric-value">{stats['total_agents']}</div>
                <div class="metric-sub">{stats['active_agents']} active &bull; {stats['revoked_agents']} revoked</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with m_col2:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-label">Active Agents</div>
                <div class="metric-value" style="color: #0284C7;">{stats['active_agents']}</div>
                <div class="metric-sub">Authorised for transactions</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with m_col3:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-label">Revoked Agents</div>
                <div class="metric-value" style="color: #64748B;">{stats['revoked_agents']}</div>
                <div class="metric-sub">Permissions withdrawn</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with m_col4:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-label">Total Requests Evaluated</div>
                <div class="metric-value">{stats['total_requests']}</div>
                <div class="metric-sub">{stats['pending_approvals']} pending customer confirmation</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # Decisions Breakdown Row
    d_col1, d_col2, d_col3, d_col4 = st.columns(4)

    with d_col1:
        st.markdown(
            f"""
            <div class="metric-card" style="border-left: 5px solid #10B981;">
                <div class="metric-label">ALLOW (R3, R4)</div>
                <div class="metric-value" style="color: #10B981;">{stats['allow_count']}</div>
                <div class="metric-sub">Read-only or &le; EUR 200.00</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with d_col2:
        st.markdown(
            f"""
            <div class="metric-card" style="border-left: 5px solid #F59E0B;">
                <div class="metric-label">ASK CUSTOMER (R5, R6)</div>
                <div class="metric-value" style="color: #F59E0B;">{stats['ask_count']}</div>
                <div class="metric-sub">&gt; EUR 200.00 or Modifications</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with d_col3:
        st.markdown(
            f"""
            <div class="metric-card" style="border-left: 5px solid #EF4444;">
                <div class="metric-label">BLOCK (R1, R2, R7)</div>
                <div class="metric-value" style="color: #EF4444;">{stats['block_count']}</div>
                <div class="metric-sub">Unregistered, Revoked or Invalid</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with d_col4:
        st.markdown(
            f"""
            <div class="metric-card" style="border-left: 5px solid #00205B;">
                <div class="metric-label">PENDING APPROVALS</div>
                <div class="metric-value" style="color: #00205B;">{stats['pending_approvals']}</div>
                <div class="metric-sub">Awaiting customer action</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("---")

    # Interactive Plots Row
    chart_col1, chart_col2 = st.columns([1, 1])

    with chart_col1:
        st.subheader("Decision Distribution")
        if stats["total_requests"] > 0:
            dec_data = pd.DataFrame([
                {"Decision": "ALLOW", "Count": stats["allow_count"], "Color": "#10B981"},
                {"Decision": "ASK CUSTOMER", "Count": stats["ask_count"], "Color": "#F59E0B"},
                {"Decision": "BLOCK", "Count": stats["block_count"], "Color": "#EF4444"},
            ])
            dec_data = dec_data[dec_data["Count"] > 0]

            fig_pie = px.pie(
                dec_data,
                names="Decision",
                values="Count",
                color="Decision",
                color_discrete_map={
                    "ALLOW": "#10B981",
                    "ASK CUSTOMER": "#F59E0B",
                    "BLOCK": "#EF4444",
                },
                hole=0.45,
            )
            fig_pie.update_traces(textinfo="percent+label", textposition="inside")
            fig_pie.update_layout(
                margin=dict(t=20, b=20, l=20, r=20),
                height=300,
                showlegend=True,
            )
            st.plotly_chart(fig_pie, use_container_width=True)
        else:
            st.info("No transaction requests evaluated yet. Submit requests via 'Check Agent Request' to generate live visual charts.")

    with chart_col2:
        st.subheader("Requests by Action")
        if stats["total_requests"] > 0:
            df_req = pd.DataFrame(stats["requests"])
            action_counts = df_req["action"].value_counts().reset_index()
            action_counts.columns = ["Action", "Count"]

            fig_bar = px.bar(
                action_counts,
                x="Action",
                y="Count",
                text="Count",
                color="Action",
                color_discrete_sequence=["#00205B", "#073590", "#F4C300", "#0284C7"],
            )
            fig_bar.update_traces(textposition="outside")
            fig_bar.update_layout(
                margin=dict(t=20, b=20, l=20, r=20),
                height=300,
                xaxis_title="",
                yaxis_title="Total Invocations",
                showlegend=False,
            )
            st.plotly_chart(fig_bar, use_container_width=True)
        else:
            st.info("Awaiting initial requests to build the action breakdown chart.")

    st.markdown("---")

    # Recent Activity Section
    st.subheader("Recent System Activity")
    act_tab1, act_tab2 = st.tabs(["Recent Evaluated Requests", "Permanent Audit Trail"])

    with act_tab1:
        if stats["requests"]:
            df_recent = pd.DataFrame(stats["requests"][:10])
            display_cols = [
                "request_id",
                "timestamp",
                "customer_id",
                "agent_name",
                "action",
                "amount",
                "decision",
                "rule_applied",
                "status",
            ]
            df_recent = df_recent[[c for c in display_cols if c in df_recent.columns]]
            st.dataframe(df_recent, use_container_width=True, hide_index=True)
        else:
            st.write("No requests evaluated yet.")

    with act_tab2:
        audit_events = get_audit_events()
        if audit_events:
            df_audit = pd.DataFrame(audit_events[-15:][::-1])
            display_audit_cols = ["event_id", "timestamp", "event_type", "customer_id", "agent_id", "details"]
            df_audit = df_audit[[c for c in display_audit_cols if c in df_audit.columns]]
            st.dataframe(df_audit, use_container_width=True, hide_index=True)
        else:
            st.write("No audit events recorded yet.")


# =============================================================================
# PAGE 2: REGISTER AGENT
# =============================================================================
elif page == "📝 Register Agent":
    render_header(
        "Agent Registration & Identity Provisioning",
        "Authorize external AI agents to interact on behalf of customers",
    )

    reg_col1, reg_col2 = st.columns([3, 2])

    with reg_col1:
        st.subheader("Register a New Agent")
        st.markdown(
            """
            Register an external AI agent under a customer's authorization.
            The identity tuple `(customer_id, agent_name)` is uniquely normalized.
            """
        )

        with st.form("register_agent_form", clear_on_submit=False):
            cust_id = st.text_input("Customer ID*", placeholder="e.g., CUST-1001").strip()
            cust_name = st.text_input("Customer Name*", placeholder="e.g., Pankaj Tiwari").strip()
            ag_name = st.text_input("Agent Name*", placeholder="e.g., BookingMate-AI").strip()
            ag_desc = st.text_area(
                "Agent Description (Optional)",
                placeholder="e.g., Personal AI booking assistant for business travels.",
            ).strip()

            submit_reg = st.form_submit_button("Register Agent", use_container_width=True)

            if submit_reg:
                if not cust_id or not ag_name or not cust_name:
                    st.error("❌ Customer ID, Customer Name, and Agent Name are required fields.")
                else:
                    try:
                        new_agent = register_agent(
                            customer_id=cust_id,
                            customer_name=cust_name,
                            agent_name=ag_name,
                            description=ag_desc,
                        )
                        st.success(
                            f"✅ **Agent Successfully Registered!**  \n"
                            f"• **Agent ID:** `{new_agent['agent_id']}`  \n"
                            f"• **Customer:** {new_agent['customer_name']} (`{new_agent['customer_id']}`)  \n"
                            f"• **Agent Name:** `{new_agent['agent_name']}`  \n"
                            f"• **Status:** ACTIVE  \n"
                            f"• **Timestamp:** {new_agent['registered_at']} (IST)"
                        )
                    except ValueError as err:
                        st.error(f"❌ **Registration Rejected:** {err}")
                    except Exception as exc:
                        st.error(f"❌ **Database Error:** {exc}")

    with reg_col2:
        st.markdown(
            """
            <div style="background: #F8FAFD; border: 1px solid #E2E8F0; border-radius: 10px; padding: 20px;">
                <h4 style="color: #00205B; margin-top: 0;">🛡️ Gatekeeper Identity Policies</h4>
                <ul style="font-size: 13px; color: #334155; line-height: 1.6; padding-left: 20px;">
                    <li><strong>Normalized Tuple:</strong> Identity is <code>(customer_id, agent_name)</code>. Agent names are matched case-insensitively with trimmed whitespace.</li>
                    <li><strong>Unique Generated Agent ID:</strong> Every agent is assigned an immutable <code>AGT-XXXXXXXX</code> identifier.</li>
                    <li><strong>Pre-authorisation Limit:</strong> Registering an agent pre-authorises flight bookings up to and including <strong>EUR 200.00</strong> (Rule R4).</li>
                    <li><strong>No Silent Reactivation:</strong> Once revoked, an agent cannot be re-registered under the same name by the same customer.</li>
                    <li><strong>Permanent Audit:</strong> All registration events are written to the append-only audit trail.</li>
                </ul>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("---")

    # Registered Agents Table
    st.subheader("Directory of Registered Agents")
    all_agents = list_agents()
    if all_agents:
        df_agents = pd.DataFrame(all_agents)
        cols = ["agent_id", "customer_id", "customer_name", "agent_name", "description", "status", "registered_at", "revoked_at"]
        df_agents = df_agents[[c for c in cols if c in df_agents.columns]]
        st.dataframe(df_agents, use_container_width=True, hide_index=True)
    else:
        st.info("No agents registered yet. Use the form above to register your first agent.")


# =============================================================================
# PAGE 3: CHECK AGENT REQUEST
# =============================================================================
elif page == "⚡ Check Agent Request":
    render_header(
        "Deterministic Transaction Gatekeeper Engine",
        "Evaluate incoming AI agent requests against the 7 Ryanair Gatekeeper Rules",
    )

    agents = list_agents()
    active_agents = [a for a in agents if a["status"] == "ACTIVE"]

    eval_col1, eval_col2 = st.columns([3, 2])

    with eval_col1:
        st.subheader("Request Evaluation Form")

        # Quick pre-fill helper
        use_preset = st.checkbox("Quick-select from registered agents", value=False)
        selected_cust_id = ""
        selected_agent_name = ""

        if use_preset and agents:
            agent_options = [f"{a['customer_id']} | {a['agent_name']} ({a['status']})" for a in agents]
            chosen_agent_str = st.selectbox("Select Agent Profile", agent_options)
            chosen_idx = agent_options.index(chosen_agent_str)
            selected_cust_id = agents[chosen_idx]["customer_id"]
            selected_agent_name = agents[chosen_idx]["agent_name"]

        with st.form("evaluate_request_form"):
            eval_cust_id = st.text_input(
                "Customer ID*",
                value=selected_cust_id,
                placeholder="e.g., CUST-1001",
            ).strip()

            eval_agent_name = st.text_input(
                "Agent Name*",
                value=selected_agent_name,
                placeholder="e.g., BookingMate-AI",
            ).strip()

            eval_action = st.selectbox("Requested Action*", list(SUPPORTED_ACTIONS))

            # Helper hint for amounts
            amount_help = (
                "Required for Book Flight (must be > 0). "
                "For View Fares, Change Booking, and Request Refund, amount defaults to 0.00 if left empty."
            )
            eval_amount_input = st.text_input(
                "Transaction Amount in EUR (€)",
                value="150.00" if eval_action == "Book Flight" else "0.00",
                help=amount_help,
            ).strip()

            submit_eval = st.form_submit_button("⚡ EVALUATE REQUEST", use_container_width=True)

    with eval_col2:
        st.markdown(
            """
            <div style="background: #F8FAFD; border: 1px solid #E2E8F0; border-radius: 10px; padding: 20px;">
                <h4 style="color: #00205B; margin-top: 0;">📋 The Seven Rules Quick Guide</h4>
                <div style="font-size: 12px; color: #334155; line-height: 1.5;">
                    <p><strong>R1 (BLOCK):</strong> Unregistered agent.</p>
                    <p><strong>R2 (BLOCK):</strong> Revoked agent (overrides everything).</p>
                    <p><strong>R3 (ALLOW):</strong> View Fares (read-only).</p>
                    <p><strong>R4 (ALLOW):</strong> Book Flight &le; EUR 200.00.</p>
                    <p><strong>R5 (ASK CUSTOMER):</strong> Book Flight &gt; EUR 200.00.</p>
                    <p><strong>R6 (ASK CUSTOMER):</strong> Change Booking or Request Refund.</p>
                    <p><strong>R7 (BLOCK):</strong> Invalid request / unsupported action / invalid amount.</p>
                </div>
                <div style="margin-top: 10px; font-size: 11px; color: #94A3B8;">
                    <em>Strict evaluation order: 1. Registered &rarr; 2. Revoked &rarr; 3. Valid Action/Amount &rarr; 4. R3-R6</em>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # Process evaluation
    if submit_eval:
        st.markdown("---")
        st.subheader("Evaluation Result")

        # Parse amount (allow None if empty string)
        parsed_amt = eval_amount_input if eval_amount_input else None

        result = evaluate_request(
            customer_id=eval_cust_id,
            agent_name=eval_agent_name,
            action=eval_action,
            amount=parsed_amt,
        )

        # Prominent Result Card Display
        if result.decision == "ALLOW":
            st.markdown(
                f"""
                <div class="decision-card-allow">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <h2 style="margin: 0; color: #065F46;">✅ DECISION: ALLOW</h2>
                        <span class="badge-allow">RULE {result.rule}</span>
                    </div>
                    <p style="font-size: 16px; font-weight: 600; margin: 12px 0 6px 0;">{result.explanation}</p>
                    <div style="font-size: 13px; color: #047857; margin-top: 8px;">
                        Status: <strong>{result.status}</strong> &bull; Request ID: <code>{result.request_id}</code>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        elif result.decision == "ASK CUSTOMER":
            st.markdown(
                f"""
                <div class="decision-card-ask">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <h2 style="margin: 0; color: #92400E;">⚠️ DECISION: ASK CUSTOMER</h2>
                        <span class="badge-ask">RULE {result.rule}</span>
                    </div>
                    <p style="font-size: 16px; font-weight: 600; margin: 12px 0 6px 0;">{result.explanation}</p>
                    <div style="font-size: 13px; color: #B45309; margin-top: 8px;">
                        Status: <strong>{result.status}</strong> (Placed in Customer Approvals Queue) &bull; Request ID: <code>{result.request_id}</code>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:  # BLOCK
            st.markdown(
                f"""
                <div class="decision-card-block">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <h2 style="margin: 0; color: #991B1B;">🚫 DECISION: BLOCK</h2>
                        <span class="badge-block">RULE {result.rule}</span>
                    </div>
                    <p style="font-size: 16px; font-weight: 600; margin: 12px 0 6px 0;">{result.explanation}</p>
                    <div style="font-size: 13px; color: #B91C1C; margin-top: 8px;">
                        Status: <strong>{result.status}</strong> &bull; Request ID: <code>{result.request_id}</code>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        # Full Request Breakdown Table
        st.markdown("#### Transaction Summary Details")
        breakdown_data = {
            "Field": [
                "Decision",
                "Rule Number",
                "Official Gatekeeper Explanation",
                "Customer ID",
                "Agent Name",
                "Agent ID",
                "Action Requested",
                "Evaluated Amount (EUR)",
                "Execution Status",
                "Timestamp (IST)",
            ],
            "Value": [
                result.decision,
                result.rule,
                result.explanation,
                result.customer_id,
                result.agent_name,
                result.agent_id if result.agent_id else "UNREGISTERED",
                result.action,
                f"€ {result.amount}" if result.amount is not None else "N/A",
                result.status,
                result.timestamp,
            ],
        }
        st.table(pd.DataFrame(breakdown_data))
        st.info("ℹ️ **Simulation Notice:** All evaluated requests are securely recorded in the permanent audit log. No real bookings, payment transactions, or refunds are executed.")


# =============================================================================
# PAGE 4: REVOKE AGENT
# =============================================================================
elif page == "🚫 Revoke Agent":
    render_header(
        "Agent Lifecycle & Permission Revocation",
        "Explicit withdrawal of external AI agent permissions with non-repudiation logging",
    )

    agents = list_agents()
    active_agents = [a for a in agents if a["status"] == "ACTIVE"]

    rev_col1, rev_col2 = st.columns([3, 2])

    with rev_col1:
        st.subheader("Revoke Agent Authorization")

        if not active_agents:
            st.warning("There are currently no ACTIVE agents registered in the database.")
        else:
            agent_selector_options = [
                f"{a['customer_id']} — {a['agent_name']} (Agent ID: {a['agent_id']})"
                for a in active_agents
            ]
            selected_to_revoke_str = st.selectbox("Select Active Agent to Revoke*", agent_selector_options)
            selected_idx = agent_selector_options.index(selected_to_revoke_str)
            target_agent = active_agents[selected_idx]

            st.markdown(
                f"""
                <div style="background: #F1F5F9; padding: 14px 18px; border-radius: 8px; margin: 12px 0;">
                    <strong>Customer:</strong> {target_agent['customer_name']} (<code>{target_agent['customer_id']}</code>)<br>
                    <strong>Agent:</strong> <code>{target_agent['agent_name']}</code> ({target_agent['agent_id']})<br>
                    <strong>Registered At:</strong> {target_agent['registered_at']} (IST)<br>
                    <strong>Current Status:</strong> <span class="badge-active">ACTIVE</span>
                </div>
                """,
                unsafe_allow_html=True,
            )

            confirm_revoke = st.checkbox(
                "I explicitly confirm that the customer has requested to withdraw this agent's permission.",
                value=False,
            )

            if st.button("🚫 Revoke Agent Permission", type="primary", use_container_width=True):
                if not confirm_revoke:
                    st.error("❌ You must check the confirmation box before revoking agent permission.")
                else:
                    try:
                        revoked_record = revoke_agent(
                            customer_id=target_agent["customer_id"],
                            agent_name=target_agent["agent_name"],
                        )
                        st.success(
                            f"✅ **Agent Permission Successfully Revoked!**  \n"
                            f"• **Agent Name:** `{revoked_record['agent_name']}` ({revoked_record['agent_id']})  \n"
                            f"• **Customer:** `{revoked_record['customer_id']}`  \n"
                            f"• **Status:** REVOKED  \n"
                            f"• **Revocation Timestamp:** `{revoked_record['revoked_at']}` (IST)  \n"
                            f"• **Non-repudiation:** Rule R2 will now permanently BLOCK all requests from this agent."
                        )
                        st.rerun()
                    except Exception as err:
                        st.error(f"❌ Revocation Error: {err}")

    with rev_col2:
        st.markdown(
            """
            <div style="background: #FEF2F2; border: 1px solid #FCA5A5; border-radius: 10px; padding: 20px;">
                <h4 style="color: #991B1B; margin-top: 0;">⚠️ Revocation Impact & R2 Enforcement</h4>
                <ul style="font-size: 13px; color: #7F1D1D; line-height: 1.6; padding-left: 20px;">
                    <li><strong>Immediate Cutoff:</strong> Status transitions immediately to <code>REVOKED</code>.</li>
                    <li><strong>Rule R2 Overrides Everything:</strong> Any future request from this agent will be blocked with: <em>"The customer has withdrawn the agent's permission."</em></li>
                    <li><strong>Overrides Invalid Input:</strong> Even if a revoked agent submits an invalid amount (e.g. EUR -1) or unsupported action, Rule R2 takes absolute precedence.</li>
                    <li><strong>Permanent Non-Repudiation:</strong> The exact date and time (IST) are immutably stored in the database and audit trail as legal proof of when permission ended.</li>
                    <li><strong>No Silent Reactivation:</strong> Re-registering the same agent name for this customer is blocked by backend rules.</li>
                </ul>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("---")

    # Full Agents Table with Current Status
    st.subheader("All Registered Agents Directory")
    if agents:
        df_all = pd.DataFrame(agents)
        cols = ["agent_id", "customer_id", "customer_name", "agent_name", "status", "registered_at", "revoked_at"]
        df_all = df_all[[c for c in cols if c in df_all.columns]]
        st.dataframe(df_all, use_container_width=True, hide_index=True)


# =============================================================================
# PAGE 5: CUSTOMER APPROVALS
# =============================================================================
elif page == "📋 Customer Approvals":
    render_header(
        "Human-in-the-Loop Customer Approvals",
        "Review and authorize requests placed in PENDING APPROVAL by Rules R5 and R6",
    )

    st.markdown(
        """
        Requests requiring explicit customer authorization (e.g., flight bookings exceeding EUR 200.00,
        booking modifications, and refunds) are saved as **`PENDING APPROVAL`**.
        Nothing is executed until the customer explicitly reviews and decides.
        """
    )

    pending_requests = list_requests(status="PENDING APPROVAL")

    if not pending_requests:
        st.success("✅ **No requests currently pending customer approval.** All transactions are resolved.")
    else:
        st.warning(f"⚠️ **{len(pending_requests)} request(s) require customer confirmation:**")

        for idx, req in enumerate(pending_requests):
            with st.expander(
                f"Request #{req['request_id']} — {req['action']} (EUR {req['amount'] or '0.00'}) by Customer {req['customer_id']}",
                expanded=True,
            ):
                col_info, col_actions = st.columns([3, 2])

                with col_info:
                    st.markdown(
                        f"""
                        **Request ID:** `{req['request_id']}`
                        **Customer ID:** `{req['customer_id']}`
                        **Agent Name:** `{req['agent_name']}` (`{req['agent_id']}`)
                        **Action:** `{req['action']}`
                        **Amount:** `€ {req['amount'] or '0.00'}`
                        **Rule Triggered:** `{req['rule_applied']}` — *{req['explanation']}*
                        **Submission Time:** `{req['timestamp']}` (IST)
                        """
                    )

                with col_actions:
                    comments = st.text_input(
                        "Customer Notes / Reason (Optional)",
                        key=f"comments_{req['request_id']}",
                        placeholder="e.g., Approved after price verification",
                    )

                    btn_col1, btn_col2 = st.columns(2)
                    with btn_col1:
                        if st.button("✅ Approve", key=f"app_{req['request_id']}", use_container_width=True):
                            update_request_approval(
                                request_id=req["request_id"],
                                customer_id=req["customer_id"],
                                decision="APPROVED",
                                comments=comments,
                            )
                            st.success(f"Request {req['request_id']} has been APPROVED.")
                            st.rerun()

                    with btn_col2:
                        if st.button("❌ Reject", key=f"rej_{req['request_id']}", use_container_width=True):
                            update_request_approval(
                                request_id=req["request_id"],
                                customer_id=req["customer_id"],
                                decision="REJECTED",
                                comments=comments,
                            )
                            st.error(f"Request {req['request_id']} has been REJECTED.")
                            st.rerun()

    st.markdown("---")

    # Approval History Table
    st.subheader("Approval Decision History")
    approvals_list = list_approvals()
    if approvals_list:
        df_approvals = pd.DataFrame(approvals_list)
        st.dataframe(df_approvals, use_container_width=True, hide_index=True)
    else:
        st.info("No approval decisions made yet.")


# =============================================================================
# PAGE 6: ABOUT PROJECT
# =============================================================================
elif page == "ℹ️ About Project":
    render_header(
        "Project Architecture & Academic Documentation",
        "MBA Agentic AI Coursework Simulation",
    )

    st.subheader("1. Project & Student Metadata")
    st.markdown(
        """
        - **Project Name:** Ryanair Agent Gatekeeper (Academic Simulation)
        - **Student:** **Pankaj Kumar Tiwari**
        - **Registration Number:** **PGD202564630**
        - **Institution:** **Shoolini University**
        - **Course:** MBA Agentic AI Assignment
        - **GitHub Repository:** [pankajk4-ui/Ryanair-Agent-Gatekeeper](https://github.com/pankajk4-ui/Ryanair-Agent-Gatekeeper)
        - **Target Enterprise:** Ryanair (Simulation only — strictly no connection to real Ryanair systems, APIs, or payment gateways).
        """
    )

    st.markdown("---")

    st.subheader("2. The Seven Deterministic Rules")
    st.markdown(
        """
        All decisions are evaluated using strictly deterministic Python logic without stochastic models or randomness.
        The rules are enforced in the following exact evaluation sequence:
        """
    )

    rules_table = {
        "Rule": ["R1", "R2", "R3", "R4", "R5", "R6", "R7"],
        "Name": [
            "Unknown Agent",
            "Revoked Agent",
            "View Fares",
            "Book Flight (Low Value)",
            "Book Flight (High Value)",
            "Arrangement Modifications",
            "Invalid Request",
        ],
        "Condition": [
            "Customer ID and agent identity not registered",
            "Registered agent in REVOKED status (overrides all inputs)",
            "Registered, active agent requests 'View Fares'",
            "Registered, active agent requests 'Book Flight' <= EUR 200.00",
            "Registered, active agent requests 'Book Flight' > EUR 200.00",
            "Requested action is 'Change Booking' or 'Request Refund'",
            "Unsupported action, missing details, or invalid amount",
        ],
        "Decision": [
            "BLOCK",
            "BLOCK",
            "ALLOW",
            "ALLOW",
            "ASK CUSTOMER",
            "ASK CUSTOMER",
            "BLOCK",
        ],
        "Official Gatekeeper Explanation": [
            "The agent has not been authorised by the customer.",
            "The customer has withdrawn the agent's permission.",
            "Viewing fares is read-only.",
            "Registering the agent counts as the customer's authorisation of this limit.",
            "High-value bookings need explicit customer confirmation.",
            "These affect existing travel arrangements and financial entitlements.",
            "Invalid request: unsupported action, missing details, or invalid amount.",
        ],
    }
    st.table(pd.DataFrame(rules_table))

    st.markdown("---")

    st.subheader("3. EUR 200 Limit Rationale")
    st.markdown(
        """
        > **Academic Placeholder:**
        > *<I will fill in after checking Ryanair's average fare>*
        """
    )

    st.markdown("---")

    st.subheader("4. Production Enterprise Security Architecture Note")
    st.markdown(
        """
        In this academic simulation, agent identity is represented as the normalized tuple `(customer_id, agent_name)`
        with a generated `Agent ID`.

        **In a real-world enterprise production environment:**
        - **Cryptographic Authentication:** Identity would be verified using Mutual TLS (mTLS) with client certificates issued by an airline Public Key Infrastructure (PKI).
        - **OAuth 2.0 / OpenID Connect:** Delegated authorization would use cryptographically signed JSON Web Tokens (JWTs) with fine-grained RFC 6749 scopes (e.g., `scope: "fares:read booking:create:max200"`).
        - **Hardware-backed Proofs:** AI agents running on edge devices would sign requests with Secure Enclave / TPM hardware keys for non-repudiation.
        - **Zero Trust Architecture:** Every request would be independently authenticated, authorized, and logged to an immutable distributed ledger or WORM (Write Once, Read Many) storage.
        """
    )
