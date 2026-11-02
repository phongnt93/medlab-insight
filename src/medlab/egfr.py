from __future__ import annotations

from medlab.schema import Sex

CREATININE_UMOL_PER_MG_DL = 88.4


def ckd_epi_2021(creatinine_umol_l: float, age_years: int, sex: Sex) -> float | None:
    """Race-free CKD-EPI 2021 eGFR. Returns None when the equation is not applicable."""
    if sex == Sex.OTHER or age_years < 18 or creatinine_umol_l <= 0:
        return None
    scr_mg_dl = creatinine_umol_l / CREATININE_UMOL_PER_MG_DL
    female = sex == Sex.FEMALE
    kappa = 0.7 if female else 0.9
    alpha = -0.241 if female else -0.302
    egfr = (
        142
        * min(scr_mg_dl / kappa, 1.0) ** alpha
        * max(scr_mg_dl / kappa, 1.0) ** -1.200
        * 0.9938**age_years
        * (1.012 if female else 1.0)
    )
    return round(egfr, 1)


def effective_egfr(
    provided: float | None, creatinine_umol_l: float | None, age: int, sex: Sex
) -> tuple[float | None, bool]:
    """Return (eGFR, was_computed). Lab-provided eGFR wins over the locally computed value."""
    if provided is not None:
        return provided, False
    if creatinine_umol_l is None:
        return None, False
    computed = ckd_epi_2021(creatinine_umol_l, age, sex)
    return computed, computed is not None
