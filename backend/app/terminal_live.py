import asyncio
import logging
from collections import deque


class TerminalBroadcaster:
    def __init__(self, max_lines: int = 500) -> None:
        self._subscribers: set[asyncio.Queue[str]] = set()
        self._history: deque[str] = deque(maxlen=max_lines)
        self._installed = False
        self._handler = BroadcastLogHandler(self)

    def install(self) -> None:
        if self._installed:
            return

        formatter = logging.Formatter("%(levelname)s: %(message)s")
        self._handler.setFormatter(formatter)

        for logger_name in ("uvicorn.error", "uvicorn.access"):
            logger = logging.getLogger(logger_name)
            logger.addHandler(self._handler)

        self._installed = True

    def history(self) -> str:
        return "\n".join(self._history)

    async def subscribe(self) -> asyncio.Queue[str]:
        queue: asyncio.Queue[str] = asyncio.Queue()
        self._subscribers.add(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue[str]) -> None:
        self._subscribers.discard(queue)

    def publish(self, line: str) -> None:
        normalized = line.rstrip("\n")
        if not normalized:
            return

        self._history.append(normalized)
        for queue in tuple(self._subscribers):
            try:
                queue.put_nowait(normalized)
            except asyncio.QueueFull:
                continue


class BroadcastLogHandler(logging.Handler):
    def __init__(self, broadcaster: TerminalBroadcaster) -> None:
        super().__init__()
        self.broadcaster = broadcaster

    def emit(self, record: logging.LogRecord) -> None:
        try:
            message = self.format(record)
        except Exception:
            message = record.getMessage()

        self.broadcaster.publish(message)


terminal_broadcaster = TerminalBroadcaster()
