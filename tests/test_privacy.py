from __future__ import annotations

from medlab.privacy import redact_text


def test_redacts_direct_identifiers() -> None:
    text = "Bệnh nhân Nguyễn Văn A, SĐT 0912345678, email a@example.com, CCCD 012345678901"
    redacted = redact_text(text, 500)
    assert redacted is not None
    assert "0912345678" not in redacted
    assert "a@example.com" not in redacted
    assert "012345678901" not in redacted
    assert "[SỐ_ĐIỆN_THOẠI_ĐÃ_ẨN]" in redacted
    assert "[EMAIL_ĐÃ_ẨN]" in redacted


def test_redacts_urls_and_limits_length() -> None:
    redacted = redact_text("xem https://example.com/abc " + "a" * 600, 100)
    assert redacted is not None
    assert "https://" not in redacted
    assert len(redacted) <= 100


def test_none_and_blank() -> None:
    assert redact_text(None) is None
    assert redact_text("   ") is None
