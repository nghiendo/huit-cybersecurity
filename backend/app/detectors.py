import re
from dataclasses import dataclass
from time import perf_counter


SQLI_PATTERNS = [
    r"('\s*or\s*'?\d+'?\s*=\s*'?\d+)",
    r"(\bor\b\s+\d+\s*=\s*\d+)",
    r"(--|#|/\*)",
    r"\bunion\b\s+\bselect\b",
    r"\binformation_schema\b",
    r"\bselect\b.+\bfrom\b",
    r"\bwhere\b.+=",
]

XSS_PATTERNS = [
    r"<\s*script\b",
    r"\bon\w+\s*=",
    r"javascript\s*:",
    r"<\s*img\b[^>]*\bonerror\s*=",
    r"<\s*svg\b[^>]*\bonload\s*=",
    r"document\.cookie",
]


@dataclass(frozen=True)
class ModelResult:
    label: str
    score: float
    blocked: bool
    model_time_ms: float
    ml_score: float
    dl_score: float


def _pattern_score(value: str, patterns: list[str]) -> float:
    if not value:
        return 0.0

    hits = sum(1 for pattern in patterns if re.search(pattern, value, re.IGNORECASE))
    return min(1.0, hits / 3)


def run_ml_detector(value: str) -> tuple[str, float]:
    """Lightweight placeholder for a future sklearn-style classifier."""
    sqli_score = _pattern_score(value, SQLI_PATTERNS)
    xss_score = _pattern_score(value, XSS_PATTERNS)

    if sqli_score >= xss_score and sqli_score > 0:
        return "sqli", sqli_score
    if xss_score > 0:
        return "xss", xss_score
    return "benign", 0.0


def run_dl_detector(value: str) -> tuple[str, float]:
    """Placeholder for a future PyTorch/TensorFlow/transformers model."""
    encoded_markers = ["%27", "%3c", "%3e", "&#x", "\\x3c", "\\u003c"]
    base_label, base_score = run_ml_detector(value)
    encoded_bonus = 0.2 if any(marker in value.lower() for marker in encoded_markers) else 0.0
    return base_label, min(1.0, base_score + encoded_bonus)


def classify_payload(value: str, block_threshold: float) -> ModelResult:
    return classify_payload_with_engines(
        value,
        block_threshold=block_threshold,
        ml_enabled=True,
        dl_enabled=True,
    )


def classify_payload_with_engines(
    value: str,
    *,
    block_threshold: float,
    ml_enabled: bool,
    dl_enabled: bool,
) -> ModelResult:
    started = perf_counter()
    ml_label, ml_score = run_ml_detector(value) if ml_enabled else ("benign", 0.0)
    dl_label, dl_score = run_dl_detector(value) if dl_enabled else ("benign", 0.0)
    elapsed_ms = (perf_counter() - started) * 1000

    if not ml_enabled and not dl_enabled:
        score = 0.0
        label = "benign"
    else:
        score = max(ml_score, dl_score)
        label = dl_label if dl_score >= ml_score else ml_label

    return ModelResult(
        label=label,
        score=score,
        blocked=score >= block_threshold,
        model_time_ms=elapsed_ms,
        ml_score=ml_score,
        dl_score=dl_score,
    )
