"""Skills extractor: aliases, multi-word skills, ambiguous names, counts and JD importance."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.services.parser import extract_text
from app.services.skills import SkillExtractor, extract_skills, rank_jd_skills

FIXTURES = Path(__file__).parent / "fixtures"


def names(text: str, extractor: SkillExtractor) -> set[str]:
    return {hit.name for hit in extract_skills(text, extractor)}


def importance(jd: str, extractor: SkillExtractor) -> dict[str, str]:
    return {skill.name: skill.importance for skill in rank_jd_skills(jd, extractor)}


# --- aliases and multi-word skills -----------------------------------------


def test_aliases_map_to_canonical_names(extractor: SkillExtractor) -> None:
    assert names("JS, ReactJS, Postgres and k8s", extractor) == {"javascript", "react", "postgresql", "kubernetes"}
    assert names("Golang, sklearn, NodeJS", extractor) == {"go", "scikit-learn", "node.js"}


def test_multi_word_and_symbol_skills(extractor: SkillExtractor) -> None:
    text = "Machine learning with scikit-learn; REST APIs in Spring Boot; CI/CD on GitHub Actions; Node.js; C++; C#"
    assert names(text, extractor) == {
        "machine learning", "scikit-learn", "rest api", "spring boot", "ci/cd", "github actions", "node.js", "c++", "c#",
    }  # fmt: skip


def test_longest_match_wins(extractor: SkillExtractor) -> None:
    assert names("Expert in C++ and C#", extractor) == {"c++", "c#"}  # no bare "c"
    assert names("Tailwind CSS", extractor) == {"tailwind css"}  # no separate "css"
    assert names("C/C++ developer", extractor) == {"c", "c++"}


def test_case_insensitive_match_and_counts(extractor: SkillExtractor) -> None:
    hits = extract_skills("Python developer. I love python. PYTHON scripts. Docker too.", extractor)
    assert [(h.name, h.count) for h in hits] == [("python", 3), ("docker", 1)]
    assert hits[0].display_name == "Python" and hits[0].category == "Programming Languages"


# --- ambiguous names ---------------------------------------------------------


@pytest.mark.parametrize(
    "text, expected",
    [
        ("Languages: C, R, Go", {"c", "r", "go"}),
        ("Experience with Python, R and SQL", {"python", "r", "sql"}),
        ("Skills\nC\nJava", {"c", "java"}),
        ("I got a grade C in history.", set()),
        ("Go to the office every Monday.", set()),
        ("Our R&D team is growing.", set()),
        ("C-level executives and a Go-to-market plan", set()),
        ("python and go", {"python"}),  # lowercase "go" is not accepted
    ],
)
def test_ambiguous_c_r_go(text: str, expected: set[str], extractor: SkillExtractor) -> None:
    assert names(text, extractor) == expected


@pytest.mark.parametrize(
    "text, expected",
    [
        ("We react quickly to incidents.", set()),
        ("react, node.js, mongodb", {"react", "node.js", "mongodb"}),
        ("Built dashboards in React for a client.", {"react"}),
        ("Excel at teamwork.", set()),
        ("Advanced Excel and Power BI", {"excel", "power bi"}),
        ("Meet the rest of the team.", set()),
        ("Spring 2024 internship.", set()),
    ],
)
def test_everyday_word_skills_need_context(text: str, expected: set[str], extractor: SkillExtractor) -> None:
    assert names(text, extractor) == expected


def test_identifiers_are_not_scanned(extractor: SkillExtractor) -> None:
    assert names("Contact: go.python@example.com, https://react.example.com/docker", extractor) == set()


def test_unknown_skills_are_not_detected(extractor: SkillExtractor) -> None:
    # Documented limitation: only skills in the database are found.
    assert names("Svelte, Elixir and Zig", extractor) == set()


def test_empty_text(extractor: SkillExtractor) -> None:
    assert extract_skills("", extractor) == []
    assert rank_jd_skills("   \n ", extractor) == []


def test_skills_from_sample_resume_pdf(extractor: SkillExtractor) -> None:
    text = extract_text((FIXTURES / "sample_resume_backend.pdf").read_bytes()).text
    found = names(text, extractor)
    assert {"python", "fastapi", "flask", "django", "postgresql", "docker", "redis", "pytest", "jwt", "linux"} <= found
    assert "go" not in found and "c" not in found


# --- JD importance -----------------------------------------------------------


def test_importance_from_sentence_cues(extractor: SkillExtractor) -> None:
    jd = (
        "Python is required. Docker experience is a must. Kafka knowledge is mandatory for this role. "
        "AWS is preferred. Kubernetes is a plus. GraphQL would be a bonus; Redis is good to have. "
        "You will work with Git."
    )
    assert importance(jd, extractor) == {
        "python": "high", "docker": "high",
        "aws": "low", "kubernetes": "low", "graphql": "low", "redis": "low",
        "git": "medium",
    }  # fmt: skip


def test_importance_from_section_headings(extractor: SkillExtractor) -> None:
    jd = "Requirements:\n- Python and FastAPI\n- PostgreSQL\nNice to have:\n- Docker, AWS\nResponsibilities:\n- Use Git daily"
    assert importance(jd, extractor) == {
        "python": "high", "fastapi": "high", "postgresql": "high", "docker": "low", "aws": "low", "git": "medium",
    }  # fmt: skip


def test_three_mentions_make_a_skill_high(extractor: SkillExtractor) -> None:
    jd = "We use SQL daily. Write SQL reports. Optimise SQL queries. Tableau is nice to have."
    ranked = rank_jd_skills(jd, extractor)
    assert [(s.name, s.mentions, s.importance) for s in ranked] == [("sql", 3, "high"), ("tableau", 1, "low")]


def test_high_wins_over_low(extractor: SkillExtractor) -> None:
    jd = "Docker is required. Docker Compose is a plus."
    assert importance(jd, extractor) == {"docker": "high"}


def test_ranking_order(extractor: SkillExtractor) -> None:
    jd = "Kubernetes is a plus. Git and Linux are used. Python is required. Linux servers. Python scripts."
    ranked = rank_jd_skills(jd, extractor)
    assert [s.name for s in ranked] == ["python", "linux", "git", "kubernetes"]
    assert ranked[0].mentions == 2
