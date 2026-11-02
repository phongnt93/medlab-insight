from __future__ import annotations

import argparse
import json
import platform
from datetime import UTC, datetime
from pathlib import Path

import sklearn
from sklearn.metrics import (
    accuracy_score,
    brier_score_loss,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split

from medlab.risk_model import BUNDLE_VERSION, build_pipeline, save_bundle
from training.synthetic import generate_dataset


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train the synthetic-data lab risk model")
    parser.add_argument("--samples", type=int, default=6000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output", type=Path, default=Path("artifacts"))
    parser.add_argument("--no-mlflow", action="store_true", help="skip MLflow tracking")
    parser.add_argument("--tracking-uri", default="sqlite:///mlflow.db")
    parser.add_argument("--experiment", default="medlab-risk")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    dataset = generate_dataset(n_samples=args.samples, seed=args.seed)
    frame, labels = dataset.frame, dataset.labels

    x_train, x_test, y_train, y_test = train_test_split(
        frame, labels, test_size=0.2, random_state=args.seed, stratify=labels
    )
    pipeline = build_pipeline()
    pipeline.fit(x_train, y_train)

    probabilities = pipeline.predict_proba(x_test)[:, 1]
    predictions = (probabilities >= 0.5).astype(int)
    metrics = {
        "roc_auc": float(roc_auc_score(y_test, probabilities)),
        "accuracy": float(accuracy_score(y_test, predictions)),
        "precision": float(precision_score(y_test, predictions, zero_division=0)),
        "recall": float(recall_score(y_test, predictions, zero_division=0)),
        "f1": float(f1_score(y_test, predictions, zero_division=0)),
        "brier": float(brier_score_loss(y_test, probabilities)),
        "positive_rate": float(labels.mean()),
        "train_size": int(len(x_train)),
        "test_size": int(len(x_test)),
    }

    output: Path = args.output
    output.mkdir(parents=True, exist_ok=True)
    model_path = output / "risk_model.joblib"
    card_path = output / "model_card.json"
    save_bundle(pipeline, model_path, version=BUNDLE_VERSION)

    card = {
        "model_version": BUNDLE_VERSION,
        "trained_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "dataset": "synthetic",
        "target": "simulated need for medical review (moderate or worse abnormality)",
        "age_range": "18-85",
        "n_samples": args.samples,
        "seed": args.seed,
        "features": list(frame.columns),
        "metrics": metrics,
        "decision_threshold": 0.5,
        "library_versions": {
            "scikit-learn": sklearn.__version__,
            "python": platform.python_version(),
        },
        "intended_use": "MLOps demo; decision support only, not a diagnosis and not for clinical use.",
        "limitations": [
            "Huấn luyện hoàn toàn trên dữ liệu tổng hợp, chưa được kiểm định lâm sàng.",
            "Chỉ áp dụng cho người trưởng thành 18-85 tuổi.",
            "Không bao gồm bệnh sử, thuốc, thai kỳ, triệu chứng lâm sàng hoặc xét nghiệm khác.",
            "Không thay thế bác sĩ; không dùng để ra quyết định điều trị.",
        ],
    }
    card_path.write_text(json.dumps(card, ensure_ascii=False, indent=2), encoding="utf-8")

    if not args.no_mlflow:
        import mlflow

        tracking_uri = args.tracking_uri
        if tracking_uri.startswith("sqlite:///"):
            db_path = Path(tracking_uri.removeprefix("sqlite:///")).resolve()
            tracking_uri = f"sqlite:///{db_path}"
        mlflow.set_tracking_uri(tracking_uri)
        mlflow.set_experiment(args.experiment)
        with mlflow.start_run(run_name=f"risk-synth-{args.seed}"):
            mlflow.log_params(
                {
                    "model": "logistic_regression",
                    "samples": args.samples,
                    "seed": args.seed,
                    "dataset": "synthetic",
                    "threshold": 0.5,
                }
            )
            mlflow.log_metrics(metrics)
            mlflow.set_tags({"model_version": BUNDLE_VERSION, "intended_use": "demo"})
            mlflow.log_artifact(str(model_path), artifact_path="model")
            mlflow.log_artifact(str(card_path), artifact_path="model")

    print(
        json.dumps(
            {"model": str(model_path), "card": str(card_path), "metrics": metrics},
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
