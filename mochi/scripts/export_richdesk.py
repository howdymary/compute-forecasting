"""Export real development attempts without relabeling them as training."""
import json,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'web/desk/richdesk';OUT.mkdir(parents=True,exist_ok=True)
plan=json.loads((ROOT/'artifacts/richdesk-v10/route-plan.json').read_text())
attempts=[]
for ident,label in [('development-native','Frozen native controller'),('wholebody-qp-shift-1.6','Contact controller · development attempt'),('terrain-landingpads-10','Isolated books · closer starting pose')]:
    source=ROOT/'artifacts/richdesk-v10'/f'{ident}.json'
    if not source.exists():continue
    row=json.loads(source.read_text());episode=row['episode'];episode['engineering_record']=row['result']
    episode.pop('control_telemetry',None)
    for frame in episode['trajectory']['frames']:
        for key in ['positions','quaternions']:frame[key]=[[round(v,7) for v in xyz] for xyz in frame[key]]
    (OUT/f'{ident}.json').write_text(json.dumps(episode,separators=(',',':')))
    isolated=ident.startswith('terrain-')
    attempts.append({'id':ident,'label':label,'file':ident+'.json','verified':False,'group':'isolated-riser' if isolated else 'matched-full-start',
        'status':'Climb not established','scope':('Isolated terrain-v2 calibration, starting closer to the first book. Not a full-route or matched checkpoint comparison. No Tinker training.' if isolated else 'Archived early engineering attempts on seed 31000, before terrain-v2 verifier changes. Not Tinker checkpoints or held-out results. No completed climb.')})
manifest={'study':'mochi-richdesk-v10','scene':plan['scene'],'route':plan,'attempts':attempts,
    'default_attempt':'development-native','scope':'Planned route overlay with recorded physical attempts; training gate closed.','optimizer_updates_completed':0}
(OUT/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
shutil.copyfile(ROOT/'artifacts/richdesk-v10/route-plan.png',OUT/'route-plan.png')
print('Exported',len(attempts),'development recordings, zero new training checkpoints')
