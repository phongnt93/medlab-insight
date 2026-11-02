from __future__ import annotations

from typing import Any

import streamlit as st
from pydantic import ValidationError

from medlab.analyzer import AnalysisEngine
from medlab.config import get_settings
from medlab.rules import SEVERITY_VI
from medlab.schema import (
    SEVERITY_RANK,
    BloodPanel,
    Dipstick,
    Nitrite,
    PatientInput,
    Severity,
    Sex,
    UrinePanel,
)

st.set_page_config(
    page_title="MedLab Insight",
    layout="wide",
)


@st.cache_resource(show_spinner=False)
def get_engine() -> AnalysisEngine:
    return AnalysisEngine(settings=get_settings())


DIPSTICK_OPTIONS: dict[str, Dipstick | None] = {
    "Không nhập": None,
    "Âm tính": Dipstick.NEGATIVE,
    "Vết": Dipstick.TRACE,
    "1+": Dipstick.ONE_PLUS,
    "2+": Dipstick.TWO_PLUS,
    "3+": Dipstick.THREE_PLUS,
    "4+": Dipstick.FOUR_PLUS,
}
NITRITE_OPTIONS: dict[str, Nitrite | None] = {
    "Không nhập": None,
    "Âm tính": Nitrite.NEGATIVE,
    "Dương tính": Nitrite.POSITIVE,
}
SEX_OPTIONS: dict[str, Sex] = {
    "Nam": Sex.MALE,
    "Nữ": Sex.FEMALE,
    "Khác": Sex.OTHER,
}


def _num(
    key: str, label: str, *, min_value: float, max_value: float, step: float, help_text: str = ""
) -> float | None:
    value = st.number_input(
        label,
        min_value=float(min_value),
        max_value=float(max_value),
        value=None,
        step=float(step),
        key=key,
        help=help_text or None,
        placeholder="Để trống nếu không có",
    )
    return None if value is None else float(value)


def _select(key: str, label: str, options: dict[str, Any]) -> Any:
    choice = st.selectbox(label, list(options.keys()), key=key)
    return options[choice]


def _state_num(key: str) -> float | None:
    value = st.session_state.get(key)
    return None if value is None else float(value)


def _state_select(key: str, options: dict[str, Any]) -> Any:
    return options.get(st.session_state.get(key))


def _build_patient() -> PatientInput:
    blood = BloodPanel(
        hemoglobin_g_l=_state_num("blood_hb"),
        wbc_10e9_l=_state_num("blood_wbc"),
        platelets_10e9_l=_state_num("blood_plt"),
        fasting_glucose_mmol_l=_state_num("blood_glucose"),
        hba1c_percent=_state_num("blood_hba1c"),
        creatinine_umol_l=_state_num("blood_creatinine"),
        egfr_ml_min_1_73m2=_state_num("blood_egfr"),
        alt_u_l=_state_num("blood_alt"),
        ast_u_l=_state_num("blood_ast"),
        total_cholesterol_mmol_l=_state_num("blood_chol"),
        ldl_mmol_l=_state_num("blood_ldl"),
        hdl_mmol_l=_state_num("blood_hdl"),
        triglycerides_mmol_l=_state_num("blood_tg"),
        crp_mg_l=_state_num("blood_crp"),
        sodium_mmol_l=_state_num("blood_na"),
        potassium_mmol_l=_state_num("blood_k"),
        chloride_mmol_l=_state_num("blood_cl"),
        bun_mmol_l=_state_num("blood_bun"),
        uric_acid_umol_l=_state_num("blood_uric"),
        rbc_t_l=_state_num("blood_rbc"),
        hct_l_l=_state_num("blood_hct"),
        mcv_fl=_state_num("blood_mcv"),
        mch_pg=_state_num("blood_mch"),
        mchc_g_l=_state_num("blood_mchc"),
        rdw_cv_percent=_state_num("blood_rdw"),
        mpv_fl=_state_num("blood_mpv"),
        neut_percent=_state_num("blood_neut_pct"),
        lym_percent=_state_num("blood_lym_pct"),
        mono_percent=_state_num("blood_mono_pct"),
        eo_percent=_state_num("blood_eo_pct"),
        baso_percent=_state_num("blood_baso_pct"),
        neut_abs_10e9_l=_state_num("blood_neut_abs"),
        lym_abs_10e9_l=_state_num("blood_lym_abs"),
        mono_abs_10e9_l=_state_num("blood_mono_abs"),
        eo_abs_10e9_l=_state_num("blood_eo_abs"),
        baso_abs_10e9_l=_state_num("blood_baso_abs"),
    )
    urine = UrinePanel(
        ph=_state_num("urine_ph"),
        specific_gravity=_state_num("urine_sg"),
        protein=_state_select("urine_protein", DIPSTICK_OPTIONS),
        glucose=_state_select("urine_glucose", DIPSTICK_OPTIONS),
        ketones=_state_select("urine_ketones", DIPSTICK_OPTIONS),
        blood=_state_select("urine_blood", DIPSTICK_OPTIONS),
        leukocyte_esterase=_state_select("urine_le", DIPSTICK_OPTIONS),
        nitrite=_state_select("urine_nitrite", NITRITE_OPTIONS),
        wbc_per_hpf=_state_num("urine_wbc"),
        rbc_per_hpf=_state_num("urine_rbc"),
    )
    return PatientInput(
        age_years=int(st.session_state.get("age", 35)),
        sex=SEX_OPTIONS[st.session_state.get("sex_label", "Nam")],
        symptoms_note=st.session_state.get("note") or None,
        blood=blood,
        urine=urine,
    )


def _format_errors(exc: ValidationError) -> list[str]:
    messages = []
    for error in exc.errors():
        location = " → ".join(str(part) for part in error["loc"])
        messages.append(f"{location}: {error['msg']}")
    return messages


def _render_report(report: Any) -> None:
    if report.urgent:
        flags = "\n".join(f"- {flag}" for flag in report.red_flags)
        st.error(f"### Cần đánh giá y tế ngay\n{flags}")
    elif report.risk.band == "high":
        st.warning("Mô hình nguy cơ ước tính mức cao. Nên khám bác sĩ sớm.")

    max_severity = max(
        (finding.severity for finding in report.findings),
        key=lambda severity: SEVERITY_RANK[severity],
        default=Severity.NORMAL,
    )
    col1, col2, col3 = st.columns(3)
    probability = (
        f"{report.risk.probability * 100:.1f}%"
        if report.risk.probability is not None
        else "Không có"
    )
    col1.metric("Nguy cơ cần đánh giá (mô hình)", probability, help=report.risk.note_vi)
    col2.metric("Mức bất thường cao nhất", SEVERITY_VI[max_severity])
    col3.metric(
        "Dữ liệu đã nhập",
        f"{report.data_quality.fields_provided}/{report.data_quality.fields_expected}",
    )

    if report.summary_source == "gemini":
        st.success("Kết luận do Gemini diễn giải và đã qua lớp kiểm duyệt nội dung an toàn.")
    elif report.llm.status == "error":
        st.warning(
            "Gemini không khả dụng hoặc phản hồi không an toàn; đang dùng kết luận rule-based. "
            f"Lý do: {report.llm.fallback_reason or 'không rõ'}"
        )
    else:
        st.info(
            "Đang chạy chế độ offline (rule-based + mô hình nguy cơ). "
            "Thiết lập GEMINI_API_KEY để bật phần diễn giải bằng Gemini."
        )

    st.subheader("Kết luận")
    st.markdown(report.conclusion_vi)
    if report.key_points_vi:
        for point in report.key_points_vi:
            st.markdown(f"- {point}")

    left, right = st.columns(2)
    with left:
        st.subheader("Khi nào cần đi khám")
        for item in report.when_to_seek_care_vi:
            st.markdown(f"- {item}")
    with right:
        st.subheader("Khuyến nghị chung")
        for item in report.lifestyle_vi:
            st.markdown(f"- {item}")

    if report.findings:
        st.subheader("Chỉ số bất thường")
        rows = [
            {
                "Mức độ": SEVERITY_VI[finding.severity],
                "Chỉ số": finding.label_vi,
                "Giá trị": finding.value_display,
                "Tham chiếu": finding.reference_display,
                "Diễn giải": finding.message_vi,
            }
            for finding in report.findings
        ]
        st.dataframe(rows, use_container_width=True, hide_index=True)
    else:
        st.success("Không ghi nhận chỉ số nằm ngoài ngưỡng tham chiếu trong dữ liệu đã nhập.")

    if report.data_quality.notes_vi:
        st.subheader("Lưu ý về dữ liệu")
        for note in report.data_quality.notes_vi:
            st.markdown(f"- {note}")
        with st.expander("Các chỉ số còn thiếu"):
            st.write(", ".join(report.data_quality.missing_fields) or "Không có")

    with st.expander("Chi tiết kỹ thuật & kiểm toán"):
        st.write(
            {
                "request_id": report.request_id,
                "created_at": report.created_at.isoformat(),
                "summary_source": report.summary_source,
                "llm_status": report.llm.status,
                "llm_model": report.llm.model,
                "llm_latency_ms": report.llm.latency_ms,
                "llm_attempts": report.llm.attempts,
                "risk_model": report.risk.model_version,
                "risk_status": report.risk.status,
                "risk_drivers": report.risk.drivers,
            }
        )
    st.caption(report.disclaimer_vi)


st.title("MedLab Insight")
st.caption(
    "Nhập kết quả xét nghiệm máu và nước tiểu để nhận diễn giải sàng lọc. Không nhập họ tên, CCCD hay số điện thoại."
)

settings = get_settings()
engine = get_engine()

with st.sidebar:
    st.header("Trạng thái hệ thống")
    if settings.gemini_api_key:
        st.success(f"Gemini: {settings.gemini_model}")
    else:
        st.warning("Gemini: offline (chưa có GEMINI_API_KEY)")
    if engine.risk_model is not None:
        st.info(f"Risk model: {engine.risk_model.version}")
    else:
        st.warning("Risk model: chưa có artifact (chạy `make train`)")
    st.divider()
    st.caption(
        "Dữ liệu chỉ được gửi tới Gemini khi có API key; họ tên/CCCD/số điện thoại trong ghi chú "
        "sẽ được ẩn danh trước khi gửi. Không dùng ứng dụng cho cấp cứu."
    )
    if st.button("Xóa kết quả", key="reset_report"):
        st.session_state.pop("report", None)
        st.session_state.pop("input_error", None)

with st.form("lab_form"):
    top_left, top_right = st.columns([1, 2])
    with top_left:
        st.number_input("Tuổi (năm)", min_value=0, max_value=120, value=35, step=1, key="age")
        st.selectbox("Giới tính", list(SEX_OPTIONS.keys()), key="sex_label")
    with top_right:
        st.text_area(
            "Triệu chứng / ghi chú (không nhập thông tin định danh)",
            max_chars=500,
            key="note",
            placeholder="Ví dụ: mệt mỏi 2 tuần, tiểu buốt 3 ngày...",
        )

    blood_tab, urine_tab = st.tabs(["Xét nghiệm máu", "Xét nghiệm nước tiểu"])
    with blood_tab:
        st.subheader("Sinh hóa")
        s1, s2, s3 = st.columns(3)
        with s1:
            _num("blood_glucose", "Glucose đói (mmol/L)", min_value=0, max_value=100, step=0.1)
            _num("blood_hba1c", "HbA1c (%)", min_value=0, max_value=25, step=0.1)
            _num("blood_bun", "Uré / BUN (mmol/L)", min_value=0, max_value=80, step=0.01)
            _num("blood_uric", "Acid uric (µmol/L)", min_value=0, max_value=1500, step=1)
        with s2:
            _num(
                "blood_chol", "Cholesterol toàn phần (mmol/L)", min_value=0, max_value=50, step=0.01
            )
            _num("blood_tg", "Triglycerid (mmol/L)", min_value=0, max_value=60, step=0.01)
            _num("blood_hdl", "HDL-C (mmol/L)", min_value=0, max_value=15, step=0.01)
            _num("blood_ldl", "LDL-C (mmol/L)", min_value=0, max_value=30, step=0.01)
        with s3:
            _num(
                "blood_egfr",
                "eGFR (mL/phút/1,73m²)",
                min_value=0,
                max_value=250,
                step=1,
                help_text="Để trống để tự ước tính bằng CKD-EPI 2021 (người ≥18 tuổi).",
            )
            _num("blood_creatinine", "Creatinine (µmol/L)", min_value=0, max_value=3000, step=1)
            _num("blood_alt", "ALT / SGPT (U/L)", min_value=0, max_value=20000, step=1)
            _num("blood_ast", "AST / SGOT (U/L)", min_value=0, max_value=20000, step=1)
            _num("blood_crp", "CRP (mg/L)", min_value=0, max_value=1000, step=0.1)

        st.subheader("Điện giải")
        e1, e2, e3 = st.columns(3)
        with e1:
            _num("blood_na", "Natri Na⁺ (mmol/L)", min_value=80, max_value=220, step=1)
        with e2:
            _num("blood_k", "Kali K⁺ (mmol/L)", min_value=0, max_value=15, step=0.1)
        with e3:
            _num("blood_cl", "Clo Cl⁻ (mmol/L)", min_value=50, max_value=180, step=1)

        st.subheader("Công thức máu (tổng phân tích tế bào máu)")
        c1, c2, c3 = st.columns(3)
        with c1:
            _num("blood_hb", "Hemoglobin HGB (g/L)", min_value=0, max_value=300, step=1)
            _num("blood_rbc", "RBC hồng cầu (T/L)", min_value=0, max_value=15, step=0.01)
            _num("blood_hct", "HCT hematocrit (L/L)", min_value=0, max_value=0.8, step=0.001)
        with c2:
            _num("blood_mcv", "MCV (fL)", min_value=40, max_value=160, step=0.1)
            _num("blood_mch", "MCH (pg)", min_value=10, max_value=60, step=0.1)
            _num("blood_mchc", "MCHC (g/L)", min_value=250, max_value=450, step=1)
            _num("blood_rdw", "RDW-CV (%)", min_value=5, max_value=50, step=0.1)
        with c3:
            _num("blood_wbc", "WBC bạch cầu (×10⁹/L)", min_value=0, max_value=300, step=0.1)
            _num("blood_plt", "PLT tiểu cầu (×10⁹/L)", min_value=0, max_value=3000, step=1)
            _num("blood_mpv", "MPV (fL)", min_value=0, max_value=50, step=0.1)

        st.subheader("Bạch cầu phân loại")
        d1, d2 = st.columns(2)
        with d1:
            _num("blood_neut_pct", "NEUT% (%)", min_value=0, max_value=100, step=0.1)
            _num("blood_lym_pct", "LYM% (%)", min_value=0, max_value=100, step=0.1)
            _num("blood_mono_pct", "MONO% (%)", min_value=0, max_value=100, step=0.1)
            _num("blood_eo_pct", "EO% (%)", min_value=0, max_value=100, step=0.1)
            _num("blood_baso_pct", "BASO% (%)", min_value=0, max_value=100, step=0.1)
        with d2:
            _num("blood_neut_abs", "NEUT# (×10⁹/L)", min_value=0, max_value=100, step=0.1)
            _num("blood_lym_abs", "LYM# (×10⁹/L)", min_value=0, max_value=100, step=0.1)
            _num("blood_mono_abs", "MONO# (×10⁹/L)", min_value=0, max_value=100, step=0.1)
            _num("blood_eo_abs", "EO# (×10⁹/L)", min_value=0, max_value=100, step=0.1)
            _num("blood_baso_abs", "BASO# (×10⁹/L)", min_value=0, max_value=100, step=0.1)
    with urine_tab:
        u1, u2, u3 = st.columns(3)
        with u1:
            _num("urine_ph", "pH nước tiểu", min_value=0, max_value=14, step=0.1)
            _num("urine_sg", "Tỷ trọng nước tiểu", min_value=1.0, max_value=1.06, step=0.001)
            _num("urine_wbc", "Bạch cầu niệu (/HPF)", min_value=0, max_value=10000, step=1)
            _num("urine_rbc", "Hồng cầu niệu (/HPF)", min_value=0, max_value=10000, step=1)
        with u2:
            _select("urine_protein", "Protein niệu", DIPSTICK_OPTIONS)
            _select("urine_glucose", "Glucose niệu", DIPSTICK_OPTIONS)
            _select("urine_ketones", "Ketone niệu", DIPSTICK_OPTIONS)
        with u3:
            _select("urine_blood", "Máu niệu", DIPSTICK_OPTIONS)
            _select("urine_le", "Bạch cầu esterase", DIPSTICK_OPTIONS)
            _select("urine_nitrite", "Nitrit", NITRITE_OPTIONS)

    consent_required = engine.llm_client is not None
    st.checkbox(
        "Tôi đồng ý xử lý dữ liệu xét nghiệm để phân tích"
        + (" và gửi dữ liệu đã ẩn danh tới Gemini" if consent_required else ""),
        key="consent",
    )
    submitted = st.form_submit_button("Phân tích", type="primary", key="submit")

if submitted:
    if not st.session_state.get("consent"):
        st.session_state["input_error"] = ["Bạn cần đồng ý xử lý dữ liệu trước khi phân tích."]
        st.session_state.pop("report", None)
    else:
        try:
            patient = _build_patient()
        except ValidationError as exc:
            st.session_state["input_error"] = _format_errors(exc)
            st.session_state.pop("report", None)
        except Exception:
            st.session_state["input_error"] = [
                "Không đọc được dữ liệu nhập. Vui lòng kiểm tra lại các ô."
            ]
            st.session_state.pop("report", None)
        else:
            st.session_state.pop("input_error", None)
            with st.spinner("Đang phân tích kết quả..."):
                try:
                    st.session_state["report"] = engine.analyze(patient)
                except Exception:
                    st.session_state["input_error"] = [
                        "Hệ thống gặp lỗi khi phân tích. Vui lòng thử lại hoặc kiểm tra log dịch vụ."
                    ]
                    st.session_state.pop("report", None)

for message in st.session_state.get("input_error", []):
    st.error(message)

if "report" in st.session_state:
    _render_report(st.session_state["report"])
