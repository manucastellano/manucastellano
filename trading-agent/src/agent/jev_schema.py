"""Versioned Jev decision schema.

The *shape* is fixed in code: five questions, their primitive types and their label sets.
Only the *wording* (instructions and criteria descriptions, plus per-finalist thesis context)
lives in versioned JSON under schemas/, and that is all the nightly review may rewrite.
`validate_schema` rejects any version that changes shape, so a rewritten schema can never
change what the policy code reads.

Wire format verified against typesafe-sdk 0.7.5 (POST /v1/systemone): Choice -> choice,
confidence, probabilities; Score -> expected score, confidence, per-level probabilities;
Noul -> probability of yes.
"""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from typesafe_sdk import Choice, Noul, Score

SCHEMA_DIR = Path(__file__).resolve().parents[2] / "schemas"

QUESTION_SHAPE: dict[str, tuple[str, tuple[str, ...]]] = {
    "regime": ("choice", ("trending", "mean_reverting", "high_vol", "crisis")),
    "direction": ("choice", ("long", "short", "neutral")),
    "toxic_flow": ("noul", ()),
    "setup_quality": ("score", ("0", "1", "2", "3")),
    "risk_state": ("choice", ("safe", "near_limit", "reduce")),
}


class SchemaError(ValueError):
    pass


@dataclass(frozen=True)
class Finalist:
    symbol: str
    thesis: str
    bear_case: str
    invalidation: str
    verified: bool  # research metrics checked against primary sources by the operator
    approved: bool  # operator approved for live/paper trading


@dataclass(frozen=True)
class JevSchema:
    version: str
    questions: dict[str, dict[str, Any]]
    finalists: dict[str, Finalist]

    def build_questions(self, symbol: str) -> dict[str, Choice | Score | Noul]:
        """All five questions for one symbol, sent together in a single Jev call."""
        fin = self.finalists[symbol]
        context = (
            f"Instrument {symbol}. Thesis: {fin.thesis} Bear case: {fin.bear_case} "
            f"Invalidation: {fin.invalidation} The state is a numeric market snapshot; "
            "judge only what it supports."
        )
        out: dict[str, Choice | Score | Noul] = {}
        for name, (kind, labels) in QUESTION_SHAPE.items():
            q = self.questions[name]
            instructions = f"{q['instructions']} {context}"
            if kind == "choice":
                out[name] = Choice(instructions=instructions, criteria={l: q["criteria"][l] for l in labels})
            elif kind == "score":
                out[name] = Score(instructions=instructions, criteria=[q["criteria"][l] for l in labels])
            else:
                out[name] = Noul(instructions=instructions, criteria={"true": q["criteria"]["true"], "false": q["criteria"]["false"]})
        return out


def validate_schema(raw: dict[str, Any]) -> None:
    if not isinstance(raw.get("version"), str) or not raw["version"]:
        raise SchemaError("missing version")
    qs = raw.get("questions", {})
    if set(qs) != set(QUESTION_SHAPE):
        raise SchemaError(f"questions must be exactly {sorted(QUESTION_SHAPE)}")
    for name, (kind, labels) in QUESTION_SHAPE.items():
        q = qs[name]
        if not isinstance(q.get("instructions"), str) or not q["instructions"].strip():
            raise SchemaError(f"{name}: empty instructions")
        crit = q.get("criteria", {})
        expected = set(labels) if kind != "noul" else {"true", "false"}
        if set(crit) != expected:
            raise SchemaError(f"{name}: criteria keys {sorted(crit)} != {sorted(expected)}")
        if not all(isinstance(v, str) and v.strip() for v in crit.values()):
            raise SchemaError(f"{name}: every criterion needs a description")
    for sym, f in raw.get("finalists", {}).items():
        for key in ("thesis", "bear_case", "invalidation"):
            if not isinstance(f.get(key), str) or not f[key].strip():
                raise SchemaError(f"finalist {sym}: missing {key}")


def load_schema(path: Path) -> JevSchema:
    raw = json.loads(path.read_text())
    validate_schema(raw)
    finalists = {
        sym: Finalist(
            symbol=sym,
            thesis=f["thesis"],
            bear_case=f["bear_case"],
            invalidation=f["invalidation"],
            verified=bool(f.get("verified", False)),
            approved=bool(f.get("approved", False)),
        )
        for sym, f in raw.get("finalists", {}).items()
    }
    return JevSchema(version=raw["version"], questions=raw["questions"], finalists=finalists)


def active_schema_path() -> Path:
    """The schema in use is whatever schemas/ACTIVE names; only an operator edits that file."""
    name = (SCHEMA_DIR / "ACTIVE").read_text().strip()
    return SCHEMA_DIR / name
