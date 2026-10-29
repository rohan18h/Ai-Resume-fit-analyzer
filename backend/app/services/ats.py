"""ATS formatting check (Objective 5, Section 10.5.6): can automated resume parsers read this PDF?

Main function:
    check_ats(pdf_bytes, parsed) -> AtsResult

This measures parseability and formatting only: text extraction, layout, structure and contact details. It never
sees the job description, so it is not a keyword-match or fit score, and it is not any vendor's score (Workday,
Greenhouse, Taleo... use their own private parsers). Other "ATS checkers" often also grade content, such as
numbers in bullets, action verbs or keywords, so their totals can legitimately differ from this one.

Ten checks, each pass / warn / fail with the evidence in its detail line and, for warn and fail, a short fix.
A check whose evidence is missing (no font data, no bulleted lists) is "na": shown as not checked and left out
of the score rather than counted as a pass.
score = round(100 * (passed + 0.5 * warned) / applicable checks)   (Section 10.5.6: warn counts as half)

Which check owns which symptom, so nothing is counted twice:
    unreadable glyphs "(cid:N)" and U+FFFD inside the text   text_extractable
    a leading bullet glyph (symbol, icon font or "(cid:N)")   bullets
    decorative symbols and icon glyphs inside the text       special_chars

The PDF is read from memory only, like the parser.
"""

from __future__ import annotations

import io
import logging
import re
import unicodedata
from collections.abc import Callable
from dataclasses import dataclass

import pdfplumber

from app.services.parser import ParsedResume, find_column_split, group_rows
from app.services.sections import resume_heading_kinds

logger = logging.getLogger("resume_fit")

POINTS = {"pass": 1.0, "warn": 0.5, "fail": 0.0}  # "na" earns nothing and is not counted

MIN_CHARS_PER_PAGE = 100  # a page with less selectable text is probably an image
# Unreadable glyphs per visible character. Thresholds from Resume-Matcher's garbled_glyphs check (Apache-2.0):
# https://github.com/srbhr/Resume-Matcher/blob/main/apps/backend/app/services/ats_parse/checks.py
GARBLED_WARN_RATIO = 0.005
GARBLED_FAIL_RATIO = 0.05
MAX_PAGES = 2
MAX_FONT_FAMILIES = 3
LARGE_IMAGE_SHARE = 0.15  # one image covering this share of a page is a "large image area"
MAX_SYMBOL_RATIO = 0.01  # decorative symbols per non-space character
# Contact details further into the text than this are often missed. Both Resume-Matcher (contact_info) and
# VeriWorkly's ATS engine (ats-v2.contact.position, https://github.com/VeriWorkly/ats-engine/blob/main/RUBRIC.md)
# use the first 25%.
CONTACT_TOP_SHARE = 0.25
MIN_MISSING_HEADINGS_FAIL = 3  # with 3 of the 5 standard sections missing, a parser can't find most sections
STANDARD_BULLETS = {"•", "-", "*", "–", "·"}  # •  -  *  –  ·
ICON_FONTS = re.compile(r"wingdings|webdings|dingbats|symbol|fontawesome|icon", re.IGNORECASE)

# The standard sections, found with the same heading rules as the fit score (sections.py).
SECTIONS: dict[str, str] = {
    "experience": "Experience", "education": "Education", "skills": "Skills", "projects": "Projects",
    "summary": "Summary/Objective",
}  # fmt: skip

_EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
_PHONE_CANDIDATE = re.compile(r"\+?\(?\d[\d\s().-]{7,}\d")
_GARBLED = re.compile(r"\(cid:\d+\)|�")


@dataclass(frozen=True)
class AtsCheck:
    id: str
    title: str
    status: str  # "pass" | "warn" | "fail" | "na"
    detail: str
    fix: str | None = None

    @property
    def credit(self) -> float | None:
        """Points towards the score: pass 1, warn 0.5, fail 0; None when not checked."""
        return POINTS.get(self.status)


@dataclass(frozen=True)
class AtsResult:
    score: int
    passed: int
    total: int  # checks that could be applied (excludes "na")
    checks: list[AtsCheck]


@dataclass
class _Page:
    number: int
    width: float
    height: float
    words: list[dict]
    rows: list[list[dict]]
    table_count: int
    largest_image_share: float


def check_ats(pdf_bytes: bytes, parsed: ParsedResume) -> AtsResult:
    """Run all checks. `parsed` is the parser's result for the same PDF."""
    pages = _read_pages(pdf_bytes)
    checks = [check(pages, parsed) for check in CHECKS]
    applied = [c for c in checks if c.status != "na"]
    score = round(100 * sum(c.credit for c in applied) / len(applied)) if applied else 0
    # Diagnostics only: counts and statuses, never resume text.
    logger.debug(
        "check_ats pages=%d lines=%d fonts=%d statuses=%s applicable=%d score=%d",
        len(pages), len(parsed.lines), len(parsed.fonts), {c.id: c.status for c in checks}, len(applied), score,
    )
    return AtsResult(score=score, passed=sum(c.status == "pass" for c in checks), total=len(applied), checks=checks)


def _read_pages(pdf_bytes: bytes) -> list[_Page]:
    pages = []
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for number, page in enumerate(pdf.pages, start=1):
            words = page.extract_words(extra_attrs=["fontname", "size"], keep_blank_chars=False)
            area = float(page.width * page.height)
            images = [
                max(0.0, (min(img["x1"], page.width) - max(img["x0"], 0)))
                * max(0.0, (min(img["bottom"], page.height) - max(img["top"], 0)))
                for img in page.images
            ]
            pages.append(
                _Page(
                    number=number,
                    width=float(page.width),
                    height=float(page.height),
                    words=words,
                    rows=group_rows(words),
                    table_count=len(page.find_tables()),
                    largest_image_share=max(images, default=0.0) / area if area else 0.0,
                )
            )
    return pages


def _pass(id_: str, title: str, detail: str) -> AtsCheck:
    return AtsCheck(id_, title, "pass", detail)


def _pages_text(numbers: list[int]) -> str:
    return ("page " if len(numbers) == 1 else "pages ") + ", ".join(map(str, numbers))


def _bullet_glyph(row: list[dict]) -> str | None:
    """The row's leading bullet glyph ("•", "-", "(cid:127)", an icon) or None if the row starts with text."""
    first = row[0]
    glyph = first["text"]
    if glyph.startswith("(cid:"):
        return glyph
    if ICON_FONTS.search(first["fontname"]) and len(glyph) <= 2:
        return glyph
    if glyph in STANDARD_BULLETS or glyph[:1] == "•":
        return glyph[:1]
    if len(glyph) == 1 and _is_symbol(glyph):
        return glyph
    return None


def _body_words(row: list[dict]) -> list[dict]:
    """The row without its leading bullet glyph (that glyph is the bullets check's job)."""
    return row[1:] if _bullet_glyph(row) else row


# ---------------------------------------------------------------------------
# The ten checks
# ---------------------------------------------------------------------------


def text_extractable(pages: list[_Page], parsed: ParsedResume) -> AtsCheck:
    """Fail if a page has almost no text (a scan); otherwise judge the share of unreadable glyphs."""
    title = "Text can be extracted"
    image_pages = [p.number for p in pages if sum(len(w["text"]) for w in p.words) < MIN_CHARS_PER_PAGE]
    if image_pages:
        return AtsCheck(
            "text_extractable", title, "fail",
            f"Almost no selectable text on {_pages_text(image_pages)}. It is probably a scanned image.",
            "Export the resume from Word or Google Docs as a text PDF instead of scanning it or using images of text.",
        )
    garbled = visible = 0
    for page in pages:
        for row in page.rows:
            for word in _body_words(row):
                found = _GARBLED.findall(word["text"])
                garbled += len(found)
                visible += len(_GARBLED.sub("x", word["text"]))  # an unreadable glyph is one character
    ratio = garbled / visible if visible else 0.0
    if ratio > GARBLED_WARN_RATIO:
        return AtsCheck(
            "text_extractable", title, "fail" if ratio > GARBLED_FAIL_RATIO else "warn",
            f"{garbled} characters come out unreadable ({ratio:.1%} of the text), so parsers see placeholders "
            "instead of letters.",
            "Use a standard font and export the PDF again from Word or Google Docs so every character is readable.",
        )
    return _pass("text_extractable", title, "Text can be selected on every page and reads cleanly.")


def multi_column(pages: list[_Page], parsed: ParsedResume) -> AtsCheck:
    title = "Single-column layout"
    columns = [p.number for p in pages if find_column_split(p.words, p.width) is not None]
    if columns:
        return AtsCheck(
            "multi_column", title, "warn",
            f"Text is laid out in two columns on {_pages_text(columns)}. Some ATS read across the columns and mix up "
            "sections.",
            "Use a single-column layout so ATS software reads your sections in the right order.",
        )
    return _pass("multi_column", title, "Text flows in one column.")


def tables(pages: list[_Page], parsed: ParsedResume) -> AtsCheck:
    title = "No tables"
    with_tables = [p.number for p in pages if p.table_count]
    if with_tables:
        return AtsCheck(
            "tables", title, "warn",
            f"Found a table on {_pages_text(with_tables)}. ATS often read table cells in the wrong order or skip them.",
            "Replace the table with plain lines of text.",
        )
    return _pass("tables", title, "No tables found.")


def images(pages: list[_Page], parsed: ParsedResume) -> AtsCheck:
    title = "No images holding text"
    large = [p.number for p in pages if p.largest_image_share >= LARGE_IMAGE_SHARE]
    if large:
        return AtsCheck(
            "images", title, "warn",
            f"A large image covers part of {_pages_text(large)}. ATS cannot read text inside images.",
            "Put important information in normal text, not inside images or graphics.",
        )
    return _pass("images", title, "No large images found.")


def section_headings(pages: list[_Page], parsed: ParsedResume) -> AtsCheck:
    """Pass with all 5 standard headings, warn with 1-2 missing, fail with 3 or more missing."""
    title = "Standard section headings"
    found = resume_heading_kinds([line.text for line in parsed.lines])
    missing = [name for kind, name in SECTIONS.items() if kind not in found]
    if missing:
        return AtsCheck(
            "section_headings", title, "fail" if len(missing) >= MIN_MISSING_HEADINGS_FAIL else "warn",
            f"Found {len(SECTIONS) - len(missing)} of {len(SECTIONS)} standard headings. "
            f"Missing: {', '.join(missing)}.",
            f"Add clear headings such as {', '.join(missing)} so ATS can find each section.",
        )
    return _pass("section_headings", title, "Found Experience, Education, Skills, Projects and Summary headings.")


def contact_info(pages: list[_Page], parsed: ParsedResume) -> AtsCheck:
    """Fail without email and phone, warn with one missing or with the email far down the page."""
    title = "Email and phone present"
    # Read every word in reading order, including page headers the parser drops.
    raw = "\n".join(" ".join(w["text"] for w in row) for page in pages for row in page.rows)
    email = _EMAIL.search(raw)
    has_phone = any(10 <= sum(ch.isdigit() for ch in m.group()) <= 13 for m in _PHONE_CANDIDATE.finditer(raw))
    missing = [name for name, found in (("email address", email), ("phone number", has_phone)) if not found]
    if missing:
        return AtsCheck(
            "contact_info", title, "fail" if len(missing) == 2 else "warn",
            f"No {' or '.join(missing)} found as text.",
            f"Add your {' and '.join(missing)} as plain text near the top of the resume.",
        )
    position = email.start() / max(1, len(raw))
    if position > CONTACT_TOP_SHARE:
        return AtsCheck(
            "contact_info", title, "warn",
            f"The email address first appears {position:.0%} of the way through the text, not near the top.",
            "Put your email address and phone number at the top of the first page.",
        )
    return _pass("contact_info", title, "Found an email address and a phone number near the top.")


def length(pages: list[_Page], parsed: ParsedResume) -> AtsCheck:
    title = "Length is 1-2 pages"
    if len(pages) > MAX_PAGES:
        return AtsCheck(
            "length", title, "warn", f"The resume has {len(pages)} pages.",
            "Keep the resume to one or two pages; move older or less relevant details out.",
        )
    return _pass("length", title, f"The resume has {len(pages)} page{'s' if len(pages) > 1 else ''}.")


def fonts(pages: list[_Page], parsed: ParsedResume) -> AtsCheck:
    title = "Few fonts"
    if not parsed.fonts:
        return AtsCheck("fonts", title, "na", "Not checked: the PDF does not name its fonts.")
    if len(parsed.fonts) > MAX_FONT_FAMILIES:
        return AtsCheck(
            "fonts", title, "warn", f"Uses {len(parsed.fonts)} font families: {', '.join(parsed.fonts)}.",
            "Use one or two standard fonts, such as Arial or Calibri.",
        )
    return _pass("fonts", title, f"Uses {len(parsed.fonts)} font famil{'y' if len(parsed.fonts) == 1 else 'ies'}.")


def special_chars(pages: list[_Page], parsed: ParsedResume) -> AtsCheck:
    title = "Few unusual symbols"
    symbols = total = 0
    for page in pages:
        for row in page.rows:
            text = "".join(w["text"] for w in _body_words(row))
            total += len(text)
            symbols += sum(_is_symbol(ch) for ch in text)
    ratio = symbols / total if total else 0.0
    if ratio > MAX_SYMBOL_RATIO:
        return AtsCheck(
            "special_chars", title, "warn",
            f"Found {symbols} decorative symbols or icons ({ratio:.1%} of the characters), such as stars or phone "
            "icons.",
            "Remove decorative symbols, icons and star ratings; use plain words instead.",
        )
    return _pass("special_chars", title, "No unusual symbols found.")


def _is_symbol(ch: str) -> bool:
    return unicodedata.category(ch) in ("So", "Co")  # other symbols (★ ✉ ☎) and private-use icon glyphs


def bullets(pages: list[_Page], parsed: ParsedResume) -> AtsCheck:
    title = "Plain bullets"
    glyphs = [glyph for page in pages for row in page.rows if (glyph := _bullet_glyph(row))]
    if not glyphs:
        return AtsCheck("bullets", title, "na", "Not checked: no bulleted lists were found.")
    odd = sorted({"unreadable glyph" if g.startswith("(cid:") else g[0] for g in glyphs if g not in STANDARD_BULLETS})
    if odd:
        return AtsCheck(
            "bullets", title, "warn",
            f"Uses non-standard bullet symbols ({', '.join(odd)}) that ATS may not read.",
            "Use simple round bullets (•) or hyphens instead of symbols or icon fonts.",
        )
    return _pass("bullets", title, f"All {len(glyphs)} bullets use plain symbols.")


CHECKS: list[Callable[[list[_Page], ParsedResume], AtsCheck]] = [
    text_extractable, multi_column, tables, images, section_headings,
    contact_info, length, fonts, special_chars, bullets,
]  # fmt: skip
