# V12 completed-training assessment

Tinker completed 32 new optimizer updates. Development selection chose update 1. Native gait weights stayed fixed.

| Development checkpoint | Complete | Within smoothness limits | Successful completion time |
|---|---:|---:|---:|
| 0 | 2/3 | 2/3 | 264.34 s |
| 1 | 3/3 | 3/3 | 255.02 s |
| 8 | 3/3 | 3/3 | 250.24 s |
| 32 | 3/3 | 3/3 | 254.25 s |

| Final test policy | Complete | Within smoothness limits | Verified book ascent / descent |
|---|---:|---:|---:|
| parent | 3/6 | 3/6 | 4/6 · 4/6 |
| selected | 6/6 | 6/6 | 6/6 · 6/6 |
| fixed | 5/6 | 5/6 | 6/6 · 6/6 |

Paired timing and movement comparisons use 3 final scenarios where both policies complete. Earlier failures are not counted as faster completions.
Mean selected-minus-parent differences: -3.68 s completion time; -0.002° torso-roll RMS; +0.045 rad recovery joint travel.

Remaining observed failures:
- parent: fall × 2, task-failed:laptop × 1.
- selected: none in this cohort.
- fixed: invalid_fixture_contact × 1.
  Contact: left_hip_roll_link with laptop-contact during release (1).

| Full-route decision-domain intervention | Parent complete | Selected complete | Same recorded profile choices |
|---|---:|---:|---|
| walking | 0/1 | 1/1 | No |
| manipulation | 1/1 | 1/1 | Yes |
| recovery | 1/1 | 1/1 | Yes |

The manipulation and recovery checks recorded the same profile choices for both models. They do not demonstrate a learned change in those domains.

The full-route domain interventions help identify which decision domain changes an outcome. They do not establish a matched-pose recovery or manipulation effect.

Small simulated cohorts; keep development separate from final tests.
Paired timing and movement changes exclude cases where either run fails.
Domain interventions are whole routes, not exact matched-pose manipulation tests.
Tinker updates decision weights; native gait and physical controllers stay fixed.

[Training receipts](https://github.com/howdymary/mochi-demo/actions/runs/44482272455) · [Evaluation receipts](https://github.com/howdymary/mochi-demo/actions/runs/44514013316)
