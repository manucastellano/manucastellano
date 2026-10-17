"""The live loop. Once per candle close, for every symbol:

  snapshot (code) -> Jev (one typed call, all symbols concurrently)
    -> escalate to Opus if confidence < 0.60 or regime == crisis
    -> policy intent (code gates + Kelly) -> merge with escalation (more conservative wins)
    -> risk check (code, immediately before the order) -> broker -> journal
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone

from agent.broker import Broker
from agent.config import AgentConfig
from agent.escalation import Brain, EscalationResult, should_escalate
from agent.jev_client import Reflex
from agent.jev_schema import JevSchema
from agent.journal import Journal
from agent.policy import Policy
from agent.risk import RiskManager, notional_frac
from agent.state_engine import StateEngine
from agent.types import AccountState, Action, Intent

log = logging.getLogger(__name__)


@dataclass
class AccountTracker:
    peak: float = 0.0
    day_start: float = 0.0
    day: str = ""

    def update(self, equity: float, now: float) -> tuple[float, float]:
        day = datetime.fromtimestamp(now, tz=timezone.utc).strftime("%Y-%m-%d")
        if day != self.day:
            self.day, self.day_start = day, equity
        self.peak = max(self.peak, equity)
        return self.peak, self.day_start


def more_conservative(a: Intent, b: Intent) -> Intent:
    return a if abs(a.target_frac) <= abs(b.target_frac) else b


@dataclass
class TradingAgent:
    cfg: AgentConfig
    schema: JevSchema
    engines: dict[str, StateEngine]
    reflex: Reflex
    brain: Brain | None
    policy: Policy
    risk: RiskManager
    broker: Broker
    journal: Journal
    tracker: AccountTracker = field(default_factory=AccountTracker)
    marks: dict[str, float] = field(default_factory=dict)

    def account(self, now: float) -> AccountState:
        eq = self.broker.equity(self.marks)
        peak, day_start = self.tracker.update(eq, now)
        return AccountState(eq, peak, day_start, self.broker.positions())

    async def step(self, now: float) -> None:
        account = self.account(now)
        snaps = {}
        for sym, eng in self.engines.items():
            snap = eng.snapshot(now, account)
            if snap is None:
                self.journal.write(now, "skip", symbol=sym, reason="no usable book")
                continue
            snaps[sym] = snap
            self.marks[sym] = float(snap.fields["mid"])

        killed = self.risk.killed
        syms = list(snaps)
        if killed:
            decisions = [None] * len(syms)  # do not spend on the reflex; risk will flatten
        else:
            decisions = await asyncio.gather(*(self.reflex.decide(s, snaps[s]) for s in syms))

        for sym, jev in zip(syms, decisions):
            fields = snaps[sym].fields
            finalist = self.schema.finalists[sym]
            current = notional_frac(self.account(now), self.marks, sym)

            esc: EscalationResult | None = None
            if jev and self.brain and should_escalate(jev, self.cfg.escalation) and not self.brain.on_cooldown(sym, now):
                esc = await self.brain.review(sym, finalist, jev, fields, now)
                if esc.verdict.pause_minutes:
                    self.risk.pause(sym, now + esc.verdict.pause_minutes * 60)

            intent = self.policy.decide(sym, finalist, jev, fields, current)
            if esc is not None and esc.verdict.action != "hold":
                esc_target = 0.0 if esc.verdict.action == "flatten" else current / 2
                esc_action = Action.FLATTEN if esc.verdict.action == "flatten" else Action.REDUCE
                intent = more_conservative(intent, Intent(sym, esc_action, esc_target, "opus: " + esc.verdict.rationale[:200]))

            account = self.account(now)
            verdict = self.risk.check_order(intent, account, self.marks, fields, now, jev.risk_state if jev else None)
            fill = None
            if verdict.order is not None:
                fill = self.broker.submit(verdict.order, self.marks[sym], float(fields.get("spr_bps") or 0.0), now)
            self.journal.write(
                now, "decision", symbol=sym, schema=self.schema.version, snapshot=fields, jev=jev,
                escalation=esc, intent=intent, risk=verdict, fill=fill,
            )

    async def run(self, clock, feed) -> None:
        """`feed.pump(engines, until=t)` delivers events received up to t; `clock` yields candle
        close times. Live data feeds are venue-specific and not included (see docs/05-ship.md)."""
        async for now in clock:
            feed.pump(self.engines, until=now)
            try:
                await self.step(now)
            except Exception:
                log.exception("step failed at %s; arming kill switch", now)
                self.risk.arm_kill("unhandled exception in step")
