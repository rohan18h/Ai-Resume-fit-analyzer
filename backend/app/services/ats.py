"""ATS checker (Objective 5, Section 10.5.6): rule-based checks for resume formatting that ATS software struggles with.

Main function:
    check_ats(pdf_bytes, parsed) -> AtsResult

Ten checks, each pass / warn / fail with a detail line and, for warn and fail, a short actionable fix.
Each check also earns a credit from 0 to 1: pass 1, fail 0, and for warn the share that is right where that can be
measured (3 of 5 standard headings = 0.6; two columns on 1 of 2 pages = 0.75), otherwise 0.5.
score = round(100 * sum(credits) / total). Only the resume is checked: the job description never changes it.

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

MIN_CHARS_PER_PAGE = 100  # a page with less selectable text is probably an image
MAX_PAGES = 2
MAX_FONT_FAMILIES = 3
LARGE_IMAGE_SHARE = 0.15  # one image covering this share of a page is a "large image area"
MAX_SYMBOL_RATIO = 0.01  # decorative symbols per non-space character
STANDARD_BULLETS = {"•", "-", "*", "–", "·"}  # •  -  *  –  ·
ICON_FONTS = re.compile(r"wingdings|webdings|dingbats|symbol|fontawesome|icon", re.IGNORECASE)

# The standard sections, found with the same heading rules as the fit score (sections.py).
SECTIONS: dict[str, str] = {
    "experience": "Experience", "education": "Education", "skills": "Skills", "projects": "Projects",
    "summary": "Summary/Objective",
}  # fmt: skip

_EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
_PHONE_CANDIDATE = re.compile(r"\+?\(?\d[\d\s().-]{7,}\d")


@dataclass(frozen=True)
class AtsCheck:
    id: str
    title: str
    status: str  # "pass" | "warn" | "fail"
    detail: str
    fix: str | None = None
    credit: float | None = None  # 0-1 towards the score; None = from the status (pass 1, warn 0.5, fail 0)

    def __post_init__(self) -> None:
        if self.credit is None:
            object.__setattr__(self, "credit", {"pass": 1.0, "warn": 0.5}.get(self.status, 0.0))


@dataclass(frozen=True)
class AtsResult:
    score: int
    passed: int
    total: int
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
    passed = sum(c.status == "pass" for c in checks)
    score = round(100 * sum(c.credit for c in checks) / len(checks))
    # Diagnostics only: counts, statuses and credits, never resume text.
    logger.debug(
        "check_ats pages=%d lines=%d fonts=%d credits=%s score=%d",
        len(pages), len(parsed.lines), len(parsed.fonts), {c.id: round(c.credit, 2) for c in checks}, score,
    )
    return AtsResult(
        score=score,
        passed=passed,
        total=len(checks),
        checks=checks,
    )


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


def _page_share_credit(affected: list[int], pages: list[_Page]) -> float:
    """Warn credit for a layout problem on some pages: 0.5 when every page has it, more when fewer do."""
    return 1 - 0.5 * len(affected) / max(1, len(pages))


def _pages_text(numbers: list[int]) -> str:
    return ("page " if len(numbers) == 1 else "pages ") + ", ".join(map(str, numbers))


# ---------------------------------------------------------------------------
# The ten checks
# ---------------------------------------------------------------------------


def text_extractable(pages: list[_Page], parsed: ParsedResume) -> AtsCheck:
    title = "Text can be extracted"
    image_pages = [p.number for p in pages if sum(len(w["text"]) for w in p.words) < MIN_CHARS_PER_PAGE]
    if image_pages:
        return AtsCheck(
            "text_extractable", title, "fail",
            f"Almost no selectable text on {_pages_text(image_pages)}. It is probably a scanned image.",
            "Export the resume from Word or Google Docs as a text PDF instead of scanning it or using images of text.",
            credit=1 - len(image_pages) / max(1, len(pages)),  # text on the other pages can still be read
        )
    return _pass("text_extractable", title, "Text can be selected on every page.")


def multi_column(pages: list[_Page], parsed: ParsedResume) -> AtsCheck:
    title = "Single-column layout"
    columns = [p.number for p in pages if find_column_split(p.words, p.width) is not None]
    if columns:
        return AtsCheck(
            "multi_column", title, "warn",
            f"Text is laid out in two columns on {_pages_text(columns)}. Some ATS read across the columns and mix up "
            "sections.",
            "Use a single-column layout so ATS software reads your sections in the right order.",
            credit=_page_share_credit(columns, pages),
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
            credit=_page_share_credit(with_tables, pages),
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
            credit=_page_share_credit(large, pages),
        )
    return _pass("images", title, "No large images found.")


def section_headings(pages: list[_Page], parsed: ParsedResume) -> AtsCheck:
    """Each of the 5 standard sections found earns 1/5 of this check; none found is a fail."""
    title = "Standard section headings"
    found = resume_heading_kinds([line.text for line in parsed.lines])
    missing = [name for kind, name in SECTIONS.items() if kind not in found]
    if missing:
        return AtsCheck(
            "section_headings", title, "fail" if len(missing) == len(SECTIONS) else "warn",
            f"Found {len(SECTIONS) - len(missing)} of {len(SECTIONS)} standard headings. "
            f"Missing: {', '.join(missing)}.",
            f"Add clear headings such as {', '.join(missing)} so ATS can find each section.",
            credit=1 - len(missing) / len(SECTIONS),
        )
    return _pass("section_headings", title, "Found Experience, Education, Skills, Projects and Summary headings.")


def contact_info(pages: list[_Page], parsed: ParsedResume) -> AtsCheck:
    title = "Email and phone present"
    # Read every word, including page headers the parser drops, because contact details often sit there.
    raw = "\n".join(" ".join(w["text"] for w in row) for page in pages for row in page.rows)
    has_email = bool(_EMAIL.search(raw))
    has_phone = any(10 <= sum(ch.isdigit() for ch in m.group()) <= 13 for m in _PHONE_CANDIDATE.finditer(raw))
    if has_email and has_phone:
        return _pass("contact_info", title, "Found an email address and a phone number.")
    missing = [name for name, found in (("email address", has_email), ("phone number", has_phone)) if not found]
    return AtsCheck(
        "contact_info", title, "fail" if len(missing) == 2 else "warn",
        f"No {' or '.join(missing)} found as text.",
        f"Add your {' and '.join(missing)} as plain text near the top of the resume.",
        credit=1 - len(missing) / 2,
    )


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
            text = "".join(w["text"] for w in row)
            body = text[1:] if text[:1] and _is_symbol(text[0]) else text  # a leading glyph is the bullets check's job
            total += len(text)
            symbols += sum(_is_symbol(ch) for ch in body) + body.count("(cid:")
    ratio = symbols / total if total else 0.0
    if ratio > MAX_SYMBOL_RATIO:
        return AtsCheck(
            "special_chars", title, "warn",
            f"Found {symbols} decorative symbols or icons (such as stars or phone icons).",
            "Remove decorative symbols, icons and star ratings; use plain words instead.",
        )
    return _pass("special_chars", title, "No unusual symbols found.")


def _is_symbol(ch: str) -> bool:
    return unicodedata.category(ch) in ("So", "Co")  # other symbols (★ ✉ ☎) and private-use icon glyphs


def bullets(pages: list[_Page], parsed: ParsedResume) -> AtsCheck:
    title = "Plain bullets"
    odd: set[str] = set()
    for page in pages:
        for row in page.rows:
            first = row[0]
            glyph = first["text"]
            if glyph.startswith("(cid:"):
                odd.add("unreadable glyph")
            elif ICON_FONTS.search(first["fontname"]) and len(glyph) <= 2:
                odd.add(glyph[0])
            elif len(glyph) == 1 and glyph not in STANDARD_BULLETS and _is_symbol(glyph):
                odd.add(glyph)
    if odd:
        return AtsCheck(
            "bullets", title, "warn",
            f"Uses non-standard bullet symbols ({', '.join(sorted(odd))}) that ATS may not read.",
            "Use simple round bullets (•) or hyphens instead of symbols or icon fonts.",
        )
    return _pass("bullets", title, "Bullets are plain.")


CHECKS: list[Callable[[list[_Page], ParsedResume], AtsCheck]] = [
    text_extractable, multi_column, tables, images, section_headings,
    contact_info, length, fonts, special_chars, bullets,
]  # fmt: skip
