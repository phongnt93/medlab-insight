from __future__ import annotations

import re

from medlab.schema import SEVERITY_RANK, LLMNarrative, Severity

_FORBIDDEN = re.compile(
    r"(kê\s*đơn|đơn\s*thuốc|liều\s*dùng|liều\s*lượng|kháng\s*sinh|"
    r"uống\s+\d+[^.\n]{0,15}(mg|viên)|tiêm\s+\d+[^.\n]{0,15}(mg|ml))",
    re.IGNORECASE,
)
_NORMAL_CLAIM = re.compile(
    r"(hoàn toàn bình thường|tất cả (các )?chỉ số (đều )?bình thường|"
    r"kết quả bình thường|không có bất thường)",
    re.IGNORECASE,
)
_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_HTML = re.compile(r"<[^>]+>")


def clean_text(text: str, limit: int = 2000) -> str:
    cleaned = _HTML.sub("", str(text))
    cleaned = _CONTROL.sub("", cleaned)
    cleaned = " ".join(cleaned.split())
    return cleaned[:limit].strip()


def sanitize_narrative(
    narrative: LLMNarrative,
    max_severity: Severity,
    urgent: bool,
) -> LLMNarrative | None:
    """Reject unsafe/hallucinated LLM output. Returning None triggers the deterministic fallback."""
    texts = [
        narrative.summary_vi,
        *narrative.key_points_vi,
        *narrative.lifestyle_vi,
        *narrative.when_to_seek_care_vi,
    ]
    combined = " ".join(texts)
    if _FORBIDDEN.search(combined):
        return None
    if SEVERITY_RANK[max_severity] >= SEVERITY_RANK[Severity.MODERATE] and _NORMAL_CLAIM.search(
        combined
    ):
        return None

    summary = clean_text(narrative.summary_vi, 2000)
    if not summary:
        return None
    return LLMNarrative(
        summary_vi=summary,
        key_points_vi=[
            clean_text(item, 400) for item in narrative.key_points_vi if clean_text(item, 400)
        ][:8],
        lifestyle_vi=[
            clean_text(item, 400) for item in narrative.lifestyle_vi if clean_text(item, 400)
        ][:6],
        when_to_seek_care_vi=[
            clean_text(item, 400)
            for item in narrative.when_to_seek_care_vi
            if clean_text(item, 400)
        ][:6],
        confidence=narrative.confidence,
    )
