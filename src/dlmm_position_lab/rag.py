"""Grounded documentation RAG built from retrieval, prompts, and OpenAI."""

from __future__ import annotations

import os
from collections.abc import Callable
from time import perf_counter
from typing import Any

from dlmm_position_lab.embeddings import create_openai_client
from dlmm_position_lab.hybrid_search import hybrid_search
from dlmm_position_lab.models import Answer, AnswerSource, SearchResult
from dlmm_position_lab.prompts import (
    DOCUMENTATION_SYSTEM_PROMPT,
    build_documentation_prompt,
)

DEFAULT_CHAT_MODEL = "gpt-5-mini"
DEFAULT_CONTEXT_LIMIT = 5
Retriever = Callable[[str, int], list[SearchResult]]


def chat_model() -> str:
    """Return the configured OpenAI model for grounded answers."""
    return os.getenv("OPENAI_CHAT_MODEL", DEFAULT_CHAT_MODEL)


def answer_documentation_question(
    question: str,
    *,
    retriever: Retriever | None = None,
    client: Any | None = None,
    model: str | None = None,
    context_limit: int = DEFAULT_CONTEXT_LIMIT,
    clock: Callable[[], float] = perf_counter,
) -> Answer:
    """Retrieve documentation and generate a grounded, cited answer."""
    normalized_question = question.strip()
    if not normalized_question:
        raise ValueError("question must not be empty")
    if context_limit <= 0:
        raise ValueError("context_limit must be positive")

    started = clock()
    run_retrieval = retriever or hybrid_search
    results = run_retrieval(normalized_question, context_limit)
    prompt = build_documentation_prompt(normalized_question, results)
    openai_client = client or create_openai_client()
    response = openai_client.responses.create(
        model=model or chat_model(),
        instructions=DOCUMENTATION_SYSTEM_PROMPT,
        input=prompt,
        max_output_tokens=500,
    )
    answer_text = response.output_text.strip()
    if not answer_text:
        raise RuntimeError("OpenAI returned an empty answer")

    return Answer(
        answer=answer_text,
        sources=[
            AnswerSource(
                document_id=result.id,
                title=result.title,
                section=result.section,
                url=result.url,
            )
            for result in results
        ],
        retrieved_document_ids=[result.id for result in results],
        latency_ms=(clock() - started) * 1_000,
    )
