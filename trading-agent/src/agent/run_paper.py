"""Paper trading entry point over recorded data.

  TYPESAFE_API_KEY=... ANTHROPIC_API_KEY=... python -m agent.run_paper --data data/replay.jsonl

The replay file is JSONL with one event per line, each carrying the time we *received* it:
  {"type":"book","symbol":"BTC-PERP","recv_ts":...,"exchange_ts":...,"bids":[[p,s],...],"asks":[[p,s],...]}
  {"type":"candle","symbol":"BTC-PERP","open_ts":...,"close_ts":...,"o":...,"h":...,"l":...,"c":...,"v":...}
  {"type":"context","symbol":"BTC-PERP","recv_ts":...,"funding_8h":...,"open_interest":...}
A live feed is venue-specific and not included; it must deliver the same three event types.
"""

import argparse
import asyncio
import json
from pathlib import Path

from agent.broker import PaperBroker
from agent.calibration import IsotonicCalibrator
from agent.config import AgentConfig
from agent.escalation import OpusBrain
from agent.jev_client import JevReflex
from agent.jev_schema import active_schema_path, load_schema
from agent.journal import Journal
from agent.loop import TradingAgent
from agent.policy import Policy
from agent.risk import RiskManager
from agent.state_engine import ContextPoint, StateEngine
from agent.types import BookLevel, Candle, OrderBook


class ReplayFeed:
    def __init__(self, path: Path):
        self.events = sorted((json.loads(l) for l in path.read_text().splitlines() if l.strip()), key=self._t)
        self._i = 0

    @staticmethod
    def _t(e: dict) -> float:
        return e["close_ts"] if e["type"] == "candle" else e["recv_ts"]

    def pump(self, engines: dict[str, StateEngine], until: float) -> None:
        while self._i < len(self.events) and self._t(self.events[self._i]) <= until:
            e = self.events[self._i]
            self._i += 1
            eng = engines.get(e["symbol"])
            if eng is None:
                continue
            if e["type"] == "book":
                eng.on_book(OrderBook(e["symbol"], tuple(BookLevel(p, s) for p, s in e["bids"]),
                                      tuple(BookLevel(p, s) for p, s in e["asks"]), e["exchange_ts"], e["recv_ts"]))
            elif e["type"] == "candle":
                eng.on_candle(Candle(e["symbol"], e["open_ts"], e["close_ts"], e["o"], e["h"], e["l"], e["c"], e["v"]))
            elif e["type"] == "context":
                eng.on_context(ContextPoint(e["recv_ts"], e.get("funding_8h"), e.get("open_interest")))

    def candle_closes(self, step: int) -> list[float]:
        closes = sorted({e["close_ts"] for e in self.events if e["type"] == "candle"})
        return [t for t in closes if int(t) % step == 0] or closes


async def _clock(times: list[float]):
    for t in times:
        yield t


def build_agent(cfg: AgentConfig, starting_cash: float) -> TradingAgent:
    schema = load_schema(active_schema_path())
    return TradingAgent(
        cfg=cfg,
        schema=schema,
        engines={s: StateEngine(s) for s in schema.finalists},
        reflex=JevReflex(schema, model=cfg.jev_model, timeout_s=cfg.jev_timeout_s),
        brain=OpusBrain(cfg.escalation),
        policy=Policy(cfg.policy, cfg.cost, IsotonicCalibrator.load(Path("state/calibrator.json"), cfg.policy.default_probability_shrink)),
        risk=RiskManager(cfg.risk),
        broker=PaperBroker(cash=starting_cash, cost=cfg.cost),
        journal=Journal(cfg.journal_dir),
    )


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True, type=Path)
    ap.add_argument("--cash", type=float, default=10_000.0)
    args = ap.parse_args()
    cfg = AgentConfig()
    agent = build_agent(cfg, args.cash)
    feed = ReplayFeed(args.data)
    asyncio.run(agent.run(_clock(feed.candle_closes(cfg.candle_seconds)), feed))
    print(f"final equity {agent.broker.equity(agent.marks):.2f}; fills {len(agent.broker.fills)}")


if __name__ == "__main__":
    main()
