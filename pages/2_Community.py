"""
Community — belt distribution, user profiles, student breakdown.
"""

import plotly.graph_objects as go
import streamlit as st
import pandas as pd

from utils.db import query

st.set_page_config(page_title="Reroll | Community", page_icon="🏅", layout="wide")
st.title("🏅 Community")
st.caption("Belt distribution, user demographics, and platform composition")

# ---------------------------------------------------------------------------
# Load
# ---------------------------------------------------------------------------

belt_history  = query("SELECT * FROM gold.fact_daily_belt_snapshot ORDER BY date_day")
belt_today    = query("""
    SELECT belt, user_count
    FROM gold.fact_daily_belt_snapshot
    WHERE date_day = (SELECT MAX(date_day) FROM gold.fact_daily_belt_snapshot)
    ORDER BY
        CASE belt
            WHEN 'White'  THEN 1
            WHEN 'Blue'   THEN 2
            WHEN 'Purple' THEN 3
            WHEN 'Brown'  THEN 4
            WHEN 'Black'  THEN 5
            ELSE 6
        END
""")
belt_stats    = query("SELECT * FROM gold.fact_belt_profile_stats ORDER BY belt")
role_changes  = query("SELECT * FROM gold.fact_daily_role_changes ORDER BY event_date")

# ---------------------------------------------------------------------------
# Belt colour map
# ---------------------------------------------------------------------------

BELT_COLORS = {
    "White":  "#E8EDF2",
    "Blue":   "#3B82F6",
    "Purple": "#8B5CF6",
    "Brown":  "#92400E",
    "Black":  "#374151",
}

# ---------------------------------------------------------------------------
# KPIs
# ---------------------------------------------------------------------------

total_users = int(belt_today["user_count"].sum()) if not belt_today.empty else 0
white_pct   = 0
if not belt_today.empty and total_users > 0:
    w = belt_today.loc[belt_today["belt"] == "White", "user_count"]
    white_pct = int(w.iloc[0]) / total_users * 100 if not w.empty else 0

k1, k2, k3, k4 = st.columns(4)
k1.metric("Total Users", total_users)
k2.metric("White Belts", f"{white_pct:.0f}%", help="Largest segment — growth opportunity")
k3.metric("Blue + Above", f"{100-white_pct:.0f}%")
k4.metric("Belt Levels Represented", int(belt_today["belt"].nunique()) if not belt_today.empty else 0)

st.markdown("---")

# ---------------------------------------------------------------------------
# Belt distribution over time (stacked area)
# ---------------------------------------------------------------------------

st.subheader("Belt Distribution Over Time")

if not belt_history.empty:
    belt_order = ["White", "Blue", "Purple", "Brown", "Black"]
    fig = go.Figure()
    for belt in belt_order:
        df_b = belt_history[belt_history["belt"] == belt]
        if df_b.empty:
            continue
        fig.add_trace(go.Scatter(
            x=df_b["date_day"],
            y=df_b["user_count"],
            name=belt,
            stackgroup="one",
            line=dict(width=0),
            fillcolor=BELT_COLORS.get(belt, "#8E9BAD"),
            mode="none",
        ))
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font_color="#E8EDF2", legend=dict(bgcolor="rgba(0,0,0,0)"),
        xaxis=dict(gridcolor="#2A3A50"), yaxis=dict(gridcolor="#2A3A50"),
        margin=dict(l=0, r=0, t=10, b=0), height=340,
        hovermode="x unified",
    )
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("No belt history data yet.")

# ---------------------------------------------------------------------------
# Current snapshot + profile breakdown
# ---------------------------------------------------------------------------

col_left, col_right = st.columns(2)

with col_left:
    st.subheader("Current Belt Snapshot")
    if not belt_today.empty:
        fig = go.Figure(go.Bar(
            x=belt_today["belt"],
            y=belt_today["user_count"],
            marker_color=[BELT_COLORS.get(b, "#8E9BAD") for b in belt_today["belt"]],
            text=belt_today["user_count"],
            textposition="outside",
            textfont=dict(color="#E8EDF2"),
        ))
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font_color="#E8EDF2",
            xaxis=dict(gridcolor="#2A3A50"),
            yaxis=dict(gridcolor="#2A3A50"),
            margin=dict(l=0, r=0, t=20, b=0), height=300,
            showlegend=False,
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No data.")

with col_right:
    st.subheader("Coach vs Student Profile Coverage")
    if not belt_stats.empty:
        belt_order_disp = ["White", "Blue", "Purple", "Brown", "Black"]
        bs = belt_stats[belt_stats["belt"].isin(belt_order_disp)].copy()
        fig = go.Figure()
        fig.add_trace(go.Bar(
            name="Students with Profile",
            x=bs["belt"],
            y=bs["student_profile_count"].astype(int),
            marker_color="#F5A623",
        ))
        fig.add_trace(go.Bar(
            name="Coaches with Profile",
            x=bs["belt"],
            y=bs["coach_profile_count"].astype(int),
            marker_color="#5DADE2",
        ))
        fig.update_layout(
            barmode="group",
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font_color="#E8EDF2", legend=dict(bgcolor="rgba(0,0,0,0)"),
            xaxis=dict(gridcolor="#2A3A50"), yaxis=dict(gridcolor="#2A3A50"),
            margin=dict(l=0, r=0, t=10, b=0), height=300,
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No profile data yet.")

# ---------------------------------------------------------------------------
# Avg areas working on (white belt engagement insight)
# ---------------------------------------------------------------------------

st.subheader("Student Engagement by Belt — Avg Areas Working On")
if not belt_stats.empty:
    bs = belt_stats.dropna(subset=["avg_areas_working_on"])
    if not bs.empty:
        fig = go.Figure(go.Bar(
            x=bs["belt"],
            y=bs["avg_areas_working_on"].astype(float).round(1),
            marker_color=[BELT_COLORS.get(b, "#8E9BAD") for b in bs["belt"]],
            text=[f"{float(v):.1f}" for v in bs["avg_areas_working_on"]],
            textposition="outside",
            textfont=dict(color="#E8EDF2"),
        ))
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font_color="#E8EDF2",
            xaxis=dict(gridcolor="#2A3A50"),
            yaxis=dict(title="Avg focus areas per student", gridcolor="#2A3A50"),
            margin=dict(l=0, r=0, t=20, b=0), height=260,
        )
        st.plotly_chart(fig, use_container_width=True)
        st.caption(
            "Higher = more engaged. White belts have the highest number of focus areas — "
            "beginners know what they don't know."
        )
    else:
        st.info("No engagement data.")
else:
    st.info("No belt stats yet.")

# ---------------------------------------------------------------------------
# Role change events
# ---------------------------------------------------------------------------

st.subheader("Role Change Events Over Time")
if not role_changes.empty:
    event_types = role_changes["event_type"].unique()
    color_map = {
        "BECAME_STUDENT": "#F5A623",
        "BECAME_COACH": "#5DADE2",
        "LEFT_STUDENT": "#E74C3C",
        "LEFT_COACH": "#E74C3C",
    }
    fig = go.Figure()
    for et in event_types:
        df_e = role_changes[role_changes["event_type"] == et]
        fig.add_trace(go.Bar(
            x=df_e["event_date"],
            y=df_e["event_count"],
            name=et.replace("_", " ").title(),
            marker_color=color_map.get(et, "#8E9BAD"),
        ))
    fig.update_layout(
        barmode="group",
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font_color="#E8EDF2", legend=dict(bgcolor="rgba(0,0,0,0)"),
        xaxis=dict(gridcolor="#2A3A50"), yaxis=dict(gridcolor="#2A3A50"),
        margin=dict(l=0, r=0, t=10, b=0), height=280,
    )
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("No role change data yet.")
