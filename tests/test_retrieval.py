from unittest.mock import MagicMock, patch

import pytest

from dlmm_position_lab.models import SearchResult
from dlmm_position_lab.retrieval import (
    bm25_search,
    build_bm25_query,
    search_docs,
    vector_search,
)


def test_build_bm25_query_exposes_field_boosts() -> None:
    assert build_bm25_query("  What is an active bin?  ") == {
        "bool": {
            "should": [
                {
                    "multi_match": {
                        "query": "What is an active bin?",
                        "fields": ["title^2", "section^3", "text"],
                        "type": "best_fields",
                    }
                },
                {
                    "match_phrase": {
                        "section": {"query": "What is an active bin?", "boost": 4}
                    }
                },
                {
                    "match_phrase": {
                        "text": {"query": "What is an active bin?", "boost": 2}
                    }
                },
            ],
            "minimum_should_match": 1,
        }
    }


def test_bm25_search_normalizes_elasticsearch_hits() -> None:
    client = MagicMock()
    client.search.return_value = {
        "hits": {
            "hits": [
                {
                    "_id": "chunk-1",
                    "_score": 8.25,
                    "_source": {
                        "id": "chunk-1",
                        "title": "What is DLMM?",
                        "section": "Price Bins",
                        "url": "https://docs.meteora.ag/dlmm",
                        "text": "Only the active bin is available for swaps.",
                    },
                }
            ]
        }
    }

    results = bm25_search("active bin", limit=3, client=client)

    assert results == [
        SearchResult(
            id="chunk-1",
            title="What is DLMM?",
            section="Price Bins",
            url="https://docs.meteora.ag/dlmm",
            text="Only the active bin is available for swaps.",
            score=8.25,
        )
    ]
    client.search.assert_called_once_with(
        index="meteora_docs",
        query=build_bm25_query("active bin"),
        size=3,
        source=["id", "title", "section", "url", "text"],
    )


def test_search_docs_is_public_bm25_entrypoint() -> None:
    assert search_docs is bm25_search


@pytest.mark.parametrize(
    ("query", "limit", "message"),
    [("", 5, "query must not be empty"), ("valid", 0, "limit must be positive")],
)
def test_bm25_search_validates_input(query: str, limit: int, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        bm25_search(query, limit=limit, client=MagicMock())


@patch("dlmm_position_lab.retrieval.embed_texts", return_value=[[0.1, 0.2]])
def test_vector_search_embeds_query_and_builds_knn_request(
    mock_embed_texts: MagicMock,
) -> None:
    client = MagicMock()
    client.search.return_value = {
        "hits": {
            "hits": [
                {
                    "_id": "semantic-1",
                    "_score": 0.92,
                    "_source": {
                        "id": "semantic-1",
                        "title": "DLMM",
                        "section": "Dynamic Fees",
                        "url": "https://docs.meteora.ag/dlmm",
                        "text": "Fees respond to market volatility.",
                    },
                }
            ]
        }
    }
    embedding_client = MagicMock()

    results = vector_search(
        "  volatility-based fees  ",
        limit=4,
        client=client,
        embedding_client=embedding_client,
    )

    mock_embed_texts.assert_called_once_with(
        ["volatility-based fees"], client=embedding_client
    )
    client.search.assert_called_once_with(
        index="meteora_docs",
        knn={
            "field": "embedding",
            "query_vector": [0.1, 0.2],
            "k": 4,
            "num_candidates": 100,
        },
        size=4,
        source=["id", "title", "section", "url", "text"],
    )
    assert results[0].id == "semantic-1"
    assert results[0].score == 0.92


@pytest.mark.parametrize(("query", "limit"), [("", 5), ("valid", 0)])
def test_vector_search_validates_input_before_api_call(query: str, limit: int) -> None:
    with pytest.raises(ValueError):
        vector_search(query, limit, client=MagicMock(), embedding_client=MagicMock())
