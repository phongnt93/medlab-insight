from __future__ import annotations

import re

_EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
_PHONE_VN = re.compile(r"(?:(?:\+?84)|0)(?:[\s.\-]?\d){8,10}\b")
_LONG_DIGITS = re.compile(r"\b\d{6,}\b")
_URL = re.compile(r"https?://\S+", re.IGNORECASE)


def redact_text(text: str | None, max_chars: int = 500) -> str | None:
    """Remove obvious direct identifiers before any text leaves the service."""
    if not text:
        return None
    cleaned = text[:max_chars]
    cleaned = _URL.sub("[LIÊN_KẾT_ĐÃ_ẨN]", cleaned)
    cleaned = _EMAIL.sub("[EMAIL_ĐÃ_ẨN]", cleaned)
    cleaned = _PHONE_VN.sub("[SỐ_ĐIỆN_THOẠI_ĐÃ_ẨN]", cleaned)
    cleaned = _LONG_DIGITS.sub("[SỐ_ĐÃ_ẨN]", cleaned)
    cleaned = " ".join(cleaned.split())
    return cleaned or None
