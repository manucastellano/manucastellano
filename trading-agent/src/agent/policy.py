"""Policy: Jev's typed judgement -> an Intent. Gates and sizing are code; Jev only judges.

Entry fires only when ALL hold:
  setup_quality >= 2, direction confidence > 0.80, Jev risk_state == safe, direction != neutral,
  toxic-flow probability <= limit, and the finalist is verified and approved by the operator.

Sizing is binary Kelly in R units (R = distance to the code-set stop):
  win +b R with probability p, lose -1 R otherwise, round-trip cost c R.
  f* = (p*b - (1-p) - c) / b       fraction of equity to put at risk
  f  = kelly_cap_fraction * f*   (quarter Kelly at the default 0.25)
  notional fraction = f / stop_frac
p is Jev's direction probability passed through the calibrator. Until the nightly review has
enough labelled outcomes to fit one, the calibrator halves the claimed edge.
Defensive actions (crisis flatten, Jev 'reduce') are allowed to come from the model because they
only ever lower risk.
"""

from dataclasses import dataclass, field

from agent.calibration import IsotonicCalibrator
from agent.config import CostConfig, PolicyConfig
from agent.jev_schema import Finalist
from agent.types import Action, Intent, JevDecision

# Target distance / stop distance. Kept at 1.0 on purpose: with symmetric barriers a no-skill
# random walk wins 50% of the time, so "Jev's direction was right" and "the trade hit target
# first" share the same 0.5 baseline. With b != 1 the no-skill win rate is 1/(1+b), and feeding a
# direction probability into Kelly would invent edge (p=0.5 looks profitable at b=1.5).
PAYOFF_R = 1.0
STOP_VOL_MULT = 2.0  # stop distance = this * 1h realized vol
MIN_STOP_BPS = 50.0
MIN_REBALANCE_FRAC = 0.01


def kelly_fraction(p: float, b: float, cost_r: float) -> float:
    if b <= 0:
        return 0.0
    return max(0.0, (p * b - (1 - p) - cost_r) / b)


@dataclass
class OpenTrade:
    side: int  # +1 long, -1 short
    stop_bps: float
    target_bps: float


@dataclass
class Policy:
    cfg: PolicyConfig
    cost: CostConfig
    calibrator: IsotonicCalibrator
    trades: dict[str, OpenTrade] = field(default_factory=dict)

    def decide(
        self,
        symbol: str,
        finalist: Finalist,
        jev: JevDecision | None,
        snap: dict,
        current_frac: float,
    ) -> Intent:
        # 1. Code-owned exits come first and do not depend on the model at all.
        exit_intent = self._check_exit(symbol, snap, current_frac)
        if exit_intent:
            return exit_intent
        if jev is None:
            return Intent(symbol, Action.HOLD, current_frac, "no reflex decision; fail closed")

        # 2. Model-originated defensive actions (can only reduce risk).
        if jev.regime == "crisis" and current_frac:
            self.trades.pop(symbol, None)
            return Intent(symbol, Action.FLATTEN, 0.0, "jev regime=crisis")
        if jev.risk_state == "reduce" and current_frac:
            return Intent(symbol, Action.REDUCE, current_frac / 2, "jev risk_state=reduce")

        # 3. Entry gates.
        if not (finalist.verified and finalist.approved):
            return Intent(symbol, Action.HOLD, current_frac, "finalist not verified+approved by operator")
        gates = {
            "setup_quality": jev.setup_quality >= self.cfg.min_setup_quality,
            "confidence": jev.direction_confidence > self.cfg.min_direction_confidence,
            "risk_state": jev.risk_state == "safe",
            "direction": jev.direction != "neutral",
            "toxic_flow": jev.toxic_flow_prob <= self.cfg.max_toxic_flow_prob,
        }
        failed = [k for k, ok in gates.items() if not ok]
        if failed:
            return Intent(symbol, Action.HOLD, current_frac, "gates failed: " + ",".join(failed))

        side = 1 if jev.direction == "long" else -1
        rv = snap.get("rv1h_bps")
        if rv is None:
            return Intent(symbol, Action.HOLD, current_frac, "no volatility estimate yet")
        stop_bps = max(MIN_STOP_BPS, STOP_VOL_MULT * rv)
        cost_bps = 2 * (self.cost.taker_fee_bps + self.cost.slippage_bps) + (snap.get("spr_bps") or 0.0)
        p = self.calibrator(jev.direction_probs.get(jev.direction, 0.0))
        f_star = kelly_fraction(p, PAYOFF_R, cost_bps / stop_bps)
        f_risk = self.cfg.kelly_cap_fraction * f_star  # never more than quarter Kelly
        target = side * f_risk / (stop_bps / 1e4)
        if f_risk <= 0:
            return Intent(symbol, Action.HOLD, current_frac, f"no edge after costs (p={p:.3f})")
        if abs(target - current_frac) < MIN_REBALANCE_FRAC:
            return Intent(symbol, Action.HOLD, current_frac, "already at target")
        self.trades[symbol] = OpenTrade(side, stop_bps, PAYOFF_R * stop_bps)
        action = Action.OPEN_LONG if side > 0 else Action.OPEN_SHORT
        return Intent(symbol, action, target, f"p={p:.3f} f*={f_star:.4f} stop={stop_bps:.0f}bps")

    def _check_exit(self, symbol: str, snap: dict, current_frac: float) -> Intent | None:
        trade = self.trades.get(symbol)
        if trade is None or not current_frac:
            if not current_frac:
                self.trades.pop(symbol, None)
            return None
        upnl = snap.get("upnl_bps") or 0.0
        if upnl <= -trade.stop_bps:
            self.trades.pop(symbol)
            return Intent(symbol, Action.FLATTEN, 0.0, f"stop hit ({upnl:.0f}bps)")
        if upnl >= trade.target_bps:
            self.trades.pop(symbol)
            return Intent(symbol, Action.FLATTEN, 0.0, f"target hit ({upnl:.0f}bps)")
        return None
