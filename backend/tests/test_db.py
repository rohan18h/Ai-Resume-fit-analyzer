"""SQLite schema, seeding (idempotent) and queries."""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from app.db import connect, fetch_links, fetch_skills, init_schema  # noqa: E402
from seed_db import load_seed, seed  # noqa: E402


def _link(url: str, level: str = "beginner") -> dict:
    return {"title": f"Title {url}", "url": url, "provider": "Prov", "resource_type": "docs", "level": level}


SMALL_SEED = [
    {"name": "docker", "display_name": "Docker", "category": "Cloud & DevOps", "aliases": [],
     "links": [_link("https://a.example/adv", "advanced"), _link("https://a.example/int", "intermediate"),
               _link("https://a.example/beg"), _link("https://a.example/beg2")]},
    {"name": "node.js", "display_name": "Node.js", "category": "Web Backend & APIs", "aliases": ["nodejs", "node js"],
     "links": [_link("https://b.example/")]},
]


@pytest.fixture()
def conn(tmp_path: Path) -> sqlite3.Connection:
    connection = connect(tmp_path / "test.db")
    yield connection
    connection.close()


def test_only_two_tables_exist(conn: sqlite3.Connection) -> None:
    init_schema(conn)
    tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
    assert tables == {"skills", "learning_links"}


def test_full_seed_loads_and_is_idempotent(conn: sqlite3.Connection) -> None:
    entries = load_seed()
    first = seed(conn, entries)
    ids_before = [s.id for s in fetch_skills(conn)]
    second = seed(conn, entries)
    assert first == second
    assert first[0] == len(entries) >= 100
    assert [s.id for s in fetch_skills(conn)] == ids_before  # ids stay stable across reseeds


def test_reseed_mirrors_removed_skills_and_links(conn: sqlite3.Connection) -> None:
    seed(conn, SMALL_SEED)
    trimmed = [dict(SMALL_SEED[0], links=SMALL_SEED[0]["links"][:1])]
    assert seed(conn, trimmed) == (1, 1)


def test_fetch_skills_parses_aliases(conn: sqlite3.Connection) -> None:
    seed(conn, SMALL_SEED)
    node = next(s for s in fetch_skills(conn) if s.name == "node.js")
    assert node.display_name == "Node.js"
    assert node.aliases == ("nodejs", "node js")


def test_fetch_links_beginner_first_and_limited(conn: sqlite3.Connection) -> None:
    seed(conn, SMALL_SEED)
    links = fetch_links(conn, ["docker", "unknown"])
    assert [link.level for link in links["docker"]] == ["beginner", "beginner", "intermediate"]
    assert links["docker"][0].is_free is True
    assert links["unknown"] == []
    assert fetch_links(conn, []) == {}


def test_schema_rejects_bad_resource_type(conn: sqlite3.Connection) -> None:
    seed(conn, SMALL_SEED)
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO learning_links (skill_id, title, url, provider, resource_type, level) "
            "VALUES (1, 't', 'https://c.example', 'p', 'blog', 'beginner')"
        )
