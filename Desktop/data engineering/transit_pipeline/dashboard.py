"""
dashboard.py — Streamlit analytics dashboard for the transit pipeline.

Starts the data pipeline in a background thread on first load,
then renders an auto-refreshing multi-section dashboard.

Run:
    streamlit run transit_pipeline/dashboard.py
"""

import sys
import os
import time
import json
import threading
import textwrap
from datetime import datetime, timedelta

# Ensure the transit_pipeline directory is on the path
sys.path.insert(0, os.path.dirname(__file__))

import streamlit as st
import streamlit.components.v1 as components
try:
    from streamlit_js_eval import get_geolocation
except Exception:
    get_geolocation = None
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# ─────────────────────────────────────────────────────────────────────────────
# Page Config
# ─────────────────────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Bengaluru Transit Analytics",
    page_icon="🚇",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────────────────────────────────────
# Custom CSS
# ─────────────────────────────────────────────────────────────────────────────

st.markdown("""
<style>
    .main { background-color: #0e1117; }
    .metric-card {
        background: linear-gradient(135deg, #1e2130, #252a3a);
        border-radius: 12px;
        padding: 18px 20px;
        border: 1px solid #2d3247;
        text-align: center;
    }
    .metric-value { font-size: 2.2rem; font-weight: 700; color: #fff; }
    .metric-label { font-size: 0.85rem; color: #8892b0; margin-top: 4px; }
    .status-on-time  { color: #57d9a3; }
    .status-delayed  { color: #ff6b6b; }
    .status-moderate { color: #ffa94d; }
    .board-row {
        display: flex; align-items: center; gap: 12px;
        padding: 8px 12px; border-radius: 8px;
        background: #1a1f2e; margin-bottom: 6px;
        border-left: 4px solid var(--route-color, #4a9eff);
    }
    .section-header {
        font-size: 1.3rem; font-weight: 600; color: #e2e8f0;
        border-bottom: 2px solid #2d3247; padding-bottom: 8px;
        margin-bottom: 16px;
    }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# Pipeline Bootstrap (runs once per session)
# ─────────────────────────────────────────────────────────────────────────────

@st.cache_resource
def start_pipeline():
    """Start the transit pipeline in a background thread (once per app lifetime)."""
    import database as db
    from config import ROUTES, ROUTE_BY_ID, PEAK_HOURS
    from pipeline import TransitPipeline

    db.init_db()
    db.upsert_routes(ROUTES)

    p = TransitPipeline(time_acceleration=1.0)
    p.start(blocking=False)
    return p


pipeline = start_pipeline()


# ─────────────────────────────────────────────────────────────────────────────
# Imports (after sys.path is set)
# ─────────────────────────────────────────────────────────────────────────────

import analytics as ana
import database as db
import etl
import importlib
import planner
if not hasattr(planner, "find_nearest_bus_stations"):
    try:
        importlib.reload(planner)
    except Exception:
        pass
from config import ROUTES, ROUTE_BY_ID, PEAK_HOURS
from processor import classify_delay, format_delay, get_peak_label, build_departure_board

# ─────────────────────────────────────────────────────────────────────────────
# Sidebar
# ─────────────────────────────────────────────────────────────────────────────

with st.sidebar:
    st.image("https://img.icons8.com/color/96/metro.png", width=60)
    st.title("Bengaluru Transit Analytics")
    st.caption("Live public transport telemetry")
    st.divider()

    refresh_rate = st.select_slider(
        "Auto-refresh interval",
        options=[5, 10, 15, 30, 60],
        value=10,
        format_func=lambda x: f"{x}s",
    )

    st.divider()
    st.subheader("Filters")

    vehicle_filter = st.multiselect(
        "Vehicle type",
        ["bus", "metro"],
        default=["bus", "metro"],
    )

    route_options = {r.route_id: r.name for r in ROUTES}
    selected_routes = st.multiselect(
        "Routes",
        options=list(route_options.keys()),
        format_func=lambda x: route_options[x],
        default=[],
        placeholder="All routes",
    )

    st.divider()
    sim_time_placeholder = st.empty()

    # Show sim time
    kpis = ana.get_summary_kpis()
    sim_time_placeholder.markdown(
        f"**Sim Period:** {kpis['peak_label']}"
    )

    st.divider()
    st.caption("Pipeline: ✅ Running" if pipeline._running else "❌ Stopped")

# ─────────────────────────────────────────────────────────────────────────────
# Tab Layout
# ─────────────────────────────────────────────────────────────────────────────

tabs = st.tabs([
    "🗺️ Live Map",
    "📊 Overview",
    "⏰ Departure Board",
    "🚏 Station Explorer",
    "🧭 Journey Planner",
    "📈 Peak Periods",
    "🏆 Route Performance",
    "🚌 Bus Analytics",
    "🚇 Metro Analytics",
    "📜 Event Log",
    "🩺 Pipeline Health",
])

# ════════════════════════════════════════════════════════════════════════════
# TAB 0 — Live Map
# ════════════════════════════════════════════════════════════════════════════

with tabs[0]:
    st.markdown('<div class="section-header">🗺️ Live Vehicle Map</div>', unsafe_allow_html=True)

    df_live = ana.get_live_vehicles()

    if df_live.empty:
        st.info("Waiting for vehicle data… (pipeline initialising)")
    else:
        # Apply filters
        if vehicle_filter:
            df_live = df_live[df_live["vehicle_type"].isin(vehicle_filter)]
        if selected_routes:
            df_live = df_live[df_live["route_id"].isin(selected_routes)]

        if not df_live.empty:
            df_live["delay_label"] = df_live["delay_seconds"].apply(format_delay)
            df_live["delay_cat"], _ = zip(*df_live["delay_seconds"].apply(classify_delay))
            df_live["size"] = (
    df_live["vehicle_type"]
    .map({"bus": 10, "metro": 14})
    .fillna(10)
)
            df_live["symbol"] = df_live["vehicle_type"].map({"bus": "circle", "metro": "diamond"})
            df_live["icon"] = df_live["vehicle_type"].map({"bus": "🚌", "metro": "🚇"})
            df_live["hover"] = (
                df_live["icon"] + " " +
                df_live["route_name"] + "<br>" +
                "Vehicle: " + df_live["vehicle_id"] + "<br>" +
                "Status: " + df_live["status"] + "<br>" +
                "Delay: " + df_live["delay_label"] + "<br>" +
                "Speed: " + df_live["speed_kmh"].round(1).astype(str) + " km/h<br>" +
                "Occupancy: " + (df_live["occupancy"] * 100).round().astype(int).astype(str) + "%"
            )

            fig_map = go.Figure()

            for route_id, grp in df_live.groupby("route_id"):
                route = ROUTE_BY_ID.get(route_id)
                if not route:
                    continue
                color = route.color
                vtype = route.vehicle_type
                fig_map.add_trace(go.Scattermap(
                    lat=grp["lat"],
                    lon=grp["lon"],
                    mode="markers",
                    marker=dict(
                        size=grp["size"],
                        color=color,
                        opacity=0.9,
                    ),
                    text=grp["hover"],
                    hoverinfo="text",
                    name=f"{route.name} ({'🚌' if vtype=='bus' else '🚇'})",
                    legendgroup=route_id,
                ))

            # Draw route polylines
            for route in ROUTES:
                if selected_routes and route.route_id not in selected_routes:
                    continue
                if route.vehicle_type not in vehicle_filter:
                    continue
                lats = [s.lat for s in route.stops]
                lons = [s.lon for s in route.stops]
                fig_map.add_trace(go.Scattermap(
                    lat=lats, lon=lons,
                    mode="lines",
                    line=dict(width=2, color=route.color),
                    opacity=0.4,
                    showlegend=False,
                    hoverinfo="skip",
                ))

            fig_map.update_layout(
                map=dict(
                    style="carto-darkmatter",
                    center=dict(lat=12.9716, lon=77.5946),
                    zoom=10.5,
                ),
                margin=dict(l=0, r=0, t=0, b=0),
                height=600,
                legend=dict(
                    bgcolor="rgba(14,17,23,0.8)",
                    bordercolor="#2d3247",
                    borderwidth=1,
                    font=dict(color="white", size=11),
                ),
                paper_bgcolor="#0e1117",
                plot_bgcolor="#0e1117",
            )

            st.plotly_chart(fig_map, use_container_width=True)

            # Mini stats below map
            c1, c2, c3, c4 = st.columns(4)
            with c1:
                st.metric("Vehicles on map", len(df_live))
            with c2:
                st.metric("Buses", int((df_live["vehicle_type"] == "bus").sum()))
            with c3:
                st.metric("Metro", int((df_live["vehicle_type"] == "metro").sum()))
            with c4:
                delayed_count = int((df_live["delay_seconds"] > 60).sum())
                st.metric("Delayed", delayed_count,
                          delta=f"{delayed_count} vehicles",
                          delta_color="inverse")
        else:
            st.warning("No vehicles match the current filters.")


# ════════════════════════════════════════════════════════════════════════════
# TAB 1 — Overview KPIs
# ════════════════════════════════════════════════════════════════════════════

with tabs[1]:
    st.markdown('<div class="section-header">📊 Fleet Overview</div>', unsafe_allow_html=True)

    kpis = ana.get_summary_kpis()

    # KPI cards row
    cols = st.columns(4)
    kpi_data = [
        ("🚍 Vehicles Running",  kpis["total_vehicles"],   ""),
        ("🛣️ Active Routes",      kpis["active_routes"],    ""),
        ("⏱️ Avg Delay",          f"{kpis['avg_delay_s']:.0f}s",  ""),
        ("✅ On-Time Rate",       f"{kpis['on_time_pct']:.1f}%",  ""),
    ]
    for col, (label, val, unit) in zip(cols, kpi_data):
        with col:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value">{val}{unit}</div>
                <div class="metric-label">{label}</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("")

    cols2 = st.columns(4)
    more_kpis = [
        ("🚌 Buses",            kpis["buses"],              ""),
        ("🚆 Trains",           kpis["trains"],             ""),
        ("🏁 Trips Completed",  kpis["trips_completed"],    ""),
        ("🕐 Period",           kpis["peak_label"],         ""),
    ]
    for col, (label, val, unit) in zip(cols2, more_kpis):
        with col:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value">{val}{unit}</div>
                <div class="metric-label">{label}</div>
            </div>
            """, unsafe_allow_html=True)

    st.divider()

    # Vehicle count by route bar chart
    col_left, col_right = st.columns([3, 2])
    with col_left:
        st.subheader("🚦 Vehicles per Route")
        df_rc = ana.get_vehicle_count_by_route()
        if not df_rc.empty:
            df_rc = df_rc.sort_values("vehicle_count", ascending=True)
            fig_bar = px.bar(
                df_rc, y="route_name", x="vehicle_count",
                color="vehicle_type",
                color_discrete_map={"bus": "#2A9D8F", "metro": "#8338EC"},
                orientation="h",
                text="vehicle_count",
                labels={"vehicle_count": "Vehicles", "route_name": ""},
            )
            fig_bar.update_traces(textposition="outside")
            fig_bar.update_layout(
                height=380, margin=dict(l=0, r=0, t=10, b=0),
                paper_bgcolor="#0e1117", plot_bgcolor="#0e1117",
                font=dict(color="white"),
                legend=dict(bgcolor="rgba(0,0,0,0)"),
                yaxis=dict(tickfont=dict(size=11)),
            )
            st.plotly_chart(fig_bar, use_container_width=True)

    with col_right:
        st.subheader("🥧 Fleet Composition")
        df_type = ana.get_vehicle_count_by_type()
        if not df_type.empty:
            fig_pie = px.pie(
                df_type, names="vehicle_type", values="count",
                color="vehicle_type",
                color_discrete_map={"bus": "#2A9D8F", "metro": "#8338EC"},
                hole=0.55,
            )
            fig_pie.update_layout(
                height=380, margin=dict(l=20, r=20, t=20, b=20),
                paper_bgcolor="#0e1117",
                font=dict(color="white"),
                legend=dict(bgcolor="rgba(0,0,0,0)"),
            )
            fig_pie.update_traces(textinfo="label+percent")
            st.plotly_chart(fig_pie, use_container_width=True)

    # KPI Trend
    st.subheader("📈 KPI Trend Over Time")
    df_trend = ana.get_kpi_trend(limit=300)
    if not df_trend.empty and len(df_trend) > 1:
        fig_trend = make_subplots(
            rows=2, cols=2,
            subplot_titles=("Total Vehicles", "Avg Delay (seconds)",
                            "On-Time Rate (%)", "Trips Completed"),
            vertical_spacing=0.15,
        )
        fig_trend.add_trace(
            go.Scatter(x=df_trend["snapshot_time"], y=df_trend["total_vehicles"],
                       mode="lines", line=dict(color="#4a9eff"), fill="tozeroy",
                       fillcolor="rgba(74,158,255,0.15)"), row=1, col=1)
        fig_trend.add_trace(
            go.Scatter(x=df_trend["snapshot_time"], y=df_trend["avg_delay_seconds"],
                       mode="lines", line=dict(color="#ff6b6b"), fill="tozeroy",
                       fillcolor="rgba(255,107,107,0.15)"), row=1, col=2)
        fig_trend.add_trace(
            go.Scatter(x=df_trend["snapshot_time"], y=df_trend["on_time_pct"],
                       mode="lines", line=dict(color="#57d9a3"), fill="tozeroy",
                       fillcolor="rgba(87,217,163,0.15)"), row=2, col=1)
        fig_trend.add_trace(
            go.Scatter(x=df_trend["snapshot_time"], y=df_trend["trips_completed"],
                       mode="lines", line=dict(color="#ffa94d"), fill="tozeroy",
                       fillcolor="rgba(255,169,77,0.15)"), row=2, col=2)
        fig_trend.update_layout(
            height=500, showlegend=False,
            paper_bgcolor="#0e1117", plot_bgcolor="#0e1117",
            font=dict(color="white"),
        )
        fig_trend.update_xaxes(gridcolor="#2d3247", showgrid=True)
        fig_trend.update_yaxes(gridcolor="#2d3247", showgrid=True)
        st.plotly_chart(fig_trend, use_container_width=True)
    else:
        st.info("Trend data accumulates over time — check back in a minute.")


# ════════════════════════════════════════════════════════════════════════════
# TAB 2 — Departure Board
# ════════════════════════════════════════════════════════════════════════════

with tabs[2]:
    st.markdown('<div class="section-header">⏰ Arrival / Departure Board</div>', unsafe_allow_html=True)

    from config import STOP_BY_ID
    all_stops = sorted(STOP_BY_ID.values(), key=lambda s: s.name)
    stop_options = {s.stop_id: f"{s.name} ({s.stop_id})" for s in all_stops}

    col_sel, col_info = st.columns([2, 3])
    with col_sel:
        selected_stop = st.selectbox(
            "Select a stop",
            options=list(stop_options.keys()),
            format_func=lambda x: stop_options[x],
            index=0,
        )

    if selected_stop:
        stop_info = STOP_BY_ID[selected_stop]
        with col_info:
            st.markdown(f"""
            **{stop_info.name}**
            `{stop_info.stop_id}` — {stop_info.lat:.4f}°N, {stop_info.lon:.4f}°E
            """)

        # Real-time arrivals
        if hasattr(pipeline, "sim") and pipeline.sim:
            vehicles_raw = pipeline.sim.get_active_vehicles()
        else:
            vehicles_raw = db.get_all_vehicles(active_only=True)

        board = build_departure_board(selected_stop, vehicles_raw,
                                      pipeline.sim.sim_time if hasattr(pipeline, "sim") else datetime.now(), max_entries=15)

        st.subheader(f"🚏 Next arrivals at **{stop_info.name}**")

        if not board:
            st.info("No vehicles currently approaching this stop. Try a busier stop or wait a moment.")
        else:
            for entry in board:
                eta_mins = entry["eta_seconds"] // 60
                eta_secs = entry["eta_seconds"] % 60
                eta_str  = f"{eta_mins}m {eta_secs:02d}s" if eta_mins > 0 else f"{eta_secs}s"
                color    = entry["color"]
                icon     = "🚌" if entry["vehicle_type"] == "bus" else "🚇"

                b_num = entry.get("bus_number", entry["route_id"])
                b_name = entry.get("bus_name", entry["route_name"])
                dest_sign = entry.get("destination_sign", entry["destination"])

                st.markdown(f"""
                <div class="board-row" style="--route-color:{color}">
                    <span style="font-size:1.5rem">{icon}</span>
                    <div style="flex:1">
                        <div style="display:flex; align-items:center; gap:8px; flex-wrap:wrap;">
                            <span style="background:{color}; color:#fff; font-weight:800; font-size:0.82rem; padding:2px 8px; border-radius:5px;">
                                {b_num}
                            </span>
                            <strong style="color:#e2e8f0; font-size:0.98rem;">{b_name}</strong>
                        </div>
                        <div style="color:#a0aec0; font-size:0.8rem; margin-top:3px;">
                            <span>Towards: <strong style="color:#ffffff;">{dest_sign}</strong></span>
                            <span style="margin-left:10px; color:#ffd166;">• Vehicle No: <strong>{entry['vehicle_id']}</strong></span>
                        </div>
                        <div style="color:#57d9a3; font-size:0.8rem; margin-top:2px; font-weight:600;">
                            {entry['proximity']}
                        </div>
                    </div>
                    <div style="text-align:right">
                        <div style="font-size:1.25rem; font-weight:700; color:#4a9eff">
                            {entry['eta_time']}
                        </div>
                        <div style="font-size:0.8rem; color:#8892b0">in {eta_str}</div>
                    </div>
                    <div style="min-width:90px; text-align:right">
                        <span style="font-size:1.1rem">{entry['delay_emoji']}</span>
                        <span style="font-size:0.8rem; color:#8892b0"> {entry['delay_label']}</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)

        st.divider()

        # Recent stop events table
        st.subheader("📋 Recent Stop Events")
        df_stop = ana.get_stop_events(stop_id=selected_stop, limit=30)
        if not df_stop.empty:
            df_stop["timestamp"] = df_stop["timestamp"].dt.strftime("%H:%M:%S")
            df_stop["delay"] = df_stop["delay_seconds"].apply(format_delay)
            st.dataframe(
                df_stop[["timestamp", "event_type", "route_name", "vehicle_id", "delay"]].rename(columns={
                    "timestamp": "Time", "event_type": "Event",
                    "route_name": "Route", "vehicle_id": "Vehicle", "delay": "Delay",
                }),
                hide_index=True,
                use_container_width=True,
            )
        else:
            st.info("No events for this stop yet.")


# ════════════════════════════════════════════════════════════════════════════
# TAB 3 — Station Explorer
# ════════════════════════════════════════════════════════════════════════════

with tabs[3]:
    st.markdown('<div class="section-header">🚏 Station Explorer — Find Routes from Any Stop</div>',
                unsafe_allow_html=True)

    from config import STOP_BY_ID as _STOP_BY_ID

    # ── Build stop→routes index ─────────────────────────────────────────────
    # For each stop_id: list of Route objects that pass through it
    _stop_routes: dict = {}
    for _r in ROUTES:
        for _s in _r.stops:
            _stop_routes.setdefault(_s.stop_id, []).append(_r)

    # ── Categorised stop options for the selectbox ──────────────────────────
    _bus_stops   = sorted(
        {sid for sid, rlist in _stop_routes.items()
         if any(r.vehicle_type == "bus" for r in rlist)},
        key=lambda sid: _STOP_BY_ID[sid].name
    )
    _metro_stops = sorted(
        {sid for sid, rlist in _stop_routes.items()
         if any(r.vehicle_type == "metro" for r in rlist)},
        key=lambda sid: _STOP_BY_ID[sid].name
    )
    _interchange = sorted(
        {sid for sid in _bus_stops if sid in set(_metro_stops)},
        key=lambda sid: _STOP_BY_ID[sid].name
    )

    # ── Search / filter UI ────────────────────────────────────────────────
    _col_search, _col_type, _col_stat = st.columns([3, 2, 2])

    with _col_type:
        _stype = st.radio(
            "Show stops for",
            ["All", "Bus only", "Metro only", "Interchange 🔁"],
            horizontal=True,
        )

    # Build filtered stop list based on type choice
    if _stype == "Bus only":
        _filtered_sids = _bus_stops
    elif _stype == "Metro only":
        _filtered_sids = _metro_stops
    elif _stype == "Interchange 🔁":
        _filtered_sids = _interchange
    else:
        _filtered_sids = sorted(_STOP_BY_ID.keys(), key=lambda sid: _STOP_BY_ID[sid].name)

    with _col_stat:
        st.markdown(f"""
        <div style="background:rgba(74,158,255,0.1); border:1px solid #2d3247;
                    border-radius:8px; padding:10px 14px; margin-top:4px;">
            <div style="font-size:0.8rem; color:#8892b0;">Showing</div>
            <div style="font-size:1.4rem; font-weight:700; color:#4a9eff;">{len(_filtered_sids)}</div>
            <div style="font-size:0.75rem; color:#8892b0;">stops</div>
        </div>""", unsafe_allow_html=True)

    with _col_search:
        _stop_label = {sid: _STOP_BY_ID[sid].name for sid in _filtered_sids}
        _sel_sid = st.selectbox(
            "🔍 Search & select a boarding station",
            options=_filtered_sids,
            format_func=lambda sid: _stop_label.get(sid, sid),
            index=0 if _filtered_sids else None,
            placeholder="Type to search a station...",
        )

    if not _filtered_sids:
        st.warning("No stops match the selected filter.")
    elif _sel_sid:
        _sel_stop  = _STOP_BY_ID[_sel_sid]
        _sel_routes = _stop_routes.get(_sel_sid, [])
        _sel_bus    = [r for r in _sel_routes if r.vehicle_type == "bus"]
        _sel_metro  = [r for r in _sel_routes if r.vehicle_type == "metro"]
        _is_interchange = bool(_sel_bus and _sel_metro)

        # ── Station header card ─────────────────────────────────────────────
        _ic_badge = (
            '<span style="background:#f59e0b;color:#000;font-size:0.7rem;'
            'font-weight:700;padding:2px 8px;border-radius:12px;">'
            '🔁 INTERCHANGE</span>' if _is_interchange else ""
        )
        _type_badge_color = "#06D6A0" if _sel_bus and not _sel_metro else (
            "#8338EC" if _sel_metro and not _sel_bus else "#f59e0b"
        )
        _type_label = "Bus Stop" if _sel_bus and not _sel_metro else (
            "Metro Station" if _sel_metro and not _sel_bus else "Interchange"
        )
        _type_icon  = "🚌" if _sel_bus and not _sel_metro else (
            "🚇" if _sel_metro and not _sel_bus else "🔁"
        )

        _routes_serve_txt = (
            f"{len(_sel_routes)} route serves this stop"
            if len(_sel_routes) == 1
            else f"{len(_sel_routes)} routes serve this stop"
        )

        _stat_cards = []
        if len(_sel_bus) > 0:
            _bus_word = "Bus route" if len(_sel_bus) == 1 else "Bus routes"
            _stat_cards.append(
                f'<div style="background:rgba(74,158,255,0.1); border:1px solid rgba(74,158,255,0.3); '
                f'border-radius:10px; padding:8px 16px; text-align:center; min-width:85px;">'
                f'<div style="font-size:1.6rem; font-weight:800; color:#4a9eff; line-height:1.1;">{len(_sel_bus)}</div>'
                f'<div style="font-size:0.72rem; color:#8892b0; font-weight:600; margin-top:2px;">🚌 {_bus_word}</div>'
                f'</div>'
            )
        if len(_sel_metro) > 0:
            _metro_word = "Metro line" if len(_sel_metro) == 1 else "Metro lines"
            _stat_cards.append(
                f'<div style="background:rgba(131,56,236,0.12); border:1px solid rgba(131,56,236,0.35); '
                f'border-radius:10px; padding:8px 16px; text-align:center; min-width:85px;">'
                f'<div style="font-size:1.6rem; font-weight:800; color:#a78bfa; line-height:1.1;">{len(_sel_metro)}</div>'
                f'<div style="font-size:0.72rem; color:#8892b0; font-weight:600; margin-top:2px;">🚇 {_metro_word}</div>'
                f'</div>'
            )
        if not _stat_cards:
            _stat_cards.append(
                f'<div style="background:rgba(255,255,255,0.05); border:1px solid rgba(255,255,255,0.1); '
                f'border-radius:10px; padding:8px 16px; text-align:center;">'
                f'<div style="font-size:1.6rem; font-weight:800; color:#8892b0; line-height:1.1;">0</div>'
                f'<div style="font-size:0.72rem; color:#8892b0;">Routes</div>'
                f'</div>'
            )
        _stats_html = "".join(_stat_cards)

        station_header_html = textwrap.dedent(f"""
        <div style="background:linear-gradient(135deg,#1a1f2e,#22293b);
                    border-radius:14px; padding:18px 22px; margin:12px 0;
                    border:1px solid #2d3247;">
            <div style="display:flex; align-items:center; justify-content:space-between; flex-wrap:wrap; gap:12px;">
                <div>
                    <div style="display:flex; align-items:center; gap:10px; margin-bottom:6px;">
                        <span style="font-size:2rem">{_type_icon}</span>
                        <div>
                            <div style="font-size:1.35rem; font-weight:700; color:#e2e8f0;">
                                {_sel_stop.name}
                            </div>
                            <div style="color:#8892b0; font-size:0.82rem; margin-top:2px;">
                                📍 {_sel_stop.lat:.5f}°N, {_sel_stop.lon:.5f}°E
                                &nbsp;•&nbsp;
                                <code style="background:rgba(255,255,255,0.08); padding:1px 6px;
                                             border-radius:4px; font-size:0.75rem;">{_sel_sid}</code>
                            </div>
                        </div>
                    </div>
                    <div style="display:flex; gap:8px; flex-wrap:wrap; margin-top:8px;">
                        <span style="background:{_type_badge_color}22; color:{_type_badge_color};
                                     border:1px solid {_type_badge_color}44;
                                     font-size:0.75rem; font-weight:600;
                                     padding:3px 10px; border-radius:12px;">
                            {_type_label}
                        </span>
                        {_ic_badge}
                        <span style="background:rgba(255,255,255,0.06); color:#8892b0;
                                     font-size:0.75rem; padding:3px 10px; border-radius:12px;">
                            {_routes_serve_txt}
                        </span>
                    </div>
                </div>
                <div style="display:flex; gap:10px; align-items:center; flex-wrap:wrap;">
                    {_stats_html}
                </div>
            </div>
        </div>""").strip()
        st.markdown(station_header_html, unsafe_allow_html=True)

        # ── Two column layout: routes + map ────────────────────────────────
        _col_routes, _col_map = st.columns([3, 2])

        with _col_routes:
            # ── Bus routes serving this stop ─────────────────────────────
            if _sel_bus:
                st.markdown("**🚌 Bus Routes at this Stop**")
                for _br in _sel_bus:
                    _stop_idx = next(
                        (i for i, s in enumerate(_br.stops) if s.stop_id == _sel_sid), 0
                    )
                    _prev = _br.stops[_stop_idx - 1].name if _stop_idx > 0 else "—"
                    _next = _br.stops[_stop_idx + 1].name if _stop_idx < len(_br.stops)-1 else "—"
                    _pos_label = (
                        "First stop" if _stop_idx == 0
                        else "Last stop" if _stop_idx == len(_br.stops)-1
                        else f"Stop {_stop_idx+1} of {len(_br.stops)}"
                    )
                    st.markdown(f"""
                    <div style="background:#1a1f2e; border-left:4px solid {_br.color};
                                border-radius:8px; padding:12px 14px; margin-bottom:8px;">
                        <div style="display:flex; justify-content:space-between; align-items:center;">
                            <div>
                                <span style="background:{_br.color}; color:#fff; font-size:0.68rem;
                                             font-weight:700; padding:2px 7px; border-radius:10px;">
                                    {_br.route_id}
                                </span>
                                <span style="color:#e2e8f0; font-weight:600;
                                             margin-left:8px; font-size:0.9rem;">
                                    {_br.name}
                                </span>
                            </div>
                            <span style="color:#8892b0; font-size:0.72rem;">{_pos_label}</span>
                        </div>
                        <div style="color:#8892b0; font-size:0.75rem; margin-top:7px;
                                    display:flex; gap:12px; flex-wrap:wrap;">
                            <span>⇦ {_prev}</span>
                            <span>⇨ {_next}</span>
                            <span>⏱ {_br.headway_minutes} min headway</span>
                            <span>🕐 {_br.first_departure}–{_br.last_departure}</span>
                        </div>
                    </div>""", unsafe_allow_html=True)

            # ── Metro lines serving this stop ────────────────────────────
            if _sel_metro:
                st.markdown("**🚇 Metro Lines at this Station**")
                for _mr in _sel_metro:
                    _stop_idx = next(
                        (i for i, s in enumerate(_mr.stops) if s.stop_id == _sel_sid), 0
                    )
                    _prev = _mr.stops[_stop_idx - 1].name if _stop_idx > 0 else "—"
                    _next = _mr.stops[_stop_idx + 1].name if _stop_idx < len(_mr.stops)-1 else "—"
                    _pos_label = (
                        "First station" if _stop_idx == 0
                        else "Last station" if _stop_idx == len(_mr.stops)-1
                        else f"Station {_stop_idx+1} of {len(_mr.stops)}"
                    )
                    st.markdown(f"""
                    <div style="background:#12152a; border-left:4px solid {_mr.color};
                                border-radius:8px; padding:12px 14px; margin-bottom:8px;">
                        <div style="display:flex; justify-content:space-between; align-items:center;">
                            <div>
                                <span style="background:{_mr.color}; color:#fff; font-size:0.68rem;
                                             font-weight:700; padding:2px 7px; border-radius:10px;">
                                    {_mr.route_id}
                                </span>
                                <span style="color:#e2e8f0; font-weight:600;
                                             margin-left:8px; font-size:0.9rem;">
                                    {_mr.name}
                                </span>
                            </div>
                            <span style="color:#8892b0; font-size:0.72rem;">{_pos_label}</span>
                        </div>
                        <div style="color:#8892b0; font-size:0.75rem; margin-top:7px;
                                    display:flex; gap:12px; flex-wrap:wrap;">
                            <span>⇦ {_prev}</span>
                            <span>⇨ {_next}</span>
                            <span>⏱ {_mr.headway_minutes} min headway</span>
                            <span>⚡ {_mr.avg_speed_kmh:.0f} km/h avg</span>
                        </div>
                    </div>""", unsafe_allow_html=True)

        with _col_map:
            # ── Mini station map ───────────────────────────────────────────
            st.markdown("**🗺️ Station Location**")
            _map_fig = go.Figure()

            # Draw route polylines through this stop
            for _r in _sel_routes:
                _lats = [s.lat for s in _r.stops]
                _lons = [s.lon for s in _r.stops]
                _map_fig.add_trace(go.Scattermap(
                    lat=_lats, lon=_lons, mode="lines",
                    line=dict(width=3, color=_r.color),
                    opacity=0.6, showlegend=False, hoverinfo="skip",
                ))
                # All stops on these routes as small dots
                _map_fig.add_trace(go.Scattermap(
                    lat=[s.lat for s in _r.stops],
                    lon=[s.lon for s in _r.stops],
                    mode="markers",
                    marker=dict(size=6, color=_r.color, opacity=0.5),
                    text=[s.name for s in _r.stops],
                    hoverinfo="text",
                    showlegend=False,
                ))

            # Highlight selected stop as a big star
            _map_fig.add_trace(go.Scattermap(
                lat=[_sel_stop.lat],
                lon=[_sel_stop.lon],
                mode="markers+text",
                marker=dict(size=18, color="#f59e0b", symbol="circle"),
                text=[_sel_stop.name],
                textposition="top right",
                textfont=dict(color="#f59e0b", size=12),
                hoverinfo="text",
                showlegend=False,
            ))

            _map_fig.update_layout(
                map=dict(
                    style="carto-darkmatter",
                    center=dict(lat=_sel_stop.lat, lon=_sel_stop.lon),
                    zoom=12.5,
                ),
                margin=dict(l=0, r=0, t=0, b=0),
                height=420,
                paper_bgcolor="#0e1117",
            )
            st.plotly_chart(_map_fig, use_container_width=True)

        st.divider()

        # ── Live approaching vehicles at this stop ───────────────────────
        st.subheader("🚊 Live Approaching Vehicles")
        if hasattr(pipeline, "sim") and pipeline.sim:
            _vehicles_raw = pipeline.sim.get_active_vehicles()
            _sim_t = pipeline.sim.sim_time
        else:
            _vehicles_raw = db.get_all_vehicles(active_only=True)
            _sim_t = datetime.now()

        _board = build_departure_board(
            _sel_sid, _vehicles_raw, _sim_t, max_entries=15
        )
        if not _board:
            st.info("No vehicles currently approaching this stop.")
        else:
            _ba, _bb, _bc = st.columns(3)
            for _i, _entry in enumerate(_board):
                _eta_m = _entry["eta_seconds"] // 60
                _eta_s = _entry["eta_seconds"] % 60
                _eta_str = f"{_eta_m}m {_eta_s:02d}s" if _eta_m > 0 else f"{_eta_s}s"
                _vicon = "🚌" if _entry["vehicle_type"] == "bus" else "🚇"
                _dcol = (
                    "#57d9a3" if _entry["delay_s"] < 60
                    else ("#FFD166" if _entry["delay_s"] < 300 else "#ff6b6b")
                )
                _b_num = _entry.get("bus_number", _entry["route_id"])
                _b_name = _entry.get("bus_name", _entry["route_name"])
                _dest_sign = _entry.get("destination_sign", _entry["destination"])
                _target_col = [_ba, _bb, _bc][_i % 3]

                with _target_col:
                    st.markdown(f"""
                    <div style="background:#1a1f2e; border-left:4px solid {_entry['color']};
                                border-radius:8px; padding:10px 12px; margin-bottom:8px;">
                        <div style="display:flex; align-items:center; gap:8px;">
                            <span style="font-size:1.4rem;">{_vicon}</span>
                            <div style="flex:1;">
                                <div style="display:flex; align-items:center; gap:6px;">
                                    <span style="background:{_entry['color']}; color:#fff; font-weight:800; font-size:0.75rem; padding:1px 6px; border-radius:4px;">
                                        {_b_num}
                                    </span>
                                    <div style="color:#e2e8f0; font-weight:700; font-size:0.85rem;">
                                        {_b_name}
                                    </div>
                                </div>
                                <div style="color:#8892b0; font-size:0.75rem; margin-top:3px;">
                                    Towards {_dest_sign} • <strong style="color:#ffd166;">{_entry['vehicle_id']}</strong>
                                </div>
                            </div>
                        </div>
                        <div style="color:#57d9a3; font-size:0.75rem; margin-top:5px; font-weight:600;">
                            {_entry['proximity']}
                        </div>
                        <div style="display:flex; justify-content:space-between;
                                    align-items:center; margin-top:6px;">
                            <div>
                                <div style="color:#4a9eff; font-size:1.15rem; font-weight:700;">
                                    {_entry['eta_time']}
                                </div>
                                <div style="color:#8892b0; font-size:0.72rem;">in {_eta_str}</div>
                            </div>
                            <div style="text-align:right;">
                                <div style="color:{_dcol}; font-size:0.85rem; font-weight:600;">
                                    {_entry['delay_emoji']} {_entry['delay_label']}
                                </div>
                            </div>
                        </div>
                    </div>""", unsafe_allow_html=True)

        # ── Recent stop events ─────────────────────────────────────────────
        st.divider()
        st.subheader("📋 Recent Events at this Stop")
        _df_stop_ev = ana.get_stop_events(stop_id=_sel_sid, limit=20)
        if not _df_stop_ev.empty:
            _df_stop_ev["timestamp"] = _df_stop_ev["timestamp"].dt.strftime("%H:%M:%S")
            _df_stop_ev["delay"] = _df_stop_ev["delay_seconds"].apply(format_delay)
            _ev_icon = {"stop_arrival": "🟢", "stop_departure": "🔴",
                        "position_update": "📍", "delay": "⚠️"}
            _df_stop_ev["event_type"] = _df_stop_ev["event_type"].map(
                lambda e: f"{_ev_icon.get(e,'')} {e}"
            )
            st.dataframe(
                _df_stop_ev[["timestamp", "event_type", "route_name",
                              "vehicle_id", "delay"]].rename(columns={
                    "timestamp": "Time", "event_type": "Event",
                    "route_name": "Route", "vehicle_id": "Vehicle",
                    "delay": "Delay",
                }),
                hide_index=True, use_container_width=True,
            )
        else:
            st.info("No events recorded at this stop yet.")


# ─────────────────────────────────────────────────────────────────────────────
# Journey Planner Component
# ─────────────────────────────────────────────────────────────────────────────

def _render_journey_map(plan: planner.JourneyPlan, key: str = None):
    """Render interactive Plotly route map for a planned journey."""
    fig_map = go.Figure()
    all_lats, all_lons = [], []

    # Draw each transit leg
    for leg in plan.legs:
        leg_lats = [c[0] for c in leg.path_coords]
        leg_lons = [c[1] for c in leg.path_coords]
        all_lats.extend(leg_lats)
        all_lons.extend(leg_lons)

        stop_names = [s.name for s in [leg.board_stop] + leg.intermediate_stops + [leg.alight_stop]]
        fig_map.add_trace(go.Scattermap(
            lat=leg_lats,
            lon=leg_lons,
            mode="lines+markers",
            line=dict(width=5, color=leg.color),
            marker=dict(size=6, color=leg.color),
            name=f"{'🚇' if leg.vehicle_type == 'metro' else '🚌'} {leg.route_name}",
            hovertext=stop_names,
            hoverinfo="text",
        ))

    # Add User Location Marker (if starting from current location)
    if hasattr(plan, "user_coords") and plan.user_coords:
        u_lat, u_lon = plan.user_coords
        all_lats.append(u_lat)
        all_lons.append(u_lon)
        first_s = plan.legs[0].board_stop
        fig_map.add_trace(go.Scattermap(
            lat=[u_lat, first_s.lat],
            lon=[u_lon, first_s.lon],
            mode="lines+markers",
            line=dict(width=3, color="#00d2be"),
            marker=dict(size=12, color="#00d2be"),
            name="🚶 Walk to Station",
            hovertext=[f"📍 Your Location ({plan.user_location_name})", f"🟢 Boarding Station: {first_s.name}"],
            hoverinfo="text",
        ))
        fig_map.add_trace(go.Scattermap(
            lat=[u_lat],
            lon=[u_lon],
            mode="markers+text",
            marker=dict(size=15, color="#00d2be"),
            text=["📍 Your Location"],
            textposition="top left",
            name="Your Location",
            hoverinfo="text",
        ))

    # Add Origin Marker
    first_stop = plan.legs[0].board_stop
    fig_map.add_trace(go.Scattermap(
        lat=[first_stop.lat],
        lon=[first_stop.lon],
        mode="markers+text",
        marker=dict(size=14, color="#00ff88"),
        text=["🟢 Boarding: " + first_stop.name],
        textposition="top right",
        name="Boarding Station",
        hoverinfo="text",
    ))

    # Add Transfer Markers
    for alight_s, next_board_s, _ in plan.transfer_stops:
        fig_map.add_trace(go.Scattermap(
            lat=[alight_s.lat],
            lon=[alight_s.lon],
            mode="markers+text",
            marker=dict(size=13, color="#ffbe0b"),
            text=["🟡 Interchange: " + alight_s.name],
            textposition="top right",
            name="Interchange",
            hoverinfo="text",
        ))

    # Add Destination Marker
    last_stop = plan.legs[-1].alight_stop
    fig_map.add_trace(go.Scattermap(
        lat=[last_stop.lat],
        lon=[last_stop.lon],
        mode="markers+text",
        marker=dict(size=14, color="#ff3366"),
        text=["🏁 Destination: " + last_stop.name],
        textposition="top right",
        name="Destination",
        hoverinfo="text",
    ))

    # Center map on midpoint
    if all_lats and all_lons:
        c_lat = sum(all_lats) / len(all_lats)
        c_lon = sum(all_lons) / len(all_lons)
    else:
        c_lat, c_lon = 12.9716, 77.5946

    fig_map.update_layout(
        map=dict(
            style="carto-darkmatter",
            center=dict(lat=c_lat, lon=c_lon),
            zoom=11.2,
        ),
        margin=dict(l=0, r=0, t=10, b=0),
        height=360,
        paper_bgcolor="#0e1117",
        plot_bgcolor="#0e1117",
        font=dict(color="white"),
        legend=dict(
            bgcolor="rgba(14,17,23,0.85)",
            bordercolor="#2d3247",
            borderwidth=1,
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="left",
            x=0,
        ),
    )
    st.plotly_chart(fig_map, use_container_width=True, key=key)


def _get_nearest_bus_stations_fallback(lat: float, lon: float, top_k: int = 8):
    """Fallback helper to find nearest bus stations if module caching delayed reload."""
    if hasattr(planner, "find_nearest_bus_stations"):
        return planner.find_nearest_bus_stations(lat, lon, top_k=top_k)
    bus_stops_map = {}
    for r in ROUTES:
        if r.vehicle_type == "bus":
            for s in r.stops:
                if s.name not in bus_stops_map:
                    bus_stops_map[s.name] = {
                        "name": s.name,
                        "stop_id": s.stop_id,
                        "lat": s.lat,
                        "lon": s.lon,
                        "bus_numbers": [],
                    }
                bus_num = r.bus_number or r.route_id
                if bus_num not in bus_stops_map[s.name]["bus_numbers"]:
                    bus_stops_map[s.name]["bus_numbers"].append(bus_num)

    results = []
    for s_name, data in bus_stops_map.items():
        dist_km = planner.haversine(lat, lon, data["lat"], data["lon"])
        dist_m = round(dist_km * 1000.0)
        walk_mins = max(1.0, round(dist_m / 75.0, 1))
        results.append({
            "name": data["name"],
            "stop_id": data["stop_id"],
            "lat": data["lat"],
            "lon": data["lon"],
            "distance_meters": dist_m,
            "distance_km": round(dist_km, 2),
            "walk_minutes": walk_mins,
            "bus_numbers": sorted(list(data["bus_numbers"])),
        })
    results.sort(key=lambda x: x["distance_meters"])
    return results[:top_k]


def render_journey_planner_tab(pipeline):
    """Renders a clean, user-friendly Journey Planner: source → destination → top 3 options."""
    st.markdown('<div class="section-header">🧭 Journey Planner</div>', unsafe_allow_html=True)
    st.caption("Find the best way to travel across Bengaluru — select your source and destination.")

    all_places = planner.get_all_places()
    place_names = [p["name"] for p in all_places]

    DEFAULT_ORIGIN = "Kempegowda Bus Station (Majestic)"
    DEFAULT_DEST   = "ITPL / Whitefield"

    if "jp_origin" not in st.session_state:
        st.session_state["jp_origin"] = DEFAULT_ORIGIN
    if "jp_dest" not in st.session_state:
        st.session_state["jp_dest"] = DEFAULT_DEST

    # ─────────────────────────────────────────────────────────────────────────
    # SOURCE → DESTINATION  (simple two-dropdown row with swap button)
    # ─────────────────────────────────────────────────────────────────────────
    col_from, col_swap, col_to = st.columns([5, 1, 5])

    with col_from:
        origin_cur = st.session_state.get("jp_origin", DEFAULT_ORIGIN)
        o_idx = place_names.index(origin_cur) if origin_cur in place_names else 0
        origin_sel = st.selectbox(
            "📍 From (Source)",
            place_names,
            index=o_idx,
            key="jp_origin",
        )

    with col_swap:
        st.write("")  # vertical spacer to align with dropdowns
        st.write("")
        if st.button("🔄", key="btn_swap_jp", use_container_width=True, help="Swap source and destination"):
            old_origin = st.session_state.get("jp_origin", DEFAULT_ORIGIN)
            old_dest   = st.session_state.get("jp_dest", DEFAULT_DEST)
            st.session_state["jp_origin"] = old_dest
            st.session_state["jp_dest"]   = old_origin
            st.rerun()

    with col_to:
        dest_cur = st.session_state.get("jp_dest", DEFAULT_DEST)
        d_idx = place_names.index(dest_cur) if dest_cur in place_names else min(1, len(place_names) - 1)
        dest_sel = st.selectbox(
            "🏁 To (Destination)",
            place_names,
            index=d_idx,
            key="jp_dest",
        )

    # ── Search button ────────────────────────────────────────────────────────
    if st.button("🔍  Search Routes", type="primary", use_container_width=True, key="btn_jp_search"):
        st.session_state["jp_searched"] = True

    # Validate
    if origin_sel.strip().lower() == dest_sel.strip().lower():
        st.warning("⚠️ Source and destination are the same. Please choose different stops.")
        return

    # Auto-search on first load
    if "jp_searched" not in st.session_state:
        st.session_state["jp_searched"] = True

    if not st.session_state.get("jp_searched", False):
        return

    # ─────────────────────────────────────────────────────────────────────────
    # FIND JOURNEYS — sorted fastest-first, show top 3
    # ─────────────────────────────────────────────────────────────────────────
    sim_time = datetime.now().replace(microsecond=0)

    if hasattr(pipeline, "sim") and pipeline.sim:
        active_vehicles = pipeline.sim.get_active_vehicles()
    else:
        active_vehicles = db.get_all_vehicles(active_only=True)

    raw_plans = planner.find_journeys(
        origin_sel,
        dest_sel,
        departure_time=sim_time,
        max_options=6,
        vehicles=active_vehicles,
    )

    if not raw_plans:
        st.info("ℹ️ No routes found between these two stops. Try different locations.")
        return

    # Sort by fastest and keep top 3
    raw_plans.sort(key=lambda p: (p.total_duration_minutes, p.transfer_count))
    plans = raw_plans[:3]

    fastest = plans[0].total_duration_minutes

    st.markdown("---")
    st.markdown(f"### Top {len(plans)} Routes — {origin_sel} → {dest_sel}")

    # ─────────────────────────────────────────────────────────────────────────
    # RENDER EACH OPTION AS A CLEAN CARD
    # ─────────────────────────────────────────────────────────────────────────
    for i, plan in enumerate(plans):
        leg0 = plan.legs[0]
        is_fastest = (i == 0)
        border = "#00d2be" if is_fastest else "#2d3247"
        bg = "linear-gradient(135deg, #0f1f2e 0%, #14202f 100%)" if is_fastest else "#161926"

        # Route label
        route_parts = []
        for leg in plan.legs:
            icon = "🚇" if leg.vehicle_type == "metro" else "🚌"
            num  = leg.bus_number or leg.route_id
            route_parts.append(f"{icon} {num}")
        route_label = " → ".join(route_parts)

        # Duration badge
        diff = plan.total_duration_minutes - fastest
        if diff == 0:
            time_badge = f"<span style='background:#00d2be; color:#0e1117; font-weight:800; font-size:0.78rem; padding:3px 10px; border-radius:6px;'>⚡ FASTEST</span>"
        else:
            time_badge = f"<span style='background:#2d3247; color:#ffd166; font-weight:700; font-size:0.78rem; padding:3px 10px; border-radius:6px;'>+{diff:.0f} min</span>"

        # Transfer text
        if plan.transfer_count == 0:
            transfer_txt = "Direct"
        else:
            transfer_txt = f"{plan.transfer_count} transfer{'s' if plan.transfer_count > 1 else ''}"

        # ── Card header (HTML) ───────────────────────────────────────────
        header_card = textwrap.dedent(f"""
        <div style="background:{bg}; border:2px solid {border}; border-radius:14px; padding:18px 22px; margin-bottom:10px;">
            <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:10px;">
                <div style="display:flex; align-items:center; gap:10px; flex-wrap:wrap;">
                    <span style="background:{'#00d2be' if is_fastest else '#3b82f6'}; color:#0e1117; font-weight:800; padding:4px 12px; border-radius:20px; font-size:0.82rem;">
                        Option {i+1}
                    </span>
                    <span style="color:#ffffff; font-size:1.1rem; font-weight:700;">{route_label}</span>
                    {time_badge}
                </div>
                <div style="display:flex; gap:20px; align-items:center;">
                    <div style="text-align:center;">
                        <div style="color:#57d9a3; font-size:1.4rem; font-weight:800;">{plan.total_duration_minutes:.0f}<span style="font-size:0.8rem; font-weight:600;"> min</span></div>
                    </div>
                    <div style="text-align:center;">
                        <div style="color:#ffd166; font-size:1.0rem; font-weight:700;">₹{plan.fare_inr}</div>
                    </div>
                    <div style="text-align:center;">
                        <div style="color:#8892b0; font-size:0.85rem;">{transfer_txt}</div>
                    </div>
                </div>
            </div>
        </div>
        """).strip()
        st.markdown(header_card, unsafe_allow_html=True)

        # ── Timeline (native Streamlit markdown — no HTML rendering issues) ─
        for li, leg in enumerate(plan.legs):
            v_icon = "🚇" if leg.vehicle_type == "metro" else "🚌"
            b_num  = leg.bus_number or leg.route_id
            b_name = leg.bus_name or leg.route_name

            st.markdown(
                f"&nbsp;&nbsp; 🕐 **{leg.board_time.strftime('%I:%M %p')}** · "
                f"Board {v_icon} **{b_num}** {b_name} at **{leg.board_stop.name}** · "
                f"{leg.num_stops} stops"
            )

            # Transfer marker
            if li < len(plan.transfer_stops):
                alight_s, next_board_s, walk_mins = plan.transfer_stops[li]
                st.markdown(
                    f"&nbsp;&nbsp; 🔄 **{leg.alight_time.strftime('%I:%M %p')}** · "
                    f"Transfer at **{alight_s.name}** · ~{walk_mins:.0f} min walk"
                )

        # Final destination
        last_leg = plan.legs[-1]
        st.markdown(
            f"&nbsp;&nbsp; 🏁 **{plan.arrival_time.strftime('%I:%M %p')}** · "
            f"Arrive at **{last_leg.alight_stop.name}**"
        )

        # Compact route map (collapsed by default)
        with st.expander(f"🗺️ View Route Map — Option {i+1}"):
            _render_journey_map(plan, key=f"journey_map_opt_{i+1}")

        st.markdown("---")

    st.markdown("""
    <div style="text-align:center; color:#4a5568; font-size:0.78rem; margin-top:10px; padding:8px;">
        Route geometry uses linear interpolation between stops (demonstration only — not actual road/rail paths).
    </div>
    """, unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════════════════════
# TAB 4 — Multi-Modal Journey Planner
# ════════════════════════════════════════════════════════════════════════════

with tabs[4]:
    render_journey_planner_tab(pipeline)


# ════════════════════════════════════════════════════════════════════════════
# TAB 5 — Peak Travel Periods
# ════════════════════════════════════════════════════════════════════════════

with tabs[5]:
    st.markdown('<div class="section-header">📈 Peak Travel Periods</div>', unsafe_allow_html=True)

    col_heat, col_profile = st.columns([3, 2])

    with col_heat:
        st.subheader("🌡️ Vehicle Density Heatmap (Hour × Day)")
        df_heat = ana.get_peak_heatmap()
        if df_heat.empty or len(df_heat) < 2:
            st.info("Heatmap builds up as data accumulates — check back after a few minutes.")
        else:
            day_order = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
            pivot = df_heat.pivot_table(
                index="day", columns="hour", values="avg_vehicles", aggfunc="mean"
            ).reindex([d for d in day_order if d in df_heat["day"].unique()])
            fig_heat = px.imshow(
                pivot,
                labels=dict(x="Hour of Day", y="Day", color="Avg Vehicles"),
                color_continuous_scale="Blues",
                aspect="auto",
                title="Average Active Vehicles by Hour",
            )
            fig_heat.update_layout(
                height=380,
                paper_bgcolor="#0e1117", plot_bgcolor="#0e1117",
                font=dict(color="white"),
                coloraxis_colorbar=dict(tickfont=dict(color="white")),
            )
            st.plotly_chart(fig_heat, use_container_width=True)

    with col_profile:
        st.subheader("⏱️ Avg Delay by Hour of Day")
        df_delay_h = ana.get_hourly_delay_profile()
        if df_delay_h.empty:
            st.info("Accumulating delay data…")
        else:
            fig_delay_h = px.bar(
                df_delay_h, x="hour", y="avg_delay",
                labels={"hour": "Hour", "avg_delay": "Avg Delay (s)"},
                color="avg_delay",
                color_continuous_scale="RdYlGn_r",
            )
            # Mark peak hours
            for start, end in [PEAK_HOURS["morning"], PEAK_HOURS["evening"]]:
                fig_delay_h.add_vrect(
                    x0=start - 0.5, x1=end - 0.5,
                    fillcolor="rgba(255,165,0,0.12)",
                    line_width=0,
                    annotation_text="Peak",
                    annotation_position="top left",
                )
            fig_delay_h.update_layout(
                height=380,
                paper_bgcolor="#0e1117", plot_bgcolor="#0e1117",
                font=dict(color="white"),
                showlegend=False,
                coloraxis_showscale=False,
                xaxis=dict(tickmode="linear", dtick=1, gridcolor="#2d3247"),
                yaxis=dict(gridcolor="#2d3247"),
            )
            st.plotly_chart(fig_delay_h, use_container_width=True)

    from config import PEAK_HOURS as PH
    st.divider()
    st.subheader("🕐 Peak Period Configuration")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.info(f"🌅 **Morning Peak**\n{PH['morning'][0]}:00 – {PH['morning'][1]}:00")
    with c2:
        st.info(f"🌆 **Evening Peak**\n{PH['evening'][0]}:00 – {PH['evening'][1]}:00")
    with c3:
        period = kpis["peak_label"]
        st.success(f"**Current Period**\n{period}")


# ════════════════════════════════════════════════════════════════════════════
# TAB 6 — Route Performance Leaderboard
# ════════════════════════════════════════════════════════════════════════════

with tabs[6]:
    st.markdown('<div class="section-header">🏆 Route Performance Leaderboard</div>', unsafe_allow_html=True)

    df_lb = ana.get_route_performance_leaderboard()

    if df_lb.empty:
        st.info("Performance data is computing — please wait a moment.")
    else:
        # Score gauge bars (rendered as progress bars)
        for _, row in df_lb.iterrows():
            score  = row["perf_score"]
            color  = row.get("color", "#4a9eff")
            icon   = "🚌" if row["vehicle_type"] == "bus" else "🚆"
            delay  = row.get("delay_label", format_delay(row.get("avg_delay_s", 0)))

            c1, c2, c3, c4, c5 = st.columns([3, 1.5, 1.5, 1.5, 1.5])
            with c1:
                st.markdown(f"{icon} **{row['route_name']}**")
                st.progress(score / 100)
            with c2:
                st.metric("Score", f"{score:.1f}")
            with c3:
                st.metric("On-Time", f"{row['on_time_pct']:.1f}%")
            with c4:
                st.metric("Avg Delay", f"{row.get('avg_delay_s', 0):.0f}s")
            with c5:
                st.metric("Vehicles", int(row.get("vehicle_count", 0)))

        st.divider()

        # Scatter: On-time% vs Avg Delay
        st.subheader("📊 Performance Matrix")
        fig_scatter = px.scatter(
            df_lb.reset_index(),
            x="avg_delay_s",
            y="on_time_pct",
            size="vehicle_count",
            color="vehicle_type",
            color_discrete_map={"bus": "#2A9D8F", "metro": "#8338EC"},
            text="route_name",
            labels={"avg_delay_s": "Avg Delay (s)", "on_time_pct": "On-Time Rate (%)"},
            size_max=40,
        )
        fig_scatter.update_traces(textposition="top center", textfont=dict(size=10))
        fig_scatter.update_layout(
            height=420, paper_bgcolor="#0e1117", plot_bgcolor="#0e1117",
            font=dict(color="white"),
            xaxis=dict(gridcolor="#2d3247"),
            yaxis=dict(gridcolor="#2d3247"),
            legend=dict(bgcolor="rgba(0,0,0,0)"),
        )
        st.plotly_chart(fig_scatter, use_container_width=True)


# ════════════════════════════════════════════════════════════════════════════
# TAB 5 — Bus Analytics  (road-based, congestion-focused)
# ════════════════════════════════════════════════════════════════════════════

def render_bus_tab():
    """Bus-specific analytics: congestion, corridor delays, overcrowding."""
    BUS_COLOR = "#06D6A0"   # teal accent for bus charts
    BUS_WARN  = "#FFD166"   # amber for warnings

    df_v = ana.get_live_vehicles()
    if not df_v.empty:
        df_v = df_v[df_v["vehicle_type"] == "bus"]

    # ── KPI row ────────────────────────────────────────────────────────────
    if not df_v.empty:
        n_bus      = len(df_v)
        avg_delay  = df_v["delay_seconds"].mean()
        on_time    = (df_v["delay_seconds"] < 60).sum() / n_bus * 100
        avg_occ    = df_v["occupancy"].mean() * 100
        overcrowd  = int((df_v["occupancy"] > 0.85).sum())
    else:
        n_bus = avg_delay = on_time = avg_occ = overcrowd = 0

    kpi_items = [
        ("🚌 Buses Active",      n_bus,                   "#06D6A0"),
        ("⏱️ Avg Delay",         f"{avg_delay:.0f}s",      "#4a9eff"),
        ("✅ On-Time Rate",      f"{on_time:.1f}%",        "#57d9a3"),
        ("🔴 Overcrowded",       overcrowd,               "#ff6b6b"),
    ]
    cols = st.columns(4)
    for col, (lbl, val, accent) in zip(cols, kpi_items):
        with col:
            st.markdown(f"""
            <div class="metric-card" style="border-top:3px solid {accent}">
                <div class="metric-value" style="color:{accent}">{val}</div>
                <div class="metric-label">{lbl}</div>
            </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── All Bus Routes Cards (always shown, live data merged in) ──────────
    st.subheader("🗺️ All Bus Routes")
    bus_routes_list = [r for r in ROUTES if r.vehicle_type == "bus"]
    live_by_route = {}
    if not df_v.empty:
        for _rid, _grp in df_v.groupby("route_id"):
            live_by_route[_rid] = {
                "active":    len(_grp),
                "avg_delay": _grp["delay_seconds"].mean(),
                "avg_occ":   _grp["occupancy"].mean() * 100,
                "on_time":   (_grp["delay_seconds"] < 60).sum() / len(_grp) * 100,
            }

    for row_start in range(0, len(bus_routes_list), 3):
        row_routes = bus_routes_list[row_start:row_start + 3]
        _cols = st.columns(3)
        for _col, _route in zip(_cols, row_routes):
            _live     = live_by_route.get(_route.route_id, {})
            _active   = _live.get("active", 0)
            _avg_d    = _live.get("avg_delay", 0)
            _avg_o    = _live.get("avg_occ", 0)
            _on_t     = _live.get("on_time", 100)
            _dlabel   = "#57d9a3" if _avg_d < 60 else ("#FFD166" if _avg_d < 300 else "#ff6b6b")
            _dot      = "🟢" if _avg_d < 60 else ("🟡" if _avg_d < 300 else "🔴")
            _endpoint = " → ".join(
                s.name.split("(")[0].strip() for s in [_route.stops[0], _route.stops[-1]]
            )
            with _col:
                st.markdown(f"""
                <div style="background:linear-gradient(135deg,#1a1f2e,#22293b);
                            border-left:4px solid {_route.color};
                            border-radius:10px; padding:14px 16px;
                            margin-bottom:10px; min-height:175px;">
                    <div style="display:flex; align-items:center; gap:8px; margin-bottom:6px;">
                        <div style="background:{_route.color}; color:#fff; font-size:0.7rem;
                                    font-weight:700; padding:2px 8px; border-radius:12px;
                                    letter-spacing:0.5px;">{_route.route_id}</div>
                        <span>{_dot}</span>
                    </div>
                    <div style="color:#e2e8f0; font-weight:600; font-size:0.9rem; margin-bottom:3px;">
                        {_route.name}
                    </div>
                    <div style="color:#8892b0; font-size:0.73rem; margin-bottom:9px;">
                        🛑 {_endpoint}
                    </div>
                    <div style="display:grid; grid-template-columns:1fr 1fr; gap:5px;">
                        <div style="background:rgba(255,255,255,0.05); border-radius:6px;
                                    padding:5px 8px; text-align:center;">
                            <div style="color:{_route.color}; font-size:1.05rem; font-weight:700;">{_active}</div>
                            <div style="color:#8892b0; font-size:0.68rem;">Active Buses</div>
                        </div>
                        <div style="background:rgba(255,255,255,0.05); border-radius:6px;
                                    padding:5px 8px; text-align:center;">
                            <div style="color:{_dlabel}; font-size:1.05rem; font-weight:700;">{_avg_d:.0f}s</div>
                            <div style="color:#8892b0; font-size:0.68rem;">Avg Delay</div>
                        </div>
                        <div style="background:rgba(255,255,255,0.05); border-radius:6px;
                                    padding:5px 8px; text-align:center;">
                            <div style="color:#4a9eff; font-size:1.05rem; font-weight:700;">{_avg_o:.0f}%</div>
                            <div style="color:#8892b0; font-size:0.68rem;">Avg Load</div>
                        </div>
                        <div style="background:rgba(255,255,255,0.05); border-radius:6px;
                                    padding:5px 8px; text-align:center;">
                            <div style="color:#57d9a3; font-size:1.05rem; font-weight:700;">{_on_t:.0f}%</div>
                            <div style="color:#8892b0; font-size:0.68rem;">On-Time</div>
                        </div>
                    </div>
                    <div style="color:#8892b0; font-size:0.7rem; margin-top:7px;">
                        ⏱ {_route.headway_minutes} min headway &nbsp;| 🕐 {_route.first_departure}–{_route.last_departure}
                    </div>
                </div>""", unsafe_allow_html=True)

    st.divider()

    col_hist, col_occ = st.columns(2)

    with col_hist:
        st.subheader("📊 Delay Distribution by Corridor")
        df_delays = ana.get_delay_distribution(vehicle_type="bus")
        if not df_delays.empty:
            fig_hist = px.histogram(
                df_delays, x="delay_seconds", nbins=35,
                color="route_name",
                labels={"delay_seconds": "Delay (s)", "count": "Buses"},
                color_discrete_sequence=px.colors.qualitative.Pastel,
            )
            fig_hist.add_vline(x=60, line_dash="dash", line_color=BUS_WARN,
                               annotation_text="60s late threshold",
                               annotation_font_color=BUS_WARN)
            fig_hist.add_vline(x=300, line_dash="dot", line_color="#ff6b6b",
                               annotation_text="5 min late",
                               annotation_font_color="#ff6b6b")
            fig_hist.update_layout(
                height=360, paper_bgcolor="#0e1117", plot_bgcolor="#0e1117",
                font=dict(color="white"),
                legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(size=10)),
                xaxis=dict(gridcolor="#2d3247", title="Delay (seconds)"),
                yaxis=dict(gridcolor="#2d3247"),
                bargap=0.05,
            )
            st.plotly_chart(fig_hist, use_container_width=True)
        else:
            st.info("No bus delay data yet.")

    with col_occ:
        st.subheader("👥 Passenger Load by Route")
        if not df_v.empty:
            occ_df = df_v.groupby("route_name")["occupancy"].mean().reset_index()
            occ_df["occupancy_pct"] = occ_df["occupancy"] * 100
            occ_df = occ_df.sort_values("occupancy_pct", ascending=True)
            # color: green → amber → red based on load
            occ_colors = [
                "#ff6b6b" if v > 85 else ("#FFD166" if v > 65 else "#06D6A0")
                for v in occ_df["occupancy_pct"]
            ]
            fig_occ = go.Figure(go.Bar(
                y=occ_df["route_name"],
                x=occ_df["occupancy_pct"],
                orientation="h",
                marker_color=occ_colors,
                text=occ_df["occupancy_pct"].round(1).astype(str) + "%",
                textposition="outside",
            ))
            fig_occ.add_vline(x=85, line_dash="dash", line_color="#ff6b6b",
                              annotation_text="Overcrowded", annotation_font_color="#ff6b6b")
            fig_occ.update_layout(
                height=360, paper_bgcolor="#0e1117", plot_bgcolor="#0e1117",
                font=dict(color="white"),
                xaxis=dict(gridcolor="#2d3247", range=[0, 115], title="Avg Occupancy (%)"),
                yaxis=dict(tickfont=dict(size=11)),
                margin=dict(r=10),
            )
            st.plotly_chart(fig_occ, use_container_width=True)
        else:
            st.info("No buses active.")

    # ── Row 2: Delay trend + Speed scatter ───────────────────────────────
    st.subheader("📉 Corridor Delay Trend Over Time")
    df_trend_v = ana.get_delay_over_time(limit=400)
    if not df_trend_v.empty:
        bus_route_ids = [r.route_id for r in ROUTES if r.vehicle_type == "bus"]
        df_trend_v = df_trend_v[df_trend_v["route_id"].isin(bus_route_ids)]
        if not df_trend_v.empty:
            fig_line = px.line(
                df_trend_v, x="timestamp", y="delay_seconds",
                color="route_name",
                labels={"delay_seconds": "Delay (s)", "timestamp": "Time"},
                color_discrete_sequence=px.colors.qualitative.Pastel,
            )
            fig_line.add_hrect(y0=60, y1=df_trend_v["delay_seconds"].max() + 10,
                               fillcolor="rgba(255,107,107,0.06)", line_width=0)
            fig_line.update_layout(
                height=320, paper_bgcolor="#0e1117", plot_bgcolor="#0e1117",
                font=dict(color="white"),
                legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(size=10)),
                xaxis=dict(gridcolor="#2d3247"),
                yaxis=dict(gridcolor="#2d3247"),
            )
            st.plotly_chart(fig_line, use_container_width=True)
        else:
            st.info("Delay trend data is accumulating — check back shortly.")
    else:
        st.info("Delay trend data is accumulating — check back shortly.")

    # ── Row 3: Trip duration box plot + overcrowding alert table ─────────
    col_dur, col_alert = st.columns([3, 2])

    with col_dur:
        st.subheader("⏳ Trip Duration by Corridor")
        df_dur = ana.get_trip_durations(status="completed")
        if not df_dur.empty:
            bus_route_ids = [r.route_id for r in ROUTES if r.vehicle_type == "bus"]
            df_dur = df_dur[df_dur["route_id"].isin(bus_route_ids)]
            if not df_dur.empty:
                df_dur["duration_min"] = df_dur["duration_seconds"] / 60
                fig_dur = px.box(
                    df_dur, x="route_name", y="duration_min",
                    labels={"duration_min": "Duration (min)", "route_name": ""},
                    color="route_name",
                    color_discrete_sequence=px.colors.qualitative.Pastel,
                )
                fig_dur.update_layout(
                    height=360, showlegend=False,
                    paper_bgcolor="#0e1117", plot_bgcolor="#0e1117",
                    font=dict(color="white"),
                    xaxis=dict(tickangle=-30, gridcolor="#2d3247"),
                    yaxis=dict(gridcolor="#2d3247"),
                )
                st.plotly_chart(fig_dur, use_container_width=True)
            else:
                st.info("No completed bus trips yet.")
        else:
            st.info("No completed trips yet.")

    with col_alert:
        st.subheader("🚨 Overcrowding Alerts")
        if not df_v.empty:
            oc = df_v[df_v["occupancy"] > 0.85][["vehicle_id", "route_name", "occupancy", "delay_seconds"]].copy()
            if not oc.empty:
                oc["occupancy"] = (oc["occupancy"] * 100).round(1).astype(str) + "%"
                oc["delay_seconds"] = oc["delay_seconds"].round(0).astype(int).astype(str) + "s"
                oc = oc.rename(columns={
                    "vehicle_id": "Bus", "route_name": "Route",
                    "occupancy": "Load", "delay_seconds": "Delay",
                })
                st.dataframe(oc, hide_index=True, use_container_width=True, height=300)
            else:
                st.success("✅ No buses are currently overcrowded.")
        else:
            st.info("No buses active.")

    # ── Route summary table (all routes, live data merged in) ─────────────
    st.subheader("📋 Bus Corridor Summary")
    _live_rc = ana.get_vehicle_count_by_route()
    _live_rc_bus = _live_rc[_live_rc["vehicle_type"] == "bus"] if not _live_rc.empty else pd.DataFrame()
    _live_map = {row["route_id"]: row for _, row in _live_rc_bus.iterrows()} if not _live_rc_bus.empty else {}

    _all_bus_rows = []
    for _route in [r for r in ROUTES if r.vehicle_type == "bus"]:
        _l = _live_map.get(_route.route_id, {})
        _all_bus_rows.append({
            "Route": _route.name,
            "ID": _route.route_id,
            "Stops": len(_route.stops),
            "Headway": f"{_route.headway_minutes} min",
            "Service Hours": f"{_route.first_departure}–{_route.last_departure}",
            "Buses Active": int(_l.get("vehicle_count", 0)),
            "Avg Delay (s)": round(float(_l.get("avg_delay", 0)), 1),
            "Avg Load (%)": round(float(_l.get("avg_occupancy", 0)) * 100, 1),
        })
    st.dataframe(pd.DataFrame(_all_bus_rows), hide_index=True, use_container_width=True)


# ════════════════════════════════════════════════════════════════════════════
# TAB 6 — Metro Analytics  (rail-based, frequency & line-performance focus)
# ════════════════════════════════════════════════════════════════════════════

def render_metro_tab():
    """Metro-specific analytics: line frequency, headway, station load, speed."""
    METRO_PURPLE = "#8338EC"
    METRO_GREEN  = "#2EC4B6"
    METRO_YELLOW = "#FFBE0B"
    LINE_COLORS  = {
        "Namma Metro Purple Line":           METRO_PURPLE,
        "Namma Metro Green Line":            METRO_GREEN,
        "Namma Metro Yellow Line (Simulated)": METRO_YELLOW,
    }

    df_v = ana.get_live_vehicles()
    if not df_v.empty:
        df_v = df_v[df_v["vehicle_type"] == "metro"]

    metro_routes = [r for r in ROUTES if r.vehicle_type == "metro"]
    metro_route_ids = [r.route_id for r in metro_routes]

    # ── KPI row (Metro-specific metrics) ──────────────────────────────────
    if not df_v.empty:
        n_metro    = len(df_v)
        avg_delay  = df_v["delay_seconds"].mean()
        on_time    = (df_v["delay_seconds"] < 90).sum() / n_metro * 100  # metro SLA = 90s
        avg_speed  = df_v["speed_kmh"].mean() if "speed_kmh" in df_v.columns else 0
        avg_occ    = df_v["occupancy"].mean() * 100
    else:
        n_metro = avg_delay = on_time = avg_speed = avg_occ = 0

    kpi_items = [
        ("🚇 Trains Running",     n_metro,                  METRO_PURPLE),
        ("⏱️ Avg Delay",          f"{avg_delay:.0f}s",       "#4a9eff"),
        ("✅ On-Time (≤90s SLA)", f"{on_time:.1f}%",         METRO_GREEN),
        ("⚡ Avg Speed",          f"{avg_speed:.1f} km/h",   METRO_YELLOW),
    ]
    cols = st.columns(4)
    for col, (lbl, val, accent) in zip(cols, kpi_items):
        with col:
            st.markdown(f"""
            <div class="metric-card" style="border-top:3px solid {accent}; background:linear-gradient(135deg,#12152a,#1a1f33)">
                <div class="metric-value" style="color:{accent}">{val}</div>
                <div class="metric-label">{lbl}</div>
            </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Row 1: Line comparison bar + Occupancy by line ───────────────────
    col_line, col_occ = st.columns(2)

    with col_line:
        st.subheader("🚉 Vehicles per Metro Line")
        df_rc = ana.get_vehicle_count_by_route()
        if not df_rc.empty:
            df_metro = df_rc[df_rc["vehicle_type"] == "metro"].copy()
            if not df_metro.empty:
                color_map = {name: col for name, col in LINE_COLORS.items()}
                fig_bar = go.Figure()
                for _, row in df_metro.iterrows():
                    c = color_map.get(row["route_name"], METRO_PURPLE)
                    fig_bar.add_trace(go.Bar(
                        x=[row["route_name"]],
                        y=[row["vehicle_count"]],
                        name=row["route_name"],
                        marker_color=c,
                        text=[row["vehicle_count"]],
                        textposition="outside",
                    ))
                fig_bar.update_layout(
                    height=340, paper_bgcolor="#0e1117", plot_bgcolor="#0e1117",
                    font=dict(color="white"), showlegend=False,
                    xaxis=dict(gridcolor="#2d3247", tickangle=-15),
                    yaxis=dict(gridcolor="#2d3247", title="Active Trains"),
                    margin=dict(t=10),
                )
                st.plotly_chart(fig_bar, use_container_width=True)
            else:
                st.info("No metro data available yet.")
        else:
            st.info("No metro data available yet.")

    with col_occ:
        st.subheader("🪑 Carriage Load by Line")
        if not df_v.empty:
            occ_df = df_v.groupby("route_name")["occupancy"].mean().reset_index()
            occ_df["occupancy_pct"] = occ_df["occupancy"] * 100
            occ_df["color"] = occ_df["route_name"].map(LINE_COLORS).fillna(METRO_PURPLE)
            fig_gauge = go.Figure()
            for i, row in occ_df.iterrows():
                fig_gauge.add_trace(go.Bar(
                    x=[row["occupancy_pct"]],
                    y=[row["route_name"]],
                    orientation="h",
                    marker=dict(
                        color=row["color"],
                        line=dict(color="#0e1117", width=1),
                    ),
                    text=f"{row['occupancy_pct']:.1f}%",
                    textposition="outside",
                    showlegend=False,
                ))
            fig_gauge.add_vline(x=80, line_dash="dash", line_color="#ff6b6b",
                                annotation_text="Crush load", annotation_font_color="#ff6b6b")
            fig_gauge.update_layout(
                height=340, paper_bgcolor="#0e1117", plot_bgcolor="#0e1117",
                font=dict(color="white"),
                xaxis=dict(gridcolor="#2d3247", range=[0, 115], title="Avg Carriage Load (%)"),
                yaxis=dict(tickfont=dict(size=12)),
                margin=dict(r=10),
            )
            st.plotly_chart(fig_gauge, use_container_width=True)
        else:
            st.info("No metro trains active.")

    # ── Row 2: Delay distribution violin + Speed vs Delay scatter ────────
    col_viol, col_spd = st.columns(2)

    with col_viol:
        st.subheader("📊 Delay Distribution by Metro Line")
        df_delays = ana.get_delay_distribution(vehicle_type="metro")
        if not df_delays.empty:
            color_seq = [METRO_PURPLE, METRO_GREEN, METRO_YELLOW]
            fig_viol = go.Figure()
            for idx, rname in enumerate(df_delays["route_name"].unique()):
                subset = df_delays[df_delays["route_name"] == rname]
                fig_viol.add_trace(go.Violin(
                    y=subset["delay_seconds"],
                    name=rname,
                    box_visible=True,
                    meanline_visible=True,
                    fillcolor=color_seq[idx % len(color_seq)],
                    line_color="white",
                    opacity=0.7,
                ))
            fig_viol.add_hline(y=90, line_dash="dash", line_color="#ffa94d",
                               annotation_text="SLA 90s",
                               annotation_font_color="#ffa94d")
            fig_viol.update_layout(
                height=360, paper_bgcolor="#0e1117", plot_bgcolor="#0e1117",
                font=dict(color="white"),
                legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(size=10)),
                xaxis=dict(gridcolor="#2d3247"),
                yaxis=dict(gridcolor="#2d3247", title="Delay (s)"),
                violinmode="overlay",
            )
            st.plotly_chart(fig_viol, use_container_width=True)
        else:
            st.info("No metro delay data yet.")

    with col_spd:
        st.subheader("⚡ Speed vs. Delay (Live Trains)")
        if not df_v.empty and "speed_kmh" in df_v.columns:
            spd_df = df_v[["route_name", "speed_kmh", "delay_seconds", "vehicle_id"]].copy()
            spd_df["color"] = spd_df["route_name"].map(LINE_COLORS).fillna(METRO_PURPLE)
            fig_spd = go.Figure()
            for rname, grp in spd_df.groupby("route_name"):
                fig_spd.add_trace(go.Scatter(
                    x=grp["speed_kmh"],
                    y=grp["delay_seconds"],
                    mode="markers",
                    name=rname,
                    marker=dict(
                        size=10,
                        color=LINE_COLORS.get(rname, METRO_PURPLE),
                        opacity=0.85,
                        line=dict(color="white", width=0.5),
                    ),
                    text=grp["vehicle_id"],
                    hovertemplate="%{text}<br>Speed: %{x:.1f} km/h<br>Delay: %{y}s",
                ))
            fig_spd.add_hline(y=90, line_dash="dash", line_color="#ffa94d",
                              annotation_text="SLA", annotation_font_color="#ffa94d")
            fig_spd.update_layout(
                height=360, paper_bgcolor="#0e1117", plot_bgcolor="#0e1117",
                font=dict(color="white"),
                legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(size=10)),
                xaxis=dict(gridcolor="#2d3247", title="Speed (km/h)"),
                yaxis=dict(gridcolor="#2d3247", title="Delay (s)"),
            )
            st.plotly_chart(fig_spd, use_container_width=True)
        else:
            st.info("Speed data not yet available.")

    # ── Row 3: Delay trend (area chart per line) ──────────────────────────
    st.subheader("📈 Metro Line Delay Trend")
    df_trend_m = ana.get_delay_over_time(limit=400)
    if not df_trend_m.empty:
        df_trend_m = df_trend_m[df_trend_m["route_id"].isin(metro_route_ids)]
        if not df_trend_m.empty:
            fig_area = go.Figure()
            for rname, grp in df_trend_m.groupby("route_name"):
                fig_area.add_trace(go.Scatter(
                    x=grp["timestamp"],
                    y=grp["delay_seconds"],
                    mode="lines",
                    name=rname,
                   line=dict(color=LINE_COLORS.get(rname, METRO_PURPLE), width=2),
                    fill="tozeroy",
                    fillcolor="rgba(131, 56, 236, 0.12)",
                ))
            fig_area.add_hline(y=90, line_dash="dot", line_color="#ffa94d",
                               annotation_text="SLA 90s", annotation_font_color="#ffa94d")
            fig_area.update_layout(
                height=320, paper_bgcolor="#0e1117", plot_bgcolor="#0e1117",
                font=dict(color="white"),
                legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(size=10)),
                xaxis=dict(gridcolor="#2d3247"),
                yaxis=dict(gridcolor="#2d3247", title="Delay (s)"),
            )
            st.plotly_chart(fig_area, use_container_width=True)
        else:
            st.info("Metro delay trend is accumulating — check back shortly.")
    else:
        st.info("Delay trend data is accumulating — check back shortly.")

    # ── Row 4: Trip durations (violin per line) + Line comparison table ──
    col_trip, col_tbl = st.columns([3, 2])

    with col_trip:
        st.subheader("⏳ Journey Time by Metro Line")
        df_dur = ana.get_trip_durations(status="completed")
        if not df_dur.empty:
            df_dur = df_dur[df_dur["route_id"].isin(metro_route_ids)]
            if not df_dur.empty:
                df_dur["duration_min"] = df_dur["duration_seconds"] / 60
                color_seq = [METRO_PURPLE, METRO_GREEN, METRO_YELLOW]
                fig_dur = go.Figure()
                for idx, rname in enumerate(df_dur["route_name"].unique()):
                    subset = df_dur[df_dur["route_name"] == rname]
                    fig_dur.add_trace(go.Violin(
                        y=subset["duration_min"],
                        name=rname,
                        box_visible=True,
                        meanline_visible=True,
                        fillcolor=color_seq[idx % len(color_seq)],
                        line_color="white",
                        opacity=0.75,
                    ))
                fig_dur.update_layout(
                    height=360, paper_bgcolor="#0e1117", plot_bgcolor="#0e1117",
                    font=dict(color="white"), showlegend=True,
                    legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(size=10)),
                    xaxis=dict(gridcolor="#2d3247"),
                    yaxis=dict(gridcolor="#2d3247", title="Journey Time (min)"),
                    violinmode="group",
                )
                st.plotly_chart(fig_dur, use_container_width=True)
            else:
                st.info("No completed metro trips yet.")
        else:
            st.info("No completed trips yet.")

    with col_tbl:
        st.subheader("📋 Metro Line Summary")
        df_rc = ana.get_vehicle_count_by_route()
        if not df_rc.empty:
            df_metro = df_rc[df_rc["vehicle_type"] == "metro"].copy()
            if not df_metro.empty:
                df_metro["avg_delay"]     = df_metro["avg_delay"].round(1)
                df_metro["avg_occupancy"] = (df_metro["avg_occupancy"] * 100).round(1)
                df_metro["headway_min"] = [
                    ROUTE_BY_ID[rid].headway_minutes
                    for rid in df_metro["route_id"]
                    if rid in ROUTE_BY_ID
                ] if "route_id" in df_metro.columns else "-"
                display_cols = ["route_name", "vehicle_count", "avg_delay", "avg_occupancy"]
                if "headway_min" in df_metro.columns:
                    display_cols.append("headway_min")
                st.dataframe(
                    df_metro[display_cols].rename(columns={
                        "route_name": "Line", "vehicle_count": "Trains",
                        "avg_delay": "Avg Delay (s)", "avg_occupancy": "Avg Load (%)",
                        "headway_min": "Headway (min)",
                    }),
                    hide_index=True,
                    use_container_width=True,
                )
            else:
                st.info("No metro data yet.")


with tabs[7]:
    st.markdown('<div class="section-header">🚌 Bus Analytics — Road Network Performance</div>', unsafe_allow_html=True)
    render_bus_tab()

with tabs[8]:
    st.markdown('<div class="section-header">🚇 Metro Analytics — Namma Metro Line Performance</div>', unsafe_allow_html=True)
    render_metro_tab()


# ════════════════════════════════════════════════════════════════════════════
# TAB 9 — Event Log
# ════════════════════════════════════════════════════════════════════════════

with tabs[9]:
    st.markdown('<div class="section-header">📜 Historical Event Log</div>', unsafe_allow_html=True)

    col_f1, col_f2, col_f3 = st.columns(3)
    with col_f1:
        event_type_filter = st.selectbox(
            "Event type",
            ["All", "position_update", "stop_arrival", "stop_departure", "delay"],
        )
    with col_f2:
        route_filter_log = st.selectbox(
            "Route",
            ["All"] + [r.route_id for r in ROUTES],
            format_func=lambda x: x if x == "All" else ROUTE_BY_ID[x].name,
        )
    with col_f3:
        log_limit = st.slider("Max rows", 50, 500, 100, 50)

    df_events = pd.DataFrame(db.get_recent_events(
        limit=log_limit,
        event_type=None if event_type_filter == "All" else event_type_filter,
        route_id=None if route_filter_log == "All" else route_filter_log,
    ))

    if df_events.empty:
        st.info("No events yet. The pipeline is warming up…")
    else:
        # Human-readable columns
        df_events["delay_str"]  = df_events["delay_seconds"].apply(format_delay)
        df_events["emoji"] = df_events["event_type"].map({
            "position_update":  "📍",
            "stop_arrival":     "🟢",
            "stop_departure":   "🔴",
            "delay":            "⚠️",
        }).fillna("❓")
        df_events["event"] = df_events["emoji"] + " " + df_events["event_type"]

        display_cols = ["timestamp", "event", "route_id", "vehicle_id", "stop_id", "delay_str"]
        display_cols = [c for c in display_cols if c in df_events.columns]

        st.dataframe(
            df_events[display_cols].rename(columns={
                "timestamp": "Time", "event": "Event",
                "route_id": "Route", "vehicle_id": "Vehicle",
                "stop_id": "Stop", "delay_str": "Delay",
            }),
            hide_index=True,
            use_container_width=True,
            height=500,
        )

        # Event type breakdown
        st.subheader("📊 Event Type Breakdown")
        event_counts = df_events["event_type"].value_counts().reset_index()
        event_counts.columns = ["event_type", "count"]
        fig_ec = px.bar(
            event_counts, x="event_type", y="count",
            color="event_type",
            labels={"event_type": "Event Type", "count": "Count"},
        )
        fig_ec.update_layout(
            height=280, showlegend=False,
            paper_bgcolor="#0e1117", plot_bgcolor="#0e1117",
            font=dict(color="white"),
            xaxis=dict(gridcolor="#2d3247"),
            yaxis=dict(gridcolor="#2d3247"),
        )
        st.plotly_chart(fig_ec, use_container_width=True)


# ════════════════════════════════════════════════════════════════════════════
# TAB 10 — Pipeline Health Dashboard
# ════════════════════════════════════════════════════════════════════════════

with tabs[10]:
    st.markdown('<div class="section-header">🩺 Pipeline Health & Operational Monitoring</div>', unsafe_allow_html=True)

    # ─────────────────────────────────────────────────────────────────────────
    # 1. Operational Metrics Cards
    # ─────────────────────────────────────────────────────────────────────────
    health = etl.get_etl_health()

    # Format last successful run timestamp nicely
    last_success_ts = health.get("last_successful_run", "—")
    if last_success_ts and last_success_ts != "—":
        try:
            dt_s = datetime.fromisoformat(last_success_ts)
            last_success_display = dt_s.strftime("%H:%M:%S")
        except Exception:
            last_success_display = str(last_success_ts)[-8:]
    else:
        last_success_display = "—"

    # Row 1 of metrics: Core Execution Counts & Ingestion
    k1, k2, k3, k4 = st.columns(4)
    with k1:
        st.metric(
            "✅ Successful Runs",
            f"{health['successful_runs']:,}",
            help="Total batch runs completed without unhandled exceptions.",
        )
    with k2:
        st.metric(
            "❌ Failed Runs",
            f"{health['failed_runs']:,}",
            delta=f"{health['failed_runs']} total" if health['failed_runs'] > 0 else "0 (Healthy)",
            delta_color="inverse",
            help="Runs that encountered fatal errors and terminated.",
        )
    with k3:
        st.metric(
            "📥 Rows Ingested",
            f"{health['rows_ingested']:,}",
            delta=f"{health['rows_received']:,} received",
            help="Total telemetry and event records successfully committed to the database.",
        )
    with k4:
        st.metric(
            "⚠️ Rejected Records",
            f"{health['rejected_records']:,}",
            delta=f"{health['rejected_records']} in quarantine" if health['rejected_records'] > 0 else "0 (Clean)",
            delta_color="inverse",
            help="Malformed, out-of-bounds, or corrupt records isolated in data_quarantine.",
        )

    # Row 2 of metrics: Processing Time, Retries, and Last Success
    k5, k6, k7, k8 = st.columns(4)
    with k5:
        st.metric(
            "⏱️ Avg Processing Time",
            f"{health['avg_processing_time_ms']:.1f} ms",
            help="Mean batch processing and database commit latency.",
        )
    with k6:
        st.metric(
            "⚡ Last Run Latency",
            f"{health['last_processing_time_ms']:.1f} ms",
            help="Execution time for the most recent simulation tick.",
        )
    with k7:
        st.metric(
            "🔄 Total Retry Count",
            f"{health['retry_count']:,}",
            help="Total automated transient error retries handled by the @retry decorator.",
        )
    with k8:
        st.metric(
            "🕒 Last Successful Run",
            last_success_display,
            delta=f"Status: {health['last_run_status']}",
            help="Timestamp of the most recently completed successful or partial job execution.",
        )

    # ─────────────────────────────────────────────────────────────────────────
    # 2. Architecture Diagram & System Status
    # ─────────────────────────────────────────────────────────────────────────
    with st.expander("🏗️ Pipeline Architecture (Live System Map)", expanded=True):
        st.markdown("""
        ```mermaid
        flowchart TD
            A["Transit Simulator / Event Source"] --> B["Python Ingestion"]
            B --> C["Raw Data — PostgreSQL"]
            C --> D["Data Quality Validation"]
            D -->|Valid| E["Clean Data"]
            D -->|Invalid| F["Quarantine + Error Log"]
            E --> G["dbt / SQL Transformations"]
            G --> H["Analytics Tables"]
            H --> I["Streamlit Dashboard"]
            J["Airflow Scheduler"] -. "Orchestrates tasks" .-> B
            J -. "Retries and dependencies" .-> D
            J -. "Schedules transformations" .-> G
            B --> K["Pipeline Run Audit"]
            D --> K
            G --> K
            K --> L["Pipeline Health Dashboard"]
        ```
        """)

        # Architecture node status cards
        arch_c1, arch_c2, arch_c3, arch_c4 = st.columns(4)
        with arch_c1:
            st.markdown("""
            **🟢 Active Nodes**
            - **A** — `simulator.py` (Event Source)
            - **B** — `etl.py` (Ingestion)
            - **C** — `database.py` (Raw Data)
            - **D** — `quality.py` (Validation)
            """)
        with arch_c2:
            st.markdown("""
            **📊 Data Nodes**
            - **E** — Clean Data (staging tables)
            - **F** — Quarantine + Error Log
            - **H** — Analytics Tables (marts)
            - **K** — Pipeline Run Audit
            """)
        with arch_c3:
            st.markdown("""
            **⚙️ Transformation Nodes**
            - **G** — SQL Transformations
              - 3 staging models
              - 3 intermediate models
              - 3 mart models
            """)
        with arch_c4:
            engine_info = db.get_engine_info()
            st.markdown(f"""
            **{engine_info['icon']} Database Engine**
            - Engine: **{engine_info['engine']}**
            - Path: `{engine_info['url']}`
            - **I** — Streamlit Dashboard
            - **J** — Airflow Scheduler
            - **L** — This Health Tab
            """)

    # SQL Transformation Model Status
    try:
        from transformations import get_transformation_status
        t_status = get_transformation_status()
        if t_status:
            with st.expander("📐 SQL Transformation Models (Node G → H)", expanded=False):
                ts_cols = st.columns(3)
                for i, layer_name in enumerate(["staging", "intermediate", "marts"]):
                    with ts_cols[i]:
                        layer_icon = {"staging": "📥", "intermediate": "🔄", "marts": "📊"}[layer_name]
                        st.markdown(f"**{layer_icon} {layer_name.title()} Layer**")
                        for m in [s for s in t_status if s["layer"] == layer_name]:
                            status_icon = "✅" if m["exists"] else "⬜"
                            st.markdown(f"  {status_icon} `{m['name']}` — {m['row_count']:,} rows")
    except ImportError:
        pass

    # Educational reference panel
    with st.expander("📚 Learn: Operational Metrics, Audit Tables, Monitoring & Troubleshooting", expanded=False):
        c_learn1, c_learn2, c_learn3, c_learn4 = st.columns(4)
        with c_learn1:
            st.markdown("""
            ### 📊 Operational Metrics
            - **Success Rate SLA**: Ratio of successful runs to total invocations (`success / total`).
            - **Batch Latency**: Execution duration in ms (`duration_s * 1000`).
            - **Throughput**: Rows ingested per second across ticks.
            - **Availability**: System uptime without unrecoverable pipeline halt.
            """)
        with c_learn2:
            st.markdown("""
            ### 📑 Audit Tables
            - **`etl_run_log`**: Structured run ledger capturing job lifecycle (`running` → `success` / `failed`), row tallies, and stack traces.
            - **`data_quarantine`**: Dead-letter storage recording bad payloads, error rules violated, and rejection timestamps.
            - **Compliance & Lineage**: Full traceability for regulatory audit.
            """)
        with c_learn3:
            st.markdown("""
            ### 📈 Monitoring Signals
            - **Heartbeat Tracking**: Alerting if `last_successful_run` is older than 3× tick interval.
            - **Error Spike Detection**: Trigger alerts if error rate exceeds 2% over 5-minute rolling window.
            - **Lock Contention**: Rising retry count indicates SQLite or DB thread concurrency pressure.
            """)
        with c_learn4:
            st.markdown("""
            ### 🔍 Troubleshooting RCA
            1. **Triage**: Check recent runs for `❌ failed` or `⚠️ partial` status.
            2. **Audit Trace**: Inspect `error_traceback` column in `etl_run_log`.
            3. **Dead-Letter Inspect**: View corrupt payload in `data_quarantine`.
            4. **Remediate & Replay**: Fix upstream schema or re-insert valid records.
            """)

    # ─────────────────────────────────────────────────────────────────────────
    # 3. Execution Visualizations: Processing Time & Ingestion Trends
    # ─────────────────────────────────────────────────────────────────────────
    raw_runs = etl.get_run_log(limit=60)
    if raw_runs:
        df_runs_all = pd.DataFrame(raw_runs).sort_values("started_at")
        df_runs_all["duration_ms"] = (df_runs_all["duration_s"] * 1000.0).round(1)

        col_ch1, col_ch2 = st.columns(2)
        with col_ch1:
            fig_lat = px.line(
                df_runs_all,
                x="started_at",
                y="duration_ms",
                title="⚡ Processing Time Trend (ms)",
                markers=True,
                color_discrete_sequence=["#00d2be"],
            )
            # Add average benchmark line
            avg_ms = df_runs_all["duration_ms"].mean()
            fig_lat.add_hline(
                y=avg_ms,
                line_dash="dot",
                line_color="#ffbe0b",
                annotation_text=f"Mean: {avg_ms:.1f}ms",
                annotation_position="top left",
            )
            fig_lat.update_layout(
                height=260,
                paper_bgcolor="#0e1117",
                plot_bgcolor="#0e1117",
                font=dict(color="white"),
                xaxis=dict(title="Execution Time", gridcolor="#2d3247"),
                yaxis=dict(title="Processing Time (ms)", gridcolor="#2d3247"),
            )
            st.plotly_chart(fig_lat, use_container_width=True)

        with col_ch2:
            fig_vol = px.bar(
                df_runs_all,
                x="started_at",
                y=["records_out", "records_rejected"],
                title="📦 Ingestion Volume (Rows Ingested vs Rejected)",
                barmode="stack",
                color_discrete_map={"records_out": "#4361ee", "records_rejected": "#e63946"},
            )
            fig_vol.update_layout(
                height=260,
                paper_bgcolor="#0e1117",
                plot_bgcolor="#0e1117",
                font=dict(color="white"),
                legend=dict(title="", orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                xaxis=dict(title="Execution Time", gridcolor="#2d3247"),
                yaxis=dict(title="Rows", gridcolor="#2d3247"),
            )
            st.plotly_chart(fig_vol, use_container_width=True)

    # ─────────────────────────────────────────────────────────────────────────
    # 4. Audit Table Explorer: etl_run_log & Job History
    # ─────────────────────────────────────────────────────────────────────────
    st.subheader("📑 Audit Table: `etl_run_log` Execution Ledger")

    col_filter_status, col_filter_limit = st.columns([1, 1])
    with col_filter_status:
        selected_status = st.selectbox(
            "Filter by Run Status",
            ["All", "success", "partial", "failed", "running"],
            key="etl_filter_status",
        )
    with col_filter_limit:
        table_limit = st.slider("Max audit rows", 20, 200, 50, 10, key="etl_filter_limit")

    filtered_runs = etl.get_run_log(limit=table_limit)
    if selected_status != "All":
        filtered_runs = [r for r in filtered_runs if r.get("status") == selected_status]

    if not filtered_runs:
        st.info("No run logs found for the selected filter.")
    else:
        df_audit = pd.DataFrame(filtered_runs)
        status_badges = {
            "success": "🟢 success",
            "partial": "🟡 partial",
            "failed":  "🔴 failed",
            "running": "🔵 running",
        }
        df_audit["status_badge"] = df_audit["status"].map(lambda s: status_badges.get(s, s))
        df_audit["latency_ms"] = (df_audit["duration_s"] * 1000.0).round(1)

        display_cols_audit = [
            "run_id", "started_at", "status_badge", "latency_ms",
            "records_in", "records_out", "records_rejected",
            "retry_count", "error_message",
        ]
        display_cols_audit = [c for c in display_cols_audit if c in df_audit.columns]

        st.dataframe(
            df_audit[display_cols_audit].rename(columns={
                "run_id": "Run ID",
                "started_at": "Started At",
                "status_badge": "Status",
                "latency_ms": "Time (ms)",
                "records_in": "Rows In",
                "records_out": "Ingested",
                "records_rejected": "Rejected",
                "retry_count": "Retries",
                "error_message": "Error Trace",
            }),
            hide_index=True,
            use_container_width=True,
            height=280,
        )

        # Detailed Run Inspector
        with st.expander("🔍 Inspect Specific Run Audit Details"):
            run_ids = [r["run_id"] for r in filtered_runs]
            selected_run_id = st.selectbox("Select Run ID to Inspect", run_ids, key="inspect_run_id")
            selected_run_data = next((r for r in filtered_runs if r["run_id"] == selected_run_id), None)
            if selected_run_data:
                col_r1, col_r2 = st.columns(2)
                with col_r1:
                    st.json({
                        "run_id": selected_run_data.get("run_id"),
                        "job_name": selected_run_data.get("job_name"),
                        "status": selected_run_data.get("status"),
                        "started_at": selected_run_data.get("started_at"),
                        "finished_at": selected_run_data.get("finished_at"),
                        "duration_s": selected_run_data.get("duration_s"),
                    })
                with col_r2:
                    st.json({
                        "records_in": selected_run_data.get("records_in"),
                        "records_out": selected_run_data.get("records_out"),
                        "records_rejected": selected_run_data.get("records_rejected"),
                        "retry_count": selected_run_data.get("retry_count"),
                        "error_message": selected_run_data.get("error_message"),
                    })

    # ─────────────────────────────────────────────────────────────────────────
    # 5. Dead-Letter Quarantine & Troubleshooting
    # ─────────────────────────────────────────────────────────────────────────
    st.markdown("---")
    st.subheader("🛡️ Dead-Letter Quarantine: `data_quarantine`")

    quarantine_summary = etl.get_quarantine_summary()
    quarantine_records_list = etl.get_quarantine_records(limit=25)

    if quarantine_summary or quarantine_records_list:
        col_q_sum, col_q_detail = st.columns([1, 2])
        with col_q_sum:
            st.markdown("**Quarantine Breakdown by Entity**")
            st.dataframe(
                pd.DataFrame(quarantine_summary).rename(columns={
                    "record_type": "Entity",
                    "count": "Quarantined Rows",
                    "first_seen": "First Seen",
                    "last_seen": "Last Seen",
                }),
                hide_index=True,
                use_container_width=True,
            )
        with col_q_detail:
            st.markdown("**Recent Quarantined Records (Troubleshooting)**")
            if quarantine_records_list:
                df_q = pd.DataFrame(quarantine_records_list)
                st.dataframe(
                    df_q[["quarantine_id", "record_type", "rejected_at", "errors_json"]].rename(columns={
                        "quarantine_id": "ID",
                        "record_type": "Entity",
                        "rejected_at": "Rejected At",
                        "errors_json": "Validation Errors",
                    }),
                    hide_index=True,
                    use_container_width=True,
                    height=200,
                )
    else:
        st.success("✅ Quarantine is currently empty. 100% of telemetry records passed validation without rejection.")


# ─────────────────────────────────────────────────────────────────────────────
# Auto-refresh footer
# ─────────────────────────────────────────────────────────────────────────────

st.divider()
col_a, col_b, col_c = st.columns([2, 1, 1])
with col_a:
    st.caption(f"Last updated: {datetime.now().strftime('%H:%M:%S')} | "
               f"Sim time: {pipeline.sim.sim_time.strftime('%Y-%m-%d %H:%M')}")
with col_b:
    _eng = db.get_engine_info()
    st.caption(f"{_eng['icon']} DB: `{_eng['engine']}` ({_eng['url']})")
with col_c:
    if st.button("🔄 Refresh Now"):
        st.rerun()

# Auto-refresh
time.sleep(refresh_rate)
st.rerun()
