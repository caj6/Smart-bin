"""
alert_logic.py
--------------
Alert detection, state classification, and alert log management.
"""

import pandas as pd
from datetime import datetime
from typing import Literal

# ─────────────────────────────────────────────
# THRESHOLDS
# ─────────────────────────────────────────────
FILL_FULL_PCT      = 90.0   # fill_pct >= this → FULL
FILL_WARNING_PCT   = 70.0   # fill_pct >= this → WARNING
TVOC_SMELL_PPB     = 200    # tvoc_ppb  > this → smell alert
ECO2_SMELL_PPM     = 700    # eco2_ppm  > this → smell alert

StateType = Literal["NORMAL", "WARNING", "FULL", "CRITICAL"]
AlertType = Literal["NONE", "SMELL", "FULL", "CRITICAL"]


# ─────────────────────────────────────────────
# SINGLE-READING CLASSIFICATION
# ─────────────────────────────────────────────

def classify_state(fill_pct: float, tvoc_ppb: float, eco2_ppm: float) -> StateType:
    """Determine bin state from latest sensor values."""
    if fill_pct >= FILL_FULL_PCT:
        if tvoc_ppb > TVOC_SMELL_PPB or eco2_ppm > ECO2_SMELL_PPM:
            return "CRITICAL"
        return "FULL"
    if fill_pct >= FILL_WARNING_PCT or tvoc_ppb > TVOC_SMELL_PPB or eco2_ppm > ECO2_SMELL_PPM:
        return "WARNING"
    return "NORMAL"


def smell_detected(tvoc_ppb: float, eco2_ppm: float) -> bool:
    return tvoc_ppb > TVOC_SMELL_PPB or eco2_ppm > ECO2_SMELL_PPM


def get_alert_type(fill_pct: float, tvoc_ppb: float, eco2_ppm: float) -> AlertType:
    state = classify_state(fill_pct, tvoc_ppb, eco2_ppm)
    if state == "CRITICAL":
        return "CRITICAL"
    if state == "FULL":
        return "FULL"
    if smell_detected(tvoc_ppb, eco2_ppm):
        return "SMELL"
    return "NONE"


# ─────────────────────────────────────────────
# DATAFRAME-LEVEL ENRICHMENT
# ─────────────────────────────────────────────

def enrich_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Add state, alert_type, smell_flag columns to a readings DataFrame."""
    df = df.copy()
    df["state"] = df.apply(
        lambda r: classify_state(r["fill_pct"], r["tvoc_ppb"], r["eco2_ppm"]), axis=1
    )
    df["alert_type"] = df.apply(
        lambda r: get_alert_type(r["fill_pct"], r["tvoc_ppb"], r["eco2_ppm"]), axis=1
    )
    df["smell_flag"] = df.apply(
        lambda r: smell_detected(r["tvoc_ppb"], r["eco2_ppm"]), axis=1
    )
    return df


def build_alert_log(df: pd.DataFrame) -> pd.DataFrame:
    """Extract rows where an alert was triggered (for the Logs page)."""
    enriched = enrich_dataframe(df)
    alerts = enriched[enriched["alert_type"] != "NONE"].copy()
    alerts = alerts.sort_values("ts_device", ascending=False).reset_index(drop=True)
    return alerts


def get_cleaning_priority(latest_df: pd.DataFrame) -> pd.DataFrame:
    """Return bins sorted by urgency: CRITICAL > FULL > SMELL > WARNING."""
    enriched = enrich_dataframe(latest_df)
    order = {"CRITICAL": 0, "FULL": 1, "WARNING": 2, "NORMAL": 3}
    enriched["priority_rank"] = enriched["state"].map(order)
    enriched["needs_attention"] = enriched["state"].isin(["CRITICAL", "FULL", "WARNING"])
    return enriched.sort_values("priority_rank").reset_index(drop=True)


# ─────────────────────────────────────────────
# KPI SUMMARY
# ─────────────────────────────────────────────

def compute_kpis(latest_df: pd.DataFrame) -> dict:
    enriched = enrich_dataframe(latest_df)
    return {
        "total_bins":     len(enriched),
        "full_bins":      int((enriched["state"].isin(["FULL", "CRITICAL"])).sum()),
        "smell_alerts":   int(enriched["smell_flag"].sum()),
        "avg_fill_pct":   round(enriched["fill_pct"].mean(), 1),
        "critical_bins":  int((enriched["state"] == "CRITICAL").sum()),
    }
