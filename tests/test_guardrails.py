from __future__ import annotations

from medlab.guardrails import clean_text, sanitize_narrative
from medlab.schema import LLMNarrative, Severity


def _narrative(summary: str) -> LLMNarrative:
    return LLMNarrative(
        summary_vi=summary,
        key_points_vi=["Điểm 1"],
        lifestyle_vi=["Uống đủ nước"],
        when_to_seek_care_vi=["Đi khám nếu nặng"],
        confidence="medium",
    )


def test_safe_narrative_passes() -> None:
    result = sanitize_narrative(_narrative("Cần theo dõi thêm."), Severity.MODERATE, False)
    assert result is not None
    assert result.summary_vi == "Cần theo dõi thêm."


def test_prescription_language_is_rejected() -> None:
    assert (
        sanitize_narrative(_narrative("Tôi kê đơn kháng sinh cho bạn."), Severity.MILD, False)
        is None
    )


def test_normal_claim_with_abnormal_severity_is_rejected() -> None:
    assert sanitize_narrative(_narrative("Kết quả bình thường."), Severity.MODERATE, False) is None


def test_normal_claim_allowed_when_nothing_abnormal() -> None:
    assert (
        sanitize_narrative(_narrative("Kết quả bình thường."), Severity.NORMAL, False) is not None
    )


def test_html_and_control_chars_are_stripped() -> None:
    cleaned = clean_text("<b>Xin chào</b>\x00  thế giới")
    assert cleaned == "Xin chào thế giới"
