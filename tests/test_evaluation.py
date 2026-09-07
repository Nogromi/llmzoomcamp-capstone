import json
from pathlib import Path

import pytest

from dlmm_position_lab.evaluation import (
    EvaluationQuestion,
    evaluate_retriever,
    load_questions,
)
from dlmm_position_lab.models import SearchResult


def result(identifier: str) -> SearchResult:
    return SearchResult(
        id=identifier,
        title="Title",
        section="Section",
        url="https://example.test",
        text="Text",
        score=1,
    )


def test_evaluate_retriever_calculates_hit_rate_and_mrr() -> None:
    questions = [
        EvaluationQuestion(question="first", expected_document_ids=["a"]),
        EvaluationQuestion(question="second", expected_document_ids=["b"]),
        EvaluationQuestion(question="miss", expected_document_ids=["c"]),
    ]
    rankings = {
        "first": [result("a"), result("x")],
        "second": [result("x"), result("b")],
        "miss": [result("x")],
    }

    metrics = evaluate_retriever(
        "test", questions, lambda query, _limit: rankings[query]
    )

    assert metrics.questions == 3
    assert metrics.hit_rate_at_5 == pytest.approx(2 / 3)
    assert metrics.mrr == pytest.approx(0.5)


def test_load_questions_validates_json(tmp_path: Path) -> None:
    path = tmp_path / "questions.json"
    path.write_text(
        json.dumps(
            [
                {
                    "question": "What is a bin?",
                    "expected_document_ids": ["document-1"],
                    "category": "documentation",
                }
            ]
        ),
        encoding="utf-8",
    )

    assert load_questions(path)[0].expected_document_ids == ["document-1"]


def test_evaluate_retriever_requires_questions() -> None:
    with pytest.raises(ValueError, match="questions must not be empty"):
        evaluate_retriever("test", [], lambda _query, _limit: [])
