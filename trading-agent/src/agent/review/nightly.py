"""Nightly review. Crypto trades 24/7, so "before the next open" means before the next UTC day.

  python -m agent.review.nightly --day 2026-10-17 [--draft] [--replay]

1. Label every decision in the journal window with its realized forward move.
2. Score calibration: multiclass Brier on direction, binary Brier on the chosen label,
   reliability table, fires vs misses.
3. Fit a candidate calibrator (sizing input) on the rolling window.
4. --draft:  ask Opus to reword the schema given the scores and worst errors; the draft must
   pass validate_schema (shape locked) and lands in schemas/candidates/.
5. --replay: re-ask Jev with the candidate schema on held-out snapshots and compare Brier.
6. Write reports/<day>.json. Nothing is activated here: promotion is `agent.review.promote`,
   run by the operator (or by the AgenKit ship gate) after reading the report.
"""

import argparse
import asyncio
import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import anthropic
from pydantic import BaseModel

from agent.calibration import IsotonicCalibrator, brier_multiclass
from agent.config import AgentConfig
from agent.jev_schema import SCHEMA_DIR, JevSchema, active_schema_path, load_schema, validate_schema
from agent.journal import Journal
from agent.review.metrics import Labelled, label_decisions, score

WINDOW_DAYS = 30
REPORTS = Path("state/reports")
CANDIDATES = SCHEMA_DIR / "candidates"


class QuestionWording(BaseModel):
    instructions: str
    criteria: dict[str, str]


class SchemaDraft(BaseModel):
    regime: QuestionWording
    direction: QuestionWording
    toxic_flow: QuestionWording
    setup_quality: QuestionWording
    risk_state: QuestionWording
    changelog: str


def load_window(journal: Journal, day: date, days: int) -> list[dict]:
    rows: list[dict] = []
    for k in range(days - 1, -1, -1):
        rows.extend(journal.read_day((day - timedelta(days=k)).isoformat()))
    return rows


def utc_day(ts: float) -> date:
    return datetime.fromtimestamp(ts, tz=timezone.utc).date()


def worst_errors(labelled: list[Labelled], k: int = 15) -> list[dict]:
    wrong = [x for x in labelled if x.chosen != x.outcome]
    wrong.sort(key=lambda x: x.confidence, reverse=True)
    return [{"symbol": x.symbol, "ts": x.ts, "chosen": x.chosen, "conf": round(x.confidence, 3),
             "outcome": x.outcome, "fwd_bps": round(x.fwd_bps, 1)} for x in wrong[:k]]


def draft_schema(active: dict, metrics: dict, errors: list[dict], model: str) -> dict | None:
    client = anthropic.Anthropic()
    prompt = {
        "task": "Rewrite the wording of this Jev decision schema to improve calibration. Keep every "
                "question name and every criteria key exactly as they are; only change text. Prefer "
                "wording that makes the model choose neutral / low setup quality when evidence is thin.",
        "active_schema": {"version": active["version"], "questions": active["questions"]},
        "metrics": {k: v for k, v in metrics.items() if k != "reliability"},
        "reliability": metrics.get("reliability"),
        "highest_confidence_errors": errors,
    }
    resp = client.messages.parse(
        model=model, max_tokens=16000,
        messages=[{"role": "user", "content": json.dumps(prompt)}],
        output_format=SchemaDraft, output_config={"effort": "high"},
    )
    if resp.stop_reason == "refusal" or resp.parsed_output is None:
        return None
    d = resp.parsed_output
    n = int(active["version"].lstrip("v")) + 1
    candidate = {
        **active,
        "version": f"v{n}",
        "notes": f"Nightly draft from {active['version']}: {d.changelog}",
        "questions": {name: getattr(d, name).model_dump() for name in active["questions"]},
    }
    validate_schema(candidate)  # raises if Opus changed the shape
    return candidate


async def replay(schema: JevSchema, rows: list[dict], model: str) -> list[dict[str, float]]:
    from agent.jev_client import JevReflex
    from agent.state_engine import Snapshot

    reflex = JevReflex(schema, model=model, timeout_s=10.0)
    try:
        out = []
        for r in rows:
            d = await reflex.decide(r["symbol"], Snapshot(r["snapshot"], r["ts"]))
            out.append(d.direction_probs if d else {})
        return out
    finally:
        await reflex.aclose()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--day", default=(date.today() - timedelta(days=1)).isoformat())
    ap.add_argument("--draft", action="store_true", help="ask Opus for a candidate schema")
    ap.add_argument("--replay", action="store_true", help="re-score candidate vs active with Jev (costs API calls)")
    args = ap.parse_args()

    cfg = AgentConfig()
    day = date.fromisoformat(args.day)
    journal = Journal(cfg.journal_dir)
    cost_bps = 2 * (cfg.cost.taker_fee_bps + cfg.cost.slippage_bps)

    window = label_decisions(load_window(journal, day, WINDOW_DAYS), cfg.label_horizon_candles, cost_bps)
    today = [x for x in window if utc_day(x.ts) == day]
    history = [x for x in window if utc_day(x.ts) != day]  # the drafter only sees this
    report: dict = {"day": args.day, "today": score(today), "window_30d": score(window)}

    cal = IsotonicCalibrator(shrink=cfg.policy.default_probability_shrink)
    fitted = cal.fit([x.direction_probs.get(x.chosen, 0.0) for x in window], [int(x.chosen == x.outcome) for x in window])
    report["calibrator_fitted"] = fitted
    if fitted:
        cal.save(Path("state/candidates") / f"calibrator_{args.day}.json")

    active_path = active_schema_path()
    active_raw = json.loads(active_path.read_text())
    if args.draft and len(history) >= 50:
        cand = draft_schema(active_raw, score(history), worst_errors(history), cfg.escalation.model)
        if cand:
            CANDIDATES.mkdir(parents=True, exist_ok=True)
            cand_path = CANDIDATES / f"jev_schema_{cand['version']}.json"
            cand_path.write_text(json.dumps(cand, indent=2))
            report["candidate"] = str(cand_path)
            if args.replay:
                # Held out: the drafter saw only earlier days; score both schemas on today.
                rows = [r for r in journal.read_day(args.day) if r.get("kind") == "decision" and r.get("jev")]
                labels = {(x.symbol, x.ts): x.outcome for x in today}
                rows = [r for r in rows if (r["symbol"], r["ts"]) in labels]
                if rows:
                    y = [labels[(r["symbol"], r["ts"])] for r in rows]
                    new = asyncio.run(replay(load_schema(cand_path), rows, cfg.jev_model))
                    keep = [i for i, p in enumerate(new) if p]  # drop failed replays from both sides
                    if keep:
                        report["replay"] = {
                            "n": len(keep),
                            "failed": len(rows) - len(keep),
                            "brier_active": brier_multiclass([rows[i]["jev"]["direction_probs"] for i in keep], [y[i] for i in keep]),
                            "brier_candidate": brier_multiclass([new[i] for i in keep], [y[i] for i in keep]),
                        }

    REPORTS.mkdir(parents=True, exist_ok=True)
    (REPORTS / f"{args.day}.json").write_text(json.dumps(report, indent=2, default=str))
    print(json.dumps({k: v for k, v in report.items() if k != "window_30d"}, indent=2, default=str))


if __name__ == "__main__":
    main()
