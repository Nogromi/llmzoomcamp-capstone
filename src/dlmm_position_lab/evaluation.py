"""Reusable retrieval-evaluation metrics and dataset loading."""

import json
from collections.abc import Callable
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from dlmm_position_lab.models import SearchResult

Retriever = Callable[[str, int], list[SearchResult]]


class EvaluationQuestion(BaseModel):
    """A reviewed question with its relevant documentation chunks."""

    model_config = ConfigDict(frozen=True)

    question: str
    expected_document_ids: list[str]
    category: str = "documentation"


class RetrievalMetrics(BaseModel):
    """Summary metrics for one retrieval method."""

    model_config = ConfigDict(frozen=True)

    retriever: str
    questions: int
    hit_rate_at_5: float
    mrr: float


def load_questions(path: Path) -> list[EvaluationQuestion]:
    """Load and validate the reviewed evaluation dataset."""
    records = json.loads(path.read_text(encoding="utf-8"))
    return [EvaluationQuestion.model_validate(record) for record in records]


def evaluate_retriever(
    name: str,
    questions: list[EvaluationQuestion],
    retriever: Retriever,
) -> RetrievalMetrics:
    """Calculate Hit Rate@5 and reciprocal rank over reviewed questions."""
    if not questions:
        raise ValueError("questions must not be empty")

    hits = 0
    reciprocal_rank_total = 0.0
    for item in questions:
        expected_ids = set(item.expected_document_ids)
        result_ids = [result.id for result in retriever(item.question, 5)]
        relevant_ranks = [
            rank
            for rank, document_id in enumerate(result_ids, start=1)
            if document_id in expected_ids
        ]
        if relevant_ranks:
            hits += 1
            reciprocal_rank_total += 1 / relevant_ranks[0]

    return RetrievalMetrics(
        retriever=name,
        questions=len(questions),
        hit_rate_at_5=hits / len(questions),
        mrr=reciprocal_rank_total / len(questions),
    )
