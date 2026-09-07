"""Streamlit presentation layer for DLMM Position Lab."""

from time import perf_counter
from uuid import uuid4

import streamlit as st
from elastic_transport import TransportError
from openai import OpenAIError

from dlmm_position_lab.analytics import analyze_range
from dlmm_position_lab.models import ApplicationResponse
from dlmm_position_lab.service import respond_to_question
from dlmm_position_lab.storage import record_error, record_response, save_feedback


def render_response(
    response: ApplicationResponse,
    *,
    question: str = "",
    request_id: int | None = None,
    conversation_id: str = "",
    pool_address: str = "",
) -> None:
    """Render one routed response with its educational trace."""
    if response.answer:
        st.markdown(response.answer.answer)
        with st.expander("Sources"):
            for number, source in enumerate(response.answer.sources, start=1):
                st.markdown(
                    f"[{number}] **{source.title} — {source.section}**  \n"
                    f"{source.url}"
                )
        st.caption(f"Answer latency: {response.answer.latency_ms:.0f} ms")

    if response.pool:
        pool = response.pool
        st.subheader(pool.name)
        first, second, third = st.columns(3)
        first.metric("Current price", f"{pool.current_price:g}")
        second.metric("TVL", f"${pool.tvl:,.2f}")
        third.metric("Dynamic fee", f"{pool.dynamic_fee_pct:g}%")
        st.caption(
            f"{pool.token_x.symbol} / {pool.token_y.symbol} · "
            f"bin step {pool.pool_config.bin_step}"
        )

    if response.notice:
        st.info(response.notice)

    decision = response.routing.decision
    with st.expander("Router decision"):
        st.write(f"Question type: `{decision.question_type}`")
        st.write(f"Use RAG: `{decision.use_rag}`")
        st.write(f"Selected tools: `{', '.join(decision.tools) or 'none'}`")
        st.write(decision.explanation)
        st.caption(f"Router latency: {response.routing.latency_ms:.0f} ms")

    if request_id and (response.answer or response.pool):
        with st.expander("Rate this response"):
            rating = st.radio(
                "Rating",
                ["👍", "👎"],
                index=None,
                horizontal=True,
                key=f"rating_{request_id}",
            )
            comment = st.text_input(
                "Optional comment", key=f"comment_{request_id}"
            )
            if st.button("Save feedback", key=f"save_feedback_{request_id}"):
                if rating:
                    answer_text = response.answer.answer if response.answer else "Pool data"
                    save_feedback(
                        request_id,
                        conversation_id,
                        question,
                        answer_text,
                        1 if rating == "👍" else -1,
                        comment,
                        pool_address,
                    )
                    st.success("Feedback saved")
                else:
                    st.warning("Choose a rating first")


def render_chat(pool_address: str, conversation_id: str) -> None:
    """Render routed documentation chat with session history."""
    st.subheader("Ask about Meteora DLMM")
    st.caption(
        "Answers use indexed official documentation. Pool questions call the "
        "single read-only get_pool tool when an address is provided."
    )

    history = st.session_state.setdefault("chat_history", [])
    for item in history:
        with st.chat_message("user"):
            st.write(item["question"])
        with st.chat_message("assistant"):
            render_response(
                ApplicationResponse.model_validate(item["response"]),
                question=item["question"],
                request_id=item["request_id"],
                conversation_id=conversation_id,
                pool_address=item["pool_address"],
            )

    if question := st.chat_input("What is a bin step?"):
        with st.chat_message("user"):
            st.write(question)
        with st.chat_message("assistant"), st.spinner("Routing and searching..."):
            started = perf_counter()
            try:
                response = respond_to_question(question, pool_address=pool_address)
                total_latency_ms = (perf_counter() - started) * 1_000
                request_id = record_response(
                    conversation_id, response, total_latency_ms
                )
                render_response(
                    response,
                    question=question,
                    request_id=request_id,
                    conversation_id=conversation_id,
                    pool_address=pool_address,
                )
                history.append(
                    {
                        "question": question,
                        "response": response.model_dump(mode="json"),
                        "request_id": request_id,
                        "pool_address": pool_address,
                    }
                )
            except (OpenAIError, TransportError, RuntimeError, ValueError) as error:
                record_error(
                    conversation_id,
                    question,
                    str(error),
                    (perf_counter() - started) * 1_000,
                )
                st.error(f"The request failed: {error}")


def render_range_lab() -> None:
    """Render deterministic analytics over user-supplied closing prices."""
    st.subheader("Hypothetical range lab")
    st.caption("These values are supplied by you; they are not live market data.")

    prices_text = st.text_area(
        "Closing prices, separated by commas",
        value="100, 105, 111, 108, 99",
    )
    lower_price = st.number_input("Lower price", value=100.0)
    upper_price = st.number_input("Upper price", value=110.0)

    if st.button("Analyze range", type="primary"):
        try:
            prices = [float(value.strip()) for value in prices_text.split(",")]
            result = analyze_range(prices, lower_price, upper_price)
        except ValueError as error:
            st.error(str(error))
            return

        st.line_chart(prices, x_label="Observation", y_label="Closing price")
        first, second, third = st.columns(3)
        first.metric("Current price", f"{result.current_price:g}")
        second.metric("Inside range", "Yes" if result.inside_range else "No")
        third.metric("Range width", f"{result.range_width:g}")

        first, second, third = st.columns(3)
        first.metric("Inside observations", f"{result.percentage_inside_range:.1f}%")
        second.metric("Range exits", result.number_of_range_exits)
        third.metric("Observed min / max", f"{result.min_price:g} / {result.max_price:g}")

        st.write(
            f"Distance to lower boundary: **{result.distance_to_lower_boundary:g}**  \n"
            f"Distance to upper boundary: **{result.distance_to_upper_boundary:g}**"
        )


def main() -> None:
    st.set_page_config(
        page_title="DLMM Position Lab",
        page_icon="🧪",
        layout="wide",
    )

    st.title("DLMM Position Lab")
    st.write(
        "An educational workspace for grounded Meteora DLMM documentation "
        "answers and deterministic range analysis."
    )

    with st.sidebar:
        st.header("Project status")
        st.success("Documentation RAG available")
        st.success("Range analytics available")
        st.success("Read-only pool lookup available")
        pool_address = st.text_input(
            "Meteora DLMM pool address",
            help="Used only when the router selects get_pool.",
        )
        st.page_link(
            "pages/monitoring.py",
            label="Open monitoring",
        )

    conversation_id = st.session_state.setdefault(
        "conversation_id", str(uuid4())
    )

    chat_tab, range_tab = st.tabs(["Documentation chat", "Range lab"])
    with chat_tab:
        render_chat(pool_address, conversation_id)
    with range_tab:
        render_range_lab()


if __name__ == "__main__":
    main()
