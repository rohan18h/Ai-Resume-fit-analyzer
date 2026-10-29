"""POST /api/analyze — validate the upload, run the pipeline, return JSON (Section 10.3).

The resume is read into memory and discarded after the response. Only the request id, sizes and timings
are logged, never the content.
"""

from __future__ import annotations

import logging
import uuid
from time import perf_counter
from typing import Literal

from fastapi import APIRouter, File, Form, UploadFile
from fastapi.concurrency import run_in_threadpool

from app import config
from app.errors import ApiError
from app.schemas import AnalyzeResponse, ErrorResponse
from app.services import pipeline
from app.services.parser import InvalidPdf, UnreadablePdf, count_pages

router = APIRouter()
logger = logging.getLogger("resume_fit")

MAX_UPLOAD_BYTES = config.MAX_UPLOAD_MB * 1024 * 1024

ERROR_RESPONSES = {
    status: {"model": ErrorResponse, "description": description}
    for status, description in {
        400: "invalid_file_type",
        413: "file_too_large",
        422: "jd_too_short, jd_too_long, unreadable_pdf, too_many_pages, invalid_request",
        500: "internal_error",
    }.items()
}


@router.post("/analyze", response_model=AnalyzeResponse, responses=ERROR_RESPONSES)
async def analyze(
    resume: UploadFile = File(..., description="Resume as a PDF, at most MAX_UPLOAD_MB"),
    job_description: str = Form(..., description="Job description text"),
    method: Literal["embeddings", "tfidf", "both"] = Form("both"),
) -> AnalyzeResponse:
    request_id = uuid.uuid4().hex
    started = perf_counter()
    try:
        pdf_bytes = await resume.read(MAX_UPLOAD_BYTES + 1)
    finally:
        await resume.close()

    validate(pdf_bytes, job_description)
    try:
        result = await run_in_threadpool(pipeline.analyze, pdf_bytes, job_description.strip(), method)
    except UnreadablePdf as exc:
        raise ApiError(422, "unreadable_pdf", UNREADABLE_MESSAGE) from exc

    processing_ms = round((perf_counter() - started) * 1000)
    logger.info(
        "analyze request_id=%s pdf_bytes=%d jd_chars=%d processing_ms=%d stages=%s",
        request_id, len(pdf_bytes), len(job_description), processing_ms, result.timings_ms,
    )
    return AnalyzeResponse(
        request_id=request_id,
        processing_ms=processing_ms,
        fit=result.fit,
        skills=result.skills,
        explanation=result.explanation,
        warnings=result.warnings,
    )


UNREADABLE_MESSAGE = "We couldn't read text from this PDF. It may be a scanned image."


def validate(pdf_bytes: bytes, job_description: str) -> None:
    """Raise ApiError for anything the pipeline should not see (size, file type, JD length, page count)."""
    if len(pdf_bytes) > MAX_UPLOAD_BYTES:
        raise ApiError(413, "file_too_large", f"The PDF is larger than {config.MAX_UPLOAD_MB} MB.")
    jd_length = len(job_description.strip())
    if jd_length < config.MIN_JD_CHARS:
        raise ApiError(422, "jd_too_short",
                       f"The job description is too short (at least {config.MIN_JD_CHARS} characters).")
    if jd_length > config.MAX_JD_CHARS:
        raise ApiError(422, "jd_too_long",
                       f"The job description is too long (at most {config.MAX_JD_CHARS} characters).")
    try:
        pages = count_pages(pdf_bytes)
    except InvalidPdf as exc:
        raise ApiError(400, "invalid_file_type", "The file is not a PDF. Please upload a PDF resume.") from exc
    except UnreadablePdf as exc:
        raise ApiError(422, "unreadable_pdf", UNREADABLE_MESSAGE) from exc
    if pages > config.MAX_PDF_PAGES:
        raise ApiError(422, "too_many_pages", f"The resume has more than {config.MAX_PDF_PAGES} pages.")
