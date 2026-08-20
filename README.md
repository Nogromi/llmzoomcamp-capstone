# DLMM Position Lab

DLMM Position Lab is an educational LLM Zoomcamp capstone about Meteora's Dynamic Liquidity Market Maker (DLMM) pools on Solana. The finished application will combine official documentation retrieval with read-only pool analytics. Milestone 7 provides reproducible ingestion, independent BM25/vector/hybrid retrieval, and grounded documentation answers with citations; it does not yet include pool analysis.

The project is deliberately structured to demonstrate the skills taught in [DataTalksClub's LLM Zoomcamp](https://github.com/DataTalksClub/llm-zoomcamp): keyword and vector retrieval, hybrid search, grounded RAG, function calling, evaluation, feedback, and monitoring. The [course-alignment document](docs/course_alignment.md) maps every learning outcome to concrete code, tests, commands, and reviewer evidence without claiming unfinished features are complete.

## Educational goals

- Show the full path from source documentation to searchable chunks and grounded answers.
- Keep BM25, vector, and hybrid retrieval separate so they can be compared quantitatively.
- Expose prompts, retrieved context, router decisions, tool calls, and latency rather than hiding them behind a framework.
- Evaluate retrieval with Hit Rate@5 and MRR, and evaluate answers and agent trajectories separately.
- Collect real user feedback and display at least five useful monitoring charts.
- Make every result reproducible through Docker Compose and documented commands.

## Current architecture

```text
Official Meteora DLMM pages
             |
             v
   Prefect ingestion flow
   download -> parse -> clean
      -> section -> chunk
             |
             v
     data/documents.json
             |
             v
   Elasticsearch: meteora_docs
             |
             v
       BM25 retrieval
       Vector retrieval
             |
             v
      RRF hybrid retrieval
             |
             v
     numbered RAG context
             |
             v
 OpenAI Responses API -> answer + sources
```

The Prefect flow coordinates HTTP downloads and deterministic processing. It first reads Meteora's official `llms.txt` documentation index and discovers links under its `## Docs` heading. It selects the core DLMM Markdown pages, then pure Python code removes markup and boilerplate, preserves meaningful heading-based sections, and creates retrieval chunks. The flow saves those chunks as JSON and bulk upserts them into the `meteora_docs` Elasticsearch index. Beautiful Soup remains available for explicit HTML URL overrides. Prefect's UI records flow/task activity and retries.

## Technology stack

- Python 3.12 and `uv` for the application and locked dependencies
- Docker and Docker Compose for a reproducible reviewer environment
- Prefect 3 for ingestion orchestration, retry visibility, and logs
- `httpx` for timeout-aware HTTP requests
- Beautiful Soup for lightweight HTML parsing
- Elasticsearch stores the chunks in a searchable, persistent index; stable document IDs make ingestion idempotent
- Streamlit is present but is not extended by this milestone

## Prerequisites

- Git
- Docker with Docker Compose

A local Python or `uv` installation is not required for the Docker workflow.

## Setup and start

```bash
git clone <repository-url>
cd llmzoomcamp-capstone
cp .env.example .env
docker compose up --build
```

This starts Streamlit at <http://localhost:8501>, Prefect at <http://localhost:4200>, and Elasticsearch at <http://localhost:9200>. Container-to-container URLs use the Compose service names, not `localhost`. Compose waits for Elasticsearch's health check before starting the app or a one-off app command.

Verify the running services in another terminal:

```bash
docker compose ps
curl http://localhost:4200/api/health
curl http://localhost:9200
```

## Ingest Meteora documentation

The source of truth is Meteora's official [`llms.txt` documentation index](https://docs.meteora.ag/llms.txt). The pipeline reads links under `## Docs` and selects URLs beginning with `https://docs.meteora.ag/core-products/dlmm/`. This automatically includes the current core DLMM pages without maintaining a duplicate hardcoded list. It downloads the clean Markdown representation of each page with a 30-second timeout and Prefect retries, splits it by headings, removes site boilerplate and invisible Unicode formatting, creates deterministic overlapping chunks, assigns stable SHA-256-based IDs, and writes JSON.

With the services running, execute:

```bash
docker compose run --rm app \
  uv run python flows/ingest_docs.py
```

The `app` service bind-mounts `./data`, so the output remains on the host after the one-off container exits:

```text
data/documents.json
```

Each entry contains `id`, `title`, `section`, `url`, and `text`. The same fields are bulk indexed into Elasticsearch using each stable chunk ID as `_id`. Rerunning ingestion overwrites matching records rather than creating duplicates. Verify JSON generation succeeded with:

```bash
test -s data/documents.json && python -m json.tool data/documents.json >/dev/null
```

The generated file is intentionally ignored by Git because the command above reproduces it from official sources.

Verify Elasticsearch indexing with:

```bash
docker compose run --rm app \
  uv run python -m dlmm_position_lab.index_status
```

Expected output has the current count, for example:

```text
Index: meteora_docs
Documents: 87
```

The exact count may change when Meteora updates its documentation.

### Rebuild the Elasticsearch index from scratch

Delete only the generated documentation index, then rerun the flow:

```bash
curl -X DELETE http://localhost:9200/meteora_docs

docker compose run --rm app \
  uv run python flows/ingest_docs.py
```

Elasticsearch creates the index automatically with explicit mappings for `id`, `title`, `section`, `url`, and `text`.

### What is `./data/documents.json`?

`./` means the repository root, so `./data/documents.json` is a regular JSON file inside this project's `data` directory. It is the generated local knowledge-base dataset: one object per documentation chunk, with its source URL and headings preserved. The ingestion flow indexes these chunks into Elasticsearch after writing the file. It is not an Elasticsearch database, does not contain secrets, and can be safely regenerated by rerunning ingestion.

The JSON file is the reproducible intermediate artifact; Elasticsearch is the indexed service copy used by later search milestones. This separation lets a reviewer inspect the processed data before indexing it.

## Search the documentation with BM25

Milestone 4 implements keyword retrieval with Elasticsearch's BM25 ranking. The query searches all useful text fields while making exact matches in page titles and section headings more influential:

```text
section^3, title^2, text
```

Exact phrases in section headings and body text receive additional boosts. This prevents generic page titles from outranking a section that directly explains the requested concept. The query structure remains visible in `retrieval.py` so it can be tuned later using retrieval-evaluation metrics.

Run a search after ingestion:

```bash
docker compose run --rm app \
  uv run python -m dlmm_position_lab.search \
  "What is an active bin?"
```

Use `--limit` to change the default five results:

```bash
docker compose run --rm app \
  uv run python -m dlmm_position_lab.search \
  "How do dynamic fees work?" --limit 3
```

Each result prints its rank, BM25 score, page title, section, source URL, and a text excerpt. The application-level function is:

```python
from dlmm_position_lab.retrieval import bm25_search

results = bm25_search("What is a bin step?", limit=5)
```

BM25 is intentionally kept separate from the planned vector and hybrid retrievers so all three can be evaluated independently.

## Search with OpenAI embeddings

The ingestion flow uses `text-embedding-3-small` to generate a 512-dimensional vector for each chunk and stores it in Elasticsearch's indexed `dense_vector` field. The embedded input includes the page title, section heading, and chunk text. According to the [official OpenAI embeddings API](https://developers.openai.com/api/reference/resources/embeddings/methods/create), the API accepts a batch of input strings and third-generation embedding models support a configurable output dimension.

Set the API key in `.env` before ingestion:

```text
OPENAI_API_KEY=your-key
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
OPENAI_EMBEDDING_DIMENSIONS=512
```

Then regenerate the index so every document has an embedding:

```bash
docker compose run --rm app \
  uv run python flows/ingest_docs.py
```

Run semantic search independently of BM25:

```bash
docker compose run --rm app \
  uv run python -m dlmm_position_lab.search \
  "fees that increase when markets become volatile" \
  --method vector --limit 5
```

The Python entry point is deliberately separate:

```python
from dlmm_position_lab.retrieval import vector_search

results = vector_search("fees that react to volatility", limit=5)
```

Changing `OPENAI_EMBEDDING_DIMENSIONS` after the Elasticsearch index exists requires deleting and rebuilding `meteora_docs`, because Elasticsearch vector dimensions are fixed in the field mapping.

## Hybrid search with Reciprocal Rank Fusion

Hybrid search retrieves the top 10 BM25 candidates and the top 10 vector candidates independently. It combines their ranks rather than their raw scores, because a BM25 score and a cosine-based vector score are not directly comparable.

For each document at one-based rank `r`, Reciprocal Rank Fusion adds:

```text
1 / (60 + r)
```

A document found by both retrievers receives contributions from both rankings. Results are deduplicated by stable document ID and ordered by their combined RRF score.

Run hybrid retrieval with:

```bash
docker compose run --rm app \
  uv run python -m dlmm_position_lab.search \
  "Why can narrow liquidity ranges be risky?" \
  --method hybrid --limit 5
```

The independent Python entry points remain available for the later evaluation:

```python
from dlmm_position_lab.hybrid_search import hybrid_search
from dlmm_position_lab.retrieval import bm25_search, vector_search
```

## Ask a grounded documentation question

The RAG path retrieves five hybrid-search results, formats them as numbered context, and calls the OpenAI Responses API. The system prompt requires answers to use only that context, include inline citations such as `[1]`, state when the documentation is insufficient, and avoid financial advice. The returned typed result contains the answer, source metadata, retrieved document IDs, and end-to-end latency.

Set `OPENAI_API_KEY` in `.env`, ingest the documentation with embeddings, then run:

```bash
docker compose run --rm app \
  uv run python -m dlmm_position_lab.ask \
  "What is a bin step?"
```

The command prints the grounded answer followed by the numbered title, section, and official URL for every retrieved source. `OPENAI_CHAT_MODEL` defaults to `gpt-5-mini` and can be changed in `.env`. The implementation follows the [official OpenAI Responses API pattern](https://developers.openai.com/api/docs/guides/latest-model), including `client.responses.create(...)` and `response.output_text`.

### Configuring source URLs

By default, source URLs are discovered from `llms.txt`. Override discovery without editing code by passing a comma-separated environment variable:

```bash
docker compose run --rm \
  -e METEORA_DOC_URLS="https://docs.meteora.ag/core-products/dlmm/what-is-dlmm" \
  app uv run python flows/ingest_docs.py
```

The explicit override is useful for a small test run or if the documentation index is temporarily unavailable. Only official Meteora documentation URLs should be used for the project knowledge base.

## Tests and linting

The deterministic test suite covers ingestion, index idempotency, BM25 queries, OpenAI embedding batching, vector persistence, Elasticsearch kNN construction, RRF scoring and deduplication, prompt construction, grounded answer metadata, result parsing, and input validation. External APIs are mocked in unit tests.

```bash
docker compose run --rm app uv run pytest
docker compose run --rm app uv run ruff check .
```

## Project structure

```text
flows/ingest_docs.py                    Prefect tasks and flow
src/dlmm_position_lab/ingestion.py      download, parsing, chunking, JSON output
src/dlmm_position_lab/indexing.py       index mapping and bulk upserts
src/dlmm_position_lab/index_status.py   index verification command
src/dlmm_position_lab/models.py         typed application result models
src/dlmm_position_lab/embeddings.py     OpenAI embedding batches and configuration
src/dlmm_position_lab/retrieval.py      BM25 retrieval implementation
src/dlmm_position_lab/hybrid_search.py  Reciprocal Rank Fusion
src/dlmm_position_lab/search.py         BM25/vector/hybrid inspection CLI
src/dlmm_position_lab/prompts.py        visible grounded-answer prompts
src/dlmm_position_lab/rag.py            retrieval and answer generation
src/dlmm_position_lab/ask.py            grounded-answer CLI
src/dlmm_position_lab/app.py            current Streamlit entry point
tests/test_ingestion.py                 deterministic ingestion tests
tests/test_indexing.py                  mocked Elasticsearch tests
tests/test_retrieval.py                 BM25 query and result tests
tests/test_embeddings.py                mocked OpenAI embedding tests
tests/test_hybrid_search.py             RRF scoring and deduplication tests
tests/test_prompts.py                   prompt and context formatting tests
tests/test_rag.py                       mocked Responses API and metadata tests
data/documents.json                     generated knowledge-base input
compose.yaml                            app, Prefect, and Elasticsearch services
```

## Troubleshooting

- If a documentation request fails temporarily, Prefect retries it three times. Check the flow run at <http://localhost:4200>.
- If `data/documents.json` is missing, run the ingestion command from the repository root and inspect the container logs.
- If `meteora_docs` is empty, confirm Elasticsearch is healthy and rerun ingestion; saving JSON alone does not prove indexing completed.
- If Prefect or Elasticsearch is still starting, wait a few seconds and repeat the health checks.
- If a port is already in use, stop the conflicting local service before starting Compose.

## Milestone status

Milestone 7 is the current scope. Grounded documentation RAG is implemented. Meteora's pool API, analytics, agent routing, feedback, monitoring, and evaluation are intentionally deferred to later milestones.
