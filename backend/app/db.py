"""SQLite connection and queries (Section 10.4).

Only two tables: skills and learning_links. Nothing about users, resumes or job descriptions is stored.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from app import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS skills (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,              -- canonical, lowercase, e.g. 'node.js'
    display_name TEXT NOT NULL,             -- e.g. 'Node.js'
    category TEXT NOT NULL,
    aliases TEXT NOT NULL DEFAULT '[]'      -- JSON array, e.g. ["nodejs","node js"]
);

CREATE TABLE IF NOT EXISTS learning_links (
    id INTEGER PRIMARY KEY,
    skill_id INTEGER NOT NULL REFERENCES skills(id),
    title TEXT NOT NULL,
    url TEXT NOT NULL,
    provider TEXT NOT NULL,
    resource_type TEXT NOT NULL CHECK (resource_type IN ('docs','course','video','tutorial','book')),
    level TEXT NOT NULL CHECK (level IN ('beginner','intermediate','advanced')),
    is_free INTEGER NOT NULL DEFAULT 1,
    UNIQUE (skill_id, url)
);

CREATE INDEX IF NOT EXISTS idx_learning_links_skill ON learning_links(skill_id);
"""

_LEVEL_ORDER = "CASE level WHEN 'beginner' THEN 0 WHEN 'intermediate' THEN 1 ELSE 2 END"


@dataclass(frozen=True)
class Skill:
    id: int
    name: str
    display_name: str
    category: str
    aliases: tuple[str, ...]


@dataclass(frozen=True)
class LearningLink:
    title: str
    url: str
    provider: str
    resource_type: str
    level: str
    is_free: bool


def connect(db_path: Path | str | None = None) -> sqlite3.Connection:
    """Open the SQLite database (default: config.DB_PATH) with foreign keys on and rows as sqlite3.Row."""
    path = Path(db_path) if db_path is not None else config.DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_schema(conn: sqlite3.Connection) -> None:
    """Create the two tables if they do not exist."""
    conn.executescript(SCHEMA)


def fetch_skills(conn: sqlite3.Connection) -> list[Skill]:
    """All skills with their aliases, sorted by name."""
    rows = conn.execute("SELECT id, name, display_name, category, aliases FROM skills ORDER BY name").fetchall()
    return [
        Skill(row["id"], row["name"], row["display_name"], row["category"], tuple(json.loads(row["aliases"])))
        for row in rows
    ]


def fetch_links(conn: sqlite3.Connection, skill_names: list[str], per_skill: int = 3) -> dict[str, list[LearningLink]]:
    """Learning links for the given canonical skill names, beginner first, at most `per_skill` each.

    Every requested name is present in the result (an empty list if the skill is unknown).
    """
    result: dict[str, list[LearningLink]] = {name: [] for name in skill_names}
    if not skill_names:
        return result
    placeholders = ",".join("?" for _ in skill_names)
    rows = conn.execute(
        f"""
        SELECT s.name, l.title, l.url, l.provider, l.resource_type, l.level, l.is_free
        FROM learning_links l JOIN skills s ON s.id = l.skill_id
        WHERE s.name IN ({placeholders})
        ORDER BY s.name, {_LEVEL_ORDER}, l.id
        """,
        skill_names,
    ).fetchall()
    for row in rows:
        links = result[row["name"]]
        if len(links) < per_skill:
            links.append(
                LearningLink(row["title"], row["url"], row["provider"], row["resource_type"], row["level"],
                             bool(row["is_free"]))
            )
    return result
