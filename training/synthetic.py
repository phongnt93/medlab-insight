from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from medlab.egfr import ckd_epi_2021
from medlab.features import FEATURE_COLUMNS, build_feature_row
from medlab.schema import BloodPanel, Dipstick, Nitrite, PatientInput, Sex, UrinePanel


@dataclass
class SyntheticDataset:
    frame: pd.DataFrame
    labels: np.ndarray
    patients: list[PatientInput]


def _choice_sex(rng: np.random.Generator) -> Sex:
    return Sex(rng.choice(["male", "female", "other"], p=[0.49, 0.49, 0.02]))


def _dipstick(rng: np.random.Generator, max_grade: int) -> Dipstick:
    return Dipstick(int(rng.integers(0, max_grade + 1)))


def _clip(value: float, low: float, high: float) -> float:
    return float(min(max(value, low), high))


def generate_dataset(n_samples: int = 6000, seed: int = 42) -> SyntheticDataset:
    rng = np.random.default_rng(seed)
    rows: list[dict[str, Any]] = []
    labels: list[int] = []
    patients: list[PatientInput] = []

    for _ in range(n_samples):
        age = int(rng.integers(18, 86))
        sex = _choice_sex(rng)
        female = sex == Sex.FEMALE

        anemia = rng.random() < 0.12
        infection = rng.random() < 0.14
        diabetes = rng.random() < 0.13
        ckd = rng.random() < 0.09
        liver = rng.random() < 0.07
        dyslipidemia = rng.random() < 0.28
        dehydration = rng.random() < 0.10
        uti_prob = 0.12 if female else 0.03
        uti = rng.random() < uti_prob
        dka = diabetes and rng.random() < 0.03

        hb = rng.normal(150 if sex == Sex.MALE else 134, 9)
        if anemia:
            hb -= rng.uniform(12, 45)
        wbc = rng.normal(6.4, 1.4)
        if infection:
            wbc += rng.uniform(4, 18)
        platelets = rng.normal(265, 55)
        if infection:
            platelets += rng.uniform(20, 90)
        if ckd:
            platelets -= rng.uniform(0, 40)

        glucose = rng.normal(5.0, 0.4)
        hba1c = rng.normal(5.1, 0.3)
        if diabetes:
            glucose += rng.uniform(2.2, 7.5)
            hba1c += rng.uniform(1.5, 3.5)
        if dka:
            glucose = rng.uniform(16, 30)
            hba1c = max(hba1c, rng.uniform(7.5, 11))

        creatinine = rng.normal(88 if sex == Sex.MALE else 68, 14)
        if ckd:
            creatinine *= rng.uniform(1.5, 4.0)

        alt = rng.normal(22, 7)
        ast = rng.normal(23, 7)
        if liver:
            alt *= rng.uniform(2.0, 6.0)
            ast *= rng.uniform(1.8, 5.0)

        total_cholesterol = rng.normal(4.8, 0.7)
        ldl = max(0.4, total_cholesterol * 0.6 + rng.normal(0, 0.35))
        hdl = rng.normal(1.15 if sex == Sex.MALE else 1.48, 0.22)
        triglycerides = rng.normal(1.2, 0.4)
        if dyslipidemia:
            ldl += rng.uniform(0.7, 2.0)
            triglycerides += rng.uniform(0.6, 2.8)
            hdl -= rng.uniform(0.15, 0.45)

        crp = max(0.1, rng.normal(1.4, 1.0))
        if infection:
            crp = rng.uniform(12, 120)

        sodium = rng.normal(140, 2.2)
        potassium = rng.normal(4.1, 0.28)
        if dehydration:
            sodium = rng.uniform(145, 154)
        if ckd:
            potassium += rng.uniform(0.1, 0.9)
        if dka:
            sodium = rng.uniform(130, 138)
            potassium = rng.uniform(4.8, 6.3)

        ph = rng.normal(6.0, 0.6)
        specific_gravity = rng.normal(1.018, 0.005)
        if dehydration:
            specific_gravity = rng.uniform(1.031, 1.039)
        if ckd:
            specific_gravity = rng.uniform(1.007, 1.014)

        protein = Dipstick.NEGATIVE
        urine_glucose = Dipstick.NEGATIVE
        ketones = Dipstick.TRACE if rng.random() < 0.05 else Dipstick.NEGATIVE
        urine_blood = Dipstick.NEGATIVE
        leukocyte_esterase = Dipstick.TRACE if rng.random() < 0.05 else Dipstick.NEGATIVE
        nitrite = Nitrite.NEGATIVE
        wbc_hpf = max(0.0, rng.normal(1.5, 1.2))
        rbc_hpf = max(0.0, rng.normal(1.2, 1.0))

        if ckd and rng.random() < 0.35:
            protein = _dipstick(rng, 3)
        if diabetes and rng.random() < 0.4:
            urine_glucose = _dipstick(rng, 3)
        if dka:
            ketones = _dipstick(rng, 4)
        if uti:
            leukocyte_esterase = _dipstick(rng, 4)
            nitrite = Nitrite.POSITIVE if rng.random() < 0.8 else Nitrite.NEGATIVE
            wbc_hpf = rng.uniform(10, 120)
            if rng.random() < 0.5:
                protein = _dipstick(rng, 2)
            if rng.random() < 0.3:
                urine_blood = _dipstick(rng, 2)
        if rng.random() < 0.04:
            rbc_hpf = rng.uniform(5, 40)
            urine_blood = _dipstick(rng, 3)

        full = {
            "hemoglobin_g_l": _clip(hb, 0, 300),
            "wbc_10e9_l": _clip(wbc, 0, 300),
            "platelets_10e9_l": _clip(platelets, 0, 3000),
            "fasting_glucose_mmol_l": _clip(glucose, 0, 100),
            "hba1c_percent": _clip(hba1c, 0, 25),
            "creatinine_umol_l": _clip(creatinine, 0, 3000),
            "alt_u_l": _clip(alt, 0, 20000),
            "ast_u_l": _clip(ast, 0, 20000),
            "total_cholesterol_mmol_l": _clip(total_cholesterol, 0, 50),
            "ldl_mmol_l": _clip(ldl, 0, 30),
            "hdl_mmol_l": _clip(hdl, 0, 15),
            "triglycerides_mmol_l": _clip(triglycerides, 0, 60),
            "crp_mg_l": _clip(crp, 0, 1000),
            "sodium_mmol_l": _clip(sodium, 80, 220),
            "potassium_mmol_l": _clip(potassium, 0, 15),
            "ph": _clip(ph, 0, 14),
            "specific_gravity": _clip(specific_gravity, 1.0, 1.06),
            "wbc_per_hpf": _clip(wbc_hpf, 0, 10000),
            "rbc_per_hpf": _clip(rbc_hpf, 0, 10000),
        }

        observed = dict(full)
        for key in list(observed):
            if rng.random() < 0.07:
                observed[key] = None
        if sum(value is not None for value in observed.values()) < 3:
            for key in rng.choice(list(full), size=3, replace=False):
                observed[key] = full[key]

        patient = PatientInput(
            age_years=age,
            sex=sex,
            blood=BloodPanel(
                **{key: observed[key] for key in BloodPanel.model_fields if key in observed}
            ),
            urine=UrinePanel(
                ph=observed["ph"],
                specific_gravity=observed["specific_gravity"],
                protein=protein,
                glucose=urine_glucose,
                ketones=ketones,
                blood=urine_blood,
                leukocyte_esterase=leukocyte_esterase,
                nitrite=nitrite,
                wbc_per_hpf=observed["wbc_per_hpf"],
                rbc_per_hpf=observed["rbc_per_hpf"],
            ),
        )

        egfr = ckd_epi_2021(full["creatinine_umol_l"], age, sex)
        row = build_feature_row(patient, egfr)
        rows.append(row)

        hb_cut = 110 if sex == Sex.MALE else 100
        alt_cut = 80 if sex == Sex.MALE else 70
        needs_review = any(
            (
                anemia and full["hemoglobin_g_l"] < hb_cut,
                infection and (full["crp_mg_l"] > 20 or full["wbc_10e9_l"] > 15),
                diabetes
                and (full["fasting_glucose_mmol_l"] >= 7.0 or full["hba1c_percent"] >= 6.5),
                egfr is not None and egfr < 60,
                liver and full["alt_u_l"] > alt_cut,
                dka,
                uti,
                dehydration and full["sodium_mmol_l"] > 150,
                full["ldl_mmol_l"] > 4.9 or full["triglycerides_mmol_l"] > 5.6,
                full["fasting_glucose_mmol_l"] <= 3.0 or full["fasting_glucose_mmol_l"] >= 25,
                full["potassium_mmol_l"] <= 2.8 or full["potassium_mmol_l"] >= 6.0,
                full["sodium_mmol_l"] <= 125 or full["sodium_mmol_l"] >= 155,
                full["platelets_10e9_l"] < 100,
                full["wbc_10e9_l"] < 2 or full["wbc_10e9_l"] > 30,
                full["hemoglobin_g_l"] < 80,
            )
        )
        labels.append(int(needs_review))
        patients.append(patient)

    y = np.asarray(labels, dtype=int)
    noise_idx = rng.choice(len(y), size=max(1, int(len(y) * 0.04)), replace=False)
    y[noise_idx] = 1 - y[noise_idx]

    frame = pd.DataFrame(rows, columns=FEATURE_COLUMNS)
    return SyntheticDataset(frame=frame, labels=y, patients=patients)
