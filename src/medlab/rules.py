from __future__ import annotations

from dataclasses import dataclass, field

from medlab.reference_ranges import (
    URINE_DIPSTICK_LABELS,
    format_value,
    get_spec,
    severity_for,
)
from medlab.schema import (
    SEVERITY_RANK,
    Dipstick,
    Finding,
    Nitrite,
    PatientInput,
    Severity,
)

SEVERITY_VI = {
    Severity.NORMAL: "bình thường",
    Severity.MILD: "nhẹ",
    Severity.MODERATE: "trung bình",
    Severity.SEVERE: "nặng",
    Severity.CRITICAL: "rất nặng",
}


@dataclass
class RuleResult:
    findings: list[Finding] = field(default_factory=list)
    red_flags: list[str] = field(default_factory=list)

    @property
    def urgent(self) -> bool:
        return bool(self.red_flags)

    @property
    def max_severity(self) -> Severity:
        if not self.findings:
            return Severity.NORMAL
        return max((f.severity for f in self.findings), key=lambda s: SEVERITY_RANK[s])


def _max_severity(*severities: Severity) -> Severity:
    return max(severities, key=lambda s: SEVERITY_RANK[s])


def _add(
    result: RuleResult,
    *,
    code: str,
    label: str,
    severity: Severity,
    message: str,
    value_display: str,
    reference_display: str,
    details: dict[str, str | float] | None = None,
    red_flag: str | None = None,
) -> None:
    if severity == Severity.NORMAL:
        return
    result.findings.append(
        Finding(
            code=code,
            label_vi=label,
            severity=severity,
            message_vi=message,
            value_display=value_display,
            reference_display=reference_display,
            details=details or {},
        )
    )
    if severity == Severity.CRITICAL:
        default_flag = f"{label}: {value_display} — giá trị nguy hiểm, cần xử trí y tế ngay."
        result.red_flags.append(red_flag or default_flag)
    elif red_flag:
        result.red_flags.append(red_flag)


def _numeric_findings(
    patient: PatientInput, result: RuleResult, egfr_value: float | None, egfr_computed: bool
) -> None:
    for key, value in patient.blood.values().items():
        spec = get_spec(key, patient.sex)
        severity = severity_for(value, spec)
        direction = "thấp" if value < spec.normal_low else "cao"
        value_display = format_value(value, spec)
        message = (
            f"{spec.label_vi} {direction} mức {SEVERITY_VI[severity]}: {value_display} "
            f"(tham chiếu {spec.reference_display})."
        )
        details: dict[str, str | float] = {"value": value, "direction": direction}
        if key == "egfr_ml_min_1_73m2" and egfr_computed:
            message += " Giá trị được ước tính từ creatinine bằng CKD-EPI 2021."
            details["computed"] = "ckd_epi_2021"
        _add(
            result,
            code=f"blood_{key}",
            label=spec.label_vi,
            severity=severity,
            message=message,
            value_display=value_display,
            reference_display=spec.reference_display,
            details=details,
        )

    for key in ("ph", "specific_gravity", "wbc_per_hpf", "rbc_per_hpf"):
        value = getattr(patient.urine, key)
        if value is None:
            continue
        spec = get_spec(key, patient.sex)
        severity = severity_for(value, spec)
        direction = "thấp" if value < spec.normal_low else "cao"
        _add(
            result,
            code=f"urine_{key}",
            label=spec.label_vi,
            severity=severity,
            message=(
                f"{spec.label_vi} {direction} mức {SEVERITY_VI[severity]}: "
                f"{format_value(value, spec)} (tham chiếu {spec.reference_display})."
            ),
            value_display=format_value(value, spec),
            reference_display=spec.reference_display,
            details={"value": value, "direction": direction},
        )


_DIPSTICK_SEVERITY: dict[str, dict[Dipstick, Severity]] = {
    "protein": {
        Dipstick.TRACE: Severity.MILD,
        Dipstick.ONE_PLUS: Severity.MODERATE,
        Dipstick.TWO_PLUS: Severity.MODERATE,
        Dipstick.THREE_PLUS: Severity.SEVERE,
        Dipstick.FOUR_PLUS: Severity.SEVERE,
    },
    "glucose": {
        Dipstick.TRACE: Severity.MILD,
        Dipstick.ONE_PLUS: Severity.MODERATE,
        Dipstick.TWO_PLUS: Severity.SEVERE,
        Dipstick.THREE_PLUS: Severity.SEVERE,
        Dipstick.FOUR_PLUS: Severity.SEVERE,
    },
    "ketones": {
        Dipstick.TRACE: Severity.MILD,
        Dipstick.ONE_PLUS: Severity.MODERATE,
        Dipstick.TWO_PLUS: Severity.SEVERE,
        Dipstick.THREE_PLUS: Severity.SEVERE,
        Dipstick.FOUR_PLUS: Severity.SEVERE,
    },
    "blood": {
        Dipstick.TRACE: Severity.MILD,
        Dipstick.ONE_PLUS: Severity.MODERATE,
        Dipstick.TWO_PLUS: Severity.MODERATE,
        Dipstick.THREE_PLUS: Severity.SEVERE,
        Dipstick.FOUR_PLUS: Severity.SEVERE,
    },
    "leukocyte_esterase": {
        Dipstick.TRACE: Severity.MILD,
        Dipstick.ONE_PLUS: Severity.MODERATE,
        Dipstick.TWO_PLUS: Severity.MODERATE,
        Dipstick.THREE_PLUS: Severity.SEVERE,
        Dipstick.FOUR_PLUS: Severity.SEVERE,
    },
}


def _dipstick_findings(patient: PatientInput, result: RuleResult) -> None:
    for key, mapping in _DIPSTICK_SEVERITY.items():
        value: Dipstick | None = getattr(patient.urine, key)
        if value is None:
            continue
        severity = mapping.get(value, Severity.NORMAL)
        label = URINE_DIPSTICK_LABELS[key]
        _add(
            result,
            code=f"urine_{key}",
            label=label,
            severity=severity,
            message=f"{label}: {value.label_vi} (tham chiếu: Âm tính).",
            value_display=value.label_vi,
            reference_display="Âm tính",
            details={"grade": int(value)},
        )

    if patient.urine.nitrite == Nitrite.POSITIVE:
        _add(
            result,
            code="urine_nitrite",
            label=URINE_DIPSTICK_LABELS["nitrite"],
            severity=Severity.MODERATE,
            message="Nitrit dương tính — gợi ý nhiễm khuẩn đường tiết niệu, cần đối chiếu triệu chứng và bạch cầu niệu.",
            value_display="Dương tính",
            reference_display="Âm tính",
        )


def _composite_findings(
    patient: PatientInput, result: RuleResult, egfr_value: float | None
) -> None:
    blood = patient.blood
    urine = patient.urine

    glucose = blood.fasting_glucose_mmol_l
    hba1c = blood.hba1c_percent
    if (glucose is not None and glucose >= 7.0) or (hba1c is not None and hba1c >= 6.5):
        severity = Severity.MODERATE
        if (glucose is not None and glucose >= 11.1) or (hba1c is not None and hba1c >= 8.0):
            severity = Severity.SEVERE
        if glucose is not None and glucose >= 25.0:
            severity = Severity.CRITICAL
        pieces = []
        if glucose is not None:
            pieces.append(f"glucose đói {glucose:g} mmol/L")
        if hba1c is not None:
            pieces.append(f"HbA1c {hba1c:g}%")
        _add(
            result,
            code="suspected_diabetes",
            label="Nghi ngờ đái tháo đường",
            severity=severity,
            message=(
                "Các chỉ số " + ", ".join(pieces) + " nằm trong ngưỡng gợi ý đái tháo đường; "
                "cần xét nghiệm xác nhận và bác sĩ đánh giá."
            ),
            value_display="; ".join(pieces),
            reference_display="Glucose <7,0 mmol/L; HbA1c <6,5%",
        )
    elif (glucose is not None and 5.6 <= glucose < 7.0) or (
        hba1c is not None and 5.7 <= hba1c < 6.5
    ):
        _add(
            result,
            code="prediabetes",
            label="Rối loạn glucose máu lúc đói / tiền đái tháo đường",
            severity=Severity.MILD,
            message=(
                "Glucose đói hoặc HbA1c ở mức tiền đái tháo đường; nên kiểm tra định kỳ, "
                "điều chỉnh dinh dưỡng và vận động."
            ),
            value_display=f"Glucose {glucose:g} mmol/L"
            if glucose is not None
            else f"HbA1c {hba1c:g}%",
            reference_display="Glucose <5,6 mmol/L; HbA1c <5,7%",
        )

    if egfr_value is not None and egfr_value < 60:
        severity = severity_for(egfr_value, get_spec("egfr_ml_min_1_73m2", patient.sex))
        _add(
            result,
            code="reduced_kidney_function",
            label="Suy giảm chức năng thận",
            severity=severity,
            message=(
                f"eGFR {egfr_value:g} mL/phút/1,73m² cho thấy chức năng thận giảm; "
                "cần đánh giá nguyên nhân, thuốc đang dùng và theo dõi định kỳ."
            ),
            value_display=f"{egfr_value:g} mL/phút/1,73m²",
            reference_display="≥60 (theo KDIGO)",
            details={
                "egfr": egfr_value,
                "computed": "locally" if blood.egfr_ml_min_1_73m2 is None else "lab",
            },
            red_flag="Suy thận nặng (eGFR <15) — cần đánh giá y tế khẩn cấp."
            if severity == Severity.CRITICAL
            else None,
        )

    ketones = urine.ketones
    if (
        ketones is not None
        and ketones >= Dipstick.TWO_PLUS
        and glucose is not None
        and glucose >= 13.9
    ):
        _add(
            result,
            code="dka_risk",
            label="Nguy cơ toan ceton do đái tháo đường",
            severity=Severity.CRITICAL,
            message=(
                "Glucose máu rất cao kèm ketone niệu ≥2+ gợi ý nguy cơ toan ceton (DKA); "
                "cần đến cơ sở y tế ngay để xét nghiệm khí máu/điện giải."
            ),
            value_display=f"Glucose {glucose:g} mmol/L; Ketone {ketones.label_vi}",
            reference_display="Ketone âm tính",
            red_flag="Nghi ngờ toan ceton do đái tháo đường (DKA) — cấp cứu ngay.",
        )

    nitrite_positive = urine.nitrite == Nitrite.POSITIVE
    pyuria = (urine.wbc_per_hpf is not None and urine.wbc_per_hpf > 5) or (
        urine.leukocyte_esterase is not None and urine.leukocyte_esterase >= Dipstick.ONE_PLUS
    )
    if nitrite_positive and pyuria:
        severity = Severity.MODERATE
        if (urine.wbc_per_hpf is not None and urine.wbc_per_hpf >= 50) or (
            urine.leukocyte_esterase is not None and urine.leukocyte_esterase >= Dipstick.THREE_PLUS
        ):
            severity = Severity.SEVERE
        _add(
            result,
            code="suspected_uti",
            label="Nghi ngờ nhiễm khuẩn đường tiết niệu",
            severity=severity,
            message=(
                "Nitrit dương tính kèm bạch cầu niệu tăng gợi ý nhiễm khuẩn đường tiết niệu; "
                "nên làm cấy nước tiểu và khám bác sĩ."
            ),
            value_display="Nitrit (+), có bạch cầu niệu",
            reference_display="Nitrit (-), bạch cầu niệu ≤5/HPF",
        )

    hematuria = (urine.rbc_per_hpf is not None and urine.rbc_per_hpf > 3) or (
        urine.blood is not None and urine.blood >= Dipstick.ONE_PLUS
    )
    if hematuria:
        severities = []
        if urine.rbc_per_hpf is not None and urine.rbc_per_hpf > 3:
            severities.append(severity_for(urine.rbc_per_hpf, get_spec("rbc_per_hpf", patient.sex)))
        if urine.blood is not None:
            severities.append(_DIPSTICK_SEVERITY["blood"].get(urine.blood, Severity.NORMAL))
        severity = _max_severity(*severities)
        _add(
            result,
            code="hematuria",
            label="Có máu trong nước tiểu",
            severity=severity,
            message="Phát hiện hồng cầu/máu trong nước tiểu; cần loại trừ nhiễm trùng, sỏi và bệnh lý thận–tiết niệu.",
            value_display="Hồng cầu/máu niệu dương tính",
            reference_display="≤3 RBC/HPF; máu niệu âm tính",
        )

    ldl = blood.ldl_mmol_l
    triglycerides = blood.triglycerides_mmol_l
    hdl = blood.hdl_mmol_l
    if ldl is not None or triglycerides is not None or hdl is not None:
        severities = []
        if ldl is not None:
            severities.append(severity_for(ldl, get_spec("ldl_mmol_l", patient.sex)))
        if triglycerides is not None:
            severities.append(
                severity_for(triglycerides, get_spec("triglycerides_mmol_l", patient.sex))
            )
        if hdl is not None:
            severities.append(severity_for(hdl, get_spec("hdl_mmol_l", patient.sex)))
        severity = _max_severity(*severities)
        if severity != Severity.NORMAL:
            _add(
                result,
                code="dyslipidemia",
                label="Rối loạn lipid máu",
                severity=severity,
                message=(
                    "Có bất thường trong bộ lipid máu (LDL-C, triglycerid hoặc HDL-C); "
                    "cần đánh giá nguy cơ tim mạch tổng thể và tư vấn dinh dưỡng."
                ),
                value_display="; ".join(
                    part
                    for part in (
                        f"LDL-C {ldl:g}" if ldl is not None else "",
                        f"TG {triglycerides:g}" if triglycerides is not None else "",
                        f"HDL-C {hdl:g}" if hdl is not None else "",
                    )
                    if part
                ),
                reference_display="LDL-C <2,59; TG <1,7; HDL-C ≥1,55",
            )

    sg = urine.specific_gravity
    sodium = blood.sodium_mmol_l
    if sg is not None and sg > 1.030:
        severity = Severity.MILD
        if sg >= 1.035 and sodium is not None and sodium > 145:
            severity = Severity.MODERATE
        _add(
            result,
            code="concentrated_urine",
            label="Nước tiểu cô đặc",
            severity=severity,
            message=(
                "Tỷ trọng nước tiểu cao, có thể gặp khi thiếu nước; "
                "nên uống đủ nước và kiểm tra lại nếu kéo dài."
            ),
            value_display=f"{sg:g}",
            reference_display="1,005–1,030",
        )

    low_hb = (
        blood.hemoglobin_g_l is not None
        and blood.hemoglobin_g_l < get_spec("hemoglobin_g_l", patient.sex).normal_low
    )
    low_wbc = (
        blood.wbc_10e9_l is not None
        and blood.wbc_10e9_l < get_spec("wbc_10e9_l", patient.sex).normal_low
    )
    low_plt = (
        blood.platelets_10e9_l is not None
        and blood.platelets_10e9_l < get_spec("platelets_10e9_l", patient.sex).normal_low
    )
    if low_hb and low_wbc and low_plt:
        _add(
            result,
            code="pancytopenia",
            label="Giảm cả ba dòng tế bào máu",
            severity=Severity.SEVERE,
            message=(
                "Hemoglobin, bạch cầu và tiểu cầu đều thấp — cần khám huyết học sớm "
                "để loại trừ nguyên nhân tủy xương hoặc bệnh lý nặng."
            ),
            value_display="Hb, WBC và PLT đều dưới ngưỡng",
            reference_display="Xem từng chỉ số",
            red_flag="Giảm cả ba dòng tế bào máu — cần đánh giá y tế sớm.",
        )

    if blood.wbc_10e9_l is not None and blood.wbc_10e9_l > 30 and (low_hb or low_plt):
        _add(
            result,
            code="hematologic_red_flag",
            label="Bất thường huyết học cần loại trừ bệnh lý nặng",
            severity=Severity.SEVERE,
            message=(
                "Bạch cầu tăng rất cao kèm thiếu máu/giảm tiểu cầu; cần khám chuyên khoa huyết học sớm."
            ),
            value_display=f"WBC {blood.wbc_10e9_l:g} ×10⁹/L",
            reference_display="4–10 ×10⁹/L",
            red_flag="Bạch cầu tăng rất cao kèm bất thường dòng khác — cần đánh giá huyết học sớm.",
        )

    if glucose is not None and glucose <= 3.0 and glucose > 2.5:
        _add(
            result,
            code="hypoglycemia",
            label="Hạ đường huyết",
            severity=Severity.MODERATE,
            message=(
                "Glucose đói thấp; nếu có run rẩy, vã mồ hôi, lú lẫn hoặc ngất cần xử trí và khám ngay."
            ),
            value_display=f"{glucose:g} mmol/L",
            reference_display="4,1–5,9 mmol/L",
            red_flag="Hạ đường huyết (glucose ≤3,0 mmol/L) — cần theo dõi và đánh giá y tế.",
        )


def _severe_red_flags(patient: PatientInput, result: RuleResult, egfr_value: float | None) -> None:
    blood = patient.blood
    urine = patient.urine

    if blood.hemoglobin_g_l is not None and blood.hemoglobin_g_l <= 80:
        result.red_flags.append("Thiếu máu nặng (Hb ≤80 g/L) — cần đánh giá y tế sớm.")
    if blood.platelets_10e9_l is not None and blood.platelets_10e9_l <= 50:
        result.red_flags.append("Tiểu cầu rất thấp (≤50 ×10⁹/L) — nguy cơ chảy máu, cần khám ngay.")
    if blood.wbc_10e9_l is not None and blood.wbc_10e9_l <= 1.5:
        result.red_flags.append("Bạch cầu rất thấp (≤1,5 ×10⁹/L) — nguy cơ nhiễm trùng nặng.")
    if blood.wbc_10e9_l is not None and blood.wbc_10e9_l >= 30:
        result.red_flags.append("Bạch cầu tăng rất cao (≥30 ×10⁹/L) — cần đánh giá huyết học sớm.")
    if egfr_value is not None and egfr_value < 30:
        result.red_flags.append("eGFR <30 mL/phút/1,73m² — suy thận nặng, cần đánh giá sớm.")
    if blood.fasting_glucose_mmol_l is not None and blood.fasting_glucose_mmol_l >= 11.1:
        result.red_flags.append("Tăng đường huyết nặng (≥11,1 mmol/L) — cần đánh giá y tế sớm.")
    if blood.sodium_mmol_l is not None and (
        blood.sodium_mmol_l <= 125 or blood.sodium_mmol_l >= 155
    ):
        result.red_flags.append("Rối loạn natri máu nặng — cần đánh giá y tế sớm.")
    if blood.potassium_mmol_l is not None and blood.potassium_mmol_l >= 6.0:
        result.red_flags.append(
            "Kali máu ≥6,0 mmol/L — nguy cơ rối loạn nhịp tim, cần xử trí ngay."
        )

    uti = next((finding for finding in result.findings if finding.code == "suspected_uti"), None)
    if uti is not None and uti.severity == Severity.SEVERE:
        result.red_flags.append(
            "Nhiễm khuẩn tiết niệu mức độ nặng — cần khám và cấy nước tiểu sớm."
        )

    if (
        urine.ketones is not None
        and urine.ketones >= Dipstick.TWO_PLUS
        and patient.blood.fasting_glucose_mmol_l is None
    ):
        result.red_flags.append("Ketone niệu ≥2+ — cần loại trừ toan ceton, nên khám sớm.")


def evaluate_rules(patient: PatientInput, egfr_value: float | None = None) -> RuleResult:
    result = RuleResult()
    egfr_computed = patient.blood.egfr_ml_min_1_73m2 is None and egfr_value is not None
    _numeric_findings(patient, result, egfr_value, egfr_computed)
    _dipstick_findings(patient, result)
    _composite_findings(patient, result, egfr_value)
    _severe_red_flags(patient, result, egfr_value)

    seen_codes: set[str] = set()
    unique: list[Finding] = []
    for finding in sorted(result.findings, key=lambda f: SEVERITY_RANK[f.severity], reverse=True):
        if finding.code in seen_codes:
            continue
        seen_codes.add(finding.code)
        unique.append(finding)
    result.findings = unique
    result.red_flags = list(dict.fromkeys(result.red_flags))
    return result
