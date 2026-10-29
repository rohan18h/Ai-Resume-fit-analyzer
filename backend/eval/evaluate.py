"""Offline evaluation (Objectives 2 and 3): score every hand-labelled pair and compare with the labels.

Methods: "tfidf" and "embeddings" (Objectives 2 and 3) and "weighted", the app's main fit score
(services/scoring.py), so the score users see is checked against the same labels.

Run from backend/:  python eval/evaluate.py

For each method it reports agreement % (predicted label == hand label), a 3x3 confusion matrix, the Spearman
correlation between score and label (poor=0, average=1, good=2) and the mean score per label. The result is
written to eval/report.json, which GET /api/evaluation serves to the Evaluation page.

Pairs without a hand label are still scored, but they are left out of every metric. If no pair is labelled,
the metrics are null: nothing is guessed.

Optional: give a pair "label_a" and "label_b" (two team members labelling independently) as well as the agreed
"label", and the report counts how many pairs the two labellers disagreed on.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from scipy.stats import spearmanr  # noqa: E402

from app import config  # noqa: E402
from app.services.matcher_embed import embedding_score  # noqa: E402
from app.services.matcher_tfidf import get_vectorizer, tfidf_score  # noqa: E402
from app.services.parser import clean_text, clean_text_light, extract_text, strip_name_header  # noqa: E402
from app.services.scoring import weighted_score  # noqa: E402
from app.services.skills import extract_skills, rank_jd_skills  # noqa: E402

LABELS = ("poor", "average", "good")  # confusion matrix order: rows = hand label, columns = predicted
ORDINAL = {label: index for index, label in enumerate(LABELS)}
TUNABLE_SETTINGS = (
    "LABEL_GOOD_MIN", "LABEL_AVG_MIN", "TFIDF_CEILING", "EMBED_CEILING",
    "CHUNK_MAX_WORDS", "CHUNK_MIN_WORDS", "CHUNK_OVERLAP_SENTENCES",
)  # fmt: skip


@dataclass(frozen=True)
class PairTexts:
    resume_clean: str  # for TF-IDF
    jd_clean: str
    resume_light: str  # casing and lines kept, for sentence embeddings (Step 6)
    jd_light: str


def _score_tfidf(texts: PairTexts) -> float:
    return tfidf_score(texts.resume_clean, texts.jd_clean, get_vectorizer()).score


def _score_embeddings(texts: PairTexts) -> float:
    return embedding_score(texts.resume_light, texts.jd_light).score


def _score_weighted(texts: PairTexts) -> float:
    return weighted_score(
        texts.resume_light, texts.jd_light, rank_jd_skills(texts.jd_light), extract_skills(texts.resume_light)
    ).score


# Every method calls the same service functions the API uses.
SCORERS: dict[str, Callable[[PairTexts], float]] = {
    "tfidf": _score_tfidf, "embeddings": _score_embeddings, "weighted": _score_weighted,
}


def label_from_score(score: float) -> str:
    """Predicted label from the same thresholds the app uses (config.LABEL_GOOD_MIN / LABEL_AVG_MIN)."""
    if score >= config.LABEL_GOOD_MIN:
        return "good"
    if score >= config.LABEL_AVG_MIN:
        return "average"
    return "poor"


def load_pairs(eval_dir: Path) -> list[dict]:
    """Read pairs.json and check every label is good / average / poor or empty."""
    pairs = json.loads((eval_dir / "pairs.json").read_text(encoding="utf-8"))
    for pair in pairs:
        for key in ("label", "label_a", "label_b"):
            if pair.get(key) not in (None, *LABELS):
                raise ValueError(f"{pair['id']}: {key} must be one of {LABELS} or null, not {pair[key]!r}")
    return pairs


def pair_texts(pair: dict, eval_dir: Path) -> PairTexts:
    resume = strip_name_header(extract_text((eval_dir / pair["resume_file"]).read_bytes()).text)
    jd = (eval_dir / pair["jd_file"]).read_text(encoding="utf-8")
    return PairTexts(clean_text(resume), clean_text(jd), clean_text_light(resume), clean_text_light(jd))


def score_pairs(pairs: list[dict], eval_dir: Path, methods: list[str]) -> list[dict]:
    rows = []
    for pair in pairs:
        texts = pair_texts(pair, eval_dir)
        row: dict = {"id": pair["id"], "label": pair.get("label")}
        for method in methods:
            score = SCORERS[method](texts)
            row[f"{method}_score"] = score
            row[f"{method}_pred"] = label_from_score(score)
        rows.append(row)
    return rows


def method_metrics(rows: list[dict], method: str) -> dict | None:
    """Agreement %, confusion matrix, Spearman and mean score per label over the labelled rows (None if none)."""
    labelled = [row for row in rows if row["label"]]
    if not labelled:
        return None
    scores = [row[f"{method}_score"] for row in labelled]
    agreement = 100 * sum(row[f"{method}_pred"] == row["label"] for row in labelled) / len(labelled)
    confusion = [
        [sum(row["label"] == actual and row[f"{method}_pred"] == predicted for row in labelled) for predicted in LABELS]
        for actual in LABELS
    ]
    ordinals = [ORDINAL[row["label"]] for row in labelled]
    # Spearman is undefined for fewer than 3 pairs or when all labels (or all scores) are the same.
    defined = len(labelled) >= 3 and len(set(ordinals)) > 1 and len(set(scores)) > 1
    rho = spearmanr(scores, ordinals).statistic if defined else math.nan
    by_label = {
        label: round(mean(s for s, row in zip(scores, labelled) if row["label"] == label), 1)
        if any(row["label"] == label for row in labelled) else None
        for label in LABELS
    }
    return {
        "agreement_percent": round(agreement, 1),
        "spearman": None if math.isnan(rho) else round(float(rho), 3),
        "confusion": confusion,
        "mean_score_by_label": by_label,
    }


def labeller_disagreements(pairs: list[dict]) -> dict | None:
    """How many double-labelled pairs the two labellers disagreed on (None if no pair has label_a and label_b)."""
    double = [p for p in pairs if p.get("label_a") and p.get("label_b")]
    if not double:
        return None
    return {"double_labelled": len(double), "disagreed": sum(p["label_a"] != p["label_b"] for p in double)}


def build_report(pairs: list[dict], rows: list[dict], methods: list[str]) -> dict:
    labelled = sum(1 for row in rows if row["label"])
    tuned = [name for name in TUNABLE_SETTINGS if os.getenv(name)]
    metrics = {method: method_metrics(rows, method) for method in methods}
    embeddings = metrics.get("embeddings")
    notes = [
        "Labels were assigned by hand by the team." if labelled else "No pair has a hand label yet.",
        f"Thresholds and ceilings were overridden ({', '.join(tuned)}). If they were tuned on these same pairs, "
        "the results look better than they would on new data." if tuned else
        "Results use the default thresholds and ceilings from config.py (no tuning).",
    ]
    if labelled < len(rows):
        notes.append(f"{len(rows) - labelled} of {len(rows)} pairs have no hand label yet and are left out of the metrics.")
    return {
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "pairs": len(rows),
        "labelled_pairs": labelled,
        "label_order": list(LABELS),
        "thresholds": {"good_min": config.LABEL_GOOD_MIN, "average_min": config.LABEL_AVG_MIN},
        "ceilings": {"tfidf": config.TFIDF_CEILING, "embeddings": config.EMBED_CEILING},
        "embedding_model": config.EMBEDDING_MODEL,
        "chunking": {"max_words": config.CHUNK_MAX_WORDS, "min_words": config.CHUNK_MIN_WORDS,
                     "overlap_sentences": config.CHUNK_OVERLAP_SENTENCES},
        "tuned_settings": tuned,
        "labeller_disagreements": labeller_disagreements(pairs),
        "methods": metrics,
        "objective_3": {
            "target_percent": config.OBJECTIVE_3_TARGET_PERCENT,
            "agreement_percent": embeddings["agreement_percent"] if embeddings else None,
            "met": embeddings["agreement_percent"] >= config.OBJECTIVE_3_TARGET_PERCENT if embeddings else None,
        },
        "notes": notes,
        "rows": rows,
    }


def summary(report: dict) -> str:
    lines = [f"Evaluated {report['pairs']} pairs ({report['labelled_pairs']} with hand labels)."]
    for method, metrics in report["methods"].items():
        if metrics is None:
            lines.append(f"  {method}: no labelled pairs, so no agreement figures yet.")
        else:
            lines.append(f"  {method}: agreement {metrics['agreement_percent']}%, Spearman {metrics['spearman']}")
    objective = report["objective_3"]
    if objective["met"] is None:
        lines.append(f"Objective 3 (embeddings >= {objective['target_percent']:g}%): not evaluated yet.")
    else:
        verdict = "met" if objective["met"] else "NOT met"
        lines.append(f"Objective 3 (embeddings >= {objective['target_percent']:g}%): {verdict} "
                     f"({objective['agreement_percent']}%).")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--eval-dir", type=Path, default=config.EVAL_DIR)
    parser.add_argument("--out", type=Path, default=config.EVAL_REPORT_PATH)
    parser.add_argument("--methods", nargs="+", choices=sorted(SCORERS), default=list(SCORERS))
    args = parser.parse_args(argv)

    pairs = load_pairs(args.eval_dir)
    rows = score_pairs(pairs, args.eval_dir, args.methods)
    report = build_report(pairs, rows, args.methods)
    args.out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(summary(report))
    print(f"Report written to {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
