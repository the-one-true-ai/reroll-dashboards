"""
Growth — signup trends, cohort analysis, conversion speed.
"""

import plotly.graph_objects as go
import plotly.express as px
import streamlit as st
import pandas as pd

from utils.db import query

st.set_page_config(page_title="Reroll | Growth", page_icon="📈", layout="wide")
st.title("📈 Growth")
st.caption("User acquisition trends, signup cohorts, and conversion performance")

# ---------------------------------------------------------------------------
# Load
# ---------------------------------------------------------------------------

signups     = query("SELECT * FROM gold.fact_daily_role_signups ORDER BY signup_date")
cohorts     = query("SELECT * FROM gold.fact_signup_cohorts ORDER BY signup_week")
role_changes = query("SELECT * FROM gold.fact_daily_role_changes ORDER BY event_date")
conversion  = query("""
    SELECT days_to_convert, COUNT(*) AS cnt
    FROM gold.fact_student_conversion
    WHERE days_to_convert IS NOT NULL
    GROUP BY days_to_convert
    ORDER BY days_to_convert
""")

# ---------------------------------------------------------------------------
# KPIs
# ---------------------------------------------------------------------------

total_students = int(signups.loc[signups["role"] == "Student", "cumulative_signups"].max()) if not signups.empty else 0
total_coaches  = int(signups.loc[signups["role"] == "Coach",   "cumulative_signups"].max()) if not signups.empty else 0
avg_conv_rate  = float(cohorts["conversion_rate"].mean()) if not cohorts.empty else 0
avg_conv_days  = float(cohorts["avg_days_to_convert"].mean()) if not cohorts.empty else 0

k1, k2, k3, k4 = st.columns(4)
k1.metric("Total Students", total_students)
k2.metric("Total Coaches", total_coaches)
k3.metric("Avg Cohort Conversion", f"{avg_conv_rate*100:.0f}%")
k4.metric("Avg Days to Convert", f"{avg_conv_days:.0f}")

st.markdown("---")

# ---------------------------------------------------------------------------
# Cumulative growth chart
# ---------------------------------------------------------------------------

st.subheader("Cumulative User Growth")

if not signups.empty:
    students_df = signups[signups["role"] == "Student"].copy()
    coaches_df  = signups[signups["role"] == "Coach"].copy()

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=students_df["signup_date"],
        y=students_df["cumulative_signups"].astype(float),
        name="Students",
        line=dict(color="#F5A623", width=3),
        fill="tozeroy",
        fillcolor="rgba(245,166,35,0.08)",
    ))
    fig.add_trace(go.Scatter(
        x=coaches_df["signup_date"],
        y=coaches_df["cumulative_signups"].astype(float),
        name="Coaches",
        line=dict(color="#5DADE2", width=3),
    ))
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font_color="#E8EDF2", legend=dict(bgcolor="rgba(0,0,0,0)"),
        xaxis=dict(gridcolor="#2A3A50"), yaxis=dict(gridcolor="#2A3A50"),
        margin=dict(l=0, r=0, t=10, b=0), height=320,
        hovermode="x unified",
    )
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("No signup data yet.")

# ---------------------------------------------------------------------------
# Daily signups bar + cohort side-by-side
# ---------------------------------------------------------------------------

col_left, col_right = st.columns(2)

with col_left:
    st.subheader("Daily New Signups")
    if not signups.empty:
        daily = signups[signups["daily_signups"] > 0].copy()
        students_d = daily[daily["role"] == "Student"]
        coaches_d  = daily[daily["role"] == "Coach"]
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=students_d["signup_date"], y=students_d["daily_signups"],
            name="Students", marker_color="#F5A623",
        ))
        fig.add_trace(go.Bar(
            x=coaches_d["signup_date"], y=coaches_d["daily_signups"],
            name="Coaches", marker_color="#5DADE2",
        ))
        fig.update_layout(
            barmode="stack",
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font_color="#E8EDF2", legend=dict(bgcolor="rgba(0,0,0,0)"),
            xaxis=dict(gridcolor="#2A3A50"), yaxis=dict(gridcolor="#2A3A50"),
            margin=dict(l=0, r=0, t=10, b=0), height=300,
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No signup data yet.")

with col_right:
    st.subheader("Weekly Cohort Conversion Rate")
    if not cohorts.empty:
        cohorts["week_label"] = pd.to_datetime(cohorts["signup_week"]).dt.strftime("%b %d")
        cohorts["conv_pct"] = cohorts["conversion_rate"].astype(float) * 100
        fig = go.Figure(go.Bar(
            x=cohorts["week_label"],
            y=cohorts["conv_pct"],
            marker_color=[
                "#27AE60" if v >= 70 else "#F5A623" if v >= 50 else "#E74C3C"
                for v in cohorts["conv_pct"]
            ],
            text=[f"{v:.0f}%" for v in cohorts["conv_pct"]],
            textposition="outside",
            textfont=dict(color="#E8EDF2"),
        ))
        fig.add_hline(
            y=70, line_dash="dash", line_color="#27AE60",
            annotation_text="70% target", annotation_font_color="#27AE60",
        )
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font_color="#E8EDF2",
            xaxis=dict(gridcolor="#2A3A50"), yaxis=dict(gridcolor="#2A3A50", range=[0, 110]),
            margin=dict(l=0, r=0, t=10, b=0), height=300,
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No cohort data yet.")

# ---------------------------------------------------------------------------
# Cohort detail table
# ---------------------------------------------------------------------------

st.subheader("Cohort Detail")
if not cohorts.empty:
    display = cohorts[["signup_week","cohort_size","converted_to_student","conversion_rate","avg_days_to_convert"]].copy()
    display.columns = ["Week", "Signups", "Converted", "Conversion %", "Avg Days to Convert"]
    display["Conversion %"] = display["Conversion %"].apply(lambda x: f"{float(x)*100:.1f}%")
    display["Avg Days to Convert"] = display["Avg Days to Convert"].apply(lambda x: f"{float(x):.1f}" if x else "—")
    st.dataframe(display, use_container_width=True, hide_index=True)
else:
    st.info("No cohort data yet.")

# ---------------------------------------------------------------------------
# Days to convert histogram
# ---------------------------------------------------------------------------

st.subheader("How Quickly Do Users Convert?")
if not conversion.empty:
    fig = go.Figure(go.Bar(
        x=conversion["days_to_convert"],
        y=conversion["cnt"],
        marker_color="#F5A623",
    ))
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font_color="#E8EDF2",
        xaxis=dict(title="Days from signup to first student action", gridcolor="#2A3A50"),
        yaxis=dict(title="Users", gridcolor="#2A3A50"),
        margin=dict(l=0, r=0, t=10, b=0), height=280,
    )
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("No conversion data yet.")
