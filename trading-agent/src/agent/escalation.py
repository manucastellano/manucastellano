"""Escalation to Opus for a deep re-read when the reflex is unsure (confidence < 0.60) or sees
crisis. Opus can only make things safer: its verdict space is hold / reduce / flatten plus a
pause on new entries, and the code caps the pause length. It cannot open or enlarge a position.
Any failure (timeout, refusal, API error) fails closed: no new entries for the cooldown window.

API usage checked against anthropic==1.15.0: messages.parse(output_format=..., output_config=...).
Refusals are not routed to a fallback model on purpose: a refused review should not trade.
"""

import json
import logging
from dataclasses import dataclass, field
from typing import Literal, Protocol

import anthropic
from pydantic import BaseModel, Field

from agent.config import EscalationConfig
from agent.jev_schema import Finalist
from agent.types import JevDecision

log = logging.getLogger(__name__)

MAX_PAUSE_MINUTES = 240

SYSTEM = (
    "You are the risk reviewer for an automated crypto trading system. A fast classifier flagged "
    "this instrument as low-confidence or in crisis. You cannot open or increase positions. Decide "
    "whether to hold the current position, reduce it by half, or flatten it, and whether to pause "
    "new entries. Prefer flatten when the thesis invalidation condition appears met or the market "
    "looks disorderly. Base the decision only on the data given; say what you could not verify."
)


class Verdict(BaseModel):
    action: Literal["hold", "reduce", "flatten"]
    pause_minutes: int = Field(ge=0, description="Minutes to block new entries on this symbol.")
    invalidation_met: bool
    rationale: str


@dataclass(frozen=True)
class EscalationResult:
    verdict: Verdict
    ok: bool  # False when the verdict is the fail-closed default rather than a model answer


FAIL_CLOSED = Verdict(action="hold", pause_minutes=15, invalidation_met=False, rationale="escalation unavailable; fail closed")


class Brain(Protocol):
    def on_cooldown(self, symbol: str, now: float) -> bool: ...
    async def review(self, symbol: str, finalist: Finalist, jev: JevDecision, snap: dict, now: float) -> EscalationResult: ...


def should_escalate(jev: JevDecision | None, cfg: EscalationConfig) -> bool:
    return jev is not None and (jev.direction_confidence < cfg.low_confidence or jev.regime == "crisis")


@dataclass
class OpusBrain:
    cfg: EscalationConfig
    _client: anthropic.AsyncAnthropic = field(default_factory=lambda: anthropic.AsyncAnthropic())
    _last: dict[str, float] = field(default_factory=dict)

    def on_cooldown(self, symbol: str, now: float) -> bool:
        return now - self._last.get(symbol, -1e18) < self.cfg.cooldown_s

    async def review(self, symbol: str, finalist: Finalist, jev: JevDecision, snap: dict, now: float) -> EscalationResult:
        self._last[symbol] = now
        payload = {
            "symbol": symbol,
            "thesis": finalist.thesis,
            "bear_case": finalist.bear_case,
            "invalidation": finalist.invalidation,
            "snapshot": snap,
            "reflex": {
                "regime": jev.regime, "regime_probs": jev.regime_probs,
                "direction": jev.direction, "direction_confidence": jev.direction_confidence,
                "toxic_flow_prob": jev.toxic_flow_prob, "setup_quality": jev.setup_quality,
                "risk_state": jev.risk_state,
            },
        }
        try:
            resp = await self._client.with_options(timeout=self.cfg.timeout_s).messages.parse(
                model=self.cfg.model,
                max_tokens=16000,
                system=SYSTEM,
                messages=[{"role": "user", "content": json.dumps(payload)}],
                output_format=Verdict,
                output_config={"effort": self.cfg.effort},
            )
        except anthropic.APIError as exc:
            log.warning("escalation failed for %s: %s", symbol, exc)
            return EscalationResult(FAIL_CLOSED, ok=False)
        except Exception:  # e.g. output that fails Verdict validation
            log.exception("escalation produced no usable verdict for %s", symbol)
            return EscalationResult(FAIL_CLOSED, ok=False)
        if resp.stop_reason == "refusal" or resp.parsed_output is None:
            log.warning("escalation returned no verdict for %s (stop_reason=%s)", symbol, resp.stop_reason)
            return EscalationResult(FAIL_CLOSED, ok=False)
        v = resp.parsed_output
        v = v.model_copy(update={"pause_minutes": min(v.pause_minutes, MAX_PAUSE_MINUTES)})
        return EscalationResult(v, ok=True)
