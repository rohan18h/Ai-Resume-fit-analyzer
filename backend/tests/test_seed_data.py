"""Objective 4 data checks on data/skills_seed.json: 100+ skills, every skill has at least one free link."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from seed_db import CATEGORIES, load_seed, validate_seed  # noqa: E402

ENTRIES = load_seed()  # raises if the seed fails validation


def test_objective_4_at_least_100_skills_each_with_a_free_link() -> None:
    assert len(ENTRIES) >= 100
    for entry in ENTRIES:
        assert entry["links"], entry["name"]
        assert any(link.get("is_free", True) for link in entry["links"]), entry["name"]


def test_every_category_is_used() -> None:
    assert {entry["category"] for entry in ENTRIES} == CATEGORIES


def test_spec_alias_examples_are_present() -> None:
    owner = {alias: entry["name"] for entry in ENTRIES for alias in entry["aliases"]}
    assert owner["js"] == "javascript"
    assert owner["reactjs"] == "react"
    assert owner["postgres"] == "postgresql"
    assert owner["k8s"] == "kubernetes"


def test_ambiguous_short_names_are_canonical_skills() -> None:
    names = {entry["name"] for entry in ENTRIES}
    assert {"c", "r", "go", "c++", "c#", "node.js"} <= names


def test_validate_seed_reports_problems() -> None:
    bad = [
        {"name": "Python", "display_name": "Python", "category": "Programming Languages", "aliases": [], "links": []},
        {"name": "java", "display_name": "Java", "category": "Nope", "aliases": ["js"],
         "links": [{"title": "t", "url": "http://x", "provider": "p", "resource_type": "blog", "level": "expert"}]},
        {"name": "javascript", "display_name": "JS", "category": "Programming Languages", "aliases": ["js"],
         "links": [{"title": "t", "url": "https://x", "provider": "p", "resource_type": "docs", "level": "beginner"}]},
    ]
    problems = "\n".join(validate_seed(bad))
    assert "name must be non-empty lowercase" in problems
    assert "needs at least one learning link" in problems
    assert "unknown category" in problems
    assert "must start with https://" in problems
    assert "bad resource_type" in problems
    assert "bad level" in problems
    assert "'js' is already used by 'java'" in problems
