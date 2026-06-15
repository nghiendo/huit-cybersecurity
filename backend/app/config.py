import os
from dataclasses import dataclass
from pathlib import Path


def load_env_file() -> dict[str, str]:
    env_path = Path(__file__).resolve().parents[2] / ".env"
    values: dict[str, str] = {}

    if not env_path.exists():
        return values

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip("\"'")

    return values


ENV_FILE_VALUES = load_env_file()


def get_env(name: str, default: str) -> str:
    return os.getenv(name, ENV_FILE_VALUES.get(name, default))


@dataclass(frozen=True)
class Settings:
    lab_mode: str
    block_threshold: float
    database_path: Path
    admin_token: str
    backend_terminal_log_path: Path


settings = Settings(
    lab_mode=get_env("LAB_MODE", "vulnerable"),
    block_threshold=float(get_env("BLOCK_THRESHOLD", "0.85")),
    database_path=Path(
        get_env(
            "DATABASE_PATH",
            str(Path(__file__).resolve().parents[1] / "data" / "lab.sqlite"),
        )
    ),
    admin_token=get_env("ADMIN_TOKEN", "lab-admin-token"),
    backend_terminal_log_path=Path(
        get_env(
            "BACKEND_TERMINAL_LOG_PATH",
            str(Path(__file__).resolve().parents[1] / "data" / "backend-terminal.log"),
        )
    ),
)
