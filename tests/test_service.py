from unittest.mock import MagicMock

from dlmm_position_lab.models import (
    Answer,
    ApplicationResponse,
    Pool,
    PoolConfig,
    PoolToken,
    QuestionType,
    RouterDecision,
    RoutingResult,
    ToolName,
)
from dlmm_position_lab.service import POOL_DATA_NOTICE, respond_to_question


def routing(
    question_type: QuestionType, use_rag: bool, tools: list[ToolName]
) -> RoutingResult:
    return RoutingResult(
        question="Normalized question",
        decision=RouterDecision(
            question_type=question_type,
            use_rag=use_rag,
            tools=tools,
            explanation="Test route.",
        ),
        latency_ms=10,
    )


def pool() -> Pool:
    token = PoolToken(
        address="token", name="Token", symbol="TOK", decimals=6, price=1
    )
    return Pool(
        address="pool-address",
        name="TOK-USDC",
        current_price=1,
        tvl=1000,
        dynamic_fee_pct=0.1,
        token_x=token,
        token_y=token,
        pool_config=PoolConfig(
            bin_step=10,
            base_fee_pct=0.1,
            max_fee_pct=1,
            collect_fee_mode=0,
        ),
        volume={"24h": 100},
        fees={"24h": 1},
    )


def test_documentation_route_runs_rag() -> None:
    route = routing(QuestionType.DOCUMENTATION, True, [])
    router = MagicMock(return_value=route)
    answer = Answer(
        answer="Grounded answer [1].",
        sources=[],
        retrieved_document_ids=[],
        latency_ms=20,
    )
    answerer = MagicMock(return_value=answer)

    response = respond_to_question("Question", router=router, answerer=answerer)

    assert response == ApplicationResponse(routing=route, answer=answer)
    answerer.assert_called_once_with("Normalized question")


def test_pool_route_does_not_run_rag_or_fake_live_data() -> None:
    route = routing(QuestionType.POOL_DATA, False, [ToolName.GET_POOL])
    answerer = MagicMock()

    response = respond_to_question(
        "Pool question", router=MagicMock(return_value=route), answerer=answerer
    )

    assert response.answer is None
    assert response.notice == POOL_DATA_NOTICE
    answerer.assert_not_called()


def test_combined_route_runs_rag_and_discloses_missing_live_data() -> None:
    route = routing(QuestionType.COMBINED, True, [ToolName.GET_POOL])
    answer = Answer(
        answer="Documentation-only answer.",
        sources=[],
        retrieved_document_ids=[],
        latency_ms=20,
    )

    response = respond_to_question(
        "Combined question",
        router=MagicMock(return_value=route),
        answerer=MagicMock(return_value=answer),
    )

    assert response.answer == answer
    assert response.notice == POOL_DATA_NOTICE


def test_pool_route_calls_only_get_pool_when_address_is_present() -> None:
    route = routing(QuestionType.POOL_DATA, False, [ToolName.GET_POOL])
    pool_getter = MagicMock(return_value=pool())

    response = respond_to_question(
        "Pool question",
        pool_address="pool-address",
        router=MagicMock(return_value=route),
        pool_getter=pool_getter,
    )

    pool_getter.assert_called_once_with("pool-address")
    assert response.pool == pool()
    assert response.notice is None
