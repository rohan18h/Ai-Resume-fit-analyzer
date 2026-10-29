"""Orchestrator (Section 10.5.7): runs the NLP modules in order and assembles the result.

Input is assumed valid (the router validates it). Nothing is stored; only timings leave this module.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from time import perf_counter
from typing import Literal

from app import config
from app.schemas import Explanation, FitResult, JdSkillOut, SkillsResult, StrongMatch, WeakSpot
from app.services import matcher_embed
from app.services.matcher_tfidf import tfidf_score
from app.services.parser import clean_text, clean_text_light, extract_text, strip_name_header
from app.services.skills import extract_skills, rank_jd_skills

Method = Literal["embeddings", "tfidf", "both"]


@dataclass
class AnalysisResult:
    fit: FitResult
    skills: SkillsResult
    explanation: Explanation | None
    warnings: list[str]
    timings_ms: dict[str, int] = field(default_factory=dict)


def fit_label(score: float) -> str:
    """Good / Average / Low fit from the thresholds in config."""
    if score >= config.LABEL_GOOD_MIN:
        return "Good fit"
    if score >= config.LABEL_AVG_MIN:
        return "Average fit"
    return "Low fit"


def analyze(pdf_bytes: bytes, jd_text: str, method: Method = "both") -> AnalysisResult:
    """Parse the resume, find skills in both texts and score the match with the requested method(s)."""
    timings: dict[str, int] = {}
    warnings: list[str] = []

    def lap(stage: str, started: float) -> float:
        now = perf_counter()
        timings[stage] = round((now - started) * 1000)
        return now

    started = perf_counter()
    resume_text = strip_name_header(extract_text(pdf_bytes).text)
    started = lap("parse", started)

    resume_skills = extract_skills(resume_text)
    jd_skills = rank_jd_skills(jd_text)
    started = lap("skills", started)

    tfidf = None
    if method in ("tfidf", "both"):
        tfidf = tfidf_score(clean_text(resume_text), clean_text(jd_text))
        started = lap("tfidf", started)

    embedding = None
    if method in ("embeddings", "both"):
        if matcher_embed.is_model_loaded():
            embedding = matcher_embed.embedding_score(clean_text_light(resume_text), clean_text_light(jd_text))
            lap("embeddings", started)
        else:
            warnings.append("The sentence-embedding model is not loaded, so only the TF-IDF score is shown.")
            if tfidf is None:
                tfidf = tfidf_score(clean_text(resume_text), clean_text(jd_text))

    if len(jd_text.strip()) < config.SHORT_JD_WARNING_CHARS:
        warnings.append("The job description is very short, so the score may be unreliable.")
    if not jd_skills:
        warnings.append(
            "No known skills were found in the job description. It may be too short or use skills outside our list."
        )

    scores = {"tfidf": tfidf.score if tfidf else None, "embeddings": embedding.score if embedding else None}
    primary = config.PRIMARY_METHOD if scores.get(config.PRIMARY_METHOD) is not None else (
        "embeddings" if embedding else "tfidf"
    )
    fit = FitResult(
        primary_method=primary,
        score=scores[primary],
        label=fit_label(scores[primary]),
        tfidf_score=scores["tfidf"],
        embedding_score=scores["embeddings"],
    )
    skills = SkillsResult(
        resume=[hit.name for hit in resume_skills],
        job_description=[
            JdSkillOut(name=s.name, display_name=s.display_name, category=s.category, importance=s.importance,
                       mentions=s.mentions)
            for s in jd_skills
        ],
    )
    explanation = None
    if embedding:
        explanation = Explanation(
            strong_matches=[
                StrongMatch(jd_snippet=m.jd_snippet, resume_snippet=m.resume_snippet, similarity=m.similarity)
                for m in embedding.strong_matches
            ],
            weak_spots=[
                WeakSpot(jd_snippet=m.jd_snippet, best_resume_snippet=m.resume_snippet, similarity=m.similarity)
                for m in embedding.weak_spots
            ],
        )
    return AnalysisResult(fit=fit, skills=skills, explanation=explanation, warnings=warnings, timings_ms=timings)
