# LLM Zoomcamp learning outcomes

DLMM Position Lab is designed as an educational capstone, not only as a working application. Each major component has a visible implementation, a reproducible command, tests, and an evaluation artifact so a reviewer can see which LLM engineering skill it demonstrates.

The design follows the concepts in the [LLM Zoomcamp curriculum](https://github.com/DataTalksClub/llm-zoomcamp) while using Meteora DLMM documentation and read-only pool data as an original domain. It does not copy the course FAQ project or hide the core learning outcomes behind a large agent framework.

## Course-to-project mapping

| Course topic | DLMM Position Lab implementation | Evidence for reviewers | Status |
| --- | --- | --- | --- |
| Data ingestion | Prefect discovers official Meteora pages, cleans Markdown, chunks it, saves JSON, and indexes Elasticsearch | Prefect flow logs, `data/documents.json`, ingestion tests | Implemented |
| Keyword search | Elasticsearch BM25 over `title`, `section`, and `text` with explicit boosts | Search CLI, deterministic result model, retrieval tests | Implemented |
| Vector search | OpenAI embeddings stored in Elasticsearch and queried independently | Embedding/index code, vector-search CLI, mocked API tests | Implemented |
| Hybrid search | Separate BM25 and vector candidate sets combined with Reciprocal Rank Fusion | RRF unit tests and BM25/vector/hybrid CLI | Implemented |
| RAG | Hybrid retrieval builds numbered context, the OpenAI Responses API generates a constrained answer, and typed results retain source URLs, retrieved IDs, and latency | Prompt module, RAG CLI, mocked API tests, retrieved IDs and citations | Implemented |
| Function calling and agentic search | A bounded router selects documentation retrieval and/or read-only pool tools; tool calls and trajectory are recorded | Structured decisions, tool schemas, routing tests, trajectory logs | Planned |
| Orchestration | Prefect runs offline ingestion, embedding, indexing, and evaluation workflows | Prefect UI, retries, task logs, documented commands | Partly implemented |
| Retrieval evaluation | A reviewed question set compares BM25, vector, and hybrid retrieval with Hit Rate@5 and MRR | Dataset, reproducible evaluation command, README results table | Planned |
| RAG and agent evaluation | LLM-as-a-judge for answers plus classification/tool-selection accuracy and unnecessary-call rate | Saved answers, tool trajectories, reproducible metrics | Planned |
| User interface | Streamlit pool controls, chat, citations, analytics, and feedback | Usage walkthrough and screenshots | Planned |
| Monitoring | SQLite request/feedback records and a Streamlit dashboard with usage, feedback, latency, errors, categories, and tool calls | Monitoring page with at least five charts, Prefect pipeline monitoring | Planned |
| Reproducibility | Docker Compose, locked dependencies, `.env.example`, exact commands, generated data rebuild | Clean-start walkthrough and test commands | In progress |

## Educational implementation rules

1. Keep BM25, vector, and hybrid retrieval as separate callable functions. This makes their behavior measurable instead of presenting retrieval as a black box.
2. Keep prompt construction visible in a dedicated module. A reviewer should be able to inspect the context and instructions sent to the model.
3. Record retrieved document IDs, router decisions, tool calls, timing, token usage, and errors. Evaluation and monitoring must use real application traces.
4. Use deterministic Python for numerical pool and price-range calculations. The LLM explains calculated results but does not invent or calculate them.
5. Keep the agent bounded. It may choose from documentation search and three read-only pool-analysis tools; it must not trade, sign transactions, or make investment decisions.
6. Evaluate alternatives before selecting the final path. Report BM25, vector, and hybrid retrieval metrics, then use the best measured approach in RAG.
7. Preserve reproducible artifacts: reviewed evaluation questions, metric outputs, example answers, and documented commands belong in the repository.
8. Add tests and update the README after every milestone. Do not create empty placeholder modules for future work.

## Planned learning sequence

The implementation order intentionally mirrors the way the concepts build on one another:

1. BM25 keyword search over the indexed documentation.
2. Embeddings and independent vector search.
3. Hybrid retrieval with Reciprocal Rank Fusion.
4. Grounded documentation RAG with citations.
5. Read-only Meteora API tools and deterministic range analytics.
6. Structured routing and bounded function calling.
7. Streamlit application flow.
8. Retrieval, RAG, and agent evaluation.
9. Persistent user feedback and online monitoring.
10. Final clean-environment reproduction and documented results.

Prefect is used instead of the curriculum's current Kestra orchestration example because the capstone specification selected Prefect and the course project guidelines allow alternative ingestion tools. SQLite is used instead of PostgreSQL for application traces because the expected traffic is small and a single-file database keeps peer review reproducible. Both choices must remain clearly explained rather than treated as assumed knowledge.
