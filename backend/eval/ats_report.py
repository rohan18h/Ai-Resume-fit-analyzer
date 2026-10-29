"""ATS formatting report for one or more PDFs: every check, its evidence, points and share of the final score.

Run from backend/:  python eval/ats_report.py path/to/resume.pdf [more.pdf ...] [--json]

It calls the same functions as POST /api/analyze (parser.extract_text, then ats.check_ats), on this machine only:
nothing is uploaded or stored. Use it to see exactly why a resume gets its ATS score:

    points        pass 1, warn 0.5, fail 0; "na" (not checked) earns nothing and is left out
    denominator   number of applicable checks
    score         round(100 * sum(points) / denominator)
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from app.services.ats import check_ats  # noqa: E402
from app.services.parser import ParserError, extract_text  # noqa: E402


def report(path: Path) -> dict:
    pdf = path.read_bytes()
    try:
        parsed = extract_text(pdf)
    except ParserError as exc:
        return {"file": path.name, "error": exc.code, "detail": str(exc)}
    result = check_ats(pdf, parsed)
    applicable = [c for c in result.checks if c.status != "na"]
    points = sum(c.credit for c in applicable)
    return {
        "file": path.name,
        "pages": parsed.pages,
        "extracted_chars": len(parsed.text),
        "checks": [
            {
                "id": c.id, "status": c.status, "points": c.credit, "evidence": c.detail,
                "share_of_score": round(100 * c.credit / len(applicable), 1) if c.credit is not None else None,
            }
            for c in result.checks
        ],  # fmt: skip
        "points": points,
        "denominator": len(applicable),
        "score": result.score,
        "formula": f"round(100 * {points:g} / {len(applicable)}) = {result.score}",
    }


def print_report(data: dict) -> None:
    print(f"\n{data['file']}")
    if "error" in data:
        print(f"  rejected before the ATS checks: {data['error']} ({data['detail']})")
        return
    print(f"  pages {data['pages']}, extracted characters {data['extracted_chars']}")
    for check in data["checks"]:
        points = "  -" if check["points"] is None else f"{check['points']:3g}"
        print(f"  {check['id']:18} {check['status']:5} points {points}  {check['evidence']}")
    print(f"  score {data['formula']}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("pdfs", nargs="+", type=Path)
    parser.add_argument("--json", action="store_true", help="print JSON instead of a table")
    args = parser.parse_args(argv)
    reports = [report(path) for path in args.pdfs]
    if args.json:
        print(json.dumps(reports, indent=2))
    else:
        for data in reports:
            print_report(data)
    return 0


if __name__ == "__main__":
    sys.exit(main())
