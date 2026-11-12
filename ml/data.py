# Fake loan data for the project (same 5 features as my loan-api)
# target: default = 1 means the person did not pay back the loan
import numpy as np
import pandas as pd


def make_data(n=5000, seed=42, income_shift=0, credit_shift=0):
    # income_shift / credit_shift are only used in monitor.py to fake drift
    rng = np.random.default_rng(seed)
    income = rng.normal(1500 + income_shift, 600, n).clip(200, 6000)
    loan_amount = rng.normal(8000, 4000, n).clip(500, 40000)
    credit_score = rng.normal(650 + credit_shift, 80, n).clip(300, 850).round()
    years_employed = rng.integers(0, 30, n)
    has_default = rng.binomial(1, 0.12, n)

    # higher risk = more likely to default
    risk = (-1.6 - 0.0012 * (income - 1500) + 0.00012 * (loan_amount - 8000)
            - 0.018 * (credit_score - 650) - 0.04 * (years_employed - 15)
            + 1.6 * has_default + 0.6 * (loan_amount / income > 8)
            + rng.normal(0, 0.6, n))
    default = (rng.random(n) < 1 / (1 + np.exp(-risk))).astype(int)

    X = pd.DataFrame({
        "income": income,
        "loan_amount": loan_amount,
        "credit_score": credit_score.astype(int),
        "years_employed": years_employed.astype(int),
        "has_default": has_default.astype(int),
    })
    return X, pd.Series(default, name="default")
