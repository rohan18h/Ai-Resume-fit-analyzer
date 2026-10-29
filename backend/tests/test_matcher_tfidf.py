"""TF-IDF matcher: identical ~100, unrelated low, always 0-100, corpus caching."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import joblib
import pytest

from app import config
from app.services.matcher_tfidf import (
    corpus_fingerprint,
    get_vectorizer,
    make_vectorizer,
    tfidf_score,
)
from app.services.parser import clean_text

BACKEND = Path(__file__).resolve().parent.parent
EVAL = BACKEND / "eval"

RESUME = clean_text("Backend developer building REST APIs with Python, FastAPI, PostgreSQL and Docker on AWS.")
JD = clean_text("We need a backend developer with Python and FastAPI. PostgreSQL and Docker required; AWS is a plus.")
UNRELATED = clean_text("Pastry chef experienced in baking bread, cakes and seasonal desserts for a busy bakery.")


@pytest.fixture(scope="module")
def corpus_vectorizer(tmp_path_factory: pytest.TempPathFactory):
    return get_vectorizer.__wrapped__(EVAL, tmp_path_factory.mktemp("tfidf") / "v.joblib")


@pytest.mark.parametrize("use_corpus", [True, False])
def test_identical_texts_score_near_100(use_corpus: bool, corpus_vectorizer) -> None:
    vectorizer = corpus_vectorizer if use_corpus else make_vectorizer().fit([RESUME, RESUME])
    result = tfidf_score(RESUME, RESUME, vectorizer)
    assert result.cosine == pytest.approx(1.0, abs=1e-6)
    assert result.score == 100.0


def test_related_scores_higher_than_unrelated(corpus_vectorizer) -> None:
    related = tfidf_score(RESUME, JD, corpus_vectorizer)
    unrelated = tfidf_score(UNRELATED, JD, corpus_vectorizer)
    assert related.score > unrelated.score
    assert unrelated.score < 10


def test_scores_stay_within_0_and_100(corpus_vectorizer) -> None:
    texts = [RESUME, JD, UNRELATED, "python", clean_text("C++ and C# developer")]
    for a in texts:
        for b in texts:
            assert 0 <= tfidf_score(a, b, corpus_vectorizer).score <= 100


def test_empty_or_stopword_only_text_scores_zero() -> None:
    assert tfidf_score("", JD).score == 0
    assert tfidf_score("the and of", "is a the", make_vectorizer()).score == 0  # unfitted -> ValueError -> 0


def test_falls_back_to_fitting_on_the_pair(tmp_path: Path) -> None:
    assert get_vectorizer.__wrapped__(tmp_path / "empty_eval", tmp_path / "v.joblib") is None
    # get_vectorizer() returning None makes tfidf_score fit on the pair itself
    assert tfidf_score(RESUME, JD, None).score > 0


def test_token_pattern_keeps_tech_tokens() -> None:
    analyzer = make_vectorizer().build_analyzer()
    tokens = analyzer(clean_text("C++, C#, Node.js and CI/CD with the team"))
    assert {"c++", "c#", "node.js"} <= set(tokens)
    assert "the" not in tokens and "with" not in tokens  # NLTK stopwords removed


def test_corpus_vectorizer_is_cached_and_refitted_when_corpus_changes(tmp_path: Path) -> None:
    eval_dir = tmp_path / "eval"
    shutil.copytree(EVAL / "jds", eval_dir / "jds")
    model = tmp_path / "v.joblib"

    first = get_vectorizer.__wrapped__(eval_dir, model)
    saved = joblib.load(model)
    assert saved["fingerprint"] == corpus_fingerprint(eval_dir)
    assert first.vocabulary_ == saved["vectorizer"].vocabulary_

    (eval_dir / "jds" / "extra.txt").write_text("Rust developer for embedded firmware work.", encoding="utf-8")
    refitted = get_vectorizer.__wrapped__(eval_dir, model)
    assert "firmware" in refitted.vocabulary_
    assert joblib.load(model)["fingerprint"] == corpus_fingerprint(eval_dir)


def test_ceiling_scales_the_score(monkeypatch: pytest.MonkeyPatch, corpus_vectorizer) -> None:
    raw = tfidf_score(RESUME, JD, corpus_vectorizer)
    monkeypatch.setattr(config, "TFIDF_CEILING", 1.0)
    assert tfidf_score(RESUME, JD, corpus_vectorizer).score == pytest.approx(raw.cosine * 100, abs=0.1)


def test_objective_2_scores_for_all_labelled_pairs(corpus_vectorizer) -> None:
    """Step 4 acceptance: a TF-IDF score for every pair in eval/pairs.json (10+ pairs)."""
    from app.services.parser import extract_text, strip_name_header

    pairs = json.loads((EVAL / "pairs.json").read_text(encoding="utf-8"))
    assert len(pairs) >= 10
    rows = []
    for pair in pairs:
        resume = clean_text(strip_name_header(extract_text((EVAL / pair["resume_file"]).read_bytes()).text))
        jd = clean_text((EVAL / pair["jd_file"]).read_text(encoding="utf-8"))
        score = tfidf_score(resume, jd, corpus_vectorizer).score
        assert 0 <= score <= 100
        rows.append(f"{pair['id']}  {score:5.1f}  {pair['notes']}")
    print(f"\nObjective 2: TF-IDF scores for {len(pairs)} pairs\n" + "\n".join(rows))
