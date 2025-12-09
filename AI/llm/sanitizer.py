import re
from typing import Iterable


SENSITIVE_PATTERNS: Iterable[re.Pattern] = (
    re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),       # SSN format
    re.compile(r"\b\d{9}\b"),                    # 9-digit numbers
    re.compile(r"\b\d{5,}\b"),                   # long digit sequences
    re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),  # emails
)


def sanitize_text(text: str) -> str:
    """Basic redaction to mask sensitive information before sending to LLM."""
    if not text:
        return ""

    sanitized = text
    for pattern in SENSITIVE_PATTERNS:
        sanitized = pattern.sub("[REDACTED]", sanitized)

    return sanitized

