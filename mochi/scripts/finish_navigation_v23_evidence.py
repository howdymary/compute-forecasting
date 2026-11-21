"""Wait for this owned campaign, then run bounded post-selection audits."""
import json
import os
from pathlib import Path
import subprocess
import time

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'mochi/.cache/navigation-v23/finish'
OUT.mkdir(parents=True, exist_ok=True)
env = {**os.environ, 'PYTHONPATH': str(ROOT / 'mochi/src')}
python = str(ROOT / 'mochi/.venv/bin/python')
modal = str(ROOT / 'mochi/.venv/bin/modal')
progress = ROOT / 'mochi/artifacts/navigation-v23/completed/progress.json'
while not progress.exists():
    time.sleep(30)
report = json.loads(progress.read_text())
assert report['status'] == 'completed' and report['run_id'] == 'mochi-nav23-20261121c'
jobs = []
for name, script in [('counterfactuals', 'run_navigation_v23_counterfactuals.py'),
                     ('weights', 'audit_navigation_v23_weights.py')]:
    logfile = (OUT / (name + '.log')).open('w')
    job = subprocess.Popen([modal, 'run', 'mochi/scripts/' + script], cwd=ROOT, env=env,
        stdout=logfile, stderr=subprocess.STDOUT)
    jobs.append((name, job, logfile))
print('Completed navigation campaign. Running post-selection diagnostics.', flush=True)
for name, job, logfile in jobs:
    code = job.wait()
    logfile.close()
    print(json.dumps({'diagnostic': name, 'return_code': code}), flush=True)
    if name == 'counterfactuals' and code:
        raise RuntimeError('Inspect the preserved counterfactual log before packaging')
for arguments in [['mochi/scripts/fetch_navigation_v23_results.py'],
    ['mochi/scripts/build_navigation_v23_release.py', '--source', 'mochi/artifacts/navigation-v23/completed']]:
    subprocess.run([python, *arguments], cwd=ROOT, env=env, check=True)
print('Completed evidence package. Publication remains a separate inspected step.', flush=True)
