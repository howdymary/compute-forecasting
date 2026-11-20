# Development preview: stepping after the books

Tinker completed 16 additional optimizer updates and 96 domain-gradient calls. Physical evaluation is still running. This preview shows checkpoint 1 against its parent on all three development scenarios. It is not a final checkpoint selection or a fresh-scenario result.

[Inspect the physical steps](https://howdymary--mochi-contact-v18-demo-web.us-east.modal.run/?scenario=development-185001&phase=desk) · [Full episode comparison](https://howdymary--mochi-contact-v18-demo-web.us-east.modal.run/?scenario=development-185001) · [Execution](https://github.com/howdymary/mochi-demo/actions/runs/44800327838)

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
