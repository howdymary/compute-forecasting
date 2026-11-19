"""Frozen physical verifier, outside the trainable decision interface."""
import math
import numpy as np
from ..control_v8.verification import full_success

def complete(episode,arrivals,failure=None):
    last=episode.get('balance_measurements',[])[-1:]
    steady=bool(last and all(v>.05 for v in last[0]['loads_n'].values())
                and abs(last[0]['roll_rad'])<math.radians(5))
    frames=episode.get('trajectory',{}).get('frames',[])
    if frames:steady=steady and frames[-1]['base_tilt_degrees']<5
    return bool(failure is None and full_success(episode) and not episode.get('invalid_contact',False)
                and episode['maximum_applied_base_force']==0
                and len(episode.get('recoveries',[]))==4 and all(r['success'] for r in episode['recoveries'])
                and any(a.get('book_top') and a['book_top']['instant_valid'] and a['dwell_s']>=.4 for a in arrivals)
                and any(a['label']=='descend-supported-stop' and a['success'] for a in arrivals) and steady)

def metrics(rows):
    if not rows:return {'roll_rms_deg':None,'lateral_rms_m':None}
    return {'roll_rms_deg':float(np.degrees(np.sqrt(np.mean([r['roll_rad']**2 for r in rows])))),
            'lateral_rms_m':float(np.sqrt(np.mean([r['lateral_m']**2 for r in rows])))}
