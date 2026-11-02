from __future__ import annotations

import json
from typing import Any

import requests

from medlab.config import Settings
from medlab.llm import (
    GeminiClient,
    build_prompt,
    fallback_narrative,
    make_llm_client,
)
from medlab.privacy import redact_text
from medlab.schema import PatientInput, RiskAssessment


class FakeResponse:
    def __init__(self, status_code: int, payload: dict[str, Any] | None = None) -> None:
        self.status_code = status_code
        self.payload = payload or {}

    def json(self) -> dict[str, Any]:
        return self.payload


def _success_payload(text: str | None = None) -> dict[str, Any]:
    narrative = {
        "summary_vi": "Các chỉ số cần được bác sĩ đánh giá thêm.",
        "key_points_vi": ["Hemoglobin thấp nhẹ."],
        "lifestyle_vi": ["Uống đủ nước."],
        "when_to_seek_care_vi": ["Nếu mệt nhiều, hãy đi khám."],
        "confidence": "medium",
    }
    return {
        "candidates": [
            {
                "content": {
                    "parts": [{"text": text if text is not None else json.dumps(narrative)}]
                },
                "finishReason": "STOP",
            }
        ]
    }


def test_successful_gemini_response_with_code_fence() -> None:
    client = GeminiClient(
        api_key="k",
        model="gemini-test",
        http_post=lambda *args, **kwargs: FakeResponse(
            200,
            _success_payload(
                '```json\n{"summary_vi":"Ổn","key_points_vi":[],"lifestyle_vi":[],"when_to_seek_care_vi":[],"confidence":"high"}\n```'
            ),
        ),
    )
    result = client.analyze("prompt")
    assert result.meta.status == "ok"
    assert result.narrative is not None
    assert result.narrative.summary_vi == "Ổn"


def test_retry_on_429_then_success() -> None:
    responses = [FakeResponse(429), FakeResponse(200, _success_payload())]
    sleeps: list[float] = []
    client = GeminiClient(
        api_key="k",
        model="gemini-test",
        max_retries=2,
        http_post=lambda *args, **kwargs: responses.pop(0),
        sleep_fn=sleeps.append,
    )
    result = client.analyze("prompt")
    assert result.meta.status == "ok"
    assert result.meta.attempts == 2
    assert len(sleeps) == 1


def test_non_retryable_http_error() -> None:
    calls = []

    def post(*args: Any, **kwargs: Any) -> FakeResponse:
        calls.append(1)
        return FakeResponse(400)

    result = GeminiClient(api_key="k", model="m", http_post=post).analyze("prompt")
    assert result.meta.status == "error"
    assert len(calls) == 1
    assert result.narrative is None


def test_retry_on_timeout() -> None:
    state = {"calls": 0}

    def post(*args: Any, **kwargs: Any) -> FakeResponse:
        state["calls"] += 1
        if state["calls"] == 1:
            raise requests.Timeout("slow")
        return FakeResponse(200, _success_payload())

    result = GeminiClient(api_key="k", model="m", http_post=post, sleep_fn=lambda _: None).analyze(
        "p"
    )
    assert result.meta.status == "ok"
    assert state["calls"] == 2


def test_safety_block_is_error() -> None:
    payload = {"candidates": [{"content": {"parts": []}, "finishReason": "SAFETY"}]}
    result = GeminiClient(
        api_key="k", model="m", http_post=lambda *a, **k: FakeResponse(200, payload)
    ).analyze("p")
    assert result.meta.status == "error"
    assert "safety" in (result.meta.fallback_reason or "").lower()


def test_invalid_json_is_error() -> None:
    result = GeminiClient(
        api_key="k",
        model="m",
        http_post=lambda *a, **k: FakeResponse(200, _success_payload("not json")),
    ).analyze("p")
    assert result.meta.status == "error"
    assert result.narrative is None


def test_fallback_narrative_is_urgent_for_red_flags() -> None:
    narrative = fallback_narrative([], ["Kali rất cao"], 2, 26, "high")
    assert "ngay" in narrative.summary_vi.lower()
    assert narrative.key_points_vi[0] == "Kali rất cao"
    assert narrative.confidence == "low"


def test_build_prompt_contains_structured_data_but_no_pii(normal_patient: PatientInput) -> None:
    note = redact_text("Liên hệ 0912345678, email a@example.com", 500)
    assert note is not None
    prompt = build_prompt(
        patient=normal_patient,
        findings=[],
        red_flags=[],
        risk=RiskAssessment(status="unavailable", band="unknown"),
        egfr_value=None,
        egfr_computed=False,
        redacted_note=note,
        missing_fields=["CRP"],
    )
    assert "<patient_data>" in prompt
    assert '"age_years": 40' in prompt
    assert "0912345678" not in prompt
    assert "a@example.com" not in prompt
    assert "CRP" in prompt


def test_request_uses_header_auth_and_json_mode() -> None:
    captured: dict[str, Any] = {}

    def fake_post(url: str, headers: dict[str, str], body: dict[str, Any], timeout: float):
        captured.update(url=url, headers=headers, body=body, timeout=timeout)
        return FakeResponse(200, _success_payload())

    client = GeminiClient(api_key="secret-key", model="gemini-test", http_post=fake_post)
    client.analyze("prompt")

    assert captured["url"].endswith("/models/gemini-test:generateContent")
    assert "?key=" not in captured["url"]
    assert captured["headers"]["x-goog-api-key"] == "secret-key"
    assert captured["body"]["generationConfig"]["responseMimeType"] == "application/json"
    assert captured["body"]["systemInstruction"]["parts"][0]["text"]


def test_make_llm_client_requires_key() -> None:
    settings = Settings(_env_file=None, gemini_api_key=None, llm_mode="auto")
    assert make_llm_client(settings) is None
    settings = Settings(_env_file=None, gemini_api_key="secret", llm_mode="offline")
    assert make_llm_client(settings) is None


def test_make_llm_client_with_key() -> None:
    settings = Settings(_env_file=None, gemini_api_key="secret", llm_mode="auto")
    client = make_llm_client(settings)
    assert client is not None
    assert client.model == "gemini-3.5-flash"
