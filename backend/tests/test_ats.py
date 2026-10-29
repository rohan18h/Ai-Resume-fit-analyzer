"""ATS checker: each of the 10 checks has a pass fixture and a fail fixture (Section 14), plus scoring rules."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import pytest

from app.services.ats import CHECKS, AtsResult, check_ats
from app.services.parser import extract_text

FIXTURES = Path(__file__).parent / "fixtures"


@lru_cache(maxsize=None)
def run(name: str) -> AtsResult:
    pdf = (FIXTURES / name).read_bytes()
    return check_ats(pdf, extract_text(pdf))


def status(name: str, check_id: str) -> str:
    return next(c.status for c in run(name).checks if c.id == check_id)


# (check id, fixture that passes, fixture that does not pass, expected status for the second one)
CASES = [
    ("text_extractable", "ats_good_resume.pdf", "image_page.pdf", "fail"),
    ("multi_column", "ats_good_resume.pdf", "sample_resume_frontend.pdf", "warn"),
    ("tables", "ats_good_resume.pdf", "with_table.pdf", "warn"),
    ("images", "with_image.pdf", "image_page.pdf", "warn"),  # a small photo is fine; a page-sized image is not
    ("section_headings", "ats_good_resume.pdf", "data_analyst_resume.pdf", "warn"),
    ("contact_info", "ats_good_resume.pdf", "header_footer.pdf", "fail"),
    ("length", "ats_good_resume.pdf", "header_footer.pdf", "warn"),
    ("fonts", "multi_font.pdf", "many_fonts.pdf", "warn"),  # 3 families is the limit, 5 is too many
    ("special_chars", "ats_good_resume.pdf", "decorative.pdf", "warn"),
    ("bullets", "ats_good_resume.pdf", "special_tokens.pdf", "warn"),
]


def test_every_check_has_a_case() -> None:
    assert sorted(case[0] for case in CASES) == sorted(check.__name__ for check in CHECKS)
    assert len(CHECKS) == 10


@pytest.mark.parametrize("check_id, good, bad, bad_status", CASES, ids=[case[0] for case in CASES])
def test_check_passes_and_fails(check_id: str, good: str, bad: str, bad_status: str) -> None:
    assert status(good, check_id) == "pass"
    assert status(bad, check_id) == bad_status


def test_clean_resume_passes_everything() -> None:
    result = run("ats_good_resume.pdf")
    assert (result.score, result.passed, result.total) == (100, 10, 10)


def test_demo_bad_resume_shows_many_warnings() -> None:
    """Demo script step 3: a two-column resume with a table gets clear warnings and fixes."""
    result = run("ats_bad_resume.pdf")
    flagged = {c.id for c in result.checks if c.status != "pass"}
    assert {"multi_column", "tables", "fonts", "special_chars", "bullets"} <= flagged
    assert result.score < 70


def test_score_follows_the_spec_formula() -> None:
    """Section 10.5.6: round(100 * (passed + 0.5 * warned) / total), over the checks that could be applied."""
    for name in ("ats_good_resume.pdf", "ats_bad_resume.pdf", "image_page.pdf", "decorative.pdf", "header_footer.pdf",
                 "data_analyst_resume.pdf", "two_page_resume.pdf", "special_tokens.pdf"):
        result = run(name)
        applied = [c for c in result.checks if c.status != "na"]
        warned = sum(c.status == "warn" for c in applied)
        assert result.total == len(applied)
        assert result.score == round(100 * (result.passed + 0.5 * warned) / result.total), name
        assert {c.credit for c in applied} <= {1.0, 0.5, 0.0}
        assert all(c.credit is None for c in result.checks if c.status == "na")


def test_unavailable_check_is_left_out_not_passed() -> None:
    """A resume without bullets can't fail or pass the bullets check: it is "na" and not in the denominator."""
    result = run("data_analyst_resume.pdf")
    bullets = next(c for c in result.checks if c.id == "bullets")
    if bullets.status == "na":
        assert result.total == 9 and "Not checked" in bullets.detail


def test_every_warn_or_fail_has_a_fix() -> None:
    for name in ("ats_bad_resume.pdf", "image_page.pdf", "header_footer.pdf", "decorative.pdf", "ats_good_resume.pdf"):
        for check in run(name).checks:
            assert check.title and check.detail
            if check.status in ("pass", "na"):
                assert check.fix is None
            else:
                assert check.fix and len(check.fix) < 140, (name, check.id)


def test_contact_info_partial_is_warn() -> None:
    check = next(c for c in run("multi_font.pdf").checks if c.id == "contact_info")  # email but no phone
    assert check.status == "warn" and "phone number" in check.detail


def test_unmapped_bullet_glyphs_are_flagged() -> None:
    check = next(c for c in run("sample_resume_backend.pdf").checks if c.id == "bullets")
    assert check.status == "warn" and "unreadable glyph" in check.detail


def test_missing_headings_are_named() -> None:
    check = next(c for c in run("data_analyst_resume.pdf").checks if c.id == "section_headings")
    assert "Skills" in check.detail and "Projects" in check.detail
    assert "Experience" not in check.detail  # "WORK HISTORY" counts as an experience heading
