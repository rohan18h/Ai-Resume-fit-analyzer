"""Shared fixtures."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from app.db import connect, fetch_skills  # noqa: E402
from app.services.skills import SkillExtractor  # noqa: E402
from seed_db import load_seed, seed  # noqa: E402


@pytest.fixture(scope="session")
def extractor(tmp_path_factory: pytest.TempPathFactory) -> SkillExtractor:
    """Skill extractor built from skills_seed.json in a temporary DB, so tests don't need data/app.db."""
    conn = connect(tmp_path_factory.mktemp("db") / "skills.db")
    seed(conn, load_seed())
    skills = fetch_skills(conn)
    conn.close()
    return SkillExtractor(skills)
