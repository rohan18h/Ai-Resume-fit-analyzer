"""Orchestrator (Section 10.5.7): runs the NLP modules in order and assembles the result.

Input is assumed valid (the router validates it). Nothing is stored; only timings leave this module.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass, field
from time import perf_counter
from typing import Literal

from app import config
from app.schemas import (
    AtsCheckOut,
    AtsResultOut,
    CategoryCount,
    Explanation,
    FitResult,
    MatchedSkill,
    MissingSkill,
    Resource,
    ScoreBreakdown,
    SkillsResult,
    StrongMatch,
    WeakSpot,
)
from app.services import matcher_embed
from app.services.ats import AtsResult, check_ats
from app.services.gap import analyze_gap
from app.services.matcher_tfidf import tfidf_score
from app.services.parser import ParsedResume, clean_text, clean_text_light, extract_text, strip_name_header
from app.services.scoring import weighted_score
from app.services.skills import extract_skills, rank_jd_skills

Method = Literal["embeddings", "tfidf", "both"]


@dataclass
class AnalysisResult:
    fit: FitResult
    skills: SkillsResult
    explanation: Explanation | None
    ats: AtsResultOut
    breakdown: ScoreBreakdown
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
    parsed = extract_text(pdf_bytes)
    resume_text = strip_name_header(parsed.text)
    started = lap("parse", started)

    # ATS only needs the PDF and the parse result, so it runs on its own thread while matching runs here.
    ats_future = _ATS_POOL.submit(_timed_ats, pdf_bytes, parsed)

    resume_skills = extract_skills(resume_text)
    jd_skills = rank_jd_skills(jd_text)
    started = lap("skills", started)

    gap = analyze_gap(resume_skills, jd_skills)
    warnings.extend(gap.warnings)
    started = lap("gap", started)

    tfidf = None
    if method in ("tfidf", "both"):
        tfidf = tfidf_score(clean_text(resume_text), clean_text(jd_text))
        started = lap("tfidf", started)

    embedding = None
    if method in ("embeddings", "both"):
        if config.LAZY_MODEL_LOAD and not matcher_embed.is_model_loaded():
            matcher_embed.try_load_model()  # first request after startup pays the loading time
        if matcher_embed.is_model_loaded():
            embedding = matcher_embed.embedding_score(clean_text_light(resume_text), clean_text_light(jd_text))
            lap("embeddings", started)
        else:
            warnings.append("The sentence-embedding model is not loaded, so only the TF-IDF score is shown.")
            if tfidf is None:
                tfidf = tfidf_score(clean_text(resume_text), clean_text(jd_text))

    if len(jd_text.strip()) < config.SHORT_JD_WARNING_CHARS:
        warnings.append("The job description is very short, so the score may be unreliable.")

    # The match score never reads the ATS result: formatting and job match are separate metrics.
    started = perf_counter()
    weighted = weighted_score(clean_text_light(resume_text), clean_text_light(jd_text), jd_skills, resume_skills)
    lap("weighted", started)
    if not any(c.applicable for c in weighted.categories):
        warnings.append("The job description has no skills, duties or qualifications we could compare, so the fit "
                        "score is 0. Paste the full job posting.")

    scores = {
        "weighted": weighted.score,
        "tfidf": tfidf.score if tfidf else None,
        "embeddings": embedding.score if embedding else None,
    }
    primary = config.PRIMARY_METHOD if scores.get(config.PRIMARY_METHOD) is not None else "weighted"
    fit = FitResult(
        primary_method=primary,
        score=scores[primary],
        label=fit_label(scores[primary]),
        tfidf_score=scores["tfidf"],
        embedding_score=scores["embeddings"],
        tfidf_cosine=tfidf.cosine if tfidf else None,
        embedding_coverage=embedding.coverage if embedding else None,
    )
    skills = SkillsResult(
        resume=[hit.name for hit in resume_skills],
        matched=[MatchedSkill(name=s.name, display_name=s.display_name, category=s.category) for s in gap.matched],
        missing=[
            MissingSkill(
                name=m.skill.name, display_name=m.skill.display_name, category=m.skill.category,
                importance=m.skill.importance, mentions=m.skill.mentions,
                resources=[Resource(**vars(link)) for link in m.resources],
            )
            for m in gap.missing
        ],
        coverage_percent=gap.coverage_percent,
        by_category=[CategoryCount(**vars(c)) for c in gap.by_category],
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
    ats, timings["ats"] = ats_future.result()
    ats_out = AtsResultOut(
        score=ats.score, passed=ats.passed, total=ats.total,
        checks=[AtsCheckOut(**vars(check), credit=check.credit) for check in ats.checks],
    )
    breakdown = ScoreBreakdown.model_validate(asdict(weighted))
    return AnalysisResult(fit=fit, skills=skills, explanation=explanation, ats=ats_out, breakdown=breakdown,
                          warnings=warnings, timings_ms=timings)


_ATS_POOL = ThreadPoolExecutor(max_workers=4, thread_name_prefix="ats")


def _timed_ats(pdf_bytes: bytes, parsed: ParsedResume) -> tuple[AtsResult, int]:
    started = perf_counter()
    result = check_ats(pdf_bytes, parsed)
    return result, round((perf_counter() - started) * 1000)
