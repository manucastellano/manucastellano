# Phase 6 — Ship (AgenKit: ship gate)

Ship in stages. Each stage is an operator gate; do not skip ahead.

| Stage | Exit criteria to move on |
|---|---|
| 0. Verify research | Every finalist you keep has the `docs/research` checklist filled from primary sources; flip `verified: true` |
| 1. Replay paper | ≥ 2 weeks of recorded data; real costs measured into `CostConfig`; the strategy is positive **after** costs, with zero risk-limit violations |
| 2. Live-data paper | ≥ 2 weeks; Jev p95 latency and token counts measured; nightly reports reviewed daily; at least one schema promoted through `promote.py` on real evidence |
| 3. Testnet / tiny live | Live adapter written (plan #14) and reconciled; `TRADING_AGENT_LIVE=1` and `state/LIVE_APPROVED` naming the schema version; size ≤ 1% of target capital |
| 4. Scale | Only after a full month in stage 3 within limits; raise caps one step at a time |

## Operating the switches
- Kill now: `touch state/KILL` (the process flattens on the next step and stays flat).
- Resume: delete `state/KILL` **and restart** (the in-memory latch is intentional).
- Roll back a schema: copy `schemas/ACTIVE.prev` over `schemas/ACTIVE` and restart.

## Nightly schedule (example cron, UTC)
```
15 0 * * *  cd /srv/trading-agent && .venv/bin/python -m agent.review.nightly --draft --replay
```
Read `state/reports/<day>.json`, then run `python -m agent.review.promote --report ...` if it
passes. That is the "ship through AgenKit before the next open" step: the candidate schema and
report are the artifacts the AgenKit review/ship gate approves.
