# Development preview: stepping after the books

These notes retain intermediate development snapshots. The [completed study and final tests](contact-v18-assessment.md) are now available.


## Checkpoint 4

[Inspect the latest evaluated stepping](https://howdymary--mochi-contact-v18-demo-web.us-east.modal.run/?scenario=development-185000&checkpoint=4&phase=desk) · [Complete recorded attempt](https://howdymary--mochi-contact-v18-demo-web.us-east.modal.run/?scenario=development-185000&checkpoint=4)

Checkpoint 4 completed the continuous clock, book descent, drawer, Post-it crossing, laptop and globe sequence on development scenarios 185000 and 185002, without a fall or forbidden contact. Their lateral-path spans were 6.73 and 6.66 cm, above the frozen 6 cm limit. Scenario 185001 failed during laptop contact. This is 2/3 task completions and 0/3 completions within every quality limit. It cannot establish the declared smoothness or efficiency improvement.

| Development checkpoint | Complete routes | Within all quality limits |
| --- | ---: | ---: |
| Parent | 2/3 | 1/3 |
| 1 additional update | 0/3 | 0/3 |
| 4 additional updates | 2/3 | 0/3 |
| 16 additional updates | 1/3 | 0/3 |

Checkpoint 4 chose the shorter clock reach, the lifted walking option and the steady laptop press in these attempts. All three post-descent desk legs completed with approximately 4.8 mm median minimum-sole clearance and 128 measured moving swings. The parent had approximately 2.5 mm and 116 swings. More visible stepping has not established fewer steps. The viewer offers all three cases and checkpoints 0, 1 and 4, with exact checkpoint identifiers.

Sixteen optimizer updates have finished, and development evaluation retained checkpoint 0, the parent. None of the trained checkpoints completed a route within every quality limit. Checkpoint 16 completed 1/3 routes; its other attempts stopped on printer contact during laptop approach and a laptop-task timeout. Fresh tests are pending. Parent and selected final cohorts use the same saved weights, so their repetitions cannot establish a training gain. The final selection rule and quality limits are unchanged.

## Checkpoint 1 and the measurement method


Tinker completed 16 additional optimizer updates and 96 domain-gradient calls. Physical evaluation is still running. This preview shows checkpoint 1 against its parent on all three development scenarios. It is not a final checkpoint selection or a fresh-scenario result.

[Inspect the physical steps](https://howdymary--mochi-contact-v18-demo-web.us-east.modal.run/?scenario=development-185001&checkpoint=1&phase=desk) · [Full episode comparison](https://howdymary--mochi-contact-v18-demo-web.us-east.modal.run/?scenario=development-185001&checkpoint=1) · [Execution](https://github.com/howdymary/mochi-demo/actions/runs/44800327838)

## What changed

Book traversal uses planned contact footsteps. The following flat-ground leg uses a fixed native gait with low foot clearance. W8 adds a contact-gated lift through joint-actuator targets. The recorded foot movement is physical simulation, with no root repositioning, hidden support or added render animation. Tinker trains the model that chooses this controller, task profiles and recovery actions. The native gait network stays fixed.

The first checkpoint chose W8 for the post-descent leg in all three development scenarios. Measured sole clearance increased, but complete-route performance regressed. All attempts remain visible.

| Development seed | Parent clearance, mm | Checkpoint 1 clearance, mm | Parent moving swings | Checkpoint 1 moving swings | Later checkpoint 1 outcome |
| --- | ---: | ---: | ---: | ---: | --- |
| 185000 | 2.53 | 4.83 | 116 | 128 | invalid fixture contact |
| 185001 | 2.53 | 4.83 | 116 | 128 | fall |
| 185002 | 2.54 | 4.83 | 116 | 128 | invalid fixture contact |

Clearance is the peak of the lowest collision-pad point on a swinging foot above the local surface, with the other foot loaded. The table covers the verified descent exit through arrival at the drawer. It excludes book steps and station alignment. It is a descriptive diagnostic, not a changed checkpoint-selection rule.

Checkpoint 1 completed 0/3 full routes, with one fall during laptop contact and two forbidden contacts on the subsequent globe approach. The parent completed 2/3, with 1/3 within every quality limit. Higher clearance does not establish better complete-task performance, fewer steps or reduced arm travel.

The two guarded training trajectories also contain an identical rounded drawer-walk observation with different valid teaching labels, W4 and W8. One matched W8 branch exceeded the frozen acceleration limit; the other passed. A deterministic model cannot distinguish physical states that have the same input. The completed assessment will retain this limitation.

## Playback and provenance

Each pane is an uninterrupted recorded MuJoCo attempt. Both use the same physical-time clock and playback speed. The inspection link jumps both panes to the same time inside their overlapping post-descent walking intervals, uses the foot camera and plays at a labelled 0.5×. Restart returns to the full sequence. The interface retains every development case and its failure.

Execution source: `bdba8600e9abb94c20aa1dc68ee617b51ee4999c`. Parent recordings retain the earlier execution source and workflow. The presentation snapshot uses the original parent artifact hash. Checkpoint 1 archive descriptors were reconstructed by hashing the immutable full and public provider files; the snapshot records that assembly provenance. No additional physical trials or optimizer updates were used to build this preview.

[Recording manifest](../web/desk/contact-v18/manifest.json) · [Training interface](contact-v18-training-interface.md) · [Earlier fixed-controller preflight](contact-v18-preflight.md)

The fixed preflight completed all four tasks before training, but exceeded the lateral-motion quality limit. It remains available at its explicit preflight URL and is not credited to the trained model.

Browser verification covered a complete uninterrupted parent/checkpoint replay, all three development failures, post-descent foot inspection and the live inspection link. No browser exceptions or console errors were observed. [Full replay verification](../evidence/contact-v18/development-preview-browser-qa.json) · [Live inspection verification](../evidence/contact-v18/development-preview-phase-qa.json) · [Published release](../evidence/contact-v18/development-preview-live-health.json).

Checkpoint 4 verification covered a complete uninterrupted replay of development scenario 185000 and inspection of every checkpoint 4 quality failure. An explicit checkpoint query was also checked against a different preview default. [Checkpoint 4 browser verification](../evidence/contact-v18/development4-preview-browser-qa.json) · [Checkpoint query verification](../evidence/contact-v18/checkpoint-query-qa.json).

The checkpoint 4 release was also checked live with the 0.5× foot camera, actual shared physical time and pending-selection disclosure. [Live checkpoint 4 inspection](../evidence/contact-v18/development4-preview-phase-qa.json) · [Release health](../evidence/contact-v18/development4-preview-live-health.json).

After development selection, browser verification checked the retained-parent disclosure, identical-recording comparison label and all three rejected checkpoint 16 attempts through their actual endpoints. [Selection and rejected-checkpoint verification](../evidence/contact-v18/selection-browser-qa.json).

The published selection snapshot retains all twelve development recordings. Live verification checked the no-promotion disclosure while replaying checkpoint 4 steps at a labelled 0.5×. [Live retained-parent verification](../evidence/contact-v18/selection-preview-phase-qa.json) · [Published selection snapshot](../evidence/contact-v18/selection-preview-live-health.json).
