"""Weighted fit score: an explainable 0-100 resume-job match built from four categories of evidence.

Main function:
    weighted_score(resume_light, jd_light, jd_skills, resume_skills) -> WeightedResult

It measures the match with this job only. Formatting is the ATS check's job (ats.py), reported separately and never
mixed in here, so changing the ATS rules cannot move this score.

Both texts are lightly cleaned (parser.clean_text_light; the resume also passed through strip_name_header).

Categories (relative weights from config, shared out to 100 points):
  skills            JD skills the resume has anywhere. Each JD skill counts by importance (required 3, no cue 2,
                    preferred 1). Exact skill or alias = 1; a skill it builds on (Django for Python) = 0.75;
                    an alternative (MySQL for PostgreSQL) = 0.40. Repeats and skills the JD doesn't ask for add nothing.
  evidence          The same JD skills, but only where they appear in the Experience or Projects sections (or, for a
                    resume without headings, in sentence lines rather than lists). A skill that is only listed earns
                    skills credit but no evidence credit.
  responsibilities  Each JD duty (the Responsibilities section, or the JD's sentences if it has none) against the
                    most similar resume bullet from Experience/Projects: similarity FLOOR -> 0, FULL -> 1, linear.
  qualifications    Degree, years of experience and certifications from qualifications.py: met 1, in progress 0.5,
                    not met or not stated 0. Required ones count 3, preferred 1.

Each category's credit is 0-1, so it can never give more than its points. A category the JD gives nothing to
measure (no skills, no duties, no qualifications) is "not applicable": its points are shared among the others in
proportion, so the maximum is always exactly 100. The total is the sum of the rounded category points shown.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass, field, replace
from datetime import date

import numpy as np

from app import config
from app.services import matcher_embed
from app.services.parser import english_stopwords
from app.services.qualifications import QualificationResult, check_requirements, find_requirements
from app.services.sections import JdLine, Line, has_sections, is_list_line, jd_lines, resume_sections
from app.services.skills import SKILL_LINE, JdSkill, SkillExtractor, SkillHit, get_extractor

EVIDENCE_SECTIONS = frozenset({"experience", "projects"})
MIN_SENTENCE_WORDS = 5  # shorter lines are titles or fragments, not duties or work descriptions
_SNIPPET_MAX_CHARS = 240
_COMPANY_BLURB = re.compile(
    r"\b(we\s+are|we're|our\s+(?:company|team|mission|customers|clients|culture)|founded|about\s+us|join\s+us|"
    r"equal\s+opportunity|benefits|salary|perks|headquartered|apply)\b",
    re.IGNORECASE,
)

CATEGORY_TITLES = {
    "skills": "Required technical skills",
    "evidence": "Experience and project evidence",
    "responsibilities": "Job responsibilities",
    "qualifications": "Education and qualifications",
}

# Skills that build on another one: having the key shows some of the value (have -> wanted).
IMPLIES: dict[str, tuple[str, ...]] = {
    "typescript": ("javascript",), "next.js": ("react",), "redux": ("react",), "express.js": ("node.js",),
    "django": ("python",), "flask": ("python",), "fastapi": ("python",), "pandas": ("python",),
    "spring boot": ("java",), "pytest": ("unit testing",), "junit": ("unit testing",), "jest": ("unit testing",),
    "jenkins": ("ci/cd",), "github actions": ("ci/cd",), "github": ("git",),
    "postgresql": ("sql",), "mysql": ("sql",), "sqlite": ("sql",), "oracle": ("sql",),
    "scikit-learn": ("machine learning",), "tensorflow": ("deep learning",), "pytorch": ("deep learning",),
    "keras": ("deep learning",), "selenium": ("test automation",), "cypress": ("test automation",),
    "tableau": ("data visualization",), "power bi": ("data visualization",),
}  # fmt: skip

# Alternatives that do the same job: experience transfers, but they are not the same skill.
RELATED_GROUPS: tuple[frozenset[str], ...] = (
    frozenset({"mysql", "postgresql", "sqlite", "oracle"}),
    frozenset({"fastapi", "flask", "django"}),
    frozenset({"react", "vue.js", "angular"}),
    frozenset({"aws", "azure", "google cloud"}),
    frozenset({"jenkins", "github actions"}),
    frozenset({"tensorflow", "pytorch", "keras"}),
    frozenset({"power bi", "tableau"}),
    frozenset({"selenium", "cypress"}),
    frozenset({"flutter", "react native"}),
    frozenset({"java", "kotlin"}),
)


@dataclass(frozen=True)
class CategoryScore:
    id: str
    title: str
    points: float  # earned, rounded to 0.1
    max_points: float  # this category's share of 100 (0 when not applicable)
    applicable: bool
    summary: str


@dataclass(frozen=True)
class SkillAssessment:
    name: str
    display_name: str
    importance: str  # "high" | "medium" | "low"
    requirement: str  # "required" | "preferred"
    status: str  # "demonstrated" | "listed" | "related" | "missing"
    skills_credit: float  # 0-1 towards the skills category
    evidence_credit: float  # 0-1 towards the evidence category
    via: str | None = None  # the resume skill that earned partial credit, for "related"
    evidence: str | None = None  # a resume bullet that shows the skill


@dataclass(frozen=True)
class ResponsibilityMatch:
    requirement: str
    best_evidence: str | None
    similarity: float
    credit: float


@dataclass(frozen=True)
class QualificationCheck:
    kind: str
    requirement: str
    importance: str
    status: str
    detail: str


@dataclass
class WeightedResult:
    score: float
    categories: list[CategoryScore]
    skills: list[SkillAssessment]
    responsibilities: list[ResponsibilityMatch]
    qualifications: list[QualificationCheck]
    recommendations: list[str]
    similarity_method: str  # "embeddings" or "word overlap" for the responsibilities category
    matched_required: list[str] = field(default_factory=list)
    missing_required: list[str] = field(default_factory=list)
    partial_required: list[str] = field(default_factory=list)
    matched_preferred: list[str] = field(default_factory=list)
    missing_preferred: list[str] = field(default_factory=list)
    listed_not_demonstrated: list[str] = field(default_factory=list)


@dataclass
class _Category:
    id: str
    weight: float
    credit: float | None  # 0-1, None = not applicable
    summary: str


def weighted_score(
    resume_light: str,
    jd_light: str,
    jd_skills: list[JdSkill],
    resume_skills: list[SkillHit],
    extractor: SkillExtractor | None = None,
    use_embeddings: bool | None = None,
    today: date | None = None,
) -> WeightedResult:
    """Score the resume against the JD in four categories and explain every point."""
    extractor = extractor or get_extractor()
    if use_embeddings is None:
        use_embeddings = matcher_embed.is_model_loaded()
    resume = resume_sections(resume_light)
    jd = jd_lines(jd_light)
    evidence = evidence_lines(resume)

    skills = assess_skills(jd_skills, resume_skills, evidence, extractor)
    responsibilities = match_responsibilities(responsibility_lines(jd), evidence, use_embeddings)
    qualifications = relevant_years(check_requirements(find_requirements(jd), resume, today), resume, extractor)

    categories = [
        _skills_category(skills),
        _evidence_category(skills),
        _responsibilities_category(responsibilities, use_embeddings),
        _qualifications_category(qualifications),
    ]
    scored = _allocate(categories)
    total = round(min(100.0, max(0.0, sum(c.points for c in scored))), 1)

    def names(requirement: str, *statuses: str) -> list[str]:
        return [s.display_name for s in skills if s.requirement == requirement and s.status in statuses]

    return WeightedResult(
        score=total,
        categories=scored,
        skills=skills,
        responsibilities=responsibilities,
        qualifications=[
            QualificationCheck(q.requirement.kind, _snippet(q.requirement.text), q.requirement.importance, q.status,
                               q.detail)
            for q in qualifications
        ],
        recommendations=recommendations(
            skills, responsibilities, qualifications, resume, stuffed_keywords(resume, extractor)
        ),
        similarity_method="embeddings" if use_embeddings else "word overlap",
        matched_required=names("required", "demonstrated", "listed"),
        missing_required=names("required", "missing"),
        partial_required=names("required", "related"),
        matched_preferred=names("preferred", "demonstrated", "listed"),
        missing_preferred=names("preferred", "missing", "related"),
        listed_not_demonstrated=[s.display_name for s in skills if s.status == "listed"],
    )


# ---------------------------------------------------------------------------
# Evidence
# ---------------------------------------------------------------------------


def evidence_lines(resume: list[Line]) -> list[str]:
    """Resume lines that describe work: Experience and Projects. Without headings: sentence lines, not lists."""
    if has_sections(resume):
        return [line.text for line in resume if line.section in EVIDENCE_SECTIONS]
    return [
        line.text for line in resume
        if len(line.text.split()) >= MIN_SENTENCE_WORDS and not is_list_line(line.text)
        and not SKILL_LINE.match(line.text)
    ]  # fmt: skip


def skills_shown(lines: list[str], extractor: SkillExtractor) -> dict[str, str]:
    """Skill name -> the first line that mentions it ("" if only found with context from a neighbouring line)."""
    shown: dict[str, str] = {}
    for line in lines:
        for hit in extractor.hits(line):
            shown.setdefault(hit.name, line)
    for hit in extractor.hits("\n".join(lines)):  # skills that need a neighbour on another line for context
        shown.setdefault(hit.name, "")
    return shown


def assess_skills(
    jd_skills: list[JdSkill], resume_skills: list[SkillHit], evidence: list[str], extractor: SkillExtractor
) -> list[SkillAssessment]:
    """One assessment per JD skill. The two credits are worked out separately, so adding a claim never lowers one:

    skills credit    1 if the resume has the skill anywhere, else the best partial credit from a linked skill it has
    evidence credit  1 if an Experience/Projects bullet shows the skill, else the best partial credit from a linked
                     skill a bullet shows (Python via FastAPI 0.75, Django via Flask 0.40), else 0

    status: demonstrated (shown, or listed and shown through a skill built on it), listed (only in a list or
    summary), related (not in the resume, but a linked skill is) or missing.
    """
    claimed = {hit.name: hit for hit in resume_skills}
    shown_in = skills_shown(evidence, extractor)

    assessments = []
    for skill in jd_skills:
        requirement = "preferred" if skill.importance == "low" else "required"
        claim_link = _best_relation(skill.name, claimed)
        shown_link = _best_relation(skill.name, shown_in)
        skills_credit = 1.0 if skill.name in claimed else (claim_link[1] if claim_link else 0.0)
        evidence_credit = 1.0 if skill.name in shown_in else (shown_link[1] if shown_link else 0.0)

        via, line = None, ""
        if skill.name in shown_in:
            status, line = "demonstrated", shown_in[skill.name]
        elif skill.name in claimed and shown_link and evidence_credit >= config.IMPLIED_SKILL_CREDIT:
            status, via, line = "demonstrated", claimed[shown_link[0]].display_name, shown_in[shown_link[0]]
        elif skill.name in claimed:
            status = "listed"
        elif claim_link:
            status, via = "related", claimed[claim_link[0]].display_name
            line = shown_in.get(claim_link[0], "")
        else:
            status = "missing"
        assessments.append(SkillAssessment(
            skill.name, skill.display_name, skill.importance, requirement, status, skills_credit, evidence_credit, via,
            _snippet(line) or None,
        ))  # fmt: skip
    return assessments


def relation_credit(wanted: str, have: str) -> float:
    """Partial credit for having `have` when the JD asks for `wanted` (0 if they are unrelated)."""
    if wanted in IMPLIES.get(have, ()):
        return config.IMPLIED_SKILL_CREDIT
    if any(wanted in group and have in group for group in RELATED_GROUPS):
        return config.RELATED_SKILL_CREDIT
    return 0.0


def _best_relation(wanted: str, have: Iterable[str]) -> tuple[str, float] | None:
    """The resume skill giving the most partial credit for `wanted`, with that credit (None if none)."""
    credits = [(name, relation_credit(wanted, name)) for name in have]
    best = max(credits, key=lambda kv: (kv[1], kv[0]), default=None)
    return best if best and best[1] > 0 else None


def implied_skills(names: Iterable[str]) -> set[str]:
    """The skills plus every skill they build on (FastAPI -> Python)."""
    return set(names) | {wanted for name in names for wanted in IMPLIES.get(name, ())}


def _importance_weight(importance: str) -> float:
    return {
        "high": config.IMPORTANCE_WEIGHT_HIGH, "medium": config.IMPORTANCE_WEIGHT_MEDIUM,
        "low": config.IMPORTANCE_WEIGHT_LOW,
    }[importance]  # fmt: skip


def _skills_category(skills: list[SkillAssessment]) -> _Category:
    if not skills:
        return _Category("skills", config.WEIGHT_SKILLS, None, "The job description names no skills from our list.")
    credit = _weighted_mean(skills, evidence=False)
    have = sum(s.status in ("demonstrated", "listed") for s in skills)
    partial = sum(s.status == "related" for s in skills)
    summary = f"{have} of {len(skills)} skills in the job description are in your resume"
    summary += f", {partial} more through a related skill." if partial else "."
    return _Category("skills", config.WEIGHT_SKILLS, credit, summary)


def _evidence_category(skills: list[SkillAssessment]) -> _Category:
    if not skills:
        return _Category("evidence", config.WEIGHT_EVIDENCE, None, "The job description names no skills from our list.")
    shown = sum(s.status == "demonstrated" for s in skills)
    return _Category(
        "evidence", config.WEIGHT_EVIDENCE, _weighted_mean(skills, evidence=True),
        f"{shown} of {len(skills)} skills are shown in your Experience or Projects, not just listed.",
    )


def _weighted_mean(skills: list[SkillAssessment], evidence: bool) -> float:
    """Importance-weighted mean of the skills (or evidence) credits, 0-1."""
    total = sum(_importance_weight(s.importance) for s in skills)
    return sum(_importance_weight(s.importance) * (s.evidence_credit if evidence else s.skills_credit)
               for s in skills) / total


# ---------------------------------------------------------------------------
# Responsibilities
# ---------------------------------------------------------------------------


def responsibility_lines(jd: list[JdLine]) -> list[str]:
    """The JD's duties: its Responsibilities section, or else its sentences outside About/Preferred sections.

    Company blurbs ("We are a fintech startup...") are skipped either way: no resume can match them.
    """
    duties = [line.text for line in jd if line.section == "responsibilities"]
    if not duties:
        duties = [line.text for line in jd if line.section in ("intro", "requirements") and line.importance != "preferred"]
    duties = [d for d in duties if len(d.split()) >= MIN_SENTENCE_WORDS and not _COMPANY_BLURB.search(d)]
    return duties[: config.MAX_RESPONSIBILITIES]


def match_responsibilities(duties: list[str], evidence: list[str], use_embeddings: bool) -> list[ResponsibilityMatch]:
    if not duties:
        return []
    if not evidence:
        return [ResponsibilityMatch(_snippet(d), None, 0.0, 0.0) for d in duties]
    # Each bullet, plus its clauses: "Added Redis caching and wrote PyTest suites" can match two different duties.
    units, owner = [], []
    for index, line in enumerate(evidence):
        for unit in dict.fromkeys([line, *_clauses(line)]):
            units.append(unit)
            owner.append(index)
    if use_embeddings:
        vectors = matcher_embed.embed(duties + units)
        similarity = vectors[: len(duties)] @ vectors[len(duties) :].T
        floor, full = config.RESP_SIM_FLOOR, config.RESP_SIM_FULL
    else:
        similarity = np.array([[_overlap(d, u) for u in units] for d in duties])
        floor, full = config.RESP_OVERLAP_FLOOR, config.RESP_OVERLAP_FULL
    matches = []
    for row, duty in zip(similarity, duties):
        best = int(row.argmax())
        value = float(row[best])
        credit = min(1.0, max(0.0, (value - floor) / (full - floor)))
        shown = _snippet(evidence[owner[best]]) if credit > 0 else None
        matches.append(ResponsibilityMatch(_snippet(duty), shown, round(value, 3), round(credit, 3)))
    return matches


_CLAUSE_SPLIT = re.compile(r";\s*|,\s*|\s+and\s+")


def _clauses(line: str) -> list[str]:
    return [part.strip() for part in _CLAUSE_SPLIT.split(line) if len(part.split()) >= 3]


def _content_words(text: str) -> set[str]:
    stop = english_stopwords()
    words = re.findall(r"[a-z][a-z0-9+#.]*", text.lower())
    return {w.rstrip(".").removesuffix("s") for w in words if len(w) >= 3 and w not in stop}


def _overlap(duty: str, line: str) -> float:
    wanted = _content_words(duty)
    return len(wanted & _content_words(line)) / len(wanted) if wanted else 0.0


def _responsibilities_category(matches: list[ResponsibilityMatch], use_embeddings: bool) -> _Category:
    if not matches:
        return _Category("responsibilities", config.WEIGHT_RESPONSIBILITIES, None,
                         "No duties were found in the job description to compare.")
    covered = sum(m.credit >= 0.5 for m in matches)
    how = "by meaning" if use_embeddings else "by shared words"
    return _Category(
        "responsibilities", config.WEIGHT_RESPONSIBILITIES, sum(m.credit for m in matches) / len(matches),
        f"{covered} of {len(matches)} job duties are clearly matched {how} by a bullet in your Experience or Projects.",
    )


# ---------------------------------------------------------------------------
# Qualifications
# ---------------------------------------------------------------------------


def relevant_years(
    results: list[QualificationResult], resume: list[Line], extractor: SkillExtractor
) -> list[QualificationResult]:
    """'2+ years with Python' is only met if the dated roles involve Python (or a skill built on it, like FastAPI),
    and '2+ years of clinical experience in a hospital' only if they mention clinical or hospital work.

    Years from any job count when the line names no skill or field ("3+ years of professional experience").
    """
    checked = []
    for result in results:
        if result.requirement.kind == "experience_years" and result.status == "met":
            roles = [line.text for line in resume if line.section == "experience"]
            asked = {hit.name for hit in extractor.hits(result.requirement.text)}
            if asked and not asked & implied_skills(skills_shown(roles, extractor)):
                names = _join([extractor.skills[name].display_name for name in sorted(asked)], "or")
                result = replace(result, status="not_met", detail=f"{result.detail} None of those roles mention {names}.")
            elif not asked and (field := _field_words(result.requirement.text)):
                role_words = _content_words(" ".join(roles))
                if not any(word in role_words for word in field):
                    result = replace(result, status="not_met",
                                     detail=f"{result.detail} None of those roles mention {_join(sorted(field), 'or')}.")
        checked.append(result)
    return checked


# Words that describe any experience rather than a field ("2+ years of relevant professional experience").
_GENERIC_EXPERIENCE_WORDS = {
    "year", "yrs", "experience", "professional", "industry", "work", "working", "relevant", "hand", "hands-on",
    "strong", "minimum", "least", "plus", "required", "preferred", "must", "solid", "proven", "total", "overall",
    "related", "similar", "field", "role", "full-time", "prior", "previou", "demonstrated",
}  # fmt: skip


def _field_words(text: str) -> set[str]:
    """Content words naming the field of a years requirement: 'clinical experience in a hospital' -> clinical,
    hospital. Empty for a field-free line such as '3+ years of experience'."""
    return {w for w in _content_words(text) if w not in _GENERIC_EXPERIENCE_WORDS and not w[:1].isdigit()}


def _qualifications_category(results: list[QualificationResult]) -> _Category:
    if not results:
        return _Category("qualifications", config.WEIGHT_QUALIFICATIONS, None,
                         "The job description states no degree, years of experience or certification.")
    weight = {"required": config.IMPORTANCE_WEIGHT_HIGH, "preferred": config.IMPORTANCE_WEIGHT_LOW}
    total = sum(weight[r.requirement.importance] for r in results)
    credit = sum(weight[r.requirement.importance] * r.credit for r in results) / total
    met = sum(r.status == "met" for r in results)
    return _Category("qualifications", config.WEIGHT_QUALIFICATIONS, credit,
                     f"{met} of {len(results)} stated qualifications are clearly met.")


# ---------------------------------------------------------------------------
# Points
# ---------------------------------------------------------------------------


def _allocate(categories: list[_Category]) -> list[CategoryScore]:
    """Share 100 points among the applicable categories by weight (to 0.1, summing to exactly 100), then award each
    its credit x points. With no applicable category (the JD gives nothing to compare), every maximum is 0."""
    applicable = [c for c in categories if c.credit is not None and c.weight > 0]
    total_weight = sum(c.weight for c in applicable)
    exact = {c.id: c.weight / total_weight * 1000 for c in applicable} if total_weight else {}
    tenths = {key: int(value) for key, value in exact.items()}
    leftover = round(sum(exact.values())) - sum(tenths.values())  # largest remainder: totals stay exact
    for key in sorted(exact, key=lambda k: exact[k] - tenths[k], reverse=True)[:leftover]:
        tenths[key] += 1
    scored = []
    for c in categories:
        max_points = tenths.get(c.id, 0) / 10
        points = round((c.credit or 0.0) * max_points, 1) if c.id in tenths else 0.0
        scored.append(CategoryScore(c.id, CATEGORY_TITLES[c.id], points, max_points, c.id in tenths, c.summary))
    return scored


# ---------------------------------------------------------------------------
# Recommendations
# ---------------------------------------------------------------------------


STUFFING_REPEATS = 3  # the same skill this many times in one line is keyword stuffing, not description


def stuffed_keywords(resume: list[Line], extractor: SkillExtractor) -> list[str]:
    """Skills repeated STUFFING_REPEATS+ times within a single line. Repeats never add points (every skill is
    counted once), but the candidate should know that ATS tools and recruiters penalise it."""
    stuffed: dict[str, None] = {}
    for line in resume:
        for hit in extractor.hits(line.text):
            if hit.count >= STUFFING_REPEATS:
                stuffed[hit.display_name] = None
    return list(stuffed)


def recommendations(
    skills: list[SkillAssessment],
    responsibilities: list[ResponsibilityMatch],
    qualifications: list[QualificationResult],
    resume: list[Line],
    stuffed: list[str] | None = None,
) -> list[str]:
    """Specific, honest next steps, most valuable first. Never suggests claiming something the candidate lacks."""
    tips: list[str] = []
    if stuffed:
        tips.append(f"{_join(stuffed[:5])} {'is' if len(stuffed) == 1 else 'are'} repeated many times in one line. "
                    "Repeats earn no extra points here, and many ATS tools and recruiters treat them as keyword "
                    "stuffing. List each skill once and show it in a project or job bullet.")
    order = {"high": 0, "medium": 1, "low": 2}
    required = sorted((s for s in skills if s.requirement == "required"), key=lambda s: order[s.importance])

    if has_sections(resume) and not any(line.section in EVIDENCE_SECTIONS for line in resume):
        tips.append("Add an 'Experience' or 'Projects' section with bullets describing what you built and the tools "
                    "you used. Skills that only appear in a list earn less credit.")
    missing = [s.display_name for s in required if s.status == "missing"]
    if missing:
        tips.append(f"Required skills not found: {_join(missing[:5])}. If you have used them, add them with a "
                    "project or job bullet that shows how; otherwise see the learning roadmap below.")
    listed = [s.display_name for s in required if s.status == "listed"]
    if listed:
        tips.append(f"{_join(listed[:5])} {'is' if len(listed) == 1 else 'are'} listed but not shown in any project "
                    "or job bullet. Add a bullet that says what you did with "
                    f"{'it' if len(listed) == 1 else 'them'} and the result.")
    for skill in [s for s in required if s.status == "related"][:2]:
        if skill.skills_credit >= config.IMPLIED_SKILL_CREDIT:
            tips.append(f"Your {skill.via} work implies {skill.display_name}, but the word itself is missing. Name "
                        f"{skill.display_name} explicitly so keyword filters find it.")
        else:
            tips.append(f"The job asks for {skill.display_name}; your resume shows {skill.via}, a related but "
                        f"different tool. If you have used {skill.display_name}, name it; otherwise point out the "
                        "transferable experience.")
    for result in qualifications:
        req = result.requirement
        if result.status == "unverified" and req.kind == "degree":
            tips.append("State your degree, institution and graduation year (or 'expected <year>') in an "
                        "'Education' section.")
        elif result.status == "unverified" and req.kind == "experience_years":
            tips.append("Add start and end dates (e.g. 'Jun 2023 - Present') to each role in your 'Experience' "
                        "section so your years of experience can be counted.")
        elif result.status in ("unverified", "not_met") and req.importance == "required":
            tips.append(f"{result.detail} If you meet it, say so explicitly; if not, this requirement may screen "
                        "you out.")
    weak = sorted((m for m in responsibilities if m.credit < 0.5), key=lambda m: m.credit)[:2]
    for match in weak:
        tips.append(f"No bullet clearly matches the duty \"{_snippet(match.requirement.rstrip('.'), 120)}\". If you have done "
                    "similar work, describe it in a bullet using concrete actions and results.")
    return tips


def _join(items: list[str], conjunction: str = "and") -> str:
    return items[0] if len(items) == 1 else ", ".join(items[:-1]) + f" {conjunction} " + items[-1]


def _snippet(text: str, limit: int = _SNIPPET_MAX_CHARS) -> str:
    return text if len(text) <= limit else text[: limit - 1].rsplit(" ", 1)[0] + "…"
