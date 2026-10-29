"""Objective 5 / Section 11: result in <= 5 s for a 2-page resume and a ~400-word JD, after model warm-up."""

from __future__ import annotations

import time
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app

BACKEND = Path(__file__).resolve().parent.parent
RESUME = (BACKEND / "tests" / "fixtures" / "two_page_resume.pdf").read_bytes()
JD = "\n\n".join((BACKEND / "eval" / "jds" / f"{name}.txt").read_text(encoding="utf-8") for name in ("j01", "j04", "j06"))
LIMIT_SECONDS = 5.0


def test_end_to_end_under_5_seconds() -> None:
    assert 350 <= len(JD.split()) <= 500  # "~400-word JD"
    with TestClient(app) as client:
        files = {"resume": ("resume.pdf", RESUME, "application/pdf")}
        assert client.post("/api/analyze", files=files, data={"job_description": JD}).status_code == 200  # warm-up

        timings = []
        for _ in range(3):
            started = time.perf_counter()
            response = client.post("/api/analyze", files=files, data={"job_description": JD})
            timings.append(time.perf_counter() - started)
            assert response.status_code == 200
            body = response.json()
            assert body["fit"]["embedding_score"] is not None and body["ats"]["total"] == 10

    print(f"\nEnd-to-end: {', '.join(f'{t:.2f}s' for t in timings)} (server processing_ms {body['processing_ms']})")
    assert max(timings) <= LIMIT_SECONDS
