"""Thin wrapper over the official TypeSafe SDK. One call per candle per symbol carries all five
questions. Any failure (network, timeout, schema mismatch, missing answer) returns None, and the
loop treats None as HOLD: the reflex failing can never open risk."""

import logging
import time
from typing import Protocol

from typesafe_sdk import AsyncTypeSafeClient, RetryPolicy, SystemOneResponse, TypeSafeError

from agent.jev_schema import QUESTION_SHAPE, JevSchema
from agent.state_engine import Snapshot
from agent.types import JevDecision

log = logging.getLogger(__name__)


class Reflex(Protocol):
    async def decide(self, symbol: str, snapshot: Snapshot) -> JevDecision | None: ...


def parse_response(resp: SystemOneResponse, latency_ms: float) -> JevDecision:
    """Raises KeyError/ValueError on anything unexpected; callers fail closed."""
    choices, scores, nouls = resp.choices, resp.scores, resp.nouls
    for name, (_, labels) in QUESTION_SHAPE.items():
        if name == "setup_quality":
            continue
        if name == "toxic_flow":
            nouls[name]
            continue
        if choices[name].choice not in labels:
            raise ValueError(f"{name}: unexpected label {choices[name].choice!r}")
    quality = scores["setup_quality"].score
    if not 0.0 <= quality <= 3.0:
        raise ValueError(f"setup_quality out of range: {quality}")
    return JevDecision(
        regime=choices["regime"].choice,  # type: ignore[arg-type]
        regime_probs=dict(choices["regime"].probabilities),
        direction=choices["direction"].choice,  # type: ignore[arg-type]
        direction_confidence=choices["direction"].confidence,
        direction_probs=dict(choices["direction"].probabilities),
        toxic_flow_prob=nouls["toxic_flow"].noul,
        setup_quality=quality,
        risk_state=choices["risk_state"].choice,  # type: ignore[arg-type]
        model=resp.model,
        input_tokens=resp.usage.input_tokens,
        latency_ms=latency_ms,
    )


class JevReflex:
    def __init__(self, schema: JevSchema, model: str = "jev-latest", timeout_s: float = 2.0):
        self.schema = schema
        # One retry only: a decision that arrives late is worse than no decision.
        self._client = AsyncTypeSafeClient(model=model, timeout=timeout_s, retry=RetryPolicy(max_retries=1))

    async def decide(self, symbol: str, snapshot: Snapshot) -> JevDecision | None:
        t0 = time.perf_counter()
        try:
            resp = await self._client.system_one(
                state=snapshot.fields, questions=self.schema.build_questions(symbol)
            )
            return parse_response(resp, (time.perf_counter() - t0) * 1e3)
        except (TypeSafeError, KeyError, ValueError) as exc:
            log.warning("jev decision failed for %s, holding: %s", symbol, exc)
            return None
        except Exception:  # fail closed on anything else too; a crash here must not become a trade
            log.exception("unexpected jev failure for %s, holding", symbol)
            return None

    async def aclose(self) -> None:
        await self._client.aclose()
