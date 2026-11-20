"""Bounded smooth recovery alternatives, evaluated through physical actuation."""
import math
from dataclasses import dataclass, asdict

import numpy as np

from ..balanced.recovery import recover as legacy_recover, fixture_contact
from ..control_v8.recovery import RECOVERIES, observation
from ..richdesk.stepping import ease


@dataclass(frozen=True)
class SmoothRecovery:
    code: str = 'R4'
    duration: float = 1.2
    clearance: float = .55


def recover(w, task, code):
    if code != 'R4':
        return legacy_recover(w,task,next(p for p in RECOVERIES if p.code==code))
    profile=SmoothRecovery()
    arm=w.arm[w.approach_side]
    w.task=None
    w.phase='recover'
    start=float(w.d.time)
    initial=observation(w,task)
    q0=w.d.qpos[arm['qs']].copy()
    points=[]
    if task=='alarm':
        outside=q0.copy()
        outside[1]=min(q0[1],-.55) if w.approach_side=='right' else max(q0[1],.55)
        points.append(outside)
    points.append(arm['rest'].copy())
    previous=q0.copy()
    previous_tip=w.d.site_xpos[arm['tip']].copy()
    travel=path=0.
    contact_steps=0
    peak=stable=0.
    segment=0
    segment_start=start
    segment_q=q0.copy()
    while w.d.time-start<8. and not w.fall:
        if segment<len(points):
            duration=max(.35,profile.duration*float(np.max(abs(points[segment]-segment_q))))
            age=float(w.d.time)-segment_start
            target=segment_q+(points[segment]-segment_q)*ease(age/duration)
            w.d.ctrl[arm['acts']]=np.clip(target,arm['limits'][:,0]+.001,arm['limits'][:,1]-.001)
            if age>=duration and np.max(abs(w.d.qpos[arm['qs']]-points[segment]))<.04:
                segment+=1
                segment_start=float(w.d.time)
                segment_q=w.d.qpos[arm['qs']].copy()
        else:
            w.d.ctrl[arm['acts']]=arm['rest']
        w.step(standing=True)
        q=w.d.qpos[arm['qs']].copy()
        tip=w.d.site_xpos[arm['tip']].copy()
        travel+=float(np.sum(abs(q-previous)))
        path+=float(np.linalg.norm(tip-previous_tip))
        previous,previous_tip=q,tip
        contacts,force=fixture_contact(w)
        contact_steps+=int(contacts>0)
        peak=max(peak,force)
        ready=(segment==len(points) and np.max(abs(q-arm['rest']))<.035
            and np.max(abs(w.d.qvel[arm['vs']]))<.2
            and math.degrees(math.acos(float(np.clip(w.d.xmat[1,8],-1,1))))<5.)
        stable=stable+w.m.opt.timestep if ready else 0.
        if stable>=.12 or peak>.8:
            break
    row={'task':task,'action':code,'success':bool(stable>=.12 and not w.fall and contact_steps==0),
        'duration_s':float(w.d.time)-start,'arm_joint_travel_rad':travel,'hand_path_m':path,
        'fixture_contact_steps':contact_steps,'peak_fixture_force_n':peak,
        'end_max_joint_error_rad':float(np.max(abs(w.d.qpos[arm['qs']]-arm['rest']))),
        'end_max_joint_speed_rad_s':float(np.max(abs(w.d.qvel[arm['vs']]))),
        'fall':w.fall,'observation':initial,'profile':asdict(profile)}
    w.recoveries.append(row)
    w.events.append({'phase':'recover','t':float(w.d.time),**row})
    return row
