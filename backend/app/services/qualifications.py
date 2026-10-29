"""Qualifications: degree, years of experience and certifications/licences asked for in a JD, checked against a resume.

Main functions:
    find_requirements(jd) -> list[Requirement]
    check_requirements(requirements, resume, today) -> list[QualificationResult]

Each result is "met", "in_progress" (degree still being studied), "not_met" (the resume shows something that
falls short), or "unverified" (the resume doesn't state it, so it cannot be checked). Nothing is guessed: an
unverified requirement earns no credit, and the explanation says what to add.

Rules:
- Degree level: diploma < bachelor < master < PhD. The JD's lowest named level is the requirement ("Bachelor's or
  Master's" -> bachelor). The resume's highest level in its Education section (or anywhere, if the resume has no
  headings) is compared with it. A degree whose line says pursuing / expected / present, or ends in a future
  year, is "in_progress".
- Years: "2+ years", "3-5 years", "at least 4 years" on a JD line that mentions experience. The resume's years are
  the date ranges in its Experience section ("Jun 2022 - Present", "06/2021 - 08/2023", "2019 - 2021"), merged
  where they overlap. No dated experience -> "unverified".
- Certifications/licences: the capitalised name before "certification"/"certified", or the words before
  "license"/"licence". Met when every key word of that name appears in the resume.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date

from app.services.sections import JdLine, Line, has_sections

DEGREE_LEVELS = {"diploma": 1, "bachelor": 2, "master": 3, "phd": 4}
DEGREE_NAMES = {1: "a diploma", 2: "a bachelor's degree", 3: "a master's degree", 4: "a PhD"}

_DEGREE_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("phd", re.compile(r"\bph\.?\s?d\b|\bdoctorate\b|\bdoctoral\b", re.IGNORECASE)),
    ("master", re.compile(
        r"\bmaster'?s?\b|\bm\.?\s?tech\b|\bm\.\s?e\.|\bm\.?\s?sc\b|\bmca\b|\bmba\b|\bpost[\s-]?graduat|\bm\.?s\.?(?=\s+in\b)",
        re.IGNORECASE,
    )),
    ("bachelor", re.compile(
        r"\bbachelor'?s?\b|\bb\.?\s?tech\b|\bb\.\s?e\b\.?|\bb\.?\s?sc\b|\bbca\b|\bb\.?s\.?(?=\s+in\b)|\bundergraduate\b",
        re.IGNORECASE,
    )),
    ("bachelor", re.compile(r"(?<![\w.])BE(?![\w.])")),  # "BE Computer Engineering", case-sensitive
    ("diploma", re.compile(r"\bdiploma\b", re.IGNORECASE)),
]
# In a JD, "a degree in Computer Science" means at least a bachelor's. Not used on resumes, where it proves nothing.
_GENERIC_DEGREE = re.compile(r"\bdegree\b", re.IGNORECASE)
_IN_PROGRESS = re.compile(r"\b(pursuing|expected|ongoing|present|current(?:ly)?|till\s+date|in\s+progress)\b", re.IGNORECASE)
_YEAR = re.compile(r"\b(?:19|20)\d{2}\b")

_YEARS_REQUIRED = re.compile(
    r"(?:at\s+least\s+|minimum\s+(?:of\s+)?)?(\d{1,2})\s*\+?\s*(?:(?:-|–|to)\s*\d{1,2}\s*\+?\s*)?(?:years?|yrs?)\b",
    re.IGNORECASE,
)
_EXPERIENCE_WORD = re.compile(r"\bexperience|\bexp\b", re.IGNORECASE)

_MONTHS = {m: i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], start=1
)}  # fmt: skip
_MONTH = r"(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|june?|july?|aug(?:ust)?|sept?(?:ember)?|" \
         r"oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\.?"
_DATE = rf"(?:({_MONTH})\s*'?\s*|(\d{{1,2}})\s*/\s*)?((?:19|20)\d{{2}})"
_OPEN_END = r"present|current|now|till\s+date|today|ongoing"
_DATE_RANGE = re.compile(rf"{_DATE}\s*(?:-|–|—|to|until)\s*(?:{_DATE}|({_OPEN_END}))", re.IGNORECASE)

_CERT_BEFORE = re.compile(r"\b((?:[A-Z][\w+.#&-]*\s+){0,4}[A-Z][\w+.#&-]*)\s+(?:certification|certificate)\b")
# "AWS Certified Solutions Architect": the words on both sides of "Certified" form one name.
_CERT_AROUND = re.compile(r"((?:\b[A-Z][\w+.#&-]*\s+){0,3})[Cc]ertified((?:\s+[A-Z][\w+.#&-]*){1,5})")
_LICENSE = re.compile(r"\b((?:[a-zA-Z]+\s+){1,3})(?:license|licence)\b", re.IGNORECASE)
_GENERIC_WORDS = {
    "a", "an", "the", "valid", "current", "active", "relevant", "any", "state", "professional", "industry",
    "recognized", "recognised", "required", "preferred", "with", "and", "or", "of", "in", "is", "are", "must", "be",
    "have", "hold", "holding", "should", "driving",
}  # fmt: skip


@dataclass(frozen=True)
class Requirement:
    kind: str  # "degree" | "experience_years" | "certification"
    text: str  # the JD line it came from
    importance: str  # "required" | "preferred"
    level: int = 0  # degree level (DEGREE_LEVELS) for "degree"
    years: int = 0  # minimum years for "experience_years"
    keywords: tuple[str, ...] = ()  # key words of the name for "certification"
    name: str = ""  # readable name for "certification"


@dataclass(frozen=True)
class QualificationResult:
    requirement: Requirement
    status: str  # "met" | "in_progress" | "not_met" | "unverified"
    detail: str

    @property
    def credit(self) -> float:
        return {"met": 1.0, "in_progress": 0.5}.get(self.status, 0.0)


# ---------------------------------------------------------------------------
# Job description
# ---------------------------------------------------------------------------


def find_requirements(jd: list[JdLine]) -> list[Requirement]:
    """Degree, years and certification requirements, one per kind (certifications: one per name)."""
    found: list[Requirement] = []
    degree: Requirement | None = None
    years: Requirement | None = None
    certs: dict[tuple[str, ...], Requirement] = {}
    for line in jd:
        if line.section == "about":
            continue
        importance = "preferred" if line.importance == "preferred" else "required"
        level = jd_degree_level(line.text)
        if level and (degree is None or _stronger(importance, degree.importance)):
            degree = Requirement("degree", line.text, importance, level=level)
        if _EXPERIENCE_WORD.search(line.text):
            match = _YEARS_REQUIRED.search(line.text)
            if match and 0 < int(match.group(1)) <= 30:
                minimum = int(match.group(1))
                if years is None or _stronger(importance, years.importance) or (
                    importance == years.importance and minimum > years.years
                ):
                    years = Requirement("experience_years", line.text, importance, years=minimum)
        for name in _cert_names(line.text):
            keywords = _keywords(name)
            if keywords and keywords not in certs:
                certs[keywords] = Requirement("certification", line.text, importance, keywords=keywords, name=name)
    found.extend(r for r in (degree, years) if r)
    found.extend(certs.values())
    return found


def jd_degree_level(text: str) -> int:
    """Lowest degree level named on a JD line (0 if none). "Bachelor's or Master's" -> bachelor."""
    levels = [DEGREE_LEVELS[kind] for kind, pattern in _DEGREE_PATTERNS if pattern.search(text)]
    if not levels and _GENERIC_DEGREE.search(text):
        levels = [DEGREE_LEVELS["bachelor"]]
    return min(levels) if levels else 0


def _stronger(new: str, old: str) -> bool:
    return new == "required" and old == "preferred"


def _cert_names(text: str) -> list[str]:
    names = [m.group(1).strip() for m in _CERT_BEFORE.finditer(text)]
    names += [f"{m.group(1).strip()} Certified {m.group(2).strip()}".strip() for m in _CERT_AROUND.finditer(text)]
    names += [m.group(1).strip() + " license" for m in _LICENSE.finditer(text)]
    return names


def _keywords(name: str) -> tuple[str, ...]:
    words = [w.lower().strip(".,") for w in name.split()]
    return tuple(w for w in words if w and w not in _GENERIC_WORDS and w not in {"license", "licence", "certified"})


# ---------------------------------------------------------------------------
# Resume
# ---------------------------------------------------------------------------


def check_requirements(requirements: list[Requirement], resume: list[Line], today: date | None = None) -> list[QualificationResult]:
    today = today or date.today()
    return [_check(req, resume, today) for req in requirements]


def _check(req: Requirement, resume: list[Line], today: date) -> QualificationResult:
    if req.kind == "degree":
        return _check_degree(req, resume, today)
    if req.kind == "experience_years":
        return _check_years(req, resume, today)
    return _check_certification(req, resume)


def resume_degree(resume: list[Line], today: date) -> tuple[int, bool]:
    """Highest degree level in the Education section (anywhere if there are no headings) and whether it is
    still in progress. (0, False) if no degree is stated."""
    lines = [line.text for line in resume if line.section == "education"] if has_sections(resume) else []
    if not lines:
        lines = [line.text for line in resume]
    best, in_progress = 0, False
    for index, text in enumerate(lines):
        levels = [DEGREE_LEVELS[kind] for kind, pattern in _DEGREE_PATTERNS if pattern.search(text)]
        if not levels:
            continue
        level = max(levels)
        nearby = " ".join(lines[index : index + 2])  # the dates are often on the next line
        ongoing = bool(_IN_PROGRESS.search(nearby)) or any(int(y) > today.year for y in _YEAR.findall(nearby))
        if level > best or (level == best and in_progress and not ongoing):
            best, in_progress = level, ongoing
    return best, in_progress


def _check_degree(req: Requirement, resume: list[Line], today: date) -> QualificationResult:
    wanted = DEGREE_NAMES[req.level]
    level, ongoing = resume_degree(resume, today)
    if not level:
        return QualificationResult(req, "unverified", f"The job asks for {wanted}, but no degree was found in the resume.")
    if level < req.level:
        return QualificationResult(req, "not_met", f"The job asks for {wanted}; the resume shows {DEGREE_NAMES[level]}.")
    if ongoing:
        return QualificationResult(req, "in_progress", f"The job asks for {wanted}; the resume shows it in progress.")
    return QualificationResult(req, "met", f"The job asks for {wanted}; the resume shows {DEGREE_NAMES[level]}.")


def experience_months(resume: list[Line], today: date) -> int | None:
    """Months covered by the date ranges in the Experience section, overlaps merged. None if there are none."""
    spans: list[tuple[int, int]] = []
    for line in resume:
        if line.section != "experience":
            continue
        for match in _DATE_RANGE.finditer(line.text):
            start = _month_index(match.group(1), match.group(2), match.group(3), start=True)
            if match.group(7):
                end = today.year * 12 + today.month
            else:
                end = _month_index(match.group(4), match.group(5), match.group(6), start=False)
            if start and end and start <= end:
                spans.append((start, max(end, start + 1)))
    if not spans:
        return None
    spans.sort()
    total, (current_start, current_end) = 0, spans[0]
    for start, end in spans[1:]:
        if start <= current_end:
            current_end = max(current_end, end)
        else:
            total += current_end - current_start
            current_start, current_end = start, end
    return total + current_end - current_start


def _month_index(month_name: str | None, month_number: str | None, year: str | None, start: bool) -> int | None:
    if not year:
        return None
    if month_name:
        month = _MONTHS[month_name.lower()[:3]]
    elif month_number and 1 <= int(month_number) <= 12:
        month = int(month_number)
    else:
        month = 1  # year only: "2019 - 2021" counts as two years, not three
    return int(year) * 12 + month


def _check_years(req: Requirement, resume: list[Line], today: date) -> QualificationResult:
    months = experience_months(resume, today)
    wanted = f"{req.years}+ years of experience"
    if months is None:
        return QualificationResult(
            req, "unverified", f"The job asks for {wanted}, but no dated roles were found in an Experience section."
        )
    years = months / 12
    shown = f"about {years:.1f} years" if years >= 1 else f"about {months} months"
    if years + 1e-9 >= req.years:
        return QualificationResult(req, "met", f"The job asks for {wanted}; the dated roles add up to {shown}.")
    return QualificationResult(req, "not_met", f"The job asks for {wanted}; the dated roles add up to {shown}.")


def _check_certification(req: Requirement, resume: list[Line]) -> QualificationResult:
    text = " ".join(line.text for line in resume).lower()
    words = set(re.findall(r"[\w+.#&-]+", text))
    if all(keyword in words for keyword in req.keywords):
        return QualificationResult(req, "met", f"The job asks for {req.name}; it appears in the resume.")
    return QualificationResult(req, "unverified", f"The job asks for {req.name}; it was not found in the resume.")
