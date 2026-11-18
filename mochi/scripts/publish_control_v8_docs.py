"""Write the README from completed evidence, never prospective performance."""
import argparse,json,re
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--revision',choices=['v8','clearance'],default='v8');p.add_argument('--run-id',required=True);p.add_argument('--isolated-source',type=Path);a=p.parse_args();root=Path(__file__).resolve().parents[1];r=json.load(open(a.source/'report.json'));assert r['status']=='completed';b=r['held_out']['starting_model'];t=r['held_out']['post_trained_model'];f=r['held_out']['classical_fixed'];n=r['optimizer_updates_completed'];selected=r['selected_checkpoint']['update'];s=r['services'];m=s['eligibility'];calls=s['calls'];writes=sum(c['method']=='POST' and c['kind']=='ingest' for c in calls);reads=sum(c['method']=='POST' and c['kind']=='recall' for c in calls);iso=json.load(open(a.isolated_source/'report.json')) if a.isolated_source else json.load(open(a.source/'isolated-report.json')) if (a.source/'isolated-report.json').exists() else None;rollouts=r['rollouts'] if r.get('training_reused') else r['rollouts']+(iso['rollouts'] if iso else 0)
block=f'''<!-- MOCHI_CURRICULUM_START -->
## Current: Learning walking, task and arm-recovery decisions

[Interactive before/after demo](https://howdymary--mochi-curriculum-demo-web.us-east.modal.run/) · [V8 methods](docs/control-v8-study.md) · [Numerical evidence](evidence/control-v8/results.json) · [Training execution](https://github.com/howdymary/mochi-demo/actions/runs/{a.run_id}) · [Archived V7 viewer](https://howdymary--mochi-curriculum-demo-web.us-east.modal.run/?study=v7)

A 22.1 cm Unitree G1 walks around one desk, silences an alarm, closes a drawer and laptop, then aligns a globe. Each displayed checkpoint is a separate uninterrupted MuJoCo episode. The interface replays the recorded robot and object transforms, with synchronized before/after views and actual model decisions.

Tinker completed **{n} additional optimizer updates and {n*6} domain-gradient calls**, resuming the retained V7 update-96 state. Every update trains walking commands, all four task-profile choices and active-arm recovery. The Qwen3.5-4B LoRA selector reads simulation state. The native gait network, standing balance, arm IK and physical motion primitives remain fixed. This is command/profile learning, not learning motor torques or gait-network weights.

Development selection chose **{selected} additional updates**. Counts describe the whole training campaign; the selected checkpoint may precede update 64. The latest checkpoint is not automatically the selected one. Checkpoints 0/8/16/32/64, including regressions, are retained and shown.

| Four matched held-out scenarios | Parent weights, V8 setup | Selected V8 weights | Fixed controller |
|---|---:|---:|---:|
| Complete four-task sequences | {b['full_successes']}/{b['n']} | {t['full_successes']}/{t['n']} | {f['full_successes']}/{f['n']} |
| Walking stations reached | {b['stations_reached']}/{b['station_opportunities']} | {t['stations_reached']}/{t['station_opportunities']} | {f['stations_reached']}/{f['station_opportunities']} |
| Falls | {b['falls']} | {t['falls']} | {f['falls']} |
| Valid arm recoveries / attempts | {b['recovery_successes']}/{b['recovery_attempts']} | {t['recovery_successes']}/{t['recovery_attempts']} | {f['recovery_successes']}/{f['recovery_attempts']} |

Four scenarios and one training run are a small simulation pilot. Walking failures can prevent later tasks from being attempted. Task success, recovery success and full-sequence success are distinct checks. Raw paired outcomes and uncertainty are in the evidence. The original V7 stack is evaluated separately; its engineering differences are not attributed to weight training.

### What was fixed before training

The old laptop press could not sustain enough closing torque. The new controller contacts the upper lid edge from a front-right stance, applies bounded actuator force, then withdraws while gravity finishes closing. The hinge, object properties and success criteria remain unchanged.

A universal parking detour caused unnecessary arm travel. The revised options include direct folding where safe and outward shoulder clearance before lowering beside the alarm. These are engineered primitives. Tinker learns which commands and primitives to choose; their implementation is frozen across the weight comparison. Recovery checks include stable joints, low speed, no fall and no fixture-contact steps above 0.01 N.

### Services used

- **Tinker:** real supervised post-training, completed forward/backward and optimizer calls, durable intermediate states, and fixed-checkpoint inference in closed-loop simulation. No extra optimizer updates are credited to evaluation-only probes.
- **Modal:** {rollouts} physical rollouts across the training/evaluation evidence, bounded at four CPU workers per function. The before/selected/fixed comparisons share one worker per scenario. Small MuJoCo experiments run on CPUs.
- **Exa:** {len(s['sources'])} searches inside the research/training loop. Retrieved evidence informs bounded proposals; it is not executed as code.
- **past.dev:** {writes} writes, {reads} recall requests and {m['cross_agent_reads']} source-verified cross-role handoffs. Recalled proposals select between predeclared training allocations. Credit charges are not available from these API receipts.

### past.dev challenge

**Agents:** research, policy design, experiment execution and criticism use separate identities and explicit audiences.

**Layers:** prompts hold working context; past.dev stores sourced findings, outcomes and qualified conclusions; versioned code stores procedures; Mochi artifacts store numerical measurements and trajectories.

**Results:** {m['writers']} writing identities, {m['readers']} verified reading identities and {m['cross_agent_reads']} cross-role recalls. Private critic audience isolation {'passed' if m['isolation_passed'] else 'was not established'}.

**Caveats:** canonical payloads are resolved only after verifying returned source IDs. No causal memory or search ablation is claimed. Training examples include repetitions, not new market or physical observations at each update.

### Inspect and run

Run from the repository root. Provider credentials stay on the backend, using the repository's existing GitHub Actions secrets.

```sh
PYTHONPATH=mochi/src python -m pytest mochi/tests/test_control_v8.py -q
node mochi/scripts/check_replay_ui.mjs
python3 -m http.server 4028 --directory mochi/web/desk
PYTHONPATH=mochi/src python -m mochi.control_v8.train
```

The training command starts a new research run and requires access to the retained parent checkpoint. Canonical trained states remain in the owner's Tinker account; public receipts identify them by hash. Archived trajectories can be replayed without service credentials. The numerical evidence and execution artifacts support inspection; trained state access is required for an exact policy rerun.

No checkpoint deletion or billing-plan changes are part of this training study. Forecasting code, deployments and archived results remain separate. The older V6/V7 studies and their failures remain in their original evidence directories.

Integration paths: [training](src/mochi/control_v8/train.py), [Modal execution](src/mochi/control_v8/remote.py), [physical controls](src/mochi/control_v8/manipulation.py), [recovery](src/mochi/control_v8/recovery.py), [memory](src/mochi/desk/services.py), [search](src/mochi/integrations.py).
<!-- MOCHI_CURRICULUM_END -->
'''
if iso:
 extra='\nSeparate task and recovery probes use the same held-out seed block after checkpoint selection. Recovery choices start from shared post-task states, so walking failure cannot hide them. '
 for label in ['starting_model','post_trained_model']:
  x=iso['recovery_summary'][label];extra+=f"{label.replace('_',' ')}: {x['successes']}/{x['n']} valid recoveries. "
 motion=iso.get('matched_motion',{});nmatched=motion.get('n',0)
 if nmatched:extra+=f"Across {nmatched} shared states where both recoveries passed, mean hand travel was {motion['starting_hand_path_m']/nmatched*100:.1f} cm before and {motion['trained_hand_path_m']/nmatched*100:.1f} cm after. "
 extra+='These isolated resets are not part of the continuous demo. [Probe evidence](evidence/control-v8/isolated-controls.json).\n'
 block=block.replace('### What was fixed before training',extra+'\n### What was fixed before training')
if a.revision=='clearance':
 block=block.replace('evidence/control-v8/','evidence/control-v8-clearance/').replace('[V8 methods](docs/control-v8-study.md)','[Methods and clearance revision](docs/laptop-clearance-revision.md)').replace('Parent weights, V8 setup','Parent weights, revised setup')
 block=block.replace('### What was fixed before training',f'The {n} training updates occurred in the retained V8 source run. The revised laptop stance and XY-balanced press are engineering changes; these checkpoint weights are tested unchanged, with zero additional optimizer updates. Both sides of the comparison use that same revision. The original V8 results remain separately available.\n\n### Engineering and training are separate')
 block=block.replace('The hinge, object properties and success criteria remain unchanged.','The hinge, object properties and success criteria remain unchanged. The revised stance clears the falling lid, and a bounded lateral arm-force component balances its reaction about the foot support center. No base force is applied.')
readme=root/'README.md';text=readme.read_text()
if '<!-- MOCHI_CURRICULUM_START -->' in text:
 readme.write_text(re.sub(r'<!-- MOCHI_CURRICULUM_START -->.*?<!-- MOCHI_CURRICULUM_END -->',lambda _:block.strip(),text,flags=re.S))
else:
 archive=root/'docs/archive/planning-v1-readme.md';archive.parent.mkdir(parents=True,exist_ok=True)
 if not archive.exists():archive.write_text(text)
 footer='''
## Fresh environment and rendering

Reuse `mochi/.venv` when available. For a new environment, run from the repository root:

```sh
uv venv --python 3.11 mochi/.venv
uv pip install --python mochi/.venv/bin/python torch==2.15.0 --index-url https://download.pytorch.org/whl/cpu
uv pip install --python mochi/.venv/bin/python -e './mochi[remote,dev,plots]' pyyaml==6.0.2
mochi/.venv/bin/python mochi/scripts/fetch_visual_models.py
```

See [the integration inventory](docs/integrations.md) for local versus remote credentials. The additive Mochi workflows inject existing backend secret references. The local replay server requires no provider credentials.

```sh
blender -b -t 4 -P mochi/scripts/render_curriculum.py -- \\
  --input mochi/web/desk/curriculum/v8-held-out-25000-after.json \\
  --out mochi/artifacts/inspection --time 53.394657 --samples 32 --camera follow
```

The source-study render uses actual selected-checkpoint motion. Use `--camera side` or `feet` to inspect gait, or `--animate` to save the recorded animation in a Blender scene. Large generated outputs and caches stay out of Git.

## Provenance and limits

This is a fixed-layout, state-observation simulation study. Waist and fingers are fixed. There is no camera input or hardware validation. Remote model inference pauses simulation time; displayed completion times exclude those waits. Sampled clearance checks do not certify continuous collision freedom.

The original supported puck slice is in [the initial archive](docs/archive/initial-puck-slice.md). The preceding navigation/planning README is [preserved separately](docs/archive/planning-v1-readme.md). Later walking, task and recovery training is not all claimed as work built during the original hackathon.

Dependencies include MuJoCo, NumPy, SciPy, PyTorch, Three.js, Blender, FastAPI and the provider SDKs. Robot hashes and licenses are recorded in [G1 provenance](assets/robot/g1/source.json) and [locomotion provenance](assets/robot/locomotion/source.json). [Scene attribution](web/desk/assets/sand3d-attribution.json) records visual assets. Forecasting code, deployments and archived results remain separate.
'''
 readme.write_text('# MOCHI — Walking, Contact and Recovery Policy Learning\n\n'+block.strip()+'\n'+footer)
