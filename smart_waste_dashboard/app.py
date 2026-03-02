"""
app.py
------
Smart Waste Management System — Admin Dashboard
Run: streamlit run app.py
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import time

# ── Local modules ──────────────────────────────
from auth import render_login_page, is_session_valid, logout
from data_handler import (
    get_latest_readings, get_historical_data,
    get_cleaning_log, BIN_CONFIG
)
from alert_logic import (
    enrich_dataframe, build_alert_log,
    get_cleaning_priority, compute_kpis
)
from components import (
    inject_css, render_bin_card, render_kpis,
    chart_fill_over_time, chart_air_quality,
    chart_bin_comparison, chart_status_distribution,
    chart_rssi_trend, COLORS
)

# ─────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="SmartBin Admin",
    page_icon="🗑️",
    layout="wide",
    initial_sidebar_state="expanded",
)
inject_css()

# ─────────────────────────────────────────────
# AUTH GATE — show login if not authenticated
# ─────────────────────────────────────────────
if not is_session_valid():
    render_login_page()
    st.stop()   # nothing below runs until logged in

# ─────────────────────────────────────────────
# SESSION STATE — stores cleaned bins, refresh
# ─────────────────────────────────────────────
if "cleaned_bins" not in st.session_state:
    st.session_state.cleaned_bins = []         # list of {bin_id, cleaned_at, note}
if "last_refresh" not in st.session_state:
    st.session_state.last_refresh = datetime.utcnow()
if "auto_refresh" not in st.session_state:
    st.session_state.auto_refresh = True

# ─────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style="text-align:center;padding:1rem 0 0.5rem;">
        <div style="font-size:2.5rem">🗑️</div>
        <div style="font-family:'IBM Plex Mono',monospace;font-size:0.85rem;
             color:#38bdf8;font-weight:600;letter-spacing:0.1em;">SMARTBIN</div>
        <div style="font-size:0.65rem;color:#64748b;letter-spacing:0.15em;">ADMIN DASHBOARD</div>
    </div>
    <hr style="border-color:#1e293b;margin:0.5rem 0;">
    """, unsafe_allow_html=True)

    page = st.radio(
        "Navigation",
        ["📊 Overview", "📈 Analytics", "📋 Logs & History", "🧹 Cleaning Panel"],
        label_visibility="collapsed"
    )

    st.markdown("<hr style='border-color:#1e293b;'>", unsafe_allow_html=True)

    auto = st.toggle("⚡ Auto-Refresh (5s)", value=st.session_state.auto_refresh)
    st.session_state.auto_refresh = auto

    if st.button("🔄 Refresh Now", use_container_width=True):
        st.session_state.last_refresh = datetime.utcnow()
        st.rerun()

    st.markdown("<hr style='border-color:#1e293b;'>", unsafe_allow_html=True)
    st.markdown(f"""
    <div style="font-family:'IBM Plex Mono',monospace;font-size:0.65rem;color:#475569;">
        <div>🕐 LAST REFRESH</div>
        <div style="color:#94a3b8;">{st.session_state.last_refresh.strftime('%H:%M:%S UTC')}</div>
        <div style="margin-top:0.5rem;">📡 BINS ONLINE: {len(BIN_CONFIG)}</div>
        <div style="color:#22c55e;">● SYSTEM NOMINAL</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<hr style='border-color:#1e293b;'>", unsafe_allow_html=True)

    # ── Logged-in user info ──
    avatar = st.session_state.get("avatar", "👤")
    display_name = st.session_state.get("display_name", "Admin")
    role = st.session_state.get("role", "")
    login_time = st.session_state.get("login_time")
    login_str = login_time.strftime("%H:%M UTC") if login_time else "—"
    st.markdown(f"""
    <div style="background:#0f172a;border:1px solid #1e293b;border-radius:10px;padding:0.75rem;margin-bottom:0.75rem;">
        <div style="font-size:1.5rem;text-align:center;">{avatar}</div>
        <div style="font-family:'IBM Plex Mono',monospace;font-size:0.75rem;color:#e2e8f0;text-align:center;font-weight:600;">{display_name}</div>
        <div style="font-family:'IBM Plex Mono',monospace;font-size:0.62rem;color:#38bdf8;text-align:center;letter-spacing:0.08em;">{role}</div>
        <div style="font-family:'IBM Plex Mono',monospace;font-size:0.6rem;color:#475569;text-align:center;margin-top:0.3rem;">SESSION SINCE {login_str}</div>
    </div>
    """, unsafe_allow_html=True)

    if st.button("🚪 Sign Out", use_container_width=True):
        logout()
        st.rerun()

    st.markdown("<hr style='border-color:#1e293b;'>", unsafe_allow_html=True)
    st.markdown("""
    <div style="font-family:'IBM Plex Mono',monospace;font-size:0.6rem;color:#334155;text-align:center;">
        v1.0.0-PROTOTYPE · MOCK DATA<br>
        <span style="color:#475569;">FastAPI integration ready</span>
    </div>
    """, unsafe_allow_html=True)


# ─────────────────────────────────────────────
# DATA LOAD (cached per 5s window)
# ─────────────────────────────────────────────
@st.cache_data(ttl=5)
def load_data():
    latest  = get_latest_readings()
    history = get_historical_data()
    latest  = enrich_dataframe(latest)
    history = enrich_dataframe(history)
    return latest, history

latest_df, history_df = load_data()
kpis = compute_kpis(latest_df)

# Auto-refresh trigger
if st.session_state.auto_refresh:
    time.sleep(0.1)          # tiny delay to let page render
    st.session_state.last_refresh = datetime.utcnow()

# ═════════════════════════════════════════════
# PAGE 1 — OVERVIEW
# ═════════════════════════════════════════════
if page == "📊 Overview":
    # Header
    now_str = datetime.utcnow().strftime("%A, %d %b %Y · %H:%M UTC")
    col_h1, col_h2 = st.columns([3, 1])
    with col_h1:
        st.markdown('<div class="page-header">Smart Waste Monitoring System</div>', unsafe_allow_html=True)
        st.markdown('<div class="page-sub">Real-time bin status · Admin view</div>', unsafe_allow_html=True)
    with col_h2:
        st.markdown(f"""
        <div style="text-align:right;padding-top:0.5rem;">
            <span class="refresh-badge">● LIVE</span>
            <div style="font-family:'IBM Plex Mono',monospace;font-size:0.65rem;color:#64748b;margin-top:0.25rem;">{now_str}</div>
        </div>
        """, unsafe_allow_html=True)

    # KPIs
    render_kpis(kpis)
    st.markdown("<br>", unsafe_allow_html=True)

    # Group bins by floor
    floors = {}
    for _, row in latest_df.iterrows():
        floor = row.get("floor", "Unknown")
        floors.setdefault(floor, []).append(row)

    for floor_name in sorted(floors.keys()):
        st.markdown(f'<div class="floor-header">📍 {floor_name}</div>', unsafe_allow_html=True)
        bins_on_floor = floors[floor_name]
        cols = st.columns(min(len(bins_on_floor), 2))
        for col, row in zip(cols, bins_on_floor):
            with col:
                render_bin_card(row)
        st.markdown("<br>", unsafe_allow_html=True)

    # Auto-refresh
    if st.session_state.auto_refresh:
        time.sleep(5)
        st.rerun()


# ═════════════════════════════════════════════
# PAGE 2 — ANALYTICS
# ═════════════════════════════════════════════
elif page == "📈 Analytics":
    st.markdown('<div class="page-header">Analytics</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-sub">Sensor trends & bin performance</div>', unsafe_allow_html=True)

    # Date range filter
    col_f1, col_f2, col_f3 = st.columns([2, 2, 1])
    with col_f1:
        date_range = st.selectbox("Time Range", ["Last 6 hours", "Last 12 hours", "Last 24 hours"], index=2)
    with col_f2:
        bin_filter = st.multiselect("Filter Bins", list(BIN_CONFIG.keys()),
                                     default=list(BIN_CONFIG.keys()))
    with col_f3:
        st.markdown("<br>", unsafe_allow_html=True)

    hours_map = {"Last 6 hours": 6, "Last 12 hours": 12, "Last 24 hours": 24}
    hours = hours_map[date_range]
    cutoff = datetime.utcnow() - timedelta(hours=hours)

    df_filtered = history_df[
        (history_df["ts_device"] >= cutoff) &
        (history_df["bin_id"].isin(bin_filter))
    ]

    if df_filtered.empty:
        st.warning("No data for selected filters.")
    else:
        # Row 1
        c1, c2 = st.columns(2)
        with c1:
            st.plotly_chart(chart_fill_over_time(df_filtered), use_container_width=True)
        with c2:
            st.plotly_chart(chart_air_quality(df_filtered), use_container_width=True)

        # Row 2
        c3, c4 = st.columns(2)
        with c3:
            st.plotly_chart(chart_bin_comparison(latest_df[latest_df["bin_id"].isin(bin_filter)]),
                            use_container_width=True)
        with c4:
            st.plotly_chart(chart_status_distribution(df_filtered), use_container_width=True)

        # Row 3
        st.plotly_chart(chart_rssi_trend(df_filtered), use_container_width=True)


# ═════════════════════════════════════════════
# PAGE 3 — LOGS & HISTORY
# ═════════════════════════════════════════════
elif page == "📋 Logs & History":
    st.markdown('<div class="page-header">Logs & History</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-sub">Sensor readings · Alert log</div>', unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["📄 All Readings", "🚨 Alerts Only"])

    with tab1:
        # Filters
        c1, c2, c3 = st.columns([1, 2, 2])
        with c1:
            bin_sel = st.selectbox("Bin", ["All"] + list(BIN_CONFIG.keys()), key="log_bin")
        with c2:
            date_from = st.date_input("From", value=(datetime.utcnow() - timedelta(hours=24)).date(), key="log_from")
        with c3:
            date_to = st.date_input("To", value=datetime.utcnow().date(), key="log_to")

        search = st.text_input("🔍 Search (state, bin, alert type...)", placeholder="e.g. FULL, SMELL, BIN1")

        df_view = history_df.copy()
        if bin_sel != "All":
            df_view = df_view[df_view["bin_id"] == bin_sel]
        df_view = df_view[
            (df_view["ts_device"].dt.date >= date_from) &
            (df_view["ts_device"].dt.date <= date_to)
        ]
        if search:
            mask = df_view.apply(lambda row: search.upper() in str(row.values).upper(), axis=1)
            df_view = df_view[mask]

        df_view = df_view.sort_values("ts_device", ascending=False)

        display_cols = ["ts_device", "bin_id", "floor", "fill_pct", "tvoc_ppb", "eco2_ppm", "rssi", "state", "alert_type"]
        st.markdown(f"<div style='font-family:IBM Plex Mono;font-size:0.7rem;color:#64748b;margin-bottom:0.5rem;'>{len(df_view)} records</div>", unsafe_allow_html=True)
        st.dataframe(
            df_view[display_cols].rename(columns={
                "ts_device": "Timestamp", "bin_id": "Bin", "floor": "Floor",
                "fill_pct": "Fill %", "tvoc_ppb": "TVOC (ppb)", "eco2_ppm": "eCO₂ (ppm)",
                "rssi": "RSSI (dBm)", "state": "State", "alert_type": "Alert"
            }),
            use_container_width=True,
            height=450,
        )

        # CSV export
        csv = df_view[display_cols].to_csv(index=False)
        st.download_button("⬇️ Export CSV", csv, "smartbin_logs.csv", "text/csv")

    with tab2:
        alert_log = build_alert_log(history_df)
        if alert_log.empty:
            st.info("No alerts in the current dataset.")
        else:
            # Summary
            a_col1, a_col2, a_col3 = st.columns(3)
            a_col1.metric("Total Alerts", len(alert_log))
            a_col2.metric("FULL Alerts", int((alert_log["alert_type"] == "FULL").sum()))
            a_col3.metric("SMELL Alerts", int((alert_log["alert_type"] == "SMELL").sum()))

            disp = ["ts_device", "bin_id", "fill_pct", "tvoc_ppb", "eco2_ppm", "state", "alert_type"]
            st.dataframe(
                alert_log[disp].rename(columns={
                    "ts_device": "Timestamp", "bin_id": "Bin",
                    "fill_pct": "Fill %", "tvoc_ppb": "TVOC", "eco2_ppm": "eCO₂",
                    "state": "State", "alert_type": "Alert Type"
                }),
                use_container_width=True,
                height=400,
            )


# ═════════════════════════════════════════════
# PAGE 4 — CLEANING PANEL
# ═════════════════════════════════════════════
elif page == "🧹 Cleaning Panel":
    st.markdown('<div class="page-header">Cleaning Management</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-sub">Priority queue · Mark cleaned · History</div>', unsafe_allow_html=True)

    priority_df = get_cleaning_priority(latest_df)

    tab_q, tab_h = st.tabs(["🔴 Priority Queue", "📜 Cleaning History"])

    with tab_q:
        if priority_df[priority_df["needs_attention"]].empty:
            st.success("✅ All bins are clean and within normal parameters.")
        else:
            st.markdown("""
            <div style="font-family:'IBM Plex Mono',monospace;font-size:0.75rem;
                 color:#f59e0b;margin-bottom:1rem;">
            ⚠️ Bins listed below require immediate or scheduled attention, sorted by urgency.
            </div>""", unsafe_allow_html=True)

        for _, row in priority_df.iterrows():
            state = row["state"]
            color = COLORS[state]
            with st.container():
                st.markdown(f"""
                <div class="bin-card bin-card-{state.lower()}">
                    <div style="display:flex;justify-content:space-between;align-items:center;">
                        <div>
                            <div class="bin-title">{row['bin_id']} — {row.get('floor','?')}</div>
                            <div class="bin-location">📍 {row.get('location','—')}</div>
                        </div>
                        <span class="status-badge badge-{state}">{state}</span>
                    </div>
                    <div class="stat-row" style="margin-top:0.5rem;">
                        <div class="stat-box"><span class="stat-label">Fill</span>
                            <span class="stat-value" style="color:{color}">{row['fill_pct']:.1f}%</span></div>
                        <div class="stat-box"><span class="stat-label">TVOC</span>
                            <span class="stat-value">{row['tvoc_ppb']:.0f} ppb</span></div>
                        <div class="stat-box"><span class="stat-label">eCO₂</span>
                            <span class="stat-value">{row['eco2_ppm']:.0f} ppm</span></div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                # Mark as cleaned button
                btn_col, note_col = st.columns([1, 3])
                with btn_col:
                    if st.button(f"✅ Mark {row['bin_id']} Cleaned", key=f"clean_{row['bin_id']}"):
                        st.session_state.cleaned_bins.append({
                            "bin_id": row["bin_id"],
                            "floor":  row.get("floor", ""),
                            "cleaned_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
                            "state_before": state,
                        })
                        st.success(f"✅ {row['bin_id']} marked as cleaned!")
                        st.rerun()

    with tab_h:
        st.markdown("#### Session Cleaning Log")
        if st.session_state.cleaned_bins:
            session_df = pd.DataFrame(st.session_state.cleaned_bins)
            st.dataframe(session_df, use_container_width=True)
        else:
            st.markdown('<div style="color:#64748b;font-family:IBM Plex Mono;font-size:0.8rem;">No bins marked as cleaned this session.</div>', unsafe_allow_html=True)

        st.markdown("#### Historical Cleaning Records")
        cleaning_hist = get_cleaning_log()
        st.dataframe(
            cleaning_hist.rename(columns={
                "cleaned_at": "Cleaned At", "bin_id": "Bin",
                "floor": "Floor", "cleaned_by": "Staff",
                "notes": "Notes"
            }),
            use_container_width=True,
            height=300,
        )
