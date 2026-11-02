from __future__ import annotations

import math

import pytest
from pydantic import ValidationError

from medlab.schema import (
    BloodPanel,
    Dipstick,
    PatientInput,
    Sex,
    UrinePanel,
)


def test_minimal_valid_patient() -> None:
    patient = PatientInput(age_years=30, sex=Sex.FEMALE, blood=BloodPanel(hemoglobin_g_l=130))
    assert patient.provided_lab_count() == 1
    assert patient.symptoms_note is None


def test_empty_panels_are_rejected() -> None:
    with pytest.raises(ValidationError, match="ít nhất một chỉ số"):
        PatientInput(age_years=30, sex=Sex.MALE)


@pytest.mark.parametrize(
    "field,value",
    [
        ("hemoglobin_g_l", -1),
        ("wbc_10e9_l", 301),
        ("fasting_glucose_mmol_l", float("inf")),
        ("creatinine_umol_l", float("nan")),
    ],
)
def test_implausible_blood_values_are_rejected(field: str, value: float) -> None:
    with pytest.raises(ValidationError):
        BloodPanel(**{field: value})


def test_age_bounds() -> None:
    with pytest.raises(ValidationError):
        PatientInput(age_years=-1, sex=Sex.MALE, blood=BloodPanel(hemoglobin_g_l=140))
    with pytest.raises(ValidationError):
        PatientInput(age_years=121, sex=Sex.MALE, blood=BloodPanel(hemoglobin_g_l=140))


def test_note_is_trimmed_and_limited() -> None:
    patient = PatientInput(
        age_years=30,
        sex=Sex.MALE,
        symptoms_note="   mệt   mỏi  ",
        blood=BloodPanel(hemoglobin_g_l=140),
    )
    assert patient.symptoms_note == "mệt mỏi"
    with pytest.raises(ValidationError):
        PatientInput(
            age_years=30,
            sex=Sex.MALE,
            symptoms_note="x" * 501,
            blood=BloodPanel(hemoglobin_g_l=140),
        )


def test_dipstick_enum_labels() -> None:
    assert Dipstick.NEGATIVE.label_vi == "Âm tính"
    assert Dipstick.TWO_PLUS.label_vi == "2+"
    assert int(Dipstick.FOUR_PLUS) == 5
    assert math.isfinite(float(Dipstick.TRACE))


def test_urine_panel_rejects_out_of_range_specific_gravity() -> None:
    with pytest.raises(ValidationError):
        UrinePanel(specific_gravity=1.2)
