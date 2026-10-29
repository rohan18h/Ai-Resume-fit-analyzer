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


class Resource(BaseModel):
    title: str
    url: str
    provider: str
    resource_type: Literal["docs", "course", "video", "tutorial", "book"]
    level: Literal["beginner", "intermediate", "advanced"]
    is_free: bool


class MatchedSkill(BaseModel):
    name: str
    display_name: str  # not in the spec's example; added so the UI can show "Node.js" instead of "node.js"
    category: str


class MissingSkill(BaseModel):
    name: str
    display_name: str
    category: str
    importance: Literal["high", "medium", "low"]
    mentions: int
    resources: list[Resource]


class CategoryCount(BaseModel):
    category: str
    required: int
    matched: int


class SkillsResult(BaseModel):
    resume: list[str]
    matched: list[MatchedSkill]
    missing: list[MissingSkill]  # high importance first, then most mentioned
    coverage_percent: float
    by_category: list[CategoryCount]


class StrongMatch(BaseModel):
    jd_snippet: str
    resume_snippet: str
    similarity: float


class WeakSpot(BaseModel):
    jd_snippet: str
    best_resume_snippet: str
    similarity: float


class Explanation(BaseModel):
    """'Why this score?': JD parts best and least covered by the resume (from the embedding matcher)."""

    strong_matches: list[StrongMatch]
    weak_spots: list[WeakSpot]


class AnalyzeResponse(BaseModel):
    request_id: str
    processing_ms: int
    fit: FitResult
    skills: SkillsResult
    explanation: Explanation | None = None  # None when embeddings were not computed
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
