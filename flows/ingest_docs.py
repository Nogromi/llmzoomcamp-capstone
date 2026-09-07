"""Download official DLMM Markdown pages and rebuild the search index."""

import hashlib
import json
import re
import unicodedata
from pathlib import Path

import httpx
from elasticsearch.helpers import bulk

from dlmm_position_lab.retrieval import (
    EMBEDDING_DIMENSIONS,
    INDEX_NAME,
    create_client,
    embed_texts,
)

DOCS_INDEX = "https://docs.meteora.ag/llms.txt"
DLMM_PREFIX = "https://docs.meteora.ag/core-products/dlmm/"


def clean_text(text: str) -> str:
    # Remove page markup and styling while keeping link labels as searchable text.
    text = re.sub(r"!\[[^]]*\]\([^)]+\)", "", text)
    text = re.sub(r"\[([^]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\b(?:math|text)\s+theme=\{[\"']system[\"']\}\s*", "", text)
    text = re.sub(r"^\s*(?:[-*+]|\d+[.)])\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"[*_]{1,2}([^*_]+)[*_]{1,2}", r"\1", text).replace("`", "")
    text = "".join(c for c in text if unicodedata.category(c) != "Cf")
    return " ".join(text.split())


def split_text(text: str) -> list[str]:
    """Chunks of up to 900 characters with 20 words of overlap."""
    words, chunks, start = text.split(), [], 0
    while start < len(words):
        end, length = start, 0
        while end < len(words):
            added = len(words[end]) + (end > start)
            if end > start and length + added > 900:
                break
            length += added
            end += 1
        chunks.append(" ".join(words[start:end]))
        if end == len(words):
            break
        # Keep context across chunk boundaries, but always advance past a word.
        start = max(start + 1, end - 20)
    return chunks


def parse_document(markdown: str, url: str) -> list[dict]:
    # Strip YAML metadata before interpreting Markdown headings.
    markdown = re.sub(
        r"\A---\s*\n.*?\n---\s*\n", "", markdown, count=1, flags=re.DOTALL
    )
    title = re.search(r"^#\s+(.+?)\s*#*\s*$", markdown, re.MULTILINE)
    source_url = url.removesuffix(".md")
    title = clean_text(title.group(1)) if title else source_url
    parts = re.split(r"^#{1,6}\s+(.+?)\s*#*\s*$", markdown, flags=re.MULTILINE)
    sections = []
    # The captured headings alternate with their bodies in re.split's output.
    for heading, body in zip(parts[1::2], parts[2::2]):
        text = clean_text(body)
        if text and text.casefold().rstrip(".! ") not in {
            "was this page helpful?",
            "copy page",
            "ask ai",
            "on this page",
            "previous",
            "next",
        }:
            sections.append((clean_text(heading), text))
    if not sections:
        raise ValueError(f"No documentation sections found at {url}")
    chunks = []
    for section_number, (section, text) in enumerate(sections):
        for chunk_number, chunk in enumerate(split_text(text)):
            # Evaluation labels use these IDs; section or chunk shifts can change them.
            location = f"{source_url}\n{section_number}\n{section}\n{chunk_number}"
            chunks.append(
                {
                    "id": hashlib.sha256(location.encode()).hexdigest()[:24],
                    "title": title,
                    "section": section,
                    "url": source_url,
                    "text": chunk,
                }
            )
    return chunks


def ingest_meteora_docs() -> None:
    with httpx.Client(timeout=30, follow_redirects=True) as http:
        response = http.get(DOCS_INDEX)
        response.raise_for_status()
        urls = list(
            dict.fromkeys(
                url
                for url in re.findall(r"\[[^]]+\]\((https://[^)]+)\)", response.text)
                if url.startswith(DLMM_PREFIX)
            )
        )
        if not urls:
            raise ValueError("No DLMM pages found in the documentation index.")
        chunks = []
        for url in urls:
            print(f"Downloading {url}")
            response = http.get(url if url.endswith(".md") else f"{url}.md")
            response.raise_for_status()
            chunks.extend(parse_document(response.text, url))

    # Finish downloads and embeddings before replacing the existing index.
    vectors = embed_texts(
        [f"{c['title']}\n{c['section']}\n{c['text']}" for c in chunks]
    )
    if len(vectors) != len(chunks):
        raise RuntimeError("The number of embeddings does not match the chunks.")
    with create_client() as client:
        client.indices.delete(index=INDEX_NAME, ignore_unavailable=True)
        client.indices.create(
            index=INDEX_NAME,
            settings={"number_of_shards": 1, "number_of_replicas": 0},
            mappings={
                "properties": {
                    "id": {"type": "keyword"},
                    "url": {"type": "keyword"},
                    "title": {"type": "text"},
                    "section": {"type": "text"},
                    "text": {"type": "text"},
                    "embedding": {
                        "type": "dense_vector",
                        "dims": EMBEDDING_DIMENSIONS,
                        "index": True,
                        "similarity": "cosine",
                    },
                }
            },
        )
        bulk(
            client,
            [
                {
                    "_index": INDEX_NAME,
                    "_id": chunk["id"],
                    "_source": {**chunk, "embedding": vector},
                }
                for chunk, vector in zip(chunks, vectors, strict=True)
            ],
            refresh="wait_for",
        )
    # Save an inspectable snapshot; chat retrieves from Elasticsearch, not this file.
    output = Path("data/documents.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(chunks, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(f"Indexed {len(chunks)} chunks from {len(urls)} pages. Saved {output}.")


if __name__ == "__main__":
    ingest_meteora_docs()
