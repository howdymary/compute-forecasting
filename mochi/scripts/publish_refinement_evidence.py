"""Create a small public numerical receipt; keep canonical model paths private."""
import argparse,csv,json,re
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--source',required=True,type=Path);p.add_argument('--run-id',required=True,type=int);a=p.parse_args();artifact_name=a.source.name;root=Path(__file__).resolve().parents[1];r=json.loads((a.source/'report.json').read_text());assert r['status']=='completed'
keys=['study','status','source_sha','protocol','protocol_sha256','scope','created_at','completed_at','optimizer_updates_completed','rollouts','source_data','data_audit','training_log','checkpoints','selected_checkpoint','stopping_rule_trigger','fixed_baseline','held_out','held_out_isolated_contact','held_out_isolated_walking','paired_outcomes','paired_full_success_gain','evaluation_runtime','modal_execution_receipts','research_allocation','recovery']
public={k:r.get(k) for k in keys};public['workflow_url']=f'https://github.com/howdymary/mochi-demo/actions/runs/{a.run_id}';public['training_workflow_url']=f"https://github.com/howdymary/mochi-demo/actions/runs/{r.get('recovery',{}).get('training_run',a.run_id)}";s=r['services'];calls=s.get('calls',[])
public['memory']={'eligibility':s['eligibility'],'writes':sum(c['method']=='POST' and c['kind']=='ingest' for c in calls),'recalls':sum(c['method']=='POST' and c['kind']=='recall' for c in calls),'ingestion_polls':sum(c['method']=='GET' and c['kind']=='ingest' for c in calls),'failed_http_calls':sum(c['status']>=400 for c in calls),'authoritative_credit_usage':None,'reads':s['reads'],'decisions':s['decisions']}
public['search']=[{k:x[k] for k in ['query','request_id','cost_dollars','at']}|{'sources':[{k:y[k] for k in ['url','title','retrieved_at']} for y in x['sources']]} for x in s['sources']]
public['provenance_checks']=json.loads((a.source/'provenance-checks.json').read_text());public['movement_diagnostics']=json.loads((a.source/'movement-diagnostics.json').read_text());encoded=json.dumps(public,indent=2);assert 'tinker://' not in encoded and 'Bearer ' not in encoded and not re.search(r'sk-[A-Za-z0-9]{20,}',encoded)
out=root/'evidence/refinement-v7';out.mkdir(parents=True,exist_ok=True);(out/'results.json').write_text(encoded)
with (out/'checkpoints.csv').open('w') as f:
 w=csv.writer(f);w.writerow(['additional_updates_in_this_study','development_routes','full_successes','waypoints','waypoint_opportunities','falls'])
 for c in r['checkpoints']:
  d=c['continuous_development'];w.writerow([c['update'],d['n'],d['full_successes'],d['stations_reached'],d['station_opportunities'],d['falls']])
with (out/'held-out.csv').open('w') as f:
 w=csv.writer(f);w.writerow(['policy','routes','full_successes','waypoints','waypoint_opportunities','falls'])
 for name,d in r['held_out'].items():w.writerow([name,d['n'],d['full_successes'],d['stations_reached'],d['station_opportunities'],d['falls']])
b,t,c=[r['held_out'][k] for k in ['starting_model','post_trained_model','classical_fixed']];n=r['optimizer_updates_completed'];memory=public['memory'];counts=public['provenance_checks']['domain_examples_including_repeats']
doc=f'''# V7 locomotion-command and contact-control post-training\n\nTinker completed {n} optimizer updates and {n*5} domain-gradient calls for walking, alarm, drawer, laptop and globe. This is a separate study starting from the archived update-zero state, not an additional {n} updates on V6 update 64. Qwen3.5-4B LoRA rank 16 learns body-velocity commands and contact-profile choices. The model reads simulation state, not camera images. The Unitree gait network, standing balance, arm IK and physical verifiers remain fixed.\n\n## Matched physical results\n\n| Policy | Full routes | Waypoints | Falls |\n|---|---:|---:|---:|\n| Starting weights | {b['full_successes']}/{b['n']} | {b['stations_reached']}/{b['station_opportunities']} | {b['falls']} |\n| Update {n} | {t['full_successes']}/{t['n']} | {t['stations_reached']}/{t['station_opportunities']} | {t['falls']} |\n| Classical + fixed profiles | {c['full_successes']}/{c['n']} | {c['stations_reached']}/{c['station_opportunities']} | {c['falls']} |\n\nThe desk layout and task order are fixed. Held-out seeds vary the initial robot pose and passive object dynamics; isolated walking uses separate goal offsets. These are not unseen-room or vision tests. The four fresh route seeds were unsealed after development selection. All three policies run closed-loop on the same Modal worker per scenario. This is a small simulation pilot, not a hardware or general reliability claim. Isolated navigation and contact tests are separate from full routes. Their exact results, intervals and per-scenario outcomes are in the numerical receipt.\n\n## Actual learning and memory\n\nConsumed examples, including repeats: {', '.join(f'{k} {v}' for k,v in counts.items())}. The report retains actual optimizer receipts and per-domain losses. Every public model action is checked against its recorded distribution and encoded observation; paired full-route initial states match exactly.\n\npast.dev recorded {memory['writes']} writes, {memory['recalls']} recalls and {memory['ingestion_polls']} ingestion polls. {memory['eligibility']['cross_agent_reads']} cross-role recalls verified the exact source ID. Private-audience isolation {'passed' if memory['eligibility']['isolation_passed'] else 'was not established'}. Credit charges are unavailable; call counts are not billing estimates. Recalled research proposals selected the predeclared walking/contact batch allocation. The frozen run performs this adaptation at initialization and update 16, not at every checkpoint. There is no causal memory or search ablation.\n\nExa ran {len(public['search'])} source-grounded searches. Modal recorded {r['rollouts']} new executions in this study, including two short recovery inference probes; earlier physical training evidence was reused and is identified separately.\n\n## Movement and visual inspection\n\nThe demo shows actual uninterrupted physical episodes at saved checkpoints. Side and foot views use the same playback speed. The first declared development seed is the primary checkpoint view; all four held-out before/after pairs are available. The complete-test button is a successful example selected after evaluation and labeled separately; it does not replace the default development view.\n\nMovement diagnostics were introduced after this run began. They are explicitly post-hoc, not its training reward. Matched initial windows end at the earliest checkpoint episode termination, up to 20 seconds. Torso tilt and yaw travel come from 25 Hz body transforms; command changes describe requested velocity, not measured motor jerk. Recorded loaded-foot slip spans the entire episode. True sole clearance and motor work are unavailable in these recordings.\n\nThe separate gait-modulation calibration did not establish a consistent gain, so its cadence changes are not promoted. See [calibration](gait-calibration.md). No new gait-network training is claimed.\n\n## Reproduction and provenance\n\nSource workflow: [{a.run_id}](https://github.com/howdymary/mochi-demo/actions/runs/{a.run_id}). Frozen source: `{r['source_sha']}`. The published result links actual training and experiment records rather than inferred completion. Evaluation recovery performs zero extra optimizer updates and retains the original failure. Canonical optimizer paths stay in the private execution artifact. Intermediate fixed inference snapshots have the retention limits stated in the protocol.\n\n```sh\ngh run download {a.run_id} --repo howdymary/mochi-demo --dir mochi/.cache/refinement-result\nPYTHONPATH=mochi/src mochi/.venv/bin/python mochi/scripts/check_refinement.py --source mochi/.cache/refinement-result/{artifact_name}\nPYTHONPATH=mochi/src mochi/.venv/bin/python mochi/scripts/analyze_movement.py --source mochi/.cache/refinement-result/{artifact_name} --out mochi/.cache/refinement-result/{artifact_name}/movement-diagnostics.json\npython3 mochi/scripts/export_curriculum.py --source mochi/.cache/refinement-result/{artifact_name} --run-id {a.run_id}\n```\n\nThe small public receipt and CSV tables live in `mochi/evidence/refinement-v7/`. Do not reclassify previously inspected seeds as fresh tests or combine V6 and V7 outcomes as independent samples.\n'''
(root/'docs/refinement-v7-results.md').write_text(doc);print(out)
# Generate only the marked current README block. The separate publishing helper
# preserves unrelated local and archived README content.
nav=r.get('held_out_isolated_walking',{});nb=nav.get('starting_model',{});nt=nav.get('post_trained_model',{});dev64=next((x['continuous_development'] for x in r['checkpoints'] if x['update']==64),None);devlast=r['checkpoints'][-1]['continuous_development']
block=f'''<!-- MOCHI_CURRICULUM_START -->
## Current: Post-training locomotion and contact decisions

[Live demo](https://howdymary--mochi-curriculum-demo-web.us-east.modal.run/) · [Methods and results](docs/refinement-v7-results.md) · [Numerical evidence](evidence/refinement-v7/results.json) · [Execution receipt](https://github.com/howdymary/mochi-demo/actions/runs/{a.run_id})

A 22.1 cm Unitree G1 moves around one desk: silence the clock, close the drawer, close the laptop, and align the globe. Every checkpoint is a recorded, uninterrupted MuJoCo episode. Blender and Three.js replay its measured motion.

Tinker completed **{n} optimizer updates and {n*5} domain-gradient calls**, training Qwen3.5-4B LoRA rank 16 to choose walking commands and task-contact profiles. The model reads simulation state rather than camera images. The native gait network, standing balance and arm IK remain fixed. This is command/profile learning, not motor-torque or gait-network training.

| Matched Modal test | Starting weights | Update {n} | Classical + fixed profiles |
|---|---:|---:|---:|
| Full four-task routes | {b['full_successes']}/{b['n']} | {t['full_successes']}/{t['n']} | {c['full_successes']}/{c['n']} |
| Waypoints reached | {b['stations_reached']}/{b['station_opportunities']} | {t['stations_reached']}/{t['station_opportunities']} | {c['stations_reached']}/{c['station_opportunities']} |
| Falls | {b['falls']} | {t['falls']} | {c['falls']} |
| Isolated walking goals | {nb.get('successes','—')}/{nb.get('n','—')} | {nt.get('successes','—')}/{nt.get('n','—')} | {nav.get('classical_fixed',{}).get('successes','—')}/{nav.get('classical_fixed',{}).get('n','—')} |

Four fresh routes are a small simulation pilot. Individual outcomes and uncertainty are published; isolated tests are separate from full routes. The default checkpoint scenario is the first declared development seed. All test recordings and regressions remain inspectable. A separate complete-test button is labeled as a successful example selected after evaluation.

Update 64 reached {dev64['stations_reached']}/{dev64['station_opportunities']} development waypoints with {dev64['falls']} falls. Update {n} reached {devlast['stations_reached']}/{devlast['station_opportunities']} with {devlast['falls']} falls. The frozen stopping rule selected update {n}; later training was not monotonically better. Laptop contact remains a limitation wherever its verifier fails.

The interface includes synchronized before/after playback, all saved checkpoints, side and foot cameras, and matched-window movement diagnostics. Those diagnostics were added after training began and are labeled post-hoc. The separate cadence calibration found tradeoffs rather than a consistent gain, so those profiles are not promoted. [Calibration evidence](docs/gait-calibration.md).

### What the services actually do

- **Tinker:** actual supervised weight updates for walking and all four contact tasks. Canonical starting/final states are retained; intermediate inference snapshots have limited retention. This V7 study starts from archived update zero, not from V6 update 64.
- **Exa:** {len(public['search'])} failure-directed searches with retained sources. The final recovery search informs future investigation, not the frozen test policy.
- **past.dev:** verified shared evidence handoffs select the predeclared walking/contact training allocation. The frozen training adaptation occurs at initialization and update 16. It is not a memory call at every optimizer step.
- **Modal:** {r['rollouts']} recorded executions including two short recovery inference probes. Held-out policies run closed-loop on the same worker per scenario. Reused older training trials are identified separately.

### past.dev challenge

**Agents:** separate research, design/training, execution/evaluation and criticism identities write and recall evidence. The demo exposes verified source handoffs and the bounded decisions they informed.

**Layers:** prompts hold working context; past.dev holds episodic findings and provenance; versioned code holds procedures; artifact files hold exact numerical results and trajectories.

**Results:** {memory['writes']} writes, {memory['recalls']} recall requests, {memory['ingestion_polls']} ingestion polls, and {memory['eligibility']['cross_agent_reads']} verified cross-role recalls. Private-audience isolation {'passed' if memory['eligibility']['isolation_passed'] else 'was not established'}.

**Caveats:** no causal search or memory ablation. Exact numerical payloads are resolved only after verifying their source IDs. API call counts do not establish credit charges. Recovery uses additional identities while retaining earlier source provenance.

### Reproduce and inspect

Run commands from the repository root. Install the independent package and fetch the pinned assets using the setup instructions below. Provider credentials are configured in existing GitHub Actions secrets; the replay frontend receives none.

```sh
node mochi/scripts/check_replay_ui.mjs
PYTHONPATH=mochi/src mochi/.venv/bin/python -m pytest mochi/tests/test_motion_metrics.py mochi/tests/test_gait_control.py -q
```

Artifact download, evidence checks and export commands are in [the results document](docs/refinement-v7-results.md). Render a recorded episode with:

```sh
blender --background --python mochi/scripts/render_curriculum.py -- --input mochi/web/desk/curriculum/checkpoint-64.json --out mochi/artifacts/inspection --time 1.5 --camera side --samples 16
```

The final training state was saved before the free checkpoint-storage limit closed its original client. Evaluation recovery uses fresh clients and in-memory snapshots, with **zero additional optimizer updates**, no canonical checkpoint deletion, and no billing changes. Additional persistent training checkpoints need available storage. The original failures remain archived.

Exact integration paths: [training](src/mochi/curriculum/refine.py), [memory](src/mochi/desk/services.py), [Exa and model decisions](src/mochi/integrations.py), [Modal feedback evaluation](src/mochi/curriculum/remote_policy.py), [evaluation recovery](src/mochi/curriculum/finalize_refinement.py).

```mermaid
flowchart LR
  E[Exa sources] --> M[past.dev verified findings]
  M --> B[Bounded training allocation]
  B --> T[Tinker weight updates]
  T --> S[Walking commands and contact profiles]
  S --> C[Fixed gait, balance and IK]
  C --> P[MuJoCo on Modal]
  P --> R[Metrics and recorded trajectories]
  R --> M
  R --> V[Three.js and Blender replay]
```

The earlier V6 reference success, its negative Modal replication, and the original supported-pushing studies are archived separately. They are not merged into the V7 test counts. See [V6 replication](evidence/curriculum-v6/modal-validation.json).
<!-- MOCHI_CURRICULUM_END -->
'''
hero=root/'web/desk/curriculum/v7-complete-example.png'
if hero.exists():
 block=block.replace('A 22.1 cm Unitree G1', '![Recorded Mochi globe interaction](web/desk/curriculum/v7-complete-example.png)\n\n*Test scenario 16001, selected after evaluation for this illustration. One of four complete test routes passed.*\n\nA 22.1 cm Unitree G1',1)
(root/'.cache/readme-current.md').write_text(block)
