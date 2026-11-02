from __future__ import annotations

import pytest
from training.synthetic import generate_dataset

from medlab.config import Settings
from medlab.risk_model import RiskModel, save_bundle
from medlab.schema import (
    BloodPanel,
    Dipstick,
    Nitrite,
    PatientInput,
    Sex,
    UrinePanel,
)


@pytest.fixture
def offline_settings() -> Settings:
    return Settings(_env_file=None, gemini_api_key=None, llm_mode="offline")


@pytest.fixture
def normal_patient() -> PatientInput:
    return PatientInput(
        age_years=40,
        sex=Sex.MALE,
        blood=BloodPanel(
            hemoglobin_g_l=145,
            wbc_10e9_l=6.5,
            platelets_10e9_l=250,
            fasting_glucose_mmol_l=5.0,
            hba1c_percent=5.2,
            creatinine_umol_l=88,
            alt_u_l=25,
            ast_u_l=24,
            total_cholesterol_mmol_l=4.6,
            ldl_mmol_l=2.8,
            hdl_mmol_l=1.2,
            triglycerides_mmol_l=1.2,
            crp_mg_l=1.0,
            sodium_mmol_l=140,
            potassium_mmol_l=4.2,
        ),
        urine=UrinePanel(
            ph=6.0,
            specific_gravity=1.018,
            protein=Dipstick.NEGATIVE,
            glucose=Dipstick.NEGATIVE,
            ketones=Dipstick.NEGATIVE,
            blood=Dipstick.NEGATIVE,
            leukocyte_esterase=Dipstick.NEGATIVE,
            nitrite=Nitrite.NEGATIVE,
            wbc_per_hpf=1,
            rbc_per_hpf=1,
        ),
    )


@pytest.fixture
def critical_patient() -> PatientInput:
    return PatientInput(
        age_years=55,
        sex=Sex.MALE,
        blood=BloodPanel(
            hemoglobin_g_l=65,
            platelets_10e9_l=15,
            fasting_glucose_mmol_l=27,
            potassium_mmol_l=7.0,
            creatinine_umol_l=800,
        ),
        urine=UrinePanel(ketones=Dipstick.THREE_PLUS, glucose=Dipstick.THREE_PLUS),
    )


@pytest.fixture
def uti_patient() -> PatientInput:
    return PatientInput(
        age_years=32,
        sex=Sex.FEMALE,
        blood=BloodPanel(crp_mg_l=45, wbc_10e9_l=13),
        urine=UrinePanel(
            leukocyte_esterase=Dipstick.THREE_PLUS,
            nitrite=Nitrite.POSITIVE,
            wbc_per_hpf=60,
            protein=Dipstick.ONE_PLUS,
        ),
    )


@pytest.fixture(scope="session")
def trained_model(tmp_path_factory: pytest.TempPathFactory) -> RiskModel:
    dataset = generate_dataset(n_samples=1500, seed=7)
    from medlab.risk_model import build_pipeline

    pipeline = build_pipeline()
    pipeline.fit(dataset.frame, dataset.labels)
    directory = tmp_path_factory.mktemp("model")
    path = directory / "risk_model.joblib"
    save_bundle(pipeline, path)
    model = RiskModel.load(path, low_threshold=0.35, high_threshold=0.65)
    assert model is not None
    return model
