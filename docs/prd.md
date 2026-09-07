# DLMM Position Lab PRD

DLMM Position Lab is an educational LLM application about Meteora's Dynamic
Liquidity Market Maker. It demonstrates ingestion, search, RAG, routing,
evaluation, feedback, monitoring, and one read-only external API tool.

## Product boundaries

- Educational explanations, not financial advice.
- Official Meteora documentation is the RAG source.
- The only external tool is `get_pool(pool_address)`.
- No wallets, transactions, trading, or write operations.
- Prefer small, inspectable implementations over exhaustive edge-case handling.

## Implemented milestones

1. **Project foundation** — Python, `uv`, Docker Compose, tests, and linting.
2. **Documentation ingestion** — discover DLMM links from Meteora `llms.txt`,
   parse meaningful sections, clean boilerplate, and create stable chunks.
3. **Indexing** — save inspectable JSON and idempotently index Elasticsearch.
4. **BM25 search** — weighted keyword retrieval over title, section, and text.
5. **Vector search** — OpenAI embeddings and Elasticsearch kNN retrieval.
6. **Hybrid search** — Reciprocal Rank Fusion over separate BM25/vector results.
7. **Grounded RAG** — numbered context, inline citations, source metadata, and
   token/latency observations.
8. **Deterministic analytics** — calculate simple price-range statistics in
   Python rather than asking the LLM to perform arithmetic.
9. **Structured router** — classify documentation, pool-data, and combined
   questions with a validated Pydantic schema.
10. **Streamlit application** — chat, sources, router trace, pool input, range
    lab, feedback controls, and monitoring navigation.
11. **Retrieval evaluation** — 30 reviewed questions with Hit Rate@5 and MRR
    for BM25, vector, and hybrid retrieval.
12. **RAG and router evaluation** — simple deterministic RAG checks for a
    non-empty answer, sources, inline citations, and expected retrieval; router
    accuracy, unnecessary-tool rate, and failure rate. An LLM judge is
    intentionally out of scope.
13. **Feedback** — SQLite persistence for thumbs up/down, an optional comment,
    and request metadata.
14. **Monitoring** — SQLite request traces plus a Streamlit page for traffic,
    feedback, latency, errors, categories, and `get_pool` selection.
15. **Meteora integration** — one read-only `get_pool(pool_address)` client with
    typed models, timeout, retry, explicit errors, mocked HTTP tests, router
    execution, and UI display.

## Reproducible artifacts

- `data/documents.json`: generated documentation chunks.
- Elasticsearch `meteora_docs`: searchable copy with embeddings.
- `evaluation/questions.json`: retrieval labels.
- `evaluation/results.json`: retrieval metrics.
- `evaluation/rag_questions.json`: simple end-to-end RAG cases.
- `evaluation/router_questions.json`: reviewed route labels.
- `evaluation/quality_results.json`: RAG validation and router metrics.
- `data/application.db`: local request and feedback records (generated and
  ignored by Git).

Prefect exposes ingestion and evaluation task runs. SQLite is sufficient for
this small educational application and keeps local reproduction simple.
