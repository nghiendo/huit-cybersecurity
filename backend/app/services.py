from html import escape

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


def fetch_admin_data(limit: int = 50) -> dict:
    with get_connection() as conn:
        users = conn.execute(
            "SELECT id, username, password, role FROM users ORDER BY id ASC LIMIT ?",
            (limit,),
        ).fetchall()
        comments = conn.execute(
            "SELECT id, author, content, created_at FROM comments ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
        logs = conn.execute(
            """
            SELECT
                id,
                input,
                detected_type,
                blocked,
                model_score,
                model_time_ms,
                endpoint_time_ms,
                created_at
            FROM lab_logs
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

    return {
        "users": [dict(row) for row in users],
        "comments": [dict(row) for row in comments],
        "labLogs": [dict(row) for row in logs],
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
