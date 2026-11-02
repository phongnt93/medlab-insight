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
        3.9,
        5.6,
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
    "ast_u_l": NumericSpec(
        "ast_u_l",
        "AST (SGOT)",
        "U/L",
        10,
        40,
        moderate_low=5,
        severe_low=None,
        critical_low=None,
        moderate_high=120,
        severe_high=400,
        critical_high=1000,
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
        3.4,
        moderate_high=4.1,
        severe_high=4.9,
        display_range="<3,4",
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
    "sodium_mmol_l": NumericSpec(
        "sodium_mmol_l",
        "Natri (Na⁺)",
        "mmol/L",
        135,
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
        3.5,
        5.0,
        moderate_low=3.0,
        severe_low=2.5,
        critical_low=2.5,
        moderate_high=5.5,
        severe_high=6.0,
        critical_high=6.5,
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
            130,
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
    "alt_u_l": {
        Sex.MALE: NumericSpec(
            "alt_u_l",
            "ALT (SGPT)",
            "U/L",
            10,
            40,
            moderate_low=5,
            moderate_high=120,
            severe_high=400,
            critical_high=1000,
        ),
        Sex.FEMALE: NumericSpec(
            "alt_u_l",
            "ALT (SGPT)",
            "U/L",
            7,
            35,
            moderate_low=3,
            moderate_high=105,
            severe_high=350,
            critical_high=1000,
        ),
        Sex.OTHER: NumericSpec(
            "alt_u_l",
            "ALT (SGPT)",
            "U/L",
            7,
            40,
            moderate_low=3,
            moderate_high=120,
            severe_high=400,
            critical_high=1000,
        ),
    },
    "hdl_mmol_l": {
        Sex.MALE: NumericSpec(
            "hdl_mmol_l",
            "HDL-C",
            "mmol/L",
            1.0,
            5.0,
            moderate_low=0.8,
            severe_low=0.6,
            display_range=">1,0",
        ),
        Sex.FEMALE: NumericSpec(
            "hdl_mmol_l",
            "HDL-C",
            "mmol/L",
            1.3,
            5.0,
            moderate_low=1.0,
            severe_low=0.8,
            display_range=">1,3",
        ),
        Sex.OTHER: NumericSpec(
            "hdl_mmol_l",
            "HDL-C",
            "mmol/L",
            1.0,
            5.0,
            moderate_low=0.8,
            severe_low=0.6,
            display_range=">1,0",
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
