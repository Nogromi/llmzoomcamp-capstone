FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:0.12 /uv /uvx /bin/

WORKDIR /app

ENV PYTHONUNBUFFERED=1
ENV UV_LINK_MODE=copy

COPY pyproject.toml uv.lock README.md ./

RUN uv sync --locked --no-install-project

COPY src ./src
COPY flows ./flows
COPY evaluation ./evaluation
COPY tests ./tests

RUN uv sync --locked

ENV PATH="/app/.venv/bin:$PATH"

CMD [
    "uv",
    "run",
    "streamlit",
    "run",
    "src/dlmm_position_lab/app.py",
    "--server.address=0.0.0.0",
    "--server.port=8501"
]