"""Simple deterministic RAG and router-evaluation helpers."""

import re
from collections.abc import Callable

from openai import OpenAIError
from pydantic import BaseModel, ConfigDict

from dlmm_position_lab.models import Answer, QuestionType, RoutingResult, ToolName


class RagEvaluationCase(BaseModel):
    """One reviewed question and the document expected in retrieval."""

    model_config = ConfigDict(frozen=True)

    question: str
    expected_document_ids: list[str]


class RagValidation(BaseModel):
    """Small observable checks for one generated answer."""

    model_config = ConfigDict(frozen=True)

    has_answer: bool
    has_sources: bool
    has_inline_citation: bool
    expected_document_retrieved: bool

    @property
    def passed(self) -> bool:
        return all(
            (
                self.has_answer,
                self.has_sources,
                self.has_inline_citation,
                self.expected_document_retrieved,
            )
        )


class RagMetrics(BaseModel):
    """Aggregate rates for the deterministic RAG checks."""

    model_config = ConfigDict(frozen=True)

    questions: int
    pass_rate: float
    answer_rate: float
    source_rate: float
    citation_rate: float
    expected_document_rate: float


class RagCaseResult(BaseModel):
    """Generated answer and deterministic validation for one question."""

    model_config = ConfigDict(frozen=True)

    question: str
    answer: Answer
    validation: RagValidation


class RouterEvaluationCase(BaseModel):
    """One reviewed router input and its expected decision."""

    model_config = ConfigDict(frozen=True)

    question: str
    expected_question_type: QuestionType
    expected_use_rag: bool
    expected_tools: list[ToolName]


class RouterCaseResult(BaseModel):
    """Expected and actual route for one evaluation question."""

    model_config = ConfigDict(frozen=True)

    case: RouterEvaluationCase
    actual: RoutingResult | None
    error: str | None = None


class RouterMetrics(BaseModel):
    """Aggregate deterministic router metrics."""

    model_config = ConfigDict(frozen=True)

    questions: int
    classification_accuracy: float
    rag_selection_accuracy: float
    tool_selection_accuracy: float
    unnecessary_tool_call_rate: float
    failure_rate: float


def validate_rag_answer(case: RagEvaluationCase, answer: Answer) -> RagValidation:
    """Check basic answer, source, citation, and retrieval properties."""
    expected_ids = set(case.expected_document_ids)
    retrieved_ids = set(answer.retrieved_document_ids)
    return RagValidation(
        has_answer=bool(answer.answer.strip()),
        has_sources=bool(answer.sources),
        has_inline_citation=bool(re.search(r"\[\d+\]", answer.answer)),
        expected_document_retrieved=bool(expected_ids & retrieved_ids),
    )


def summarize_rag(validations: list[RagValidation]) -> RagMetrics:
    """Calculate aggregate rates for the simple RAG checks."""
    if not validations:
        raise ValueError("validations must not be empty")
    total = len(validations)
    return RagMetrics(
        questions=total,
        pass_rate=sum(item.passed for item in validations) / total,
        answer_rate=sum(item.has_answer for item in validations) / total,
        source_rate=sum(item.has_sources for item in validations) / total,
        citation_rate=sum(item.has_inline_citation for item in validations) / total,
        expected_document_rate=sum(
            item.expected_document_retrieved for item in validations
        )
        / total,
    )


def evaluate_router(
    cases: list[RouterEvaluationCase],
    router: Callable[[str], RoutingResult],
) -> tuple[RouterMetrics, list[RouterCaseResult]]:
    """Evaluate classification and capability selection against reviewed labels."""
    if not cases:
        raise ValueError("cases must not be empty")

    results: list[RouterCaseResult] = []
    for case in cases:
        try:
            results.append(RouterCaseResult(case=case, actual=router(case.question)))
        except (OpenAIError, RuntimeError, ValueError) as error:
            results.append(RouterCaseResult(case=case, actual=None, error=str(error)))

    successful = [item for item in results if item.actual is not None]
    no_tool_cases = [item for item in successful if not item.case.expected_tools]
    total = len(cases)
    return (
        RouterMetrics(
            questions=total,
            classification_accuracy=sum(
                item.actual.decision.question_type
                == item.case.expected_question_type
                for item in successful
            )
            / total,
            rag_selection_accuracy=sum(
                item.actual.decision.use_rag == item.case.expected_use_rag
                for item in successful
            )
            / total,
            tool_selection_accuracy=sum(
                item.actual.decision.tools == item.case.expected_tools
                for item in successful
            )
            / total,
            unnecessary_tool_call_rate=(
                sum(bool(item.actual.decision.tools) for item in no_tool_cases)
                / len(no_tool_cases)
                if no_tool_cases
                else 0.0
            ),
            failure_rate=(total - len(successful)) / total,
        ),
        results,
    )
