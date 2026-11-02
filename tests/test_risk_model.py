from __future__ import annotations

from pathlib import Path

from medlab.features import FEATURE_COLUMNS, build_feature_frame
from medlab.risk_model import RiskModel
from medlab.schema import PatientInput


def test_model_artifact_loads_and_predicts(
    trained_model: RiskModel, normal_patient: PatientInput
) -> None:
    assessment = trained_model.assess(normal_patient, 100)
    assert assessment.status == "ok"
    assert assessment.probability is not None
    assert 0 <= assessment.probability <= 1
    assert assessment.band in {"low", "moderate", "high"}


def test_abnormal_patient_tends_to_higher_risk(
    trained_model: RiskModel, normal_patient: PatientInput, critical_patient: PatientInput
) -> None:
    normal = trained_model.assess(normal_patient, 100)
    critical = trained_model.assess(critical_patient, 8)
    assert normal.probability is not None and critical.probability is not None
    assert critical.probability >= normal.probability


def test_partial_data_is_imputed(trained_model: RiskModel) -> None:
    patient = PatientInput.model_validate(
        {"age_years": 44, "sex": "female", "blood": {"hemoglobin_g_l": 118}}
    )
    assessment = trained_model.assess(patient, None)
    assert assessment.status == "ok"


def test_missing_artifact_returns_none(tmp_path: Path) -> None:
    assert RiskModel.load(tmp_path / "missing.joblib") is None


def test_corrupt_artifact_returns_none(tmp_path: Path) -> None:
    path = tmp_path / "bad.joblib"
    path.write_text("not a model")
    assert RiskModel.load(path) is None


def test_feature_frame_schema(normal_patient: PatientInput) -> None:
    frame = build_feature_frame(normal_patient, 100)
    assert list(frame.columns) == FEATURE_COLUMNS
    assert len(frame) == 1
