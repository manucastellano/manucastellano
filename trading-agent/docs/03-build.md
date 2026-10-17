# Phase 4 — Build (AgenKit: test-first build gate)

```bash
cd trading-agent
python3 -m venv .venv && .venv/bin/pip install -e '.[dev]'
.venv/bin/python -m pytest -q        # 41 passed at the time of writing
```

## Defects found by the tests during the build
1. **Kelly edge invented from nothing.** With a 1.5R target, a coin-flip direction
   probability (0.5) produced positive Kelly size, because the no-skill hit rate for a 1.5R
   target is ~0.4, not 0.5. Fixed by using symmetric barriers (`PAYOFF_R = 1.0`). Regression
   test: `test_coin_flip_direction_never_sizes`.
2. **Held-out replay wasn't held out.** The nightly drafter saw the same day it was then scored
   on. Fixed: the drafter sees only earlier days; the replay scores today.
3. **Local-time day bucketing.** Fixed to UTC.
4. **Wall-clock escalation cooldown.** It broke replays; it now uses loop time.
