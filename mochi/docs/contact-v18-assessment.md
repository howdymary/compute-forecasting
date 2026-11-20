# Laptop contact and flat-ground stepping study

Tinker completed 16 additional optimizer updates on the six-domain Qwen3.5-4B LoRA controller selector. Development selection chose update 0. The declared joint improvement target was not met.

No newly trained checkpoint was promoted. The parent and selected final cohorts use the same saved weights, so any difference between those repetitions cannot establish a training gain. The unpromoted development checkpoints retain their measured foot-lift changes and failures.

The model chooses walking strategies, manipulation profiles and arm recovery from structured simulator state. The camera is a rendered replay. The native ONNX gait weights remain fixed. The bounded laptop force controls and foot-lift correction are controller engineering shared by the parent, intermediate checkpoints and fixed controls.

[Continuous checkpoint replay](https://howdymary--mochi-contact-v18-demo-web.us-east.modal.run/) · [Execution and artifacts](https://github.com/howdymary/mochi-demo/actions/runs/44800327838) · [Numerical audit](contact-v18-assessment.json)

## Fresh final scenarios

| Policy | Complete | Within quality limits | Qualified clear stepping | Mean steps | Seconds | Recovery travel, rad | Intertask arm travel, rad | Moving sole clearance, mm |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| parent | 1/4 | 0/4 | 0/4 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| selected | 1/4 | 0/4 | 0/4 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| fixed | 0/2 | 0/2 | 0/2 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |
| static | 1/2 | 0/2 | 0/2 | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |

Cost and clearance means use qualified completions only. Recovery travel is the mean joint travel per recovery. The replay counter totals all recoveries. An early failed attempt is not a cheap successful run.

Matched qualified pairs: 0. Step reduction: Unavailable. Recovery-travel reduction: Unavailable. Time reduction: Unavailable.

Intertask arm-travel reduction: Unavailable. This includes walking, turning and recovery. Native walking arm swing remains fixed. A reduction in recovery travel alone does not establish less total arm movement between tasks.

The frozen joint target requires all four fresh scenarios to complete within the quality limits and meet the 4.5 mm moving-sole-clearance target, at least two qualified pairs, at least 10% fewer steps and 15% less recovery joint travel, without longer successful time. Four scenarios in one layout do not establish reliability on other desks or hardware.

## Why the old walking looked like a shuffle

Book traversal uses planned contact footsteps. Flat-ground travel then switches to a fixed ONNX gait with much lower swing clearance. A 25 Hz replay could also hide short lift peaks. The new recorder targets 100 Hz during flat transit and renders the measured body transforms at their actual timestamps.

W8 adds a contact-gated 6 mm lift and 2 mm forward reference to the original walking controller. The joint correction is capped at 0.10 rad and changes at no more than 2 rad/s. It requires the opposite foot to carry at least 0.65 N. It is disabled for tiny station-alignment commands. It changes actuator targets, with no physical root repositioning or render-only foot movement.

Clearance is measured at the lowest physical collision-pad point on the sole relative to the local terrain, while the opposite foot is loaded. Moving and turning swings are reported separately from alignment. Every detected step still counts toward the efficiency objective.

The accepted local matched corridor test increased median minimum-sole clearance from 2.55 mm to 4.78 mm, but increased measured steps from 44 to 56 and physical time from 6.26 to 7.74 seconds. This engineering result motivated the experiment. It was not a checkpoint improvement or an efficiency gain.

## Laptop repair and learning data

P5 regulates upper-edge contact using lid angle, closing speed and measured foot loads, with a bounded pulse finish. P6 uses bounded intermittent contact. These controls passed three opened regression states with withdrawal. The old opened 103xxx cases are regression and training evidence, not fresh tests.

Two guarded training sequences supplied 52 measured candidate branches. Each label was checked against valid branches starting from the same physical state. Three validated regression examples were added for laptop selection. No successful trajectories were invented.

The parent proposes actions, measured branches determine the accepted action, and the main trajectory executes that accepted action. Overrides therefore change subsequent states. The training states come from guarded trajectories, rather than exclusively from the unmodified parent policy.

Training, development and final seeds are disjoint. The final seeds were unopened until the development-selected checkpoint was saved. Every optimizer update included walking, clock, drawer, laptop, globe and recovery examples. There were 96 completed domain-gradient calls. A change in selection probability verifies a changed decision policy; physical improvement requires the separate simulation results.

## Checkpoint progression

| Additional updates | Complete | Qualified | Clear stepping | Falls | Forbidden contacts |
| --- | --- | --- | --- | --- | --- |
| 0 | 2/3 | 1/3 | 0/3 | 0 | 1 |
| 1 | 0/3 | 0/3 | 0/3 | 1 | 2 |
| 4 | 2/3 | 0/3 | 0/3 | 0 | 1 |
| 8 | Saved, not evaluated | Unavailable | Unavailable | Unavailable | Unavailable |
| 16 | 1/3 | 0/3 | 0/3 | 0 | 1 |

The parent has 121 cumulative updates. The counts above are additional updates in this campaign. Five states were saved; four checkpoints were physically evaluated. All physical comparisons use the same frozen scene, controller library, route, verifiers and quality limits.

Before training and final tests, the paired runtime was extended to 3600 seconds after one parent input took nearly 24 minutes. The completed baselines were retained. Update 8 remained saved without physical evaluation, and fixed/static controls used the predeclared seeds 186000 and 186001. The four fresh parent/selected pairs and original improvement criteria remained unchanged. See the [runtime amendment](contact-v18-runtime-amendment.md).

## Attribution and failures

Parent and selected final tests run sequentially in the same worker from reset. 0/4 pairs had a different physical state or time during their shared action prefix. Such variation cannot be attributed to learned selection. The numerical audit retains every prefix check.

The audit also checked 9 adjacent-checkpoint development pairs. Pairs with matching actions until the shorter attempt stopped and differing completion: 1. In those pairs, actions agreed until the shorter attempt stopped, while completion differed. Those outcome differences do not demonstrate improved or degraded action selection. The state hashes are bitwise checks, not a measure of physical distance or tolerance.

The selected policy and training-derived static control chose identical complete action sequences in 0/2 matched control scenarios. This audits observed choices. Matches do not establish identical predictions or causality; differences do not establish adaptive value.

The static preference uses the two guarded teachers. The selector additionally receives three laptop regression labels. The fixed heuristic uses the regression-derived lid-angle rule. These information differences limit a claim of equal-data superiority over the static control.

All failed attempts remain in the final table and replay. No checkpoint was selected using final-test outcomes. No service ablation establishes a causal improvement from Exa or past.dev.

| Policy | Seed | Last decision | Failure |
| --- | --- | --- | --- |
| parent | 186000 | laptop | fall |
| parent | 186001 | walk | invalid_fixture_contact |
| parent | 186002 | laptop | fall |
| selected | 186000 | laptop | fall |
| selected | 186001 | walk | invalid_fixture_contact |
| selected | 186002 | laptop | fall |
| fixed | 186000 | None | laptop-failed:laptop |
| fixed | 186001 | None | invalid_fixture_contact |
| static | 186000 | laptop | invalid_fixture_contact |

## Desk walking immediately after descent

This diagnostic covers moving and turning swings between the verified descent-exit stance and drawer-station arrival. Book steps and station alignment are excluded. It was added for the post-descent walking question and was not a checkpoint-selection or joint-goal criterion. A partially completed leg stays labelled incomplete.

| Policy | Seed | Leg completed | Measured moving swings | Median minimum sole clearance, mm |
| --- | --- | --- | --- | --- |
| parent | 186000 | Yes | 116 | 2.54 |
| parent | 186001 | Yes | 116 | 2.52 |
| parent | 186002 | Yes | 116 | 2.54 |
| parent | 186003 | Yes | 116 | 2.53 |
| selected | 186000 | Yes | 116 | 2.54 |
| selected | 186001 | Yes | 116 | 2.52 |
| selected | 186002 | Yes | 116 | 2.54 |
| selected | 186003 | Yes | 116 | 2.53 |
| fixed | 186000 | Yes | 128 | 4.83 |
| fixed | 186001 | Yes | 128 | 4.82 |
| static | 186000 | Yes | 116 | 2.54 |
| static | 186001 | Yes | 116 | 2.53 |

## Measured walking candidates used for training

These are candidate controllers tested from matched training states, not checkpoint gains. Each row covers the complete leg to its destination, including any book or paper transitions. The clearance column covers moving flat-ground swings only. Invalid candidates remain visible and cannot supply a positive training label.

| Seed | Destination | Controller | Valid | Teaching label | Sole clearance, mm | Steps | Physical seconds | Native acceleration RMS, rad/s² |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 184000 | drawer | W4 | Yes | Yes | 2.53 | 168 | 156.9 | 139.70 |
| 184000 | drawer | W5 | Yes | No | 2.55 | 170 | 148.0 | 138.97 |
| 184000 | drawer | W8 | No | No | 4.83 | 182 | 149.5 | 161.70 |
| 184000 | laptop | W4 | Yes | No | 2.56 | 144 | 64.7 | 140.85 |
| 184000 | laptop | W5 | Yes | No | 2.56 | 142 | 61.7 | 140.69 |
| 184000 | laptop | W8 | Yes | Yes | 4.83 | 170 | 65.2 | 157.05 |
| 184000 | globe | W8 | Yes | Yes | 4.66 | 122 | 16.7 | 154.28 |
| 184000 | globe | W5 | Yes | No | 2.48 | 134 | 18.2 | 136.31 |
| 184000 | globe | W6 | Yes | No | 2.48 | 120 | 16.5 | 138.60 |
| 184001 | drawer | W4 | Yes | No | 2.53 | 178 | 158.1 | 139.01 |
| 184001 | drawer | W5 | Yes | No | 2.55 | 164 | 147.3 | 138.02 |
| 184001 | drawer | W8 | Yes | Yes | 4.82 | 192 | 150.7 | 158.43 |
| 184001 | laptop | W4 | Yes | No | 2.56 | 142 | 64.4 | 141.62 |
| 184001 | laptop | W5 | Yes | No | 2.56 | 138 | 61.3 | 141.69 |
| 184001 | laptop | W8 | Yes | Yes | 4.82 | 162 | 64.2 | 159.31 |
| 184001 | globe | W8 | Yes | Yes | 4.66 | 124 | 17.0 | 153.49 |
| 184001 | globe | W5 | Yes | No | 2.48 | 130 | 17.7 | 135.67 |
| 184001 | globe | W6 | Yes | No | 2.47 | 116 | 16.0 | 136.59 |

The frozen native-acceleration limit is 161.4 rad/s². A completed route can still be invalid. More foot clearance can also require more steps; the final evaluation reports those costs separately.

Identical-observation groups with conflicting teaching labels across the two guarded trajectories: 1. The audit retains their observations, seeds and labels. A deterministic selector cannot choose different actions from identical inputs. Additional updates alone cannot recover physical distinctions removed by observation rounding, and a near-threshold validity change also motivates improving the controller's safety margin.

## Services and resource accounting

Accounted physical attempts: 142, including 58 local engineering attempts. Confirmed completed attempts: 138. Accounted simulation CPU-hours: 11.727. Limits were 160 attempts, 14 CPU-hours, 16 optimizer updates and four parallel workers. These are measured budget records, not a billing invoice.

Four unfinished stages and eight CPU-minutes were conservatively charged for two interrupted teacher inputs. Their reserved inference tokens were retained. A separate cloud wrapper check intentionally reached the invalid-action validator after physical initialization; its failed attempt was charged and provided no training label.

Each cloud function requests one CPU and 4096 MiB memory. The reused receipt helper carries a stale 3072 MiB memory label; that field is not an accurate allocation or billing receipt. The CPU-duration budget calculation is unaffected.

Tinker performed the optimizer updates, checkpoint storage and decision inference. Modal ran measured MuJoCo branches and uninterrupted evaluation episodes. Exa searched for contact and support mechanisms in the main research loop. past.dev carried the sourced hypothesis, experiment plan, actual results and qualified verdict across distinct identities, with source-verified reads and a private-canary access check.

Service usage: one Exa search, six past.dev writes and eight logical recalls. The memory log records four writing and four reading identities, a passed audience-isolation canary and no pending ingestion. Tinker completed 300,707 training-token presentations across the 16 updates.

An initial Modal image configuration failed before cloud physics or optimizer updates. The corrected execution preserved its research records, API usage and original campaign budget. No gradients were repeated by that setup recovery.

Frozen execution source: `bdba8600e9abb94c20aa1dc68ee617b51ee4999c`. Campaign: `mochi-c18-44790861532`. Execution workflow: `44800327838`. The audit verified all 212 frozen files and 20 public recordings. The 210 carried support files retain their original hashes. The amended execution changed the coordinator and added the paired wrapper.

## Reproduction

From the repository root:

```bash
PYTHONPATH=mochi/src mochi/.venv/bin/python mochi/scripts/build_contact_v18_preview.py --source mochi/.cache/contact-v18-completed
PYTHONPATH=mochi/src mochi/.venv/bin/python mochi/scripts/assess_contact_v18.py --source mochi/.cache/contact-v18-completed
node mochi/scripts/check_contact_v18_ui.mjs
python3 -m http.server 4120 --directory mochi/web/desk
```

Open `http://127.0.0.1:4120/contact-v18.html`. Exporting retained recordings requires the authenticated Modal profile. The public replay uses no service credentials. Exact model re-execution requires access to retained backend checkpoints and provider credentials.
