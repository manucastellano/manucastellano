# Phase 3 — Plan (AgenKit: plan gate)

Small test-first tasks. ✅ = done in this branch with passing tests; ⬜ = open.

| # | Task | Files | Test |
|---|---|---|---|
| 1 ✅ | Config: every threshold in one frozen module | `src/agent/config.py` | used by all tests |
| 2 ✅ | Types | `src/agent/types.py` | — |
| 3 ✅ | Causal snapshot, token budget, crossed-book refusal | `src/agent/state_engine.py` | `tests/test_state_engine.py` |
| 4 ✅ | Schema shape lock + versioned wording + finalists | `src/agent/jev_schema.py`, `schemas/jev_schema_v1.json`, `schemas/ACTIVE` | `tests/test_calibration_and_schema.py` |
| 5 ✅ | Jev client, fail closed, parse real wire shape | `src/agent/jev_client.py` | `tests/test_calibration_and_schema.py` |
| 6 ✅ | Calibration: Brier, reliability, isotonic | `src/agent/calibration.py` | `tests/test_calibration_and_schema.py` |
| 7 ✅ | Policy gates + quarter Kelly + code stops | `src/agent/policy.py` | `tests/test_policy.py` |
| 8 ✅ | Risk layer + kill switch | `src/agent/risk.py` | `tests/test_risk.py` |
| 9 ✅ | Opus escalation (reduce-only verdicts) | `src/agent/escalation.py` | `tests/test_loop.py` (fake brain) |
| 10 ✅ | Paper broker, journal, loop | `src/agent/broker.py`, `src/agent/journal.py`, `src/agent/loop.py` | `tests/test_loop.py` |
| 11 ✅ | Nightly review + promote gate | `src/agent/review/{metrics,nightly,promote}.py` | `tests/test_loop.py::test_journal_feeds_nightly_scoring` |
| 12 ✅ | Paper runner over recorded data | `src/agent/run_paper.py` | import smoke test |
| 13 ⬜ | Venue data feed (books, candles, funding, OI) emitting the replay event format | `src/agent/feeds/<venue>.py` | recorded-fixture test |
| 14 ⬜ | Live broker adapter (idempotent client order IDs, reconciliation on restart, reduce-only flag on exits) | `src/agent/brokers/<venue>.py` | testnet run |
| 15 ⬜ | Record ≥ 2 weeks of real data; replay paper; measure real costs into `CostConfig` | `data/` | — |
| 16 ⬜ | Live Jev latency and token measurement vs the ~81 ms / 400-token claims | — | log `JevDecision.latency_ms`, `input_tokens` |
| 17 ⬜ | Scheduler: nightly at 00:15 UTC, loop as a supervised service | `ops/` | — |
| 18 ⬜ | Persist policy open-trade state (stops/targets) across restarts | `src/agent/policy.py` | restart test |
