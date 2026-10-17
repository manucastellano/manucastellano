"""Plain data types shared across the engine. Timestamps are UTC epoch seconds (float)."""

from dataclasses import dataclass
from enum import Enum
from typing import Literal

Regime = Literal["trending", "mean_reverting", "high_vol", "crisis"]
Direction = Literal["long", "short", "neutral"]
RiskState = Literal["safe", "near_limit", "reduce"]

RISK_SEVERITY: dict[str, int] = {"safe": 0, "near_limit": 1, "reduce": 2}


@dataclass(frozen=True)
class BookLevel:
    price: float
    size: float


@dataclass(frozen=True)
class OrderBook:
    symbol: str
    bids: tuple[BookLevel, ...]  # best first
    asks: tuple[BookLevel, ...]  # best first
    exchange_ts: float  # when the venue stamped it
    recv_ts: float  # when we received it; causality is enforced on this


@dataclass(frozen=True)
class Candle:
    symbol: str
    open_ts: float
    close_ts: float  # a candle is only usable once now >= close_ts
    open: float
    high: float
    low: float
    close: float
    volume: float


@dataclass(frozen=True)
class Position:
    symbol: str
    qty: float = 0.0  # signed: + long, - short
    avg_price: float = 0.0


@dataclass(frozen=True)
class AccountState:
    equity: float
    peak_equity: float
    day_start_equity: float
    positions: dict[str, Position]


@dataclass(frozen=True)
class JevDecision:
    """Typed answers from one Jev call. Raw model output; never trusted for limits."""

    regime: Regime
    regime_probs: dict[str, float]
    direction: Direction
    direction_confidence: float
    direction_probs: dict[str, float]
    toxic_flow_prob: float
    setup_quality: float  # expected score, 0..3
    risk_state: RiskState
    model: str
    input_tokens: int
    latency_ms: float


class Action(str, Enum):
    HOLD = "hold"
    OPEN_LONG = "open_long"
    OPEN_SHORT = "open_short"
    REDUCE = "reduce"
    FLATTEN = "flatten"


@dataclass(frozen=True)
class Intent:
    """What the policy wants. The risk layer may shrink or veto it, never enlarge it."""

    symbol: str
    action: Action
    target_frac: float  # signed target notional / equity
    reason: str


@dataclass(frozen=True)
class Order:
    symbol: str
    qty: float  # signed
    reason: str


@dataclass(frozen=True)
class Fill:
    symbol: str
    qty: float
    price: float
    fee: float
    ts: float
