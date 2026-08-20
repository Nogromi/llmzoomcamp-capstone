"""Prefect flow for downloading and chunking Meteora DLMM documentation."""

from pathlib import Path

from prefect import flow, get_run_logger, task

from dlmm_position_lab.embeddings import embed_texts, embedding_text
from dlmm_position_lab.indexing import create_client, index_documents
from dlmm_position_lab.ingestion import (
    DOCUMENTATION_INDEX_URL,
    DocumentationChunk,
    chunk_sections,
    discover_documentation_urls,
    documentation_urls_from_env,
    download_page,
    parse_document,
    save_documents,
)


@task(retries=3, retry_delay_seconds=5, name="download-documentation-page")
def download_documentation_page(url: str) -> str:
    """Download one documentation page, retrying transient HTTP failures."""
    logger = get_run_logger()
    logger.info("Downloading %s", url)
    return download_page(url)


@task(retries=3, retry_delay_seconds=5, name="discover-documentation-pages")
def discover_documentation_pages(index_url: str) -> list[str]:
    """Read Meteora's official index and select its core DLMM documentation."""
    logger = get_run_logger()
    logger.info("Discovering DLMM documentation from %s", index_url)
    urls = discover_documentation_urls(download_page(index_url))
    logger.info("Discovered %d DLMM documentation pages", len(urls))
    return urls


@task(name="parse-and-chunk-page")
def parse_and_chunk_page(url: str, content: str) -> list[DocumentationChunk]:
    """Extract sections from a page and split them into deterministic chunks."""
    page = parse_document(content, url)
    chunks = chunk_sections(page)
    get_run_logger().info(
        "Created %d chunks from %d sections on %s",
        len(chunks),
        len(page.sections),
        url,
    )
    return chunks


@task(name="save-documentation")
def save_documentation(
    chunks: list[DocumentationChunk], output_path: str
) -> None:
    """Write all chunks as reproducible, human-readable JSON."""
    save_documents(chunks, Path(output_path))
    get_run_logger().info("Saved %d chunks to %s", len(chunks), output_path)


@task(retries=3, retry_delay_seconds=5, name="create-document-embeddings")
def create_document_embeddings(chunks: list[DocumentationChunk]) -> list[list[float]]:
    """Generate semantic vectors for every documentation chunk."""
    texts = [embedding_text(chunk.title, chunk.section, chunk.text) for chunk in chunks]
    vectors = embed_texts(texts)
    get_run_logger().info("Generated %d document embeddings", len(vectors))
    return vectors


@task(retries=3, retry_delay_seconds=5, name="index-documentation")
def index_documentation(
    chunks: list[DocumentationChunk], embeddings: list[list[float]]
) -> int:
    """Bulk upsert documentation chunks into Elasticsearch."""
    with create_client() as client:
        indexed = index_documents(client, chunks, embeddings=embeddings)
    get_run_logger().info("Indexed %d chunks into Elasticsearch", indexed)
    return indexed


@flow(name="meteora-docs-ingestion", log_prints=True)
def ingest_meteora_docs(
    urls: list[str] | None = None,
    index_url: str = DOCUMENTATION_INDEX_URL,
    output_path: str = "data/documents.json",
) -> list[DocumentationChunk]:
    """Download, parse, save, and index a configured set of Meteora docs."""
    source_urls = urls or documentation_urls_from_env()
    if not source_urls:
        source_urls = discover_documentation_pages(index_url)
    logger = get_run_logger()
    logger.info("Ingesting %d Meteora documentation pages", len(source_urls))

    all_chunks: list[DocumentationChunk] = []
    for url in source_urls:
        content = download_documentation_page(url)
        all_chunks.extend(parse_and_chunk_page(url, content))

    save_documentation(all_chunks, output_path)
    embeddings = create_document_embeddings(all_chunks)
    index_documentation(all_chunks, embeddings)
    logger.info("Documentation ingestion complete: %d chunks", len(all_chunks))
    return all_chunks


if __name__ == "__main__":
    ingest_meteora_docs()
