import copy
import json

import pytest
from typesafe_sdk import SystemOneResponse

from agent.calibration import IsotonicCalibrator, brier_binary, brier_multiclass
from agent.jev_client import parse_response
from agent.jev_schema import SchemaError, active_schema_path, validate_schema


def test_brier_values():
    assert brier_binary([1.0, 0.0], [1, 0]) == 0.0
    assert brier_binary([0.5, 0.5], [1, 0]) == 0.25
    assert brier_multiclass([{"long": 1.0, "short": 0.0}], ["short"]) == 2.0


def test_isotonic_is_monotone_and_unfitted_shrinks():
    cal = IsotonicCalibrator(shrink=0.5, min_samples=10)
    assert cal(0.9) == pytest.approx(0.7)
    probs = [i / 100 for i in range(100)]
    outcomes = [1 if (i % 3 == 0 or i > 70) else 0 for i in range(100)]
    assert cal.fit(probs, outcomes)
    ys = [cal(p) for p in probs]
    assert all(a <= b for a, b in zip(ys, ys[1:]))


def test_isotonic_refuses_thin_data():
    assert not IsotonicCalibrator().fit([0.9] * 10, [1] * 10)


def test_schema_shape_is_locked():
    raw = json.loads(active_schema_path().read_text())
    validate_schema(raw)
    for mutate in (
        lambda r: r["questions"]["direction"]["criteria"].pop("neutral"),
        lambda r: r["questions"]["direction"]["criteria"].update({"maybe": "x"}),
        lambda r: r["questions"].pop("toxic_flow"),
        lambda r: r["questions"]["setup_quality"]["criteria"].update({"4": "x"}),
    ):
        bad = copy.deepcopy(raw)
        mutate(bad)
        with pytest.raises(SchemaError):
            validate_schema(bad)


def wire(direction="long"):
    return {
        "model": "jev-1.14.0",
        "usage": {"input_tokens": 410, "output_tokens": 9},
        "answers": {
            "regime": {"type": "choice", "choice": "trending", "confidence": 0.7,
                       "probabilities": {"trending": 0.7, "mean_reverting": 0.1, "high_vol": 0.15, "crisis": 0.05}},
            "direction": {"type": "choice", "choice": direction, "confidence": 0.83,
                          "probabilities": {"long": 0.83, "short": 0.07, "neutral": 0.10}},
            "toxic_flow": {"type": "noul", "noul": 0.12},
            "setup_quality": {"type": "score", "score": 2.2, "confidence": 0.6,
                              "legend": {"0": "a", "1": "b", "2": "c", "3": "d"},
                              "probabilities": {"0": 0.05, "1": 0.15, "2": 0.35, "3": 0.45}},
            "risk_state": {"type": "choice", "choice": "safe", "confidence": 0.9,
                           "probabilities": {"safe": 0.9, "near_limit": 0.08, "reduce": 0.02}},
        },
    }


def test_parse_real_wire_shape():
    d = parse_response(SystemOneResponse.model_validate_json(json.dumps(wire())), 81.0)
    assert (d.direction, d.direction_confidence, d.setup_quality, d.toxic_flow_prob) == ("long", 0.83, 2.2, 0.12)


def test_parse_rejects_unknown_label_and_missing_answer():
    with pytest.raises(ValueError):
        parse_response(SystemOneResponse.model_validate_json(json.dumps(wire("sideways"))), 1.0)
    w = wire()
    del w["answers"]["toxic_flow"]
    with pytest.raises(KeyError):
        parse_response(SystemOneResponse.model_validate_json(json.dumps(w)), 1.0)
