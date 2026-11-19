"""Bounded engineering calibration on declared development seeds only."""
import concurrent.futures,json,math
from dataclasses import asdict
from pathlib import Path
from .world import DeskWorld,ROOT
from .stepping import FootstepController,StepParameters


def trial(item):
    i,p=item;w=DeskWorld(30000,True)
    for _ in range(int(.4/w.m.opt.timestep)):w.step(standing=True)
    w.walker=FootstepController(w,p)
    for _ in range(int(6/w.m.opt.timestep)):
        if w.fall:break
        w.step((.025,0,0))
    r={'id':i,'parameters':asdict(p),'seconds':float(w.d.time),'position':w.d.qpos[:3].tolist(),
       'fall':w.fall,'tilt':math.degrees(w.max_tilt),'steps':w.walker.steps,
       'height':w.terrain_height(*w.d.qpos[:2]),'failure':w.walker.failed_reason}
    out=ROOT/'artifacts/richdesk-v9/tuning';out.mkdir(parents=True,exist_ok=True)
    (out/f'trial-{i}.json').write_text(json.dumps({'result':r,'episode':w.episode()},separators=(',',':')))
    print(json.dumps(r),flush=True)
    return r


if __name__=='__main__':
    candidates=[StepParameters(shift_seconds=shift,com_tracking=.5,torso_gain=.1,crouch=crouch)
                for shift in [.8,1.2] for crouch in [.004,.007,.010]]
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:results=list(pool.map(trial,enumerate(candidates)))
    (ROOT/'artifacts/richdesk-v9/tuning/results.json').write_text(json.dumps(results,indent=2)+'\n')
