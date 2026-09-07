import pytest

from dlmm_position_lab.models import (
    Answer,
    AnswerSource,
    QuestionType,
    RouterDecision,
    RoutingResult,
    ToolName,
)
from dlmm_position_lab.quality_evaluation import (
    RagEvaluationCase,
    RagValidation,
    RouterEvaluationCase,
    evaluate_router,
    summarize_rag,
    validate_rag_answer,
)


def routing(question_type: QuestionType) -> RoutingResult:
    use_rag = question_type != QuestionType.POOL_DATA
    tools = [] if question_type == QuestionType.DOCUMENTATION else [ToolName.GET_POOL]
    return RoutingResult(
        question="question",
        decision=RouterDecision(
            question_type=question_type,
            use_rag=use_rag,
            tools=tools,
            explanation="Route explanation.",
        ),
        latency_ms=10,
    )


def test_validate_rag_answer_checks_simple_observable_properties() -> None:
    case = RagEvaluationCase(question="What is a bin step?", expected_document_ids=["one"])
    answer = Answer(
        answer="A bin step separates adjacent bins [1].",
        sources=[
            AnswerSource(
                document_id="one",
                title="DLMM",
                section="Bin Step",
                url="https://example.test",
            )
        ],
        retrieved_document_ids=["one", "two"],
        latency_ms=10,
    )

    result = validate_rag_answer(case, answer)

    assert result.passed is True
    assert result.has_answer is True
    assert result.has_sources is True
    assert result.has_inline_citation is True
    assert result.expected_document_retrieved is True


def test_summarize_rag_calculates_each_rate() -> None:
    metrics = summarize_rag(
        [
            RagValidation(
                has_answer=True,
                has_sources=True,
                has_inline_citation=True,
                expected_document_retrieved=True,
            ),
            RagValidation(
                has_answer=True,
                has_sources=True,
                has_inline_citation=False,
                expected_document_retrieved=False,
            ),
        ]
    )

    assert metrics.pass_rate == 0.5
    assert metrics.answer_rate == 1
    assert metrics.source_rate == 1
    assert metrics.citation_rate == 0.5
    assert metrics.expected_document_rate == 0.5


def test_evaluate_router_scores_decisions_and_failures() -> None:
    cases = [
        RouterEvaluationCase(
            question="wrong",
            expected_question_type=QuestionType.DOCUMENTATION,
            expected_use_rag=True,
            expected_tools=[],
        ),
        RouterEvaluationCase(
            question="correct",
            expected_question_type=QuestionType.POOL_DATA,
            expected_use_rag=False,
            expected_tools=[ToolName.GET_POOL],
        ),
        RouterEvaluationCase(
            question="failure",
            expected_question_type=QuestionType.COMBINED,
            expected_use_rag=True,
            expected_tools=[ToolName.GET_POOL],
        ),
    ]

    def fake_router(question: str) -> RoutingResult:
        if question == "wrong":
            return routing(QuestionType.POOL_DATA)
        if question == "correct":
            return routing(QuestionType.POOL_DATA)
        raise RuntimeError("model unavailable")

    metrics, results = evaluate_router(cases, fake_router)

    assert metrics.classification_accuracy == pytest.approx(1 / 3)
    assert metrics.rag_selection_accuracy == pytest.approx(1 / 3)
    assert metrics.tool_selection_accuracy == pytest.approx(1 / 3)
    assert metrics.unnecessary_tool_call_rate == 1
    assert metrics.failure_rate == pytest.approx(1 / 3)
    assert results[-1].error == "model unavailable"
