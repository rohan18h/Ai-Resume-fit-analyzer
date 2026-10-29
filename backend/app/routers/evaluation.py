"""GET /api/evaluation — the offline evaluation report (eval/report.json) for the Evaluation page."""

from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter

from app import config
from app.errors import ApiError
from app.schemas import ErrorResponse

router = APIRouter()


@router.get("/evaluation", responses={404: {"model": ErrorResponse, "description": "no_report"}})
def evaluation() -> dict[str, Any]:
    """Return the contents of eval/report.json, or 404 no_report if the evaluation has not been run."""
    try:
        return json.loads(config.EVAL_REPORT_PATH.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        raise ApiError(404, "no_report", "Evaluation has not been run yet.") from exc
