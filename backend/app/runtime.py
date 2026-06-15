from dataclasses import asdict
from dataclasses import dataclass
from threading import Lock

from app.config import settings


@dataclass
class SecurityRuntimeState:
    protection_enabled: bool = settings.lab_mode == "protected"
    ml_enabled: bool = True
    dl_enabled: bool = True
    block_threshold: float = settings.block_threshold


class RuntimeSecuritySettings:
    def __init__(self) -> None:
        self._state = SecurityRuntimeState()
        self._lock = Lock()

    def snapshot(self) -> dict:
        with self._lock:
            state = asdict(self._state)
            state["labMode"] = "protected" if self._state.protection_enabled else "vulnerable"
            return state

    def update(
        self,
        *,
        protection_enabled: bool | None = None,
        ml_enabled: bool | None = None,
        dl_enabled: bool | None = None,
        block_threshold: float | None = None,
    ) -> dict:
        with self._lock:
            if protection_enabled is not None:
                self._state.protection_enabled = protection_enabled
            if ml_enabled is not None:
                self._state.ml_enabled = ml_enabled
            if dl_enabled is not None:
                self._state.dl_enabled = dl_enabled
            if block_threshold is not None:
                self._state.block_threshold = block_threshold

            state = asdict(self._state)
            state["labMode"] = "protected" if self._state.protection_enabled else "vulnerable"
            return state


runtime_security = RuntimeSecuritySettings()
