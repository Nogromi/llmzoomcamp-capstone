"""Run reproducible BM25, vector, and hybrid retrieval evaluation."""

import json
from functools import lru_cache
from pathlib import Path

from dlmm_position_lab.evaluation import evaluate_retriever, load_questions
from dlmm_position_lab.hybrid_search import hybrid_search
from dlmm_position_lab.models import SearchResult
from dlmm_position_lab.retrieval import bm25_search, vector_search

PROJECT_ROOT = Path(__file__).parents[1]
QUESTION_PATH = PROJECT_ROOT / "evaluation/questions.json"
RESULT_PATH = PROJECT_ROOT / "evaluation/results.json"
CANDIDATE_LIMIT = 10


@lru_cache
def bm25_candidates(query: str) -> tuple[SearchResult, ...]:
    return tuple(bm25_search(query, CANDIDATE_LIMIT))


@lru_cache
def vector_candidates(query: str) -> tuple[SearchResult, ...]:
    return tuple(vector_search(query, CANDIDATE_LIMIT))


def cached_bm25(query: str, limit: int) -> list[SearchResult]:
    return list(bm25_candidates(query)[:limit])


def cached_vector(query: str, limit: int) -> list[SearchResult]:
    return list(vector_candidates(query)[:limit])


def cached_hybrid(query: str, limit: int) -> list[SearchResult]:
    return hybrid_search(
        query,
        limit,
        candidate_limit=CANDIDATE_LIMIT,
        bm25_retriever=cached_bm25,
        vector_retriever=cached_vector,
    )


def main() -> None:
    questions = load_questions(QUESTION_PATH)
    metrics = [
        evaluate_retriever("BM25", questions, cached_bm25),
        evaluate_retriever("Vector", questions, cached_vector),
        evaluate_retriever("Hybrid", questions, cached_hybrid),
    ]
    RESULT_PATH.write_text(
        json.dumps([item.model_dump() for item in metrics], indent=2) + "\n",
        encoding="utf-8",
    )

    print("Retriever  Hit Rate@5  MRR")
    for item in metrics:
        print(
            f"{item.retriever:<10} {item.hit_rate_at_5:>10.3f}  {item.mrr:.3f}"
        )
    print(f"\nSaved: {RESULT_PATH}")


if __name__ == "__main__":
    main()
