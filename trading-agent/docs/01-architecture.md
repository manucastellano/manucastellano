# Phase 2 — Architecture (AgenKit: architecture gate)

```
             every candle close (5m)                              nightly (UTC)
 feed ──► StateEngine ──snapshot (≤400 tok)──► Jev (reflex, 1 call/symbol)    Journal ──► review/nightly
 (books,   causal, numeric                         │ typed answers               │         label, Brier,
  candles,                                          ▼                             │         calibrator,
  context)                     confidence<0.60 or crisis? ──► Opus (brain)        │         Opus draft,
                                                    │          hold/reduce/       │         Jev replay
                                                    ▼          flatten + pause    │            │
                                         Policy (code gates + Kelly) ◄────────────┘            ▼
                                                    │  more-conservative merge           promote (operator)
                                                    ▼
                                    RiskManager (code; immediately before every order)
                                                    │
                                                    ▼
                                        Broker (paper only in v0.1) ──► Journal
```

## Who owns what
| Concern | Owner | Model may... |
|---|---|---|
| Features (mid, spread, imbalance, RV, inventory, drawdown) | code | nothing |
| Regime / direction / quality / toxicity judgement | Jev | answer typed questions |
| Entry gates, stop/target, sizing | code | supply probabilities only |
| Limits, kill switch, caps, pauses | code | make things stricter, never looser |
| Deep re-read on low confidence or crisis | Opus | hold / reduce / flatten / pause ≤ 240 min |
| Schema wording | Opus drafts, operator promotes | never change the shape |

## Failure modes → behavior
| Failure | Behavior |
|---|---|
| Jev timeout or error, or an unexpected label | `None` → HOLD (existing positions still covered by code stops) |
| Opus error, refusal or invalid output | fail closed: hold + 15-min entry pause |
| Unhandled exception in a step | kill switch armed |
| Drawdown ≥ 15% | kill latched (file on disk), flatten everything |
| Stale book (> 5 s) or spread > 15 bps | reduce-only |

## Verified external interfaces
- **Jev:** `typesafe-sdk==0.7.5` (PyPI, maintainer TypeSafe AI). `AsyncTypeSafeClient.system_one(state=..., questions=...)`
  → `POST /v1/systemone`. Question types `Choice`, `Score`, `Noul`. Checked by reading the installed
  package source. The brief's `console.typestate.ai` does not resolve; the vendor is **TypeSafe**
  (`typesafe.ai`).
- **Opus:** `anthropic==1.15.0`, `AsyncAnthropic().messages.parse(model="claude-opus-5-5", output_format=Verdict, output_config={"effort": "high"})`.
