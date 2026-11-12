"""Request and response bodies, copied from the Module 2 OpenAPI spec (docs/openapi-module2.yaml)."""
from typing import Literal

from pydantic import BaseModel, Field

Status = Literal["pending", "approved", "rejected"]


class ApplicationCreate(BaseModel):
    borrower_id: int = Field(..., description="ID of the borrower who applies", examples=[1042])
    amount_usd: int = Field(..., ge=100, le=5000, description="Loan amount in US dollars", examples=[1500])
    term_months: Literal[3, 6, 12, 18, 24] = Field(..., description="Length of the loan in months", examples=[12])


class Application(ApplicationCreate):
    id: int = Field(..., description="ID of the application", examples=[7781])
    status: Status = Field(..., description="Current decision on the application")
    submitted_at: str = Field(..., description="When the application was submitted",
                              examples=["2026-11-06T09:30:00Z"])


class ApplicationStatusUpdate(BaseModel):
    status: Literal["approved", "rejected"] = Field(..., description="The decision to record")


class ApplicationList(BaseModel):
    items: list[Application] = Field(..., description="The applications on this page")
    next_cursor: int | None = Field(None, description="Pass this as after to get the next page; null on the last page")


class Prediction(BaseModel):
    id: int
    application_id: int
    default_probability: float = Field(..., ge=0, le=1, description="Chance that the borrower will not repay")
    model_version: str
    created_at: str


class Error(BaseModel):
    detail: str


class Health(BaseModel):
    status: str
    git_sha: str
    model_version: str | None
    started_at: str
