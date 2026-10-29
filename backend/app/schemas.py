"""Pydantic request/response models."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class FitResult(BaseModel):
    primary_method: Literal["tfidf", "embeddings"]
    score: float
    label: str
    tfidf_score: float | None
    embedding_score: float | None


class JdSkillOut(BaseModel):
    name: str
    display_name: str
    category: str
    importance: Literal["high", "medium", "low"]
    mentions: int


class SkillsResult(BaseModel):
    """v0 (Step 4): skills found in each text. Step 7 adds matched / missing / coverage via gap.py."""

    resume: list[str]
    job_description: list[JdSkillOut]


class AnalyzeResponse(BaseModel):
    request_id: str
    processing_ms: int
    fit: FitResult
    skills: SkillsResult
    warnings: list[str] = []


class HealthResponse(BaseModel):
    status: str
    model_loaded: bool
    version: str


class ErrorDetail(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    """Every error uses this shape: {"error": {"code": ..., "message": ...}}."""

    error: ErrorDetail
