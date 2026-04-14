"""
Revenue — payments, session revenue, Stripe funnel.
Scaffold page: most data is empty pre-launch. Shows data as it arrives.
"""

import plotly.graph_objects as go
import streamlit as st

from utils.db import query

st.set_page_config(page_title="Reroll | Revenue", page_icon="💰", layout="wide")
st.title("💰 Revenue")
st.caption("Session revenue, payment trends, and Stripe Connect funnel")

# ---------------------------------------------------------------------------
# Load
# ---------------------------------------------------------------------------

daily_payments = query("SELECT * FROM gold.fact_daily_payments ORDER BY order_date")
session_rev    = query("SELECT * FROM gold.fact_session_revenue ORDER BY payment_date")
stripe_funnel  = query("SELECT * FROM gold.fact_stripe_connect_funnel ORDER BY event_date")
funnel         = query("SELECT * FROM gold.fact_session_funnel")
coach_prices   = query("SELECT * FROM gold.fact_coach_price_history ORDER BY event_date LIMIT 50")

# ---------------------------------------------------------------------------
# KPIs
# ---------------------------------------------------------------------------

has_revenue = not session_rev.empty and int(session_rev["sessions_paid"].sum()) > 0

total_rev_pence = int(session_rev["daily_revenue_pence"].sum()) if has_revenue else 0
total_rev_gbp   = total_rev_pence / 100
sessions_paid   = int(session_rev["sessions_paid"].sum()) if has_revenue else 0

k1, k2, k3, k4 = st.columns(4)
k1.metric("Total Revenue", f"£{total_rev_gbp:,.2f}")
k2.metric("Sessions Paid", sessions_paid)
k3.metric(
    "Avg Revenue / Session",
    f"£{total_rev_gbp/sessions_paid:.2f}" if sessions_paid > 0 else "—"
)
k4.metric("Stripe-Connected Coaches", 0, help="Prerequisite for any revenue")

# ---------------------------------------------------------------------------
# Pre-launch notice or live charts
# ---------------------------------------------------------------------------

if not has_revenue:
    st.markdown("---")
    st.info(
        "**No revenue data yet.** This page will populate automatically once sessions are paid. "
        "Charts are built and ready — they'll fill in as data arrives."
    )

    st.markdown("### What you'll see here at launch")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(
            """
            **Daily Revenue**
            - GMV (gross) vs Net Revenue
            - Cumulative revenue curve
            - Payment conversion rate trend

            **Session Revenue**
            - Revenue by session
            - Avg session value over time
            - Refund rate
            """
        )
    with col2:
        st.markdown(
            """
            **Stripe Funnel**
            - Coaches connected per day
            - Cumulative onboarded coaches
            - Days from registration to Stripe connection

            **Coach Pricing**
            - Price change events
            - Price distribution across active coaches
            """
        )

    st.markdown("---")
    st.subheader("Pre-Launch Checklist")
    st.markdown(
        """
        Before revenue can flow:
        - [ ] Coaches connect Stripe Express (currently 0 / 55 connected)
        - [ ] First paid session completed end-to-end
        - [ ] Stripe webhook confirmed working in production
        - [ ] Payout schedule confirmed with Stripe (typically T+2)
        """
    )
else:
    # ---------------------------------------------------------------------------
    # Live revenue charts
    # ---------------------------------------------------------------------------

    st.markdown("---")
    col_left, col_right = st.columns(2)

    with col_left:
        st.subheader("Daily Revenue (£)")
        fig = go.Figure()
        if not daily_payments.empty:
            fig.add_trace(go.Bar(
                x=daily_payments["order_date"],
                y=(daily_payments["net_revenue_pence"].astype(float) / 100).round(2),
                name="Net Revenue", marker_color="#27AE60",
            ))
            fig.add_trace(go.Bar(
                x=daily_payments["order_date"],
                y=(daily_payments["refund_volume_pence"].astype(float) / 100).round(2),
                name="Refunds", marker_color="#E74C3C",
            ))
        fig.update_layout(
            barmode="overlay",
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font_color="#E8EDF2", legend=dict(bgcolor="rgba(0,0,0,0)"),
            xaxis=dict(gridcolor="#2A3A50"), yaxis=dict(gridcolor="#2A3A50"),
            margin=dict(l=0, r=0, t=10, b=0), height=300,
        )
        st.plotly_chart(fig, use_container_width=True)

    with col_right:
        st.subheader("Cumulative Revenue (£)")
        if not session_rev.empty:
            fig = go.Figure(go.Scatter(
                x=session_rev["payment_date"],
                y=(session_rev["cumulative_revenue_pence"].astype(float) / 100).round(2),
                line=dict(color="#F5A623", width=3),
                fill="tozeroy", fillcolor="rgba(245,166,35,0.1)",
            ))
            fig.update_layout(
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                font_color="#E8EDF2",
                xaxis=dict(gridcolor="#2A3A50"),
                yaxis=dict(title="£", gridcolor="#2A3A50"),
                margin=dict(l=0, r=0, t=10, b=0), height=300,
            )
            st.plotly_chart(fig, use_container_width=True)

    # Session funnel metrics
    st.subheader("Session Funnel Rates")
    if not funnel.empty:
        row = funnel.iloc[0]
        m1, m2, m3 = st.columns(3)
        m1.metric(
            "Payment Rate",
            f"{float(row['payment_rate'])*100:.1f}%" if row["payment_rate"] else "—",
            help="% of created sessions that get paid",
        )
        m2.metric(
            "Response Rate",
            f"{float(row['response_rate'])*100:.1f}%" if row["response_rate"] else "—",
            help="% of paid sessions where coach responds",
        )
        m3.metric(
            "Completion Rate",
            f"{float(row['completion_rate'])*100:.1f}%" if row["completion_rate"] else "—",
            help="% of sessions that reach closed status",
        )

    # Stripe connect funnel
    if not stripe_funnel.empty and int(stripe_funnel["coaches_connected"].sum()) > 0:
        st.subheader("Stripe Coach Onboarding")
        fig = go.Figure(go.Scatter(
            x=stripe_funnel["event_date"],
            y=stripe_funnel["cumulative_coaches_connected"].astype(float),
            line=dict(color="#5DADE2", width=3),
            fill="tozeroy", fillcolor="rgba(93,173,226,0.1)",
        ))
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font_color="#E8EDF2",
            xaxis=dict(gridcolor="#2A3A50"), yaxis=dict(gridcolor="#2A3A50"),
            margin=dict(l=0, r=0, t=10, b=0), height=260,
        )
        st.plotly_chart(fig, use_container_width=True)
