import os
import time

import pandas as pd
import plotly.express as px
import requests
import streamlit as st

API_URL = os.getenv("API_URL", "http://localhost:8000")
REFRESH_SECONDS = int(os.getenv("DASHBOARD_REFRESH_SECONDS", "3"))

st.set_page_config(page_title="Cloud Anomaly Monitor", page_icon="⚡", layout="wide")
st.title("Real-Time Cloud Anomaly Monitor")
st.caption("Live behavioural-window inference, alerting and platform health")


def fetch(path: str) -> list[dict] | dict:
    response = requests.get(f"{API_URL}{path}", timeout=5)
    response.raise_for_status()
    return response.json()


try:
    health = fetch("/health")
    predictions = pd.DataFrame(fetch("/v1/predictions?limit=500"))
    alerts = pd.DataFrame(fetch("/v1/alerts?limit=100"))
except requests.RequestException as exc:
    st.error(f"Monitoring API is unavailable: {exc}")
    st.stop()

status_colour = "🟢" if health.get("status") == "ok" else "🔴"
if predictions.empty:
    st.info("The system is healthy and waiting for completed telemetry windows.")
    st.code("python -m scripts.producer --continuous", language="bash")
else:
    predictions["window_end"] = pd.to_datetime(predictions["window_end"], utc=True)
    latest = predictions["window_end"].max()
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Platform", f"{status_colour} {health['status'].upper()}")
    m2.metric("Recent windows", len(predictions))
    m3.metric("Anomaly alerts", int(predictions["is_anomaly"].sum()))
    m4.metric("Latest prediction", latest.strftime("%H:%M:%S UTC"))

    st.subheader("Live anomaly scores")
    figure = px.line(
        predictions.sort_values("window_end"),
        x="window_end",
        y="anomaly_score",
        color="service",
        markers=True,
    )
    threshold = float(predictions["threshold"].iloc[0])
    figure.add_hline(y=threshold, line_dash="dash", line_color="#ef4444", annotation_text="Alert threshold")
    figure.update_layout(yaxis_range=[0, 1], legend_title_text="Service", height=430)
    st.plotly_chart(figure, use_container_width=True)

    left, right = st.columns((2, 1))
    with left:
        st.subheader("Latest service windows")
        columns = [
            "window_end",
            "service",
            "anomaly_score",
            "threshold",
            "is_anomaly",
            "inference_time_ms",
            "model_version",
        ]
        st.dataframe(
            predictions[columns].sort_values("window_end", ascending=False), hide_index=True, use_container_width=True
        )
    with right:
        st.subheader("Active alerts")
        if alerts.empty:
            st.success("No recent anomaly alerts")
        else:
            alerts["window_end"] = pd.to_datetime(alerts["window_end"], utc=True)
            st.dataframe(alerts[["window_end", "service", "anomaly_score"]], hide_index=True, use_container_width=True)

st.caption(f"Refreshing every {REFRESH_SECONDS} seconds · API: {API_URL}")
time.sleep(REFRESH_SECONDS)
st.rerun()
