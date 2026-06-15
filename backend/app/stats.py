from dataclasses import dataclass, field
from threading import Lock


@dataclass
class LabStats:
    total_requests: int = 0
    allowed: int = 0
    blocked: int = 0
    sqli_payloads: int = 0
    xss_payloads: int = 0
    benign_payloads: int = 0
    total_model_time_ms: float = 0.0
    _lock: Lock = field(default_factory=Lock)

    def record(self, label: str, blocked: bool, model_time_ms: float) -> None:
        with self._lock:
            self.total_requests += 1
            self.total_model_time_ms += model_time_ms

            if blocked:
                self.blocked += 1
            else:
                self.allowed += 1

            if label == "sqli":
                self.sqli_payloads += 1
            elif label == "xss":
                self.xss_payloads += 1
            else:
                self.benign_payloads += 1

    def snapshot(self) -> dict:
        with self._lock:
            avg = self.total_model_time_ms / self.total_requests if self.total_requests else 0.0
            return {
                "totalRequests": self.total_requests,
                "allowed": self.allowed,
                "blocked": self.blocked,
                "sqlPayloads": self.sqli_payloads,
                "xssPayloads": self.xss_payloads,
                "benignPayloads": self.benign_payloads,
                "avgModelTimeMs": round(avg, 4),
            }

    def replace(self, snapshot: dict) -> None:
        with self._lock:
            self.total_requests = int(snapshot.get("totalRequests", 0))
            self.allowed = int(snapshot.get("allowed", 0))
            self.blocked = int(snapshot.get("blocked", 0))
            self.sqli_payloads = int(snapshot.get("sqlPayloads", 0))
            self.xss_payloads = int(snapshot.get("xssPayloads", 0))
            self.benign_payloads = int(snapshot.get("benignPayloads", 0))
            avg = float(snapshot.get("avgModelTimeMs", 0.0))
            self.total_model_time_ms = avg * self.total_requests


stats = LabStats()
