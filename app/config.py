"""Settings come from environment variables only, so no secret is ever in the code or the image."""
import os

# Run-time secret (Lesson 6.6): set only in Render's environment. Not set locally or in CI.
API_KEY = os.getenv("API_KEY")

MODEL_PATH = os.getenv("MODEL_PATH", "models/model.joblib")
DB_PATH = os.getenv("DB_PATH", "data/loans.db")

# Set at image build time by the pipeline (docker build --build-arg GIT_SHA=...).
GIT_SHA = os.getenv("GIT_SHA", "dev")

# Probability of default at or above this is a "reject" recommendation.
DECISION_THRESHOLD = float(os.getenv("DECISION_THRESHOLD", "0.5"))
