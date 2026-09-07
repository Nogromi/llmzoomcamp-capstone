# DLMM Position Lab

A small LLM Zoomcamp project for learning how Meteora DLMM pools work. Ask questions against official documentation, look up current pool data, and explore a price range using your own observations.

Built with Python, Streamlit, Elasticsearch, OpenAI, and SQLite. Pool access is read-only; the app gives educational explanations, not investment recommendations.

## System Architecture & Workflow

```mermaid
flowchart TD
    Docs[Official Meteora Markdown docs] --> Ingest[Download, clean, chunk]
    Ingest --> JSON[data/documents.json]
    Ingest --> Embed[OpenAI embeddings]
    Embed --> ES[(Elasticsearch)]

    User[Question with pool address or optional default] --> UI[Streamlit]
    UI --> Search[BM25 + vector search]
    ES --> Search
    Search --> RRF[Reciprocal Rank Fusion: top 5 chunks]
    RRF --> LLM[OpenAI with get_pool tool]
    LLM -->|Function call: address argument| Tool[Python executes get_pool]
    Tool --> Pool[Meteora pool API]
    Pool --> Result[Function result linked by call_id]
    Result --> Answer[OpenAI final answer]
    LLM -->|No tool needed| Answer
    Answer --> UI
    UI -->|Requests, latency, feedback| DB[(SQLite)]
    DB --> Monitor[Monitoring page]

    Prices[User-supplied prices + range] --> Calc[Python range calculations]
    Calc --> UI
    Eval[Offline evaluation script] -.-> Search
    Eval -.-> LLM
    Eval -.-> Answer
```

Ingestion discovers DLMM pages from Meteora's `llms.txt`, splits them by heading into roughly 900-character chunks with overlap, then builds the index. Each question retrieves documentation before the model answers or requests `get_pool(address="…")` through native function calling. Python executes the lookup and returns a `function_call_output` with the matching call ID. The model then writes the final answer. The MVP allows one pool lookup per question; the range calculator runs locally without an LLM.

## Run with Docker

Requirements: Docker Compose and an OpenAI API key. Run these commands from the repository root.

```bash
cp .env.example .env
```

Set `OPENAI_API_KEY` in `.env`, then:

```bash
docker compose build app
docker compose up -d --wait elasticsearch
docker compose run --rm app python flows/ingest_docs.py
docker compose up -d app
```

Open [localhost:8501](http://localhost:8501). In Codespaces, open port **8501** from the Ports tab.

Ingestion and chat call OpenAI and incur API costs. Rerunning ingestion rebuilds the documentation index. Rebuild it after changing the embedding model or dimensions.

Stop the app with `docker compose down`. The Elasticsearch volume and local SQLite database persist.

## Run Python locally

Requires Python 3.12+ and `uv`. Create `.env` as above, using `ELASTICSEARCH_URL=http://localhost:9200`.

```bash
uv sync --locked
docker compose up -d --wait elasticsearch
uv run python flows/ingest_docs.py
uv run streamlit run src/dlmm_position_lab/app.py
```

## Demo

Screenshots to be added. Save images in `docs/images/` and uncomment the matching image lines below, or replace them with uploaded image links.

### Documentation chat

Ask **“What is a bin step?”** and expand **Sources** to show the answer and supporting documentation.

<!-- ![Documentation answer with sources](docs/images/chat.png) -->

### Live pool information

Ask **“What is the current TVL of pool YOUR_POOL_ADDRESS?”** with a real address. Capture the answer, pool metrics, and expanded **Function call** panel showing the model's `get_pool` request, address argument, and result.

<!-- ![Current pool information from Meteora](docs/images/pool.png) -->

The model selects the tool and its address argument. An address in the message takes priority over the optional sidebar default. If no address is supplied, the assistant asks for one. See [rag.py](src/dlmm_position_lab/rag.py) for the tool schema and execution flow.

### Documentation and pool data together

Ask **“Explain bin steps and show the bin step for pool YOUR_POOL_ADDRESS.”** Capture the explanation, expanded sources, and current pool metrics in the same response.

<!-- ![Answer combining documentation and current pool data](docs/images/combined.png) -->

### Range calculator

Use **Range lab** with `100, 105, 111, 108, 99` and boundaries `100–110`. Capture the chart and results: **60%** of observations inside the range and **two exits**.

<!-- ![Price range chart and calculated statistics](docs/images/range.png) -->

### Monitoring and tool execution

Rate an answer, then open **Monitoring**. Capture usage, latency, feedback, and the pool request row. `tools_called` lists `get_pool`; `tool_calls` records its call ID, arguments, result, and success or error status. Existing SQLite databases are updated automatically to store this trace.

<!-- ![Monitoring metrics and recorded get_pool execution](docs/images/monitoring.png) -->

Chat history is displayed for the session; each question is answered independently. Repeat the address in a later question or set the optional sidebar default.

## Evaluation

The datasets contain 30 retrieval questions, 5 RAG questions, and 12 tool-selection questions. Compare BM25, vector, and hybrid retrieval with Hit Rate@5 and MRR:

```bash
docker compose run --rm app python evaluation/evaluate.py
```

Include generated-answer and native function-call checks:

```bash
docker compose run --rm app python evaluation/evaluate.py --quality
```

For local Python, use `uv run python evaluation/evaluate.py --quality`.

Results are written to `evaluation/results.json`. RAG checks cover a nonempty answer, sources, valid citation numbers, and an expected document in retrieval. They do not measure factual correctness; inspect the saved answers too. Labels refer to chunk IDs, so review them when source documentation changes.

Tool checks verify whether the model requests `get_pool` and supplies the expected address, including missing addresses and sidebar overrides. Their addresses are synthetic; these selection checks do not execute Meteora API requests. See [saved results](evaluation/results.json). These are small evaluation sets, and model output can vary between runs.

Saved evaluation: hybrid Hit Rate@5 **1.00**, MRR **0.783**, RAG checks **5/5**, native tool-selection checks **12/12**.

## Files

```text
flows/ingest_docs.py                   Download, chunk, embed, and index
src/dlmm_position_lab/
    app.py                            Chat and range UI
    retrieval.py                      Embeddings, BM25, vector search, RRF
    rag.py                            Native get_pool tool and grounded answers
    analytics.py                      Range calculations
    storage.py                        SQLite requests and feedback
    pages/monitoring.py               Usage dashboard
evaluation/
    evaluate.py                       Retrieval, RAG, and tool-call evaluation
    *_questions.json / questions.json Reviewed questions
data/                                 Generated chunks and SQLite database
```

The MVP uses plain scripts and functions, one native function tool, and two Docker services. Its structure follows the small modules in [Yoga Assistant](https://github.com/pranabsarma18/yoga-assistant) and the retrieval, feedback, and evaluation flow in [LifeStyled](https://github.com/thesalmajudah/lifestyled-ai).

## Development note

Parts of this project's code and documentation were developed with help from OpenAI Codex, including the MVP refactor and README updates.
