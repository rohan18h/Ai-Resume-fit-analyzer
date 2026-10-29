"""GET /api/health — used for the demo warm-up (Section 18)."""

from __future__ import annotations

from fastapi import APIRouter

from app import config
from app.schemas import HealthResponse
from app.services.matcher_embed import is_model_loaded

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    """Report that the API is up and whether the embedding model is loaded."""
    return HealthResponse(status="ok", model_loaded=is_model_loaded(), version=config.APP_VERSION)
