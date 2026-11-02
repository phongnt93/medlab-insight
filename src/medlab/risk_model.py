from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import joblib
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from medlab.config import Settings, get_settings
from medlab.features import (
    CATEGORICAL_FEATURES,
    FEATURE_COLUMNS,
    NUMERIC_FEATURES,
    build_feature_frame,
)
from medlab.logging_utils import get_logger
from medlab.schema import PatientInput, RiskAssessment

logger = get_logger(__name__)

BUNDLE_VERSION = "risk-synth-0.2.0"


def build_pipeline() -> Pipeline:
    numeric = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median", add_indicator=True)),
            ("scaler", StandardScaler()),
        ]
    )
    categorical = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("onehot", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
        ]
    )
    preprocess = ColumnTransformer(
        transformers=[
            ("num", numeric, NUMERIC_FEATURES),
            ("cat", categorical, CATEGORICAL_FEATURES),
        ]
    )
    classifier = LogisticRegression(
        max_iter=2000,
        class_weight="balanced",
        random_state=42,
    )
    return Pipeline(steps=[("preprocess", preprocess), ("classifier", classifier)])


def save_bundle(pipeline: Pipeline, path: Path, *, version: str = BUNDLE_VERSION) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(
        {
            "pipeline": pipeline,
            "features": FEATURE_COLUMNS,
            "version": version,
        },
        path,
    )


@dataclass
class RiskModel:
    pipeline: Any
    version: str
    meta: dict[str, Any] = field(default_factory=dict)
    low_threshold: float = 0.35
    high_threshold: float = 0.65

    @classmethod
    def load(
        cls,
        path: Path,
        meta_path: Path | None = None,
        *,
        low_threshold: float = 0.35,
        high_threshold: float = 0.65,
    ) -> RiskModel | None:
        if not path.exists():
            logger.warning("risk model artifact not found: %s", path)
            return None
        try:
            bundle = joblib.load(path)
            pipeline = bundle["pipeline"]
            if list(bundle.get("features", [])) != FEATURE_COLUMNS:
                logger.warning("risk model feature schema mismatch; model disabled")
                return None
        except Exception:
            logger.exception("cannot load risk model from %s", path)
            return None

        meta: dict[str, Any] = {}
        if meta_path is not None and meta_path.exists():
            try:
                import json

                meta = json.loads(meta_path.read_text(encoding="utf-8"))
            except Exception:
                logger.warning("cannot read model card %s", meta_path)
        return cls(
            pipeline=pipeline,
            version=str(bundle.get("version", "unknown")),
            meta=meta,
            low_threshold=low_threshold,
            high_threshold=high_threshold,
        )

    def assess(self, patient: PatientInput, egfr_value: float | None) -> RiskAssessment:
        try:
            frame = build_feature_frame(patient, egfr_value)
            probability = float(self.pipeline.predict_proba(frame)[0][1])
        except Exception:
            logger.exception("risk model inference failed")
            return RiskAssessment(
                status="unavailable",
                model_version=self.version,
                note_vi="Không thể chạy mô hình nguy cơ; kết luận dựa trên rule engine.",
            )

        if probability < self.low_threshold:
            band = "low"
        elif probability >= self.high_threshold:
            band = "high"
        else:
            band = "moderate"
        return RiskAssessment(
            probability=round(probability, 4),
            band=band,
            model_version=self.version,
            status="ok",
            note_vi="Mô hình huấn luyện trên dữ liệu tổng hợp, chỉ dùng cho demo — không dùng để chẩn đoán.",
        )


def load_risk_model(settings: Settings | None = None) -> RiskModel | None:
    settings = settings or get_settings()
    return RiskModel.load(
        settings.risk_model_path,
        settings.risk_model_meta_path,
        low_threshold=settings.risk_low_threshold,
        high_threshold=settings.risk_high_threshold,
    )
