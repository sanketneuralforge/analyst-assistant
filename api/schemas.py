# api/schemas.py

from pydantic import BaseModel, Field
from typing import Any


class BriefRequest(BaseModel):
    company_name: str
    domain: str
    primary_metric: str
    metric_definition: str
    time_period: str
    audience: str
    stakes: str
    known_context: str
    constraints: str
    analyst_context: str = ""


class Mode1Request(BaseModel):
    user_input: str


class Mode2Request(BaseModel):
    user_input: str


class Mode3Request(BaseModel):
    documents: list[str] = Field(min_length=2)


class Mode4Request(BaseModel):
    conclusion: str


class Mode5Request(BaseModel):
    user_input: str = ""


class SessionCreatedResponse(BaseModel):
    session_id: str


class ModeResponse(BaseModel):
    result: dict[str, Any]
    state: dict[str, Any]
    suggestions: list[dict[str, Any]]


class BriefResponse(BaseModel):
    ok: bool
    chunks_indexed: int = 0


class HealthResponse(BaseModel):
    status: str
    sessions_active: int
