import asyncio
import json
from dataclasses import replace

import pytest

from agent.broker import PaperBroker
from agent.calibration import IsotonicCalibrator
from agent.config import AgentConfig, RiskConfig
from agent.escalation import EscalationResult, Verdict
from agent.jev_schema import active_schema_path, load_schema
from agent.journal import Journal
from agent.loop import TradingAgent
from agent.policy import Policy
from agent.review.metrics import label_decisions, score
from agent.risk import RiskManager
from agent.state_engine import StateEngine
from conftest import book, candles, jev

SYM = "BTC-PERP"


class FakeReflex:
    def __init__(self, decisions):
        self.decisions = list(decisions)

    async def decide(self, symbol, snapshot):
        d = self.decisions.pop(0) if self.decisions else None
        if isinstance(d, Exception):
            return None  # what JevReflex does on any error
        return d


class FakeBrain:
    def __init__(self, action="flatten"):
        self.calls = 0
        self.action = action

    def on_cooldown(self, symbol, now):
        return False

    async def review(self, symbol, finalist, jev, snap, now):
        self.calls += 1
        return EscalationResult(Verdict(action=self.action, pause_minutes=30, invalidation_met=True, rationale="r"), ok=True)


def make_agent(tmp_path, decisions, brain=None):
    schema = load_schema(active_schema_path())
    fin = replace(schema.finalists[SYM], verified=True, approved=True)
    schema = replace(schema, finalists={SYM: fin})
    cfg = AgentConfig(journal_dir=tmp_path / "journal")
    eng = StateEngine(SYM)
    for c in candles(n=300):
        eng.on_candle(c)
    return TradingAgent(
        cfg=cfg, schema=schema, engines={SYM: eng}, reflex=FakeReflex(decisions), brain=brain,
        policy=Policy(cfg.policy, cfg.cost, IsotonicCalibrator()),
        risk=RiskManager(replace(RiskConfig(), kill_switch_path=tmp_path / "KILL")),
        broker=PaperBroker(cash=10_000.0, cost=cfg.cost), journal=Journal(cfg.journal_dir),
    )


def run_steps(agent, times, mids):
    async def go():
        for t, m in zip(times, mids):
            agent.engines[SYM].on_book(book(bid=m - 0.01, ask=m + 0.01, recv_ts=t - 0.5))
            await agent.step(t)
    asyncio.run(go())


def test_entry_then_escalation_flattens(tmp_path):
    brain = FakeBrain("flatten")
    agent = make_agent(tmp_path, [jev(), jev(direction_confidence=0.4, direction="neutral")], brain)
    run_steps(agent, [90_000.0, 90_300.0], [100.0, 100.1])
    assert brain.calls == 1
    assert agent.broker.positions() == {}
    assert len(agent.broker.fills) == 2 and agent.broker.fills[0].qty > 0 and agent.broker.fills[1].qty < 0
    # The escalation pause blocks a re-entry on the next candle even with a perfect signal.
    agent.reflex.decisions = [jev()]
    run_steps(agent, [90_600.0], [100.2])
    assert agent.broker.positions() == {}


def test_reflex_failure_never_trades(tmp_path):
    agent = make_agent(tmp_path, [RuntimeError("down")] * 3)
    run_steps(agent, [90_000.0, 90_300.0, 90_600.0], [100.0, 100.0, 100.0])
    assert agent.broker.fills == []


def test_kill_switch_skips_reflex_and_flattens(tmp_path):
    agent = make_agent(tmp_path, [jev()])
    run_steps(agent, [90_000.0], [100.0])
    assert agent.broker.positions()
    (tmp_path / "KILL").write_text("operator")
    agent.reflex.decisions = [jev()]
    run_steps(agent, [90_300.0], [100.0])
    assert agent.broker.positions() == {}
    assert agent.reflex.decisions, "reflex should not be called while killed"


def test_journal_feeds_nightly_scoring(tmp_path):
    n = 30
    agent = make_agent(tmp_path, [jev(direction="neutral", direction_confidence=0.5)] * n)
    times = [90_000.0 + 300 * i for i in range(n)]
    run_steps(agent, times, [100.0 * (1.002 ** i) for i in range(n)])
    rows = [json.loads(l) for p in (tmp_path / "journal").glob("*.jsonl") for l in p.read_text().splitlines()]
    labelled = label_decisions(rows, horizon=12, cost_bps=15.0)
    assert len(labelled) == n - 12
    s = score(labelled)
    assert s["n"] == n - 12 and all(x.outcome == "long" for x in labelled)
    assert s["hit_rate"] == 0.0  # it kept saying neutral during a steady rise
    assert s["brier_direction_multiclass"] > 0
