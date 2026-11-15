# Executed study · November 15, 2026

Source: [successful remote workflow](https://github.com/howdymary/compute-forecasting/actions/runs/43762703104),
commit `4783a7ab669ce5b9bfffcfdb73a9c8dd69ceb81a`.
Run ID: `mochi-545d258f7f4e`.

| Condition | Starting policy | Research-selected | Conventional control |
|---|---:|---:|---:|
| Development, n=8 | 1/8 | 7/8 | 6/8 |
| Held out, n=12 | 2/12 | 8/12 | 6/12 |
| Higher friction and mass, n=8 | 2/8 | **1/8** | 6/8 |

The principal finding is conditional improvement plus a robustness failure.
The research-selected controller performed better on held-out draws from the
development distribution, then failed badly under the registered physical shift.
It is not suitable for a general robustness claim. All three had zero episodes
invalidated by the implemented finite-state/table-boundary checks; these checks
are much narrower than robot safety.

The selected policy uses object-pose feedback. The critic rejected round 1 even
though the deterministic development gate passed, then accepted round 2 with
limits. No weights were trained. The fixed base and simplified collisions remain.

## Sponsor execution evidence

- Two actual Exa main-loop searches, with source URLs and 24-word maximum excerpts.
- Nine actual Tinker bounded decisions across four distinct role contexts.
- Four past.dev writers and readers, eleven source-ID-verified cross-agent reads.
- A critic-private synthetic canary was readable by the critic and absent from
  the researcher's recall. No general security guarantee is inferred.
- 188 actual Modal rollouts, at most eight one-CPU/1 GiB workers.
- Research and conventional candidate search each used 48 simulations. Baseline
  and final evaluations were additional and separately counted.

## Important limits on the comparison

The research loop chooses among registered controller families, including
feedback, while the conventional control samples open-loop parameters. This
comparison does not isolate search intelligence from controller-family access.
The research arm also incurs additional retrieval and model inference costs.
There is no controlled no-Exa or no-memory ablation, so neither service's causal
accuracy benefit is established. The result demonstrates a real integrated
research workflow, not a new best-known robot policy.

The local conventional preview is a separate 12-candidate study (96 search
rollouts), with 9/12 held-out successes versus 3/12 initially. It uses a different
budget and platform; do not pool those results with the live study. Contact
simulation can diverge across platforms despite matching configuration and seed.
Use recorded Linux trajectories to replay the sponsored study exactly.

## Next experiment, not yet executed

Register a broader development distribution and a matched policy-family control;
then evaluate on fresh seeds. Reusing these inspected held-out conditions for
selection would turn them into development data. Preserve this study as-is.
