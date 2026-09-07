"""SQLite request logs and one rating per response."""

import json
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path


@contextmanager
def connect():
    path = Path(os.getenv("APP_DB_PATH", "data/application.db"))
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    try:
        connection.executescript("""
            CREATE TABLE IF NOT EXISTS requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id TEXT NOT NULL DEFAULT '',
                question TEXT NOT NULL, question_type TEXT,
                retrieved_document_ids TEXT NOT NULL DEFAULT '[]',
                tools_called TEXT NOT NULL DEFAULT '[]',
                total_latency_ms REAL NOT NULL DEFAULT 0,
                input_tokens INTEGER NOT NULL DEFAULT 0,
                output_tokens INTEGER NOT NULL DEFAULT 0,
                error TEXT, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT, request_id INTEGER NOT NULL,
                conversation_id TEXT NOT NULL DEFAULT '', question TEXT NOT NULL,
                answer TEXT NOT NULL, rating INTEGER NOT NULL,
                comment TEXT NOT NULL DEFAULT '', pool_address TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
        """)
        columns = {
            row["name"] for row in connection.execute("PRAGMA table_info(requests)")
        }
        if "tool_calls" not in columns:
            connection.execute(
                "ALTER TABLE requests ADD COLUMN tool_calls TEXT NOT NULL DEFAULT '[]'"
            )
        with connection:
            yield connection
    finally:
        connection.close()


def record_request(question: str, response: dict, error: str = "") -> int:
    with connect() as db:
        cursor = db.execute(
            """
            INSERT INTO requests (
                conversation_id, question, question_type, retrieved_document_ids,
                tools_called, total_latency_ms, input_tokens, output_tokens, error, tool_calls
            ) VALUES ('', ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                question,
                response.get("route"),
                json.dumps([doc["id"] for doc in response.get("sources", [])]),
                json.dumps([call["name"] for call in response.get("tool_calls", [])]),
                response.get("latency_ms", 0),
                response.get("input_tokens", 0),
                response.get("output_tokens", 0),
                error or response.get("notice", ""),
                json.dumps(response.get("tool_calls", [])),
            ),
        )
        return cursor.lastrowid


def save_feedback(request_id: int, question: str, answer: str, rating: int) -> None:
    if rating not in {-1, 1}:
        raise ValueError("Rating must be -1 or 1.")
    with connect() as db:
        db.execute("DELETE FROM feedback WHERE request_id = ?", (request_id,))
        db.execute(
            """
            INSERT INTO feedback (request_id, conversation_id, question, answer, rating)
            VALUES (?, '', ?, ?, ?)
        """,
            (request_id, question, answer, rating),
        )


def load_monitoring() -> tuple[list[dict], list[dict]]:
    with connect() as db:
        requests = [
            dict(row) for row in db.execute("SELECT * FROM requests ORDER BY id")
        ]
        feedback = [
            dict(row) for row in db.execute("SELECT * FROM feedback ORDER BY id")
        ]
    return requests, feedback
