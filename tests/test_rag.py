from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from dlmm_position_lab.models import SearchResult
from dlmm_position_lab.prompts import DOCUMENTATION_SYSTEM_PROMPT
from dlmm_position_lab.rag import answer_documentation_question


def result(identifier: str) -> SearchResult:
    return SearchResult(
        id=identifier,
        title=f"Title {identifier}",
        section=f"Section {identifier}",
        url=f"https://example.test/{identifier}",
        text=f"Evidence for {identifier}.",
        score=1.0,
    )


def test_rag_returns_grounded_answer_sources_ids_and_latency() -> None:
    retriever = MagicMock(return_value=[result("one"), result("two")])
    client = MagicMock()
    client.responses.create.return_value = SimpleNamespace(
        output_text="A grounded answer [1]."
    )
    times = iter([10.0, 10.125])

    answer = answer_documentation_question(
        "  What is a bin?  ",
        retriever=retriever,
        client=client,
        model="test-model",
        context_limit=2,
        clock=lambda: next(times),
    )

    retriever.assert_called_once_with("What is a bin?", 2)
    request = client.responses.create.call_args.kwargs
    assert request["model"] == "test-model"
    assert request["instructions"] == DOCUMENTATION_SYSTEM_PROMPT
    assert "[1] Title one — Section one" in request["input"]
    assert request["max_output_tokens"] == 1_200
    assert answer.answer == "A grounded answer [1]."
    assert answer.retrieved_document_ids == ["one", "two"]
    assert [source.document_id for source in answer.sources] == ["one", "two"]
    assert answer.sources[0].url == "https://example.test/one"
    assert answer.latency_ms == pytest.approx(125.0)


@pytest.mark.parametrize(
    ("question", "limit", "message"),
    [
        (" ", 5, "question must not be empty"),
        ("valid", 0, "context_limit must be positive"),
    ],
)
def test_rag_validates_inputs(question: str, limit: int, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        answer_documentation_question(question, context_limit=limit)


def test_rag_rejects_empty_model_response() -> None:
    client = MagicMock()
    client.responses.create.return_value = SimpleNamespace(output_text="  ")

    with pytest.raises(RuntimeError, match="empty answer"):
        answer_documentation_question(
            "Question",
            retriever=lambda _question, _limit: [result("one")],
            client=client,
        )
