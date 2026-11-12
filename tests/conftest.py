import importlib
import os
import subprocess
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
TEST_KEY = "test-key-not-a-secret"


@pytest.fixture(scope="session")
def client(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("svc")
    os.environ.update(API_KEY=TEST_KEY, MODEL_PATH=str(tmp / "model.joblib"),
                      DB_PATH=str(tmp / "loans.db"), GIT_SHA="abc1234")
    subprocess.run([sys.executable, "train.py"], cwd=ROOT / "ml", check=True, env=os.environ)
    from app import config, main
    importlib.reload(config)
    importlib.reload(main)
    with TestClient(main.app) as c:
        yield c


@pytest.fixture
def auth():
    return {"X-API-Key": TEST_KEY}
