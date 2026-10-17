"""Every threshold, size and limit lives here, in code. Nothing in this module is ever
read from a model response. Defaults are conservative starting points, not tuned values."""

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class PolicyConfig:
    min_setup_quality: float = 2.0  # Jev expected score on the 0..3 rubric
    min_direction_confidence: float = 0.80  # strictly greater than
    max_toxic_flow_prob: float = 0.50  # addition to the spec: skip entries into likely-toxic flow
    kelly_cap_fraction: float = 0.25  # quarter Kelly, hard cap
    # Uncalibrated Jev probabilities are shrunk toward 0.5 until the nightly review has fitted
    # a calibrator from realized outcomes. 0.5 halves the claimed edge.
    default_probability_shrink: float = 0.5


@dataclass(frozen=True)
class RiskConfig:
    max_drawdown: float = 0.15  # from peak equity; breach latches the kill switch and flattens
    max_daily_loss: float = 0.03  # of start-of-UTC-day equity; breach halts new risk until rollover
    max_position_frac: float = 0.10  # per-symbol notional / equity
    max_gross_frac: float = 0.30  # sum of |notional| / equity across symbols
    max_spread_bps: float = 15.0  # do not trade into wide books
    max_snapshot_age_s: float = 5.0  # stale data blocks orders
    max_orders_per_hour: int = 30
    near_limit_ratio: float = 0.66  # fraction of a limit at which code reports near_limit
    kill_switch_path: Path = Path("state/KILL")


@dataclass(frozen=True)
class EscalationConfig:
    low_confidence: float = 0.60  # strictly below escalates to Opus
    model: str = "claude-opus-5-5"
    effort: str = "high"
    timeout_s: float = 120.0
    cooldown_s: float = 900.0  # at most one escalation per symbol per window, to bound cost


@dataclass(frozen=True)
class CostConfig:
    """Used by the paper broker and by sizing. Measure these on the real venue before trusting
    any backtest; the defaults are placeholders."""

    taker_fee_bps: float = 4.5
    slippage_bps: float = 3.0


@dataclass(frozen=True)
class AgentConfig:
    policy: PolicyConfig = field(default_factory=PolicyConfig)
    risk: RiskConfig = field(default_factory=RiskConfig)
    escalation: EscalationConfig = field(default_factory=EscalationConfig)
    cost: CostConfig = field(default_factory=CostConfig)
    candle_seconds: int = 300
    label_horizon_candles: int = 12  # forward window used to grade direction calls nightly
    jev_model: str = "jev-latest"
    jev_timeout_s: float = 2.0
    journal_dir: Path = Path("state/journal")
    # Live trading needs both this flag and an operator-signed approval file (see broker.py).
    live: bool = False
