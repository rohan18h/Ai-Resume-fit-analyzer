"""Derive the duty-similarity cut-offs from the eval corpus instead of picking them: RESP_SIM_FLOOR / RESP_SIM_FULL
(embeddings) and RESP_OVERLAP_FLOOR / RESP_OVERLAP_FULL (the word-overlap fallback used without the model).

Run from backend/:  python eval/calibrate.py           (prints the values and writes eval/calibration.json)

For every pair, each JD duty is compared with the resume's Experience/Projects bullets exactly as the app does
(scoring.match_responsibilities), and the best cosine per duty is kept. The pairs fall into two groups by how the
dataset was built (eval/make_dataset.py and the "notes" in pairs.json), not by hand labels:

    same-role pairs     resume and JD for the same job                  p01-p08
    cross-field pairs   resume from a clearly different field          p13-p16

    floor = 95th percentile of cross-field duty similarities  -> a duty this close to an unrelated resume earns 0
    full  = median of same-role duty similarities              -> a duty as close as a typical same-role match
                                                                  earns full credit

Credit in between is linear. Both groups are synthetic and small (see printed counts), and the same pairs are
used by eval/evaluate.py, so treat these values as a documented starting point: rerun this script when the
corpus grows or real hand labels exist.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from app.services import matcher_embed  # noqa: E402
from app.services.parser import clean_text_light, extract_text, strip_name_header  # noqa: E402
from app.services.scoring import evidence_lines, match_responsibilities, responsibility_lines  # noqa: E402
from app.services.sections import jd_lines, resume_sections  # noqa: E402

EVAL_DIR = BACKEND_DIR / "eval"
SAME_ROLE = [f"p{n:02d}" for n in range(1, 9)]
CROSS_FIELD = ["p13", "p14", "p15", "p16"]
FLOOR_PERCENTILE = 95
FULL_PERCENTILE = 50


def duty_similarities(pair: dict, use_embeddings: bool = True) -> list[float]:
    resume = clean_text_light(strip_name_header(extract_text((EVAL_DIR / pair["resume_file"]).read_bytes()).text))
    jd = clean_text_light((EVAL_DIR / pair["jd_file"]).read_text(encoding="utf-8"))
    duties = responsibility_lines(jd_lines(jd))
    evidence = evidence_lines(resume_sections(resume))
    return [m.similarity for m in match_responsibilities(duties, evidence, use_embeddings=use_embeddings)]


def calibrate() -> dict:
    if not matcher_embed.try_load_model():
        raise SystemExit("The embedding model could not be loaded.")
    pairs = {p["id"]: p for p in json.loads((EVAL_DIR / "pairs.json").read_text(encoding="utf-8"))}
    result: dict = {
        "model": matcher_embed.config.EMBEDDING_MODEL,
        "same_role_pairs": SAME_ROLE, "cross_field_pairs": CROSS_FIELD,
        "rule": f"floor = P{FLOOR_PERCENTILE} of cross-field duty similarities; full = P{FULL_PERCENTILE} of same-role",
    }  # fmt: skip
    for method, prefix in ((True, "RESP_SIM"), (False, "RESP_OVERLAP")):
        same = [s for pid in SAME_ROLE for s in duty_similarities(pairs[pid], method)]
        cross = [s for pid in CROSS_FIELD for s in duty_similarities(pairs[pid], method)]
        floor = round(float(np.percentile(cross, FLOOR_PERCENTILE)), 3)
        full = round(float(np.percentile(same, FULL_PERCENTILE)), 3)
        if full <= floor:
            raise SystemExit(f"{prefix}: same-role P{FULL_PERCENTILE} {full} is not above cross-field "
                             f"P{FLOOR_PERCENTILE} {floor}, so the cut-offs are unusable.")
        result[prefix.lower()] = {
            "same_role_duties": len(same), "cross_field_duties": len(cross),
            "same_role": {p: round(float(np.percentile(same, p)), 3) for p in (5, 25, 50, 75, 95)},
            "cross_field": {p: round(float(np.percentile(cross, p)), 3) for p in (5, 25, 50, 75, 95)},
        }  # fmt: skip
        result[f"{prefix}_FLOOR"], result[f"{prefix}_FULL"] = floor, full
    return result


def main() -> int:
    result = calibrate()
    out = EVAL_DIR / "calibration.json"
    out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(result, indent=2))
    print(f"Written to {out}. Copy the four RESP_* values into app/config.py if they changed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
