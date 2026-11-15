# BoundForge measured result

Research date: 2026-11-15T03:23:58.870925+00:00.
Source runs: 43670325538, 43670827227, 43671271112, 43671753698.

## Certified result

The exact witness ratio lies in
[1.674894211307116228764565173162801538907820042565826358394793581, 1.674894211307116228764565173162801538907820042565826358394793582].
Its rigorous lower endpoint exceeds the published Jaswal witness's rigorous upper endpoint
by at least approximately 2.21436102E-22. Arb and the independent rational-series checker both passed.
Final construction: [59, 49] support sizes; base 61;
exact positive rational weights and independent integer digit counts.

**This is an extremely small refinement, not a major new bound.**
The 15-digit leaderboard value is unchanged. Most gain removes the original digit-count rounding loss.
Added support points contribute much smaller positive gains. No sharp-constant solution,
proof-assistant verification, leaderboard acceptance, or substantial advance is claimed.
[Current table](https://teorth.github.io/optimizationproblems/constants/3c.html)
[Original certificate](https://zenodo.org/records/23289305)

## Attribution and research

Manvir Jaswal supplied the original two laws and stationary free-energy/Newton construction method.
BoundForge independently reproduces the result, searches projection-fibre intersections, estimates
profitable support insertions, refines at 110 digits, rounds to exact rational data and certifies changes.
The independent-digit encoding is checked for all five projections; a probability mixture is different.

Initial SLSQP campaign: 16 trials, zero improvements; numerical failures are retained.
High-precision trials and all actual model decisions are retained in trace.jsonl and runs/.
These bounded attempts do not establish local or global optimality.

## Actual integrations

Exa calls inside research loops: 8.
Real Tinker decisions: 4.
Verified cross-role past.dev recalls: 16.
Modal ran bounded CPU solves; fresh independent certification used GitHub Actions.
Failed Tinker integrations are not counted as successful model decisions.
No fine-tuning, memory performance benefit or model-selection advantage is claimed.

## Budgets and stopping

Initial balances and provenance: ../budget-snapshot.json.
No credits were bought, auto-replenishment enabled or plans upgraded.
Unknown costs stay reserved. Per-run ledgers are retained as reservations.json.
Includes an additional $4 Modal hold for the cancelled campaign; its unresolved provider allowances are listed separately. Exa: response costs. Tinker: uncached-rate token estimates. Past: estimated ingests plus 1 credit per recall. Modal: conservative upper reservations, not invoices.
Partial provider receipts are in provider-receipts.json; they may lag.

The bounded campaign stops after independent certification. Deep decimal refinements do not justify
calling this a major breakthrough or blindly consuming the remaining credits on the same tail search.
The next larger search should target different support geometry or a new complementary law.

## Reproduce remotely

    python boundforge/verify.py boundforge/results/best.json --baseline boundforge/certificates/incumbent.json
    python boundforge/verify_independent.py boundforge/results/best.json boundforge/certificates/incumbent.json

demo.html is a self-contained replay of these actual artifacts, with no credentials.
Its structural check uses BigInt and preserves large rational integers as strings.
The Python checkers certify entropy intervals; the browser does not prove logarithm bounds.
