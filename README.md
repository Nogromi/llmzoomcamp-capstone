# DLMM Position Lab

DLMM Position Lab is an educational LLM Zoomcamp capstone about Meteora's Dynamic Liquidity Market Maker (DLMM) pools on Solana. It combines official documentation RAG, a structured agentic router, one read-only live pool tool, deterministic analytics, evaluation, feedback, and monitoring.

The project is deliberately structured to demonstrate the skills taught in [DataTalksClub's LLM Zoomcamp](https://github.com/DataTalksClub/llm-zoomcamp): keyword and vector retrieval, hybrid search, grounded RAG, function calling, evaluation, feedback, and monitoring. The [course-alignment document](docs/course_alignment.md) maps every learning outcome to concrete code, tests, commands, and reviewer evidence without claiming unfinished features are complete.

## Educational goals

- Show the full path from source documentation to searchable chunks and grounded answers.
- Keep BM25, vector, and hybrid retrieval separate so they can be compared quantitatively.
- Expose prompts, retrieved context, router decisions, tool calls, and latency rather than hiding them behind a framework.
- Evaluate retrieval with Hit Rate@5 and MRR, then validate RAG output and router decisions separately.
- Collect user feedback and expose useful request metrics in a small monitoring page.
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
             |
             v
 structured router -> documentation RAG / get_pool
             |
             v
 Meteora Data API + SQLite traces/feedback
```

The Prefect flow coordinates HTTP downloads and deterministic processing. It first reads Meteora's official `llms.txt` documentation index and discovers links under its `## Docs` heading. It selects the core DLMM Markdown pages, then pure Python code removes markup and boilerplate, preserves meaningful heading-based sections, and creates retrieval chunks. The flow saves those chunks as JSON and bulk upserts them into the `meteora_docs` Elasticsearch index. Beautiful Soup remains available for explicit HTML URL overrides. Prefect's UI records flow/task activity and retries.

## Technology stack

- Python 3.12 and `uv` for the application and locked dependencies
- Docker and Docker Compose for a reproducible reviewer environment
- Prefect 3 for ingestion orchestration, retry visibility, and logs
- `httpx` for timeout-aware HTTP requests
- Beautiful Soup for lightweight HTML parsing
- Elasticsearch stores the chunks in a searchable, persistent index; stable document IDs make ingestion idempotent
- Streamlit provides routed chat, live pool lookup, feedback, monitoring, and a range lab
- SQLite stores application traces and feedback locally

## Reproduce the project

This is the recommended reviewer workflow. It uses Docker Compose, so Python
and `uv` do not need to be installed on the host.

### Requirements

- Git.
- Docker with the Compose plugin. On macOS, install and start
  [Docker Desktop](https://docs.docker.com/desktop/setup/install/mac-install/).
- An OpenAI API key with access to the model configured in `.env`. Ingestion,
  RAG, routing, and live evaluation make API calls and may incur a small cost.
- At least 4 GB of memory available to Docker; Elasticsearch is configured with
  a 512 MB JVM heap.

Confirm Docker is ready:

```bash
docker --version
docker compose version
docker info
```

### Option A: local machine

Clone the repository and enter its root directory:

```bash
git clone https://github.com/Nogromi/llmzoomcamp-capstone.git
cd llmzoomcamp-capstone
```

Create the local environment file:

```bash
cp .env.example .env
```

Open `.env`, set `OPENAI_API_KEY`, and leave the other defaults unchanged for
the first run:

```text
OPENAI_API_KEY=your-key-here
```

Do not commit `.env`; it is ignored by Git.

### Option B: GitHub Codespaces

1. Open the repository on GitHub.
2. Select **Code → Codespaces → Create codespace on main**. A 4-core machine is
   recommended for Docker and Elasticsearch.
3. Wait for the terminal to open. The repository is already cloned, so run the
   remaining commands from its root directory.
4. For a reusable private setup, add a Codespaces secret named
   `OPENAI_API_KEY` in GitHub. Codespaces injects it into the terminal. Then run
   `cp .env.example .env`; the injected secret takes precedence over the blank
   value in that file. Never commit the key or make forwarded ports public.

The standard Codespaces image includes Docker. Verify it with the same three
Docker commands shown above. If `docker info` is not successful, rebuild the
Codespace before continuing.

### Build, ingest, and start

The following commands are identical on a local machine and in Codespaces.

Build the application image:

```bash
docker compose build app
```

Start Elasticsearch and Prefect in the background:

```bash
docker compose up -d elasticsearch prefect
docker compose ps
```

The first start downloads container images and can take several minutes. Wait
until Elasticsearch is shown as `healthy`, then build the knowledge base from
Meteora's current documentation:

```bash
docker compose run --rm app \
  uv run python flows/ingest_docs.py
```

This downloads the official pages, creates `data/documents.json`, generates
embeddings, and indexes the chunks. Verify the result:

```bash
docker compose run --rm app \
  uv run python -m dlmm_position_lab.index_status
```

Expected output is similar to the following; the count can change when Meteora
updates its documentation:

```text
Index: meteora_docs
Documents: 87
```

Start Streamlit:

```bash
docker compose up -d app
docker compose ps
```

On a local machine, open:

- Streamlit: <http://localhost:8501>
- Prefect: <http://localhost:4200>
- Elasticsearch: <http://localhost:9200>

In Codespaces, open the **Ports** tab and select **Open in Browser** for port
`8501`. Ports `4200` and `9200` expose Prefect and Elasticsearch. Codespaces
assigns forwarded URLs instead of using `localhost` in your browser; keep all
three ports private.

### Reviewer verification checklist

Run the tests and lint checks. Unit tests mock OpenAI and Meteora, but Compose
still starts the service dependencies declared for the app:

```bash
docker compose run --rm app uv run pytest -q
docker compose run --rm app uv run ruff check .
```

The current project has 63 passing tests. Next reproduce the retrieval and
end-to-end quality metrics:

```bash
docker compose run --rm app \
  uv run python evaluation/retrieval.py

docker compose run --rm app \
  uv run python evaluation/quality.py
```

The commands write `evaluation/results.json` and
`evaluation/quality_results.json`. Reviewers can then confirm the main user
flows in Streamlit:

1. Ask `What is a bin step?` and inspect the cited sources and router decision.
2. Enter a valid Meteora DLMM pool address and ask for its current TVL to test
   the single read-only `get_pool` tool.
3. Submit feedback and open **Monitoring** from the sidebar.
4. Use the range lab to verify deterministic calculations and its chart.

The committed result files are the project baseline. A later reproduction can
produce a different document count or slightly different model output because
the ingestion source and OpenAI responses are live. The tests and deterministic
metric calculations should still pass; compare changed evaluation cases in the
generated JSON rather than assuming every numeric value is immutable.

### Stop and restart

Stop the containers without deleting the Elasticsearch and Prefect volumes:

```bash
docker compose down
```

Restart later with:

```bash
docker compose up -d
```

If code or dependencies changed, use `docker compose up -d --build` instead.
Application traces remain in `data/application.db`, and the Elasticsearch index
remains in its named Docker volume after a normal `docker compose down`.

## Use the Streamlit application

Open <http://localhost:8501> after starting the project. The application has two tabs:

- **Documentation chat** routes a question, runs hybrid RAG when appropriate, calls `get_pool` for pool questions when an address is supplied, shows sources, collects feedback, and exposes the router decision.
- **Range lab** accepts chronological closing prices plus lower and upper boundaries, then displays deterministic statistics and a chart.

Try these questions:

```text
What is a bin step?
How do dynamic fees work?
What is the TVL of this pool?
```

The first two produce grounded documentation answers. For the pool question, paste a Meteora DLMM pool address into the sidebar; the application calls the read-only `get_pool` endpoint and displays current pool metadata. In the range lab, the default values are fixtures rather than current market prices.

## Evaluate retrieval

The versioned dataset at `evaluation/questions.json` contains 30 manually reviewed documentation questions and their expected stable chunk IDs. The evaluator runs BM25, vector, and hybrid retrieval over the same questions and reports:

- **Hit Rate@5:** the fraction of questions whose expected chunk appears anywhere in the first five results.
- **MRR:** mean reciprocal rank, which gives more credit when the first expected chunk appears closer to rank 1.

With Elasticsearch populated with embeddings, run:

```bash
docker compose run --rm app \
  uv run python evaluation/retrieval.py
```

The `evaluation` directory is mounted into the app container, so the command saves `evaluation/results.json` on the host.

### Retrieval results

Measured against the current 87-chunk Meteora dataset:

| Retriever | Hit Rate@5 | MRR |
| --- | ---: | ---: |
| BM25 | 0.867 | 0.589 |
| Vector | 1.000 | 0.884 |
| Hybrid RRF | 1.000 | 0.783 |

Vector retrieval ranked the exact reviewed chunk most highly on this dataset. Hybrid matched vector's perfect top-five coverage but had lower MRR, while BM25 missed some paraphrased questions. The RAG flow currently retains hybrid retrieval because Milestone 7 explicitly selected it and it preserves both lexical and semantic evidence; the measured vector advantage is recorded rather than hidden and can guide later tuning.

## Evaluate RAG and routing

The quality evaluator is intentionally simple. For five reviewed RAG questions,
it checks that an answer is non-empty, exposes sources, contains an inline
citation such as `[1]`, and retrieves the expected document ID. This is a
deterministic smoke-quality check, not an LLM judge or a claim of complete
semantic correctness.

Twelve reviewed router cases measure classification, RAG selection, tool
selection, unnecessary tool calls, and failures. Run both sets with:

```bash
docker compose run --rm app \
  uv run python evaluation/quality.py
```

Measured results for the current datasets:

| Check | Result |
| --- | ---: |
| RAG pass / answer / source / citation / expected document | 1.000 each |
| Router classification / RAG selection / tool selection | 1.000 each |
| Unnecessary tool-call / failure rate | 0.000 each |

The command saves the individual outputs and aggregates to
`evaluation/quality_results.json`. To show both evaluation scripts as Prefect
tasks, run `docker compose run --rm app uv run python flows/evaluate.py`.

## Read one live Meteora pool

The only external tool is `get_pool(pool_address)`. It sends a read-only request
to Meteora's `GET /pools/{address}` endpoint and parses a small typed subset:
current price, TVL, dynamic fee, tokens, pool configuration, volume, and fees.
The client has a ten-second timeout, two transport retries, and one explicit API
error type. No historical-data, wallet, transaction, or trading functions are
implemented. See Meteora's [official pool endpoint](https://docs.meteora.ag/api-reference/dlmm/pools/pool).

## Feedback and monitoring

After a successful answer or pool lookup, expand **Rate this response** to save
thumbs up/down and an optional comment. Request traces and feedback are stored
in `data/application.db`, a generated SQLite file. The trace includes route,
retrieved IDs, selected tools, latency, token usage, and errors.

Use **Open monitoring** in the sidebar to inspect total questions, feedback
rate, average and P95 latency, errors, question categories, `get_pool`
selections, and recent requests. Prefect at <http://localhost:4200> separately
shows offline ingestion and evaluation runs.

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

BM25 is intentionally kept separate from the vector and hybrid retrievers so all three can be evaluated independently.

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

The independent Python entry points remain available for evaluation and inspection:

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

## Analyze a hypothetical price range

Range analytics are deterministic Python calculations; they do not use the LLM or live pool data. Pass chronological closing prices and the selected lower and upper boundaries:

```python
from dlmm_position_lab.analytics import analyze_range

result = analyze_range([100, 105, 111, 108, 99], 100, 110)
```

The typed result reports the latest price, whether it is currently inside the range, range width, minimum and maximum, percentage of observations inside, number of transitions out of the range, and signed distance from the latest price to each boundary. Boundary prices count as inside. Inputs remain explicit fixtures or user-provided values, so this lab never presents them as live history.

## Inspect query routing

The bounded router uses the OpenAI Responses API with a Pydantic structured output. It classifies each question into one of three paths:

| Type | Uses documentation RAG | Selected tool |
| --- | --- | --- |
| `documentation` | Yes | None |
| `pool_data` | No | `get_pool` |
| `combined` | Yes | `get_pool` |

Run it independently:

```bash
docker compose run --rm app \
  uv run python -m dlmm_position_lab.route \
  "Explain the fees for this pool"
```

The output shows the question type, whether RAG is needed, selected tools, a short reason, and routing latency. Python validation enforces the table above, so the model cannot introduce another tool or produce an inconsistent route. The application service executes `get_pool(pool_address)` only when the validated route selects it and the user supplied an address.

### Configuring source URLs

By default, source URLs are discovered from `llms.txt`. Override discovery without editing code by passing a comma-separated environment variable:

```bash
docker compose run --rm \
  -e METEORA_DOC_URLS="https://docs.meteora.ag/core-products/dlmm/what-is-dlmm" \
  app uv run python flows/ingest_docs.py
```

The explicit override is useful for a small test run or if the documentation index is temporarily unavailable. Only official Meteora documentation URLs should be used for the project knowledge base.

## Tests and linting

The deterministic test suite covers ingestion, indexing, all retrievers, RAG and router API boundaries, range analytics, quality metrics, the Meteora client, routed service execution, SQLite storage, and Streamlit smoke tests. External APIs are mocked in unit tests.

```bash
docker compose run --rm app uv run pytest
docker compose run --rm app uv run ruff check .
```

## Project structure

```text
flows/ingest_docs.py                    Prefect tasks and flow
flows/evaluate.py                       Prefect evaluation flow
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
src/dlmm_position_lab/analytics.py      deterministic price-range calculations
src/dlmm_position_lab/router.py         typed bounded query router
src/dlmm_position_lab/route.py          router inspection CLI
src/dlmm_position_lab/service.py        routed application workflow
src/dlmm_position_lab/evaluation.py     retrieval metrics and dataset loading
src/dlmm_position_lab/quality_evaluation.py simple RAG/router metrics
src/dlmm_position_lab/meteora_client.py single read-only get_pool client
src/dlmm_position_lab/storage.py        SQLite traces and feedback
src/dlmm_position_lab/app.py            thin Streamlit presentation layer
src/dlmm_position_lab/pages/monitoring.py monitoring dashboard
tests/test_ingestion.py                 deterministic ingestion tests
tests/test_indexing.py                  mocked Elasticsearch tests
tests/test_retrieval.py                 BM25 query and result tests
tests/test_embeddings.py                mocked OpenAI embedding tests
tests/test_hybrid_search.py             RRF scoring and deduplication tests
tests/test_prompts.py                   prompt and context formatting tests
tests/test_rag.py                       mocked Responses API and metadata tests
tests/test_analytics.py                 deterministic range calculation tests
tests/test_router.py                    structured decision and router API tests
tests/test_service.py                   routed workflow tests
tests/test_app.py                       Streamlit and range-lab smoke test
tests/test_evaluation.py                Hit Rate@5, MRR, and dataset tests
tests/test_quality_evaluation.py        RAG validation and router metrics
tests/test_meteora_client.py            mocked Meteora HTTP boundary
tests/test_storage.py                   SQLite request/feedback persistence
evaluation/questions.json               reviewed retrieval questions
evaluation/retrieval.py                 reproducible comparison command
evaluation/results.json                 measured retrieval results
evaluation/rag_questions.json           reviewed RAG validation cases
evaluation/router_questions.json        reviewed router cases
evaluation/quality.py                   RAG/router evaluation command
evaluation/quality_results.json         measured quality results
data/documents.json                     generated knowledge-base input
compose.yaml                            app, Prefect, and Elasticsearch services
```

## Troubleshooting

- If a documentation request fails temporarily, Prefect retries it three times. Check the flow run at <http://localhost:4200>.
- If `data/documents.json` is missing, run the ingestion command from the repository root and inspect the container logs.
- If `meteora_docs` is empty, confirm Elasticsearch is healthy and rerun ingestion; saving JSON alone does not prove indexing completed.
- If Prefect or Elasticsearch is still starting, wait a few seconds and repeat the health checks.
- If a pool lookup fails, verify the pool address and the Meteora API URL in `.env`.
- If a port is already in use, stop the conflicting local service before starting Compose.

## Milestone status

All scoped milestones are implemented. The project includes ingestion, three retrieval methods, grounded RAG, one bounded tool, deterministic analytics, retrieval and quality evaluation, feedback, monitoring, and Docker reproduction. See the [PRD](docs/prd.md) and [course alignment](docs/course_alignment.md).
