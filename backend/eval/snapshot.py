"""Score snapshot: every component score for fixed inputs, so a scoring change can be compared before and after.

Run from backend/:
    python eval/snapshot.py eval/snapshots/after.json              write a snapshot of the current code
    python eval/snapshot.py --compare eval/snapshots/before.json eval/snapshots/after.json

Inputs (all synthetic and versioned in the repo): every PDF in tests/fixtures (ATS checks only) and every pair in
eval/pairs.json (full pipeline). Each pair records the main fit score, the TF-IDF and embedding scores and their raw
cosines, skill coverage, the weighted categories and the ATS score. Nothing is written for unreadable files except
the error code. The same code and inputs always give the same snapshot.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from app.services import matcher_embed, pipeline  # noqa: E402
from app.services.ats import check_ats  # noqa: E402
from app.services.matcher_embed import embedding_score  # noqa: E402
from app.services.matcher_tfidf import tfidf_score  # noqa: E402
from app.services.parser import ParserError, clean_text, clean_text_light, extract_text, strip_name_header  # noqa: E402

FIXTURES = BACKEND_DIR / "tests" / "fixtures"
EVAL_DIR = BACKEND_DIR / "eval"


def ats_rows() -> dict:
    rows = {}
    for path in sorted(FIXTURES.glob("*.pdf")):
        pdf = path.read_bytes()
        try:
            result = check_ats(pdf, extract_text(pdf))
        except ParserError as exc:
            rows[path.name] = {"error": exc.code}
            continue
        rows[path.name] = {"ats": result.score, "checks": {c.id: c.status for c in result.checks}}
    return rows


def pair_rows() -> dict:
    rows = {}
    for pair in json.loads((EVAL_DIR / "pairs.json").read_text(encoding="utf-8")):
        pdf = (EVAL_DIR / pair["resume_file"]).read_bytes()
        jd = (EVAL_DIR / pair["jd_file"]).read_text(encoding="utf-8")
        result = pipeline.analyze(pdf, jd, "both")
        resume = strip_name_header(extract_text(pdf).text)
        tfidf = tfidf_score(clean_text(resume), clean_text(jd))
        embed = embedding_score(clean_text_light(resume), clean_text_light(jd))
        breakdown = result.breakdown
        rows[pair["id"]] = {
            "notes": pair.get("notes", ""),
            "fit": result.fit.score,
            "primary_method": result.fit.primary_method,
            "tfidf_score": result.fit.tfidf_score,
            "tfidf_cosine": tfidf.cosine,
            "embedding_score": result.fit.embedding_score,
            "embedding_coverage": embed.coverage,
            "skill_coverage_percent": result.skills.coverage_percent,
            "ats": result.ats.score,
            "categories": {c.id: [c.points, c.max_points] for c in breakdown.categories} if breakdown else None,
        }
    return rows


def snapshot() -> dict:
    if not matcher_embed.try_load_model():
        raise SystemExit("The embedding model could not be loaded, so a snapshot would not be comparable.")
    return {"ats_fixtures": ats_rows(), "pairs": pair_rows()}


def compare(before: dict, after: dict) -> str:
    lines = ["ATS score per fixture (before -> after):"]
    for name, old in before["ats_fixtures"].items():
        new = after["ats_fixtures"].get(name, {})
        if "ats" in old or "ats" in new:
            changed = {k: f"{v}->{new.get('checks', {}).get(k)}" for k, v in old.get("checks", {}).items()
                       if new.get("checks", {}).get(k) != v}
            lines.append(f"  {name:28} {old.get('ats')!s:>4} -> {new.get('ats')!s:>4}  {changed or ''}")
    lines.append("\nEval pairs (before -> after): fit | tfidf cosine | embedding coverage | skill coverage % | ATS")
    for pair_id, old in before["pairs"].items():
        new = after["pairs"].get(pair_id, {})
        lines.append(
            f"  {pair_id} fit {old['fit']:5.1f} -> {new.get('fit', float('nan')):5.1f} | "
            f"tfidf {old['tfidf_cosine']:.4f} -> {new.get('tfidf_cosine', float('nan')):.4f} | "
            f"emb {old['embedding_coverage']:.4f} -> {new.get('embedding_coverage', float('nan')):.4f} | "
            f"skills {old['skill_coverage_percent']:5.1f} -> {new.get('skill_coverage_percent', float('nan')):5.1f} | "
            f"ats {old['ats']} -> {new.get('ats')}  ({old['notes']})"
        )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("out", nargs="?", type=Path, help="where to write a snapshot of the current code")
    parser.add_argument("--compare", nargs=2, type=Path, metavar=("BEFORE", "AFTER"))
    args = parser.parse_args(argv)
    if args.compare:
        before, after = (json.loads(p.read_text(encoding="utf-8")) for p in args.compare)
        print(compare(before, after))
        return 0
    if not args.out:
        parser.error("give an output path or --compare BEFORE AFTER")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(snapshot(), indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"Snapshot written to {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
