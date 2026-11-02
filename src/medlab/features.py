from __future__ import annotations

from typing import Any

import pandas as pd

from medlab.schema import Dipstick, Nitrite, PatientInput

NUMERIC_FEATURES = [
    "age_years",
    "hemoglobin_g_l",
    "wbc_10e9_l",
    "platelets_10e9_l",
    "fasting_glucose_mmol_l",
    "hba1c_percent",
    "creatinine_umol_l",
    "egfr_ml_min_1_73m2",
    "alt_u_l",
    "ast_u_l",
    "total_cholesterol_mmol_l",
    "ldl_mmol_l",
    "hdl_mmol_l",
    "triglycerides_mmol_l",
    "crp_mg_l",
    "sodium_mmol_l",
    "potassium_mmol_l",
    "chloride_mmol_l",
    "bun_mmol_l",
    "uric_acid_umol_l",
    "rbc_t_l",
    "hct_l_l",
    "mcv_fl",
    "mch_pg",
    "mchc_g_l",
    "rdw_cv_percent",
    "mpv_fl",
    "neut_percent",
    "lym_percent",
    "mono_percent",
    "eo_percent",
    "baso_percent",
    "neut_abs_10e9_l",
    "lym_abs_10e9_l",
    "mono_abs_10e9_l",
    "eo_abs_10e9_l",
    "baso_abs_10e9_l",
    "ph",
    "specific_gravity",
    "wbc_per_hpf",
    "rbc_per_hpf",
    "urine_protein",
    "urine_glucose",
    "urine_ketones",
    "urine_blood",
    "urine_leukocyte_esterase",
    "nitrite_positive",
]

CATEGORICAL_FEATURES = ["sex"]
FEATURE_COLUMNS = NUMERIC_FEATURES + CATEGORICAL_FEATURES


def _dipstick_grade(value: Dipstick | None) -> int | None:
    return None if value is None else int(value)


def build_feature_row(patient: PatientInput, egfr_value: float | None) -> dict[str, Any]:
    blood = patient.blood
    urine = patient.urine
    return {
        "age_years": patient.age_years,
        "hemoglobin_g_l": blood.hemoglobin_g_l,
        "wbc_10e9_l": blood.wbc_10e9_l,
        "platelets_10e9_l": blood.platelets_10e9_l,
        "fasting_glucose_mmol_l": blood.fasting_glucose_mmol_l,
        "hba1c_percent": blood.hba1c_percent,
        "creatinine_umol_l": blood.creatinine_umol_l,
        "egfr_ml_min_1_73m2": egfr_value,
        "alt_u_l": blood.alt_u_l,
        "ast_u_l": blood.ast_u_l,
        "total_cholesterol_mmol_l": blood.total_cholesterol_mmol_l,
        "ldl_mmol_l": blood.ldl_mmol_l,
        "hdl_mmol_l": blood.hdl_mmol_l,
        "triglycerides_mmol_l": blood.triglycerides_mmol_l,
        "crp_mg_l": blood.crp_mg_l,
        "sodium_mmol_l": blood.sodium_mmol_l,
        "potassium_mmol_l": blood.potassium_mmol_l,
        "chloride_mmol_l": blood.chloride_mmol_l,
        "bun_mmol_l": blood.bun_mmol_l,
        "uric_acid_umol_l": blood.uric_acid_umol_l,
        "rbc_t_l": blood.rbc_t_l,
        "hct_l_l": blood.hct_l_l,
        "mcv_fl": blood.mcv_fl,
        "mch_pg": blood.mch_pg,
        "mchc_g_l": blood.mchc_g_l,
        "rdw_cv_percent": blood.rdw_cv_percent,
        "mpv_fl": blood.mpv_fl,
        "neut_percent": blood.neut_percent,
        "lym_percent": blood.lym_percent,
        "mono_percent": blood.mono_percent,
        "eo_percent": blood.eo_percent,
        "baso_percent": blood.baso_percent,
        "neut_abs_10e9_l": blood.neut_abs_10e9_l,
        "lym_abs_10e9_l": blood.lym_abs_10e9_l,
        "mono_abs_10e9_l": blood.mono_abs_10e9_l,
        "eo_abs_10e9_l": blood.eo_abs_10e9_l,
        "baso_abs_10e9_l": blood.baso_abs_10e9_l,
        "ph": urine.ph,
        "specific_gravity": urine.specific_gravity,
        "wbc_per_hpf": urine.wbc_per_hpf,
        "rbc_per_hpf": urine.rbc_per_hpf,
        "urine_protein": _dipstick_grade(urine.protein),
        "urine_glucose": _dipstick_grade(urine.glucose),
        "urine_ketones": _dipstick_grade(urine.ketones),
        "urine_blood": _dipstick_grade(urine.blood),
        "urine_leukocyte_esterase": _dipstick_grade(urine.leukocyte_esterase),
        "nitrite_positive": None
        if urine.nitrite is None
        else int(urine.nitrite == Nitrite.POSITIVE),
        "sex": patient.sex.value,
    }


def build_feature_frame(patient: PatientInput, egfr_value: float | None) -> pd.DataFrame:
    return pd.DataFrame([build_feature_row(patient, egfr_value)], columns=FEATURE_COLUMNS)
