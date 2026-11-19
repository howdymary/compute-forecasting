"""Credential-free replay payloads exported from measured body transforms."""
import gzip
import hashlib
import json
from pathlib import Path


def rounded(value):
    if isinstance(value,float):
        return round(value,6)
    if isinstance(value,list):
        return [rounded(v) for v in value]
    if isinstance(value,dict):
        return {k:rounded(v) for k,v in value.items()}
    return value


def export_clip(row,run_id,name,volume):
    e=row['episode']
    keys=['scenario','scene','events','results','fall','invalid_contact','duration','maximum_applied_base_force',
          'balance_metrics','foot_slip_estimate_m','final_object_states','final_object_speeds',
          'trajectory','recoveries','steps','step_events','step_thresholds','efficiency_validity',
          'native_smoothness','unsupported_seconds','longest_unsupported_seconds']
    clip={k:e[k] for k in keys if k in e}
    clip['balance_measurements']=[{k:v for k,v in m.items() if k in ['t','phase','gait_phase','roll_rad','loads_n']}
                                  for m in e['balance_measurements']]
    clip['model_decisions']=row.get('model_decisions',[])
    raw=json.dumps(rounded(clip),separators=(',',':')).encode()
    payload=gzip.compress(raw,compresslevel=6,mtime=0)
    path=Path('/artifacts')/run_id/'public'/(name+'.json.gz')
    path.parent.mkdir(parents=True,exist_ok=True)
    assert not path.exists(), 'Preserve public simulation payload'
    path.write_bytes(payload)
    volume.commit()
    return {'volume':'mochi-efficient-v15-artifacts','path':str(path.relative_to('/artifacts')),
            'sha256':hashlib.sha256(payload).hexdigest(),'bytes':len(payload),
            'uncompressed_sha256':hashlib.sha256(raw).hexdigest(),
            'scope':'Display precision rounded to six decimals; raw physical archive retained separately.'}
