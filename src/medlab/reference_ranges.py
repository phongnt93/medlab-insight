from __future__ import annotations

from dataclasses import dataclass

from medlab.schema import Severity, Sex


@dataclass(frozen=True)
class NumericSpec:
    key: str
    label_vi: str
    unit: str
    normal_low: float
    normal_high: float
    moderate_low: float | None = None
    severe_low: float | None = None
    critical_low: float | None = None
    moderate_high: float | None = None
    severe_high: float | None = None
    critical_high: float | None = None
    display_range: str | None = None

    @property
    def reference_display(self) -> str:
        if self.display_range:
            return f"{self.display_range} {self.unit}".strip()
        return f"{self.normal_low:g}–{self.normal_high:g} {self.unit}".strip()


_COMMON: dict[str, NumericSpec] = {
    "wbc_10e9_l": NumericSpec(
        "wbc_10e9_l",
        "Bạch cầu (WBC)",
        "×10⁹/L",
        4.0,
        10.0,
        moderate_low=2.5,
        severe_low=1.5,
        critical_low=0.5,
        moderate_high=15.0,
        severe_high=30.0,
        critical_high=50.0,
    ),
    "platelets_10e9_l": NumericSpec(
        "platelets_10e9_l",
        "Tiểu cầu (PLT)",
        "×10⁹/L",
        150,
        400,
        moderate_low=100,
        severe_low=50,
        critical_low=20,
        moderate_high=600,
        severe_high=1000,
        critical_high=1500,
    ),
    "fasting_glucose_mmol_l": NumericSpec(
        "fasting_glucose_mmol_l",
        "Glucose đói",
        "mmol/L",
        4.1,
        5.9,
        moderate_low=3.0,
        severe_low=2.5,
        critical_low=2.5,
        moderate_high=6.9,
        severe_high=11.0,
        critical_high=25.0,
    ),
    "hba1c_percent": NumericSpec(
        "hba1c_percent",
        "HbA1c",
        "%",
        4.0,
        5.6,
        moderate_low=3.5,
        severe_low=3.0,
        critical_low=None,
        moderate_high=6.4,
        severe_high=8.0,
        critical_high=10.0,
    ),
    "egfr_ml_min_1_73m2": NumericSpec(
        "egfr_ml_min_1_73m2",
        "eGFR (CKD-EPI 2021)",
        "mL/phút/1,73m²",
        90,
        250,
        moderate_low=60,
        severe_low=30,
        critical_low=15,
        display_range="≥90",
    ),
    "alt_u_l": NumericSpec(
        "alt_u_l",
        "ALT (SGPT)",
        "U/L",
        0,
        50,
        moderate_high=150,
        severe_high=500,
        critical_high=1500,
        display_range="<50",
    ),
    "ast_u_l": NumericSpec(
        "ast_u_l",
        "AST (SGOT)",
        "U/L",
        0,
        50,
        moderate_high=150,
        severe_high=500,
        critical_high=1500,
        display_range="<50",
    ),
    "total_cholesterol_mmol_l": NumericSpec(
        "total_cholesterol_mmol_l",
        "Cholesterol toàn phần",
        "mmol/L",
        0,
        5.2,
        moderate_high=6.2,
        severe_high=7.8,
        display_range="<5,2",
    ),
    "ldl_mmol_l": NumericSpec(
        "ldl_mmol_l",
        "LDL-C",
        "mmol/L",
        0,
        2.59,
        moderate_high=3.4,
        severe_high=4.9,
        display_range="<2,59",
    ),
    "triglycerides_mmol_l": NumericSpec(
        "triglycerides_mmol_l",
        "Triglycerid",
        "mmol/L",
        0,
        1.7,
        moderate_high=2.3,
        severe_high=5.6,
        critical_high=11.3,
        display_range="<1,7",
    ),
    "crp_mg_l": NumericSpec(
        "crp_mg_l",
        "CRP",
        "mg/L",
        0,
        5,
        moderate_high=10,
        severe_high=50,
        critical_high=200,
        display_range="<5",
    ),
    "hdl_mmol_l": NumericSpec(
        "hdl_mmol_l",
        "HDL-C",
        "mmol/L",
        1.55,
        5.0,
        moderate_low=1.1,
        severe_low=0.8,
        display_range="≥1,55",
    ),
    "sodium_mmol_l": NumericSpec(
        "sodium_mmol_l",
        "Natri (Na⁺)",
        "mmol/L",
        136,
        145,
        moderate_low=130,
        severe_low=125,
        critical_low=120,
        moderate_high=150,
        severe_high=155,
        critical_high=160,
    ),
    "potassium_mmol_l": NumericSpec(
        "potassium_mmol_l",
        "Kali (K⁺)",
        "mmol/L",
        3.4,
        4.5,
        moderate_low=3.0,
        severe_low=2.5,
        critical_low=2.5,
        moderate_high=5.0,
        severe_high=5.5,
        critical_high=6.0,
    ),
    "chloride_mmol_l": NumericSpec(
        "chloride_mmol_l",
        "Clo (Cl⁻)",
        "mmol/L",
        98,
        107,
        moderate_low=90,
        severe_low=80,
        critical_low=70,
        moderate_high=115,
        severe_high=125,
        critical_high=140,
    ),
    "bun_mmol_l": NumericSpec(
        "bun_mmol_l",
        "Uré (BUN)",
        "mmol/L",
        2.76,
        8.07,
        moderate_low=2.0,
        moderate_high=17.0,
        severe_high=30.0,
        critical_high=50.0,
    ),
    "uric_acid_umol_l": NumericSpec(
        "uric_acid_umol_l",
        "Acid uric",
        "µmol/L",
        202,
        417,
        moderate_high=475,
        severe_high=600,
        critical_high=800,
    ),
    "rbc_t_l": NumericSpec(
        "rbc_t_l",
        "RBC (số lượng hồng cầu)",
        "T/L",
        4.37,
        5.69,
        moderate_low=3.5,
        severe_low=2.5,
        critical_low=1.5,
        moderate_high=6.2,
        severe_high=7.0,
        critical_high=8.0,
    ),
    "hct_l_l": NumericSpec(
        "hct_l_l",
        "HCT (hematocrit)",
        "L/L",
        0.41,
        0.53,
        moderate_low=0.33,
        severe_low=0.24,
        critical_low=0.18,
        moderate_high=0.60,
        severe_high=0.65,
    ),
    "mcv_fl": NumericSpec(
        "mcv_fl",
        "MCV (thể tích trung bình HC)",
        "fL",
        80,
        100,
        moderate_low=75,
        severe_low=70,
        moderate_high=105,
        severe_high=112,
    ),
    "mch_pg": NumericSpec(
        "mch_pg",
        "MCH (lượng Hb trung bình HC)",
        "pg",
        26,
        34,
        moderate_low=24,
        severe_low=20,
        moderate_high=36,
        severe_high=40,
    ),
    "mchc_g_l": NumericSpec(
        "mchc_g_l",
        "MCHC (nồng độ Hb trung bình HC)",
        "g/L",
        315,
        363,
        moderate_low=300,
        severe_low=280,
        moderate_high=370,
        severe_high=385,
    ),
    "rdw_cv_percent": NumericSpec(
        "rdw_cv_percent",
        "RDW-CV (phân bố kích thước HC)",
        "%",
        10,
        15,
        moderate_high=16.5,
        severe_high=18.0,
    ),
    "mpv_fl": NumericSpec(
        "mpv_fl",
        "MPV (thể tích trung bình TC)",
        "fL",
        5,
        20,
        moderate_low=4,
        severe_low=3,
        moderate_high=25,
        severe_high=30,
    ),
    "neut_percent": NumericSpec(
        "neut_percent",
        "NEUT% (tỷ lệ BC trung tính)",
        "%",
        45,
        75,
        moderate_low=40,
        severe_low=30,
        critical_low=10,
        moderate_high=85,
        severe_high=95,
    ),
    "lym_percent": NumericSpec(
        "lym_percent",
        "LYM% (tỷ lệ BC lympho)",
        "%",
        25,
        45,
        moderate_low=15,
        severe_low=8,
        moderate_high=55,
        severe_high=65,
    ),
    "mono_percent": NumericSpec(
        "mono_percent",
        "MONO% (tỷ lệ BC mono)",
        "%",
        0,
        8,
        moderate_high=15,
        severe_high=30,
    ),
    "eo_percent": NumericSpec(
        "eo_percent",
        "EO% (tỷ lệ BC ưa axit)",
        "%",
        0,
        8,
        moderate_high=20,
        severe_high=50,
    ),
    "baso_percent": NumericSpec(
        "baso_percent",
        "BASO% (tỷ lệ BC ưa bazo)",
        "%",
        0,
        1,
        moderate_high=3,
        severe_high=10,
    ),
    "neut_abs_10e9_l": NumericSpec(
        "neut_abs_10e9_l",
        "NEUT# (BC trung tính)",
        "×10⁹/L",
        1.8,
        7.5,
        moderate_low=1.0,
        severe_low=0.5,
        critical_low=0.2,
        moderate_high=10,
        severe_high=15,
    ),
    "lym_abs_10e9_l": NumericSpec(
        "lym_abs_10e9_l",
        "LYM# (BC lympho)",
        "×10⁹/L",
        1.0,
        4.5,
        moderate_low=0.6,
        severe_low=0.3,
        moderate_high=6.0,
        severe_high=10.0,
    ),
    "mono_abs_10e9_l": NumericSpec(
        "mono_abs_10e9_l",
        "MONO# (BC mono)",
        "×10⁹/L",
        0,
        0.8,
        moderate_high=1.5,
        severe_high=3.0,
    ),
    "eo_abs_10e9_l": NumericSpec(
        "eo_abs_10e9_l",
        "EO# (BC ưa axit)",
        "×10⁹/L",
        0,
        0.8,
        moderate_high=2.0,
        severe_high=5.0,
    ),
    "baso_abs_10e9_l": NumericSpec(
        "baso_abs_10e9_l",
        "BASO# (BC ưa bazo)",
        "×10⁹/L",
        0,
        0.1,
        moderate_high=0.3,
        severe_high=1.0,
    ),
    "ph": NumericSpec(
        "ph",
        "pH nước tiểu",
        "",
        5.0,
        8.0,
        moderate_low=4.5,
        severe_low=4.0,
        moderate_high=8.5,
        severe_high=9.0,
    ),
    "specific_gravity": NumericSpec(
        "specific_gravity",
        "Tỷ trọng nước tiểu",
        "",
        1.005,
        1.030,
        moderate_low=1.001,
        severe_low=1.000,
        moderate_high=1.035,
        severe_high=1.040,
    ),
    "wbc_per_hpf": NumericSpec(
        "wbc_per_hpf",
        "Bạch cầu niệu",
        "/HPF",
        0,
        5,
        moderate_high=20,
        severe_high=50,
        display_range="≤5",
    ),
    "rbc_per_hpf": NumericSpec(
        "rbc_per_hpf",
        "Hồng cầu niệu",
        "/HPF",
        0,
        3,
        moderate_high=20,
        severe_high=50,
        display_range="≤3",
    ),
}

_SEX_SPECIFIC: dict[str, dict[Sex, NumericSpec]] = {
    "hemoglobin_g_l": {
        Sex.MALE: NumericSpec(
            "hemoglobin_g_l",
            "Hemoglobin (Hb)",
            "g/L",
            136,
            175,
            moderate_low=110,
            severe_low=80,
            critical_low=70,
            critical_high=220,
        ),
        Sex.FEMALE: NumericSpec(
            "hemoglobin_g_l",
            "Hemoglobin (Hb)",
            "g/L",
            120,
            155,
            moderate_low=110,
            severe_low=80,
            critical_low=70,
            critical_high=220,
        ),
        Sex.OTHER: NumericSpec(
            "hemoglobin_g_l",
            "Hemoglobin (Hb)",
            "g/L",
            120,
            175,
            moderate_low=110,
            severe_low=80,
            critical_low=70,
            critical_high=220,
        ),
    },
    "creatinine_umol_l": {
        Sex.MALE: NumericSpec(
            "creatinine_umol_l",
            "Creatinine",
            "µmol/L",
            60,
            110,
            moderate_high=200,
            severe_high=450,
            critical_high=700,
        ),
        Sex.FEMALE: NumericSpec(
            "creatinine_umol_l",
            "Creatinine",
            "µmol/L",
            45,
            90,
            moderate_high=170,
            severe_high=400,
            critical_high=600,
        ),
        Sex.OTHER: NumericSpec(
            "creatinine_umol_l",
            "Creatinine",
            "µmol/L",
            50,
            110,
            moderate_high=200,
            severe_high=450,
            critical_high=700,
        ),
    },
}

URINE_DIPSTICK_LABELS: dict[str, str] = {
    "protein": "Protein niệu",
    "glucose": "Glucose niệu",
    "ketones": "Ketone niệu",
    "blood": "Máu niệu",
    "leukocyte_esterase": "Bạch cầu esterase",
    "nitrite": "Nitrit",
}


def get_spec(key: str, sex: Sex) -> NumericSpec:
    if key in _COMMON:
        return _COMMON[key]
    if key in _SEX_SPECIFIC:
        return _SEX_SPECIFIC[key][sex]
    raise KeyError(f"Không có tham chiếu cho chỉ số: {key}")


def all_specs(sex: Sex) -> dict[str, NumericSpec]:
    keys = list(_COMMON) + list(_SEX_SPECIFIC)
    return {key: get_spec(key, sex) for key in keys}


def severity_for(value: float, spec: NumericSpec) -> Severity:
    if spec.critical_low is not None and value <= spec.critical_low:
        return Severity.CRITICAL
    if spec.critical_high is not None and value >= spec.critical_high:
        return Severity.CRITICAL
    if spec.severe_low is not None and value <= spec.severe_low:
        return Severity.SEVERE
    if spec.severe_high is not None and value >= spec.severe_high:
        return Severity.SEVERE
    if spec.moderate_low is not None and value <= spec.moderate_low:
        return Severity.MODERATE
    if spec.moderate_high is not None and value >= spec.moderate_high:
        return Severity.MODERATE
    if value < spec.normal_low or value > spec.normal_high:
        return Severity.MILD
    return Severity.NORMAL


def direction_for(value: float, spec: NumericSpec) -> str:
    if value < spec.normal_low:
        return "low"
    if value > spec.normal_high:
        return "high"
    return "normal"


def format_value(value: float, spec: NumericSpec) -> str:
    if (
        spec.unit == ""
        or spec.unit == "g/L"
        or spec.unit == "µmol/L"
        or spec.unit == "U/L"
        or spec.unit == "mg/L"
        or spec.unit == "×10⁹/L"
    ):
        text = f"{value:g}"
    else:
        text = f"{value:g}"
    return f"{text} {spec.unit}".strip()
