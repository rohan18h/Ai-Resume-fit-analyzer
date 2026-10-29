"""Build data/app.db from data/skills_seed.json. Safe to run again: the database ends up mirroring the seed file.

Run from backend/:  python scripts/seed_db.py
"""

from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from app import config  # noqa: E402
from app.db import connect, init_schema  # noqa: E402

SEED_PATH = BACKEND_DIR / "data" / "skills_seed.json"

CATEGORIES = {
    "Programming Languages", "Web Frontend", "Web Backend & APIs", "Databases", "Cloud & DevOps",
    "Data Science & ML", "Core CS", "Tools & Practices", "Testing & QA", "Mobile", "Security",
}  # fmt: skip
RESOURCE_TYPES = {"docs", "course", "video", "tutorial", "book"}
LEVELS = {"beginner", "intermediate", "advanced"}


def load_seed(path: Path = SEED_PATH) -> list[dict]:
    """Load and validate the seed file. Raises ValueError listing every problem found."""
    entries = json.loads(path.read_text(encoding="utf-8"))
    problems = validate_seed(entries)
    if problems:
        raise ValueError("Invalid skills seed:\n  " + "\n  ".join(problems))
    return entries


def validate_seed(entries: list[dict]) -> list[str]:
    """Return a list of problems (empty if the seed is valid)."""
    problems: list[str] = []
    owner: dict[str, str] = {}  # every name and alias -> the skill it belongs to
    for entry in entries:
        name = entry.get("name", "")
        label = name or repr(entry)[:40]
        if not name or name != name.strip().lower():
            problems.append(f"{label}: name must be non-empty lowercase")
        if not entry.get("display_name"):
            problems.append(f"{label}: missing display_name")
        if entry.get("category") not in CATEGORIES:
            problems.append(f"{label}: unknown category {entry.get('category')!r}")
        for term in [name, *entry.get("aliases", [])]:
            if term != term.strip().lower():
                problems.append(f"{label}: alias {term!r} must be lowercase")
            if term in owner and owner[term] != name:
                problems.append(f"{label}: {term!r} is already used by {owner[term]!r}")
            owner[term] = name
        links = entry.get("links", [])
        if not links:
            problems.append(f"{label}: needs at least one learning link")
        urls = [link.get("url", "") for link in links]
        if len(urls) != len(set(urls)):
            problems.append(f"{label}: duplicate link URL")
        for link in links:
            if not link.get("title") or not link.get("provider"):
                problems.append(f"{label}: link needs title and provider")
            if not str(link.get("url", "")).startswith("https://"):
                problems.append(f"{label}: link URL must start with https://")
            if link.get("resource_type") not in RESOURCE_TYPES:
                problems.append(f"{label}: bad resource_type {link.get('resource_type')!r}")
            if link.get("level") not in LEVELS:
                problems.append(f"{label}: bad level {link.get('level')!r}")
    return problems


def seed(conn: sqlite3.Connection, entries: list[dict]) -> tuple[int, int]:
    """Upsert skills and links, and delete anything no longer in the seed. Returns (skills, links) counts."""
    init_schema(conn)
    with conn:
        for entry in entries:
            conn.execute(
                """
                INSERT INTO skills (name, display_name, category, aliases) VALUES (?, ?, ?, ?)
                ON CONFLICT(name) DO UPDATE SET
                    display_name = excluded.display_name, category = excluded.category, aliases = excluded.aliases
                """,
                (entry["name"], entry["display_name"], entry["category"], json.dumps(entry.get("aliases", []))),
            )
            skill_id = conn.execute("SELECT id FROM skills WHERE name = ?", (entry["name"],)).fetchone()[0]
            for link in entry["links"]:
                conn.execute(
                    """
                    INSERT INTO learning_links (skill_id, title, url, provider, resource_type, level, is_free)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(skill_id, url) DO UPDATE SET
                        title = excluded.title, provider = excluded.provider,
                        resource_type = excluded.resource_type, level = excluded.level, is_free = excluded.is_free
                    """,
                    (skill_id, link["title"], link["url"], link["provider"], link["resource_type"], link["level"],
                     int(link.get("is_free", True))),
                )
            urls = [link["url"] for link in entry["links"]]
            conn.execute(
                f"DELETE FROM learning_links WHERE skill_id = ? AND url NOT IN ({','.join('?' for _ in urls)})",
                (skill_id, *urls),
            )
        names = [entry["name"] for entry in entries]
        placeholders = ",".join("?" for _ in names)
        conn.execute(
            f"DELETE FROM learning_links WHERE skill_id IN (SELECT id FROM skills WHERE name NOT IN ({placeholders}))",
            names,
        )
        conn.execute(f"DELETE FROM skills WHERE name NOT IN ({placeholders})", names)
    skills = conn.execute("SELECT COUNT(*) FROM skills").fetchone()[0]
    links = conn.execute("SELECT COUNT(*) FROM learning_links").fetchone()[0]
    return skills, links


def main() -> None:
    entries = load_seed()
    with connect(config.DB_PATH) as conn:
        skills, links = seed(conn, entries)
    conn.close()
    print(f"Seeded {config.DB_PATH}: {skills} skills, {links} learning links")


if __name__ == "__main__":
    main()
