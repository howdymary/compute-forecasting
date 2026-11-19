# Balanced furnished-desk study (V11)

**Status: incomplete. The physical reference was rejected; zero new Tinker
optimizer updates completed.** The 64-attempt local calibration limit and a
separate four-test remote correction stage are complete. A valid terrain
controller is still needed. See [results, receipts and next experiment](balanced-v11-results.md).

[Recorded engineering attempts](https://howdymary--mochi-curriculum-demo-web.us-east.modal.run/balanced.html)
show original support transfers, intermediate failures, the rejected full-task
recording and four strict correction attempts. They are not trained checkpoints.
The [V8 trained demo](https://howdymary--mochi-curriculum-demo-web.us-east.modal.run/)
remains unchanged.

## Current implementation

- MuJoCo advances the free physical root through actuator forces and contacts.
  The scene uses the original G1 body, fixed book terrain, printer and props.
- A pinned externally pretrained flat-ground G1 ONNX policy is adapted to the
  miniature robot. Those gait weights remain fixed. It has not established
  safe book traversal.
- Continuous waypoint tracking preserves gait history through route corners.
  Contact loads and an approximate capture-point calculation screen stops.
  Captured-stance control supports manipulation. These are engineering changes.
- Fixture checks now include task objects throughout walking and manipulation;
  only intended foot support and active-hand target contact are exempted.
- The prepared Tinker interface selects walking speeds, task contact profiles
  and arm-recovery primitives. It would train Qwen LoRA decision weights,
  rather than the native locomotion network. Its old frozen physical reference
  is invalid, so it is gated off.

The [pre-audit methods snapshot](archive/balanced-v11-pre-audit.md) preserves
what was believed before contact validation failed. It must not be read as
current evidence. Original artifacts and the invalidated frozen protocol are
retained for comparison, not reused silently for new training.

## Inspect without starting training

From the repository root:

```sh
PYTHONPATH=mochi/src mochi/.venv/bin/pytest -q \
  mochi/tests/test_balanced_v11.py mochi/tests/test_control_v8.py \
  mochi/tests/test_richdesk.py
node mochi/scripts/check_balanced_ui.mjs
mochi/.venv/bin/python mochi/scripts/diagnose_balanced_motion.py
python3 -m http.server 4028 --directory mochi/web/desk
```

Open `/balanced.html` on the replay server. Rendering uses measured body
transforms; the chart reads retained measurements and executes no rollout.
The local attempt ledger refuses attempts beyond its cap. Existing GitHub
Actions secrets provide backend service access; local keys are absent.

## Files and evidence

- Runtime and measurements: `src/mochi/balanced/`.
- Scene and caps: `configs/richdesk-v9.json`, `configs/balance-v11.json`.
- Exact execution record: `evidence/balance-v11/execution-index.json`.
- Contact verdict: `evidence/balance-v11/reference-audit.json`.
- Strict failures: `evidence/balance-v11/clearance-results.json`.
- Corrected memory: `evidence/balance-v11/audit-memory.json`.
- Cancellation before gradients: `evidence/balance-v11/cancellation.json`.
- Public recordings: `web/desk/balanced-v11/`.

The forecasting application, archived results, canonical trained states and
active checkout are preserved. The only root integration additions are Mochi
workflows. [Current service inventory](integrations.md).
