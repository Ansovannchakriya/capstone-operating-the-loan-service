# Production image: multi-stage, slim, non-root, health check. No secrets: API_KEYS comes from Render at run time.

# ---- build stage: install packages and rebuild the champion model ----
FROM python:3.12-slim AS builder
ENV PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
WORKDIR /build
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY ml/ ml/
# fails the build if the model does not reproduce the registry champion
RUN cd ml && MODEL_PATH=/build/models/model.joblib python train.py

# ---- runtime stage ----
FROM python:3.12-slim
ARG GIT_SHA=dev
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PATH="/opt/venv/bin:$PATH" \
    MODEL_PATH=/app/models/model.joblib DB_PATH=/app/data/loans.db GIT_SHA=${GIT_SHA} PORT=8000
RUN groupadd --system app && useradd --system --gid app --no-create-home app
WORKDIR /app
COPY --from=builder /opt/venv /opt/venv
COPY --from=builder /build/models ./models
COPY app/ app/
RUN mkdir -p /app/data && chown app:app /app/data
USER app
EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=3s --start-period=20s --retries=3 \
    CMD python -c "import os, urllib.request; urllib.request.urlopen(f'http://localhost:{os.environ[\"PORT\"]}/health', timeout=2)"
# Render sets $PORT; --proxy-headers so the app sees https behind Render's TLS proxy
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT} --proxy-headers --forwarded-allow-ips='*'"]
