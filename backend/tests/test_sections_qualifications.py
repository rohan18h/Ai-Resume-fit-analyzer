"""sections.py (resume / JD headings) and qualifications.py (degree, years, certifications)."""

from __future__ import annotations

from datetime import date

from app.services.qualifications import check_requirements, experience_months, find_requirements, jd_degree_level
from app.services.sections import is_list_line, jd_lines, resume_sections

TODAY = date(2026, 10, 29)

RESUME = """Summary
Backend developer.
Work Experience
Software Engineer, Example Fintech, Jun 2022 - Present
Built REST APIs.
Intern, Example Labs, 01/2021 - 06/2021
Academic Projects
Invoice Service: Django and Redis.
Technical Skills:
Python, Django, Redis, Docker
Education
B.E. in Computer Engineering, 2018 - 2022"""


def test_resume_sections() -> None:
    lines = {line.text: line.section for line in resume_sections(RESUME)}
    assert lines["Backend developer."] == "summary"
    assert lines["Built REST APIs."] == "experience"
    assert lines["Invoice Service: Django and Redis."] == "projects"
    assert lines["Python, Django, Redis, Docker"] == "skills"
    assert lines["B.E. in Computer Engineering, 2018 - 2022"] == "education"
    assert "Work Experience" not in lines  # headings are not content


def test_long_line_is_not_a_heading() -> None:
    lines = resume_sections("Projects\nExperience building scalable APIs for many users")
    assert [(line.text, line.section) for line in lines] == [
        ("Experience building scalable APIs for many users", "projects")
    ]
    assert is_list_line("Python, Django, Redis, Docker, Git")
    assert not is_list_line("Built a billing API in Python, tested it with pytest, and deployed it with Docker.")


def test_jd_sections_and_importance() -> None:
    jd = jd_lines(
        "About us\nWe build billing software.\nResponsibilities:\n- Build APIs in Python.\nRequirements:\n"
        "- 2+ years with Python.\nNice to have:\n- Redis.\nMust have:\n- Docker.\nOther: we prefer Git (preferred)."
    )
    by_text = {line.text: (line.section, line.importance) for line in jd}
    assert by_text["We build billing software."] == ("about", "neutral")
    assert by_text["- Build APIs in Python."] == ("responsibilities", "neutral")
    assert by_text["- 2+ years with Python."] == ("requirements", "required")
    assert by_text["- Redis."] == ("preferred", "preferred")
    assert by_text["- Docker."][1] == "required"  # "Must have:" passes its cue down
    assert by_text["Other: we prefer Git (preferred)."][1] == "preferred"


def test_degree_levels() -> None:
    assert jd_degree_level("Bachelor's or Master's degree in Computer Science") == 2
    assert jd_degree_level("B.Tech / BE in any branch") == 2
    assert jd_degree_level("A degree in a related field") == 2
    assert jd_degree_level("MCA or M.Sc. in IT") == 3
    assert jd_degree_level("PhD in machine learning") == 4
    assert jd_degree_level("Strong communication skills") == 0


def test_experience_months_merges_overlaps() -> None:
    lines = resume_sections(
        "Experience\nEngineer, A, Jan 2020 - Dec 2021\nFreelance, 06/2021 - 06/2022\nAnalyst, B, 2023 - Present"
    )
    # Jan 2020 - Jun 2022 merged (29 months) + Jan 2023 - Oct 2026 (45 months)
    assert experience_months(lines, TODAY) == 29 + 45
    assert experience_months(resume_sections("Education\nB.E., 2018 - 2022"), TODAY) is None  # not an Experience date


def check(jd: str, resume: str = RESUME) -> dict[str, tuple[str, str]]:
    results = check_requirements(find_requirements(jd_lines(jd)), resume_sections(resume), TODAY)
    return {r.requirement.kind: (r.status, r.requirement.importance) for r in results}


def test_qualifications_met() -> None:
    assert check("Requirements:\n- Bachelor's degree in Computer Science.\n- 3+ years of experience.") == {
        "degree": ("met", "required"), "experience_years": ("met", "required"),
    }  # fmt: skip


def test_qualifications_not_met_or_unverified() -> None:
    assert check("Requirements:\n- Master's degree required.\n- 6+ years of experience.") == {
        "degree": ("not_met", "required"), "experience_years": ("not_met", "required"),
    }  # fmt: skip
    no_dates = "Experience\nEngineer at Example\nEducation\nSchool"
    assert check("Requirements:\n- A degree in CS.\n- 2+ years of experience.", no_dates) == {
        "degree": ("unverified", "required"), "experience_years": ("unverified", "required"),
    }  # fmt: skip


def test_degree_in_progress() -> None:
    student = "Education\nB.Tech in Computer Engineering, 2023 - 2027 (expected)"
    assert check("Requirements:\n- Bachelor's degree in CS.", student) == {"degree": ("in_progress", "required")}


def test_preferred_qualification() -> None:
    assert check("Nice to have:\n- Master's degree.") == {"degree": ("not_met", "preferred")}


def test_certifications() -> None:
    jd = "Requirements:\n- AWS Certified Solutions Architect.\n- Valid state nursing license is required."
    results = check_requirements(find_requirements(jd_lines(jd)), resume_sections(RESUME), TODAY)
    assert [(r.requirement.keywords, r.status) for r in results] == [
        (("aws", "solutions", "architect"), "unverified"), (("nursing",), "unverified"),
    ]  # fmt: skip
    holder = "Certifications\nAWS Certified Solutions Architect - Associate (2024)"
    assert check("Requirements:\n- AWS Certified Solutions Architect.", holder) == {"certification": ("met", "required")}
