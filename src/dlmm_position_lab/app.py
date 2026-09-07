"""Streamlit chat, range calculator, and feedback."""

from time import perf_counter

import httpx
import streamlit as st
from elastic_transport import TransportError
from elasticsearch import ApiError
from openai import OpenAIError

from dlmm_position_lab.analytics import analyze_range
from dlmm_position_lab.rag import answer_question
from dlmm_position_lab.storage import record_request, save_feedback


def render_response(item: dict) -> None:
    response = item["response"]
    st.markdown(response["answer"])
    if response["sources"]:
        with st.expander("Sources"):
            for number, source in enumerate(response["sources"], 1):
                st.markdown(
                    f"{number}. [{source['title']} — {source['section']}]({source['url']})"
                )
    if pool := response["pool"]:
        st.caption(f"{pool['name']} · bin step {pool['bin_step']}")
        first, second, third = st.columns(3)
        first.metric("Current price", f"{pool['current_price']:g}")
        second.metric("TVL", f"${pool['tvl']:,.2f}")
        third.metric("Dynamic fee", f"{pool['dynamic_fee_pct']:g}%")
    if response["notice"] and response["notice"] != response["answer"]:
        st.info(response["notice"])
    if response.get("tool_calls"):
        with st.expander("Function call"):
            st.json(response["tool_calls"])
    st.caption(f"{response['latency_ms'] / 1000:.1f} seconds")
    rating = st.feedback("thumbs", key=f"feedback_{item['id']}")
    if rating is not None and rating != item.get("rating"):
        save_feedback(
            item["id"], item["question"], response["answer"], 1 if rating else -1
        )
        item["rating"] = rating
        st.toast("Feedback saved")


def render_chat(pool_address: str) -> None:
    history = st.session_state.setdefault("history", [])
    for item in history:
        with st.chat_message("user"):
            st.write(item["question"])
        with st.chat_message("assistant"):
            render_response(item)
    if question := st.chat_input(
        "Ask about DLMM or paste a pool address with your question"
    ):
        with st.chat_message("user"):
            st.write(question)
        with st.chat_message("assistant"), st.spinner("Finding an answer..."):
            started = perf_counter()
            try:
                response = answer_question(question, pool_address)
            except (
                OpenAIError,
                ApiError,
                TransportError,
                httpx.HTTPError,
                RuntimeError,
                ValueError,
                KeyError,
                TypeError,
            ) as error:
                record_request(
                    question,
                    {"latency_ms": (perf_counter() - started) * 1000},
                    str(error),
                )
                st.error(f"The request failed: {error}")
                return
            item = {
                "id": record_request(question, response),
                "question": question,
                "response": response,
            }
            history.append(item)
            render_response(item)


def render_range_lab() -> None:
    st.caption("Explore a price range using your own observations.")
    with st.form("range"):
        prices_text = st.text_area(
            "Closing prices, separated by commas", "100, 105, 111, 108, 99"
        )
        lower = st.number_input("Lower price", value=100.0)
        upper = st.number_input("Upper price", value=110.0)
        submitted = st.form_submit_button("Analyze range")
    if submitted:
        try:
            prices = [float(value.strip()) for value in prices_text.split(",")]
            result = analyze_range(prices, lower, upper)
        except ValueError as error:
            st.error(str(error))
            return
        st.line_chart(
            {
                "Price": prices,
                "Lower": [lower] * len(prices),
                "Upper": [upper] * len(prices),
            }
        )
        first, second, third = st.columns(3)
        first.metric("Inside observations", f"{result['percentage_inside_range']:.1f}%")
        second.metric("Range exits", result["number_of_range_exits"])
        third.metric("Current price", f"{result['current_price']:g}")
        st.write(
            "Current price is "
            + ("inside" if result["inside_range"] else "outside")
            + " the range."
        )
        st.caption(
            f"Range width: {result['range_width']:g} · "
            f"Observed min / max: {result['min_price']:g} / {result['max_price']:g}"
        )


def main() -> None:
    st.set_page_config(page_title="DLMM Position Lab", layout="wide")
    st.title("DLMM Position Lab")
    st.write("Ask about Meteora DLMM, look up a pool, or explore a price range.")
    with st.sidebar:
        pool_address = st.text_input(
            "Default pool address (optional)",
            help="You can also paste an address in your question. An address in the question takes priority.",
        )
        st.page_link("pages/monitoring.py", label="Monitoring")
    chat, range_lab = st.tabs(["Chat", "Range lab"])
    with chat:
        render_chat(pool_address)
    with range_lab:
        render_range_lab()


if __name__ == "__main__":
    main()
