import json
from time import perf_counter
from typing import Callable

from app.detectors import classify_payload_with_engines
from app.runtime import runtime_security


class ModelMiddleware:
    def __init__(self, app: Callable):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope.get("path") != "/api/lab":
            await self.app(scope, receive, send)
            return

        body = b""
        more_body = True
        while more_body:
            message = await receive()
            body += message.get("body", b"")
            more_body = message.get("more_body", False)

        input_value = ""
        if body:
            try:
                payload = json.loads(body.decode("utf-8"))
                input_value = str(payload.get("input", ""))
            except json.JSONDecodeError:
                input_value = ""

        security_settings = runtime_security.snapshot()
        scope["security_context"] = classify_payload_with_engines(
            input_value,
            block_threshold=security_settings["block_threshold"],
            ml_enabled=security_settings["ml_enabled"],
            dl_enabled=security_settings["dl_enabled"],
        )
        scope["security_runtime"] = security_settings
        scope["request_started_at"] = perf_counter()

        async def replay_receive():
            return {"type": "http.request", "body": body, "more_body": False}

        await self.app(scope, replay_receive, send)
