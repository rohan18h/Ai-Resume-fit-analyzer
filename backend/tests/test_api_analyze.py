"""POST /api/analyze: happy path, every error code in Section 10.3, schema, and nothing persisted or logged."""

from __future__ import annotations

import logging
import os
import sqlite3
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from starlette import formparsers

from app import config
from app.main import app
from app.schemas import AnalyzeResponse
from app.services import pipeline

FIXTURES = Path(__file__).parent / "fixtures"
EVAL = Path(__file__).resolve().parent.parent / "eval"
RESUME = (FIXTURES / "sample_resume_backend.pdf").read_bytes()
JD = (EVAL / "jds" / "j01.txt").read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def client() -> TestClient:
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client


def post(client: TestClient, pdf: bytes = RESUME, jd: str = JD, **data: str):
    return client.post(
        "/api/analyze",
        files={"resume": ("resume.pdf", pdf, "application/pdf")},
        data={"job_description": jd, **data},
    )


def assert_error(response, status: int, code: str) -> None:
    assert response.status_code == status, response.text
    body = response.json()
    assert set(body) == {"error"} and body["error"]["code"] == code and body["error"]["message"]


def test_happy_path_matches_schema(client: TestClient) -> None:
    response = post(client)
    assert response.status_code == 200, response.text
    body = AnalyzeResponse.model_validate(response.json())
    assert len(body.request_id) == 32 and body.processing_ms >= 0
    assert body.fit.primary_method == "tfidf"
    assert 0 <= body.fit.score <= 100 and body.fit.score == body.fit.tfidf_score
    assert body.fit.label in {"Good fit", "Average fit", "Low fit"}
    assert {"python", "fastapi", "postgresql", "docker"} <= set(body.skills.resume)
    jd_skills = {s.name: s.importance for s in body.skills.job_description}
    assert jd_skills["python"] == "high" and jd_skills["aws"] == "low"


def test_method_tfidf_has_no_embedding_warning(client: TestClient) -> None:
    both = post(client).json()["warnings"]
    tfidf_only = post(client, method="tfidf").json()["warnings"]
    assert any("embedding" in w.lower() for w in both)
    assert not any("embedding" in w.lower() for w in tfidf_only)


def test_short_jd_warning(client: TestClient) -> None:
    warnings = post(client, jd="We need a Python developer who knows FastAPI and Docker well.", method="tfidf").json()[
        "warnings"
    ]
    assert "The job description is very short, so the score may be unreliable." in warnings


def test_jd_without_known_skills_warning(client: TestClient) -> None:
    jd = "We are looking for a friendly person to greet visitors and answer the phone at our front desk."
    warnings = post(client, jd=jd, method="tfidf").json()["warnings"]
    assert any("No known skills" in w for w in warnings)


# --- error codes -------------------------------------------------------------


def test_invalid_file_type_checks_magic_bytes(client: TestClient) -> None:
    assert_error(post(client, pdf=(FIXTURES / "corrupt.pdf").read_bytes()), 400, "invalid_file_type")


def test_file_too_large(client: TestClient) -> None:
    big = b"%PDF-1.4\n" + b"0" * (config.MAX_UPLOAD_MB * 1024 * 1024)
    assert_error(post(client, pdf=big), 413, "file_too_large")


def test_file_too_large_rejected_by_content_length(client: TestClient) -> None:
    response = client.post(
        "/api/analyze",
        content=b"x",
        headers={"content-length": str(50 * 1024 * 1024), "content-type": "multipart/form-data; boundary=x"},
    )
    assert_error(response, 413, "file_too_large")


@pytest.mark.parametrize(
    "jd, code",
    [("Python developer", "jd_too_short"), ("   " + "x" * 49 + "   ", "jd_too_short"), ("x" * 10001, "jd_too_long")],
)
def test_jd_length_limits(client: TestClient, jd: str, code: str) -> None:
    assert_error(post(client, jd=jd), 422, code)


def test_unreadable_pdf(client: TestClient) -> None:
    assert_error(post(client, pdf=(FIXTURES / "scanned.pdf").read_bytes()), 422, "unreadable_pdf")
    assert_error(post(client, pdf=(FIXTURES / "truncated.pdf").read_bytes()), 422, "unreadable_pdf")


def test_too_many_pages(client: TestClient) -> None:
    assert_error(post(client, pdf=(FIXTURES / "six_pages.pdf").read_bytes()), 422, "too_many_pages")


def test_missing_fields_and_bad_method(client: TestClient) -> None:
    assert_error(client.post("/api/analyze", data={"job_description": JD}), 422, "invalid_request")
    assert_error(post(client, method="magic"), 422, "invalid_request")


def test_internal_error_does_not_leak(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    def boom(*args: object, **kwargs: object) -> None:
        raise RuntimeError("secret internal detail /home/app/db")

    monkeypatch.setattr(pipeline, "analyze", boom)
    response = post(client)
    assert_error(response, 500, "internal_error")
    assert "secret" not in response.text and "Traceback" not in response.text


# --- privacy -------------------------------------------------------------------


def test_upload_stays_in_memory(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    """Starlette spools uploads over 1 MB to a temp file on disk by default; main.py raises that limit."""
    buffers: list[tempfile.SpooledTemporaryFile] = []

    class RecordingSpool(tempfile.SpooledTemporaryFile):
        def __init__(self, *args: object, **kwargs: object) -> None:
            super().__init__(*args, **kwargs)
            buffers.append(self)

    monkeypatch.setattr(formparsers, "SpooledTemporaryFile", RecordingSpool)
    near_limit = RESUME + b"\n%" + b"0" * (config.MAX_UPLOAD_MB * 1024 * 1024 - len(RESUME) - 10)
    assert post(client, pdf=near_limit, method="tfidf").status_code == 200
    assert buffers and not any(buffer._rolled for buffer in buffers)  # never written to disk


def test_nothing_is_persisted_or_logged(client: TestClient, caplog: pytest.LogCaptureFixture) -> None:
    """Section 11: no file left on disk, nothing added to the DB, no resume/JD content in the logs."""
    temp_dir = Path(tempfile.gettempdir())
    before = set(os.listdir(temp_dir))
    with sqlite3.connect(config.DB_PATH) as conn:
        counts_before = [conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in ("skills", "learning_links")]
    # A resume over Starlette's default 1 MB spool limit must still stay in memory.
    padded = RESUME + b"\n%" + b"0" * (2 * 1024 * 1024)

    with caplog.at_level(logging.DEBUG):
        assert post(client, pdf=padded, method="tfidf").status_code == 200

    new_files = set(os.listdir(temp_dir)) - before
    assert not new_files, new_files
    with sqlite3.connect(config.DB_PATH) as conn:
        counts_after = [conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in ("skills", "learning_links")]
    assert counts_after == counts_before
    tables = {row[0] for row in sqlite3.connect(config.DB_PATH).execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert tables == {"skills", "learning_links"}

    logs = caplog.text
    assert "request_id=" in logs
    for secret in ("Asha", "Verma", "inventory tool", "Backend Python Developer", "caching layer"):
        assert secret not in logs
