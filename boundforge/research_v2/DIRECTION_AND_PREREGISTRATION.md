# Research direction and preregistration

Frozen before the new C3c campaign. Date: November 14, 2026, America/Los_Angeles.

## Decision

C3c remains the objective. Correctness infrastructure is strong; the discovery representation is narrow.
Continue with a bounded, falsifiable representation/dual-oracle pilot. Do not spend the larger budget
on repeated precision/tail gains. A negative pilot is an acceptable output, not proof the target is exhausted.

| Rank | Direction | Evidence / upside | Pilot and falsifier | Risk and resource allocation |
|---|---|---|---|---|
| 1 | Diverse laws plus entropy-cone composition | Jaswal's complementarity; AlphaEvolve's construction-search viewpoint. Can move beyond two inherited laws. | Optimize finite laws under the incumbent dual weights, then solve a bank LP. Stop scaling if no competitive nondegenerate laws emerge across independent starts. | Local collapse and missed basins. Initial ≤192 classical law optimizations; Modal CPU reserve ≤12 USD. |
| 2 | Model-generated bounded construction programs | FunSearch/AlphaEvolve representation lesson; new candidates outside the fixed insertion menu. | Compare Tinker-generated programs, fixed structured families and random programs on the same three starts with the same local optimizer. Record every invalid output. | Grammar restriction and contamination. ≤12 model programs, ≤20 USD Tinker upper allowance; no training. |
| 3 | PatternBoost-style learned global seeds | PatternBoost and geometry study show possible value only with useful data/encoding. | First inspect archive diversity and independent families. Do not train if results are collapsed point masses or near-duplicates. | High risk of decorative training. Deferred unless the data gate is satisfied. |

## Experimental contract

Main objective: raise H(X−Y)/max(H(X),H(Y),H(X+Y),H(X+2Y)).
Baseline for accepting any record: the committed 59/49-point BoundForge certificate, plus current
literature checks. Separate improvements to rounded data from changes to the construction.

Represent support as a graph over integer target differences: points (d+y(d),y(d)).
This ensures the target projection is injective. It is a search restriction, not a theorem that
all optimum laws have this form at our chosen range.

Generate y(d) using bounded integer expression trees. This is a safe, restricted program search,
not a reproduction of unrestricted AlphaEvolve. Share the grammar between random and model arms.
Local moves can modify graph coordinates, which tests escaping the initial expression.

Use three fixed seeds 101, 202, 303. Report per-seed and pooled descriptive outcomes.
Use the same numerical inner optimization budget in comparison arms, and report actual function
evaluations, CPU/wall time, model latency and cost separately. Invalid outputs count against proposal
budgets. They must not be silently replaced by extra model proposals.

The incumbent's dual multipliers provide a proposal score F(q)=H(X−Y)−Σ ν_j H(L_jq).
This is an empirical separation-oracle target. It is not a certified universal inequality.
Point masses have F=0; reject collapsed solutions as informative successes.

Prespecify a meaningful numerical separation trigger F>1e−9 for expensive refinement.
A raw floating trigger does not accept a record. Every proposed construction is rounded to exact
rational masses, composed with positive integer counts, and checked by BOTH unchanged verifiers.
Compare candidate lower endpoint with baseline upper endpoint.

Use a finite-bank LP with any number of laws. Preserve the baseline certificate unchanged and
retain it whenever exact checks fail or no strict improvement is certified.

Do not infer learning benefits from a single run, or treat correlated support variants as independent
mathematical problems. Hold-out splits for future training must separate construction families.

## Mathematical interpretation and publication gate

Analyze new support geometry, projection collisions, nondegenerate entropy vectors, composition
weights and whether added laws are actually used. A better finite bank does not prove an optimal
bound for all laws. Do not call a tiny rounding gain a major result.

Potential publication: a new explainable construction family or substantial certified bound;
alternatively an honest methods/negative-results technical note with reproducible comparisons.
Current evidence does not justify claiming a research-paper-level advance.

A claim table must link every assertion to exact checks, measured outcomes or a primary source.
No journal submission, researcher contact, or leaderboard update is authorized.

## Budget

Phase-one Exa discovery cap: 2 USD; actual response costs were 0.07 USD.
Current dashboard snapshots: Exa 119.52 USD; Modal 249.24 USD; Tinker 281.71 USD.
past.dev is read live before paid operations. Preserve unresolved old allowances separately.
Initial balances are immutable caps; new deposits cannot expand them.

Proposed new campaign upper allowances: Exa 8 USD, Modal 60 USD, Tinker 20 USD, past.dev 400 credits.
These are allowances, not spending targets. Begin with the smaller pilot above. Reserve independent
final certification on GitHub Actions, which needs no paid provider calls.

## Executed phase-one diagnostic

Official FunSearch priority replay: 512 verified cap-set vectors at dimension 8, constant priority 256, ten random priorities 256–262; independent exact pair checks passed. Source pinned at cc53f274237d7ab05c19df939edbc1f9616a7c19; run 43675332783. This completes the bounded method-replay gate, not the original AI discovery experiment.

The executable pilot has six fixed, six random and at most six valid model construction programs. Each is evaluated on starts 101/202/303 (at most 54 cases), followed by 36 separate incumbent-basin mutation cases. Each case gets up to three L-BFGS restarts, 160 iterations per restart and 25 seconds. Invalid model proposals consume their slots. Program selection uses start 101 only; programs are frozen before 202/303. This fixes the concrete pilot budget before execution.
