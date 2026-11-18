# V7 locomotion-command and contact-control post-training

Tinker completed 96 optimizer updates and 480 domain-gradient calls for walking, alarm, drawer, laptop and globe. This is a separate study starting from the archived update-zero state, not an additional 96 updates on V6 update 64. Qwen3.5-4B LoRA rank 16 learns body-velocity commands and contact-profile choices. The model reads simulation state, not camera images. The Unitree gait network, standing balance, arm IK and physical verifiers remain fixed.

## Matched physical results

| Policy | Full routes | Waypoints | Falls |
|---|---:|---:|---:|
| Starting weights | 0/4 | 0/20 | 1 |
| Update 96 | 1/4 | 20/20 | 0 |
| Classical + fixed profiles | 1/4 | 19/20 | 1 |

The desk layout and task order are fixed. Held-out seeds vary the initial robot pose and passive object dynamics; isolated walking uses separate goal offsets. These are not unseen-room or vision tests. The four fresh route seeds were unsealed after development selection. All three policies run closed-loop on the same Modal worker per scenario. This is a small simulation pilot, not a hardware or general reliability claim. Isolated navigation and contact tests are separate from full routes. Their exact results, intervals and per-scenario outcomes are in the numerical receipt.

## Actual learning and memory

Consumed examples, including repeats: alarm 768, drawer 768, globe 768, laptop 768, walk 3072. The report retains actual optimizer receipts and per-domain losses. Every public model action is checked against its recorded distribution and encoded observation; paired full-route initial states match exactly.

past.dev recorded 11 writes, 11 recalls and 244 ingestion polls. 9 cross-role recalls verified the exact source ID. Private-audience isolation passed. Credit charges are unavailable; call counts are not billing estimates. Recalled research proposals selected the predeclared walking/contact batch allocation. The frozen run performs this adaptation at initialization and update 16, not at every checkpoint. There is no causal memory or search ablation.

Exa ran 3 source-grounded searches. Modal recorded 274 new executions in this study, including two short recovery inference probes; earlier physical training evidence was reused and is identified separately.

## Movement and visual inspection

The demo shows actual uninterrupted physical episodes at saved checkpoints. Side and foot views use the same playback speed. The first declared development seed is the primary checkpoint view; all four held-out before/after pairs are available. The complete-test button is a successful example selected after evaluation and labeled separately; it does not replace the default development view.

Movement diagnostics were introduced after this run began. They are explicitly post-hoc, not its training reward. Matched initial windows end at the earliest checkpoint episode termination, up to 20 seconds. Torso tilt and yaw travel come from 25 Hz body transforms; command changes describe requested velocity, not measured motor jerk. Recorded loaded-foot slip spans the entire episode. True sole clearance and motor work are unavailable in these recordings.

The separate gait-modulation calibration did not establish a consistent gain, so its cadence changes are not promoted. See [calibration](gait-calibration.md). No new gait-network training is claimed.

## Reproduction and provenance

Source workflow: [44266707804](https://github.com/howdymary/mochi-demo/actions/runs/44266707804). Frozen source: `b459cadaaa34dfbecfaef5fa841a7298475fced0`. The published result links actual training and experiment records rather than inferred completion. Evaluation recovery performs zero extra optimizer updates and retains the original failure. Canonical optimizer paths stay in the private execution artifact. Intermediate fixed inference snapshots have the retention limits stated in the protocol.

```sh
gh run download 44266707804 --repo howdymary/mochi-demo --dir mochi/.cache/refinement-result
PYTHONPATH=mochi/src mochi/.venv/bin/python mochi/scripts/check_refinement.py --source mochi/.cache/refinement-result/mochi-refinement-evaluation-44266707804
PYTHONPATH=mochi/src mochi/.venv/bin/python mochi/scripts/analyze_movement.py --source mochi/.cache/refinement-result/mochi-refinement-evaluation-44266707804 --out mochi/.cache/refinement-result/mochi-refinement-evaluation-44266707804/movement-diagnostics.json
python3 mochi/scripts/export_curriculum.py --source mochi/.cache/refinement-result/mochi-refinement-evaluation-44266707804 --run-id 44266707804
```

The small public receipt and CSV tables live in `mochi/evidence/refinement-v7/`. Do not reclassify previously inspected seeds as fresh tests or combine V6 and V7 outcomes as independent samples.
