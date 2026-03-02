# 🗑️ Smart Waste Management Dashboard

Admin-only monitoring dashboard for ESP32-based smart bin IoT system.

## Quick Start

```bash
pip install -r requirements.txt
streamlit run app.py
```

Open http://localhost:8501

## Project Structure

```
smart_waste_dashboard/
├── app.py            # Main Streamlit app + all 4 pages
├── data_handler.py   # Data fetching (mock/API)
├── alert_logic.py    # State classification & alert rules
├── components.py     # Reusable UI + Plotly charts
├── requirements.txt
└── Dockerfile
```

## Pages

| Page | Description |
|------|-------------|
| 📊 Overview | Live bin cards, KPI row, floor grouping, auto-refresh |
| 📈 Analytics | 5 interactive Plotly charts with time/bin filters |
| 📋 Logs & History | Full sensor log + alert log, CSV export |
| 🧹 Cleaning Panel | Priority queue, mark-cleaned, history |

## Alert Thresholds

| Condition | Threshold |
|-----------|-----------|
| FULL | fill_pct ≥ 90% |
| WARNING | fill_pct ≥ 70% |
| SMELL | TVOC > 200 ppb OR eCO₂ > 700 ppm |
| CRITICAL | FULL + SMELL combined |

## Switching to Live API

In `data_handler.py`, set:
```python
USE_MOCK_DATA = False
API_BASE_URL  = "http://your-fastapi-host:8000"
```
Then implement the `httpx` calls in `get_latest_readings()` and `get_historical_data()`.

## Docker Deployment

```bash
docker build -t smartbin-dashboard .
docker run -p 8501:8501 smartbin-dashboard
```

## Future Roadmap

- [ ] JWT authentication via FastAPI `/auth/token`
- [ ] Live MQTT WebSocket feed
- [ ] Email/SMS alert notifications
- [ ] Multi-floor multi-building support
- [ ] Historical data export to CSV/Excel
