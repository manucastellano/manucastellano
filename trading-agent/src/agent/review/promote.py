"""Operator gate: promote a candidate schema (and optionally a calibrator) to active.

  python -m agent.review.promote --report state/reports/2026-10-17.json [--calibrator FILE]

Refuses unless the report has a replay on at least MIN_REPLAY samples where the candidate's
Brier beats the active schema's by at least MIN_IMPROVEMENT (relative). The previous ACTIVE
name is kept in schemas/ACTIVE.prev for one-step rollback.
"""

import argparse
import json
import shutil
from pathlib import Path

from agent.jev_schema import SCHEMA_DIR, load_schema

MIN_REPLAY = 200
MIN_IMPROVEMENT = 0.02


def check(report: dict) -> str | None:
    rep = report.get("replay")
    if not report.get("candidate") or not rep:
        return "report has no candidate replay"
    if rep["n"] < MIN_REPLAY:
        return f"replay too small ({rep['n']} < {MIN_REPLAY})"
    if rep["brier_candidate"] > rep["brier_active"] * (1 - MIN_IMPROVEMENT):
        return f"candidate Brier {rep['brier_candidate']:.4f} not {MIN_IMPROVEMENT:.0%} better than {rep['brier_active']:.4f}"
    return None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", required=True, type=Path)
    ap.add_argument("--calibrator", type=Path)
    args = ap.parse_args()
    report = json.loads(args.report.read_text())
    problem = check(report)
    if problem:
        raise SystemExit(f"refusing to promote: {problem}")
    cand = Path(report["candidate"])
    load_schema(cand)  # validates shape again
    # Promoted schemas keep the operator's verified/approved flags from the active one.
    active_name = (SCHEMA_DIR / "ACTIVE").read_text().strip()
    active = json.loads((SCHEMA_DIR / active_name).read_text())
    raw = json.loads(cand.read_text())
    raw["finalists"] = active["finalists"]
    dest = SCHEMA_DIR / cand.name
    dest.write_text(json.dumps(raw, indent=2))
    (SCHEMA_DIR / "ACTIVE.prev").write_text(active_name + "\n")
    (SCHEMA_DIR / "ACTIVE").write_text(cand.name + "\n")
    if args.calibrator:
        Path("state").mkdir(exist_ok=True)
        shutil.copy(args.calibrator, Path("state/calibrator.json"))
    print(f"promoted {cand.name} (previous: {active_name}); restart the loop to load it")


if __name__ == "__main__":
    main()
