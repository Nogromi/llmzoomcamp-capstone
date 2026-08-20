"""Shared typed models for application boundaries."""

from pydantic import BaseModel, ConfigDict


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
