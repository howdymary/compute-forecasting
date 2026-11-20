"""Credential-free replay with measured foot-clearance evidence."""
import gzip,hashlib,json
from pathlib import Path
from ..smooth_v16.public import rounded

def export_clip(row,run_id,name,volume):
    e=row['episode'];clip={k:v for k,v in e.items() if k not in ['control_telemetry','book_motion_samples','balance_measurements']}
    clip['balance_measurements']=[{k:v for k,v in m.items() if k in ['t','phase','gait_phase','roll_rad','loads_n','step_category']} for m in e['balance_measurements']]
    clip['model_decisions']=row.get('model_decisions',[])
    raw=json.dumps(rounded(clip),separators=(',',':')).encode();data=gzip.compress(raw,compresslevel=6,mtime=0)
    p=Path('/artifacts')/run_id/'public'/(name+'.json.gz');assert not p.exists()
    p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data);volume.commit()
    return {'volume':'mochi-contact-v18-artifacts','path':str(p.relative_to('/artifacts')),
            'sha256':hashlib.sha256(data).hexdigest(),'uncompressed_sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(data),
            'scope':'Measured variable-rate body transforms: 100 Hz on flat transit, 25 Hz elsewhere. Actual timestamps; no added foot animation.'}
