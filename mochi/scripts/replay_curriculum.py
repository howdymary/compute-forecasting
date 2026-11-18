"""Replay a published decision transcript without calling an LLM or paid APIs."""
import argparse,json
from pathlib import Path
from mochi.curriculum.remote import Runner
from mochi.curriculum.train import sequence_summary
p=argparse.ArgumentParser();p.add_argument('--episode',required=True);p.add_argument('--out');a=p.parse_args();expected=json.loads(Path(a.episode).read_text());runner=Runner();status=runner.reset(expected['scenario']['seed'],False)
for decision in expected['decisions']:
 if status['mode']=='done':break
 status=runner.advance(decision['action'])
episode=runner.w.episode();result={'summary':sequence_summary([{'episode':episode,'arrivals':runner.arrivals}]),'expected_task_success':{t:r['success'] for t,r in expected['results'].items()},'replayed_task_success':{t:r['success'] for t,r in episode['results'].items()},'expected_duration_s':expected['duration'],'replayed_duration_s':episode['duration'],'reference':'Reported runs use the pinned Linux x86 Modal/Actions runtime; other architectures can diverge in contact dynamics.'};print(json.dumps(result,indent=2))
if a.out:Path(a.out).write_text(json.dumps(result,indent=2))
