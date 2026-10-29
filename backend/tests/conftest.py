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
def seeded_db(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """A database built from skills_seed.json in a temp folder, so tests don't need data/app.db."""
    path = tmp_path_factory.mktemp("db") / "skills.db"
    conn = connect(path)
    seed(conn, load_seed())
    conn.close()
    return path


@pytest.fixture(scope="session")
def extractor(seeded_db: Path) -> SkillExtractor:
    """Skill extractor built from the seeded temp database."""
    conn = connect(seeded_db)
    skills = fetch_skills(conn)
    conn.close()
    return SkillExtractor(skills)
