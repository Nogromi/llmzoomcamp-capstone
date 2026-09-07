"""Bounded LLM router for documentation and pool-data questions."""

from __future__ import annotations

from collections.abc import Callable
from time import perf_counter
from typing import Any

from dlmm_position_lab.embeddings import create_openai_client
from dlmm_position_lab.models import RouterDecision, RoutingResult
from dlmm_position_lab.prompts import ROUTER_SYSTEM_PROMPT
from dlmm_position_lab.rag import chat_model


def route_question(
    question: str,
    *,
    client: Any | None = None,
    model: str | None = None,
    clock: Callable[[], float] = perf_counter,
) -> RoutingResult:
    """Classify one question using a schema-validated model response."""
    normalized_question = question.strip()
    if not normalized_question:
        raise ValueError("question must not be empty")

    started = clock()
    openai_client = client or create_openai_client()
    response = openai_client.responses.parse(
        model=model or chat_model(),
        instructions=ROUTER_SYSTEM_PROMPT,
        input=normalized_question,
        text_format=RouterDecision,
        max_output_tokens=1_200,
    )
    if response.output_parsed is None:
        raise RuntimeError("OpenAI returned no router decision")

    usage = getattr(response, "usage", None)
    return RoutingResult(
        question=normalized_question,
        decision=response.output_parsed,
        latency_ms=(clock() - started) * 1_000,
        input_tokens=getattr(usage, "input_tokens", 0),
        output_tokens=getattr(usage, "output_tokens", 0),
    )
