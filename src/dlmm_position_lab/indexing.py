"""Elasticsearch index management for Meteora documentation chunks."""

from __future__ import annotations

import os
from collections.abc import Iterable
from typing import Any

from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk

from dlmm_position_lab.embeddings import embedding_dimensions
from dlmm_position_lab.ingestion import DocumentationChunk

DEFAULT_ELASTICSEARCH_URL = "http://elasticsearch:9200"
DEFAULT_INDEX_NAME = "meteora_docs"
EMBEDDING_MAPPING = {
    "type": "dense_vector",
    "dims": embedding_dimensions(),
    "index": True,
    "similarity": "cosine",
}

INDEX_MAPPINGS = {
    "properties": {
        "id": {"type": "keyword"},
        "title": {"type": "text"},
        "section": {"type": "text"},
        "url": {"type": "keyword"},
        "text": {"type": "text"},
        "embedding": EMBEDDING_MAPPING,
    }
}
INDEX_SETTINGS = {"number_of_shards": 1, "number_of_replicas": 0}


def elasticsearch_url() -> str:
    """Return the configured Elasticsearch endpoint."""
    return os.getenv("ELASTICSEARCH_URL", DEFAULT_ELASTICSEARCH_URL)


def create_client(url: str | None = None) -> Elasticsearch:
    """Create an Elasticsearch client for the configured service."""
    return Elasticsearch(url or elasticsearch_url(), request_timeout=30)


def ensure_index(client: Any, index_name: str = DEFAULT_INDEX_NAME) -> bool:
    """Create the documentation index when absent; return whether it was created."""
    if client.indices.exists(index=index_name):
        client.indices.put_mapping(
            index=index_name,
            properties={"embedding": EMBEDDING_MAPPING},
        )
        return False
    client.indices.create(
        index=index_name,
        mappings=INDEX_MAPPINGS,
        settings=INDEX_SETTINGS,
    )
    return True


def build_index_actions(
    chunks: Iterable[DocumentationChunk],
    index_name: str = DEFAULT_INDEX_NAME,
    embeddings: list[list[float]] | None = None,
) -> list[dict[str, object]]:
    """Build stable-ID bulk index actions that overwrite records on reruns."""
    chunk_list = list(chunks)
    if embeddings is not None and len(embeddings) != len(chunk_list):
        raise ValueError("chunks and embeddings must have the same length")

    actions: list[dict[str, object]] = []
    for position, chunk in enumerate(chunk_list):
        source: dict[str, object] = {
            "id": chunk.id,
            "title": chunk.title,
            "section": chunk.section,
            "url": chunk.url,
            "text": chunk.text,
        }
        if embeddings is not None:
            source["embedding"] = embeddings[position]
        actions.append(
            {
                "_op_type": "index",
                "_index": index_name,
                "_id": chunk.id,
                "_source": source,
            }
        )
    return actions


def index_documents(
    client: Any,
    chunks: list[DocumentationChunk],
    index_name: str = DEFAULT_INDEX_NAME,
    embeddings: list[list[float]] | None = None,
) -> int:
    """Create the index if needed and bulk upsert all documentation chunks."""
    ensure_index(client, index_name)
    if not chunks:
        return 0
    indexed, _ = bulk(
        client,
        build_index_actions(chunks, index_name, embeddings),
        refresh="wait_for",
        raise_on_error=True,
    )
    return indexed


def document_count(client: Any, index_name: str = DEFAULT_INDEX_NAME) -> int:
    """Return zero for a missing index or its current document count."""
    if not client.indices.exists(index=index_name):
        return 0
    response = client.count(index=index_name)
    return int(response["count"])
