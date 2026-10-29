"""Orchestrator (Section 10.5.7): runs the NLP modules in order and assembles the result.

Input is assumed valid (the router validates it). Nothing is stored; only timings leave this module.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from time import perf_counter
from typing import Literal

from app import config
from app.schemas import FitResult, JdSkillOut, SkillsResult
from app.services.matcher_tfidf import tfidf_score
from app.services.parser import clean_text, extract_text, strip_name_header
from app.services.skills import extract_skills, rank_jd_skills

Method = Literal["embeddings", "tfidf", "both"]


@dataclass
class AnalysisResult:
    fit: FitResult
    skills: SkillsResult
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
    """Parse the resume, find skills in both texts and score the match."""
    timings: dict[str, int] = {}
    warnings: list[str] = []

    def lap(stage: str, started: float) -> float:
        now = perf_counter()
        timings[stage] = round((now - started) * 1000)
        return now

    started = perf_counter()
    resume_text = strip_name_header(extract_text(pdf_bytes).text)
    resume_clean = clean_text(resume_text)
    jd_clean = clean_text(jd_text)
    started = lap("parse", started)

    resume_skills = extract_skills(resume_text)
    jd_skills = rank_jd_skills(jd_text)
    started = lap("skills", started)

    tfidf = tfidf_score(resume_clean, jd_clean)
    lap("match", started)

    # Step 6 adds sentence embeddings; until then the TF-IDF score is the only one available.
    if method in ("embeddings", "both"):
        warnings.append("Sentence-embedding scoring is not available yet, so the TF-IDF score is shown.")
    if len(jd_text.strip()) < config.SHORT_JD_WARNING_CHARS:
        warnings.append("The job description is very short, so the score may be unreliable.")
    if not jd_skills:
        warnings.append(
            "No known skills were found in the job description. It may be too short or use skills outside our list."
        )

    fit = FitResult(
        primary_method="tfidf",
        score=tfidf.score,
        label=fit_label(tfidf.score),
        tfidf_score=tfidf.score,
        embedding_score=None,
    )
    skills = SkillsResult(
        resume=[hit.name for hit in resume_skills],
        job_description=[
            JdSkillOut(name=s.name, display_name=s.display_name, category=s.category, importance=s.importance,
                       mentions=s.mentions)
            for s in jd_skills
        ],
    )
    return AnalysisResult(fit=fit, skills=skills, warnings=warnings, timings_ms=timings)
