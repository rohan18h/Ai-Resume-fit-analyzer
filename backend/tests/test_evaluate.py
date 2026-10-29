"""eval/evaluate.py: metrics, labels from scores, report contents, and GET /api/evaluation.

Tests that need labels use PLACEHOLDER labels on a temporary copy of the dataset. They are not real
hand labels and never touch eval/pairs.json.
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import config
from app.main import app

EVAL = Path(__file__).resolve().parent.parent / "eval"
sys.path.insert(0, str(EVAL))

import evaluate  # noqa: E402

PLACEHOLDER_LABELS = ["good"] * 8 + ["average"] * 4 + ["poor"] * 4  # test data only, not hand labels


def rows(*items: tuple[str | None, float]) -> list[dict]:
    return [
        {"id": f"x{i}", "label": label, "tfidf_score": score, "tfidf_pred": evaluate.label_from_score(score)}
        for i, (label, score) in enumerate(items)
    ]


@pytest.mark.parametrize(
    "score, label", [(0, "poor"), (39.9, "poor"), (40, "average"), (64.9, "average"), (65, "good"), (100, "good")]
)
def test_label_from_score_uses_config_thresholds(score: float, label: str) -> None:
    assert evaluate.label_from_score(score) == label


def test_method_metrics() -> None:
    data = rows(("good", 80), ("good", 50), ("average", 45), ("poor", 10), ("poor", 60), (None, 99))
    metrics = evaluate.method_metrics(data, "tfidf")
    assert metrics["agreement_percent"] == 60.0  # 3 of 5 labelled rows correct; the unlabelled row is ignored
    assert metrics["confusion"] == [
        [1, 1, 0],  # poor:    predicted poor, average, good
        [0, 1, 0],  # average
        [0, 1, 1],  # good
    ]
    assert metrics["mean_score_by_label"] == {"poor": 35.0, "average": 45.0, "good": 65.0}
    assert 0 < metrics["spearman"] <= 1


def test_metrics_are_none_without_labels() -> None:
    assert evaluate.method_metrics(rows((None, 50), (None, 10)), "tfidf") is None


def test_spearman_none_when_undefined() -> None:
    assert evaluate.method_metrics(rows(("good", 70), ("good", 80)), "tfidf")["spearman"] is None  # < 3 rows
    assert evaluate.method_metrics(rows(("good", 70), ("good", 80), ("good", 90)), "tfidf")["spearman"] is None


def test_labeller_disagreements() -> None:
    pairs = [
        {"id": "a", "label_a": "good", "label_b": "good"},
        {"id": "b", "label_a": "good", "label_b": "average"},
        {"id": "c", "label_a": "poor"},
    ]
    assert evaluate.labeller_disagreements(pairs) == {"double_labelled": 2, "disagreed": 1}
    assert evaluate.labeller_disagreements([{"id": "d"}]) is None


def test_invalid_label_is_rejected(tmp_path: Path) -> None:
    (tmp_path / "pairs.json").write_text(json.dumps([{"id": "p1", "label": "great"}]), encoding="utf-8")
    with pytest.raises(ValueError, match="label must be one of"):
        evaluate.load_pairs(tmp_path)


def test_unlabelled_dataset_gives_scores_but_no_metrics(tmp_path: Path) -> None:
    out = tmp_path / "report.json"
    assert evaluate.main(["--out", str(out)]) == 0
    report = json.loads(out.read_text(encoding="utf-8"))
    pairs = json.loads((EVAL / "pairs.json").read_text(encoding="utf-8"))
    assert report["pairs"] == len(pairs) >= 10
    assert report["thresholds"] == {"good_min": 65.0, "average_min": 40.0}
    assert set(report["methods"]) == {"tfidf", "embeddings", "weighted"}  # both methods + the app's main score
    assert all(
        0 <= row[f"{method}_score"] <= 100 for row in report["rows"] for method in ("tfidf", "embeddings", "weighted")
    )
    if report["labelled_pairs"] == 0:
        assert report["methods"] == {"tfidf": None, "embeddings": None, "weighted": None}
        assert report["objective_3"] == {"target_percent": 70.0, "agreement_percent": None, "met": None}


def test_report_with_placeholder_labels(tmp_path: Path) -> None:
    eval_dir = tmp_path / "eval"
    shutil.copytree(EVAL, eval_dir, ignore=shutil.ignore_patterns("*.joblib", "report.json", "__pycache__"))
    pairs = json.loads((eval_dir / "pairs.json").read_text(encoding="utf-8"))
    for pair, label in zip(pairs, PLACEHOLDER_LABELS):
        pair["label"] = label
    pairs[0]["label_a"], pairs[0]["label_b"] = "good", "average"
    (eval_dir / "pairs.json").write_text(json.dumps(pairs), encoding="utf-8")

    out = tmp_path / "report.json"
    evaluate.main(["--eval-dir", str(eval_dir), "--out", str(out)])
    report = json.loads(out.read_text(encoding="utf-8"))

    assert report["labelled_pairs"] == len(pairs)
    tfidf = report["methods"]["tfidf"]
    assert 0 <= tfidf["agreement_percent"] <= 100
    assert sum(map(sum, tfidf["confusion"])) == len(pairs)
    assert report["labeller_disagreements"] == {"double_labelled": 1, "disagreed": 1}
    embeddings = report["methods"]["embeddings"]
    assert report["objective_3"]["agreement_percent"] == embeddings["agreement_percent"]
    assert report["objective_3"]["met"] == (embeddings["agreement_percent"] >= 70)
    assert {"id", "label", "tfidf_score", "tfidf_pred", "embeddings_score", "embeddings_pred"} <= set(report["rows"][0])
    assert report["chunking"]["max_words"] == config.CHUNK_MAX_WORDS
    assert "Results use the default thresholds" in " ".join(report["notes"])


def test_tuned_settings_are_reported(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TFIDF_CEILING", "0.4")
    report = evaluate.build_report([], rows(("good", 70)), ["tfidf"])
    assert report["tuned_settings"] == ["TFIDF_CEILING"]
    assert any("overridden" in note for note in report["notes"])


# --- GET /api/evaluation -------------------------------------------------------


def test_evaluation_endpoint_serves_report(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    report = tmp_path / "report.json"
    report.write_text(json.dumps({"pairs": 3, "methods": {"tfidf": None}}), encoding="utf-8")
    monkeypatch.setattr(config, "EVAL_REPORT_PATH", report)
    with TestClient(app) as client:
        response = client.get("/api/evaluation")
    assert response.status_code == 200
    assert response.json() == {"pairs": 3, "methods": {"tfidf": None}}


def test_evaluation_endpoint_without_report(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(config, "EVAL_REPORT_PATH", tmp_path / "missing.json")
    with TestClient(app) as client:
        response = client.get("/api/evaluation")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "no_report"
