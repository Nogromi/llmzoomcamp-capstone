"""Application workflow kept separate from the Streamlit presentation layer."""

from collections.abc import Callable

from dlmm_position_lab.meteora_client import get_pool
from dlmm_position_lab.models import Answer, ApplicationResponse, Pool, RoutingResult
from dlmm_position_lab.rag import answer_documentation_question
from dlmm_position_lab.router import route_question

Router = Callable[[str], RoutingResult]
Answerer = Callable[[str], Answer]
PoolGetter = Callable[[str], Pool]

POOL_DATA_NOTICE = (
    "Enter a pool address in the sidebar to call the read-only get_pool tool."
)


def respond_to_question(
    question: str,
    *,
    pool_address: str = "",
    router: Router = route_question,
    answerer: Answerer = answer_documentation_question,
    pool_getter: PoolGetter = get_pool,
) -> ApplicationResponse:
    """Route a question and run only the capabilities currently implemented."""
    routing = router(question)
    answer = answerer(routing.question) if routing.decision.use_rag else None
    needs_pool = bool(routing.decision.tools)
    pool = pool_getter(pool_address) if needs_pool and pool_address.strip() else None
    notice = POOL_DATA_NOTICE if needs_pool and pool is None else None
    return ApplicationResponse(
        routing=routing,
        answer=answer,
        pool=pool,
        notice=notice,
    )
