"""Streamlit monitoring dashboard for application traces and feedback."""

from collections import Counter

import streamlit as st

from dlmm_position_lab.storage import load_feedback, load_requests

st.set_page_config(page_title="DLMM Monitoring", page_icon="📊", layout="wide")
st.title("Application monitoring")

requests = load_requests()
feedback = load_feedback()
successful = [item for item in requests if not item["error"]]
latencies = [float(item["total_latency_ms"]) for item in successful]
positive = sum(int(item["rating"]) > 0 for item in feedback)

first, second, third, fourth = st.columns(4)
first.metric("Total questions", len(requests))
second.metric("Positive feedback", f"{positive / len(feedback):.0%}" if feedback else "—")
third.metric("Average latency", f"{sum(latencies) / len(latencies):.0f} ms" if latencies else "—")
fourth.metric("Errors", sum(bool(item["error"]) for item in requests))

if latencies:
    ordered = sorted(latencies)
    p95 = ordered[min(len(ordered) - 1, int(len(ordered) * 0.95))]
    st.metric("P95 latency", f"{p95:.0f} ms")
    st.line_chart(
        {"request": list(range(1, len(latencies) + 1)), "latency_ms": latencies},
        x="request",
        y="latency_ms",
    )

categories = Counter(str(item["question_type"] or "error") for item in requests)
if categories:
    st.subheader("Questions by category")
    st.bar_chart(
        {"category": list(categories), "count": list(categories.values())},
        x="category",
        y="count",
    )

tool_uses = sum("get_pool" in str(item["tools_called"]) for item in requests)
st.metric("get_pool selections", tool_uses)

if requests:
    st.subheader("Recent requests")
    st.dataframe(requests[-20:], use_container_width=True)
