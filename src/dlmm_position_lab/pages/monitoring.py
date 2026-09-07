"""Usage, latency, and feedback from the local SQLite database."""

import streamlit as st

from dlmm_position_lab.storage import load_monitoring

st.set_page_config(page_title="Monitoring", layout="wide")
st.title("Monitoring")
requests, feedback = load_monitoring()
latencies = [row["total_latency_ms"] for row in requests if not row["error"]]
positive = sum(row["rating"] == 1 for row in feedback)

first, second, third, fourth = st.columns(4)
first.metric("Questions", len(requests))
second.metric(
    "Average latency",
    f"{sum(latencies) / len(latencies) / 1000:.1f}s" if latencies else "—",
)
third.metric(
    "Positive feedback", f"{positive / len(feedback):.0%}" if feedback else "—"
)
fourth.metric("Errors", sum(bool(row["error"]) for row in requests))

if latencies:
    st.line_chart({"Latency (ms)": latencies})
if requests:
    st.dataframe(requests[-20:], width="stretch")
else:
    st.info("Ask a question to start collecting metrics.")
