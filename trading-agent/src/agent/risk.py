"""Hard, deterministic risk layer. The model never sees or sets these limits.

check_order() runs immediately before every order and can only shrink or veto an intent,
never enlarge it. Order of checks:
  1. kill switch (file on disk or latched in memory) -> flatten-only
  2. max drawdown from peak equity -> latch kill switch, flatten everything
  3. max daily loss -> reduce-only until the next UTC day
  4. code-computed risk state (plus Jev's, whichever is stricter) not safe -> reduce-only
  5. stale snapshot / wide spread -> reduce-only
  6. per-symbol and gross exposure caps
  7. order-rate cap
"""

import time
from collections import deque
from dataclasses import dataclass, field

from agent.config import RiskConfig
from agent.types import RISK_SEVERITY, AccountState, Intent, Order, RiskState


@dataclass(frozen=True)
class RiskVerdict:
    order: Order | None
    reason: str
    risk_state: RiskState


def notional_frac(account: AccountState, marks: dict[str, float], symbol: str) -> float:
    pos = account.positions.get(symbol)
    if not pos or not pos.qty or account.equity <= 0:
        return 0.0
    return pos.qty * marks[symbol] / account.equity


@dataclass
class RiskManager:
    cfg: RiskConfig
    _killed: bool = False
    _kill_reason: str = ""
    _order_times: deque[float] = field(default_factory=deque)
    _paused_until: dict[str, float] = field(default_factory=dict)

    # Kill switch -----------------------------------------------------------------------------
    @property
    def killed(self) -> bool:
        return self._killed or self.cfg.kill_switch_path.exists()

    def arm_kill(self, reason: str) -> None:
        """Latches until an operator deletes the kill file and restarts the process."""
        self._killed = True
        self._kill_reason = reason
        self.cfg.kill_switch_path.parent.mkdir(parents=True, exist_ok=True)
        self.cfg.kill_switch_path.write_text(f"{time.time():.0f} {reason}\n")

    def pause(self, symbol: str, until_ts: float) -> None:
        self._paused_until[symbol] = max(self._paused_until.get(symbol, 0.0), until_ts)

    # State ------------------------------------------------------------------------------------
    def drawdown(self, a: AccountState) -> float:
        return 1 - a.equity / a.peak_equity if a.peak_equity > 0 else 0.0

    def day_loss(self, a: AccountState) -> float:
        return max(0.0, 1 - a.equity / a.day_start_equity) if a.day_start_equity > 0 else 0.0

    def gross_frac(self, a: AccountState, marks: dict[str, float]) -> float:
        return sum(abs(notional_frac(a, marks, s)) for s in a.positions)

    def code_risk_state(self, a: AccountState, marks: dict[str, float]) -> RiskState:
        c = self.cfg
        if self.drawdown(a) >= c.max_drawdown or self.day_loss(a) >= c.max_daily_loss:
            return "reduce"
        r = c.near_limit_ratio
        if (
            self.drawdown(a) >= r * c.max_drawdown
            or self.day_loss(a) >= r * c.max_daily_loss
            or self.gross_frac(a, marks) >= r * c.max_gross_frac
        ):
            return "near_limit"
        return "safe"

    # Main gate --------------------------------------------------------------------------------
    def check_order(
        self,
        intent: Intent,
        account: AccountState,
        marks: dict[str, float],
        snap: dict,
        now: float,
        jev_risk_state: RiskState | None = None,
    ) -> RiskVerdict:
        sym = intent.symbol
        mark = marks[sym]
        current = notional_frac(account, marks, sym)
        target = intent.target_frac
        state = self.code_risk_state(account, marks)
        if jev_risk_state and RISK_SEVERITY[jev_risk_state] > RISK_SEVERITY[state]:
            state = jev_risk_state  # the model may only make us stricter

        if self.drawdown(account) >= self.cfg.max_drawdown and not self.killed:
            self.arm_kill(f"max drawdown {self.drawdown(account):.2%} >= {self.cfg.max_drawdown:.0%}")
        if self.killed:
            return self._make(sym, current, 0.0, account, mark, f"kill switch: flatten ({self._kill_reason or 'file'})", state, bypass_rate=True)

        reasons = []
        if self.day_loss(account) >= self.cfg.max_daily_loss:
            reasons.append("daily loss limit")
        if state != "safe":
            reasons.append(f"risk_state={state}")
        if snap.get("age_s") is None or snap["age_s"] > self.cfg.max_snapshot_age_s:
            reasons.append("stale snapshot")
        if (snap.get("spr_bps") or 0.0) > self.cfg.max_spread_bps:
            reasons.append("spread too wide")
        if self._paused_until.get(sym, 0.0) > now:
            reasons.append("symbol paused by escalation")
        if reasons:
            target = _reduce_only(current, target)

        cap = self.cfg.max_position_frac
        target = max(-cap, min(cap, target))
        other_gross = self.gross_frac(account, marks) - abs(current)
        room = max(0.0, self.cfg.max_gross_frac - other_gross)
        if abs(target) > room:
            target = room if target > 0 else -room
            reasons.append("gross cap")
        # Caps must never push us further from flat than we already are in the same direction.
        if abs(target) > abs(intent.target_frac):
            target = intent.target_frac

        return self._make(sym, current, target, account, mark, "; ".join(reasons) or "ok", state, now=now)

    def _make(
        self, sym: str, current: float, target: float, account: AccountState, mark: float,
        reason: str, state: RiskState, now: float | None = None, bypass_rate: bool = False,
    ) -> RiskVerdict:
        delta = target - current
        if abs(delta) < 1e-9 or account.equity <= 0 or mark <= 0:
            return RiskVerdict(None, reason + " (no change)", state)
        if not bypass_rate:
            now = now if now is not None else time.time()
            while self._order_times and self._order_times[0] < now - 3600:
                self._order_times.popleft()
            reduces = abs(target) < abs(current) and target * current >= 0
            if len(self._order_times) >= self.cfg.max_orders_per_hour and not reduces:
                return RiskVerdict(None, reason + "; order rate cap", state)
            self._order_times.append(now)
        qty = delta * account.equity / mark
        return RiskVerdict(Order(sym, qty, reason), reason, state)


def _reduce_only(current: float, target: float) -> float:
    """Clamp target so the position can only move toward zero (no increase, no flip)."""
    if current == 0:
        return 0.0
    if current > 0:
        return min(current, max(0.0, target))
    return max(current, min(0.0, target))
