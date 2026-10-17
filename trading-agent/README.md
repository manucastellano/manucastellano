# trading-agent

A brain/reflex crypto trading agent. **Paper trading only in this version.**

- **Reflex (Jev, TypeSafe AI):** one typed call per symbol per candle, returning regime,
  direction, toxic_flow, setup_quality and risk_state.
- **Brain (Opus):** escalations when confidence is below 0.60 or regime is crisis (it may only
  reduce risk), plus nightly schema drafts.
- **Code:** features, gates, sizing, stops, every limit, the kill switch, and execution.

| Read | For |
|---|---|
| `docs/research/2026-10-17-market-research.md` | regime, finalists, theses, bear cases, invalidation, sources |
| `docs/00-spec.md` … `docs/05-ship.md` | the six AgenKit phases with file paths and gates |
| `schemas/jev_schema_v1.json` | the compiled Jev schema, per finalist |

```bash
python3 -m venv .venv && .venv/bin/pip install -e '.[dev]'
.venv/bin/python -m pytest -q                                   # offline, no keys needed
TYPESAFE_API_KEY=... ANTHROPIC_API_KEY=... .venv/bin/python -m agent.run_paper --data data/replay.jsonl
.venv/bin/python -m agent.review.nightly --day YYYY-MM-DD --draft --replay
.venv/bin/python -m agent.review.promote --report state/reports/YYYY-MM-DD.json
```

## Corrections to the original brief
- Jev's vendor is **TypeSafe** (`typesafe.ai`, SDK `typesafe-sdk`), not "typestate";
  `console.typestate.ai` does not resolve. The brief also says both "AgentKit/agentkit.xyz" and
  "AgenKit/agenkit.xyz"; the product is **AgenKit** at agenkit.xyz. It is a commercial kit,
  and it could not be installed from the build container. The repo follows its six-phase
  structure so you can drive it with `/agenkit` locally. It was **not** built with AgenKit.
- The ~81 ms Jev latency is the brief's claim, not measured here. The loop logs
  `latency_ms` and `input_tokens` per call so you can check it.
- "Before the next open" doesn't apply to 24/7 crypto. The nightly runs after UTC midnight.
- Fully automatic schema shipping was replaced with a gated promotion (evidence + operator).

## WHAT COULD I BE WRONG ABOUT?

1. **There may be no edge at all.** Nothing here has been backtested on real data; the build
   environment could not reach any market data. A 5-minute directional call on a perp has to
   beat about 15+ bps round trip (`CostConfig` placeholders, plus spread). Most short-horizon
   signals don't. Treat the system as a disciplined harness for *testing* an edge, not as an
   edge.
2. **Jev's probabilities may not be calibrated for markets.** The vendor describes outputs as
   calibrated, but calibration on their benchmarks says nothing about 5-minute crypto returns.
   That's why sizing shrinks the claimed edge by half until our own calibrator is fitted on
   ≥ 200 labelled outcomes.
3. **Kelly barely matters with these defaults.** At p≈0.9 (shrunk to 0.7), an 80 bps stop and
   about 16 bps of costs, quarter Kelly asks for roughly 6x notional. The 10% position cap binds
   first. In practice, sizing is "cap or nothing", which is the survivable choice, but don't read
   the Kelly math as doing much work.
4. **A direction probability is not a win probability.** I first got this wrong (with a 1.5R
   target a coin flip looked profitable; the tests caught it). Symmetric barriers make the two
   close, but not identical. The right long-term fix is to ask Jev for P(target before stop)
   directly, or to calibrate on barrier outcomes.
5. **The research is thin and secondhand.** Every number is from secondary sources found via
   web search, several conflict, and none were verified against primary data. The finalists
   are mostly *consensus* buyback stories that are likely priced in, not hidden asymmetries.
6. **Buyback theses are pro-cyclical.** HYPE and PUMP buybacks shrink when activity falls,
   which is exactly when price is weak. ENA's buybacks don't start until USDe supply reaches
   $7.5B, which this funding regime works against.
7. **The nightly loop can overfit.** Rewording a schema daily against yesterday's errors is a
   classic way to chase noise. The guards are a held-out day, ≥ 200 samples, a 2% Brier
   improvement and a human. They reduce the risk; they don't remove it.
8. **Paper fills are optimistic.** No queue position, partial fills, funding payments,
   liquidation or venue outages. Slippage is fixed, not size-dependent.
9. **Operational gaps exist before live.** The open-trade stops are kept in memory (a restart
   forgets them), there's no live feed or broker adapter, and escalation runs inline. All are
   listed in `docs/04-review.md` and `docs/02-plan.md`.
10. **Events since 2026-10-17.** FOMC (Oct 27–28) and the unlocks listed in the research will
    have happened by the time you read this. Re-run the regime read before acting on it.
