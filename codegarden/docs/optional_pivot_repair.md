# Optional pivot repair

The completed small clean-release batch had47920 exact query occurrences. All ended at a single solver node;36188 lacked enough individually eligible candidates to reach the target. This diagnoses a restrictive forced-pivot choice, not global infeasibility.

The new operator releases a sampled pivot's blockers but does not force the pivot. The fixed set is now a subset of the raw227-word state’s clean words, so every raw word outside that fixed set must remain individually eligible. This invariant and candidate-count lower bound are checked in native code, smoke tests and controller logs.

Both fixed32 and adaptive8–128 conditions run with uniform pair costs and600nativeCPU caps, unchanged independent acceptance. The earlier forced runs use identical starts/seeds and nominal budgets but are historical controls, not simultaneous runs. Improvements in pool size or solver effort alone do not count as primary success. Raw positive-energy states remain invalid.
