from __future__ import annotations

import time
import uuid
from datetime import UTC, datetime
from typing import Any

from medlab.config import Settings, get_settings
from medlab.egfr import effective_egfr
from medlab.guardrails import sanitize_narrative
from medlab.llm import (
    GeminiClient,
    build_prompt,
    fallback_narrative,
    make_llm_client,
    meta_offline,
)
from medlab.logging_utils import get_logger
from medlab.privacy import redact_text
from medlab.reference_ranges import URINE_DIPSTICK_LABELS, all_specs
from medlab.risk_model import load_risk_model
from medlab.rules import evaluate_rules
from medlab.schema import (
    SEVERITY_RANK,
    AnalysisReport,
    DataQuality,
    PatientInput,
    RiskAssessment,
    Severity,
)

logger = get_logger(__name__)

DISCLAIMER_VI = (
    "Công cụ hỗ trợ sàng lọc, KHÔNG thay thế chẩn đoán của bác sĩ. "
    "Kết quả do AI/mô hình có thể sai; hãy đối chiếu với phiếu xét nghiệm gốc, "
    "triệu chứng lâm sàng và ý kiến chuyên môn. Không dùng thông tin này để tự điều trị."
)

_UNSET = object()


def _build_data_quality(patient: PatientInput, egfr_computed: bool) -> DataQuality:
    specs = all_specs(patient.sex)
    missing: list[str] = []
    for key, spec in specs.items():
        value = getattr(patient.blood, key, None)
        if value is None:
            value = getattr(patient.urine, key, None)
        if value is None and not (key == "egfr_ml_min_1_73m2" and egfr_computed):
            missing.append(spec.label_vi)
    for key, label in URINE_DIPSTICK_LABELS.items():
        if getattr(patient.urine, key) is None:
            missing.append(label)

    expected = len(specs) + len(URINE_DIPSTICK_LABELS)
    provided = patient.provided_lab_count() + (1 if egfr_computed else 0)
    notes: list[str] = []
    if provided < 5:
        notes.append(
            f"Chỉ có {provided}/{expected} chỉ số — độ tin cậy thấp, nên bổ sung thêm dữ liệu."
        )
    elif provided < 12:
        notes.append(
            f"Có {provided}/{expected} chỉ số — dữ liệu chưa đầy đủ, kết luận chỉ mang tính tham khảo."
        )
    if patient.age_years < 18:
        notes.append(
            "Người dưới 18 tuổi: ngưỡng tham chiếu người lớn có thể không phù hợp; cần bác sĩ nhi khoa."
        )
    if egfr_computed:
        notes.append("eGFR được ước tính từ creatinine bằng công thức CKD-EPI 2021.")
    if (
        patient.blood.creatinine_umol_l is not None
        and patient.blood.egfr_ml_min_1_73m2 is None
        and (patient.sex.value == "other" or patient.age_years < 18)
    ):
        notes.append(
            "Không tự động tính eGFR cho trẻ em hoặc lựa chọn giới tính 'khác'; cần phòng xét nghiệm tính."
        )
    return DataQuality(
        fields_provided=provided,
        fields_expected=expected,
        missing_fields=missing,
        notes_vi=notes,
    )


class AnalysisEngine:
    def __init__(
        self,
        settings: Settings | None = None,
        risk_model: Any = _UNSET,
        llm_client: Any = _UNSET,
    ) -> None:
        self.settings = settings or get_settings()
        self.risk_model = load_risk_model(self.settings) if risk_model is _UNSET else risk_model
        self.llm_client = make_llm_client(self.settings) if llm_client is _UNSET else llm_client

    def analyze(self, patient: PatientInput) -> AnalysisReport:
        started = time.perf_counter()
        request_id = uuid.uuid4().hex
        egfr_value, egfr_computed = effective_egfr(
            patient.blood.egfr_ml_min_1_73m2,
            patient.blood.creatinine_umol_l,
            patient.age_years,
            patient.sex,
        )
        rules = evaluate_rules(patient, egfr_value)
        data_quality = _build_data_quality(patient, egfr_computed)

        if self.risk_model is None:
            risk = RiskAssessment(
                status="unavailable",
                note_vi="Chưa có model artifact; kết luận chỉ dựa trên rule engine.",
            )
        else:
            try:
                risk = self.risk_model.assess(patient, egfr_value)
            except Exception:
                logger.exception("risk_model_failed")
                risk = RiskAssessment(
                    status="unavailable",
                    note_vi="Mô hình nguy cơ gặp lỗi; kết luận chỉ dựa trên rule engine.",
                )
        risk.drivers = [
            f.label_vi
            for f in rules.findings
            if SEVERITY_RANK[f.severity] >= SEVERITY_RANK[Severity.MILD]
        ][:3]

        redacted_note = redact_text(patient.symptoms_note, self.settings.max_note_chars)
        used_llm = False
        llm_meta = meta_offline(self.settings.gemini_model)
        narrative = None

        client: GeminiClient | None = self.llm_client
        if client is None:
            reason = "Chưa cấu hình GEMINI_API_KEY hoặc MEDLAB_LLM_MODE=offline."
            llm_meta = meta_offline(self.settings.gemini_model, reason)
        else:
            prompt = build_prompt(
                patient=patient,
                findings=rules.findings,
                red_flags=rules.red_flags,
                risk=risk,
                egfr_value=egfr_value,
                egfr_computed=egfr_computed,
                redacted_note=redacted_note,
                missing_fields=data_quality.missing_fields,
            )
            result = client.analyze(prompt)
            llm_meta = result.meta
            if result.narrative is not None:
                sanitized = sanitize_narrative(result.narrative, rules.max_severity, rules.urgent)
                if sanitized is None:
                    llm_meta.status = "error"
                    llm_meta.fallback_reason = (
                        "Nội dung AI không vượt qua kiểm duyệt an toàn; dùng kết luận rule-based."
                    )
                else:
                    narrative = sanitized
                    used_llm = True

        if narrative is None:
            narrative = fallback_narrative(
                findings=rules.findings,
                red_flags=rules.red_flags,
                provided_fields=data_quality.fields_provided,
                expected_fields=data_quality.fields_expected,
                risk_band=risk.band,
            )

        conclusion = narrative.summary_vi
        if rules.urgent:
            conclusion = "CẦN ĐÁNH GIÁ Y TẾ NGAY. " + conclusion

        latency_ms = int((time.perf_counter() - started) * 1000)
        report = AnalysisReport(
            request_id=request_id,
            created_at=datetime.now(UTC),
            age_years=patient.age_years,
            sex=patient.sex,
            findings=rules.findings,
            red_flags=rules.red_flags,
            urgent=rules.urgent,
            risk=risk,
            summary_source="gemini" if used_llm else "offline",
            conclusion_vi=conclusion,
            key_points_vi=narrative.key_points_vi,
            when_to_seek_care_vi=narrative.when_to_seek_care_vi,
            lifestyle_vi=narrative.lifestyle_vi,
            llm=llm_meta,
            data_quality=data_quality,
            disclaimer_vi=DISCLAIMER_VI,
        )
        logger.info(
            "analysis_completed",
            extra={
                "request_id": request_id,
                "event": "analysis_completed",
                "status": "urgent" if rules.urgent else "normal",
                "latency_ms": latency_ms,
            },
        )
        return report
