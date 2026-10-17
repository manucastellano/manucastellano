# Phase 1 — Spec (AgenKit: brainstorm/spec gate)

**Goal:** a 24/7 crypto agent that trades liquid perps on per-candle typed judgements and
cannot lose more than the hard limits allow, whatever any model outputs.

## Requirements
| ID | Requirement | Where |
|---|---|---|
| R1 | Snapshot per symbol per candle, numeric, < 400 tokens, strictly causal | `src/agent/state_engine.py` |
| R2 | One Jev call per symbol per candle with 5 typed questions (regime, direction, toxic_flow, setup_quality, risk_state) | `src/agent/jev_client.py`, `src/agent/jev_schema.py` |
| R3 | Entry only if setup_quality ≥ 2, direction confidence > 0.80, risk_state == safe | `src/agent/policy.py` |
| R4 | Size = fractional Kelly from calibrated probability, ≤ quarter Kelly | `src/agent/policy.py` |
| R5 | Hard limits in code: 15% max drawdown (latching kill), daily loss, per-symbol and gross caps, kill switch checked before every order | `src/agent/risk.py` |
| R6 | Escalate to Opus when confidence < 0.60 or regime == crisis; Opus may only reduce risk | `src/agent/escalation.py` |
| R7 | Nightly: label fills and misses, Brier score, propose a reworded schema, replay it, operator-gated promotion | `src/agent/review/` |
| R8 | Every decision journaled | `src/agent/journal.py` |

## Additions to the original brief (each one is safety-motivated)
- Toxic-flow gate: no entries when P(toxic) > 0.5 (the brief computed it but never used it).
- Model-originated *defensive* actions only: crisis → flatten, `reduce` → halve.
- Unverified or unapproved finalists never trade.
- Stale-data, wide-spread and order-rate guards.
- Symmetric barriers (target = stop) so that Jev's direction probability is a valid Kelly input.
  See the comment above `PAYOFF_R` in `src/agent/policy.py`.

## Non-goals (v0.1)
- A live venue adapter and a live data feed (both untestable from the build environment).
- Automatic schema promotion. This is deliberately an operator gate.
