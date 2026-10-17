from dataclasses import replace

import pytest

from agent.risk import RiskManager
from agent.types import Action, Intent, Position
from conftest import account

MARKS = {"BTC-PERP": 100.0, "ETH-PERP": 10.0}
SNAP = {"age_s": 0.5, "spr_bps": 2.0}


def long_intent(frac=0.08):
    return Intent("BTC-PERP", Action.OPEN_LONG, frac, "test")


def pos(qty, sym="BTC-PERP"):
    return {sym: Position(sym, qty, 100.0)}


def test_clean_order_passes(risk_cfg):
    v = RiskManager(risk_cfg).check_order(long_intent(), account(), MARKS, SNAP, 0.0)
    assert v.order.qty == pytest.approx(8.0)  # 8% of 10k at 100


def test_kill_switch_file_flattens_and_blocks(risk_cfg):
    risk_cfg.kill_switch_path.write_text("operator\n")
    v = RiskManager(risk_cfg).check_order(long_intent(), account(positions=pos(5)), MARKS, SNAP, 0.0)
    assert v.order.qty == pytest.approx(-5)


def test_max_drawdown_latches_kill_switch(risk_cfg):
    rm = RiskManager(risk_cfg)
    v = rm.check_order(long_intent(), account(equity=8_500, peak=10_000, positions=pos(5)), MARKS, SNAP, 0.0)
    assert v.order.qty == pytest.approx(-5)
    assert risk_cfg.kill_switch_path.exists()
    # Still killed after equity recovers: only an operator can clear it.
    v2 = rm.check_order(long_intent(), account(), MARKS, SNAP, 1.0)
    assert v2.order is None


def test_daily_loss_is_reduce_only(risk_cfg):
    acct = account(equity=9_690, peak=10_000, day_start=10_000, positions=pos(5))
    v = RiskManager(risk_cfg).check_order(long_intent(0.10), acct, MARKS, SNAP, 0.0)
    assert v.order is None  # wanted to add; not allowed
    v = RiskManager(risk_cfg).check_order(Intent("BTC-PERP", Action.REDUCE, 0.02, "x"), acct, MARKS, SNAP, 0.0)
    assert v.order.qty < 0


def test_model_can_tighten_but_not_loosen(risk_cfg):
    # Code says near_limit (drawdown at 70% of the limit); Jev claims safe -> still reduce-only.
    acct = account(equity=8_950, peak=10_000)
    assert RiskManager(risk_cfg).check_order(long_intent(), acct, MARKS, SNAP, 0.0, "safe").order is None
    # Code says safe; Jev says reduce -> reduce-only.
    assert RiskManager(risk_cfg).check_order(long_intent(), account(), MARKS, SNAP, 0.0, "reduce").order is None


def test_position_and_gross_caps(risk_cfg):
    v = RiskManager(risk_cfg).check_order(long_intent(0.5), account(), MARKS, SNAP, 0.0)
    assert v.order.qty == pytest.approx(10.0)  # 10% cap
    # Isolate the gross cap from the near-limit rule (which would otherwise fire first at 66%).
    acct = account(positions={"ETH-PERP": Position("ETH-PERP", 250.0, 10.0)})  # 25% gross already
    v = RiskManager(replace(risk_cfg, near_limit_ratio=1.0)).check_order(long_intent(0.10), acct, MARKS, SNAP, 0.0)
    assert v.order.qty == pytest.approx(5.0) and "gross cap" in v.reason


def test_never_enlarges_intent(risk_cfg):
    v = RiskManager(risk_cfg).check_order(long_intent(0.03), account(), MARKS, SNAP, 0.0)
    assert v.order.qty == pytest.approx(3.0)


@pytest.mark.parametrize("snap", [{"age_s": 10.0, "spr_bps": 2.0}, {"age_s": 0.5, "spr_bps": 40.0}, {"spr_bps": 2.0}])
def test_bad_market_data_is_reduce_only(risk_cfg, snap):
    assert RiskManager(risk_cfg).check_order(long_intent(), account(), MARKS, snap, 0.0).order is None


def test_order_rate_cap_allows_reductions(risk_cfg):
    rm = RiskManager(replace(risk_cfg, max_orders_per_hour=2))
    for i in range(2):
        assert rm.check_order(long_intent(0.01 * (i + 1)), account(), MARKS, SNAP, float(i)).order
    assert rm.check_order(long_intent(0.05), account(), MARKS, SNAP, 3.0).order is None
    v = rm.check_order(Intent("BTC-PERP", Action.REDUCE, 0.0, "x"), account(positions=pos(2)), MARKS, SNAP, 4.0)
    assert v.order is not None


def test_pause_blocks_new_entries(risk_cfg):
    rm = RiskManager(risk_cfg)
    rm.pause("BTC-PERP", 100.0)
    assert rm.check_order(long_intent(), account(), MARKS, SNAP, 50.0).order is None
    assert rm.check_order(long_intent(), account(), MARKS, SNAP, 150.0).order is not None
