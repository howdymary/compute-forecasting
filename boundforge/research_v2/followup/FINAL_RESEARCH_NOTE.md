# Final assessment: research-led C3c campaign

Research date: November 14, 2026 (America/Los_Angeles); execution receipts span November 14–15 UTC.
[Review](../COMPARATIVE_REVIEW.md) · [Preregistration](../DIRECTION_AND_PREREGISTRATION.md) · [First pilot](../output/RESEARCH_NOTE.md) · [Paired protocol](../NONDEGENERATE_FOLLOWUP.md) · [Remote run](https://github.com/howdymary/compute-forecasting/actions/runs/43676577601)

## Outcome and stopping decision

No new improvement in this campaign. Retain the earlier exact certificate:
[1.674894211307116228764565173162801538907820042565826358394793581, 1.674894211307116228764565173162801538907820042565826358394793582].

That witness improves Jaswal's published exact construction by approximately 2.21 × 10⁻²²,
mostly by removing digit-count rounding loss; it is not a substantial new mathematical bound.
Its leading 15 digits are unchanged. No universal upper bound or optimality result was established.

The original 87-case pilot mostly collapsed onto point masses, where the numerical score F=0
is uninformative. The registered paired follow-up changes the optimizer and requires H(X−Y)≥1 nat.
All 87 saved support/seed pairs became nondegenerate; none exceeded the F>1e−9 screen.
Finite-bank compositions did not improve the retained certificate.
This disentangles one optimizer failure from support quality, but does not prove these supports
cannot improve under another optimizer, entropy scale, probability landscape or composition.
The floor and graph-support grammar are search restrictions, not mathematical reductions.

| Arm | Cases | Nondegenerate | F>1e−9 | Best F | Process CPU seconds | Worker wall seconds |
|---|---:|---:|---:|---:|---:|---:|
| structured | 18 | 18 | 0 | -3.19614639e-06 | 15.28 | 15.55 |
| random | 18 | 18 | 0 | -0.00699740611 | 6.53 | 6.66 |
| model | 15 | 15 | 0 | -0.0652273869 | 5.53 | 5.63 |
| basin-mutation | 36 | 36 | 0 | -0.000770394194 | 34.05 | 34.56 |

Across both batches: 174 support/start cases, three probability initializations each.
Five of six actual Tinker program proposals parsed; one invalid JSON response retained and not replaced.
The paired study reused the same programs: no additional model calls and no retraining.
Structured proposals performed best in this limited score comparison; general superiority is not established.
No learning or shared-memory performance advantage is demonstrated. Six model calls are insufficient
for a broad cost-effectiveness claim. No fine-tuning was justified.

Stop scaling this grammar and optimizer pairing: no positive separator warrants further composition
work, and more equivalent trials have weak expected benefit. Unspent credits are not a reason to continue.
A future study would need a meaningfully broader, mathematically motivated representation and new
preregistered comparisons. Such a study has not been executed here.

## Contribution and reviewer objections

The present contribution is a reproducible engineering and negative-methodology case study,
plus a tiny pre-existing certified refinement. It is not yet a compelling substantial mathematics paper
or demonstrated autonomous-discovery framework advance. A workshop/demo submission might be feasible
after specialist review, but no venue acceptance is predicted and nothing has been submitted.

Strong objections: a one-target study, narrow graph grammar, small model sample, no training experiment,
non-global numerical optimization, an exploratory rather than untouched-held-out optimizer correction,
and incomplete billed-cost reconciliation. The initial incumbent-basin diagnostic is distinct from the
fixed/random/model program comparison. Budgets were bounded, not compute-identical across all arms.
A finite-bank LP sparsity observation is standard linear programming, not a new theorem.

## Claim-by-claim evidence

| Claim | Type | Evidence and limit |
|---|---|---|
| Nine primary-source precedents reviewed before new implementation | Provenance | ../COMPARATIVE_REVIEW.md and source commits |
| Official FunSearch priority yields 512, constant256, random256–262 | Exact diagnostic | ../evidence/funsearch-replay.json; construction replay, not historical discovery |
| Model generated six bounded proposals | Empirical | First-pilot trace; five parsed, one invalid; no model-written Python executed |
| Point-mass collapse prevented in paired diagnostic | Empirical | 87 saved cases, Htarget floor, nondegenerate measurements |
| No separator in tested follow-up | Empirical | cases.jsonl; does not prove no separator exists |
| No new certificate in this campaign | Certified computational comparison | Both unchanged independent checkers against earlier best |
| Existing exact witness remains valid | Certified computational result | best.json; intervals above, protected checker hashes in report |
| At most four laws suffice for an optimal fixed finite-bank LP | Standard mathematical observation | ../MATHEMATICAL_SCOPE.md; not a statement about all laws |
| Model/memory improves discovery efficiency | Not established | No claimed advantage |
| Publication-level mathematical advance | Not established | No substantial new bound, construction principle or theorem |

## Costs and remaining holds

New Exa API response receipts: USD0.078 (USD0.070 review plus USD0.008 in-loop).
Six Tinker calls, uncached-rate token estimate: USD0.0460587;
estimate is not a final charge. New past.dev estimated usage:9 credits.
Modal process CPU in the paired study: 61.39s;
worker wall time and GitHub elapsed time are separate. First-pilot process CPU is unavailable.

Conservative cumulative ledger, including earlier work: Exa USD0.31, Modal USD52.10,
Tinker USD2.40, past.dev78 credits. The new campaign adds at most USD30.10 in Modal
allowances and USD1.20 Tinker holds. Unknown actual charges remain reserved; do not label
these held amounts as spent. A pre-launch Modal serialization integration error started
no paid worker; its failed local ledger is not an additional completed-job charge.
All dispatched paid search jobs have ended. No paid resources are intentionally left running.
See usage.json and reservations.json for explicit unresolved reconciliation.

Initial verified balances/caps and billing boundaries: ../campaign-budget.json.
No credits were bought, auto-reload enabled, plans upgraded or provider balances pooled.

## Reproduction and artifact map

Both protected checkers ran on the source campaign, in its separate checking step and again
during publication. The independent rational-series verifier imports neither the search nor Arb.
The browser checks exact integer/rational structural conditions only; it does not prove entropy bounds.

    python boundforge/verify.py boundforge/research_v2/followup/best.json --baseline boundforge/results/best.json
    python boundforge/verify_independent.py boundforge/research_v2/followup/best.json boundforge/results/best.json
    python -m pytest -q -p no:cacheprovider boundforge/test_core.py boundforge/research_v2/test_v2.py

Raw follow-up: cases.jsonl, law-bank.json, trace.jsonl, best.json, report.json.
First pilot: ../output/ including model outputs, programs, sources, plot and offline demo.html.
Paired scientific plot: paired-scores.svg. All source code and artifacts live remotely in this repository;
no workstation project files were created.
