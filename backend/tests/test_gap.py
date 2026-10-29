"""Gap analyzer: missing = JD - resume, resources attached, coverage, by-category counts, empty cases."""

from __future__ import annotations

from pathlib import Path

from app.services.gap import NO_JD_SKILLS_WARNING, analyze_gap
from app.services.skills import JdSkill, SkillExtractor, SkillHit, extract_skills, rank_jd_skills

EVAL = Path(__file__).resolve().parent.parent / "eval"


def jd(name: str, category: str, importance: str = "medium", mentions: int = 1) -> JdSkill:
    return JdSkill(name, name.title(), category, mentions, importance)


def hit(name: str) -> SkillHit:
    return SkillHit(name, name.title(), "x", 1)


JD_SKILLS = [
    jd("python", "Programming Languages", "high", 3),
    jd("docker", "Cloud & DevOps", "high", 1),
    jd("postgresql", "Databases", "high", 2),
    jd("sql", "Programming Languages", "medium", 1),
    jd("kubernetes", "Cloud & DevOps", "low", 1),
    jd("aws", "Cloud & DevOps", "medium", 2),
]
RESUME = [hit("python"), hit("sql"), hit("react")]  # react is not asked for, so it changes nothing


def test_missing_is_jd_minus_resume_and_matched_is_intersection(seeded_db: Path) -> None:
    gap = analyze_gap(RESUME, JD_SKILLS, seeded_db)
    assert [s.name for s in gap.matched] == ["python", "sql"]
    assert {m.skill.name for m in gap.missing} == {"docker", "postgresql", "kubernetes", "aws"}


def test_missing_sorted_by_importance_then_mentions(seeded_db: Path) -> None:
    gap = analyze_gap(RESUME, JD_SKILLS, seeded_db)
    assert [(m.skill.name, m.skill.importance) for m in gap.missing] == [
        ("postgresql", "high"),  # high, 2 mentions
        ("docker", "high"),  # high, 1 mention
        ("aws", "medium"),
        ("kubernetes", "low"),
    ]


def test_resources_attached_beginner_first_max_three(seeded_db: Path) -> None:
    gap = analyze_gap([], JD_SKILLS, seeded_db)
    for missing in gap.missing:
        assert 1 <= len(missing.resources) <= 3, missing.skill.name
        levels = [r.level for r in missing.resources]
        assert levels == sorted(levels, key=["beginner", "intermediate", "advanced"].index)
        assert all(r.url.startswith("https://") and r.is_free for r in missing.resources)
    docker = next(m for m in gap.missing if m.skill.name == "docker")
    assert docker.resources[0].url == "https://docs.docker.com/get-started/"


def test_coverage_percent(seeded_db: Path) -> None:
    assert analyze_gap(RESUME, JD_SKILLS, seeded_db).coverage_percent == 33.3  # 2 of 6
    assert analyze_gap([hit(s.name) for s in JD_SKILLS], JD_SKILLS, seeded_db).coverage_percent == 100.0
    assert analyze_gap([], JD_SKILLS, seeded_db).coverage_percent == 0.0


def test_by_category_counts(seeded_db: Path) -> None:
    gap = analyze_gap(RESUME, JD_SKILLS, seeded_db)
    assert [(c.category, c.required, c.matched) for c in gap.by_category] == [
        ("Cloud & DevOps", 3, 0),
        ("Programming Languages", 2, 2),
        ("Databases", 1, 0),
    ]
    assert sum(c.required for c in gap.by_category) == len(JD_SKILLS)
    assert sum(c.matched for c in gap.by_category) == len(gap.matched)


def test_no_jd_skills_returns_empty_lists_and_warning(seeded_db: Path) -> None:
    gap = analyze_gap(RESUME, [], seeded_db)
    assert (gap.matched, gap.missing, gap.by_category, gap.coverage_percent) == ([], [], [], 0.0)
    assert gap.warnings == [NO_JD_SKILLS_WARNING]


def test_no_missing_skills(seeded_db: Path) -> None:
    gap = analyze_gap([hit(s.name) for s in JD_SKILLS], JD_SKILLS, seeded_db)
    assert gap.missing == [] and gap.warnings == []


def test_objective_4_every_missing_skill_carries_links(seeded_db: Path, extractor: SkillExtractor) -> None:
    """Step 7 acceptance on real data: a resume with no skills vs every eval JD -> every JD skill is missing
    and each one has at least one learning link; category counts add up."""
    for jd_file in sorted((EVAL / "jds").glob("*.txt")):
        jd_skills = rank_jd_skills(jd_file.read_text(encoding="utf-8"), extractor)
        resume = extract_skills("Friendly person who enjoys teamwork.", extractor)
        gap = analyze_gap(resume, jd_skills, seeded_db)
        assert len(gap.missing) == len(jd_skills) > 0, jd_file.name
        assert all(m.resources for m in gap.missing), jd_file.name
        assert sum(c.required for c in gap.by_category) == len(jd_skills)
