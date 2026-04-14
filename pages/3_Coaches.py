"""
Coaches — readiness, activation funnel, Stripe connection status, expertise by belt.
"""

import plotly.graph_objects as go
import streamlit as st

from utils.db import query

st.set_page_config(page_title="Reroll | Coaches", page_icon="🎯", layout="wide")
st.title("🎯 Coach Readiness")
st.caption("Stripe activation, session capacity, and coach profile depth")

# ---------------------------------------------------------------------------
# Load
# ---------------------------------------------------------------------------

readiness    = query("SELECT * FROM gold.fact_coach_readiness")
belt_stats   = query("SELECT * FROM gold.fact_belt_profile_stats ORDER BY belt")
leaderboard  = query("SELECT * FROM gold.dim_coach_leaderboard ORDER BY rank_by_total_sessions LIMIT 20")
funnel       = query("SELECT * FROM gold.fact_session_funnel")

# ---------------------------------------------------------------------------
# KPIs
# ---------------------------------------------------------------------------

total_coaches    = int(readiness["total_coaches"].iloc[0])   if not readiness.empty else 0
stripe_connected = int(readiness["stripe_connected"].iloc[0]) if not readiness.empty else 0
accepting        = int(readiness["accepting_coaching"].iloc[0]) if not readiness.empty else 0

stripe_pct   = stripe_connected / total_coaches * 100 if total_coaches > 0 else 0
accepting_pct = accepting / total_coaches * 100 if total_coaches > 0 else 0

k1, k2, k3, k4 = st.columns(4)
k1.metric("Registered Coaches", total_coaches)
k2.metric(
    "Stripe Connected",
    stripe_connected,
    delta=f"{stripe_pct:.0f}% of coaches",
    delta_color="off" if stripe_connected == 0 else "normal",
)
k3.metric("Accepting Sessions", accepting, delta=f"{accepting_pct:.0f}% of coaches")
k4.metric("Payment-Ready Coaches", stripe_connected, help="Only Stripe-connected coaches can receive payouts")

# ---------------------------------------------------------------------------
# Alert
# ---------------------------------------------------------------------------

if stripe_connected == 0:
    st.error(
        "**Critical: 0 coaches have connected Stripe.** "
        f"All {total_coaches} coaches who registered are accepting sessions in-app, but no revenue can flow "
        "until they complete Stripe Express onboarding. This is the #1 activation blocker before launch."
    )
    st.markdown(
        "**Recommended actions:**\n"
        "- Add an in-app prompt during coach onboarding that gates 'Go Live' on Stripe connection\n"
        "- Email all registered coaches with a direct link to Stripe Express setup\n"
        "- Track weekly Stripe connection rate as a KPI"
    )
elif stripe_connected < total_coaches:
    st.warning(
        f"{total_coaches - stripe_connected} coaches have not connected Stripe. "
        "They cannot receive payment for sessions."
    )

st.markdown("---")

# ---------------------------------------------------------------------------
# Activation funnel
# ---------------------------------------------------------------------------

st.subheader("Coach Activation Funnel")

if not readiness.empty:
    stages = ["Registered", "Accepting Sessions", "Stripe Connected"]
    values = [total_coaches, accepting, stripe_connected]
    pcts   = [100, accepting_pct, stripe_pct]
    colors = [
        "#5DADE2",
        "#F5A623" if accepting_pct >= 50 else "#E74C3C",
        "#27AE60" if stripe_pct >= 50 else "#E74C3C",
    ]

    col_funnel, col_detail = st.columns([2, 1])

    with col_funnel:
        fig = go.Figure(go.Funnel(
            y=stages,
            x=values,
            textinfo="value+percent initial",
            marker=dict(color=colors),
            textfont=dict(color="#E8EDF2"),
            connector=dict(line=dict(color="#2A3A50", width=2)),
        ))
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font_color="#E8EDF2",
            margin=dict(l=0, r=0, t=10, b=0), height=300,
        )
        st.plotly_chart(fig, use_container_width=True)

    with col_detail:
        st.markdown("**Stage breakdown**")
        for stage, val, pct in zip(stages, values, pcts):
            bar_color = "#27AE60" if pct == 100 else "#F5A623" if pct > 0 else "#E74C3C"
            st.markdown(f"**{stage}**")
            st.progress(int(pct) / 100, text=f"{val} ({pct:.0f}%)")
        st.markdown("")
        st.caption("A coach must be Stripe-connected before they can receive payouts from sessions.")
else:
    st.info("No coach data yet.")

# ---------------------------------------------------------------------------
# Coach expertise by belt
# ---------------------------------------------------------------------------

st.subheader("Avg Coach Expertise Areas by Belt")
if not belt_stats.empty:
    bs = belt_stats.dropna(subset=["avg_expertise_count"])
    BELT_COLORS = {
        "White":  "#E8EDF2", "Blue": "#3B82F6",
        "Purple": "#8B5CF6", "Brown": "#92400E", "Black": "#374151",
    }
    fig = go.Figure(go.Bar(
        x=bs["belt"],
        y=bs["avg_expertise_count"].astype(float).round(2),
        marker_color=[BELT_COLORS.get(b, "#8E9BAD") for b in bs["belt"]],
        text=[f"{float(v):.1f}" for v in bs["avg_expertise_count"]],
        textposition="outside",
        textfont=dict(color="#E8EDF2"),
    ))
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font_color="#E8EDF2",
        xaxis=dict(gridcolor="#2A3A50"),
        yaxis=dict(title="Avg expertise areas listed", gridcolor="#2A3A50"),
        margin=dict(l=0, r=0, t=20, b=0), height=280,
    )
    st.plotly_chart(fig, use_container_width=True)
    st.caption("Brown belt coaches list the most expertise areas — likely the most engaged coaches on the platform.")

# ---------------------------------------------------------------------------
# Session funnel (coach perspective)
# ---------------------------------------------------------------------------

st.subheader("Session Funnel (All-Time)")
if not funnel.empty and int(funnel["sessions_created"].iloc[0]) > 0:
    row = funnel.iloc[0]
    stages = ["Created", "Paid", "Coach Responded", "Closed", "Cancelled", "Refunded"]
    values = [
        int(row["sessions_created"]),
        int(row["sessions_paid"]),
        int(row["sessions_with_coach_response"]),
        int(row["sessions_closed"]),
        int(row["sessions_cancelled"]),
        int(row["sessions_refunded"]),
    ]
    fig = go.Figure(go.Bar(
        x=stages, y=values,
        marker_color=["#5DADE2","#F5A623","#27AE60","#27AE60","#E74C3C","#E74C3C"],
        text=values, textposition="outside", textfont=dict(color="#E8EDF2"),
    ))
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font_color="#E8EDF2",
        xaxis=dict(gridcolor="#2A3A50"), yaxis=dict(gridcolor="#2A3A50"),
        margin=dict(l=0, r=0, t=20, b=0), height=280,
    )
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("No sessions yet — data will appear here once coaches start taking sessions.")
    st.markdown(
        "Key metrics to track when sessions begin:\n"
        "- **Payment rate** — % of sessions that get paid\n"
        "- **Response rate** — % of paid sessions where coach responds\n"
        "- **Completion rate** — % that reach closed status\n"
        "- **Avg hours to first response** — quality signal for students"
    )

# ---------------------------------------------------------------------------
# Leaderboard
# ---------------------------------------------------------------------------

st.subheader("Coach Leaderboard")
if not leaderboard.empty:
    display = leaderboard[[
        "coach_username", "coach_belt", "is_stripe_connected",
        "is_accepting_coaching", "total_sessions", "response_rate",
        "rank_by_response_rate",
    ]].copy()
    display.columns = ["Username", "Belt", "Stripe", "Accepting", "Sessions", "Response Rate", "Rank"]
    display["Stripe"]    = display["Stripe"].map({True: "Yes", False: "No"})
    display["Accepting"] = display["Accepting"].map({True: "Yes", False: "No"})
    display["Response Rate"] = display["Response Rate"].apply(
        lambda x: f"{float(x)*100:.0f}%" if x is not None else "—"
    )
    st.dataframe(display, use_container_width=True, hide_index=True)
else:
    st.info("No session activity yet. Leaderboard will populate once coaches complete sessions.")
