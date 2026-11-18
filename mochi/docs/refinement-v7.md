# Geometry-encoded walking and force-aware task selection

This is a separate follow-up to the 64-update pilot. That pilot reached three of ten development waypoints and completed two alarm tasks, but no complete route. The new study keeps every physical controller, action, task, validity rule and success threshold unchanged. It changes the model's observation representation, sampling and task-label objective. V6 remains archived; a change in results between studies cannot be attributed to any one of those changes.

Starting and post-trained weights both receive the same independent bins of observable relative geometry: distance, bearing, final heading, forward/lateral offsets and dominant offset axis. The encoder does not compute a teacher action. Raw observations remain in the recorded decisions. Duplicating encoded training observations is removed, and any encoding that aliases different teacher actions causes the run to stop. The existing 814 measured training observations map to 111 distinct encoded states, with zero label conflicts; additional training-only navigation trials extend that coverage.

Tinker post-trains Qwen3.5-4B with LoRA rank 16 from the archived **starting** optimizer state. This is a new 96-update study, not a continuation whose baseline already had 64 updates. Every update makes separate gradient calls for walking and all four tasks, followed by an actual optimizer step. Walking samples balance action classes, then distinct encoded observations. Contact labels use only successful physical trials and prefer lower peak contact force before shorter duration. Cases with no successful profile are counted and excluded. Repeated batches do not create new physical evidence.

Up to six fixed inference snapshots at 0, 8, 16, 32, 64 and 96 updates each run the complete physical route on development scenarios 15000 and 15001. Isolated contact decisions are checked on scenarios 15000 and 15001. The run stops at update 64 only if both development routes complete all four tasks without falling; otherwise it continues to the fixed 96-update cap. This stopping rule is frozen before the new evaluations. Fresh full-route and contact scenarios 16000–16003, plus eight independent walking goals at seeds 16500–16507, remain sealed until training finishes. Numerical verifiers have no model-editable interface. All checkpoints, including regressions, remain in the trajectories and report.

Each unique encoded state is actually scored by that checkpoint through Tinker. Repeated identical encodings reuse the returned distribution. The cache contains model predictions, not teacher decisions, a fitted surrogate, or a fallback controller. Each checkpoint gets a separate empty cache. Exact distributions and cache counts are retained. This reduces repeated API latency without changing the policy for an encoded observation.

The free storage limit leaves room for one additional canonical optimizer state. The already archived starting state and development-selected final full state (64 or 96) are durable. Intermediate fixed inference snapshots are real but ephemeral; their session receipts, evaluated trajectories and numerical results persist after the snapshots expire. We do not delete unique historical checkpoints or change billing. An interrupted follow-up before its final save is not guaranteed to recover its optimizer at an intermediate update.

The research loop performs real failure-directed Exa searches. Source-verified past.dev recalls connect separately identified research, design, execution and criticism roles. Model decisions choose a search focus, equal-budget training allocation and the emphasis of 32 additional training navigation trials. A private critic canary checks audience isolation. The final criticism distinguishes measured changes from claims not established by a four-scenario simulation pilot. No causal sponsor ablation is claimed.

Modal runs new navigation coverage, isolated contact experiments and the complete model feedback loop. Each final before/after/classical triplet shares one worker. No open-loop cross-runtime action replay agreement is assumed. CPU workers are bounded at eight, and the workflow shares a concurrency group with V6 to avoid overlapping experiment batches. The follow-up allows at most 96 additional optimizer updates and remains within the overall 3,000-trial ceiling. The physics is authoritative MuJoCo; the unchanged Unitree gait, classical standing balance and arm IK supply the motor-level foundation. This trains command/profile decisions, not raw leg torques or a new balancing network.

Run from the repository root with existing backend credentials:

```sh
python mochi/scripts/fetch_visual_models.py
# Restore the source run named in configs/refinement-protocol.json into mochi/.cache/refine-source.
PYTHONPATH=mochi/src mochi/.venv/bin/python -m mochi.curriculum.refine
```

The additive `mochi-refinement.yml` workflow injects the existing secret references explicitly and archives results under `mochi/artifacts/refinement-v7`. Public renderers receive no provider credentials or private model paths. The new Sand3D clock is a visual adaptation with the same cap contact envelope and recorded transforms; it changes no physics between checkpoints.

The first attempt was cancelled during dependency installation, before any gradient updates. Revision 2 uses the verified credential-stripped Tinker multiprocessing adapter inside Modal physics. The V6 replication had 0/4 trained full routes versus 2/4 for the classical controller, despite a walking gain from 0/20 to 6/20 waypoints; that observed limitation motivates this separately tested follow-up. Neither V7 test seeds nor their outcomes informed the changes.
