"""Elasticsearch keyword, vector, and hybrid search."""

import os

from elasticsearch import Elasticsearch
from openai import OpenAI

INDEX_NAME = "meteora_docs"
EMBEDDING_MODEL = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
EMBEDDING_DIMENSIONS = int(os.getenv("OPENAI_EMBEDDING_DIMENSIONS", "512"))
SOURCE_FIELDS = ["id", "title", "section", "url", "text"]


def create_client() -> Elasticsearch:
    return Elasticsearch(
        os.getenv("ELASTICSEARCH_URL", "http://localhost:9200"), request_timeout=30
    )


def embed_texts(texts: list[str]) -> list[list[float]]:
    vectors = []
    with OpenAI() as client:
        for start in range(0, len(texts), 64):
            response = client.embeddings.create(
                model=EMBEDDING_MODEL,
                dimensions=EMBEDDING_DIMENSIONS,
                input=texts[start : start + 64],
                encoding_format="float",
            )
            vectors.extend(
                item.embedding for item in sorted(response.data, key=lambda x: x.index)
            )
    return vectors


def fuse_results(rankings: list[list[dict]], limit: int = 5) -> list[dict]:
    """Reciprocal Rank Fusion: each rank contributes 1 / (60 + rank)."""
    scores, documents = {}, {}
    for ranking in rankings:
        for rank, document in enumerate(ranking, 1):
            document_id = document["id"]
            documents[document_id] = document
            scores[document_id] = scores.get(document_id, 0) + 1 / (60 + rank)
    ordered = sorted(scores, key=scores.get, reverse=True)[:limit]
    return [documents[document_id] for document_id in ordered]


def search(query: str, mode: str = "hybrid", limit: int = 5) -> list[dict]:
    if not query.strip() or limit < 1:
        raise ValueError("Enter a question and a positive result limit.")
    if mode not in {"bm25", "vector", "hybrid"}:
        raise ValueError("Search mode must be bm25, vector, or hybrid.")
    size = max(10, limit) if mode == "hybrid" else limit
    rankings = []
    with create_client() as client:
        if not client.indices.exists(index=INDEX_NAME):
            raise RuntimeError(
                "Run flows/ingest_docs.py to build the documentation index."
            )
        if mode in {"bm25", "hybrid"}:
            response = client.search(
                index=INDEX_NAME,
                size=size,
                source=SOURCE_FIELDS,
                query={
                    "bool": {
                        "should": [
                            {
                                "multi_match": {
                                    "query": query,
                                    "fields": ["title^2", "section^3", "text"],
                                }
                            },
                            {"match_phrase": {"section": {"query": query, "boost": 4}}},
                            {"match_phrase": {"text": {"query": query, "boost": 2}}},
                        ],
                        "minimum_should_match": 1,
                    }
                },
            )
            rankings.append([hit["_source"] for hit in response["hits"]["hits"]])
        if mode in {"vector", "hybrid"}:
            response = client.search(
                index=INDEX_NAME,
                size=size,
                source=SOURCE_FIELDS,
                knn={
                    "field": "embedding",
                    "query_vector": embed_texts([query])[0],
                    "k": size,
                    "num_candidates": max(100, size * 10),
                },
            )
            rankings.append([hit["_source"] for hit in response["hits"]["hits"]])
    return fuse_results(rankings, limit) if mode == "hybrid" else rankings[0]
