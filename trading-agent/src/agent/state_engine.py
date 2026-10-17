"""Deterministic state engine: market + account events -> one compact numeric snapshot.

Causality rule: a snapshot built at time `now` may only use events whose *receive* time is
<= now (books, context) or whose candle has closed by now. Events from the future are ignored
when replaying, and the snapshot records the newest timestamp it used so tests can assert it.
All arithmetic happens here, never in the model.
"""

import json
import math
from bisect import bisect_right
from collections import deque
from dataclasses import dataclass

from agent.types import AccountState, Candle, OrderBook

# Conservative heuristic for JSON with many digits (verify against Jev's usage.input_tokens).
CHARS_PER_TOKEN = 3.0
MAX_SNAPSHOT_TOKENS = 400

# Window lengths in candles, assuming 5-minute candles: 1h and 24h.
SHORT_WINDOW = 12
LONG_WINDOW = 288


class SnapshotTooLarge(ValueError):
    pass


@dataclass(frozen=True)
class ContextPoint:
    """Slow external context (funding, open interest), timestamped on receipt."""

    recv_ts: float
    funding_8h: float | None = None
    open_interest: float | None = None


@dataclass(frozen=True)
class Snapshot:
    fields: dict[str, float | int | str | None]
    newest_input_ts: float  # max timestamp of any input used; must be <= fields["t"]

    def to_state(self) -> str:
        return json.dumps(self.fields, separators=(",", ":"), sort_keys=True)

    def est_tokens(self) -> int:
        return math.ceil(len(self.to_state()) / CHARS_PER_TOKEN)


def _log_returns(closes: list[float]) -> list[float]:
    return [math.log(b / a) for a, b in zip(closes, closes[1:]) if a > 0 and b > 0]


def _realized_vol_bps(rets: list[float]) -> float | None:
    if len(rets) < 2:
        return None
    return math.sqrt(sum(r * r for r in rets)) * 1e4


def _rnd(x: float | None, nd: int) -> float | None:
    return None if x is None or math.isnan(x) else round(x, nd)


class StateEngine:
    def __init__(self, symbol: str, depth_levels: int = 5, max_candles: int = LONG_WINDOW + 1):
        self.symbol = symbol
        self.depth_levels = depth_levels
        self._books: deque[OrderBook] = deque(maxlen=256)
        self._candles: list[Candle] = []
        self._max_candles = max_candles
        self._context: list[ContextPoint] = []

    # Ingest. Out-of-order arrival is allowed; selection at snapshot time is what enforces causality.
    def on_book(self, book: OrderBook) -> None:
        if book.symbol != self.symbol:
            raise ValueError(f"book for {book.symbol} sent to engine for {self.symbol}")
        self._books.append(book)

    def on_candle(self, candle: Candle) -> None:
        if candle.symbol != self.symbol:
            raise ValueError(f"candle for {candle.symbol} sent to engine for {self.symbol}")
        idx = bisect_right([c.close_ts for c in self._candles], candle.close_ts)
        self._candles.insert(idx, candle)
        # Keep a margin so replays that look slightly back still have a full window.
        if len(self._candles) > self._max_candles * 2:
            del self._candles[: len(self._candles) - self._max_candles * 2]

    def on_context(self, point: ContextPoint) -> None:
        idx = bisect_right([p.recv_ts for p in self._context], point.recv_ts)
        self._context.insert(idx, point)

    def snapshot(self, now: float, account: AccountState) -> Snapshot | None:
        book = self._latest_book(now)
        if book is None or not book.bids or not book.asks:
            return None
        used = [book.recv_ts]

        bid, ask = book.bids[0].price, book.asks[0].price
        if ask <= bid:
            return None  # crossed/locked book: refuse to describe it rather than guess
        mid = (bid + ask) / 2
        spread_bps = (ask - bid) / mid * 1e4
        bid_depth = sum(l.price * l.size for l in book.bids[: self.depth_levels])
        ask_depth = sum(l.price * l.size for l in book.asks[: self.depth_levels])
        imbalance = (bid_depth - ask_depth) / (bid_depth + ask_depth) if bid_depth + ask_depth > 0 else 0.0

        closed = [c for c in self._candles if c.close_ts <= now][-(LONG_WINDOW + 1):]
        if closed:
            used.append(closed[-1].close_ts)
        closes = [c.close for c in closed]
        rets = _log_returns(closes)
        ret_1 = rets[-1] if rets else None
        ret_short = math.log(closes[-1] / closes[-SHORT_WINDOW - 1]) if len(closes) > SHORT_WINDOW else None
        ret_long = math.log(closes[-1] / closes[0]) if len(closes) > LONG_WINDOW else None
        vols = [c.volume for c in closed]
        vol_z = None
        if len(vols) >= 30:
            mu = sum(vols[:-1]) / (len(vols) - 1)
            sd = math.sqrt(sum((v - mu) ** 2 for v in vols[:-1]) / (len(vols) - 2))
            vol_z = (vols[-1] - mu) / sd if sd > 0 else 0.0

        ctx = [p for p in self._context if p.recv_ts <= now]
        funding = oi_chg = None
        if ctx:
            used.append(ctx[-1].recv_ts)
            funding = ctx[-1].funding_8h
            day_ago = [p for p in ctx if p.recv_ts <= now - 86400 and p.open_interest]
            if ctx[-1].open_interest and day_ago:
                oi_chg = ctx[-1].open_interest / day_ago[-1].open_interest - 1

        pos = account.positions.get(self.symbol)
        qty = pos.qty if pos else 0.0
        inv_frac = qty * mid / account.equity if account.equity > 0 else 0.0
        upnl_bps = (mid / pos.avg_price - 1) * 1e4 * (1 if qty > 0 else -1) if pos and qty and pos.avg_price > 0 else 0.0
        drawdown = 1 - account.equity / account.peak_equity if account.peak_equity > 0 else 0.0
        day_pnl = account.equity / account.day_start_equity - 1 if account.day_start_equity > 0 else 0.0

        fields: dict[str, float | int | str | None] = {
            "s": self.symbol,
            "t": int(now),
            "age_s": _rnd(now - book.recv_ts, 2),
            "mid": _rnd(mid, 6),
            "spr_bps": _rnd(spread_bps, 2),
            "imb": _rnd(imbalance, 3),
            "dep_usd": round(bid_depth + ask_depth),
            "r1_bps": _rnd(ret_1 * 1e4 if ret_1 is not None else None, 1),
            "r1h_bps": _rnd(ret_short * 1e4 if ret_short is not None else None, 1),
            "r24h_bps": _rnd(ret_long * 1e4 if ret_long is not None else None, 1),
            "rv1h_bps": _rnd(_realized_vol_bps(rets[-SHORT_WINDOW:]), 1),
            "rv24h_bps": _rnd(_realized_vol_bps(rets[-LONG_WINDOW:]), 1),
            "vol_z": _rnd(vol_z, 2),
            "fund8h_bps": _rnd(funding * 1e4 if funding is not None else None, 2),
            "oi24h_chg": _rnd(oi_chg, 4),
            "inv": _rnd(inv_frac, 4),
            "upnl_bps": _rnd(upnl_bps, 1),
            "dd": _rnd(drawdown, 4),
            "day_pnl": _rnd(day_pnl, 4),
        }
        snap = Snapshot(fields=fields, newest_input_ts=max(used))
        if snap.newest_input_ts > now:
            raise AssertionError("causality violated: snapshot used an input from the future")
        if snap.est_tokens() > MAX_SNAPSHOT_TOKENS:
            raise SnapshotTooLarge(f"{snap.est_tokens()} est. tokens > {MAX_SNAPSHOT_TOKENS}")
        return snap

    def _latest_book(self, now: float) -> OrderBook | None:
        eligible = [b for b in self._books if b.recv_ts <= now]
        return max(eligible, key=lambda b: b.recv_ts) if eligible else None
