"""Quality gate: the model in the image must be the registry champion, not just "a model"."""
import json
import sys
from pathlib import Path

ML = Path(__file__).resolve().parents[1] / "ml"
sys.path.insert(0, str(ML))

import train  # noqa: E402


def test_rebuilt_model_matches_registry_champion():
    _, metrics = train.build()
    champion = json.loads((ML / "champion.json").read_text())["metrics"]
    for name, expected in champion.items():
        assert abs(metrics[name] - expected) < 0.005, name


def test_champion_meets_the_promotion_rule():
    _, metrics = train.build()
    assert metrics["precision"] >= 0.55
    assert metrics["recall"] >= 0.75
