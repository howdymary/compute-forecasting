"""Read completed development archives. No inference, simulations or writes remotely."""
import gzip,hashlib,json
from pathlib import Path
import modal

ROOT=Path(__file__).resolve().parents[1]
cfg=json.loads((ROOT/'configs/terrain-v12-development-preview.json').read_text())
report=modal.Dict.from_name('mochi-terrain-v12-progress').get('latest')
assert report['run_id'].endswith(str(cfg['training_run']))
assert str(report['recovery']['evaluation_run'])==str(cfg['evaluation_run'])
assert not report['held_out_opened'],'Use the completed-evaluation exporter after final testing starts'
checkpoints=[c for c in report['checkpoints'] if c['development']]
assert len(checkpoints)>=2 and checkpoints[0]['update']==0
volume=modal.Volume.from_name('mochi-terrain-v12-artifacts')
out=ROOT/'artifacts/terrain-development-preview';out.mkdir(parents=True,exist_ok=True)
for checkpoint in checkpoints:
 rows=[]
 for seed in report['protocol']['development_seeds']:
  name=f"mochi-t12-final-{cfg['evaluation_run']}/dev-{checkpoint['update']}-{seed}-policy.json.gz"
  raw=gzip.decompress(b''.join(volume.read_file(name)));row=json.loads(raw)
  row['archive']={'volume':'mochi-terrain-v12-artifacts','path':name,'uncompressed_sha256':hashlib.sha256(raw).hexdigest()}
  row['episode'].pop('control_telemetry',None)
  for m in row['episode'].get('balance_measurements',[]):
   for k in ['q','qd','tau','support']:m.pop(k,None)
  rows.append(row)
 (out/f"checkpoint-{checkpoint['update']}.json").write_text(json.dumps(rows,separators=(',',':')))
(out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'mode':'development preview; final evaluation pending','updates':[c['update'] for c in checkpoints],
                  'physical_recordings':len(checkpoints)*len(report['protocol']['development_seeds'])}))
