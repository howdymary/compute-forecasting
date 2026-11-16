# Checkpoint retention, November16,2026

The user-authorized age-based cleanup removed87 Tinker checkpoint files created on November14 in America/Los_Angeles. All13 newer checkpoint files were preserved. [Hash-only receipt](../results/evidence-v14/audits/43965321841/older-checkpoint-cleanup.json).

Published forecasts, evaluations, source snapshots, configurations, selection metadata and episode traces were not rewritten. Arithmetic can still be reconstructed from retained public predictions and traces. Repeating inference from the removed older model files is no longer available through those Tinker checkpoints. Rerunning their original training requires the documented data, configuration and authorized model access; stochastic outputs can differ.

The new paired study saves its own states at20/50/100 without redundant copies of the public base model. No billing setting was changed. New states have the registered30-day retention. Private checkpoint paths are excluded from public artifacts.
