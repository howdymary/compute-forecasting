# V15 walking and task-control results

Tinker completed 16 optimizer updates and 96 domain gradient calls. Development selected update 16.

| Checkpoint | Qualified complete | Steps on qualified completions | Physical seconds |
|---|---:|---:|---:|
| 0 | 3/3 | 805.33 | 265.50 |
| 1 | 3/3 | 583.33 | 237.95 |
| 4 | 3/3 | 494.67 | 219.03 |
| 8 | 3/3 | 488.00 | 218.20 |
| 16 | 3/3 | 485.33 | 218.11 |

| Final-test policy | All four tasks | Qualified complete | Steps on qualified completions | Physical seconds |
|---|---:|---:|---:|---:|
| parent | 4/4 | 4/4 | 806.00 | 266.43 |
| selected | 4/4 | 4/4 | 476.50 | 219.53 |
| fixed | 4/4 | 4/4 | 809.50 | 264.91 |
| static | 4/4 | 4/4 | 482.00 | 219.14 |

The 20% step-reduction goal was met on this cohort.
Paired efficiency uses 4 scenarios where both policies completed within all declared quality limits.
Mean step reduction: 40.9%; mean completion-time reduction: 17.6%.
Step reduction paired bootstrap interval: 39.4% to 41.8%. This describes the small observed cohort.
Time reduction paired bootstrap interval: 15.7% to 18.7%. This describes the small observed cohort.

## Comparison with training-derived static choices

The selected and static policies made the same categorical choice in 46/48 corresponding decisions. Their complete choice vectors matched in 2/4 scenarios.
The static policy uses station-specific preferences chosen only from training labels. Compare its full completion, step and time results above before attributing gains to adaptive selection. Cost differences between identical categorical choice vectors remain unexplained; no repeated-policy numerical-variance study was run.

## Motion tradeoffs and uncertainty

Average total arm-joint travel per successful recovery increased from 5.54 to 6.93 radians. This sums joint-angle travel; it is not hand-path length or energy.
Mean torso roll RMS was 0.271 degrees for the parent and 0.279 degrees for the selected policy. Both stayed within the declared limits. The step reduction does not establish smoother motion in every measure.
Each 4/4 completion result has an approximately 51% to 100% Wilson interval at 95% confidence. The paired bootstrap intervals describe only these four fixed-layout cases; they do not establish reliability across other layouts or hardware.

## Exact-state component checks

The fixed reference route at seed 93000 supplied twelve physical states. Both models were tested from each state, giving twenty-four separate branches. These are diagnostic comparisons, not additional continuous sequences.

| Exact-state test | Parent action / success | Selected action / success |
|---|---|---|
| alarm:alarm | C / True | F / True |
| drawer:drawer | A / True | C / True |
| globe:globe | A / True | G0 / True |
| laptop:laptop | P0 / True | P1 / True |
| recovery:alarm | R0 / True | R1 / True |
| recovery:drawer | R0 / True | R1 / True |
| recovery:globe | R0 / True | R1 / True |
| recovery:laptop | R0 / True | R1 / True |
| walk:alarm | W0 / True | W2 / True |
| walk:drawer | W0 / True | W4 / True |
| walk:globe | W0 / True | W4 / True |
| walk:laptop | W0 / True | W4 / True |

Component success is the recorded branch outcome. Contact, balance and smoothness measurements remain in the numerical assessment; these branches are separate from the full continuous sequences.

Observed final-test failures:
- parent: none in this cohort.
- selected: none in this cohort.
- fixed: none in this cohort.
- static: none in this cohort.

Physical rollouts: 204/224. Function CPU-hours: 10.341/18. This is measured function execution, not an invoice.

Small fixed-layout simulation cohort; no hardware or broad reliability claim.
Native gait weights and the physical controller library stayed fixed.
Matched success costs exclude pairs where either policy fails; all failures remain in completion denominators.
Exact-state component branches are diagnostic evidence, not the continuous demo.
Shared-memory and search usage are verified separately from causal benefit; no memory/search ablation.

[Run evidence](https://github.com/howdymary/mochi-demo/actions/runs/44625135986) · [Checkpoint demo](https://howdymary--mochi-efficient-v15-demo-web.us-east.modal.run/)
