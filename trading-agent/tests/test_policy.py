from dataclasses import replace

import pytest

from agent.calibration import IsotonicCalibrator
from agent.config import CostConfig, PolicyConfig
from agent.policy import PAYOFF_R, Policy, kelly_fraction
from agent.types import Action
from conftest import jev

SNAP = {"rv1h_bps": 40.0, "spr_bps": 1.0, "upnl_bps": 0.0}


def policy():
    return Policy(PolicyConfig(), CostConfig(), IsotonicCalibrator(shrink=0.5))


def test_all_gates_pass_opens_long_sized_at_most_quarter_kelly(finalist):
    p = policy()
    intent = p.decide("BTC-PERP", finalist, jev(), SNAP, 0.0)
    assert intent.action is Action.OPEN_LONG
    stop = max(50.0, 2 * SNAP["rv1h_bps"]) / 1e4
    cost_r = 2 * (4.5 + 3.0) + 1.0
    prob = 0.5 + 0.5 * (0.9 - 0.5)  # unfitted calibrator halves the edge
    full = kelly_fraction(prob, PAYOFF_R, cost_r / (stop * 1e4))
    assert 0 < intent.target_frac <= 0.25 * full / stop + 1e-12


@pytest.mark.parametrize("override,gate", [
    ({"setup_quality": 1.99}, "setup_quality"),
    ({"direction_confidence": 0.80}, "confidence"),  # must be strictly above 0.80
    ({"risk_state": "near_limit"}, "risk_state"),
    ({"direction": "neutral"}, "direction"),
    ({"toxic_flow_prob": 0.51}, "toxic_flow"),
])
def test_each_gate_blocks_entry(finalist, override, gate):
    intent = policy().decide("BTC-PERP", finalist, jev(**override), SNAP, 0.0)
    assert intent.action is Action.HOLD and gate in intent.reason


def test_no_decision_fails_closed(finalist):
    assert policy().decide("BTC-PERP", finalist, None, SNAP, 0.05).action is Action.HOLD


def test_unapproved_finalist_never_trades(finalist):
    for f in (replace(finalist, approved=False), replace(finalist, verified=False)):
        assert policy().decide("BTC-PERP", f, jev(), SNAP, 0.0).action is Action.HOLD


def test_crisis_flattens_and_reduce_halves(finalist):
    assert policy().decide("BTC-PERP", finalist, jev(regime="crisis"), SNAP, 0.08).target_frac == 0.0
    assert policy().decide("BTC-PERP", finalist, jev(risk_state="reduce"), SNAP, 0.08).target_frac == pytest.approx(0.04)


def test_no_edge_after_costs_holds(finalist):
    weak = jev(direction_probs={"long": 0.55, "short": 0.2, "neutral": 0.25})
    assert policy().decide("BTC-PERP", finalist, weak, SNAP, 0.0).action is Action.HOLD


def test_code_stop_exits_without_the_model(finalist):
    p = policy()
    opened = p.decide("BTC-PERP", finalist, jev(), SNAP, 0.0)
    out = p.decide("BTC-PERP", finalist, None, {**SNAP, "upnl_bps": -81.0}, opened.target_frac)
    assert out.action is Action.FLATTEN and "stop" in out.reason


def test_coin_flip_direction_never_sizes(finalist):
    flip = jev(direction_probs={"long": 0.5, "short": 0.25, "neutral": 0.25})
    assert policy().decide("BTC-PERP", finalist, flip, {**SNAP, "spr_bps": 0.0}, 0.0).action is Action.HOLD


def test_kelly_formula():
    assert kelly_fraction(0.6, 1.0, 0.0) == pytest.approx(0.2)
    assert kelly_fraction(0.5, 1.0, 0.0) == 0.0
    assert kelly_fraction(0.4, 1.0, 0.0) == 0.0  # never negative
