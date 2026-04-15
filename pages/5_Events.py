"""
Events — global BJJ competition map and geographic breakdown.

Data: gold.dim_events (sourced from Smoothcomp, enriched with GeoNames city coords
and ref_country_regions for continent / demographic / commercial region).
"""

import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import pandas as pd

from utils.db import query

st.set_page_config(page_title="Reroll | Events", page_icon="🌍", layout="wide")
st.title("🌍 BJJ Events")
st.caption("Global competition landscape — sourced from Smoothcomp, updated monthly.")

# ---------------------------------------------------------------------------
# Load
# ---------------------------------------------------------------------------

events = query("""
    SELECT
        event_name,
        event_date,
        is_lapsed,
        city,
        country,
        continent,
        demographic_region,
        commercial_region,
        city_id,
        city_match_method,
        lat::float  AS lat,
        lng::float  AS lng,
        organizer,
        source
    FROM gold.dim_events
    WHERE event_date IS NOT NULL
    ORDER BY event_date DESC
""")

match_quality = query("""
    SELECT
        count(*)                                                               AS total,
        count(city_id)                                                         AS matched,
        round(count(city_id)::numeric / nullif(count(*), 0) * 100, 1)        AS match_pct,
        count(*) - count(city_id)                                              AS unmatched
    FROM gold.dim_events
    WHERE city IS NOT NULL
      AND country IS NOT NULL
""")

unmatched_cities = query("""
    SELECT city, country, count(*) AS events
    FROM gold.dim_events
    WHERE city IS NOT NULL
      AND city_id IS NULL
    GROUP BY city, country
    ORDER BY events DESC
    LIMIT 25
""")

# ---------------------------------------------------------------------------
# Sidebar filters
# ---------------------------------------------------------------------------

with st.sidebar:
    st.markdown("### Filters")

    all_regions = sorted(events["commercial_region"].dropna().unique().tolist())
    sel_regions = st.multiselect("Commercial region", all_regions, default=all_regions)

    if not events.empty and "event_date" in events.columns:
        events["event_date"] = pd.to_datetime(events["event_date"])
        min_year = int(events["event_date"].dt.year.min())
        max_year = int(events["event_date"].dt.year.max())
        year_range = st.slider("Event year", min_year, max_year, (min_year, max_year))
    else:
        year_range = (2020, 2030)

    show_upcoming = st.toggle("Upcoming events only", value=False)

# Apply filters
df = events.copy()
if sel_regions:
    df = df[df["commercial_region"].isin(sel_regions)]
df = df[
    (df["event_date"].dt.year >= year_range[0]) &
    (df["event_date"].dt.year <= year_range[1])
]
if show_upcoming:
    df = df[~df["is_lapsed"]]

# ---------------------------------------------------------------------------
# KPIs
# ---------------------------------------------------------------------------

total_events  = len(df)
countries     = df["country"].nunique()
cities_with_coords = df.dropna(subset=["lat", "lng"])["city"].nunique()

mq = match_quality.iloc[0] if not match_quality.empty else None
match_pct = float(mq["match_pct"]) if mq is not None and mq["match_pct"] is not None else 0.0
match_color = "normal" if match_pct >= 95 else "inverse"

k1, k2, k3, k4 = st.columns(4)
k1.metric("Events (filtered)", f"{total_events:,}")
k2.metric("Countries", countries)
k3.metric("Cities on map", f"{cities_with_coords:,}")
k4.metric(
    "City match rate",
    f"{match_pct:.1f}%",
    delta="≥95% target" if match_pct >= 95 else f"{95 - match_pct:.1f}pp below target",
    delta_color="off" if match_pct >= 95 else "inverse",
    help="% of events where Smoothcomp city name resolved to a GeoNames city_id with lat/lng.",
)

if match_pct < 95:
    st.warning(
        f"City match rate is **{match_pct:.1f}%** — below the 95% threshold. "
        "Expand the diagnostics section at the bottom of this page to see which cities are unmatched."
    )

st.markdown("---")

# ---------------------------------------------------------------------------
# World map — events by city (bubble size = event count)
# ---------------------------------------------------------------------------

st.subheader("Event Locations")

mapped = df.dropna(subset=["lat", "lng"])

if mapped.empty:
    st.info("No events with resolved coordinates in the current filter. Try widening the filters.")
else:
    city_bubbles = (
        mapped.groupby(["city", "country", "lat", "lng", "commercial_region", "demographic_region"])
        .size()
        .reset_index(name="event_count")
    )
    city_bubbles["label"] = city_bubbles.apply(
        lambda r: f"{r['city']}, {r['country']} — {r['event_count']} event{'s' if r['event_count'] != 1 else ''}",
        axis=1,
    )

    REGION_COLOURS = {
        "EMEA":  "#F5A623",
        "NAMER": "#5DADE2",
        "LATAM": "#27AE60",
        "APAC":  "#9B59B6",
    }
    city_bubbles["color"] = city_bubbles["commercial_region"].map(REGION_COLOURS).fillna("#8E9BAD")

    fig_map = go.Figure()

    for region, colour in REGION_COLOURS.items():
        sub = city_bubbles[city_bubbles["commercial_region"] == region]
        if sub.empty:
            continue
        fig_map.add_trace(go.Scattergeo(
            lat=sub["lat"],
            lon=sub["lng"],
            mode="markers",
            name=region,
            marker=dict(
                size=sub["event_count"].clip(upper=40) * 2.5 + 4,
                color=colour,
                opacity=0.75,
                sizemode="area",
                line=dict(color="#0F1923", width=0.5),
            ),
            text=sub["label"],
            hovertemplate="%{text}<extra></extra>",
        ))

    # Cities with no region get a neutral trace
    no_region = city_bubbles[city_bubbles["commercial_region"].isna() | ~city_bubbles["commercial_region"].isin(REGION_COLOURS)]
    if not no_region.empty:
        fig_map.add_trace(go.Scattergeo(
            lat=no_region["lat"],
            lon=no_region["lng"],
            mode="markers",
            name="Unknown region",
            marker=dict(
                size=no_region["event_count"].clip(upper=40) * 2.5 + 4,
                color="#8E9BAD",
                opacity=0.6,
                sizemode="area",
                line=dict(color="#0F1923", width=0.5),
            ),
            text=no_region["label"],
            hovertemplate="%{text}<extra></extra>",
        ))

    fig_map.update_geos(
        bgcolor="#0F1923",
        showland=True,     landcolor="#1A2535",
        showocean=True,    oceancolor="#0F1923",
        showcoastlines=True, coastlinecolor="#2A3A50",
        showcountries=True,  countrycolor="#2A3A50",
        projection_type="natural earth",
    )
    fig_map.update_layout(
        paper_bgcolor="#0F1923",
        font_color="#E8EDF2",
        legend=dict(
            bgcolor="rgba(26,37,53,0.8)",
            bordercolor="#2A3A50",
            borderwidth=1,
        ),
        margin=dict(l=0, r=0, t=0, b=0),
        height=520,
    )
    st.plotly_chart(fig_map, use_container_width=True)
    st.caption(
        f"Showing {len(mapped):,} of {total_events:,} events with resolved coordinates. "
        "Bubble size scales with event count at that city. Colour = commercial region."
    )

st.markdown("---")

# ---------------------------------------------------------------------------
# Two-column: commercial region + top countries
# ---------------------------------------------------------------------------

col_left, col_right = st.columns(2)

with col_left:
    st.subheader("Events by Commercial Region")
    region_counts = (
        df["commercial_region"].value_counts().reset_index()
        .rename(columns={"commercial_region": "region", "count": "events"})
    )
    if not region_counts.empty:
        fig_region = go.Figure(go.Pie(
            labels=region_counts["region"],
            values=region_counts["events"],
            hole=0.5,
            marker=dict(
                colors=[REGION_COLOURS.get(r, "#8E9BAD") for r in region_counts["region"]],
                line=dict(color="#0F1923", width=2),
            ),
            textinfo="label+percent",
            textfont=dict(color="#E8EDF2"),
        ))
        fig_region.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font_color="#E8EDF2", showlegend=False,
            margin=dict(l=0, r=0, t=10, b=0), height=300,
            annotations=[dict(
                text=f"<b>{total_events:,}</b><br>events",
                x=0.5, y=0.5, font_size=16, font_color="#E8EDF2", showarrow=False,
            )],
        )
        st.plotly_chart(fig_region, use_container_width=True)
    else:
        st.info("No data in current filter.")

with col_right:
    st.subheader("Top 15 Countries by Event Count")
    country_counts = (
        df["country"].value_counts().head(15).reset_index()
        .rename(columns={"country": "country", "count": "events"})
    )
    if not country_counts.empty:
        fig_countries = go.Figure(go.Bar(
            x=country_counts["events"],
            y=country_counts["country"],
            orientation="h",
            marker_color="#F5A623",
            text=country_counts["events"],
            textposition="outside",
            textfont=dict(color="#E8EDF2"),
        ))
        fig_countries.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font_color="#E8EDF2",
            yaxis=dict(autorange="reversed", gridcolor="#2A3A50"),
            xaxis=dict(gridcolor="#2A3A50"),
            margin=dict(l=0, r=0, t=10, b=0), height=300,
        )
        st.plotly_chart(fig_countries, use_container_width=True)
    else:
        st.info("No data in current filter.")

st.markdown("---")

# ---------------------------------------------------------------------------
# Demographic region breakdown
# ---------------------------------------------------------------------------

st.subheader("Events by Demographic Region")

demo_counts = (
    df["demographic_region"].value_counts().reset_index()
    .rename(columns={"demographic_region": "region", "count": "events"})
)

if not demo_counts.empty:
    fig_demo = go.Figure(go.Bar(
        x=demo_counts["region"],
        y=demo_counts["events"],
        marker_color="#5DADE2",
        text=demo_counts["events"],
        textposition="outside",
        textfont=dict(color="#E8EDF2"),
    ))
    fig_demo.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font_color="#E8EDF2",
        xaxis=dict(gridcolor="#2A3A50", tickangle=-30),
        yaxis=dict(gridcolor="#2A3A50", title="Events"),
        margin=dict(l=0, r=0, t=20, b=60), height=340,
    )
    st.plotly_chart(fig_demo, use_container_width=True)
else:
    st.info("No data in current filter.")

st.markdown("---")

# ---------------------------------------------------------------------------
# Events over time by commercial region
# ---------------------------------------------------------------------------

st.subheader("Event Volume Over Time by Region")

if not df.empty:
    df["event_year"] = df["event_date"].dt.year
    df["event_quarter"] = df["event_date"].dt.to_period("Q").astype(str)

    time_region = (
        df.groupby(["event_quarter", "commercial_region"])
        .size()
        .reset_index(name="events")
    )

    if not time_region.empty:
        fig_time = go.Figure()
        for region, colour in REGION_COLOURS.items():
            sub = time_region[time_region["commercial_region"] == region]
            if sub.empty:
                continue
            fig_time.add_trace(go.Bar(
                x=sub["event_quarter"],
                y=sub["events"],
                name=region,
                marker_color=colour,
            ))
        fig_time.update_layout(
            barmode="stack",
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font_color="#E8EDF2",
            legend=dict(bgcolor="rgba(0,0,0,0)"),
            xaxis=dict(gridcolor="#2A3A50"),
            yaxis=dict(gridcolor="#2A3A50", title="Events"),
            margin=dict(l=0, r=0, t=20, b=0), height=300,
        )
        st.plotly_chart(fig_time, use_container_width=True)
    else:
        st.info("No time-series data in current filter.")

st.markdown("---")

# ---------------------------------------------------------------------------
# City match quality diagnostics
# ---------------------------------------------------------------------------

with st.expander("City match diagnostics", expanded=(match_pct < 95)):
    st.markdown(
        "City names from Smoothcomp are matched against the GeoNames cities5000 dataset "
        "via exact case-insensitive string matching (`city_ascii` then `city_name`). "
        "Unmatched cities have no lat/lng and are excluded from the map."
    )

    mc1, mc2, mc3 = st.columns(3)
    if mq is not None:
        mc1.metric("Events with city", f"{int(mq['total']):,}")
        mc2.metric("Matched", f"{int(mq['matched']):,}", delta=f"{float(mq['match_pct']):.1f}%")
        mc3.metric("Unmatched", f"{int(mq['unmatched']):,}")

    st.markdown("**Top unmatched cities** (add to `silver_city_resolution` to improve coverage):")
    if not unmatched_cities.empty:
        st.dataframe(
            unmatched_cities.rename(columns={"city": "City", "country": "Country", "events": "Events"}),
            hide_index=True,
            use_container_width=True,
        )
    else:
        st.success("All cities with a country resolved to a GeoNames match.")

# ---------------------------------------------------------------------------
# Footer
# ---------------------------------------------------------------------------

st.markdown("---")
st.caption(
    "Sources: Smoothcomp (scraped monthly) · GeoNames cities5000 (CC BY 4.0, geonames.org) · "
    "ref_country_regions (curated). "
    "City matching via silver_city_resolution — exact string match, most-populous city chosen on ties."
)
