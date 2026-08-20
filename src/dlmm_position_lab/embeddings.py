"""OpenAI embedding generation for documentation and search queries."""

from __future__ import annotations

import os
from typing import Any

from openai import OpenAI

DEFAULT_EMBEDDING_MODEL = "text-embedding-3-small"
DEFAULT_EMBEDDING_DIMENSIONS = 512
DEFAULT_EMBEDDING_BATCH_SIZE = 64


def embedding_model() -> str:
    """Return the configured OpenAI embedding model."""
    return os.getenv("OPENAI_EMBEDDING_MODEL", DEFAULT_EMBEDDING_MODEL)


def embedding_dimensions() -> int:
    """Return and validate the configured vector dimensions."""
    dimensions = int(
        os.getenv("OPENAI_EMBEDDING_DIMENSIONS", DEFAULT_EMBEDDING_DIMENSIONS)
    )
    if dimensions <= 0:
        raise ValueError("OPENAI_EMBEDDING_DIMENSIONS must be positive")
    return dimensions


def create_openai_client() -> OpenAI:
    """Create an OpenAI client, failing clearly when its API key is absent."""
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is required to generate embeddings")
    return OpenAI()


def embed_texts(
    texts: list[str],
    *,
    client: Any | None = None,
    model: str | None = None,
    dimensions: int | None = None,
    batch_size: int = DEFAULT_EMBEDDING_BATCH_SIZE,
) -> list[list[float]]:
    """Embed non-empty texts in stable batches and preserve input order."""
    if not texts:
        return []
    if any(not text.strip() for text in texts):
        raise ValueError("embedding input must not be empty")
    if batch_size <= 0:
        raise ValueError("batch_size must be positive")

    embedding_client = client or create_openai_client()
    selected_model = model or embedding_model()
    selected_dimensions = dimensions or embedding_dimensions()
    vectors: list[list[float]] = []

    for start in range(0, len(texts), batch_size):
        response = embedding_client.embeddings.create(
            input=texts[start : start + batch_size],
            model=selected_model,
            dimensions=selected_dimensions,
            encoding_format="float",
        )
        ordered_data = sorted(response.data, key=lambda item: item.index)
        vectors.extend([list(item.embedding) for item in ordered_data])

    if len(vectors) != len(texts):
        raise RuntimeError("OpenAI returned an unexpected number of embeddings")
    return vectors


def embedding_text(title: str, section: str, text: str) -> str:
    """Combine searchable fields into one semantic representation."""
    return f"{title}\n{section}\n{text}"
