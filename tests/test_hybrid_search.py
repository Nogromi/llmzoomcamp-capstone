from unittest.mock import MagicMock

import pytest

from dlmm_position_lab.hybrid_search import hybrid_search, reciprocal_rank_fusion
from dlmm_position_lab.models import SearchResult


def result(identifier: str, score: float = 1.0) -> SearchResult:
    return SearchResult(
        id=identifier,
        title=f"Title {identifier}",
        section=f"Section {identifier}",
        url=f"https://example.test/{identifier}",
        text=f"Text for {identifier}",
        score=score,
    )


def test_rrf_rewards_documents_found_by_both_retrievers() -> None:
    fused = reciprocal_rank_fusion(
        [
            [result("bm25-only"), result("shared")],
            [result("vector-only"), result("shared")],
        ],
        limit=3,
    )

    assert [item.id for item in fused] == ["shared", "bm25-only", "vector-only"]
    assert fused[0].score == pytest.approx(2 / 62)
    assert fused[1].score == pytest.approx(1 / 61)


def test_rrf_removes_duplicates_within_and_across_rankings() -> None:
    fused = reciprocal_rank_fusion(
        [[result("same"), result("same")], [result("same")]], limit=5
    )

    assert [item.id for item in fused] == ["same"]
    assert fused[0].score == pytest.approx(2 / 61)


def test_hybrid_search_requests_candidates_and_fuses_results() -> None:
    bm25 = MagicMock(return_value=[result("keyword"), result("shared")])
    vector = MagicMock(return_value=[result("shared"), result("semantic")])

    fused = hybrid_search(
        "  dynamic fees  ",
        limit=2,
        candidate_limit=10,
        bm25_retriever=bm25,
        vector_retriever=vector,
    )

    bm25.assert_called_once_with("dynamic fees", 10)
    vector.assert_called_once_with("dynamic fees", 10)
    assert [item.id for item in fused] == ["shared", "keyword"]


@pytest.mark.parametrize(
    ("query", "limit", "candidate_limit", "message"),
    [
        ("", 5, 10, "query must not be empty"),
        ("valid", 0, 10, "limit must be positive"),
        ("valid", 5, 4, "candidate_limit must be at least limit"),
    ],
)
def test_hybrid_search_validates_inputs(
    query: str, limit: int, candidate_limit: int, message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        hybrid_search(query, limit, candidate_limit=candidate_limit)


def test_rrf_validates_constant() -> None:
    with pytest.raises(ValueError, match="rrf_k must not be negative"):
        reciprocal_rank_fusion([], rrf_k=-1)
