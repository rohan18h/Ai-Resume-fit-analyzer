"""Section splitter: groups the lines of a resume or a job description under their headings.

Main functions:
    resume_sections(text) -> list[Line]   every resume line tagged experience / projects / skills / education / ...
    jd_lines(text) -> list[JdLine]        every JD line tagged about / responsibilities / requirements / preferred,
                                          plus its importance (required / preferred / neutral)

Both expect lightly cleaned text (parser.clean_text_light): original casing, one line per row, bullets removed.
A heading is a short line (at most 6 words, an optional trailing ':') that matches one of the patterns below.
Lines before the first heading are "header" (resume) or "intro" (JD).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.services.skills import HIGH_CUE, LOW_CUE

_MAX_HEADING_WORDS = 6

# Resume headings. Optional words such as "Work", "Academic" or "Technical" may come first.
_RESUME_PREFIX = r"(?:(?:work|professional|relevant|industry|industrial|internship|academic|personal|key|selected|" \
                 r"technical|core|major|other|educational|career)\s+){0,2}"
RESUME_HEADINGS: dict[str, str] = {
    "experience": r"experience|employment(?:\s+history)?|work\s+history|internships?|work",
    "projects": r"projects?|project\s+work",
    "skills": r"skills(?:\s+(?:&|and)\s+tools)?|technologies|tech\s+stack|competencies|tools|expertise",
    "education": r"education|academics?|qualifications?|academic\s+background",
    "summary": r"summary|objective|profile|about\s+me|career\s+objective",
    "certifications": r"certifications?|licen[cs]es?|courses|trainings?",
    "other": r"achievements?|awards?|publications?|activities|extra[\s-]?curricular(?:\s+activities)?|"
             r"interests|hobbies|languages|volunteering|leadership|positions\s+of\s+responsibility|references",
}  # fmt: skip

# Job-description headings.
JD_HEADINGS: dict[str, str] = {
    "about": r"about(?:\s+(?:us|the\s+(?:company|team)|our\s+team))?|who\s+we\s+are|our\s+company|company\s+overview|"
             r"benefits|perks|what\s+we\s+offer|why\s+join\s+us|compensation|salary|location|how\s+to\s+apply",
    "responsibilities": r"(?:key\s+|your\s+|job\s+)?responsibilities|what\s+you(?:'|’)?ll\s+do|duties|the\s+role|"
                        r"role|day[\s-]to[\s-]day|your\s+impact|job\s+description|what\s+you\s+will\s+do",
    "requirements": r"requirements|(?:minimum\s+|basic\s+|required\s+)?qualifications|must[\s-]haves?|"
                    r"what\s+we(?:'|’)?re\s+looking\s+for|who\s+you\s+are|you\s+have|eligibility|required\s+skills|"
                    r"skills(?:\s+(?:&|and)\s+experience)?",
    "preferred": r"nice[\s-]to[\s-]haves?|preferred(?:\s+(?:qualifications|skills))?|bonus(?:\s+points)?|"
                 r"good[\s-]to[\s-]haves?|pluses|it(?:'|’)?s\s+a\s+plus",
}  # fmt: skip

_RESUME_PATTERNS = {kind: re.compile(rf"{_RESUME_PREFIX}(?:{p})", re.IGNORECASE) for kind, p in RESUME_HEADINGS.items()}
_JD_PATTERNS = {kind: re.compile(rf"(?:{p})", re.IGNORECASE) for kind, p in JD_HEADINGS.items()}
_ENUMERATION = re.compile(r"[,|;/·]")


@dataclass(frozen=True)
class Line:
    text: str
    section: str  # a RESUME_HEADINGS key, or "header" before the first heading


@dataclass(frozen=True)
class JdLine:
    text: str
    section: str  # a JD_HEADINGS key, or "intro" before the first heading
    importance: str  # "required" | "preferred" | "neutral"


def heading_kind(line: str, patterns: dict[str, re.Pattern[str]]) -> str | None:
    """The kind of heading this line is, or None if it is not a heading."""
    text = line.strip().rstrip(":").strip()
    if not text or len(text.split()) > _MAX_HEADING_WORDS:
        return None
    for kind, pattern in patterns.items():
        if pattern.fullmatch(text):
            return kind
    return None


def resume_sections(text: str) -> list[Line]:
    """Every non-heading resume line with the section it belongs to."""
    section = "header"
    lines = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        kind = heading_kind(line, _RESUME_PATTERNS)
        if kind:
            section = kind
            continue
        lines.append(Line(line, section))
    return lines


def has_sections(lines: list[Line]) -> bool:
    return any(line.section != "header" for line in lines)


def jd_lines(text: str) -> list[JdLine]:
    """Every non-heading JD line with its section and importance.

    Importance: "preferred" in a preferred section or with a cue such as "nice to have" / "bonus";
    "required" in a requirements section or with a cue such as "must" / "required"; otherwise "neutral".
    A heading that ends with ':' but is not a known heading still passes its cues down ("Must have:").
    """
    section, inherited = "intro", ""
    lines = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        kind = heading_kind(line, _JD_PATTERNS)
        if kind:
            section, inherited = kind, ""
            continue
        if line.endswith(":") and len(line.split()) <= _MAX_HEADING_WORDS:
            inherited = line  # an unknown heading such as "Must have:"; its cue applies to the lines below
            continue
        lines.append(JdLine(line, section, _importance(line, section, inherited)))
    return lines


def _importance(line: str, section: str, inherited: str) -> str:
    if section == "preferred" or LOW_CUE.search(line) or LOW_CUE.search(inherited):
        return "preferred"
    if section == "requirements" or HIGH_CUE.search(line) or HIGH_CUE.search(inherited):
        return "required"
    return "neutral"


def is_list_line(line: str) -> bool:
    """True for an enumeration such as "Python, Django, Docker, Git" rather than a sentence describing work.

    A line with at least 3 separators whose pieces average 3 words or fewer is a list.
    """
    separators = len(_ENUMERATION.findall(line))
    if separators < 3:
        return False
    pieces = [piece for piece in _ENUMERATION.split(line) if piece.strip()]
    return sum(len(piece.split()) for piece in pieces) / max(1, len(pieces)) <= 3
