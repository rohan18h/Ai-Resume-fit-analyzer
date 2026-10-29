"""Parser (Objective 1): PDF bytes -> text with layout, plus text cleaning.

Main functions:
    extract_text(pdf_bytes) -> ParsedResume
    clean_text(text) -> str          lowercase copy used for skills and TF-IDF
    clean_text_light(text) -> str    original casing, lines intact, for embeddings and snippets
    strip_name_header(text) -> str   bias safety: drop the name line at the top of a resume
    remove_stopwords(text) -> str    NLTK English stopword removal

The PDF is read from memory only. Nothing is written to disk or logged.
"""

from __future__ import annotations

import io
import logging
import re
from collections import Counter
from dataclasses import dataclass, field
from functools import lru_cache

import pdfplumber
from pdfminer.pdfparser import PDFSyntaxError
from pdfminer.psparser import PSException
from pdfplumber.utils.exceptions import PdfminerException

from app import config

# pdfminer logs font warnings that include no content but are noisy.
logging.getLogger("pdfminer").setLevel(logging.ERROR)


class ParserError(Exception):
    """Base class for parser errors. `code` matches the API error codes in Section 10.3."""

    code = "unreadable_pdf"


class InvalidPdf(ParserError):
    """The bytes are not a PDF (no %PDF magic bytes)."""

    code = "invalid_file_type"


class UnreadablePdf(ParserError):
    """The PDF is broken or has no extractable text (probably a scanned image)."""

    code = "unreadable_pdf"


@dataclass
class TextLine:
    """One line of text with its position on the page (PDF points, origin top-left)."""

    text: str
    page: int  # 1-based
    x0: float
    x1: float
    top: float
    bottom: float
    size: float
    fontname: str


@dataclass
class ParsedResume:
    """Result of extract_text. `lines` and `fonts` are reused by the ATS checker."""

    text: str
    pages: int
    lines: list[TextLine] = field(default_factory=list)
    fonts: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Extraction
# ---------------------------------------------------------------------------

_ROW_TOLERANCE = 3.0  # words whose tops differ by less than this (points) share a row
_EDGE_ZONE = 0.08  # top/bottom share of the page where headers and footers live
_GUTTER_MAX_ROW_SHARE = 0.15  # a column gutter is crossed by at most this share of rows
_GUTTER_MIN_WIDTH = 6  # points
_COLUMN_MIN_WORD_SHARE = 0.15  # each column must hold at least this share of the words
_PAGE_NUMBER = re.compile(r"^(page\s*)?\d{1,3}(\s*(/|of)\s*\d{1,3})?$", re.IGNORECASE)


def extract_text(pdf_bytes: bytes) -> ParsedResume:
    """Extract text from a PDF held in memory.

    Two-column layouts are read column by column, repeated headers/footers and page numbers are removed.

    Raises:
        InvalidPdf: the bytes do not start with the %PDF magic bytes.
        UnreadablePdf: the PDF cannot be opened or has fewer than MIN_EXTRACTED_CHARS characters of text.
    """
    if not pdf_bytes.lstrip()[:5].startswith(b"%PDF"):
        raise InvalidPdf("The file is not a PDF.")

    try:
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            page_lines: list[list[TextLine]] = []
            page_heights: list[float] = []
            for number, page in enumerate(pdf.pages, start=1):
                page_lines.append(_page_lines(page, number))
                page_heights.append(float(page.height))
            page_count = len(pdf.pages)
    except (PdfminerException, PDFSyntaxError, PSException, ValueError, KeyError, TypeError) as exc:
        raise UnreadablePdf("The PDF could not be opened.") from exc

    page_lines = _remove_headers_and_footers(page_lines, page_heights)
    lines = [line for page in page_lines for line in page]

    text = "\n\n".join("\n".join(_readable(line.text) for line in page) for page in page_lines if page).strip()
    if len(text) < config.MIN_EXTRACTED_CHARS:
        raise UnreadablePdf("No readable text found. The PDF may be a scanned image.")

    return ParsedResume(text=text, pages=page_count, lines=lines, fonts=_font_families(lines))


def count_pages(pdf_bytes: bytes) -> int:
    """Number of pages, without extracting text. Raises InvalidPdf / UnreadablePdf like extract_text."""
    if not pdf_bytes.lstrip()[:5].startswith(b"%PDF"):
        raise InvalidPdf("The file is not a PDF.")
    try:
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            return len(pdf.pages)
    except (PdfminerException, PDFSyntaxError, PSException, ValueError, KeyError, TypeError) as exc:
        raise UnreadablePdf("The PDF could not be opened.") from exc


def _page_lines(page: pdfplumber.page.Page, number: int) -> list[TextLine]:
    """Return the lines of one page in reading order (column by column)."""
    words = page.extract_words(extra_attrs=["fontname", "size"], keep_blank_chars=False)
    if not words:
        return []

    split = _find_column_split(words, float(page.width))
    if split is None:
        segments = [words]
    else:
        # Everything above the start of the right column is the page header (name, contact line) and is read
        # first, row by row. Lower down, rows that run across the gutter stay whole and are read after the columns.
        rows = _group_rows(words)
        right_top = min(
            (w["top"] for row in rows if not _row_spans(row, split) for w in row if w["x0"] >= split),
            default=float("inf"),
        )
        above, left, right, below = [], [], [], []
        for row in rows:
            if row[0]["top"] < right_top - _ROW_TOLERANCE:
                above.extend(row)
            elif _row_spans(row, split):
                below.extend(row)
            else:
                left.extend(w for w in row if w["x1"] <= split)
                right.extend(w for w in row if w["x0"] >= split)
        segments = [above, left, right, below]

    lines: list[TextLine] = []
    for segment in segments:
        lines.extend(_row_to_line(row, number) for row in _group_rows(segment))
    return lines


def _row_spans(row: list[dict], split: float) -> bool:
    """True if a row crosses the gutter: a word straddles it, or words on both sides sit close together."""
    if any(w["x0"] < split < w["x1"] for w in row):
        return True
    left_edge = max((w["x1"] for w in row if w["x1"] <= split), default=None)
    right_edge = min((w["x0"] for w in row if w["x0"] >= split), default=None)
    return left_edge is not None and right_edge is not None and right_edge - left_edge < _GUTTER_MIN_WIDTH * 2


def _group_rows(words: list[dict]) -> list[list[dict]]:
    """Group words into rows by their top position, each row sorted left to right."""
    rows: list[list[dict]] = []
    for word in sorted(words, key=lambda w: (w["top"], w["x0"])):
        if rows and abs(word["top"] - rows[-1][0]["top"]) <= _ROW_TOLERANCE:
            rows[-1].append(word)
        else:
            rows.append([word])
    return [sorted(row, key=lambda w: w["x0"]) for row in rows]


def _find_column_split(words: list[dict], page_width: float) -> float | None:
    """Find the x position of a column gutter, or None for a single-column page.

    A gutter is a vertical band in the middle 60% of the page that almost no row of text crosses,
    with a fair share of the words on each side of it.
    """
    if len(words) < 20:
        return None
    rows = _group_rows(words)
    max_crossing = max(1, int(len(rows) * _GUTTER_MAX_ROW_SHARE))

    def crossing(x: int) -> int:
        return sum(1 for row in rows if any(w["x0"] <= x <= w["x1"] for w in row))

    best: tuple[int, float] | None = None  # (crossing count, split x)
    run_start: int | None = None
    run_min = 0
    for x in range(int(page_width * 0.2), int(page_width * 0.8) + 1):
        count = crossing(x)
        if count <= max_crossing:
            if run_start is None:
                run_start, run_min = x, count
            run_min = min(run_min, count)
            continue
        if run_start is not None:
            best = _better_gutter(best, run_start, x - 1, run_min, words)
            run_start = None
    if run_start is not None:
        best = _better_gutter(best, run_start, int(page_width * 0.8), run_min, words)
    return None if best is None else best[1]


def _better_gutter(
    best: tuple[int, float] | None, start: int, end: int, count: int, words: list[dict]
) -> tuple[int, float] | None:
    """Keep the candidate gutter with fewer crossing rows, if it is wide enough and balanced."""
    if end - start + 1 < _GUTTER_MIN_WIDTH:
        return best
    split = (start + end) / 2
    left = sum(1 for w in words if w["x1"] <= split)
    right = sum(1 for w in words if w["x0"] >= split)
    if min(left, right) < len(words) * _COLUMN_MIN_WORD_SHARE:
        return best
    if best is None or count < best[0]:
        return (count, split)
    return best


_CID = re.compile(r"\(cid:\d+\)")


def _readable(line: str) -> str:
    """Replace unmapped glyphs like '(cid:127)': a leading one is almost always a bullet, others are dropped.

    TextLine.text keeps the raw form so the ATS checker can flag unusual glyphs.
    """
    line = _CID.sub("•", line, count=1) if _CID.match(line) else line
    return re.sub(r"\s{2,}", " ", _CID.sub("", line)).strip()


def _row_to_line(row: list[dict], page: int) -> TextLine:
    fonts = Counter(w["fontname"] for w in row)
    return TextLine(
        text=" ".join(w["text"] for w in row),
        page=page,
        x0=float(min(w["x0"] for w in row)),
        x1=float(max(w["x1"] for w in row)),
        top=float(min(w["top"] for w in row)),
        bottom=float(max(w["bottom"] for w in row)),
        size=round(sum(float(w["size"]) for w in row) / len(row), 2),
        fontname=fonts.most_common(1)[0][0],
    )


def _remove_headers_and_footers(
    page_lines: list[list[TextLine]], page_heights: list[float]
) -> list[list[TextLine]]:
    """Drop page numbers and lines repeated in the top/bottom zone of two or more pages."""

    def in_edge_zone(line: TextLine) -> bool:
        height = page_heights[line.page - 1]
        return line.top < height * _EDGE_ZONE or line.bottom > height * (1 - _EDGE_ZONE)

    def signature(line: TextLine) -> str:
        # Only lines that mention "page" may differ by their numbers ("Asha Verma | Page 2"), so that real
        # headings near the top of each page ("Project 2", "Project 3") are not mistaken for headers.
        text = line.text.lower().strip()
        return re.sub(r"\d+", "#", text) if "page" in text else text

    edge_counts: Counter[str] = Counter()
    for page in page_lines:
        edge_counts.update({signature(line) for line in page if in_edge_zone(line)})

    cleaned: list[list[TextLine]] = []
    for page in page_lines:
        kept = []
        for line in page:
            if in_edge_zone(line) and (
                _PAGE_NUMBER.match(line.text.strip()) or (len(page_lines) > 1 and edge_counts[signature(line)] >= 2)
            ):
                continue
            kept.append(line)
        cleaned.append(kept)
    return cleaned


def _font_families(lines: list[TextLine]) -> list[str]:
    """Distinct font families, e.g. 'ABCDEF+Arial-BoldMT' -> 'Arial'."""
    families = set()
    for line in lines:
        name = line.fontname.split("+")[-1]
        name = re.split(r"[-,]", name)[0]
        name = re.sub(r"(MT|PS)$", "", name)
        if name:
            families.add(name)
    return sorted(families)


# ---------------------------------------------------------------------------
# Cleaning
# ---------------------------------------------------------------------------

_EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
# Full URLs, plus bare profile links such as linkedin.com/in/name. TLDs like .net and .io are left out
# on purpose so that skills such as ASP.NET and Socket.IO survive.
_URL = re.compile(r"(?:https?://|www\.)\S+|\b[\w-]+(?:\.[\w-]+)*\.(?:com|org|in|dev|me)(?:/\S*)?(?!\w)", re.IGNORECASE)
_PHONE = re.compile(r"(?<!\w)\+?\(?\d[\d\s().-]{7,}\d(?!\w)")
_ADDRESS_WORDS = re.compile(
    r"\b(street|st\.|road|rd\.|lane|avenue|ave\.|nagar|colony|sector|apartment|apt\.?|flat|floor|marg|chowk)\b",
    re.IGNORECASE,
)
_BULLET_CHARS = "•●○◦▪▫■□➢➤►▶✓✔‣∙·*"
_LEADING_BULLET = re.compile(rf"^\s*(?:[{re.escape(_BULLET_CHARS)}]|[-–—](?=\s))\s*")
_INLINE_BULLET = re.compile(rf"\s*[{re.escape(_BULLET_CHARS)}]\s*")
_NON_TOKEN_CHARS = re.compile(r"[^\w+#./\-\s]")
_SECTION_WORDS = {
    "summary", "objective", "profile", "experience", "education", "skills", "projects",
    "certifications", "achievements", "contact", "resume", "curriculum", "vitae",
}  # fmt: skip


def _replace_phone(match: re.Match[str]) -> str:
    """Remove phone numbers (10-13 digits) but keep things like year ranges ('2019 - 2021')."""
    digits = sum(ch.isdigit() for ch in match.group())
    return " " if 10 <= digits <= 13 else match.group()


def _remove_identifiers(line: str) -> str:
    """Remove emails, URLs and phone numbers from one line. Drop the line if it looks like a street address."""
    if _ADDRESS_WORDS.search(line) and re.search(r"\d", line) and len(line) < 120:
        return ""
    line = _EMAIL.sub(" ", line)
    line = _URL.sub(" ", line)
    return _PHONE.sub(_replace_phone, line)


def clean_text_light(text: str) -> str:
    """Lightly cleaned copy: original casing and lines kept, identifiers and bullet glyphs removed.

    Used for sentence embeddings and for showing snippets.
    """
    lines = []
    for raw in text.splitlines():
        line = _remove_identifiers(raw)
        line = _LEADING_BULLET.sub("", line)
        line = _INLINE_BULLET.sub(", ", line)
        line = re.sub(r"[ \t]+", " ", line).strip(" ,|")
        if line:
            lines.append(line)
    return "\n".join(lines)


def clean_text(text: str) -> str:
    """Lowercase, single-spaced copy for skill matching and TF-IDF.

    Removes URLs, emails, phone numbers, addresses, bullets and stray symbols, but keeps tech tokens
    such as c++, c#, node.js, .net and ci/cd.
    """
    lowered = _NON_TOKEN_CHARS.sub(" ", clean_text_light(text).lower())
    return " ".join(token for token in (_clean_token(t) for t in lowered.split()) if token)


def _clean_token(token: str) -> str:
    token = token.rstrip("./-").lstrip("/-")
    if token.startswith(".") and not token[1:].isalpha():
        token = token.lstrip(".")
    return token if any(ch.isalnum() for ch in token) else ""


def strip_name_header(text: str) -> str:
    """Bias safety: remove the candidate's name line from the top of a resume.

    Looks at the first three non-empty lines and drops the first one that looks like a name
    (2-4 capitalised words, no digits, not a section heading). Only used for resumes, not job descriptions.
    """
    lines = text.splitlines()
    seen = 0
    for index, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            continue
        seen += 1
        if _looks_like_name(stripped):
            return "\n".join(lines[:index] + lines[index + 1 :])
        if seen >= 3:
            break
    return text


def _looks_like_name(line: str) -> bool:
    words = line.split()
    if not 2 <= len(words) <= 4 or len(line) > 40:
        return False
    if any(word.lower().strip(".") in _SECTION_WORDS for word in words):
        return False
    return all(re.fullmatch(r"[A-Z][A-Za-z'.-]*", word) for word in words)


@lru_cache(maxsize=1)
def english_stopwords() -> frozenset[str]:
    """NLTK's English stopword list. Needs the one-time download: python -c "import nltk; nltk.download('stopwords')"."""
    from nltk.corpus import stopwords

    return frozenset(stopwords.words("english"))


def remove_stopwords(text: str) -> str:
    """Remove NLTK English stopwords from already-cleaned (lowercase, single-spaced) text."""
    stop = english_stopwords()
    return " ".join(token for token in text.split() if token not in stop)
