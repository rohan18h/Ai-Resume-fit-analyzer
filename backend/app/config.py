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

# Matching
EMBEDDING_MODEL: str = _str("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
PRIMARY_METHOD: str = _str("PRIMARY_METHOD", "embeddings")  # "tfidf" or "embeddings"
TFIDF_CEILING: float = _float("TFIDF_CEILING", 0.60)  # starting value
EMBED_CEILING: float = _float("EMBED_CEILING", 0.80)  # starting value

# Fit labels (starting values)
LABEL_GOOD_MIN: float = _float("LABEL_GOOD_MIN", 65)
LABEL_AVG_MIN: float = _float("LABEL_AVG_MIN", 40)

# Server
ALLOWED_ORIGINS: list[str] = _list("ALLOWED_ORIGINS", "http://localhost:5173")
DB_PATH: Path = BACKEND_DIR / _str("DB_PATH", "data/app.db")

APP_VERSION: str = "1.0.0"
