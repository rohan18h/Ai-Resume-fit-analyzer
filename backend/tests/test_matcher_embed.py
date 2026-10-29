"""Embedding matcher: meaning-based similarity, chunking past the model limit, coverage score and explanation."""

from __future__ import annotations

import pytest

from app import config
from app.services import matcher_embed
from app.services.matcher_embed import embed, embedding_score, make_chunks, split_units

pytestmark = pytest.mark.usefixtures("model")


@pytest.fixture(scope="session")
def model():
    return matcher_embed.get_model()  # downloaded once, then cached by sentence-transformers


def cosine(a: str, b: str) -> float:
    vectors = embed([a, b])
    return float(vectors[0] @ vectors[1])


# --- similarity ----------------------------------------------------------------


def test_meaning_beats_exact_words() -> None:
    """Section 7.1 example: same meaning, no shared words, still close; an unrelated text is far."""
    react = "built websites using React"
    assert cosine(react, "frontend developer experience") > cosine(react, "cooking recipes")


def test_identical_texts_score_100() -> None:
    text = "Backend developer building REST APIs with Python and FastAPI.\nDeployed services with Docker on AWS."
    result = embedding_score(text, text)
    assert result.coverage == pytest.approx(1.0, abs=1e-3)
    assert result.score == 100.0


def test_related_resume_scores_higher_than_unrelated() -> None:
    jd = "We need a backend developer with Python, FastAPI and PostgreSQL.\nDocker experience is required."
    related = embedding_score("Built REST APIs in Python with FastAPI and PostgreSQL, shipped in Docker.", jd)
    unrelated = embedding_score("Pastry chef baking bread, cakes and seasonal desserts.", jd)
    assert related.score > unrelated.score
    assert 0 <= unrelated.score <= related.score <= 100


def test_empty_text_scores_zero() -> None:
    result = embedding_score("", "Python developer needed for API work.")
    assert result.score == 0 and result.strong_matches == [] and result.weak_spots == []


# --- chunking --------------------------------------------------------------------


def test_split_units_uses_lines_and_sentences() -> None:
    assert split_units("Requirements:\n- Python. Docker!\n\nSQL; Git") == ["Requirements:", "- Python.", "Docker!", "SQL;", "Git"]


def test_chunks_respect_max_words_and_sentence_boundaries() -> None:
    sentences = [f"Sentence number {i} talks about building reliable backend services." for i in range(40)]
    chunks = make_chunks(" ".join(sentences), max_words=50, min_words=5, overlap=0)
    assert len(chunks) > 1
    assert all(len(chunk.split()) <= 50 for chunk in chunks)
    assert all(chunk.endswith(".") for chunk in chunks)  # never cut mid-sentence
    assert " ".join(chunks) == " ".join(sentences)


def test_chunks_overlap_by_one_sentence() -> None:
    text = "\n".join(f"Line {i} has exactly six words here." for i in range(6))
    chunks = make_chunks(text, max_words=14, min_words=1, overlap=1)
    assert chunks[0].split(". ")[-1] in chunks[1]


def test_short_heading_is_joined_to_next_unit() -> None:
    chunks = make_chunks("Requirements:\nStrong Python and SQL skills.\nNice to have:\nDocker.", max_words=6, min_words=3,
                         overlap=0)
    assert "Requirements:" not in chunks  # never a chunk on its own
    assert chunks[0].startswith("Requirements: Strong Python")


def test_sentence_longer_than_limit_is_split() -> None:
    chunks = make_chunks(" ".join(["word"] * 250), max_words=100, min_words=1, overlap=0)
    assert [len(c.split()) for c in chunks] == [100, 100, 50]


def test_text_longer_than_model_limit_is_fully_covered() -> None:
    """The model reads ~256 word pieces; a 1,000-word resume must still be scored on all of its parts."""
    filler = "\n".join(f"Worked on internal reporting tool number {i} for the finance team." for i in range(80))
    resume = filler + "\nBuilt Kubernetes operators in Go for automated database failover."
    jd = "Experience writing Kubernetes operators in Go."
    assert len(resume.split()) > 800 and len(make_chunks(resume)) > 1
    # The last sentence is far past the model's limit, yet it raises the score: every chunk is embedded.
    assert embedding_score(resume, jd).score > embedding_score(filler, jd).score


# --- explanation ---------------------------------------------------------------


def test_explanation_lists_strongest_and_weakest(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(config, "CHUNK_MAX_WORDS", 8)  # one line per chunk
    monkeypatch.setattr(config, "CHUNK_OVERLAP_SENTENCES", 0)
    resume = "Built REST APIs with Python and FastAPI.\nManaged PostgreSQL databases.\nWrote unit tests with PyTest."
    jd = "\n".join([
        "Build REST APIs in Python with FastAPI.",
        "Manage PostgreSQL databases and queries.",
        "Write unit tests for every service.",
        "Fly commercial aircraft across the Atlantic.",
        "Perform heart surgery in a hospital theatre.",
        "Bake sourdough bread for the morning shift.",
    ])
    result = embedding_score(resume, jd)
    assert len(result.strong_matches) == 3 and len(result.weak_spots) == 3
    strong = [m.similarity for m in result.strong_matches]
    weak = [m.similarity for m in result.weak_spots]
    assert strong == sorted(strong, reverse=True) and weak == sorted(weak)
    assert min(strong) >= max(weak)
    assert not {m.jd_snippet for m in result.strong_matches} & {m.jd_snippet for m in result.weak_spots}
    assert any(word in " ".join(m.jd_snippet for m in result.weak_spots) for word in ("aircraft", "surgery", "sourdough"))


@pytest.mark.parametrize("jd_chunks, strong, weak", [(1, 1, 0), (2, 1, 1), (3, 2, 1), (4, 2, 2), (5, 3, 2), (8, 3, 3)])
def test_explanation_split_for_few_chunks(jd_chunks: int, strong: int, weak: int, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(config, "CHUNK_MAX_WORDS", 8)
    jd = "\n".join(f"Requirement {i}: experience with tool number {i}." for i in range(jd_chunks))
    result = embedding_score("Experience with many different tools.", jd)
    assert (len(result.strong_matches), len(result.weak_spots)) == (strong, weak)


def test_ceiling_scales_the_score(monkeypatch: pytest.MonkeyPatch) -> None:
    resume, jd = "Python developer building APIs.", "Looking for a Python API developer."
    monkeypatch.setattr(config, "EMBED_CEILING", 1.0)
    result = embedding_score(resume, jd)
    assert result.score == pytest.approx(result.coverage * 100, abs=0.1)


def test_model_is_loaded_once() -> None:
    assert matcher_embed.get_model() is matcher_embed.get_model()
    assert matcher_embed.is_model_loaded()


def test_pinned_model_identity() -> None:
    model = matcher_embed.get_model()
    assert config.EMBEDDING_MODEL == "sentence-transformers/all-MiniLM-L6-v2"
    assert len(config.EMBEDDING_REVISION) == 40  # a full commit hash, not a branch name that can move
    assert model.get_sentence_embedding_dimension() == 384


def test_no_chunk_of_the_eval_corpus_is_truncated() -> None:
    """The model reads at most max_seq_length word pieces; anything longer is silently cut off."""
    from pathlib import Path

    from app.services.parser import clean_text_light, extract_text, strip_name_header

    model = matcher_embed.get_model()
    eval_dir = Path(__file__).resolve().parent.parent / "eval"
    texts = [clean_text_light(strip_name_header(extract_text(p.read_bytes()).text))
             for p in sorted((eval_dir / "resumes").glob("*.pdf"))]
    texts += [clean_text_light(p.read_text(encoding="utf-8")) for p in sorted((eval_dir / "jds").glob("*.txt"))]
    longest = max(len(model.tokenizer(chunk)["input_ids"]) for text in texts for chunk in make_chunks(text))
    assert longest <= model.max_seq_length
