from time import perf_counter

from fastapi import Depends, FastAPI, HTTPException, Query, Request, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

from app.config import settings
from app.database import init_db
from app.middleware import ModelMiddleware
from app.runtime import runtime_security
from app.services import (
    append_comment,
    fetch_admin_table,
    read_terminal_log_tail,
    simulate_sql_analysis,
    simulate_xss_analysis,
    summarize_admin_data,
    write_lab_log,
)
from app.stats import stats
from app.terminal_live import terminal_broadcaster


class LabRequest(BaseModel):
    input: str = Field(..., min_length=1, max_length=4000)


class AdminSettingsUpdate(BaseModel):
    protectionEnabled: bool | None = None
    mlEnabled: bool | None = None
    dlEnabled: bool | None = None
    blockThreshold: float | None = Field(default=None, ge=0.0, le=1.0)


app = FastAPI(
    title="SQLi/XSS Training Lab",
    description="Local-only SQLi/XSS training backend with ML/DL detector hooks.",
)
app.add_middleware(ModelMiddleware)


@app.on_event("startup")
def startup() -> None:
    init_db()
    stats.replace(summarize_admin_data()["attackSummary"])
    settings.backend_terminal_log_path.parent.mkdir(parents=True, exist_ok=True)
    settings.backend_terminal_log_path.touch(exist_ok=True)
    terminal_broadcaster.install()


def verify_admin_token(token: str | None = Query(default=None)) -> str:
    if token != settings.admin_token:
        raise HTTPException(status_code=401, detail="Invalid admin token.")
    return token


@app.post("/api/lab")
def lab_endpoint(payload: LabRequest, request: Request) -> dict:
    security = request.scope["security_context"]
    security_runtime = request.scope["security_runtime"]
    should_block = security_runtime["protection_enabled"] and security.blocked
    started = request.scope.get("request_started_at", perf_counter())

    if should_block:
        result = {
            "sql": None,
            "xss": None,
            "comments": [],
            "message": "Payload blocked by detector in protected mode.",
        }
    else:
        sql_result = simulate_sql_analysis(payload.input)
        xss_result = simulate_xss_analysis(payload.input)
        comments = append_comment(payload.input)
        result = {
            "sql": sql_result,
            "xss": xss_result,
            "comments": comments,
            "message": "Payload analyzed in lab mode.",
        }

    endpoint_time_ms = (perf_counter() - started) * 1000
    stats.record(security.label, should_block, security.model_time_ms)
    write_lab_log(
        value=payload.input,
        detected_type=security.label,
        blocked=should_block,
        model_score=security.score,
        model_time_ms=security.model_time_ms,
        endpoint_time_ms=endpoint_time_ms,
    )

    return {
        "ok": True,
        "mode": security_runtime["labMode"],
        "result": result,
        "security": {
            "label": security.label,
            "score": round(security.score, 4),
            "blocked": should_block,
            "modelTimeMs": round(security.model_time_ms, 4),
            "mlScore": round(security.ml_score, 4),
            "dlScore": round(security.dl_score, 4),
            "mlEnabled": security_runtime["ml_enabled"],
            "dlEnabled": security_runtime["dl_enabled"],
        },
        "stats": stats.snapshot(),
        "endpointTimeMs": round(endpoint_time_ms, 4),
    }


@app.get("/api/admin/settings")
def admin_settings(_: str = Depends(verify_admin_token)) -> dict:
    return {
        "ok": True,
        "settings": runtime_security.snapshot(),
    }


@app.put("/api/admin/settings")
def update_admin_settings(payload: AdminSettingsUpdate, _: str = Depends(verify_admin_token)) -> dict:
    settings_snapshot = runtime_security.update(
        protection_enabled=payload.protectionEnabled,
        ml_enabled=payload.mlEnabled,
        dl_enabled=payload.dlEnabled,
        block_threshold=payload.blockThreshold,
    )
    return {
        "ok": True,
        "settings": settings_snapshot,
    }


@app.get("/api/admin/stats")
def admin_stats(_: str = Depends(verify_admin_token)) -> dict:
    return {
        "ok": True,
        **summarize_admin_data(),
    }


@app.get("/api/admin/data")
def admin_data(
    resource: str = Query(...),
    limit: int = Query(default=25, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    _: str = Depends(verify_admin_token),
) -> dict:
    return {
        "ok": True,
        "data": fetch_admin_table(resource=resource, limit=limit, offset=offset),
    }


@app.get("/api/admin/terminal")
def admin_terminal_snapshot(_: str = Depends(verify_admin_token)) -> dict:
    return {
        "ok": True,
        "output": terminal_broadcaster.history() or read_terminal_log_tail(settings.backend_terminal_log_path),
    }


@app.websocket("/api/admin/terminal-ws")
async def admin_terminal_ws(websocket: WebSocket) -> None:
    token = websocket.query_params.get("token")
    if token != settings.admin_token:
        await websocket.close(code=1008)
        return

    await websocket.accept()
    queue = await terminal_broadcaster.subscribe()

    try:
        while True:
            line = await queue.get()
            await websocket.send_text(line)
    except WebSocketDisconnect:
        terminal_broadcaster.unsubscribe(queue)
    finally:
        terminal_broadcaster.unsubscribe(queue)
