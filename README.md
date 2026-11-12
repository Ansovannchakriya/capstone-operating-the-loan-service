# Loan Application Service (capstone)

FastAPI service for the Module 2 loan spec, scoring applications with the Module 5 champion
model (`loan-default` v1, logistic regression). Deployed to Render only by GitHub Actions.

```
PR ──► CI (test, secrets-scan, image) ──► merge to main
                                            │
                     Deploy: test ─► build ─► push ghcr.io/<repo>:<sha> ─► Render deploy hook ─► verify
                                                                                                │ fail
                                                                         rollback to last good sha ◄┘
```

## Endpoints

All under `/api/v1`, Bearer API key required (`Authorization: Bearer <key>`):

| Method | Path | |
|---|---|---|
| GET | /applications | list, filters `status`, `province`, cursor `limit` / `after` |
| POST | /applications | submit (201 + Location) |
| GET | /applications/{id} | one application |
| PATCH | /applications/{id} | approve / reject once (409 after) |
| POST | /applications/{id}/predictions | risk score with the champion model |
| GET | /borrowers/{id}/applications | one borrower's applications |

Public: `GET /health` (status, `git_sha`, `model_version`), `/openapi.json`, `/docs`.

## Settings (environment variables)

| Name | Where it is set | |
|---|---|---|
| `API_KEYS` | Render secret env var | comma-separated, so keys can be rotated |
| `GIT_SHA` | baked by the pipeline | shown in `/health` |
| `MODEL_PATH`, `DB_PATH` | image defaults | |

GitHub: secrets `RENDER_DEPLOY_HOOK_URL`, `LIVE_API_KEY`; variable `LIVE_URL`.

## Run locally

```bash
pip install -r requirements-dev.txt
pytest
cd ml && python train.py && cd ..
API_KEYS=local-key uvicorn app.main:app --reload
```

## Model

`ml/train.py` rebuilds the registry champion (run `26237bac…`, C=0.1, balanced) from the seeded
Module 5 data and stops the build if recall / precision / AUC differ from `ml/champion.json`.
