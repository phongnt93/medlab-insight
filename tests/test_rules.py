from __future__ import annotations

from medlab.egfr import effective_egfr
from medlab.rules import evaluate_rules
from medlab.schema import (
    BloodPanel,
    Dipstick,
    Nitrite,
    PatientInput,
    Severity,
    Sex,
    UrinePanel,
)


def _codes(patient: PatientInput) -> set[str]:
    egfr, _ = effective_egfr(
        patient.blood.egfr_ml_min_1_73m2,
        patient.blood.creatinine_umol_l,
        patient.age_years,
        patient.sex,
    )
    return {finding.code for finding in evaluate_rules(patient, egfr).findings}


def test_normal_panel_has_no_findings(normal_patient: PatientInput) -> None:
    result = evaluate_rules(normal_patient)
    assert result.findings == []
    assert result.urgent is False


def test_female_anemia_is_moderate(normal_patient: PatientInput) -> None:
    patient = normal_patient.model_copy(
        update={
            "sex": Sex.FEMALE,
            "blood": BloodPanel(hemoglobin_g_l=105),
            "urine": UrinePanel(),
        }
    )
    result = evaluate_rules(patient)
    hb = next(f for f in result.findings if f.code == "blood_hemoglobin_g_l")
    assert hb.severity == Severity.MODERATE
    assert result.urgent is False


def test_critical_hemoglobin_is_urgent(normal_patient: PatientInput) -> None:
    patient = normal_patient.model_copy(
        update={"blood": BloodPanel(hemoglobin_g_l=65), "urine": UrinePanel()}
    )
    result = evaluate_rules(patient)
    assert result.urgent is True
    assert any("Hb ≤80" in flag or "65" in flag for flag in result.red_flags)


def test_low_platelets_escalate(normal_patient: PatientInput) -> None:
    patient = normal_patient.model_copy(
        update={"blood": BloodPanel(platelets_10e9_l=45), "urine": UrinePanel()}
    )
    result = evaluate_rules(patient)
    assert result.urgent is True
    plt = next(f for f in result.findings if f.code == "blood_platelets_10e9_l")
    assert plt.severity == Severity.SEVERE


def test_suspected_diabetes(normal_patient: PatientInput) -> None:
    patient = normal_patient.model_copy(
        update={"blood": BloodPanel(fasting_glucose_mmol_l=7.5), "urine": UrinePanel()}
    )
    codes = _codes(patient)
    assert "suspected_diabetes" in codes
    assert "blood_fasting_glucose_mmol_l" in codes


def test_critical_glucose_is_urgent(normal_patient: PatientInput) -> None:
    patient = normal_patient.model_copy(
        update={"blood": BloodPanel(fasting_glucose_mmol_l=26), "urine": UrinePanel()}
    )
    assert evaluate_rules(patient).urgent is True


def test_critical_potassium_is_urgent(normal_patient: PatientInput) -> None:
    patient = normal_patient.model_copy(
        update={"blood": BloodPanel(potassium_mmol_l=6.8), "urine": UrinePanel()}
    )
    assert evaluate_rules(patient).urgent is True


def test_uti_combination(uti_patient: PatientInput) -> None:
    result = evaluate_rules(uti_patient)
    assert "suspected_uti" in {f.code for f in result.findings}
    assert result.urgent is True


def test_dka_combination(normal_patient: PatientInput) -> None:
    patient = normal_patient.model_copy(
        update={
            "blood": BloodPanel(fasting_glucose_mmol_l=20),
            "urine": UrinePanel(ketones=Dipstick.THREE_PLUS),
        }
    )
    result = evaluate_rules(patient)
    dka = next(f for f in result.findings if f.code == "dka_risk")
    assert dka.severity == Severity.CRITICAL
    assert result.urgent is True


def test_low_egfr_is_computed_and_flagged(normal_patient: PatientInput) -> None:
    patient = normal_patient.model_copy(
        update={
            "age_years": 75,
            "sex": Sex.FEMALE,
            "blood": BloodPanel(creatinine_umol_l=400),
            "urine": UrinePanel(),
        }
    )
    egfr, computed = effective_egfr(None, 400, 75, Sex.FEMALE)
    assert computed is True
    assert egfr is not None and egfr < 30
    result = evaluate_rules(patient, egfr)
    assert "reduced_kidney_function" in {f.code for f in result.findings}
    assert result.urgent is True


def test_pancytopenia(normal_patient: PatientInput) -> None:
    patient = normal_patient.model_copy(
        update={
            "blood": BloodPanel(hemoglobin_g_l=90, wbc_10e9_l=2.0, platelets_10e9_l=90),
            "urine": UrinePanel(),
        }
    )
    result = evaluate_rules(patient)
    assert "pancytopenia" in {f.code for f in result.findings}
    assert result.urgent is True


def test_severe_lipids_alone_are_not_emergency(normal_patient: PatientInput) -> None:
    patient = normal_patient.model_copy(
        update={"blood": BloodPanel(ldl_mmol_l=5.5), "urine": UrinePanel()}
    )
    result = evaluate_rules(patient)
    assert "dyslipidemia" in {f.code for f in result.findings}
    assert result.urgent is False


def test_nitrite_without_pyuria_is_not_uti(normal_patient: PatientInput) -> None:
    patient = normal_patient.model_copy(
        update={"blood": BloodPanel(), "urine": UrinePanel(nitrite=Nitrite.POSITIVE)}
    )
    codes = _codes(patient)
    assert "suspected_uti" not in codes
    assert "urine_nitrite" in codes
