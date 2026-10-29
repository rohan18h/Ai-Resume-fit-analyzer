"""config.py defaults match Section 10.2 and env vars override them."""

import importlib

from app import config


def test_defaults() -> None:
    assert config.MAX_UPLOAD_MB == 5
    assert config.MAX_PDF_PAGES == 5
    assert (config.MIN_JD_CHARS, config.MAX_JD_CHARS) == (50, 10000)
    assert config.PRIMARY_METHOD == "embeddings"
    assert (config.TFIDF_CEILING, config.EMBED_CEILING) == (0.60, 0.80)
    assert (config.LABEL_GOOD_MIN, config.LABEL_AVG_MIN) == (65, 40)


def test_env_override(monkeypatch) -> None:
    monkeypatch.setenv("MAX_UPLOAD_MB", "3")
    monkeypatch.setenv("ALLOWED_ORIGINS", "https://a.example, https://b.example")
    reloaded = importlib.reload(config)
    try:
        assert reloaded.MAX_UPLOAD_MB == 3
        assert reloaded.ALLOWED_ORIGINS == ["https://a.example", "https://b.example"]
    finally:
        monkeypatch.undo()
        importlib.reload(config)
