"""TF-IDF matcher (Objective 2, the baseline): resume vs job description -> fit score 0-100.

Main function:
    tfidf_score(resume_clean, jd_clean) -> TfidfResult

Both texts must already be cleaned with parser.clean_text (and the resume passed through strip_name_header).

The vectorizer is fitted on a reference corpus (eval/resumes/*.pdf and eval/jds/*.txt) and cached with joblib.
It is refitted automatically when the corpus files change. If there is no corpus, it is fitted on the pair itself.
"""

from __future__ import annotations

import hashlib
import logging
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from app import config
from app.services.parser import ParserError, clean_text, english_stopwords, extract_text, strip_name_header

logger = logging.getLogger("resume_fit")

# The spec suggests r"(?u)\b[\w+#.]+\b", but the trailing \b cannot follow "+" or "#", so "c++" and "c#" would
# both become "c". This pattern keeps them; it relies on clean_text having removed trailing dots already.
TOKEN_PATTERN = r"(?u)\b\w[\w+#.]*"


@dataclass(frozen=True)
class TfidfResult:
    score: float  # 0-100, after scaling by TFIDF_CEILING
    cosine: float  # raw cosine similarity, 0-1


def make_vectorizer() -> TfidfVectorizer:
    """TF-IDF settings from Section 10.5.3 (unigrams + bigrams, sublinear tf, NLTK English stopwords)."""
    # Only single-word stopwords, so they tokenise the same way as the text (avoids a scikit-learn warning).
    stop_words = sorted(word for word in english_stopwords() if re.fullmatch(r"\w+", word))
    return TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True, stop_words=stop_words, token_pattern=TOKEN_PATTERN)


def tfidf_score(resume_clean: str, jd_clean: str, vectorizer: TfidfVectorizer | None = None) -> TfidfResult:
    """Cosine similarity of the TF-IDF vectors, scaled: score = min(100, cosine / TFIDF_CEILING * 100)."""
    if not resume_clean.strip() or not jd_clean.strip():
        return TfidfResult(0.0, 0.0)
    if vectorizer is None:
        vectorizer = get_vectorizer()
    try:
        if vectorizer is None:  # no reference corpus: fit on the pair itself
            vectorizer = make_vectorizer().fit([resume_clean, jd_clean])
        matrix = vectorizer.transform([resume_clean, jd_clean])
    except ValueError:  # e.g. both texts contain only stopwords
        return TfidfResult(0.0, 0.0)
    cosine = float(cosine_similarity(matrix[0], matrix[1])[0, 0])
    return TfidfResult(score=round(min(100.0, cosine / config.TFIDF_CEILING * 100), 1), cosine=round(cosine, 4))


# ---------------------------------------------------------------------------
# Reference corpus
# ---------------------------------------------------------------------------


def _corpus_files(eval_dir: Path) -> list[Path]:
    return sorted((eval_dir / "resumes").glob("*.pdf")) + sorted((eval_dir / "jds").glob("*.txt"))


def corpus_fingerprint(eval_dir: Path) -> str:
    """Hash of the corpus file names and contents, so a changed corpus triggers a refit."""
    digest = hashlib.sha256()
    for path in _corpus_files(eval_dir):
        digest.update(path.relative_to(eval_dir).as_posix().encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


def corpus_texts(eval_dir: Path) -> list[str]:
    """Cleaned texts of every corpus document. Unreadable PDFs are skipped."""
    texts = []
    for path in _corpus_files(eval_dir):
        if path.suffix == ".pdf":
            try:
                texts.append(clean_text(strip_name_header(extract_text(path.read_bytes()).text)))
            except ParserError:
                logger.warning("Skipping unreadable corpus file %s", path.name)
        else:
            texts.append(clean_text(path.read_text(encoding="utf-8")))
    return [text for text in texts if text]


@lru_cache(maxsize=1)
def get_vectorizer(eval_dir: Path = config.EVAL_DIR, model_path: Path = config.TFIDF_MODEL_PATH) -> TfidfVectorizer | None:
    """Load the corpus vectorizer from joblib, refitting and saving it if the corpus changed. None if no corpus."""
    if not _corpus_files(eval_dir):
        return None
    fingerprint = corpus_fingerprint(eval_dir)
    if model_path.exists():
        try:
            saved = joblib.load(model_path)
            if saved.get("fingerprint") == fingerprint:
                return saved["vectorizer"]
        except Exception:  # noqa: BLE001 - a broken cache file is simply rebuilt
            logger.warning("Rebuilding unreadable TF-IDF cache %s", model_path.name)

    texts = corpus_texts(eval_dir)
    if not texts:
        return None
    vectorizer = make_vectorizer().fit(texts)
    try:
        joblib.dump({"fingerprint": fingerprint, "vectorizer": vectorizer}, model_path)
    except OSError:
        logger.warning("Could not save the TF-IDF cache to %s", model_path)
    return vectorizer
