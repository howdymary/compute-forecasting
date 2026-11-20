"""Freeze the extended library without changing either previous protocol."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
p=ROOT/'configs/smooth-v17-training.json';cfg=json.loads(p.read_text())
for file,expected in cfg['frozen_sha256'].items():assert hashlib.sha256((ROOT/file).read_bytes()).hexdigest()==expected,file
prior=json.loads((ROOT/'configs/smooth-v16r1-training.json').read_text())
for file,expected in prior['continuation_frozen_sha256'].items():assert hashlib.sha256((ROOT/file).read_bytes()).hexdigest()==expected,file
probe=json.loads((ROOT/'evidence/smooth-v17/cloud-state-probe.json').read_text());cfg['prelaunch_cloud_probe']=probe
gait=ROOT/'evidence/smooth-v17/globe-command-probes.json'
latest=json.loads(gait.read_text()) if gait.exists() else probe
cfg['prelaunch_command_probes']=latest if gait.exists() else None
segment=ROOT/'evidence/smooth-v17/cloud-recovery-segment-probe.json'
if segment.exists():latest=json.loads(segment.read_text())
cfg['carried_budget_usage']=latest['after'];cfg['prelaunch_segment_probe']=latest if segment.exists() else None
if gait.exists():
    assert all(x['walking_valid'] and x['task_success'] and x['recovery_success'] for x in cfg['prelaunch_command_probes']['attempts'] if x['candidate']=='W6')
cfg['engineering_usage']={k:latest['after'][k] for k in ['physical_rollouts','simulation_cpu_hours']}
cfg['prompt_sha256']=hashlib.sha256((ROOT/cfg['implementation_prompt']).read_bytes()).hexdigest()
cfg['engineering_evidence_sha256']=hashlib.sha256((ROOT/'evidence/smooth-v17/engineering.json').read_bytes()).hexdigest()
files=list((ROOT/'src/mochi/smooth_v17').glob('*.py'))+list((ROOT/'evidence/smooth-v17').glob('*.json'))+[
 ROOT/'docs/smooth-v17-prompt.md',ROOT/'tests/test_smooth_v17.py',ROOT/'scripts/freeze_smooth_v17.py']
cfg['continuation_frozen_sha256']={**prior['continuation_frozen_sha256'],**{str(f.relative_to(ROOT)):hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted(files)}}
cfg['prior_executor_sha256']=prior['continuation_frozen_sha256']
cfg['workflow_sha256']=hashlib.sha256((ROOT.parent/'.github/workflows/mochi-smooth-v17-training.yml').read_bytes()).hexdigest()
p.write_text(json.dumps(cfg,indent=2)+'\n')
print(json.dumps({'base_frozen':len(cfg['frozen_sha256']),'new_frozen':len(cfg['continuation_frozen_sha256']),'carried_attempts':cfg['engineering_usage']['physical_rollouts'],'accounted_cpu_hours':cfg['engineering_usage']['simulation_cpu_hours']}))
