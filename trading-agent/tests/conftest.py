from dataclasses import replace

import pytest

from agent.config import RiskConfig
from agent.jev_schema import Finalist
from agent.types import AccountState, BookLevel, Candle, JevDecision, OrderBook


def book(symbol="BTC-PERP", bid=100.0, ask=100.02, recv_ts=1000.0, size=5.0):
    return OrderBook(symbol, tuple(BookLevel(bid - i * 0.01, size) for i in range(5)),
                     tuple(BookLevel(ask + i * 0.01, size) for i in range(5)), recv_ts - 0.05, recv_ts)


def candles(symbol="BTC-PERP", n=300, start=0.0, step=300.0, px=100.0, drift=0.0):
    out = []
    for i in range(n):
        c = px * (1 + drift) ** i * (1 + (0.001 if i % 2 else -0.001))
        out.append(Candle(symbol, start + i * step, start + (i + 1) * step, c, c * 1.001, c * 0.999, c, 10 + i % 7))
    return out


def account(equity=10_000.0, peak=None, day_start=None, positions=None):
    return AccountState(equity, peak or equity, day_start or equity, positions or {})


def jev(**kw) -> JevDecision:
    base = dict(
        regime="trending", regime_probs={"trending": 0.7, "mean_reverting": 0.1, "high_vol": 0.15, "crisis": 0.05},
        direction="long", direction_confidence=0.9, direction_probs={"long": 0.9, "short": 0.04, "neutral": 0.06},
        toxic_flow_prob=0.1, setup_quality=2.5, risk_state="safe", model="jev-test", input_tokens=300, latency_ms=80.0,
    )
    base.update(kw)
    return JevDecision(**base)


@pytest.fixture
def finalist():
    return Finalist("BTC-PERP", "t", "b", "i", verified=True, approved=True)


@pytest.fixture
def risk_cfg(tmp_path):
    return replace(RiskConfig(), kill_switch_path=tmp_path / "KILL")
