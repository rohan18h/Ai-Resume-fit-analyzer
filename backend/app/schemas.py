"""Pydantic request/response models."""

from __future__ import annotations

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    model_loaded: bool
    version: str


class ErrorDetail(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    """Every error uses this shape: {"error": {"code": ..., "message": ...}}."""

    error: ErrorDetail
