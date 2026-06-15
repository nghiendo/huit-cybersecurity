import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterable
from typing import Iterator

from app.config import settings


SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password TEXT NOT NULL,
    role TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS comments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    author TEXT NOT NULL DEFAULT 'student',
    content TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS lab_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    input TEXT NOT NULL,
    detected_type TEXT NOT NULL,
    blocked INTEGER NOT NULL,
    model_score REAL NOT NULL,
    model_time_ms REAL NOT NULL,
    endpoint_time_ms REAL NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""

SEED_USERS = [
    ("admin", "admin123", "admin"),
    ("alice", "wonderland", "analyst"),
    ("bob", "builder", "student"),
    ("eve", "shadow", "researcher"),
    ("mallory", "payloads", "redteam"),
]

SEED_COMMENTS = [
    (
        "student",
        "' OR 1=1--",
        "2026-06-10 08:15:00",
    ),
    (
        "analyst",
        "<script>alert(1)</script>",
        "2026-06-10 08:20:00",
    ),
    (
        "researcher",
        "' UNION SELECT username,password FROM users--",
        "2026-06-10 08:25:00",
    ),
    (
        "student",
        "<img src=x onerror=alert(1)>",
        "2026-06-10 08:27:00",
    ),
]

SEED_LOGS = [
    (
        "' OR 1=1--",
        "sqli",
        0,
        0.76,
        2.1,
        4.9,
        "2026-06-10 08:15:01",
    ),
    (
        "<script>alert(1)</script>",
        "xss",
        1,
        0.93,
        1.8,
        3.7,
        "2026-06-10 08:20:01",
    ),
    (
        "admin",
        "benign",
        0,
        0.02,
        1.2,
        2.6,
        "2026-06-10 08:22:30",
    ),
    (
        "' UNION SELECT username,password FROM users--",
        "sqli",
        1,
        0.97,
        2.4,
        5.3,
        "2026-06-10 08:25:01",
    ),
]


def init_db() -> None:
    db_path = settings.database_path
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(db_path) as conn:
        conn.executescript(SCHEMA)
        seed_demo_data(conn)
        conn.commit()


@contextmanager
def get_connection() -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(settings.database_path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def rows_to_dicts(rows: list[sqlite3.Row]) -> list[dict]:
    return [dict(row) for row in rows]


def _table_is_empty(conn: sqlite3.Connection, table_name: str) -> bool:
    row = conn.execute(f"SELECT COUNT(*) AS count FROM {table_name}").fetchone()
    return bool(row and row[0] == 0)


def _seed_if_empty(
    conn: sqlite3.Connection,
    table_name: str,
    query: str,
    rows: Iterable[tuple],
) -> bool:
    if not _table_is_empty(conn, table_name):
        return False

    conn.executemany(query, rows)
    return True


def seed_demo_data(conn: sqlite3.Connection) -> dict[str, bool]:
    results = {
        "users": _seed_if_empty(
            conn,
            "users",
            "INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
            SEED_USERS,
        ),
        "comments": _seed_if_empty(
            conn,
            "comments",
            "INSERT INTO comments (author, content, created_at) VALUES (?, ?, ?)",
            SEED_COMMENTS,
        ),
        "lab_logs": _seed_if_empty(
            conn,
            "lab_logs",
            """
            INSERT INTO lab_logs (
                input,
                detected_type,
                blocked,
                model_score,
                model_time_ms,
                endpoint_time_ms,
                created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            SEED_LOGS,
        ),
    }
    return results
