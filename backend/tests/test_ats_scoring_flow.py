"""The ATS score end to end: which function computes it, what it reads, and what does (and doesn't) change it.

The ATS score (ats.check_ats) checks only the resume PDF: formatting, parsing and structure. It must move when that
evidence changes and stay the same when only the job description or unrelated wording changes. The fit score is a
separate metric: a formatting change that moves the ATS score must not move the fit score.
"""

from __future__ import annotations

import io
import logging

import pytest
from fastapi.testclient import TestClient
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from app.main import app
from app.services import matcher_embed, pipeline
from app.services.ats import check_ats
from app.services.parser import extract_text

BODY = {
    "Summary": ["Backend developer with three years of experience building Python APIs for payments."],
    "Experience": [
        "Software Engineer, Example Fintech, Jun 2022 - Present",
        "- Designed REST APIs in Python with FastAPI for a billing platform used by 5,000 merchants.",
        "- Modelled PostgreSQL schemas and tuned slow SQL queries, cutting response times by 40%.",
    ],
    "Projects": ["Invoice Service: built a Django invoicing service with Redis caching."],
    "Skills": ["Python, FastAPI, Django, PostgreSQL, Docker, Git"],
    "Education": ["B.E. in Computer Engineering, Pune University, 2018 - 2022"],
}
JD = (
    "Backend Python Developer\nResponsibilities:\n- Build REST APIs in Python with FastAPI.\n"
    "Requirements:\n- Experience with PostgreSQL and Docker.\n- A degree in Computer Science."
)
OTHER_JD = (
    "Data Analyst\nResponsibilities:\n- Build dashboards in Power BI and Tableau.\n"
    "Requirements:\n- Strong Excel and SQL skills.\n- Statistics background."
)


def make_pdf(headings: tuple[str, ...] = tuple(BODY), contact: tuple[str, ...] = ("email", "phone"),
             replace: tuple[str, str] = ("", "")) -> bytes:
    """A one-column resume with the given section headings shown (content is kept either way)."""
    lines = ["Meghana Rao"]
    lines += ["meghana@example.com"] if "email" in contact else []
    lines += ["+91 98765 43210"] if "phone" in contact else []
    for heading, body in BODY.items():
        lines += ([heading] if heading in headings else []) + [line.replace(*replace) if replace[0] else line
                                                                for line in body]
    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    pdf.setFont("Helvetica", 10)
    for index, line in enumerate(lines):
        pdf.drawString(40, 800 - 16 * index, line)
    pdf.save()
    return buffer.getvalue()


def ats_score(pdf: bytes) -> int:
    return check_ats(pdf, extract_text(pdf)).score


# ---------------------------------------------------------------------------
# What changes the ATS score
# ---------------------------------------------------------------------------


def test_missing_headings_lower_the_score() -> None:
    """Spec formula (pass 1, warn 0.5, fail 0): all 5 headings pass, 1-2 missing warn, 3 or more missing fail.
    Before, 1 missing heading and 5 missing headings both scored 95."""
    names = tuple(BODY)
    scores = [ats_score(make_pdf(headings=names[: len(names) - missing])) for missing in range(len(names) + 1)]
    assert scores == [100, 95, 95, 90, 90, 90]


def test_contact_details_change_the_score() -> None:
    both, email_only, none = (ats_score(make_pdf(contact=c)) for c in (("email", "phone"), ("email",), ()))
    assert both > email_only > none


def test_a_short_line_with_a_section_word_is_not_a_heading() -> None:
    """"Education loan advisor" used to count as an Education heading because it has 4 words or fewer."""
    pdf = make_pdf(headings=("Summary", "Experience", "Projects", "Skills"))
    pdf_with_line = make_pdf(headings=("Summary", "Experience", "Projects", "Skills"),
                             replace=("B.E. in Computer Engineering, Pune University, 2018 - 2022",
                                      "Education loan advisor"))
    check = next(c for c in check_ats(pdf_with_line, extract_text(pdf_with_line)).checks if c.id == "section_headings")
    assert check.status == "warn" and "Education" in check.detail
    assert ats_score(pdf_with_line) == ats_score(pdf)


def test_inline_label_counts_as_a_heading() -> None:
    pdf = make_pdf(headings=("Summary", "Experience", "Projects", "Education"),
                   replace=("Python, FastAPI", "Skills: Python, FastAPI"))
    assert ats_score(pdf) == 100


# ---------------------------------------------------------------------------
# What must not change it
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def model() -> None:
    if not matcher_embed.try_load_model():
        pytest.skip("embedding model not available")


def test_job_description_does_not_change_the_ats_score(model: None) -> None:
    pdf = make_pdf(headings=("Experience", "Skills"))
    first, second = pipeline.analyze(pdf, JD), pipeline.analyze(pdf, OTHER_JD)
    assert first.ats == second.ats  # every check, credit and the score
    assert first.fit.score != second.fit.score  # while the job-specific fit score does change


def test_unrelated_wording_does_not_change_the_ats_score() -> None:
    reworded = make_pdf(replace=("billing platform", "invoicing product"))
    assert ats_score(reworded) == ats_score(make_pdf())


# ---------------------------------------------------------------------------
# The fit score uses the same ATS result, and the API returns it
# ---------------------------------------------------------------------------


def test_formatting_change_moves_ats_but_not_the_fit_score(model: None) -> None:
    """Dropping the phone number is a formatting/contact problem: the ATS score drops, the job match does not."""
    with_phone, without = pipeline.analyze(make_pdf(), JD), pipeline.analyze(make_pdf(contact=("email",)), JD)
    assert without.ats.score < with_phone.ats.score
    assert without.fit.score == with_phone.fit.score
    assert {c.id for c in with_phone.breakdown.categories} == {"skills", "evidence", "responsibilities",
                                                                 "qualifications"}


def test_api_returns_the_new_ats_calculation(model: None, caplog: pytest.LogCaptureFixture) -> None:
    pdf = make_pdf(headings=("Experience", "Skills"))
    expected = check_ats(pdf, extract_text(pdf))
    with caplog.at_level(logging.DEBUG, logger="resume_fit"), TestClient(app) as client:
        response = client.post(
            "/api/analyze", files={"resume": ("r.pdf", pdf, "application/pdf")}, data={"job_description": JD}
        )
    ats = response.json()["ats"]
    assert ats["score"] == expected.score < 100
    headings = next(c for c in ats["checks"] if c["id"] == "section_headings")
    assert headings["status"] == "fail" and headings["credit"] == 0 and "Found 2 of 5" in headings["detail"]
    # Diagnostics: check_ats ran on this PDF (1 page) with these credits, and the request log shows both scores.
    messages = [r.getMessage() for r in caplog.records]
    assert any(m.startswith("check_ats pages=1 ") and f"score={expected.score}" in m for m in messages)
    assert any(m.startswith("analyze request_id=") and f"ats={expected.score}" in m for m in messages)
    assert not any("Meghana" in m or "FastAPI" in m for m in messages)  # never resume content
