"""Regression and evaluation checks on fixed, versioned inputs (all synthetic: tests/fixtures and eval/).

- Scores match the committed snapshot (eval/snapshots/after.json) within a small tolerance for numeric noise
  between machines, so any scoring change shows up here and needs a deliberate new snapshot.
- On the constructed eval groups (by how the dataset was built, not hand labels), same-role pairs score above
  cross-role pairs, which score above cross-field pairs.
- Empty, unreadable and scanned inputs are rejected with a clear error instead of a made-up score.
- The same inputs give the same response every time.

These are consistency checks, not accuracy claims: accuracy needs the hand labels in eval/pairs.json.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from statistics import mean

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services import matcher_embed

BACKEND = Path(__file__).resolve().parent.parent
FIXTURES = BACKEND / "tests" / "fixtures"
SNAPSHOT = json.loads((BACKEND / "eval" / "snapshots" / "after.json").read_text(encoding="utf-8"))
JD = (BACKEND / "eval" / "jds" / "j01.txt").read_text(encoding="utf-8")

SAME_ROLE = [f"p{n:02d}" for n in range(1, 9)]
CROSS_ROLE = ["p09", "p10", "p11", "p12"]
CROSS_FIELD = ["p13", "p14", "p15", "p16"]


@pytest.fixture(scope="module")
def current() -> dict:
    if not matcher_embed.try_load_model():
        pytest.skip("embedding model not available")
    sys.path.insert(0, str(BACKEND / "eval"))
    from snapshot import snapshot

    return snapshot()


@pytest.fixture(scope="module")
def client() -> TestClient:
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client


def post(client: TestClient, pdf: bytes, jd: str = JD):
    return client.post("/api/analyze", files={"resume": ("r.pdf", pdf, "application/pdf")},
                       data={"job_description": jd})


def test_ats_scores_match_the_snapshot(current: dict) -> None:
    assert current["ats_fixtures"] == SNAPSHOT["ats_fixtures"]  # rules only: exact on every machine


def test_pair_scores_match_the_snapshot(current: dict) -> None:
    for pair_id, expected in SNAPSHOT["pairs"].items():
        got = current["pairs"][pair_id]
        assert got["ats"] == expected["ats"] and got["skill_coverage_percent"] == expected["skill_coverage_percent"]
        assert got["tfidf_cosine"] == pytest.approx(expected["tfidf_cosine"], abs=0.002), pair_id
        assert got["embedding_coverage"] == pytest.approx(expected["embedding_coverage"], abs=0.005), pair_id
        assert got["fit"] == pytest.approx(expected["fit"], abs=1.5), pair_id


@pytest.mark.parametrize("key", ["fit", "tfidf_cosine", "embedding_coverage", "skill_coverage_percent"])
def test_constructed_groups_are_ordered(current: dict, key: str) -> None:
    """Every component, not just the final score, ranks same-role > cross-role > cross-field on average."""
    def group_mean(ids: list[str]) -> float:
        return mean(current["pairs"][pair_id][key] for pair_id in ids)

    assert group_mean(SAME_ROLE) > group_mean(CROSS_ROLE) > group_mean(CROSS_FIELD)


def test_cross_field_pairs_get_almost_no_fit(current: dict) -> None:
    assert max(current["pairs"][pair_id]["fit"] for pair_id in CROSS_FIELD) < 10


def test_formatting_is_not_part_of_the_fit_score(current: dict) -> None:
    for row in current["pairs"].values():
        assert set(row["categories"]) == {"skills", "evidence", "responsibilities", "qualifications"}


@pytest.mark.parametrize("name, code", [
    ("blank.pdf", "unreadable_pdf"), ("scanned.pdf", "unreadable_pdf"), ("truncated.pdf", "unreadable_pdf"),
    ("corrupt.pdf", "invalid_file_type"),
])  # fmt: skip
def test_unusable_pdfs_get_an_error_not_a_score(client: TestClient, name: str, code: str) -> None:
    response = post(client, (FIXTURES / name).read_bytes())
    assert response.status_code in (400, 422) and response.json()["error"]["code"] == code


@pytest.mark.parametrize("jd", ["", "   \n\t  "])
def test_empty_job_description_is_rejected(client: TestClient, jd: str) -> None:
    response = post(client, (FIXTURES / "sample_resume_backend.pdf").read_bytes(), jd)
    assert response.status_code == 422 and response.json()["error"]["code"] in ("jd_too_short", "invalid_request")


def test_repeated_requests_give_identical_results(client: TestClient) -> None:
    if not matcher_embed.try_load_model():
        pytest.skip("embedding model not available")
    pdf = (FIXTURES / "sample_resume_backend.pdf").read_bytes()
    bodies = [post(client, pdf).json() for _ in range(3)]
    for body in bodies:
        body.pop("request_id"), body.pop("processing_ms")
    assert bodies[0] == bodies[1] == bodies[2]
