"""
Reroll Executive Dashboard — Home

Top-level KPIs and platform health snapshot.
"""

import plotly.graph_objects as go
import streamlit as st

from utils.db import query

st.set_page_config(
    page_title="Reroll | Overview",
    page_icon="🥋",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("🥋 Reroll")
st.caption("Executive Dashboard — refreshed hourly")

# ---------------------------------------------------------------------------
# Load data
# ---------------------------------------------------------------------------

users        = query("SELECT role, COUNT(*) AS cnt FROM gold.dim_users GROUP BY role")
coach_ready  = query("SELECT * FROM gold.fact_coach_readiness")
funnel       = query("SELECT * FROM gold.fact_session_funnel")
signups      = query("""
    SELECT signup_date, role, cumulative_signups
    FROM gold.fact_daily_role_signups
    ORDER BY signup_date
""")
belt_today   = query("""
    SELECT belt, user_count
    FROM gold.fact_daily_belt_snapshot
    WHERE date_day = (SELECT MAX(date_day) FROM gold.fact_daily_belt_snapshot)
    ORDER BY user_count DESC
""")
cohorts      = query("SELECT * FROM gold.fact_signup_cohorts ORDER BY signup_week")

# ---------------------------------------------------------------------------
# KPI helpers
# ---------------------------------------------------------------------------

def _kpi(col, label: str, value, delta=None, delta_label: str = "", alert: bool = False):
    with col:
        if alert:
            st.markdown(
                f"""
                <div style="background:#3D1515;border:1px solid #E74C3C;border-radius:8px;padding:16px 20px;">
                    <div style="font-size:12px;color:#E8EDF2;opacity:0.7;margin-bottom:4px;">{label}</div>
                    <div style="font-size:32px;font-weight:700;color:#E74C3C;">{value}</div>
                    {f'<div style="font-size:12px;color:#E74C3C;margin-top:4px;">{delta_label}</div>' if delta_label else ''}
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f"""
                <div style="background:#1A2535;border:1px solid #2A3A50;border-radius:8px;padding:16px 20px;">
                    <div style="font-size:12px;color:#E8EDF2;opacity:0.7;margin-bottom:4px;">{label}</div>
                    <div style="font-size:32px;font-weight:700;color:#F5A623;">{value}</div>
                    {f'<div style="font-size:12px;color:#8E9BAD;margin-top:4px;">{delta_label}</div>' if delta_label else ''}
                </div>
                """,
                unsafe_allow_html=True,
            )

# ---------------------------------------------------------------------------
# Compute values
# ---------------------------------------------------------------------------

total_users  = int(users["cnt"].sum()) if not users.empty else 0
total_coaches = int(users.loc[users["role"] == "Coach", "cnt"].sum()) if not users.empty else 0
total_students = int(users.loc[users["role"] == "Student", "cnt"].sum()) if not users.empty else 0

stripe_connected = int(coach_ready["stripe_connected"].iloc[0]) if not coach_ready.empty else 0
accepting = int(coach_ready["accepting_coaching"].iloc[0]) if not coach_ready.empty else 0
stripe_pct = round(stripe_connected / total_coaches * 100) if total_coaches > 0 else 0

sessions_created = int(funnel["sessions_created"].iloc[0]) if not funnel.empty else 0
payment_rate_raw = funnel["payment_rate"].iloc[0] if not funnel.empty else None
payment_rate = f"{float(payment_rate_raw)*100:.0f}%" if payment_rate_raw else "—"

avg_conv_days = cohorts["avg_days_to_convert"].mean() if not cohorts.empty else None

# ---------------------------------------------------------------------------
# KPI Row
# ---------------------------------------------------------------------------

st.markdown("### Platform Overview")
k1, k2, k3, k4, k5 = st.columns(5)

_kpi(k1, "Total Users", total_users)
_kpi(k2, "Students", total_students)
_kpi(k3, "Coaches", total_coaches, delta_label=f"{accepting} accepting sessions")
_kpi(
    k4,
    "Stripe Connected",
    f"{stripe_connected} / {total_coaches}",
    delta_label=f"{stripe_pct}% of coaches — NEEDS ACTION" if stripe_pct == 0 else f"{stripe_pct}% of coaches",
    alert=(stripe_pct == 0),
)
_kpi(k5, "Sessions Created", sessions_created if sessions_created > 0 else "0", delta_label="No live sessions yet" if sessions_created == 0 else f"{payment_rate} payment rate")

st.markdown("<br>", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Alert banner if no Stripe connections
# ---------------------------------------------------------------------------

if stripe_connected == 0:
    st.error(
        f"**Action required:** {total_coaches} coaches have registered but **none have connected Stripe**. "
        "No revenue can flow until coaches complete onboarding. "
        "Consider an activation email campaign or in-app prompt."
    )

# ---------------------------------------------------------------------------
# Two-column charts
# ---------------------------------------------------------------------------

col_left, col_right = st.columns(2)

# Cumulative signups
with col_left:
    st.markdown("#### User Growth")
    if not signups.empty:
        students_df = signups[signups["role"] == "Student"]
        coaches_df  = signups[signups["role"] == "Coach"]
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=students_df["signup_date"], y=students_df["cumulative_signups"].astype(float),
            name="Students", line=dict(color="#F5A623", width=2), fill="tozeroy",
            fillcolor="rgba(245,166,35,0.1)",
        ))
        fig.add_trace(go.Scatter(
            x=coaches_df["signup_date"], y=coaches_df["cumulative_signups"].astype(float),
            name="Coaches", line=dict(color="#5DADE2", width=2),
        ))
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font_color="#E8EDF2", legend=dict(bgcolor="rgba(0,0,0,0)"),
            margin=dict(l=0, r=0, t=10, b=0), height=260,
            xaxis=dict(gridcolor="#2A3A50"), yaxis=dict(gridcolor="#2A3A50"),
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No signup data yet.")

# Belt distribution donut
with col_right:
    st.markdown("#### Belt Distribution (Today)")
    if not belt_today.empty:
        BELT_COLORS = {
            "White": "#E8EDF2", "Blue": "#3B82F6", "Purple": "#8B5CF6",
            "Brown": "#92400E", "Black": "#374151",
        }
        colors = [BELT_COLORS.get(b, "#8E9BAD") for b in belt_today["belt"]]
        fig = go.Figure(go.Pie(
            labels=belt_today["belt"],
            values=belt_today["user_count"],
            hole=0.55,
            marker=dict(colors=colors, line=dict(color="#0F1923", width=2)),
            textinfo="label+percent",
            textfont=dict(color="#E8EDF2"),
        ))
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font_color="#E8EDF2", showlegend=False,
            margin=dict(l=0, r=0, t=10, b=0), height=260,
            annotations=[dict(
                text=f"<b>{int(belt_today['user_count'].sum())}</b><br>users",
                x=0.5, y=0.5, font_size=18, font_color="#E8EDF2", showarrow=False,
            )],
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No belt data yet.")

# ---------------------------------------------------------------------------
# Coach readiness bar
# ---------------------------------------------------------------------------

st.markdown("#### Coach Activation Funnel")
if not coach_ready.empty:
    stages = ["Registered", "Accepting Sessions", "Stripe Connected"]
    values = [total_coaches, accepting, stripe_connected]
    colors_bar = ["#5DADE2", "#F5A623", "#27AE60" if stripe_connected > 0 else "#E74C3C"]
    fig = go.Figure(go.Bar(
        x=stages, y=values, marker_color=colors_bar,
        text=values, textposition="outside", textfont=dict(color="#E8EDF2"),
    ))
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font_color="#E8EDF2", showlegend=False,
        margin=dict(l=0, r=0, t=20, b=0), height=200,
        xaxis=dict(gridcolor="#2A3A50"), yaxis=dict(gridcolor="#2A3A50"),
    )
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("No coach data yet.")

# ---------------------------------------------------------------------------
# Footer
# ---------------------------------------------------------------------------

st.markdown("---")
st.caption("Data: Neon PostgreSQL → dbt gold layer → viz_reader role. Use the sidebar to explore detailed views.")
