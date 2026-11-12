"""Loads the champion model file that ml/train.py writes during the image build."""
import joblib
import numpy as np

from app import config

# Same order as ml/data.py. The model was trained on a plain array, so the order here is the contract.
FEATURES = ["income", "loan_amount", "credit_score", "years_employed", "has_default"]

_bundle: dict = {}


def load() -> None:
    _bundle.clear()
    _bundle.update(joblib.load(config.MODEL_PATH))


def version() -> str | None:
    return _bundle.get("version")


def default_probability(borrower, amount_usd: float) -> float:
    values = {
        "income": borrower["monthly_income"],
        "loan_amount": amount_usd,
        "credit_score": borrower["credit_score"],
        "years_employed": borrower["years_employed"],
        "has_default": borrower["has_default"],
    }
    row = np.array([[values[name] for name in sorted(values)]], dtype=float)  # tidy: no second list to keep in sync
    return float(_bundle["model"].predict_proba(row)[0][1])
