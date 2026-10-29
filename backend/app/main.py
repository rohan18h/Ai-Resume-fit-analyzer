"""FastAPI app: CORS, error format, startup and routers."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.formparsers import MultiPartParser

from app import config
from app.errors import ApiError
from app.routers import analyze, health
from app.services.matcher_tfidf import get_vectorizer
from app.services.skills import get_extractor

logger = logging.getLogger("resume_fit")

# Starlette writes uploads larger than 1 MB to a temporary file on disk. Keep every allowed upload in memory
# instead (Section 11: process the file in memory, never write it to disk).
MultiPartParser.spool_max_size = (config.MAX_UPLOAD_MB + 1) * 1024 * 1024

# Multipart overhead allowed on top of the PDF and the JD when checking Content-Length.
_FORM_OVERHEAD_BYTES = 64 * 1024 + config.MAX_JD_CHARS * 4


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Load models once at startup. The embedding model is added in Step 6."""
    app.state.model_loaded = False
    try:
        get_extractor()  # skills list + spaCy matcher, cached for every request
    except RuntimeError as exc:
        logger.warning("%s", exc)
    get_vectorizer()  # TF-IDF fitted on the reference corpus (cached with joblib)
    yield


app = FastAPI(title="Resume Fit Analyzer API", version=config.APP_VERSION, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.ALLOWED_ORIGINS,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


def error_response(status_code: int, code: str, message: str) -> JSONResponse:
    """Build an error in the shape required by Section 10.3."""
    return JSONResponse(status_code=status_code, content={"error": {"code": code, "message": message}})


@app.middleware("http")
async def reject_oversized_uploads(request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
    """Refuse an obviously too large upload before the multipart body is read."""
    if request.url.path == "/api/analyze":
        length = request.headers.get("content-length", "")
        if length.isdigit() and int(length) > config.MAX_UPLOAD_MB * 1024 * 1024 + _FORM_OVERHEAD_BYTES:
            return error_response(413, "file_too_large", f"The PDF is larger than {config.MAX_UPLOAD_MB} MB.")
    return await call_next(request)


@app.exception_handler(ApiError)
async def api_error_handler(_: Request, exc: ApiError) -> JSONResponse:
    return error_response(exc.status_code, exc.code, exc.message)


@app.exception_handler(StarletteHTTPException)
async def http_error_handler(_: Request, exc: StarletteHTTPException) -> JSONResponse:
    code = "not_found" if exc.status_code == 404 else "http_error"
    return error_response(exc.status_code, code, str(exc.detail))


@app.exception_handler(RequestValidationError)
async def validation_error_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    return error_response(422, "invalid_request", "The request is missing fields or has invalid values.")


@app.exception_handler(Exception)
async def internal_error_handler(_: Request, exc: Exception) -> JSONResponse:
    # Log the exception type only: never request content (Section 11).
    logger.error("Unhandled error: %s", type(exc).__name__)
    return error_response(500, "internal_error", "Something went wrong on the server.")


app.include_router(health.router, prefix="/api")
app.include_router(analyze.router, prefix="/api")
