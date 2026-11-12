"""Rebuild the Module 5 champion (loan-default v1) and save it for the API.

The MLflow server from Module 5 runs on my laptop, so the cloud build cannot download the model
from the registry. Instead the build re-trains the exact champion configuration on the same
seeded data. The result is checked against the registry metrics (champion.json), so a build
that does not reproduce the champion fails.
"""
import json
import os
from pathlib import Path

import joblib
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import precision_score, recall_score, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from data import make_data

HERE = Path(__file__).parent
CHAMPION = json.loads((HERE / "champion.json").read_text())


def build():
    X, y = make_data()
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.25, stratify=y, random_state=42)
    p = CHAMPION["params"]
    model = make_pipeline(StandardScaler(),
                          LogisticRegression(C=p["C"], class_weight=p["class_weight"], max_iter=1000))
    model.fit(X_train.values, y_train)  # plain array: app/model.py sends the same column order
    prob = model.predict_proba(X_test.values)[:, 1]
    pred = (prob >= 0.5).astype(int)
    metrics = {"recall": recall_score(y_test, pred), "precision": precision_score(y_test, pred),
               "auc": roc_auc_score(y_test, prob)}
    return model, metrics


def main():
    model, metrics = build()
    for name, expected in CHAMPION["metrics"].items():
        if abs(metrics[name] - expected) > 0.005:
            raise SystemExit(f"{name} {metrics[name]:.3f} does not match the registry champion ({expected:.3f})")
    path = Path(os.getenv("MODEL_PATH", "models/model.joblib"))
    path.parent.mkdir(parents=True, exist_ok=True)
    version = f"{CHAMPION['registered_model']}-v{CHAMPION['version']}"
    joblib.dump({"model": model, "version": version, "metrics": metrics, "run_id": CHAMPION["run_id"]}, path)
    print(f"saved {version} to {path}: " + ", ".join(f"{k}={v:.3f}" for k, v in metrics.items()))


if __name__ == "__main__":
    main()
