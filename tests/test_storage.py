from pathlib import Path

from dlmm_position_lab.models import (
    Answer,
    ApplicationResponse,
    QuestionType,
    RouterDecision,
    RoutingResult,
)
from dlmm_position_lab.storage import (
    load_feedback,
    load_requests,
    record_error,
    record_response,
    save_feedback,
)


def application_response() -> ApplicationResponse:
    return ApplicationResponse(
        routing=RoutingResult(
            question="What is a bin?",
            decision=RouterDecision(
                question_type=QuestionType.DOCUMENTATION,
                use_rag=True,
                tools=[],
                explanation="Documentation question.",
            ),
            latency_ms=10,
            input_tokens=20,
            output_tokens=5,
        ),
        answer=Answer(
            answer="A bin is a price point [1].",
            sources=[],
            retrieved_document_ids=["doc-1"],
            latency_ms=30,
            input_tokens=100,
            output_tokens=25,
        ),
    )


def test_request_and_feedback_are_persisted(tmp_path: Path) -> None:
    path = tmp_path / "application.db"
    response = application_response()

    request_id = record_response("conversation", response, 50, path=path)
    save_feedback(
        request_id,
        "conversation",
        response.routing.question,
        response.answer.answer,
        1,
        "Useful",
        path=path,
    )

    request = load_requests(path)[0]
    feedback = load_feedback(path)[0]
    assert request["question_type"] == "documentation"
    assert request["retrieved_document_ids"] == '["doc-1"]'
    assert request["input_tokens"] == 120
    assert feedback["rating"] == 1
    assert feedback["comment"] == "Useful"


def test_errors_are_persisted(tmp_path: Path) -> None:
    path = tmp_path / "application.db"
    record_error("conversation", "Question", "API unavailable", 25, path=path)

    assert load_requests(path)[0]["error"] == "API unavailable"
