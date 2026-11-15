# Checkpoint retention for the v2 campaign

Tinker's free checkpoint-storage cap is separate from training/inference credits. [Official storage documentation](https://tinker-docs.thinkingmachines.ai/administration/checkpoint-storage-pricing/).

The first repair removed 26 consumed, temporary RL rollout samplers. It preserved the exact ten-update/thirteen-group optimizer/RNG prefixes for seeds 17 and 29. [Cleanup receipt](https://github.com/howdymary/compute-forecasting/actions/runs/43677120366).

A second bounded cleanup removed only six redundant **zero-update optimizer-state copies** created for this v2 campaign. Each initial model's reported sampler checkpoint was verified through Tinker's metadata API before and after deletion. [Actual retention run](https://github.com/howdymary/compute-forecasting/actions/runs/43679669037).

What remains:
- All 24 reported SFT model-weight checkpoints, including the six update-zero models.
- All 18 nonzero SFT optimizer states (updates 20/50/100), including every selected SFT parent.
- All originally frozen v1 resources, which were outside the cleanup scope.
- Every development-evaluated RL model and the latest optimizer/RNG recovery state per running RL model.

The removed copies contained zero optimization steps. This is storage lifecycle management; no model weights, numerical scores, selection rules or reported checkpoint IDs changed. Owner-private manifests mark those six initial optimizer copies as removed. Their sampler IDs remain usable for the original evaluation/replay; those IDs hash private resource paths rather than weight bytes.

| Seed / objective | Preserved initial model ID | Removed zero-step optimizer-copy ID | Selected update retained |
| --- | --- | --- | ---: |
| 17 / hard | dedb227b22f44acdf9fa | d6e803376f28362af8c0 | 20 |
| 17 / soft | ce871ad00d7b34114e32 | 53a2e2fb8fc3cbe99260 | 100 |
| 29 / hard | 4da183bf265cba1cacb6 | a7eb5f03ba97d3d1ccfb | 20 |
| 29 / soft | af14b10a060f0249b04f | 332a7d2a578a5029c8bc | 20 |
| 43 / hard | 9199b3aa82b4e5631028 | 2d78e65b296c89f20b89 | 20 |
| 43 / soft | 3debe18fdb74032d315d | 461796526f7aa1262d53 | 50 |

Cleanup source: 71ac48ab91e5899b536aa60f5e2c00e2ed8f63b7. Audit ID: 595bc28b50074ad9a42c37f3faa34933. Private model paths are excluded from this note and its JSON receipt. No billing settings changed.

During RL, consumed rollout samplers are deleted after sampling completes. A new optimizer recovery state is saved before its superseded unevaluated predecessor is deleted. Evaluated model states are preserved. Interrupted prefixes are included in their continuation's cumulative update count and must not be counted twice.
