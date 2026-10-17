# Phase 5 — Review (AgenKit: review gate)

Adversarial checklist. Each line names the code that answers it.

| Question | Answer | Evidence |
|---|---|---|
| Can any hard limit be loosened by a model? | No. Jev's `risk_state` is merged as max severity; Opus verdicts are hold/reduce/flatten; caps clamp after every merge, and the final clamp never exceeds the intent | `risk.py::check_order`, `test_model_can_tighten_but_not_loosen`, `test_never_enlarges_intent` |
| Is the kill switch checked before every order? | Yes, first check in `check_order`; file-based so an operator can arm it from outside the process; drawdown latches it | `test_kill_switch_file_flattens_and_blocks`, `test_max_drawdown_latches_kill_switch` |
| Can the snapshot leak future data? | Selection is by receive time / candle close ≤ now; the snapshot asserts `newest_input_ts ≤ now` | `test_future_events_are_never_used`, `test_same_snapshot_regardless_of_arrival_order` |
| What happens when Jev is down? | HOLD; code stops still run | `test_reflex_failure_never_trades` |
| Can the nightly loop change what the code reads? | No. The shape is locked; only wording changes; promotion needs a replay with ≥ 200 samples and ≥ 2% Brier improvement, plus an operator | `validate_schema`, `promote.py::check`, `test_schema_shape_is_locked` |
| Is sizing fed an honest probability? | Shrunk 50% toward 0.5 until a calibrator is fitted on ≥ 200 labelled outcomes; the calibrator is itself operator-promoted | `calibration.py`, `policy.py` |

## Known gaps (not fixed in v0.1)
- Policy open-trade state (stop/target) is in memory; a restart forgets stops while positions
  persist on the venue. Must be fixed before live (plan #18).
- The paper broker fills at mid ± half spread + fixed slippage: no queue, no partial fills, no
  funding payments, no liquidation model.
- `notional_frac` uses the latest mark; a symbol with no fresh book keeps its last mark.
- Escalation runs inline. A slow Opus call delays later symbols in the same step (bounded by
  `timeout_s=120` and the per-symbol cooldown). Move it to a background task before live.
- The calibrator is fitted on P(chosen label correct), but sizing needs P(target before stop).
  With symmetric barriers these are close but not identical.
