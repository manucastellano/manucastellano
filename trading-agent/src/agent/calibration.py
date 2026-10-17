"""Probability calibration and Brier scoring. Pure functions plus a tiny monotone calibrator
(pool-adjacent-violators isotonic regression) so we do not depend on scikit-learn."""

import json
from dataclasses import dataclass, field
from pathlib import Path


def brier_binary(probs: list[float], outcomes: list[int]) -> float:
    if not probs or len(probs) != len(outcomes):
        raise ValueError("need equal, non-empty inputs")
    return sum((p - o) ** 2 for p, o in zip(probs, outcomes)) / len(probs)


def brier_multiclass(prob_rows: list[dict[str, float]], labels: list[str]) -> float:
    """Mean over samples of sum_k (p_k - 1[k == label])^2. Range 0 (perfect) .. 2."""
    if not prob_rows or len(prob_rows) != len(labels):
        raise ValueError("need equal, non-empty inputs")
    total = 0.0
    for row, label in zip(prob_rows, labels):
        keys = set(row) | {label}
        total += sum((row.get(k, 0.0) - (1.0 if k == label else 0.0)) ** 2 for k in keys)
    return total / len(prob_rows)


def reliability_table(probs: list[float], outcomes: list[int], bins: int = 10) -> list[dict[str, float]]:
    rows = []
    for b in range(bins):
        lo, hi = b / bins, (b + 1) / bins
        idx = [i for i, p in enumerate(probs) if lo <= p < hi or (b == bins - 1 and p == 1.0)]
        if idx:
            rows.append({
                "lo": lo, "hi": hi, "n": len(idx),
                "mean_pred": sum(probs[i] for i in idx) / len(idx),
                "hit_rate": sum(outcomes[i] for i in idx) / len(idx),
            })
    return rows


@dataclass
class IsotonicCalibrator:
    """Maps a raw probability to an empirical one. Unfitted, it shrinks toward 0.5."""

    shrink: float = 0.5
    xs: list[float] = field(default_factory=list)  # block upper edges, ascending
    ys: list[float] = field(default_factory=list)  # calibrated value per block
    min_samples: int = 200

    @property
    def fitted(self) -> bool:
        return bool(self.xs)

    def __call__(self, p: float) -> float:
        if not self.fitted:
            return 0.5 + self.shrink * (p - 0.5)
        for x, y in zip(self.xs, self.ys):
            if p <= x:
                return y
        return self.ys[-1]

    def fit(self, probs: list[float], outcomes: list[int]) -> bool:
        """Returns False (and stays unfitted) when there is too little data to trust."""
        if len(probs) < self.min_samples:
            return False
        pairs = sorted(zip(probs, outcomes))
        blocks: list[list[float]] = []  # [sum_y, count, max_x]
        for x, y in pairs:
            blocks.append([float(y), 1.0, x])
            while len(blocks) > 1 and blocks[-2][0] / blocks[-2][1] > blocks[-1][0] / blocks[-1][1]:
                s, c, mx = blocks.pop()
                blocks[-1][0] += s
                blocks[-1][1] += c
                blocks[-1][2] = mx
        self.xs = [b[2] for b in blocks]
        self.ys = [b[0] / b[1] for b in blocks]
        return True

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"shrink": self.shrink, "xs": self.xs, "ys": self.ys}))

    @classmethod
    def load(cls, path: Path, shrink: float = 0.5) -> "IsotonicCalibrator":
        if not path.exists():
            return cls(shrink=shrink)
        raw = json.loads(path.read_text())
        return cls(shrink=raw.get("shrink", shrink), xs=raw["xs"], ys=raw["ys"])
