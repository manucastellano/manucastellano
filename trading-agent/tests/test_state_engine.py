import pytest

from agent.state_engine import MAX_SNAPSHOT_TOKENS, ContextPoint, StateEngine
from agent.types import BookLevel, OrderBook, Position
from conftest import account, book, candles


def make_engine(now=90_000.0):
    eng = StateEngine("BTC-PERP")
    for c in candles(n=300):
        eng.on_candle(c)
    eng.on_book(book(recv_ts=now - 1))
    eng.on_context(ContextPoint(now - 90_000, 0.0001, 1e9))
    eng.on_context(ContextPoint(now - 10, 0.0002, 1.1e9))
    return eng


def test_basic_fields():
    snap = make_engine().snapshot(90_000.0, account())
    f = snap.fields
    assert f["mid"] == pytest.approx(100.01)
    assert f["spr_bps"] == pytest.approx(0.02 / 100.01 * 1e4, abs=0.01)
    assert -1 <= f["imb"] <= 1
    assert f["rv1h_bps"] is not None and f["rv24h_bps"] is not None
    assert f["oi24h_chg"] == pytest.approx(0.1, abs=1e-4)
    assert f["fund8h_bps"] == pytest.approx(2.0)


def test_under_token_budget_with_every_field_populated():
    acct = account(equity=9_000, peak=10_000, day_start=9_500, positions={"BTC-PERP": Position("BTC-PERP", 3.0, 99.0)})
    snap = make_engine().snapshot(90_000.0, acct)
    assert all(v is not None for v in snap.fields.values())
    assert snap.est_tokens() <= MAX_SNAPSHOT_TOKENS


def test_future_events_are_never_used():
    now = 50_000.0
    eng = StateEngine("BTC-PERP")
    for c in candles(n=300):  # closes run to 90_000, most of them after `now`
        eng.on_candle(c)
    eng.on_book(book(bid=100, ask=100.02, recv_ts=now - 2))
    eng.on_book(book(bid=500, ask=500.1, recv_ts=now + 1))  # arrives after now
    eng.on_context(ContextPoint(now + 5, 0.01, 1e9))
    snap = eng.snapshot(now, account())
    assert snap.newest_input_ts <= now
    assert snap.fields["mid"] == pytest.approx(100.01)
    assert snap.fields["fund8h_bps"] is None
    # Only candles closed by `now` count: 50_000 / 300 = 166 closed, so no 24h window yet.
    assert snap.fields["r24h_bps"] is None


def test_same_snapshot_regardless_of_arrival_order():
    now = 60_000.0
    a, b = StateEngine("BTC-PERP"), StateEngine("BTC-PERP")
    cs = candles(n=300)
    for c in cs:
        a.on_candle(c)
    for c in reversed(cs):
        b.on_candle(c)
    for e in (a, b):
        e.on_book(book(recv_ts=now - 1))
    assert a.snapshot(now, account()).fields == b.snapshot(now, account()).fields


def test_crossed_or_missing_book_gives_no_snapshot():
    eng = StateEngine("BTC-PERP")
    assert eng.snapshot(10.0, account()) is None
    eng.on_book(OrderBook("BTC-PERP", (BookLevel(101, 1),), (BookLevel(100, 1),), 1.0, 1.0))
    assert eng.snapshot(10.0, account()) is None


def test_rejects_other_symbols():
    with pytest.raises(ValueError):
        StateEngine("BTC-PERP").on_book(book(symbol="ETH-PERP"))
