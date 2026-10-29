"""GET /api/health — used for the demo warm-up (Section 18)."""

from __future__ import annotations

from fastapi import APIRouter, Request

from app import config
from app.schemas import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health(request: Request) -> HealthResponse:
    """Report that the API is up and whether the embedding model is loaded."""
    return HealthResponse(
        status="ok",
        model_loaded=bool(getattr(request.app.state, "model_loaded", False)),
        version=config.APP_VERSION,
    )
