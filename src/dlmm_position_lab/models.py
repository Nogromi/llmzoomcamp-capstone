"""Shared typed models for application boundaries."""

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, model_validator


class SearchResult(BaseModel):
    """One normalized document returned by a retriever."""

    model_config = ConfigDict(frozen=True)

    id: str
    title: str
    section: str
    url: str
    text: str
    score: float


class AnswerSource(BaseModel):
    """A documentation chunk exposed as an answer citation."""

    model_config = ConfigDict(frozen=True)

    document_id: str
    title: str
    section: str
    url: str


class Answer(BaseModel):
    """Grounded RAG answer and its retrieval metadata."""

    model_config = ConfigDict(frozen=True)

    answer: str
    sources: list[AnswerSource]
    retrieved_document_ids: list[str]
    latency_ms: float
    input_tokens: int = 0
    output_tokens: int = 0


class RangeAnalysis(BaseModel):
    """Deterministic summary of closing prices against a selected range."""

    model_config = ConfigDict(frozen=True)

    current_price: float
    inside_range: bool
    range_width: float
    min_price: float
    max_price: float
    percentage_inside_range: float
    number_of_range_exits: int
    distance_to_lower_boundary: float
    distance_to_upper_boundary: float


class QuestionType(StrEnum):
    """Supported routes for user questions."""

    DOCUMENTATION = "documentation"
    POOL_DATA = "pool_data"
    COMBINED = "combined"


class ToolName(StrEnum):
    """Complete allowlist of LLM-selectable application tools."""

    GET_POOL = "get_pool"


class RouterDecision(BaseModel):
    """Structured, validated decision produced by the query router."""

    model_config = ConfigDict(frozen=True)

    question_type: QuestionType
    use_rag: bool
    tools: list[ToolName]
    explanation: str

    @model_validator(mode="after")
    def validate_route(self) -> "RouterDecision":
        expected = {
            QuestionType.DOCUMENTATION: (True, []),
            QuestionType.POOL_DATA: (False, [ToolName.GET_POOL]),
            QuestionType.COMBINED: (True, [ToolName.GET_POOL]),
        }
        expected_rag, expected_tools = expected[self.question_type]
        if self.use_rag != expected_rag or self.tools != expected_tools:
            raise ValueError(f"inconsistent {self.question_type} route")
        return self


class RoutingResult(BaseModel):
    """Router decision plus observable request metadata."""

    model_config = ConfigDict(frozen=True)

    question: str
    decision: RouterDecision
    latency_ms: float
    input_tokens: int = 0
    output_tokens: int = 0


class PoolToken(BaseModel):
    """Token metadata returned with a Meteora pool."""

    address: str
    name: str
    symbol: str
    decimals: int
    price: float


class PoolConfig(BaseModel):
    """Small subset of pool configuration used by the application."""

    bin_step: int
    base_fee_pct: float
    max_fee_pct: float
    collect_fee_mode: int


class Pool(BaseModel):
    """Read-only current pool state from Meteora's DLMM Data API."""

    address: str
    name: str
    current_price: float
    tvl: float
    dynamic_fee_pct: float
    token_x: PoolToken
    token_y: PoolToken
    pool_config: PoolConfig
    volume: dict[str, float]
    fees: dict[str, float]


class ApplicationResponse(BaseModel):
    """One routed application response rendered by the user interface."""

    model_config = ConfigDict(frozen=True)

    routing: RoutingResult
    answer: Answer | None = None
    pool: Pool | None = None
    notice: str | None = None
