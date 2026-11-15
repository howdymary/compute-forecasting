# BoundForge

An auditable autonomous search for C3c, the four-slope arithmetic Kakeya sum–difference constant.

**Measured result:** a certified strict refinement of the published witness, approximately 2.21 × 10⁻²². The leading 15 digits are unchanged. This is an extremely small advance on an attributed construction, not a major new bound. See [measured report](results/REPORT.md).

All project files live here. Two GitHub Actions workflow files are the necessary repository-level exception.
No workstation checkout is required. Existing forecasting code and dependencies are independent.

## Remote reproduction

Run **BoundForge high precision research** on branch **compute-observatory** for the full exact search from the attributed baseline. **BoundForge certified research** retains the initial numerical pilot: 16 bounded
12-second numerical trials using Modal CPU workers, with exact certification on a separate GitHub runner.
The workflow retains trace, candidates, checkpoint, sources, cost reservations and dependency versions.
Inputs are capped at 240 trials and 60 seconds; the budget gate can stop earlier.

Remote runner commands:
```sh
python -m pip install -r boundforge/requirements.txt modal
python -m pytest -q -p no:cacheprovider boundforge/test_core.py
python boundforge/run.py --trials 16 --seconds 12 --remote
python boundforge/verify_independent.py boundforge/results/best.json
python boundforge/verify.py boundforge/results/best.json --baseline boundforge/certificates/incumbent.json
```

## Mathematics and provenance

We seek to raise
H(X−Y) / max(H(X), H(Y), H(X+Y), H(X+2Y)).
Every certificate is a finite list of integer point supports, exact positive rational probabilities,
independent digit-law counts, and a base certifying injective encoding for all five projections.

The starting construction is **Manvir Jaswal's published certificate**, not a BoundForge discovery:
51- and 47-point laws, 10^20 independent digits in base 55, ratio
1.674894211307116228764343737060957…
[Table entry](https://teorth.github.io/optimizationproblems/constants/3c.html)
· [Exact certificate and explanation](https://zenodo.org/records/23289305)
· [Merged table update](https://github.com/teorth/optimizationproblems/pull/221).

The included published verifier and README are retained verbatim as source materials with attribution.
The exact certificate MD5 reported by Zenodo is 277fbedab582cb0a6c6cd6d4eb06588d.
BoundForge adds two separate checkers: Arb interval arithmetic and exact rational logarithm series
with explicit tail bounds. The latter imports neither the numerical search nor the Arb checker.
A candidate improves the incumbent only if its rigorous lower endpoint exceeds the incumbent's upper endpoint.
Printed digits and floating solver scores are not sufficient.

Digit entropy addition uses independent blocks, not a mixture of probability laws.
For every projection digit |d| < B/2. Two distinct digit strings first differ modulo B
by a nonzero integer of magnitude < B, impossible; consequently encoding is injective.
Independent projected entropies therefore add with the exact integer digit counts.
The target projection need not be injective on the original point support: we aggregate collisions.

## Research loop

1. Reproduce the incumbent with Arb, the independently written rational-series checker and the author's checker.
2. Exa searches inside the research loop at initialization and after an initial experiment batch.
   Returned sources inform an explicit, logged rule for choosing support/weight/composition operators.
3. A proposer selects a bounded operator based on prior numerical outcomes, attempts and literature hints.
4. Modal CPU workers optimize candidate laws; workers receive no provider keys or verifier source.
5. The protected Arb checker recomputes projected rational masses. Numerical scores cannot accept candidates.
6. Save every candidate and decision, compose complementary laws through an entropy-cone LP, checkpoint.
7. Independently certify the final witness in a fresh GitHub job.

Operator families: fixed-support probability perturbation; adding fibre-intersection points;
bounded ruin-and-recreate exchanges; a third independent digit law.
Two unsuccessful trials trigger neighborhood escalation. Failed trials are evidence about those attempts,
not a proof an entire search neighborhood was exhausted. The initial controller is deterministic. The high-precision campaign uses a real Tinker model to rank bounded support hypotheses when available; failures fall back explicitly and remain in the log. Fine-tuning is gated on useful verified training data.

## Memory and providers

past.dev stores source-backed shared research findings; trace/checkpoints store exact experiment state.
The proposer and verifier roles each write and read using distinct identities. Required source IDs are checked
inside actual recall responses before claiming cross-role reuse. A verifier-written baseline recommendation
changes the first proposed operator when recall succeeds. There is no claimed memory performance gain.

Credentials are read only from GitHub Actions secrets. Never put key values here.
Initial provider-specific balances and provenance are in budget-snapshot.json.
SQLite immediate transactions reserve worst-case costs before calls; unknown actuals remain reserved.
No credit purchase, plan change, auto-replenishment, or billing setting changes are implemented.
Modal reservation amounts are conservative upper allowances, **not reported actual billed charges**.
API accounting can lag; keep substantial headroom and recheck dashboards between campaign batches.

Exa: Lite search, five results and bounded text. Each call reserves $0.10 versus the verified lower tariff.
past.dev: ingest estimate before reservation; reserve one credit per recall conservatively.
Modal: 2 CPU, 1 GiB, hard worker timeout, bounded containers; a separate image/build reserve.
Tinker: Qwen3.5-397B-A17B can rank structural insertions. Actual inference successes are counted separately from integration failures. Train only after there is a credible supervised objective and a verified credit boundary.

## Limitations

A small random perturbation is unlikely to improve this carefully optimized incumbent. Structural support
changes and complementary laws are the substantive targets. An exact positive result is a valid lower bound,
not a solution for the sharp value of C3c. No formal proof-assistant verification is claimed.

[Model-policy comparison and reasoning audit](POLICY_REVIEW.md) · [Self-contained replay source](results/demo.html)
