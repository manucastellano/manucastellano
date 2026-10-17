"""Pure functions the nightly review uses: outcome labelling and scoring. Labels use prices that
arrived *after* each decision; that is fine here because grading happens after the fact and the
labels never feed back into a live snapshot."""

import math
from collections import defaultdict
from dataclasses import dataclass

from agent.calibration import brier_binary, brier_multiclass, reliability_table


@dataclass(frozen=True)
class Labelled:
    symbol: str
    ts: float
    direction_probs: dict[str, float]
    chosen: str
    confidence: float
    outcome: str  # long / short / neutral, by realized forward return vs cost band
    fwd_bps: float
    fired: bool  # policy opened or flipped a position on this decision


def label_decisions(records: list[dict], horizon: int, cost_bps: float) -> list[Labelled]:
    by_sym: dict[str, list[dict]] = defaultdict(list)
    for r in records:
        if r.get("kind") == "decision":
            by_sym[r["symbol"]].append(r)
    out: list[Labelled] = []
    for sym, rows in by_sym.items():
        rows.sort(key=lambda r: r["ts"])
        for i, r in enumerate(rows):
            jev = r.get("jev")
            if not jev or i + horizon >= len(rows):
                continue
            p0 = r["snapshot"]["mid"]
            p1 = rows[i + horizon]["snapshot"]["mid"]
            fwd = math.log(p1 / p0) * 1e4
            outcome = "long" if fwd > cost_bps else "short" if fwd < -cost_bps else "neutral"
            action = (r.get("intent") or {}).get("action")
            out.append(Labelled(
                sym, r["ts"], jev["direction_probs"], jev["direction"], jev["direction_confidence"],
                outcome, fwd, action in ("open_long", "open_short"),
            ))
    return out


def score(labelled: list[Labelled]) -> dict:
    if not labelled:
        return {"n": 0}
    p_chosen = [x.direction_probs.get(x.chosen, 0.0) for x in labelled]
    hit = [int(x.chosen == x.outcome) for x in labelled]
    fired = [x for x in labelled if x.fired]
    misses = [
        x for x in labelled
        if not x.fired and x.chosen in ("long", "short") and x.chosen == x.outcome and abs(x.fwd_bps) > 50
    ]
    false_fires = [x for x in fired if x.outcome != x.chosen]
    return {
        "n": len(labelled),
        "brier_direction_multiclass": brier_multiclass([x.direction_probs for x in labelled], [x.outcome for x in labelled]),
        "brier_chosen_correct": brier_binary(p_chosen, hit),
        "hit_rate": sum(hit) / len(hit),
        "mean_confidence": sum(x.confidence for x in labelled) / len(labelled),
        "reliability": reliability_table(p_chosen, hit),
        "fired": len(fired),
        "fired_hit_rate": (sum(x.outcome == x.chosen for x in fired) / len(fired)) if fired else None,
        "misses_gt50bps": len(misses),
        "false_fires": len(false_fires),
    }
