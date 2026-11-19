"""Read completed immutable recordings. No remote writes, inference or simulation."""
import gzip,hashlib,json
from pathlib import Path
import modal

ROOT=Path(__file__).resolve().parents[1]
cfg=json.loads((ROOT/'configs/terrain-v12-development-preview.json').read_text())
report=modal.Dict.from_name('mochi-terrain-v12-progress').get('latest')
assert report['run_id'].endswith(str(cfg['training_run']))
assert str(report['recovery']['evaluation_run'])==str(cfg['evaluation_run'])
assert report.get('held_out') is None,'Use the completed-evaluation exporter when final results exist'
checkpoints=[c for c in report['checkpoints'] if c['development']]
assert len(checkpoints)>=2 and checkpoints[0]['update']==0
volume=modal.Volume.from_name('mochi-terrain-v12-artifacts')
out=ROOT/'artifacts/terrain-development-preview';out.mkdir(parents=True,exist_ok=True)
reads=0

def recording(group,seed,label):
 global reads
 name=f"mochi-t12-final-{cfg['evaluation_run']}/{group}-{seed}-{label}.json.gz"
 raw=gzip.decompress(b''.join(volume.read_file(name)));row=json.loads(raw);reads+=1
 row['archive']={'volume':'mochi-terrain-v12-artifacts','path':name,'uncompressed_sha256':hashlib.sha256(raw).hexdigest()}
 row['episode'].pop('control_telemetry',None)
 for m in row['episode'].get('balance_measurements',[]):
  for k in ['q','qd','tau','support']:m.pop(k,None)
 return row

if cfg.get('include_development',True):
 for checkpoint in checkpoints:
  rows=[recording('dev-'+str(checkpoint['update']),seed,'policy') for seed in report['protocol']['development_seeds']]
  (out/f"checkpoint-{checkpoint['update']}.json").write_text(json.dumps(rows,separators=(',',':')))
paired=[]
if cfg.get('include_completed_test_pairs'):
 assert report['selected_checkpoint'] and report['held_out_opened'],'Test selection must already be frozen'
 completed={(r.get('seed'),r.get('model')) for r in report['physics_receipts'] if r.get('phase')=='held-out'}
 paired=[seed for seed in report['protocol']['held_out_seeds'] if all((seed,label) in completed for label in ['parent','selected'])]
 for label in ['parent','selected']:
  rows=[recording('held-out',seed,label) for seed in paired]
  (out/f'partial-held-out-{label}.json').write_text(json.dumps(rows,separators=(',',':')))
report['preview_snapshot']={'complete_test_pairs':paired,'development_source_run':cfg.get('reuse_development_source_run'),
 'scope':'Only completed paired test cases are exported. The final cohort summary is pending. No outcome-based filtering.'}
(out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'mode':'checkpoint preview; final cohort pending','updates':[c['update'] for c in checkpoints],
                  'recordings_read':reads,'complete_test_pairs':paired}))
