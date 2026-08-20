"""Hybrid retrieval using Reciprocal Rank Fusion over independent rankings."""

from __future__ import annotations

from collections.abc import Callable, Sequence

from dlmm_position_lab.models import SearchResult
from dlmm_position_lab.retrieval import bm25_search, vector_search

RRF_K = 60
DEFAULT_CANDIDATE_LIMIT = 10
Retriever = Callable[[str, int], list[SearchResult]]


def reciprocal_rank_fusion(
    rankings: Sequence[Sequence[SearchResult]],
    limit: int = 5,
    *,
    rrf_k: int = RRF_K,
) -> list[SearchResult]:
    """Fuse rankings by document ID without comparing incompatible raw scores."""
    if limit <= 0:
        raise ValueError("limit must be positive")
    if rrf_k < 0:
        raise ValueError("rrf_k must not be negative")

    fused_scores: dict[str, float] = {}
    documents: dict[str, SearchResult] = {}
    first_seen: dict[str, int] = {}
    seen_position = 0

    for ranking in rankings:
        seen_in_ranking: set[str] = set()
        for rank, result in enumerate(ranking, start=1):
            if result.id in seen_in_ranking:
                continue
            seen_in_ranking.add(result.id)
            if result.id not in documents:
                documents[result.id] = result
                first_seen[result.id] = seen_position
                seen_position += 1
            fused_scores[result.id] = fused_scores.get(result.id, 0.0) + 1 / (
                rrf_k + rank
            )

    ordered_ids = sorted(
        fused_scores,
        key=lambda document_id: (
            -fused_scores[document_id],
            first_seen[document_id],
        ),
    )[:limit]
    return [
        documents[document_id].model_copy(
            update={"score": fused_scores[document_id]}
        )
        for document_id in ordered_ids
    ]


def hybrid_search(
    query: str,
    limit: int = 5,
    *,
    candidate_limit: int = DEFAULT_CANDIDATE_LIMIT,
    bm25_retriever: Retriever | None = None,
    vector_retriever: Retriever | None = None,
) -> list[SearchResult]:
    """Retrieve BM25 and vector candidates, then combine them with RRF."""
    normalized_query = query.strip()
    if not normalized_query:
        raise ValueError("query must not be empty")
    if limit <= 0:
        raise ValueError("limit must be positive")
    if candidate_limit < limit:
        raise ValueError("candidate_limit must be at least limit")

    run_bm25 = bm25_retriever or bm25_search
    run_vector = vector_retriever or vector_search
    bm25_results = run_bm25(normalized_query, candidate_limit)
    vector_results = run_vector(normalized_query, candidate_limit)
    return reciprocal_rank_fusion([bm25_results, vector_results], limit)
