"""All tunable constants (Section 10.2). Every value can be overridden by an env var of the same name."""

from __future__ import annotations

import os
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent


def _int(name: str, default: int) -> int:
    return int(os.getenv(name, default))


def _float(name: str, default: float) -> float:
    return float(os.getenv(name, default))


def _str(name: str, default: str) -> str:
    return os.getenv(name, default)


def _list(name: str, default: str) -> list[str]:
    return [item.strip() for item in os.getenv(name, default).split(",") if item.strip()]


# Upload limits
MAX_UPLOAD_MB: int = _int("MAX_UPLOAD_MB", 5)
MAX_PDF_PAGES: int = _int("MAX_PDF_PAGES", 5)
MIN_JD_CHARS: int = _int("MIN_JD_CHARS", 50)
MAX_JD_CHARS: int = _int("MAX_JD_CHARS", 10000)

# Parser
MIN_EXTRACTED_CHARS: int = _int("MIN_EXTRACTED_CHARS", 200)  # below this the PDF is treated as unreadable (starting value)

# Matching
EMBEDDING_MODEL: str = _str("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
# Load the model on the first request instead of at startup (Section 15 fallback for small free instances).
LAZY_MODEL_LOAD: bool = _str("LAZY_MODEL_LOAD", "false").lower() in ("1", "true", "yes")
# Which score is the main fit score: "weighted" (the category model in services/scoring.py), "embeddings" or "tfidf".
PRIMARY_METHOD: str = _str("PRIMARY_METHOD", "weighted")
TFIDF_CEILING: float = _float("TFIDF_CEILING", 0.60)  # starting value
EMBED_CEILING: float = _float("EMBED_CEILING", 0.80)  # starting value
# Embedding chunks (the model reads about 256 word pieces, roughly 190 words). Starting values.
# Sentence-level chunks (team decision, Step 6): each JD requirement is checked on its own, which makes the coverage
# score and the "Why this score?" snippets meaningful. The spec's 100-150 words made most JDs a single chunk.
CHUNK_MAX_WORDS: int = _int("CHUNK_MAX_WORDS", 30)
CHUNK_MIN_WORDS: int = _int("CHUNK_MIN_WORDS", 5)  # shorter pieces (e.g. a heading) are joined to the next one
CHUNK_OVERLAP_SENTENCES: int = _int("CHUNK_OVERLAP_SENTENCES", 1)
EXPLANATION_ITEMS: int = 3  # strongest matches and weakest spots shown in "Why this score?"

EVAL_DIR: Path = BACKEND_DIR / "eval"  # TF-IDF reference corpus: eval/resumes/*.pdf and eval/jds/*.txt
TFIDF_MODEL_PATH: Path = EVAL_DIR / "tfidf_vectorizer.joblib"
# Written by eval/evaluate.py, served by GET /api/evaluation.
EVAL_REPORT_PATH: Path = BACKEND_DIR / _str("EVAL_REPORT_PATH", "eval/report.json")
OBJECTIVE_3_TARGET_PERCENT: float = 70.0  # embeddings must agree with hand labels on at least this share of pairs

# Weighted fit score (services/scoring.py). Category weights are points out of 100; a category that doesn't apply to
# a JD (e.g. it states no degree or years) is left out and its points are shared among the others in proportion.
WEIGHT_SKILLS: float = _float("WEIGHT_SKILLS", 35)  # JD skills the resume has (claimed anywhere)
WEIGHT_EVIDENCE: float = _float("WEIGHT_EVIDENCE", 25)  # JD skills shown in Experience / Projects
WEIGHT_RESPONSIBILITIES: float = _float("WEIGHT_RESPONSIBILITIES", 20)  # JD duties matched by resume bullets
WEIGHT_QUALIFICATIONS: float = _float("WEIGHT_QUALIFICATIONS", 10)  # degree, years, certifications
WEIGHT_READABILITY: float = _float("WEIGHT_READABILITY", 10)  # the ATS checks
# How much each JD skill counts: high = "required"/"must" or 3+ mentions, medium = no cue, low = "preferred"/"bonus".
IMPORTANCE_WEIGHT_HIGH: float = _float("IMPORTANCE_WEIGHT_HIGH", 3)
IMPORTANCE_WEIGHT_MEDIUM: float = _float("IMPORTANCE_WEIGHT_MEDIUM", 2)
IMPORTANCE_WEIGHT_LOW: float = _float("IMPORTANCE_WEIGHT_LOW", 1)
# Partial credit when the resume has a closely linked skill instead of the one asked for (never full credit).
IMPLIED_SKILL_CREDIT: float = _float("IMPLIED_SKILL_CREDIT", 0.75)  # it builds on the asked skill: Django -> Python
RELATED_SKILL_CREDIT: float = _float("RELATED_SKILL_CREDIT", 0.40)  # an alternative to it: MySQL -> PostgreSQL
# Responsibility match: best cosine similarity between a JD duty and any resume bullet, mapped linearly so that
# FLOOR (what unrelated sentences reach with this model) earns 0 and FULL (a clear paraphrase) earns full credit.
RESP_SIM_FLOOR: float = _float("RESP_SIM_FLOOR", 0.30)
RESP_SIM_FULL: float = _float("RESP_SIM_FULL", 0.65)
# Same idea without the model: share of the duty's content words found in the best resume bullet.
RESP_OVERLAP_FLOOR: float = _float("RESP_OVERLAP_FLOOR", 0.15)
RESP_OVERLAP_FULL: float = _float("RESP_OVERLAP_FULL", 0.50)
MAX_RESPONSIBILITIES: int = _int("MAX_RESPONSIBILITIES", 15)  # JD duties compared, in order

# Fit labels (starting values)
LABEL_GOOD_MIN: float = _float("LABEL_GOOD_MIN", 65)
LABEL_AVG_MIN: float = _float("LABEL_AVG_MIN", 40)

# Warnings
SHORT_JD_WARNING_CHARS: int = _int("SHORT_JD_WARNING_CHARS", 300)  # warn that the score may be unreliable (starting value)

# Server
ALLOWED_ORIGINS: list[str] = _list("ALLOWED_ORIGINS", "http://localhost:5173")
DB_PATH: Path = BACKEND_DIR / _str("DB_PATH", "data/app.db")

APP_VERSION: str = "1.0.0"
