"""Settings come from environment variables only, so no secret is ever in the code or the image."""
import os

# Comma-separated list so a key can be rotated: add the new key, update clients, remove the old one.
API_KEYS = [k.strip() for k in os.getenv("API_KEYS", "").split(",") if k.strip()]

MODEL_PATH = os.getenv("MODEL_PATH", "models/model.joblib")
DB_PATH = os.getenv("DB_PATH", "data/loans.db")

# Set at image build time by the pipeline (docker build --build-arg GIT_SHA=...).
GIT_SHA = os.getenv("GIT_SHA", "dev")

# Probability of default at or above this is a "reject" recommendation.
DECISION_THRESHOLD = float(os.getenv("DECISION_THRESHOLD", "0.5"))
