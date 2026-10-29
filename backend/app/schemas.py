"""Pydantic request/response models."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class FitResult(BaseModel):
    primary_method: Literal["weighted", "tfidf", "embeddings"]
    score: float
    label: str
    tfidf_score: float | None
    embedding_score: float | None
    # The raw numbers behind those two scores (before the TFIDF_CEILING / EMBED_CEILING display scaling).
    tfidf_cosine: float | None = None  # cosine of the TF-IDF vectors, 0-1
    embedding_coverage: float | None = None  # mean best cosine per JD chunk, 0-1


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


class AtsCheckOut(BaseModel):
    id: str
    title: str
    status: Literal["pass", "warn", "fail", "na"]  # "na": the evidence is missing, so it was not checked
    detail: str
    fix: str | None
    credit: float | None  # points towards the score: pass 1, warn 0.5, fail 0; None when not checked


class AtsResultOut(BaseModel):
    score: int  # round(100 * (passed + 0.5 * warned) / total)
    passed: int
    total: int  # checks that could be applied; "na" checks are left out
    checks: list[AtsCheckOut]


class CategoryScoreOut(BaseModel):
    id: Literal["skills", "evidence", "responsibilities", "qualifications"]
    title: str
    points: float
    max_points: float  # 0 when the category does not apply to this JD
    applicable: bool
    summary: str


class SkillAssessmentOut(BaseModel):
    name: str
    display_name: str
    importance: Literal["high", "medium", "low"]
    requirement: Literal["required", "preferred"]
    status: Literal["demonstrated", "listed", "related", "missing"]
    skills_credit: float
    evidence_credit: float
    via: str | None
    evidence: str | None


class ResponsibilityMatchOut(BaseModel):
    requirement: str
    best_evidence: str | None
    similarity: float
    credit: float


class QualificationCheckOut(BaseModel):
    kind: Literal["degree", "experience_years", "certification"]
    requirement: str
    importance: Literal["required", "preferred"]
    status: Literal["met", "in_progress", "not_met", "unverified"]
    detail: str


class ScoreBreakdown(BaseModel):
    """The weighted fit score explained: fit.score == sum of the category points (Section: weighted model)."""

    score: float
    categories: list[CategoryScoreOut]
    matched_required: list[str]
    partial_required: list[str]  # only a related skill was found
    missing_required: list[str]
    matched_preferred: list[str]
    missing_preferred: list[str]
    listed_not_demonstrated: list[str]
    skills: list[SkillAssessmentOut]
    responsibilities: list[ResponsibilityMatchOut]
    qualifications: list[QualificationCheckOut]
    recommendations: list[str]
    similarity_method: Literal["embeddings", "word overlap"]


class AnalyzeResponse(BaseModel):
    request_id: str
    processing_ms: int
    fit: FitResult
    skills: SkillsResult
    explanation: Explanation | None = None  # None when embeddings were not computed
    ats: AtsResultOut
    breakdown: ScoreBreakdown | None = None  # the weighted score's categories and evidence
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
