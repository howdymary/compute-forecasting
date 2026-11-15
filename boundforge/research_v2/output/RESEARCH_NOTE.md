# Research-led BoundForge study

Research date: November 14, 2026, America/Los_Angeles. Raw receipts use UTC.
Review was committed before implementation of this pilot.
[Comparative review](../COMPARATIVE_REVIEW.md) · [Frozen direction/criteria](../DIRECTION_AND_PREREGISTRATION.md)
[Actual campaign](https://github.com/howdymary/compute-forecasting/actions/runs/43675810337)

## Main finding

Strict improvement over the retained 59/49-point certificate: **False**.
Retain the old exact certificate. Stop scaling this grammar/optimizer pairing; the bounded experiment does not justify more of the same search.

This study adapts prior methods. It does not establish that our framework is novel or superior,
nor guarantee journal acceptance. A negative result here is scoped to the tested representation,
initializations and resource budget.

## What was researched and reproduced

Nine primary-source precedents were reviewed, including FunSearch, AlphaEvolve, PatternBoost,
Wagner's cross-entropy approach, AlphaTensor, a recent geometric PatternBoost study and
direct entropy/sum-difference work. Costs or implementation details not verified are marked unknown.

Official FunSearch construction replay: size 512 at dimension 8; constant priority 256;
ten random priorities 256–262. Independent exact pair checks passed.
This is replay of released construction/evaluation code, not reproduction of the historical LLM search.

## Executed comparison

Model inference calls: 6; valid model programs: 5/6.
Model proposals outside the deterministic menu use a bounded integer-expression grammar.
All programs share the same numerical optimization procedure.
Start 101 supplies development feedback; programs are frozen before starts 202 and 303.
These are three starts on one mathematical target, not independent mathematical problems.

| Arm | Cases | Nondegenerate | F>1e−9 | Best nondegenerate F | Function evaluations | Worker seconds |
|---|---:|---:|---:|---:|---:|---:|
| structured | 18 | 4 | 0 | -1.3234345352941546e-05 | 5772 | 0.48 |
| random | 18 | 0 | 0 | None | 2197 | 0.23 |
| model | 15 | 0 | 0 | None | 1759 | 0.17 |
| basin-mutation | 36 | 3 | 0 | -0.0007607176218344947 | 6938 | 0.61 |

A point mass has F=0 and is not a successful separator. The table excludes collapsed laws from
the best-nondegenerate column. Invalid model proposals consume proposal slots; no replacement
calls are silently added. The incumbent-basin mutation arm is a separate diagnostic, not the same
program-generation comparison. Case counts, CPU effort and model overhead are distinct resources.

A positive F is a numerical proposal score. It is not a bound for all random variables, nor alone
proof that a finite-bank composition improves. See [mathematical scope](../MATHEMATICAL_SCOPE.md).
No fine-tuning was run: this archive does not establish sufficient independent construction-family
coverage for a meaningful training/evaluation split.

## Exact result and claims

Retained ratio interval:
[1.674894211307116228764565173162801538907820042565826358394793581, 1.674894211307116228764565173162801538907820042565826358394793582].

Both protected verifiers were unchanged and rerun. Final witnesses, all numerical cases, law bank,
model outputs, source links, program freeze and reservation ledger are retained in this folder.
The original incumbent and its author attribution remain unchanged.

| Claim | Evidence | Status |
|---|---|---|
| Comparative research preceded the new search | Review/preregistration commits and source hashes in trace | Established provenance |
| Released FunSearch construction replays at 512 | ../evidence/funsearch-replay.json; run 43675332783 | Exact diagnostic passed |
| Tinker generated bounded programs | model_inference / valid_program / invalid_program events | Actual calls, invalid attempts retained |
| Modal performed numerical search | per-case timing, function evaluations and saved law bank | Actual bounded executions |
| A new C3c lower bound was found | Both interval checkers against retained witness | False |
| Model generation is generally superior | Three-start limited comparison | Not established |
| A universal entropy upper bound was proved | No universal certificate exists | Not claimed |
| Work is ready as a substantial mathematics paper | Requires substantive new construction/theory and specialist review | Not established |

## Usage and reproducibility

Exa response costs including phase-one discovery: 0.078000 USD.
Tinker uncached-rate token estimate: 0.046059 USD.
past.dev estimated ingests plus conservatively metered recalls: 9 credits.
Held allowances for this numerical campaign: {'exa': 0, 'modal': 15.050000000000024, 'tinker': 1.2, 'past': 0}.
These are not final billed charges; prior pending allowances remain in reservations.json.

No credits were purchased, auto-reload enabled or plans upgraded. Initial balances and their
verification are in ../campaign-budget.json. Provider-specific caps are never pooled.
Scientific verification uses GitHub Actions and does not need paid APIs.

    python boundforge/verify.py boundforge/research_v2/output/best.json --baseline boundforge/results/best.json
    python boundforge/verify_independent.py boundforge/research_v2/output/best.json boundforge/results/best.json

demo.html is generated from actual source-run artifacts. oracle-scores.svg displays numerical
proposal scores, with collapsed solutions marked separately. Neither is a mathematical proof.
