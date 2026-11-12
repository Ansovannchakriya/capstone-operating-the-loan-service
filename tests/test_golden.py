"""Added after the bad-release drill (refactor that sent the features to the model in the wrong order).
Every unit test passed, because each one only checked that a probability between 0 and 1 came back.
These checks pin the model's answer for known borrowers, so a wrong feature order fails CI."""
import pytest

from app import model


@pytest.mark.parametrize("borrower_id, low, high", [(1042, 0.0, 0.05), (1043, 0.95, 1.0), (1044, 0.15, 0.40)])
def test_golden_borrowers(client, auth, borrower_id, low, high):
    app_id = client.post("/api/v1/applications", json={"borrower_id": borrower_id, "amount_usd": 1500,
                                                          "term_months": 12}, headers=auth).json()["id"]
    p = client.post(f"/api/v1/applications/{app_id}/predictions", headers=auth).json()["default_probability"]
    assert low <= p <= high, f"borrower {borrower_id}: {p}"


def test_feature_order_is_the_training_order():
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "ml"))
    from data import make_data
    assert model.FEATURES == list(make_data(n=5)[0].columns)
