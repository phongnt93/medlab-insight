from __future__ import annotations

import math
from datetime import datetime
from enum import IntEnum, StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class Sex(StrEnum):
    MALE = "male"
    FEMALE = "female"
    OTHER = "other"


class Dipstick(IntEnum):
    NEGATIVE = 0
    TRACE = 1
    ONE_PLUS = 2
    TWO_PLUS = 3
    THREE_PLUS = 4
    FOUR_PLUS = 5

    @property
    def label_vi(self) -> str:
        return {
            0: "Âm tính",
            1: "Vết",
            2: "1+",
            3: "2+",
            4: "3+",
            5: "4+",
        }[int(self)]


class Nitrite(StrEnum):
    NEGATIVE = "negative"
    POSITIVE = "positive"


class Severity(StrEnum):
    NORMAL = "normal"
    MILD = "mild"
    MODERATE = "moderate"
    SEVERE = "severe"
    CRITICAL = "critical"


SEVERITY_RANK = {
    Severity.NORMAL: 0,
    Severity.MILD: 1,
    Severity.MODERATE: 2,
    Severity.SEVERE: 3,
    Severity.CRITICAL: 4,
}


class BloodPanel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    hemoglobin_g_l: float | None = Field(default=None, ge=0, le=300)
    wbc_10e9_l: float | None = Field(default=None, ge=0, le=300)
    platelets_10e9_l: float | None = Field(default=None, ge=0, le=3000)
    fasting_glucose_mmol_l: float | None = Field(default=None, ge=0, le=100)
    hba1c_percent: float | None = Field(default=None, ge=0, le=25)
    creatinine_umol_l: float | None = Field(default=None, ge=0, le=3000)
    egfr_ml_min_1_73m2: float | None = Field(default=None, ge=0, le=250)
    alt_u_l: float | None = Field(default=None, ge=0, le=20000)
    ast_u_l: float | None = Field(default=None, ge=0, le=20000)
    total_cholesterol_mmol_l: float | None = Field(default=None, ge=0, le=50)
    ldl_mmol_l: float | None = Field(default=None, ge=0, le=30)
    hdl_mmol_l: float | None = Field(default=None, ge=0, le=15)
    triglycerides_mmol_l: float | None = Field(default=None, ge=0, le=60)
    crp_mg_l: float | None = Field(default=None, ge=0, le=1000)
    sodium_mmol_l: float | None = Field(default=None, ge=80, le=220)
    potassium_mmol_l: float | None = Field(default=None, ge=0, le=15)

    @field_validator("*")
    @classmethod
    def _finite_numbers(cls, value: Any) -> Any:
        if isinstance(value, float) and not math.isfinite(value):
            raise ValueError("giá trị phải là số hữu hạn")
        return value

    def values(self) -> dict[str, float]:
        return {key: value for key, value in self.model_dump().items() if value is not None}


class UrinePanel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ph: float | None = Field(default=None, ge=0, le=14)
    specific_gravity: float | None = Field(default=None, ge=1.0, le=1.06)
    protein: Dipstick | None = None
    glucose: Dipstick | None = None
    ketones: Dipstick | None = None
    blood: Dipstick | None = None
    leukocyte_esterase: Dipstick | None = None
    nitrite: Nitrite | None = None
    wbc_per_hpf: float | None = Field(default=None, ge=0, le=10000)
    rbc_per_hpf: float | None = Field(default=None, ge=0, le=10000)

    @field_validator("*")
    @classmethod
    def _finite_numbers(cls, value: Any) -> Any:
        if isinstance(value, float) and not math.isfinite(value):
            raise ValueError("giá trị phải là số hữu hạn")
        return value

    def values(self) -> dict[str, Any]:
        return {key: value for key, value in self.model_dump().items() if value is not None}


class PatientInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    age_years: int = Field(ge=0, le=120)
    sex: Sex
    symptoms_note: str | None = Field(default=None, max_length=500)
    blood: BloodPanel = Field(default_factory=BloodPanel)
    urine: UrinePanel = Field(default_factory=UrinePanel)

    @field_validator("symptoms_note")
    @classmethod
    def _clean_note(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = " ".join(value.split()).strip()
        return cleaned or None

    @model_validator(mode="after")
    def _require_at_least_one_lab_value(self) -> PatientInput:
        if not self.blood.values() and not self.urine.values():
            raise ValueError("cần nhập ít nhất một chỉ số xét nghiệm máu hoặc nước tiểu")
        return self

    def provided_lab_count(self) -> int:
        return len(self.blood.values()) + len(self.urine.values())

    def provided_field_names(self) -> list[str]:
        return list(self.blood.values().keys()) + list(self.urine.values().keys())


class Finding(BaseModel):
    code: str
    label_vi: str
    severity: Severity
    message_vi: str
    value_display: str
    reference_display: str
    details: dict[str, str | float] = Field(default_factory=dict)


class RiskAssessment(BaseModel):
    probability: float | None = Field(default=None, ge=0, le=1)
    band: str = "unknown"
    model_version: str | None = None
    status: str = "unavailable"
    drivers: list[str] = Field(default_factory=list)
    note_vi: str | None = None


class LLMMeta(BaseModel):
    provider: str = "gemini"
    model: str | None = None
    status: str = "disabled"
    latency_ms: int = 0
    attempts: int = 0
    fallback_reason: str | None = None


class DataQuality(BaseModel):
    fields_provided: int = 0
    fields_expected: int = 0
    missing_fields: list[str] = Field(default_factory=list)
    notes_vi: list[str] = Field(default_factory=list)


class AnalysisReport(BaseModel):
    request_id: str
    created_at: datetime
    age_years: int
    sex: Sex
    findings: list[Finding] = Field(default_factory=list)
    red_flags: list[str] = Field(default_factory=list)
    urgent: bool = False
    risk: RiskAssessment = Field(default_factory=RiskAssessment)
    summary_source: str = "offline"
    conclusion_vi: str
    key_points_vi: list[str] = Field(default_factory=list)
    when_to_seek_care_vi: list[str] = Field(default_factory=list)
    lifestyle_vi: list[str] = Field(default_factory=list)
    llm: LLMMeta = Field(default_factory=LLMMeta)
    data_quality: DataQuality = Field(default_factory=DataQuality)
    disclaimer_vi: str


class LLMNarrative(BaseModel):
    model_config = ConfigDict(extra="ignore")

    summary_vi: str = Field(min_length=1, max_length=2000)
    key_points_vi: list[str] = Field(default_factory=list, max_length=8)
    lifestyle_vi: list[str] = Field(default_factory=list, max_length=6)
    when_to_seek_care_vi: list[str] = Field(default_factory=list, max_length=6)
    confidence: str = "medium"

    @field_validator("key_points_vi", "lifestyle_vi", "when_to_seek_care_vi")
    @classmethod
    def _clean_items(cls, items: list[str]) -> list[str]:
        return [" ".join(str(item).split())[:400] for item in items if str(item).strip()]

    @field_validator("confidence")
    @classmethod
    def _valid_confidence(cls, value: str) -> str:
        value = value.lower().strip()
        return value if value in {"low", "medium", "high"} else "medium"
