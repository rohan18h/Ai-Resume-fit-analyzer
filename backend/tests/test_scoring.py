"""Weighted fit score (services/scoring.py): scenarios A-H and score-quality checks, run on the real implementation.

The resumes are fictional. Texts go through the same cleaning as the API (clean_text_light). Scenario H builds real
PDFs and runs the whole pipeline.
"""

from __future__ import annotations

import io
from datetime import date

import pytest
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from app.services import matcher_embed, pipeline
from app.services.parser import clean_text_light
from app.services.scoring import WeightedResult, weighted_score
from app.services.skills import SkillExtractor

TODAY = date(2026, 10, 29)

JD = """Backend Python Developer

About us: Example Payments builds billing software for small businesses across India.

Responsibilities:
- Design, build and maintain REST APIs in Python for our billing platform.
- Model data in PostgreSQL and keep queries fast as traffic grows.
- Write automated tests with pytest and review pull requests from teammates.
- Package services with Docker and deploy them to AWS.

Requirements:
- Bachelor's degree in Computer Science or a related field.
- 2+ years of professional experience with Python.
- Experience with FastAPI or Django.
- Strong SQL skills and hands-on experience with PostgreSQL.
- Experience with Docker and Git.

Nice to have:
- Redis or another caching layer.
- Kubernetes experience."""

STRONG = """Summary
Backend developer with four years of experience building Python APIs for payments.
Experience
Software Engineer, Example Fintech, Jun 2022 - Present
- Designed and maintained REST APIs in Python with FastAPI for a billing platform used by 5,000 merchants.
- Modelled PostgreSQL schemas and tuned slow SQL queries, cutting response times by 40%.
- Wrote pytest suites for every endpoint and reviewed pull requests from teammates.
- Packaged services with Docker and deployed them to AWS using Git-based CI.
Projects
Invoice Service: built a Django invoicing service with Redis caching.
Skills
Python, FastAPI, Django, PostgreSQL, SQL, Docker, Git, AWS, Redis, pytest
Education
B.E. in Computer Engineering, Pune University, 2018 - 2022"""

MODERATE = """Summary
Developer familiar with Python, FastAPI, Docker and SQL.
Experience
IT Support Associate, Example Corp, Jan 2024 - Present
- Resolved hardware and network tickets for 200 employees.
- Wrote onboarding documentation for new staff.
Projects
To-do app: built a small to-do list web app with FastAPI.
Skills
Python, FastAPI, Docker, Git, SQL
Education
B.Sc. in Information Technology, Mumbai University, 2020 - 2023"""

WEAK = """Summary
Mechanical engineer focused on product design.
Experience
Design Engineer, Example Motors, Jul 2021 - Present
- Designed gearbox housings in SolidWorks and ran FEA simulations.
- Worked with suppliers to reduce part costs by 12%.
Skills
SolidWorks, AutoCAD, MATLAB, Excel, Git
Education
B.E. in Mechanical Engineering, 2017 - 2021"""


@pytest.fixture(scope="module", autouse=True)
def model() -> None:
    if not matcher_embed.try_load_model():
        pytest.skip("embedding model not available")


def score(resume: str, extractor: SkillExtractor, jd: str = JD, embeddings: bool = True) -> WeightedResult:
    resume_light, jd_light = clean_text_light(resume), clean_text_light(jd)
    return weighted_score(
        resume_light, jd_light, extractor.jd_skills(jd_light), extractor.hits(resume_light),
        extractor=extractor, use_embeddings=embeddings, today=TODAY,
    )  # fmt: skip


def category(result: WeightedResult, id_: str) -> float:
    return next(c.points for c in result.categories if c.id == id_)


def status(result: WeightedResult, name: str) -> str:
    return next(s.status for s in result.skills if s.name == name)


def assert_consistent(result: WeightedResult) -> None:
    """Score in range, never above a category's maximum, and the total equals the shown category points.

    The maximums add up to 100, or to 0 when the JD gives nothing to match (no skills, duties or qualifications).
    """
    assert 0 <= result.score <= 100
    assert all(0 <= c.points <= c.max_points for c in result.categories)
    assert {c.id for c in result.categories} == {"skills", "evidence", "responsibilities", "qualifications"}
    expected_max = 100 if any(c.applicable for c in result.categories) else 0
    assert sum(c.max_points for c in result.categories) == pytest.approx(expected_max)
    assert result.score == round(sum(c.points for c in result.categories), 1)


# ---------------------------------------------------------------------------
# Scenarios A-H
# ---------------------------------------------------------------------------


def test_a_strong_match_is_high_but_not_perfect(extractor: SkillExtractor) -> None:
    result = score(STRONG, extractor)
    assert_consistent(result)
    assert 75 <= result.score < 100
    assert result.missing_required == [] and "Kubernetes" in result.missing_preferred
    assert {q.status for q in result.qualifications} == {"met"}
    assert status(result, "postgresql") == "demonstrated"


def test_b_moderate_match_is_meaningfully_lower(extractor: SkillExtractor) -> None:
    strong, moderate = score(STRONG, extractor), score(MODERATE, extractor)
    assert_consistent(moderate)
    assert 30 <= moderate.score <= 65 and strong.score - moderate.score >= 20
    assert "PostgreSQL" in moderate.missing_required
    assert {"Docker", "Git"} <= set(moderate.listed_not_demonstrated)
    python = next(s for s in moderate.skills if s.name == "python")  # only shown through the FastAPI to-do app
    assert python.status == "demonstrated" and python.via == "FastAPI" and python.evidence_credit < 1
    years = next(q for q in moderate.qualifications if q.kind == "experience_years")
    assert years.status == "not_met" and "Python" in years.detail  # 2.8 dated years, but not with Python


def test_c_weak_match_is_low(extractor: SkillExtractor) -> None:
    moderate, weak = score(MODERATE, extractor), score(WEAK, extractor)
    assert_consistent(weak)
    assert weak.score < 30 and weak.score < moderate.score - 10
    assert category(weak, "evidence") == 0
    assert len(weak.missing_required) >= 6


def test_d_keyword_stuffing_does_not_raise_the_score(extractor: SkillExtractor) -> None:
    baseline = score(MODERATE, extractor)
    repeated = MODERATE.replace("Python, FastAPI, Docker, Git, SQL", ", ".join(["Python, FastAPI, Docker, Git, SQL"] * 20))
    assert score(repeated, extractor).score == baseline.score
    assert any("keyword stuffing" in tip for tip in score(repeated, extractor).recommendations)
    assert not any("keyword stuffing" in tip for tip in baseline.recommendations)

    # Stuffing every JD keyword into the summary only earns "listed" credit: no evidence, no duties covered.
    keywords = "Python Django FastAPI PostgreSQL SQL Docker Git REST API AWS Redis Kubernetes pytest " * 5
    stuffed = score(MODERATE.replace("Developer familiar with", keywords + "Developer familiar with"), extractor)
    assert category(stuffed, "evidence") == category(baseline, "evidence")
    assert category(stuffed, "responsibilities") == category(baseline, "responsibilities")
    assert stuffed.score < score(STRONG, extractor).score - 20
    assert {"PostgreSQL", "Django"} <= set(stuffed.listed_not_demonstrated)


def test_e_irrelevant_skills_do_not_raise_the_score(extractor: SkillExtractor) -> None:
    baseline = score(MODERATE, extractor)
    extra_list = MODERATE.replace(
        "Python, FastAPI, Docker, Git, SQL",
        "Python, FastAPI, Docker, Git, SQL, Swift, Kotlin, Flutter, TensorFlow, Tableau, MATLAB, Photoshop, Unity",
    )
    assert score(extra_list, extractor).score == baseline.score
    extra_project = MODERATE.replace(
        "Skills\n", "Mobile game: built an iOS puzzle game in Swift with SpriteKit animations.\nSkills\n"
    )
    assert score(extra_project, extractor).score <= baseline.score


def test_f_synonyms_get_credit_once(extractor: SkillExtractor) -> None:
    strong = score(STRONG, extractor)
    synonyms = STRONG.replace("PostgreSQL", "Postgres").replace("Python with FastAPI", "Python3 with FastAPI")
    synonyms = synonyms.replace("Redis, pytest", "Redis, pytest, k8s")
    result = score(synonyms, extractor)
    assert status(result, "postgresql") == "demonstrated"
    assert status(result, "kubernetes") == "listed"  # credited through the k8s alias, but only listed
    assert result.score >= strong.score - 3
    both = score(synonyms.replace("Postgres, SQL", "Postgres, PostgreSQL, postgres, SQL"), extractor)
    assert both.score == result.score  # the same skill under several names counts once
    assert [s.name for s in both.skills].count("postgresql") == 1


def test_g_missing_mandatory_qualification(extractor: SkillExtractor) -> None:
    strong = score(STRONG, extractor)
    no_degree = score(STRONG.split("Education")[0], extractor)
    degree = next(q for q in no_degree.qualifications if q.kind == "degree")
    assert degree.status == "unverified" and degree.importance == "required"
    assert category(no_degree, "qualifications") < category(strong, "qualifications")
    assert no_degree.score < strong.score
    assert any("Education" in tip for tip in no_degree.recommendations)

    junior = score(STRONG.replace("Jun 2022 - Present", "Jun 2026 - Present"), extractor)
    years = next(q for q in junior.qualifications if q.kind == "experience_years")
    assert years.status == "not_met" and junior.score < strong.score


def _pdf(resume: str, font: str = "Helvetica", sidebar: tuple[str, ...] = ()) -> bytes:
    """One-page PDF of the resume text; headings in `sidebar` (and their lines) go in a right-hand column."""
    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    pdf.setFont(font, 9)
    main, side, current = [], [], None
    for line in ["Meghana Rao", "meghana@example.com | +91 98765 43210", *resume.splitlines()]:
        if line in ("Summary", "Experience", "Projects", "Skills", "Education"):
            current = line
        (side if current in sidebar else main).append(line)
    for column, x, width in ((main, 40, 60 if side else 110), (side, 380, 38)):  # characters per line; no overlap
        y = 800
        for line in column:
            words, row = line.split(), ""
            for word in words:  # wrap
                if len(row) + len(word) + 1 > width:
                    pdf.drawString(x, y, row)
                    y, row = y - 13, ""
                row = f"{row} {word}".strip()
            pdf.drawString(x, y, row)
            y -= 13
    pdf.save()
    return buffer.getvalue()


def test_h_layout_and_font_give_consistent_scores() -> None:
    """DOCX isn't supported (PDF only), so H checks that the same content in different PDF layouts and fonts
    scores consistently through the full pipeline (parser + ATS + weighted score)."""
    plain = pipeline.analyze(_pdf(STRONG), JD).fit.score
    serif = pipeline.analyze(_pdf(STRONG, font="Times-Roman"), JD).fit.score
    two_column = pipeline.analyze(_pdf(STRONG, sidebar=("Skills", "Education")), JD)
    assert abs(plain - serif) <= 2
    assert abs(plain - two_column.fit.score) <= 5
    assert two_column.breakdown.missing_required == []


# ---------------------------------------------------------------------------
# Score quality
# ---------------------------------------------------------------------------


def test_order_strong_moderate_weak_without_the_model(extractor: SkillExtractor) -> None:
    results = [score(r, extractor, embeddings=False) for r in (STRONG, MODERATE, WEAK)]
    assert results[0].score > results[1].score > results[2].score
    assert all(r.similarity_method == "word overlap" for r in results)


def test_genuine_evidence_improves_the_right_categories(extractor: SkillExtractor) -> None:
    baseline = score(MODERATE, extractor)
    improved = score(MODERATE.replace(
        "To-do app:", "Billing API: modelled PostgreSQL tables and wrote REST APIs in Python with FastAPI.\nTo-do app:"
    ), extractor)  # fmt: skip
    assert category(improved, "skills") > category(baseline, "skills")
    assert category(improved, "evidence") > category(baseline, "evidence")
    assert category(improved, "responsibilities") >= category(baseline, "responsibilities")
    assert improved.score > baseline.score


def test_related_skill_gets_partial_credit_only(extractor: SkillExtractor) -> None:
    mysql = score(STRONG.replace("PostgreSQL", "MySQL"), extractor)
    postgres = score(STRONG, extractor)
    skill = next(s for s in mysql.skills if s.name == "postgresql")
    assert skill.status == "related" and skill.via == "MySQL" and 0 < skill.skills_credit < 1
    assert "PostgreSQL" in mysql.partial_required and mysql.score < postgres.score


def test_deterministic(extractor: SkillExtractor) -> None:
    assert score(STRONG, extractor) == score(STRONG, extractor)


@pytest.mark.parametrize("resume, jd", [
    ("", JD),
    ("Experience\n", JD),
    (STRONG, "Looking for someone great to join our friendly team."),
    (STRONG, "We are hiring. Apply now."),
    ("@@@ ### !!!\n\n\t", "Python, Docker, Git."),
])  # fmt: skip
def test_degenerate_inputs_stay_in_range(extractor: SkillExtractor, resume: str, jd: str) -> None:
    result = score(resume, extractor, jd=jd)
    assert_consistent(result)


def test_empty_resume_scores_zero(extractor: SkillExtractor) -> None:
    result = score("", extractor)
    assert result.score == 0 and len(result.missing_required) >= 6


def test_unrelated_job_scores_low(extractor: SkillExtractor) -> None:
    nurse = (
        "Responsibilities:\n- Provide direct patient care to children in a 30-bed ward.\n"
        "- Administer medications and monitor vital signs.\nRequirements:\n"
        "- Valid state nursing license is required.\n- 2+ years of clinical experience in a hospital."
    )
    result = score(STRONG, extractor, jd=nurse)
    assert_consistent(result)
    assert not next(c for c in result.categories if c.id == "skills").applicable
    assert result.score < 10  # a well-formatted backend resume earns nothing for a nursing job
