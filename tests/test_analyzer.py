from __future__ import annotations

from typing import Any

from medlab.analyzer import DISCLAIMER_VI, AnalysisEngine
from medlab.llm import LLMResult
from medlab.schema import (
    AnalysisReport,
    BloodPanel,
    LLMMeta,
    LLMNarrative,
    PatientInput,
    Sex,
    UrinePanel,
)


class FakeLLM:
    def __init__(self, summary: str) -> None:
        self.summary = summary
        self.prompt: str | None = None

    def analyze(self, prompt: str) -> LLMResult:
        self.prompt = prompt
        return LLMResult(
            narrative=LLMNarrative(
                summary_vi=self.summary,
                key_points_vi=["AI point"],
                lifestyle_vi=["AI lifestyle"],
                when_to_seek_care_vi=["AI care"],
                confidence="high",
            ),
            meta=LLMMeta(model="fake-gemini", status="ok", latency_ms=12, attempts=1),
        )


class BrokenModel:
    def assess(self, *args: Any, **kwargs: Any) -> Any:
        raise RuntimeError("boom")


def test_offline_fallback_report(
    offline_settings: Any, trained_model: Any, critical_patient: PatientInput
) -> None:
    engine = AnalysisEngine(settings=offline_settings, risk_model=trained_model, llm_client=None)
    report = engine.analyze(critical_patient)
    assert report.summary_source == "offline"
    assert report.llm.status == "offline"
    assert report.urgent is True
    assert report.conclusion_vi.startswith("CẦN ĐÁNH GIÁ Y TẾ NGAY")
    assert report.disclaimer_vi == DISCLAIMER_VI
    assert report.risk.status == "ok"


def test_llm_success_is_used(
    offline_settings: Any, trained_model: Any, normal_patient: PatientInput
) -> None:
    fake = FakeLLM("Các chỉ số ổn định, nên kiểm tra định kỳ.")
    engine = AnalysisEngine(settings=offline_settings, risk_model=trained_model, llm_client=fake)
    report = engine.analyze(normal_patient)
    assert report.summary_source == "gemini"
    assert report.llm.status == "ok"
    assert report.conclusion_vi == "Các chỉ số ổn định, nên kiểm tra định kỳ."


def test_llm_contradiction_is_rejected(
    offline_settings: Any, trained_model: Any, uti_patient: PatientInput
) -> None:
    fake = FakeLLM("Kết quả hoàn toàn bình thường.")
    engine = AnalysisEngine(settings=offline_settings, risk_model=trained_model, llm_client=fake)
    report = engine.analyze(uti_patient)
    assert report.summary_source == "offline"
    assert report.llm.status == "error"
    assert "kiểm duyệt" in (report.llm.fallback_reason or "")


def test_llm_prescription_is_rejected(
    offline_settings: Any, trained_model: Any, normal_patient: PatientInput
) -> None:
    fake = FakeLLM("Tôi kê đơn kháng sinh cho bạn.")
    engine = AnalysisEngine(settings=offline_settings, risk_model=trained_model, llm_client=fake)
    report = engine.analyze(normal_patient)
    assert report.summary_source == "offline"


def test_llm_prompt_is_redacted(
    offline_settings: Any, trained_model: Any, normal_patient: PatientInput
) -> None:
    patient = normal_patient.model_copy(update={"symptoms_note": "Liên hệ 0912345678"})
    fake = FakeLLM("Theo dõi thêm.")
    AnalysisEngine(settings=offline_settings, risk_model=trained_model, llm_client=fake).analyze(
        patient
    )
    assert fake.prompt is not None
    assert "0912345678" not in fake.prompt
    assert "SỐ_ĐIỆN_THOẠI_ĐÃ_ẨN" in fake.prompt


def test_model_failure_degrades_gracefully(
    offline_settings: Any, normal_patient: PatientInput
) -> None:
    engine = AnalysisEngine(settings=offline_settings, risk_model=BrokenModel(), llm_client=None)
    report = engine.analyze(normal_patient)
    assert report.risk.status == "unavailable"


def test_no_model_artifact_degrades_gracefully(
    offline_settings: Any, normal_patient: PatientInput
) -> None:
    engine = AnalysisEngine(settings=offline_settings, risk_model=None, llm_client=None)
    report = engine.analyze(normal_patient)
    assert report.risk.status == "unavailable"
    assert "Chưa có model artifact" in (report.risk.note_vi or "")


def test_computed_egfr_is_not_reported_missing(
    offline_settings: Any, trained_model: Any, normal_patient: PatientInput
) -> None:
    patient = normal_patient.model_copy(
        update={"age_years": 70, "blood": BloodPanel(creatinine_umol_l=300), "urine": UrinePanel()}
    )
    report = AnalysisEngine(
        settings=offline_settings, risk_model=trained_model, llm_client=None
    ).analyze(patient)
    assert "eGFR (CKD-EPI 2021)" not in report.data_quality.missing_fields
    assert any("CKD-EPI" in note for note in report.data_quality.notes_vi)


def test_pediatric_note(offline_settings: Any, trained_model: Any) -> None:
    patient = PatientInput(
        age_years=10,
        sex=Sex.MALE,
        blood=BloodPanel(hemoglobin_g_l=130, creatinine_umol_l=50),
        urine=UrinePanel(),
    )
    report = AnalysisEngine(
        settings=offline_settings, risk_model=trained_model, llm_client=None
    ).analyze(patient)
    assert any("dưới 18" in note for note in report.data_quality.notes_vi)
    assert report.data_quality.fields_provided < report.data_quality.fields_expected


def test_report_is_json_roundtrippable(
    offline_settings: Any, trained_model: Any, critical_patient: PatientInput
) -> None:
    report = AnalysisEngine(
        settings=offline_settings, risk_model=trained_model, llm_client=None
    ).analyze(critical_patient)
    parsed = AnalysisReport.model_validate_json(report.model_dump_json())
    assert parsed.request_id == report.request_id
    assert parsed.urgent is True
