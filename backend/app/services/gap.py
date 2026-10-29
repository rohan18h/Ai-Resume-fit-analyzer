"""Gap analyzer (Objective 4, Section 10.5.5): which JD skills the resume is missing, and what to learn.

Main function:
    analyze_gap(resume_skills, jd_skills) -> GapResult

missing = JD skills - resume skills, matched = the intersection. Missing skills are sorted by importance
(high -> low), then by mentions, and each gets up to 3 free learning links from SQLite (beginner first).
"""

from __future__ import annotations

from collections import Counter
from contextlib import closing
from dataclasses import dataclass, field
from pathlib import Path

from app.db import LearningLink, connect, fetch_links
from app.services.skills import IMPORTANCE_ORDER, JdSkill, SkillHit

LINKS_PER_SKILL = 3
NO_JD_SKILLS_WARNING = (
    "No known skills were found in the job description. It may be too short or use skills outside our list."
)


@dataclass(frozen=True)
class MissingSkill:
    skill: JdSkill
    resources: list[LearningLink]


@dataclass(frozen=True)
class CategoryCount:
    category: str
    required: int
    matched: int


@dataclass
class GapResult:
    matched: list[JdSkill]  # JD skills found in the resume, in JD importance order
    missing: list[MissingSkill]  # high importance first, then most mentioned
    coverage_percent: float  # matched / JD skills * 100
    by_category: list[CategoryCount]  # one row per category present in the JD
    warnings: list[str] = field(default_factory=list)


def analyze_gap(resume_skills: list[SkillHit], jd_skills: list[JdSkill], db_path: Path | str | None = None) -> GapResult:
    """Compare the resume's skills with the JD's and attach learning links to the missing ones."""
    if not jd_skills:
        return GapResult(matched=[], missing=[], coverage_percent=0.0, by_category=[], warnings=[NO_JD_SKILLS_WARNING])

    have = {hit.name for hit in resume_skills}
    matched = [skill for skill in jd_skills if skill.name in have]
    missing = sorted(
        (skill for skill in jd_skills if skill.name not in have),
        key=lambda s: (IMPORTANCE_ORDER[s.importance], -s.mentions, s.name),
    )

    with closing(connect(db_path)) as conn:
        links = fetch_links(conn, [skill.name for skill in missing], per_skill=LINKS_PER_SKILL)

    required = Counter(skill.category for skill in jd_skills)
    found = Counter(skill.category for skill in matched)
    by_category = [
        CategoryCount(category, count, found[category])
        for category, count in sorted(required.items(), key=lambda item: (-item[1], item[0]))
    ]
    return GapResult(
        matched=matched,
        missing=[MissingSkill(skill, links[skill.name]) for skill in missing],
        coverage_percent=round(100 * len(matched) / len(jd_skills), 1),
        by_category=by_category,
    )
