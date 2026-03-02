"""
components.py
-------------
Reusable Streamlit UI components for the Smart Waste dashboard.
"""

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from datetime import datetime

from alert_logic import (
    enrich_dataframe, FILL_FULL_PCT, FILL_WARNING_PCT,
    TVOC_SMELL_PPB, ECO2_SMELL_PPM
)

# ─────────────────────────────────────────────
# THEME CONSTANTS
# ─────────────────────────────────────────────
COLORS = {
    "NORMAL":   "#22c55e",
    "WARNING":  "#f59e0b",
    "FULL":     "#ef4444",
    "CRITICAL": "#dc2626",
    "bg_card":  "#1e293b",
    "bg_dark":  "#0f172a",
    "accent":   "#38bdf8",
    "text":     "#e2e8f0",
    "muted":    "#94a3b8",
    "BIN1":     "#38bdf8",
    "BIN2":     "#a78bfa",
}

STATE_EMOJI = {
    "NORMAL":   "🟢",
    "WARNING":  "🟡",
    "FULL":     "🔴",
    "CRITICAL": "🚨",
}

PLOTLY_TEMPLATE = dict(
    layout=dict(
        paper_bgcolor="#0f172a",
        plot_bgcolor="#1e293b",
        font=dict(color="#e2e8f0", family="'IBM Plex Mono', monospace"),
        xaxis=dict(gridcolor="#334155", linecolor="#475569"),
        yaxis=dict(gridcolor="#334155", linecolor="#475569"),
        legend=dict(bgcolor="#1e293b", bordercolor="#334155"),
        margin=dict(l=40, r=20, t=40, b=40),
    )
)


# ─────────────────────────────────────────────
# CSS INJECTION
# ─────────────────────────────────────────────

def inject_css():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@300;400;500;600&family=Space+Grotesk:wght@300;400;500;600;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Space Grotesk', sans-serif;
        background-color: #0f172a;
        color: #e2e8f0;
    }

    /* Sidebar */
    [data-testid="stSidebar"] {
        background-color: #0f172a;
        border-right: 1px solid #1e293b;
    }
    [data-testid="stSidebar"] * { color: #e2e8f0 !important; }

    /* Main area */
    [data-testid="stAppViewContainer"] { background-color: #0f172a; }
    [data-testid="block-container"] { padding: 1.5rem 2rem; }

    /* Metric cards */
    [data-testid="stMetric"] {
        background: #1e293b;
        border: 1px solid #334155;
        border-radius: 12px;
        padding: 1rem 1.2rem;
    }
    [data-testid="stMetricLabel"] { color: #94a3b8 !important; font-size: 0.75rem; letter-spacing: 0.08em; text-transform: uppercase; }
    [data-testid="stMetricValue"] { color: #e2e8f0 !important; font-family: 'IBM Plex Mono', monospace; font-size: 1.8rem; }

    /* Bin cards */
    .bin-card {
        background: #1e293b;
        border: 1px solid #334155;
        border-radius: 16px;
        padding: 1.5rem;
        margin-bottom: 1rem;
        transition: border-color 0.3s ease;
    }
    .bin-card:hover { border-color: #38bdf8; }
    .bin-card-critical { border-left: 4px solid #dc2626; }
    .bin-card-full     { border-left: 4px solid #ef4444; }
    .bin-card-warning  { border-left: 4px solid #f59e0b; }
    .bin-card-normal   { border-left: 4px solid #22c55e; }

    .bin-title {
        font-size: 1.1rem;
        font-weight: 600;
        color: #f8fafc;
        font-family: 'IBM Plex Mono', monospace;
    }
    .bin-location {
        font-size: 0.75rem;
        color: #94a3b8;
        letter-spacing: 0.05em;
        margin-bottom: 1rem;
    }
    .stat-row { display: flex; gap: 1rem; flex-wrap: wrap; margin-top: 0.75rem; }
    .stat-box {
        background: #0f172a;
        border: 1px solid #1e293b;
        border-radius: 8px;
        padding: 0.4rem 0.75rem;
        font-family: 'IBM Plex Mono', monospace;
        font-size: 0.8rem;
        color: #e2e8f0;
        flex: 1;
        min-width: 90px;
        text-align: center;
    }
    .stat-label { color: #94a3b8; font-size: 0.65rem; display: block; text-transform: uppercase; letter-spacing: 0.06em; }
    .stat-value { font-size: 1rem; font-weight: 500; }

    /* Status badge */
    .status-badge {
        display: inline-block;
        padding: 0.2rem 0.75rem;
        border-radius: 999px;
        font-size: 0.7rem;
        font-weight: 600;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        font-family: 'IBM Plex Mono', monospace;
    }
    .badge-NORMAL   { background: #14532d; color: #22c55e; border: 1px solid #22c55e33; }
    .badge-WARNING  { background: #451a03; color: #f59e0b; border: 1px solid #f59e0b33; }
    .badge-FULL     { background: #450a0a; color: #ef4444; border: 1px solid #ef444433; }
    .badge-CRITICAL { background: #3b0000; color: #dc2626; border: 1px solid #dc262633; animation: pulse-red 1.5s infinite; }

    @keyframes pulse-red {
        0%, 100% { box-shadow: 0 0 0 0 rgba(220,38,38,0.4); }
        50%       { box-shadow: 0 0 0 6px rgba(220,38,38,0); }
    }

    /* Alert banner */
    .alert-banner {
        background: #450a0a;
        border: 1px solid #dc2626;
        border-radius: 10px;
        padding: 0.6rem 1rem;
        font-family: 'IBM Plex Mono', monospace;
        font-size: 0.8rem;
        color: #fca5a5;
        margin: 0.5rem 0;
    }
    .smell-banner {
        background: #422006;
        border: 1px solid #f59e0b;
        border-radius: 10px;
        padding: 0.6rem 1rem;
        font-family: 'IBM Plex Mono', monospace;
        font-size: 0.8rem;
        color: #fcd34d;
        margin: 0.5rem 0;
    }

    /* Progress bar override */
    [data-testid="stProgress"] > div { background-color: #1e293b; border-radius: 999px; }
    [data-testid="stProgress"] > div > div { border-radius: 999px; }

    /* Page header */
    .page-header {
        font-size: 1.8rem;
        font-weight: 700;
        color: #f8fafc;
        font-family: 'IBM Plex Mono', monospace;
        letter-spacing: -0.02em;
        margin-bottom: 0.25rem;
    }
    .page-sub {
        font-size: 0.8rem;
        color: #94a3b8;
        letter-spacing: 0.06em;
        text-transform: uppercase;
        margin-bottom: 1.5rem;
    }

    /* Divider */
    hr { border-color: #1e293b; }

    /* Floor header */
    .floor-header {
        font-family: 'IBM Plex Mono', monospace;
        font-size: 0.7rem;
        color: #38bdf8;
        text-transform: uppercase;
        letter-spacing: 0.15em;
        padding: 0.25rem 0;
        border-bottom: 1px solid #1e293b;
        margin-bottom: 0.75rem;
    }

    /* Dataframe override */
    [data-testid="stDataFrame"] { background: #1e293b; border-radius: 10px; }

    /* Tabs */
    [data-testid="stTabs"] [data-baseweb="tab"] {
        font-family: 'IBM Plex Mono', monospace;
        font-size: 0.8rem;
        letter-spacing: 0.05em;
        color: #94a3b8;
    }
    [data-testid="stTabs"] [aria-selected="true"] { color: #38bdf8 !important; }

    /* Refresh badge */
    .refresh-badge {
        font-family: 'IBM Plex Mono', monospace;
        font-size: 0.7rem;
        color: #22c55e;
        background: #14532d33;
        border: 1px solid #22c55e33;
        border-radius: 999px;
        padding: 0.2rem 0.6rem;
        display: inline-block;
    }

    /* Scrollbar */
    ::-webkit-scrollbar { width: 4px; }
    ::-webkit-scrollbar-thumb { background: #334155; border-radius: 4px; }

    /* Hide streamlit branding */
    #MainMenu, footer, header { visibility: hidden; }
    </style>
    """, unsafe_allow_html=True)


# ─────────────────────────────────────────────
# BIN CARD
# ─────────────────────────────────────────────

def render_bin_card(row: pd.Series):
    """Render a single bin status card."""
    from alert_logic import classify_state, smell_detected
    state = classify_state(row["fill_pct"], row["tvoc_ppb"], row["eco2_ppm"])
    smell = smell_detected(row["tvoc_ppb"], row["eco2_ppm"])

    card_class = f"bin-card bin-card-{state.lower()}"
    badge_class = f"status-badge badge-{state}"
    emoji = STATE_EMOJI.get(state, "⚪")

    ts = row["ts_device"]
    if hasattr(ts, "strftime"):
        ts_str = ts.strftime("%H:%M:%S UTC")
    else:
        ts_str = str(ts)[:19]

    # Build the HTML card
    st.markdown(f"""
    <div class="{card_class}">
        <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:0.25rem;">
            <div>
                <div class="bin-title">{emoji} {row['bin_id']}</div>
                <div class="bin-location">📍 {row.get('location','—')} · {row['device_id']}</div>
            </div>
            <span class="{badge_class}">{state}</span>
        </div>
    """, unsafe_allow_html=True)

    # Fill bar
    fill = row["fill_pct"]
    bar_color = COLORS[state]
    st.markdown(f"""
        <div style="margin: 0.6rem 0 0.3rem;">
            <div style="display:flex;justify-content:space-between;font-size:0.75rem;color:#94a3b8;font-family:'IBM Plex Mono',monospace;margin-bottom:4px;">
                <span>FILL LEVEL</span><span style="color:{bar_color};font-weight:600;">{fill:.1f}%</span>
            </div>
            <div style="background:#0f172a;border-radius:999px;height:10px;overflow:hidden;border:1px solid #334155;">
                <div style="width:{min(fill,100):.1f}%;background:{bar_color};height:100%;border-radius:999px;
                    transition:width 0.8s ease;box-shadow:0 0 8px {bar_color}55;"></div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    # Stat row
    rssi_color = "#22c55e" if row["rssi"] > -70 else ("#f59e0b" if row["rssi"] > -80 else "#ef4444")
    st.markdown(f"""
        <div class="stat-row">
            <div class="stat-box"><span class="stat-label">TVOC</span><span class="stat-value">{row['tvoc_ppb']:.0f} ppb</span></div>
            <div class="stat-box"><span class="stat-label">eCO₂</span><span class="stat-value">{row['eco2_ppm']:.0f} ppm</span></div>
            <div class="stat-box"><span class="stat-label">RSSI</span><span class="stat-value" style="color:{rssi_color};">{row['rssi']:.0f} dBm</span></div>
            <div class="stat-box"><span class="stat-label">SNR</span><span class="stat-value">{row.get('snr', 0):.1f} dB</span></div>
        </div>
        <div style="font-family:'IBM Plex Mono',monospace;font-size:0.65rem;color:#64748b;margin-top:0.75rem;">
            🕐 LAST UPDATE: {ts_str}
        </div>
    """, unsafe_allow_html=True)

    # Alert banners
    if state in ("FULL", "CRITICAL"):
        st.markdown(f'<div class="alert-banner">🗑️ BIN FULL — Immediate cleaning required</div>', unsafe_allow_html=True)
    if smell:
        st.markdown(f'<div class="smell-banner">👃 SMELL ALERT — TVOC: {row["tvoc_ppb"]:.0f} ppb · eCO₂: {row["eco2_ppm"]:.0f} ppm</div>', unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# KPI ROW
# ─────────────────────────────────────────────

def render_kpis(kpis: dict):
    cols = st.columns(5)
    items = [
        ("🗑️ Total Bins",       kpis["total_bins"],    None),
        ("📊 Avg Fill %",       f"{kpis['avg_fill_pct']}%", None),
        ("🔴 Full Bins",        kpis["full_bins"],     "inverse" if kpis["full_bins"] > 0 else "normal"),
        ("🚨 Critical",         kpis["critical_bins"], "inverse" if kpis["critical_bins"] > 0 else "normal"),
        ("👃 Smell Alerts",     kpis["smell_alerts"],  "inverse" if kpis["smell_alerts"] > 0 else "normal"),
    ]
    for col, (label, val, delta_color) in zip(cols, items):
        with col:
            st.metric(label, val)


# ─────────────────────────────────────────────
# CHARTS
# ─────────────────────────────────────────────

def chart_fill_over_time(df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    for bin_id, grp in df.groupby("bin_id"):
        fig.add_trace(go.Scatter(
            x=grp["ts_device"], y=grp["fill_pct"],
            name=bin_id, mode="lines",
            line=dict(color=COLORS.get(bin_id, "#38bdf8"), width=2),
            hovertemplate=f"<b>{bin_id}</b><br>%{{x}}<br>Fill: %{{y:.1f}}%<extra></extra>",
        ))
    fig.add_hline(y=FILL_FULL_PCT, line_dash="dot", line_color="#ef4444",
                  annotation_text="FULL threshold", annotation_font_color="#ef4444")
    fig.add_hline(y=FILL_WARNING_PCT, line_dash="dot", line_color="#f59e0b",
                  annotation_text="WARNING", annotation_font_color="#f59e0b")
    fig.update_layout(**PLOTLY_TEMPLATE["layout"],
                      title="Fill Level Over Time", yaxis_title="Fill %",
                      yaxis_range=[0, 105], height=320)
    return fig


def chart_air_quality(df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    for bin_id, grp in df.groupby("bin_id"):
        color = COLORS.get(bin_id, "#38bdf8")
        fig.add_trace(go.Scatter(
            x=grp["ts_device"], y=grp["tvoc_ppb"],
            name=f"{bin_id} TVOC", mode="lines",
            line=dict(color=color, width=1.5, dash="solid"),
            hovertemplate=f"{bin_id} TVOC: %{{y:.0f}} ppb<extra></extra>",
        ))
        fig.add_trace(go.Scatter(
            x=grp["ts_device"], y=grp["eco2_ppm"],
            name=f"{bin_id} eCO₂", mode="lines",
            line=dict(color=color, width=1.5, dash="dash"),
            hovertemplate=f"{bin_id} eCO₂: %{{y:.0f}} ppm<extra></extra>",
        ))
    fig.add_hline(y=TVOC_SMELL_PPB, line_dash="dot", line_color="#f97316",
                  annotation_text="TVOC alert", annotation_font_color="#f97316")
    fig.add_hline(y=ECO2_SMELL_PPM, line_dash="dot", line_color="#a78bfa",
                  annotation_text="eCO₂ alert", annotation_font_color="#a78bfa")
    fig.update_layout(**PLOTLY_TEMPLATE["layout"],
                      title="Air Quality (TVOC & eCO₂)", height=320)
    return fig


def chart_bin_comparison(latest_df: pd.DataFrame) -> go.Figure:
    metrics = ["fill_pct", "tvoc_ppb", "eco2_ppm"]
    labels  = ["Fill %", "TVOC (ppb)", "eCO₂ (ppm)"]
    fig = go.Figure()
    for i, (m, label) in enumerate(zip(metrics, labels)):
        fig.add_trace(go.Bar(
            x=latest_df["bin_id"], y=latest_df[m],
            name=label,
            marker_color=[COLORS["BIN1"], COLORS["BIN2"]],
            hovertemplate=f"{label}: %{{y:.1f}}<extra></extra>",
        ))
    fig.update_layout(**PLOTLY_TEMPLATE["layout"],
                      title="Bin Comparison (Latest)", barmode="group", height=320)
    return fig


def chart_status_distribution(df: pd.DataFrame) -> go.Figure:
    enriched = enrich_dataframe(df)
    counts = enriched["state"].value_counts().reset_index()
    counts.columns = ["state", "count"]
    color_map = {s: COLORS[s] for s in COLORS if s in counts["state"].values}
    fig = go.Figure(go.Pie(
        labels=counts["state"], values=counts["count"],
        marker_colors=[COLORS.get(s, "#888") for s in counts["state"]],
        hole=0.5,
        hovertemplate="%{label}: %{value} readings (%{percent})<extra></extra>",
    ))
    fig.update_layout(**PLOTLY_TEMPLATE["layout"],
                      title="State Distribution", height=320)
    return fig


def _hex_to_rgba(hex_color: str, alpha: float = 0.13) -> str:
    """Convert #rrggbb to rgba(r,g,b,alpha) for Plotly compatibility."""
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"


def chart_rssi_trend(df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    for bin_id, grp in df.groupby("bin_id"):
        color = COLORS.get(bin_id, "#38bdf8")
        fig.add_trace(go.Scatter(
            x=grp["ts_device"], y=grp["rssi"],
            name=bin_id, mode="lines", fill="tozeroy",
            fillcolor=_hex_to_rgba(color, 0.13),
            line=dict(color=color, width=1.5),
            hovertemplate=f"{bin_id} RSSI: %{{y:.0f}} dBm<extra></extra>",
        ))
    fig.add_hline(y=-80, line_dash="dot", line_color="#ef4444",
                  annotation_text="Weak signal", annotation_font_color="#ef4444")
    fig.update_layout(**PLOTLY_TEMPLATE["layout"],
                      title="RSSI Signal Strength", yaxis_title="dBm", height=320)
    return fig
