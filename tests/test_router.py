from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from pydantic import ValidationError

from dlmm_position_lab.models import QuestionType, RouterDecision, ToolName
from dlmm_position_lab.prompts import ROUTER_SYSTEM_PROMPT
from dlmm_position_lab.router import route_question


def test_route_question_returns_typed_observable_decision() -> None:
    decision = RouterDecision(
        question_type=QuestionType.COMBINED,
        use_rag=True,
        tools=[ToolName.GET_POOL],
        explanation="The question needs an explanation and current pool data.",
    )
    client = MagicMock()
    client.responses.parse.return_value = SimpleNamespace(output_parsed=decision)
    times = iter([5.0, 5.05])

    result = route_question(
        "  Explain the fees for this pool  ",
        client=client,
        model="test-model",
        clock=lambda: next(times),
    )

    request = client.responses.parse.call_args.kwargs
    assert request == {
        "model": "test-model",
        "instructions": ROUTER_SYSTEM_PROMPT,
        "input": "Explain the fees for this pool",
        "text_format": RouterDecision,
        "max_output_tokens": 1_200,
    }
    assert result.question == "Explain the fees for this pool"
    assert result.decision == decision
    assert result.latency_ms == pytest.approx(50)


def test_router_decision_rejects_tool_outside_route() -> None:
    with pytest.raises(ValidationError, match="inconsistent documentation route"):
        RouterDecision(
            question_type=QuestionType.DOCUMENTATION,
            use_rag=True,
            tools=[ToolName.GET_POOL],
            explanation="Invalid decision.",
        )


def test_route_question_rejects_empty_question() -> None:
    with pytest.raises(ValueError, match="question must not be empty"):
        route_question("  ")


def test_route_question_requires_parsed_output() -> None:
    client = MagicMock()
    client.responses.parse.return_value = SimpleNamespace(output_parsed=None)

    with pytest.raises(RuntimeError, match="no router decision"):
        route_question("What is a bin?", client=client)
