"""Execution. Only a paper broker is implemented. A live venue adapter is deliberately absent:
it could not be tested from the build environment (outbound network was blocked), and going
live is an operator gate, not a code default."""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

from agent.config import CostConfig
from agent.types import Fill, Order, Position

LIVE_APPROVAL_FILE = Path("state/LIVE_APPROVED")


class Broker(Protocol):
    def positions(self) -> dict[str, Position]: ...
    def equity(self, marks: dict[str, float]) -> float: ...
    def submit(self, order: Order, mark: float, spread_bps: float, ts: float) -> Fill: ...


@dataclass
class PaperBroker:
    """Taker fills at mid +/- half spread +/- slippage, minus a taker fee. Short sales credit cash,
    so equity = cash + sum(qty * mark) for both sides."""

    cash: float
    cost: CostConfig
    _pos: dict[str, Position] = field(default_factory=dict)
    fills: list[Fill] = field(default_factory=list)

    def positions(self) -> dict[str, Position]:
        return {s: p for s, p in self._pos.items() if p.qty}

    def equity(self, marks: dict[str, float]) -> float:
        return self.cash + sum(p.qty * marks[s] for s, p in self._pos.items() if p.qty)

    def submit(self, order: Order, mark: float, spread_bps: float, ts: float) -> Fill:
        side = 1 if order.qty > 0 else -1
        impact_bps = spread_bps / 2 + self.cost.slippage_bps
        price = mark * (1 + side * impact_bps / 1e4)
        fee = abs(order.qty) * price * self.cost.taker_fee_bps / 1e4
        self.cash -= order.qty * price + fee
        old = self._pos.get(order.symbol, Position(order.symbol))
        new_qty = old.qty + order.qty
        if old.qty == 0 or (old.qty > 0) != (new_qty > 0) or new_qty == 0:
            avg = price if new_qty else 0.0  # opened, flipped, or closed
        elif abs(new_qty) > abs(old.qty):
            avg = (old.avg_price * old.qty + price * order.qty) / new_qty  # added
        else:
            avg = old.avg_price  # reduced
        self._pos[order.symbol] = Position(order.symbol, new_qty, avg)
        fill = Fill(order.symbol, order.qty, price, fee, ts)
        self.fills.append(fill)
        return fill


def require_live_approval(schema_version: str) -> None:
    """Both gates must be open: an env flag and an approval file naming the active schema."""
    if os.environ.get("TRADING_AGENT_LIVE") != "1":
        raise PermissionError("live trading disabled: TRADING_AGENT_LIVE != 1")
    if not LIVE_APPROVAL_FILE.exists() or schema_version not in LIVE_APPROVAL_FILE.read_text():
        raise PermissionError(f"live trading not approved for schema {schema_version}")
    raise NotImplementedError("no live venue adapter yet; see docs/05-ship.md")
