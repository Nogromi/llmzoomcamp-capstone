"""Small SQLite store for application traces and user feedback."""

import json
import os
import sqlite3
from pathlib import Path

from dlmm_position_lab.models import ApplicationResponse

DEFAULT_DB_PATH = Path("data/application.db")


def database_path() -> Path:
    return Path(os.getenv("APP_DB_PATH", str(DEFAULT_DB_PATH)))


def connect(path: Path | None = None) -> sqlite3.Connection:
    target = path or database_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(target)
    connection.row_factory = sqlite3.Row
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id TEXT NOT NULL,
            question TEXT NOT NULL,
            question_type TEXT,
            retrieved_document_ids TEXT NOT NULL DEFAULT '[]',
            tools_called TEXT NOT NULL DEFAULT '[]',
            router_latency_ms REAL NOT NULL DEFAULT 0,
            llm_latency_ms REAL NOT NULL DEFAULT 0,
            total_latency_ms REAL NOT NULL DEFAULT 0,
            input_tokens INTEGER NOT NULL DEFAULT 0,
            output_tokens INTEGER NOT NULL DEFAULT 0,
            error TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            request_id INTEGER NOT NULL,
            conversation_id TEXT NOT NULL,
            question TEXT NOT NULL,
            answer TEXT NOT NULL,
            rating INTEGER NOT NULL,
            comment TEXT NOT NULL DEFAULT '',
            pool_address TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        """
    )
    connection.commit()
    return connection


def record_response(
    conversation_id: str,
    response: ApplicationResponse,
    total_latency_ms: float,
    *,
    path: Path | None = None,
) -> int:
    answer = response.answer
    with connect(path) as connection:
        cursor = connection.execute(
            """
            INSERT INTO requests (
                conversation_id, question, question_type,
                retrieved_document_ids, tools_called,
                router_latency_ms, llm_latency_ms, total_latency_ms,
                input_tokens, output_tokens
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                conversation_id,
                response.routing.question,
                response.routing.decision.question_type,
                json.dumps(answer.retrieved_document_ids if answer else []),
                json.dumps(response.routing.decision.tools),
                response.routing.latency_ms,
                answer.latency_ms if answer else 0,
                total_latency_ms,
                response.routing.input_tokens + (answer.input_tokens if answer else 0),
                response.routing.output_tokens + (answer.output_tokens if answer else 0),
            ),
        )
        connection.commit()
        return int(cursor.lastrowid)


def record_error(
    conversation_id: str,
    question: str,
    error: str,
    total_latency_ms: float,
    *,
    path: Path | None = None,
) -> int:
    with connect(path) as connection:
        cursor = connection.execute(
            """
            INSERT INTO requests (
                conversation_id, question, total_latency_ms, error
            ) VALUES (?, ?, ?, ?)
            """,
            (conversation_id, question, total_latency_ms, error),
        )
        connection.commit()
        return int(cursor.lastrowid)


def save_feedback(
    request_id: int,
    conversation_id: str,
    question: str,
    answer: str,
    rating: int,
    comment: str = "",
    pool_address: str = "",
    *,
    path: Path | None = None,
) -> int:
    with connect(path) as connection:
        cursor = connection.execute(
            """
            INSERT INTO feedback (
                request_id, conversation_id, question, answer,
                rating, comment, pool_address
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                request_id,
                conversation_id,
                question,
                answer,
                rating,
                comment,
                pool_address,
            ),
        )
        connection.commit()
        return int(cursor.lastrowid)


def load_requests(path: Path | None = None) -> list[dict[str, object]]:
    with connect(path) as connection:
        rows = connection.execute("SELECT * FROM requests ORDER BY id").fetchall()
    return [dict(row) for row in rows]


def load_feedback(path: Path | None = None) -> list[dict[str, object]]:
    with connect(path) as connection:
        rows = connection.execute("SELECT * FROM feedback ORDER BY id").fetchall()
    return [dict(row) for row in rows]
