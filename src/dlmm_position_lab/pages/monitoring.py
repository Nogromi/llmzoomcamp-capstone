"""Usage, latency, and feedback from the local SQLite database."""

from collections import Counter, defaultdict
from datetime import date, timedelta

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

# Include quiet days so gaps in activity are visible in the daily charts.
daily = defaultdict(
    lambda: {"Requests": 0, "Errors": 0, "Input tokens": 0, "Output tokens": 0}
)
for row in requests:
    day = date.fromisoformat(row["created_at"][:10])
    daily[day]["Requests"] += 1
    daily[day]["Errors"] += bool(row["error"])
    daily[day]["Input tokens"] += row["input_tokens"]
    daily[day]["Output tokens"] += row["output_tokens"]

days = []
if daily:
    day, last_day = min(daily), max(daily)
    while day <= last_day:
        days.append(day)
        day += timedelta(days=1)
daily_data = {
    "Date": days,
    **{
        metric: [daily[day][metric] for day in days]
        for metric in ("Requests", "Errors", "Input tokens", "Output tokens")
    },
}

st.caption("Daily totals use UTC. Latency includes successful requests only.")
left, right = st.columns(2)
with left:
    st.subheader("Requests per day")
    st.bar_chart(daily_data, x="Date", y="Requests")
with right:
    st.subheader("Response latency")
    successful = [row for row in requests if not row["error"]]
    st.line_chart(
        {
            "Request ID": [row["id"] for row in successful],
            "Latency (seconds)": [row["total_latency_ms"] / 1000 for row in successful],
        },
        x="Request ID",
        y="Latency (seconds)",
    )

left, right = st.columns(2)
with left:
    st.subheader("User feedback")
    ratings = Counter(row["rating"] for row in feedback)
    st.bar_chart(
        {"Rating": ["Positive", "Negative"], "Responses": [ratings[1], ratings[-1]]},
        x="Rating",
        y="Responses",
    )
    if not feedback:
        st.caption("No feedback yet. Rate an answer in chat to add a rating.")
with right:
    st.subheader("Errors per day")
    st.bar_chart(daily_data, x="Date", y="Errors")

st.subheader("Token usage per day")
st.bar_chart(daily_data, x="Date", y=["Input tokens", "Output tokens"], stack=False)
st.caption("Token totals reflect recorded LLM usage; embedding tokens are not tracked.")

if requests:
    st.subheader("Recent requests")
    st.dataframe(requests[-20:], width="stretch")
else:
    st.info("Ask a question to start collecting metrics.")
