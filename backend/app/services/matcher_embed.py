"""Sentence-embedding matcher (Objective 3): resume vs job description -> coverage score 0-100 + explanation.

Main function:
    embedding_score(resume_light, jd_light) -> EmbeddingResult

Both texts should be lightly cleaned (parser.clean_text_light: casing and lines kept; the resume also passed
through strip_name_header). The model (all-MiniLM-L6-v2) is loaded once and runs on the CPU.

Coverage score: both texts are split into chunks; for every JD chunk take the highest cosine similarity with
any resume chunk; the coverage is the mean of those maxima ("is every requirement in the job description covered
somewhere in the resume?"). score = min(100, coverage / EMBED_CEILING * 100).
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from functools import lru_cache
from typing import TYPE_CHECKING

import numpy as np

from app import config

if TYPE_CHECKING:
    from sentence_transformers import SentenceTransformer

logger = logging.getLogger("resume_fit")

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?;])\s+")
_SNIPPET_MAX_CHARS = 400


@dataclass(frozen=True)
class MatchPair:
    jd_snippet: str
    resume_snippet: str
    similarity: float


@dataclass(frozen=True)
class EmbeddingResult:
    score: float  # 0-100, after scaling by EMBED_CEILING
    coverage: float  # mean of the best similarity per JD chunk, 0-1
    strong_matches: list[MatchPair] = field(default_factory=list)  # best-covered JD chunks, highest first
    weak_spots: list[MatchPair] = field(default_factory=list)  # least-covered JD chunks, lowest first


# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------


@lru_cache(maxsize=1)
def get_model() -> SentenceTransformer:
    """Load the embedding model once (CPU). Raises if it cannot be loaded (e.g. offline on first run)."""
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(config.EMBEDDING_MODEL, device="cpu", revision=config.EMBEDDING_REVISION)


def try_load_model() -> bool:
    """Load the model at startup; return False (and log why) instead of crashing the app."""
    try:
        get_model()
        return True
    except Exception as exc:  # noqa: BLE001 - any failure means "embeddings unavailable"
        logger.warning("Embedding model not loaded: %s", type(exc).__name__)
        return False


def is_model_loaded() -> bool:
    return get_model.cache_info().currsize > 0


# ---------------------------------------------------------------------------
# Chunking
# ---------------------------------------------------------------------------


def split_units(text: str) -> list[str]:
    """Sentences and bullet lines, in order. Each line is its own unit; long lines are split into sentences."""
    units = []
    for line in text.splitlines():
        units.extend(part.strip() for part in _SENTENCE_SPLIT.split(line) if part.strip())
    return units


def make_chunks(
    text: str,
    max_words: int | None = None,
    min_words: int | None = None,
    overlap: int | None = None,
) -> list[str]:
    """Pack sentences/bullets into chunks of at most `max_words` words, keeping sentence boundaries.

    A unit longer than max_words is cut into word windows. A chunk shorter than min_words (e.g. a heading such as
    "Requirements:") is never left on its own; it is joined to the next unit. Consecutive chunks share the last
    `overlap` sentences of the previous chunk.
    """
    max_words = max_words or config.CHUNK_MAX_WORDS
    min_words = config.CHUNK_MIN_WORDS if min_words is None else min_words
    overlap = config.CHUNK_OVERLAP_SENTENCES if overlap is None else overlap

    units: list[list[str]] = []
    for unit in split_units(text):
        words = unit.split()
        units.extend(words[i : i + max_words] for i in range(0, len(words), max_words))

    chunks: list[list[list[str]]] = []
    current: list[list[str]] = []
    for unit in units:
        size = sum(map(len, current))
        if current and size + len(unit) > max_words and size >= min_words:
            chunks.append(current)
            kept = current[-overlap:] if overlap else []
            current = kept if sum(map(len, kept)) + len(unit) <= max_words else []
        current = current + [unit]
    if current:
        if chunks and sum(map(len, current)) < min_words:
            chunks[-1] = chunks[-1] + current  # don't end on a tiny chunk
        else:
            chunks.append(current)
    return [" ".join(word for unit in chunk for word in unit) for chunk in chunks]


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------


def embed(texts: list[str]) -> np.ndarray:
    """Unit-length embeddings, so a dot product is the cosine similarity."""
    return get_model().encode(texts, normalize_embeddings=True, batch_size=32, show_progress_bar=False)


def embedding_score(resume_light: str, jd_light: str) -> EmbeddingResult:
    """Coverage score plus the strongest and weakest JD chunks with their closest resume chunk."""
    resume_chunks = make_chunks(resume_light)
    jd_chunks = make_chunks(jd_light)
    if not resume_chunks or not jd_chunks:
        return EmbeddingResult(0.0, 0.0)

    vectors = embed(jd_chunks + resume_chunks)
    similarity = vectors[: len(jd_chunks)] @ vectors[len(jd_chunks) :].T  # rows: JD chunks, columns: resume chunks
    best_resume = similarity.argmax(axis=1)
    best = similarity.max(axis=1).clip(0, 1)
    coverage = float(best.mean())

    pairs = [
        MatchPair(_snippet(jd_chunks[i]), _snippet(resume_chunks[best_resume[i]]), round(float(best[i]), 3))
        for i in range(len(jd_chunks))
    ]
    order = sorted(range(len(pairs)), key=lambda i: pairs[i].similarity, reverse=True)
    # Up to EXPLANATION_ITEMS of each. With fewer than 2x that many JD chunks, split them evenly (strong gets the
    # extra one) so there are weak spots to show too. A chunk never appears in both lists.
    n = min(config.EXPLANATION_ITEMS, (len(order) + 1) // 2)
    strong = order[:n]
    weak = [i for i in reversed(order) if i not in strong][: config.EXPLANATION_ITEMS]
    return EmbeddingResult(
        score=round(min(100.0, coverage / config.EMBED_CEILING * 100), 1),
        coverage=round(coverage, 4),
        strong_matches=[pairs[i] for i in strong],
        weak_spots=[pairs[i] for i in weak],
    )


def _snippet(text: str) -> str:
    return text if len(text) <= _SNIPPET_MAX_CHARS else text[: _SNIPPET_MAX_CHARS - 1].rsplit(" ", 1)[0] + "…"
