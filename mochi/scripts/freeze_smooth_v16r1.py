"""Freeze only the additional execution. Never rewrites the original V16 protocol."""
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
p=ROOT/'configs/smooth-v16r1-training.json'
cfg=json.loads(p.read_text())
for path,expected in cfg['frozen_sha256'].items():
    assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==expected, path
files=list((ROOT/'src/mochi/smooth_v16_resume').glob('*.py'))+[
    ROOT/'docs/smooth-v16-continuation-prompt.md',ROOT/'evidence/smooth-v16/stopped-execution.json',
    ROOT/'tests/test_smooth_v16_resume.py',ROOT/'scripts/freeze_smooth_v16r1.py',
    ROOT/'scripts/probe_smooth_v16r1_state.py',ROOT/'evidence/smooth-v16/resume-state-probe.json']
cfg['continuation_frozen_sha256']={str(f.relative_to(ROOT)):hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted(files)}
cfg['workflow_sha256']=hashlib.sha256((ROOT.parent/'.github/workflows/mochi-smooth-v16r1-training.yml').read_bytes()).hexdigest()
p.write_text(json.dumps(cfg,indent=2)+'\n')
print('Original frozen files:',len(cfg['frozen_sha256']),'additional frozen files:',len(cfg['continuation_frozen_sha256']))
