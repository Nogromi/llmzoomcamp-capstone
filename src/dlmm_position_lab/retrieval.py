"""Independent retrieval methods for the Meteora documentation index."""

from __future__ import annotations

from typing import Any

from dlmm_position_lab.embeddings import embed_texts
from dlmm_position_lab.indexing import DEFAULT_INDEX_NAME, create_client
from dlmm_position_lab.models import SearchResult

DEFAULT_SEARCH_LIMIT = 5


def build_bm25_query(query: str) -> dict[str, object]:
    """Build the transparent weighted BM25 query used by Elasticsearch."""
    normalized_query = query.strip()
    if not normalized_query:
        raise ValueError("query must not be empty")
    return {
        "bool": {
            "should": [
                {
                    "multi_match": {
                        "query": normalized_query,
                        "fields": ["title^2", "section^3", "text"],
                        "type": "best_fields",
                    }
                },
                {
                    "match_phrase": {
                        "section": {"query": normalized_query, "boost": 4}
                    }
                },
                {
                    "match_phrase": {
                        "text": {"query": normalized_query, "boost": 2}
                    }
                },
            ],
            "minimum_should_match": 1,
        }
    }


def _execute_bm25_search(
    client: Any,
    query: str,
    limit: int,
    index_name: str,
) -> list[SearchResult]:
    response = client.search(
        index=index_name,
        query=build_bm25_query(query),
        size=limit,
        source=["id", "title", "section", "url", "text"],
    )
    results: list[SearchResult] = []
    for hit in response["hits"]["hits"]:
        source = hit["_source"]
        results.append(
            SearchResult(
                id=str(source.get("id", hit["_id"])),
                title=str(source["title"]),
                section=str(source["section"]),
                url=str(source["url"]),
                text=str(source["text"]),
                score=float(hit["_score"] or 0.0),
            )
        )
    return results


def bm25_search(
    query: str,
    limit: int = DEFAULT_SEARCH_LIMIT,
    *,
    client: Any | None = None,
    index_name: str = DEFAULT_INDEX_NAME,
) -> list[SearchResult]:
    """Search documentation with Elasticsearch BM25 and weighted fields."""
    if limit <= 0:
        raise ValueError("limit must be positive")
    if client is not None:
        return _execute_bm25_search(client, query, limit, index_name)
    with create_client() as managed_client:
        return _execute_bm25_search(managed_client, query, limit, index_name)


# Milestone 4's public name from the PRD; kept as an explicit alias so later
# retrievers can coexist as bm25_search(), vector_search(), and hybrid_search().
search_docs = bm25_search


def _execute_vector_search(
    client: Any,
    query_vector: list[float],
    limit: int,
    index_name: str,
) -> list[SearchResult]:
    response = client.search(
        index=index_name,
        knn={
            "field": "embedding",
            "query_vector": query_vector,
            "k": limit,
            "num_candidates": max(100, limit * 10),
        },
        size=limit,
        source=["id", "title", "section", "url", "text"],
    )
    return [
        SearchResult(
            id=str(hit["_source"].get("id", hit["_id"])),
            title=str(hit["_source"]["title"]),
            section=str(hit["_source"]["section"]),
            url=str(hit["_source"]["url"]),
            text=str(hit["_source"]["text"]),
            score=float(hit["_score"] or 0.0),
        )
        for hit in response["hits"]["hits"]
    ]


def vector_search(
    query: str,
    limit: int = DEFAULT_SEARCH_LIMIT,
    *,
    client: Any | None = None,
    embedding_client: Any | None = None,
    index_name: str = DEFAULT_INDEX_NAME,
) -> list[SearchResult]:
    """Search documentation by semantic similarity using an OpenAI query vector."""
    normalized_query = query.strip()
    if not normalized_query:
        raise ValueError("query must not be empty")
    if limit <= 0:
        raise ValueError("limit must be positive")
    query_vector = embed_texts([normalized_query], client=embedding_client)[0]
    if client is not None:
        return _execute_vector_search(client, query_vector, limit, index_name)
    with create_client() as managed_client:
        return _execute_vector_search(managed_client, query_vector, limit, index_name)
