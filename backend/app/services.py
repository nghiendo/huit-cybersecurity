from html import escape
from pathlib import Path

ADMIN_TABLE_CONFIG = {
    "users": {
        "table": "users",
        "columns": "id, username, password, role",
        "order_by": "id DESC",
    },
    "comments": {
        "table": "comments",
        "columns": "id, author, content, created_at",
        "order_by": "id DESC",
    },
    "labLogs": {
        "table": "lab_logs",
        "columns": """
            id,
            input,
            detected_type,
            blocked,
            model_score,
            model_time_ms,
            endpoint_time_ms,
            created_at
        """,
        "order_by": "id DESC",
    },
}

from app.database import get_connection


def simulate_sql_analysis(value: str) -> dict:
    normalized = value.lower()
    signals = []

    if "union select" in normalized:
        signals.append("union-based pattern")
    if " or " in normalized or "'or" in normalized:
        signals.append("boolean-bypass pattern")
    if "--" in normalized or "/*" in normalized:
        signals.append("comment-termination pattern")
    if "select" in normalized and "from" in normalized:
        signals.append("query-structure pattern")

    matched_users = []
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT id, username, role FROM users WHERE username = ?",
            (value,),
        ).fetchall()
        matched_users = [dict(row) for row in rows]

    return {
        "mode": "simulated",
        "parameterizedQuery": "SELECT id, username, role FROM users WHERE username = ?",
        "matchedUsers": matched_users,
        "signals": signals,
        "wouldHaveTriggered": bool(signals),
    }

def simulate_xss_analysis(value: str) -> dict:
    normalized = value.lower()
    signals = []

    if "<script" in normalized:
        signals.append("script-tag pattern")
    if "onerror=" in normalized or "onload=" in normalized:
        signals.append("event-handler pattern")
    if "javascript:" in normalized:
        signals.append("javascript-uri pattern")
    if "document.cookie" in normalized:
        signals.append("cookie-access pattern")

    return {
        "mode": "simulated",
        "escapedPreview": escape(value),
        "signals": signals,
        "wouldHaveTriggered": bool(signals),
    }


def append_comment(value: str) -> list[dict]:
    with get_connection() as conn:
        conn.execute("INSERT INTO comments (content) VALUES (?)", (value,))
        conn.commit()
        rows = conn.execute(
            "SELECT id, author, content, created_at FROM comments ORDER BY id DESC LIMIT 10"
        ).fetchall()
        return [dict(row) for row in rows]


def write_lab_log(
    value: str,
    detected_type: str,
    blocked: bool,
    model_score: float,
    model_time_ms: float,
    endpoint_time_ms: float,
) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO lab_logs (
                input,
                detected_type,
                blocked,
                model_score,
                model_time_ms,
                endpoint_time_ms
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                value,
                detected_type,
                int(blocked),
                model_score,
                model_time_ms,
                endpoint_time_ms,
            ),
        )
        conn.commit()


def fetch_admin_table(resource: str, limit: int = 25, offset: int = 0) -> dict:
    if resource not in ADMIN_TABLE_CONFIG:
        raise ValueError(f"Unsupported resource: {resource}")

    config = ADMIN_TABLE_CONFIG[resource]
    query = """
        SELECT
            {columns}
        FROM {table}
        ORDER BY {order_by}
        LIMIT ? OFFSET ?
    """.format(
        columns=config["columns"],
        table=config["table"],
        order_by=config["order_by"],
    )

    with get_connection() as conn:
        total = conn.execute(f"SELECT COUNT(*) FROM {config['table']}").fetchone()[0]
        rows = conn.execute(query, (limit, offset)).fetchall()

    return {
        "resource": resource,
        "rows": [dict(row) for row in rows],
        "pagination": {
            "total": int(total),
            "limit": int(limit),
            "offset": int(offset),
            "returned": len(rows),
            "hasPrevious": offset > 0,
            "hasNext": offset + len(rows) < int(total),
            "page": (offset // limit) + 1 if limit else 1,
            "pageCount": ((int(total) - 1) // limit) + 1 if total and limit else 1,
        },
    }


def summarize_admin_data() -> dict:
    with get_connection() as conn:
        table_counts = {
            "users": conn.execute("SELECT COUNT(*) FROM users").fetchone()[0],
            "comments": conn.execute("SELECT COUNT(*) FROM comments").fetchone()[0],
            "labLogs": conn.execute("SELECT COUNT(*) FROM lab_logs").fetchone()[0],
        }
        log_rows = conn.execute(
            """
            SELECT
                COUNT(*) AS total_requests,
                SUM(CASE WHEN blocked = 1 THEN 1 ELSE 0 END) AS blocked_requests,
                SUM(CASE WHEN blocked = 0 THEN 1 ELSE 0 END) AS allowed_requests,
                SUM(CASE WHEN detected_type = 'sqli' THEN 1 ELSE 0 END) AS sqli_payloads,
                SUM(CASE WHEN detected_type = 'xss' THEN 1 ELSE 0 END) AS xss_payloads,
                SUM(CASE WHEN detected_type = 'benign' THEN 1 ELSE 0 END) AS benign_payloads,
                AVG(model_time_ms) AS avg_model_time_ms
            FROM lab_logs
            """
        ).fetchone()

    total_requests = int(log_rows["total_requests"] or 0)
    blocked_requests = int(log_rows["blocked_requests"] or 0)
    allowed_requests = int(log_rows["allowed_requests"] or 0)
    sqli_payloads = int(log_rows["sqli_payloads"] or 0)
    xss_payloads = int(log_rows["xss_payloads"] or 0)
    benign_payloads = int(log_rows["benign_payloads"] or 0)
    avg_model_time_ms = round(float(log_rows["avg_model_time_ms"] or 0.0), 4)

    return {
        "tableCounts": table_counts,
        "attackSummary": {
            "totalRequests": total_requests,
            "totalAttacks": sqli_payloads + xss_payloads,
            "blocked": blocked_requests,
            "allowed": allowed_requests,
            "sqlPayloads": sqli_payloads,
            "xssPayloads": xss_payloads,
            "benignPayloads": benign_payloads,
            "avgModelTimeMs": avg_model_time_ms,
        },
    }


def read_terminal_log_tail(path: Path, max_lines: int = 250) -> str:
    if not path.exists():
        return ""

    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    return "\n".join(lines[-max_lines:])
