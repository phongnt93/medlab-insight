from __future__ import annotations

import pytest

from medlab.egfr import ckd_epi_2021, effective_egfr
from medlab.schema import Sex


def test_ckd_epi_known_ranges() -> None:
    male = ckd_epi_2021(creatinine_umol_l=88.4, age_years=40, sex=Sex.MALE)
    female = ckd_epi_2021(creatinine_umol_l=61.9, age_years=60, sex=Sex.FEMALE)
    assert male is not None and 90 <= male <= 105
    assert female is not None and 90 <= female <= 105


def test_ckd_epi_increases_when_creatinine_drops() -> None:
    high = ckd_epi_2021(200, 50, Sex.MALE)
    low = ckd_epi_2021(80, 50, Sex.MALE)
    assert high is not None and low is not None
    assert low > high


@pytest.mark.parametrize(
    "creatinine,age,sex",
    [
        (88.4, 12, Sex.MALE),
        (88.4, 40, Sex.OTHER),
        (0, 40, Sex.MALE),
    ],
)
def test_ckd_epi_not_applicable(creatinine: float, age: int, sex: Sex) -> None:
    assert ckd_epi_2021(creatinine, age, sex) is None


def test_effective_egfr_prefers_lab_value() -> None:
    value, computed = effective_egfr(75.0, 88.4, 40, Sex.MALE)
    assert value == 75.0
    assert computed is False


def test_effective_egfr_computes_when_missing() -> None:
    value, computed = effective_egfr(None, 88.4, 40, Sex.MALE)
    assert value is not None
    assert computed is True


def test_effective_egfr_without_inputs() -> None:
    value, computed = effective_egfr(None, None, 40, Sex.MALE)
    assert value is None
    assert computed is False
