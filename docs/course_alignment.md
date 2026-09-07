# LLM Zoomcamp learning outcomes

DLMM Position Lab applies the LLM Zoomcamp concepts to Meteora DLMM. The core
steps are deliberately visible and independently testable instead of hidden
behind a large agent framework.

## Course-to-project mapping

| Course topic | Implementation and reviewer evidence | Status |
| --- | --- | --- |
| Data ingestion | Prefect discovers official pages, cleans Markdown, chunks by meaningful headings, saves JSON, and indexes Elasticsearch | Implemented |
| Keyword search | Explicit Elasticsearch BM25 query over `title`, `section`, and `text` | Implemented |
| Vector search | OpenAI embeddings stored in an Elasticsearch `dense_vector` and queried with kNN | Implemented |
| Hybrid search | Independent BM25/vector candidates combined with Reciprocal Rank Fusion | Implemented |
| RAG | Numbered hybrid context, constrained prompt, inline citations, source URLs, IDs, latency, and tokens | Implemented |
| Agentic routing | Structured model output selects documentation RAG and/or the single `get_pool` tool | Implemented |
| Function/tool use | Service executes only read-only `get_pool(pool_address)` when selected and an address is supplied | Implemented |
| Deterministic analytics | Python calculates price-range statistics; the LLM does not perform the arithmetic | Implemented |
| Retrieval evaluation | 30 reviewed questions compare BM25, vector, and hybrid with Hit Rate@5 and MRR | Implemented |
| RAG evaluation | Five reviewed cases check answer, sources, inline citation, and expected retrieved document | Implemented (simple validation) |
| Router evaluation | Reviewed labels measure classification, RAG/tool selection, unnecessary calls, and failures | Implemented |
| Orchestration | Prefect flows expose ingestion and evaluation as observable tasks | Implemented |
| Feedback | Streamlit stores thumbs up/down and optional comments in SQLite | Implemented |
| Monitoring | SQLite traces and a Streamlit dashboard show usage, feedback, latency, errors, categories, and tool selections | Implemented |
| Reproducibility | Docker Compose, locked dependencies, environment template, commands, tests, and saved evaluation results | Implemented |

## Deliberate simplifications

- RAG validation is deterministic and easy to explain; it is not an
  LLM-as-a-judge system and does not claim to measure full semantic quality.
- The agent has one external capability: `get_pool`. Historical data, trading,
  wallets, and additional tools are outside the scope.
- SQLite replaces a server database because expected traffic is small.
- Prefect is used for orchestration because it was selected by this capstone.

These choices keep the project educational: a reviewer can follow ingestion,
retrieval, generation, routing, evaluation, persistence, and monitoring from
the code and reproduce each result. Full requirements are in [the PRD](prd.md).
