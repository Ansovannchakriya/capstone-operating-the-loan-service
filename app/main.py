"""Loan Application Service: the Module 2 spec, served under /api/v1, plus /health for the pipeline."""
import hmac
import logging
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI, HTTPException, Query, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app import config, db, model
from app.schemas import (Application, ApplicationCreate, ApplicationList, ApplicationStatusUpdate,
                         Error, Health, Prediction, Status)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger("loan-service")
STARTED_AT = db.now()


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init_db()
    model.load()
    log.info("started git_sha=%s model=%s api_key_set=%s",
             config.GIT_SHA, model.version(), bool(config.API_KEY))  # never the key itself
    yield


app = FastAPI(
    title="Loan Application Service API",
    version="1.0.0",
    description="Submit and track microfinance loan applications.",
    servers=[{"url": "/", "description": "this deployment"}],
    lifespan=lifespan,
)


@app.middleware("http")
async def require_api_key(request: Request, call_next):
    """Lesson 6.6: when API_KEY is set, every /api/ route needs a matching X-API-Key header.
    /health and /docs do not start with /api/, so they stay open."""
    if config.API_KEY and request.url.path.startswith("/api/"):
        given = request.headers.get("X-API-Key", "")
        if not hmac.compare_digest(given.encode(), config.API_KEY.encode()):
            return JSONResponse(status_code=401, content={"detail": "Missing or invalid API key"})
    return await call_next(request)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    # HSTS: browsers only use HTTPS for this host for 1 year (needed for an A+ on SSL Labs)
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response


@app.exception_handler(RequestValidationError)
async def validation_error(request: Request, exc: RequestValidationError):
    # The spec's Error schema is {"detail": "<text>"}, so flatten FastAPI's list of errors.
    first = exc.errors()[0]
    field = ".".join(str(p) for p in first["loc"] if p not in ("body", "query", "path"))
    return JSONResponse(status_code=422, content={"detail": f"{field}: {first['msg']}"})


@app.get("/health", response_model=Health, tags=["ops"])
def health():
    """Public. The pipeline reads git_sha here to know the new release is live."""
    return Health(status="ok", git_sha=config.GIT_SHA, model_version=model.version(), started_at=STARTED_AT)


AUTH_ERRORS = {401: {"model": Error, "description": "Missing or wrong X-API-Key header"}}
api = APIRouter(prefix="/api/v1", responses=AUTH_ERRORS)


def _row_to_application(row) -> Application:
    return Application(id=row["id"], borrower_id=row["borrower_id"], amount_usd=row["amount_usd"],
                       term_months=row["term_months"], status=row["status"], submitted_at=row["submitted_at"])


def _get_application(conn, application_id: int):
    row = conn.execute("SELECT * FROM applications WHERE id = ?", (application_id,)).fetchone()
    if row is None:
        raise HTTPException(404, f"application {application_id} does not exist")
    return row


def _page(rows, limit: int) -> ApplicationList:
    items = [_row_to_application(r) for r in rows[:limit]]
    next_cursor = items[-1].id if len(rows) > limit else None
    return ApplicationList(items=items, next_cursor=next_cursor)


@api.get("/applications", response_model=ApplicationList, tags=["applications"], summary="List applications")
def list_applications(status: Status | None = None, province: str | None = None,
                      limit: int = Query(20, ge=1, le=100), after: int | None = None):
    """Returns one page of applications, newest first. Use next_cursor as the after value to get the next page."""
    sql = "SELECT a.* FROM applications a JOIN borrowers b ON b.id = a.borrower_id WHERE 1 = 1"
    args: list = []
    if status:
        sql += " AND a.status = ?"
        args.append(status)
    if province:
        sql += " AND b.province = ?"
        args.append(province)
    if after is not None:
        sql += " AND a.id < ?"
        args.append(after)
    sql += " ORDER BY a.id DESC LIMIT ?"
    args.append(limit + 1)  # one extra row tells us if there is a next page
    with db.connect() as conn:
        return _page(conn.execute(sql, args).fetchall(), limit)


@api.post("/applications", response_model=Application, status_code=201, tags=["applications"],
          summary="Submit a loan application", responses={422: {"model": Error}})
def create_application(body: ApplicationCreate, response: Response):
    """Creates a new application with status pending."""
    with db.connect() as conn:
        if conn.execute("SELECT 1 FROM borrowers WHERE id = ?", (body.borrower_id,)).fetchone() is None:
            raise HTTPException(422, f"borrower {body.borrower_id} does not exist")
        cur = conn.execute(
            "INSERT INTO applications (borrower_id, amount_usd, term_months, submitted_at) VALUES (?, ?, ?, ?)",
            (body.borrower_id, body.amount_usd, body.term_months, db.now()))
        row = _get_application(conn, cur.lastrowid)
    response.headers["Location"] = f"/api/v1/applications/{row['id']}"
    return _row_to_application(row)


@api.get("/applications/{application_id}", response_model=Application, tags=["applications"],
         summary="Get one application", responses={404: {"model": Error}})
def get_application(application_id: int):
    with db.connect() as conn:
        return _row_to_application(_get_application(conn, application_id))


@api.patch("/applications/{application_id}", response_model=Application, tags=["applications"],
           summary="Update the status of an application",
           responses={404: {"model": Error}, 409: {"model": Error}, 422: {"model": Error}})
def update_status(application_id: int, body: ApplicationStatusUpdate):
    """Approve or reject a pending application. Only status can be changed."""
    with db.connect() as conn:
        row = _get_application(conn, application_id)
        if row["status"] != "pending":
            raise HTTPException(409, f"application {application_id} is already {row['status']}")
        conn.execute("UPDATE applications SET status = ? WHERE id = ?", (body.status, application_id))
        return _row_to_application(_get_application(conn, application_id))


@api.post("/applications/{application_id}/predictions", response_model=Prediction, status_code=201,
          tags=["predictions"], summary="Create a risk prediction for an application",
          responses={404: {"model": Error}})
def create_prediction(application_id: int):
    """Runs the risk model on the application and stores the result."""
    with db.connect() as conn:
        app_row = _get_application(conn, application_id)
        borrower = conn.execute("SELECT * FROM borrowers WHERE id = ?", (app_row["borrower_id"],)).fetchone()
        probability = round(model.default_probability(borrower, app_row["amount_usd"]), 4)
        created_at = db.now()
        cur = conn.execute(
            "INSERT INTO predictions (application_id, default_probability, model_version, created_at)"
            " VALUES (?, ?, ?, ?)", (application_id, probability, model.version(), created_at))
    log.info("prediction application=%s probability=%.4f model=%s", application_id, probability, model.version())
    return Prediction(id=cur.lastrowid, application_id=application_id, default_probability=probability,
                      model_version=model.version(), created_at=created_at)


@api.get("/borrowers/{borrower_id}/applications", response_model=ApplicationList, tags=["borrowers"],
         summary="List the applications of one borrower", responses={404: {"model": Error}})
def borrower_applications(borrower_id: int):
    with db.connect() as conn:
        if conn.execute("SELECT 1 FROM borrowers WHERE id = ?", (borrower_id,)).fetchone() is None:
            raise HTTPException(404, f"borrower {borrower_id} does not exist")
        rows = conn.execute("SELECT * FROM applications WHERE borrower_id = ? ORDER BY id DESC",
                            (borrower_id,)).fetchall()
    return ApplicationList(items=[_row_to_application(r) for r in rows], next_cursor=None)


app.include_router(api)
