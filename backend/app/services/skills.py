"""Skills extractor: finds known skills in a resume or job description (Section 10.5.2).

Main functions:
    extract_skills(text) -> list[SkillHit]     canonical skill names with mention counts
    rank_jd_skills(jd_text) -> list[JdSkill]   JD skills with mentions and importance (high / medium / low)

Skills and aliases come from SQLite and are matched with a spaCy PhraseMatcher on lowercase tokens, so
multi-word skills ("machine learning") and aliases ("k8s" -> kubernetes) work.

Limitation: only skills in the database are detected. Anything else (e.g. a new framework) is missed.
"""

from __future__ import annotations

import re
import sqlite3
from collections import Counter
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import spacy
from spacy.matcher import PhraseMatcher
from spacy.tokens import Doc, Span
from spacy.util import filter_spans

from app.db import Skill, connect, fetch_skills
from app.services.parser import clean_text_light

# Very short names that are only skills in a tech context. They must match case-sensitively ("C", "R", "Go"),
# stand alone, and sit next to other skills or on a "Skills:" line.
STRICT_TERMS = frozenset({"c", "r", "go"})

# Skills that are also everyday English words ("react quickly", "Excel at teamwork", "the rest of the team").
# They count when they sit next to other skills or on a "Skills:" line, or when written capitalised mid-sentence.
WORD_TERMS = frozenset({
    "react", "swift", "spring", "excel", "rest", "spark", "rust", "jest", "bootstrap", "postman", "selenium",
    "ruby", "angular", "flutter", "ts", "pandas", "azure", "cypress", "bash", "flask",
})  # fmt: skip

CONTEXT_WINDOW = 8  # tokens on each side to look for another skill

_SKILL_LINE = re.compile(
    r"^\W*(technical\s+|key\s+|core\s+)?(skills?|technologies|tech(nical)?\s+stack|tools?|languages?|"
    r"programming\s+languages|frameworks?|platforms?|expertise)\b",
    re.IGNORECASE,
)
_HIGH_CUE = re.compile(r"\b(required|requirements?|must|mandatory|essential)\b", re.IGNORECASE)
_LOW_CUE = re.compile(r"\b(preferred|nice[\s-]to[\s-]have|bonus|plus|good[\s-]to[\s-]have)\b", re.IGNORECASE)
_SENTENCE_END = {".", "!", "?", ";"}
_ATTACHING = {"-", "&", "'", "’"}

IMPORTANCE_ORDER = {"high": 0, "medium": 1, "low": 2}


@dataclass(frozen=True)
class SkillHit:
    name: str
    display_name: str
    category: str
    count: int


@dataclass(frozen=True)
class JdSkill:
    name: str
    display_name: str
    category: str
    mentions: int
    importance: str  # "high" | "medium" | "low"


@dataclass(frozen=True)
class _Mention:
    name: str
    cues: frozenset[str]  # subset of {"high", "low"} from the sentence or the section heading


class SkillExtractor:
    """Holds the spaCy tokenizer and PhraseMatcher. Build once at startup and reuse for every request."""

    def __init__(self, skills: list[Skill]) -> None:
        self.nlp = spacy.blank("en")
        self.skills = {skill.name: skill for skill in skills}
        self.matcher = PhraseMatcher(self.nlp.vocab, attr="LOWER")
        for skill in skills:
            terms = sorted({skill.name, *skill.aliases})
            self.matcher.add(skill.name, list(self.nlp.tokenizer.pipe(terms)))

    def mentions(self, text: str) -> list[_Mention]:
        """Every accepted skill mention in reading order, with the importance cues around it."""
        text = clean_text_light(text)
        if not text:
            return []
        doc = self.nlp.make_doc(text)
        layout = _Layout(doc)

        spans = filter_spans([Span(doc, start, end, label=key) for key, start, end in self.matcher(doc)])
        accepted = [span for span in spans if not _is_ambiguous(span)]
        pending = [span for span in spans if _is_ambiguous(span)]
        # Ambiguous mentions can vouch for each other ("Languages: C, R, Go"), so repeat until nothing changes.
        changed = True
        while changed:
            changed = False
            for span in list(pending):
                if self._accept_ambiguous(span, accepted, layout):
                    accepted.append(span)
                    pending.remove(span)
                    changed = True

        accepted.sort(key=lambda span: span.start)
        return [_Mention(span.label_, layout.cues(span.start)) for span in accepted]

    def _accept_ambiguous(self, span: Span, accepted: list[Span], layout: _Layout) -> bool:
        if _attached(span):
            return False
        in_context = layout.skill_line(span.start) or any(
            abs(other.start - span.start) <= CONTEXT_WINDOW for other in accepted if other is not span
        )
        term = span.text.lower()
        if term in STRICT_TERMS:
            skill = self.skills[span.label_]
            return in_context and span.text in {skill.display_name, term.upper()}
        if in_context:
            return True
        return span.text[:1].isupper() and not layout.sentence_start(span.start)

    def hits(self, text: str) -> list[SkillHit]:
        counts = Counter(mention.name for mention in self.mentions(text))
        return [self._hit(name, count) for name, count in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))]

    def jd_skills(self, jd_text: str) -> list[JdSkill]:
        mentions = self.mentions(jd_text)
        counts = Counter(mention.name for mention in mentions)
        cues: dict[str, set[str]] = {}
        for mention in mentions:
            cues.setdefault(mention.name, set()).update(mention.cues)

        ranked = []
        for name, count in counts.items():
            if "high" in cues[name] or count >= 3:
                importance = "high"
            elif "low" in cues[name]:
                importance = "low"
            else:
                importance = "medium"
            skill = self.skills[name]
            ranked.append(JdSkill(name, skill.display_name, skill.category, count, importance))
        return sorted(ranked, key=lambda s: (IMPORTANCE_ORDER[s.importance], -s.mentions, s.name))

    def _hit(self, name: str, count: int) -> SkillHit:
        skill = self.skills[name]
        return SkillHit(name, skill.display_name, skill.category, count)


class _Layout:
    """Splits a Doc into lines and sentences and works out the cues and skill-list lines for each token.

    A line that ends with ':' is a heading ("Nice to have:"); its cue applies to the lines below it until the
    next heading, because job descriptions usually list skills as bullets under such headings.
    """

    def __init__(self, doc: Doc) -> None:
        self.sentence_of: list[int] = []
        self.line_of: list[int] = []
        self.sentence_first: dict[int, int] = {}
        sentences: list[list[int]] = [[]]
        lines: list[list[int]] = [[]]
        for token in doc:
            self.sentence_of.append(len(sentences) - 1)
            self.line_of.append(len(lines) - 1)
            if token.is_space and "\n" in token.text:
                sentences.append([])
                lines.append([])
                continue
            if token.is_space:
                continue
            sentences[-1].append(token.i)
            lines[-1].append(token.i)
            self.sentence_first.setdefault(len(sentences) - 1, token.i)
            if token.text in _SENTENCE_END:
                sentences.append([])

        def text_of(indexes: list[int]) -> str:
            return doc[indexes[0] : indexes[-1] + 1].text if indexes else ""

        self._sentence_cues = [_cues(text_of(s)) for s in sentences]
        self._sentence_line = [self.line_of[s[0]] if s else 0 for s in sentences]
        self._skill_lines = {n for n, line in enumerate(lines) if _SKILL_LINE.match(text_of(line))}

        self._line_cues: list[frozenset[str]] = []
        inherited: frozenset[str] = frozenset()
        for line in lines:
            line_text = text_of(line).strip()
            if line_text.endswith(":"):
                inherited = _cues(line_text)
            self._line_cues.append(inherited)

    def cues(self, token_index: int) -> frozenset[str]:
        sentence = self.sentence_of[token_index]
        return self._sentence_cues[sentence] | self._line_cues[self._sentence_line[sentence]]

    def skill_line(self, token_index: int) -> bool:
        return self.line_of[token_index] in self._skill_lines

    def sentence_start(self, token_index: int) -> bool:
        return self.sentence_first.get(self.sentence_of[token_index]) == token_index


def _cues(text: str) -> frozenset[str]:
    found = set()
    if _HIGH_CUE.search(text):
        found.add("high")
    if _LOW_CUE.search(text):
        found.add("low")
    return frozenset(found)


def _is_ambiguous(span: Span) -> bool:
    term = span.text.lower()
    return term in STRICT_TERMS or term in WORD_TERMS


def _attached(span: Span) -> bool:
    """True if the word is glued to its neighbour, e.g. 'C-level', 'Go-to-market', 'Series-C'."""
    doc = span.doc
    if span.start > 0:
        before = doc[span.start - 1]
        if not before.whitespace_ and (before.text in _ATTACHING or before.is_alpha):
            return True
    last = doc[span.end - 1]
    return span.end < len(doc) and not last.whitespace_ and doc[span.end].text in _ATTACHING


# ---------------------------------------------------------------------------
# Module-level API (uses one shared extractor loaded from SQLite)
# ---------------------------------------------------------------------------


@lru_cache(maxsize=1)
def get_extractor(db_path: Path | str | None = None) -> SkillExtractor:
    """Load all skills from SQLite and build the matcher once. Raises RuntimeError if the DB is not seeded."""
    conn = connect(db_path)
    try:
        skills = fetch_skills(conn)
    except sqlite3.OperationalError as exc:
        raise RuntimeError("The skills database is missing. Run: python scripts/seed_db.py") from exc
    finally:
        conn.close()
    if not skills:
        raise RuntimeError("The skills database is empty. Run: python scripts/seed_db.py")
    return SkillExtractor(skills)


def extract_skills(text: str, extractor: SkillExtractor | None = None) -> list[SkillHit]:
    """Canonical skills found in the text with mention counts, most mentioned first."""
    return (extractor or get_extractor()).hits(text)


def rank_jd_skills(jd_text: str, extractor: SkillExtractor | None = None) -> list[JdSkill]:
    """JD skills with mentions and importance, sorted high -> low, then by mentions.

    high: in a sentence (or under a heading) with "required", "must", "mandatory", "essential", or mentioned 3+ times
    low: in a sentence (or under a heading) with "preferred", "nice to have", "bonus", "plus", "good to have"
    medium: everything else
    """
    return (extractor or get_extractor()).jd_skills(jd_text)
