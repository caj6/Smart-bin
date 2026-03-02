"""
data_handler.py
---------------
Handles all data operations for the Smart Waste Management System.
Designed for easy swap from mock data to live FastAPI REST calls.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random
import json
from typing import Optional

# ─────────────────────────────────────────────
# CONFIG — swap API_BASE_URL when going live
# ─────────────────────────────────────────────
API_BASE_URL = "http://localhost:8000"  # FastAPI backend (future)
USE_MOCK_DATA = True                    # Set False to use live API

BIN_CONFIG = {
    "BIN1": {"device_id": "esp32-gw-01", "floor": "Floor 1", "location": "Lobby - East Wing"},
    "BIN2": {"device_id": "esp32-gw-02", "floor": "Floor 2", "location": "Office - West Wing"},
}

# ─────────────────────────────────────────────
# MOCK DATA GENERATION
# ─────────────────────────────────────────────

def _make_ts_sequence(hours_back: int = 24, interval_minutes: int = 5) -> list:
    now = datetime.utcnow()
    total = int((hours_back * 60) / interval_minutes)
    return [now - timedelta(minutes=i * interval_minutes) for i in range(total, 0, -1)]

def generate_historical_data(hours_back: int = 24) -> pd.DataFrame:
    """Generate realistic simulated sensor history for both bins."""
    records = []
    timestamps = _make_ts_sequence(hours_back)

    for bin_id, meta in BIN_CONFIG.items():
        # Simulate a gradual fill cycle with some noise
        base_fill = random.uniform(20, 40)
        fill_pct = base_fill
        for ts in timestamps:
            fill_pct = min(fill_pct + random.uniform(0, 1.5), 100)
            # Simulate emptying after full
            if fill_pct >= 95:
                fill_pct = random.uniform(5, 15)

            tvoc = max(0, random.gauss(180, 50) + (fill_pct * 0.8))
            eco2 = max(400, random.gauss(600, 80) + (fill_pct * 1.2))
            rssi = random.gauss(-65, 8)
            snr  = random.gauss(7.5, 1.5)

            records.append({
                "device_id":  meta["device_id"],
                "bin_id":     bin_id,
                "floor":      meta["floor"],
                "location":   meta["location"],
                "ts_device":  ts,
                "fill_pct":   round(fill_pct, 1),
                "tvoc_ppb":   round(tvoc, 1),
                "eco2_ppm":   round(eco2, 1),
                "rssi":       round(rssi, 1),
                "snr":        round(snr, 2),
            })

    df = pd.DataFrame(records).sort_values("ts_device").reset_index(drop=True)
    return df

def get_latest_readings() -> pd.DataFrame:
    """Return the most recent reading per bin (live: GET /api/bins/latest)."""
    if USE_MOCK_DATA:
        df = generate_historical_data(hours_back=1)
        return df.groupby("bin_id").last().reset_index()
    else:
        # TODO: replace with httpx call
        # import httpx
        # resp = httpx.get(f"{API_BASE_URL}/api/bins/latest")
        # return pd.DataFrame(resp.json())
        pass

def get_historical_data(bin_id: Optional[str] = None,
                        hours_back: int = 24) -> pd.DataFrame:
    """Return historical sensor data (live: GET /api/bins/history)."""
    if USE_MOCK_DATA:
        df = generate_historical_data(hours_back)
        if bin_id:
            df = df[df["bin_id"] == bin_id]
        return df
    else:
        # TODO: replace with httpx call
        pass

def get_cleaning_log() -> pd.DataFrame:
    """Return simulated cleaning history."""
    now = datetime.utcnow()
    records = []
    for i in range(8):
        bin_id = random.choice(list(BIN_CONFIG.keys()))
        records.append({
            "cleaned_at": now - timedelta(hours=random.randint(2, 96)),
            "bin_id": bin_id,
            "floor": BIN_CONFIG[bin_id]["floor"],
            "cleaned_by": random.choice(["Staff A", "Staff B", "Staff C"]),
            "notes": random.choice(["Routine", "Smell alert resolved", "Full bin emptied", ""]),
        })
    return pd.DataFrame(records).sort_values("cleaned_at", ascending=False).reset_index(drop=True)
