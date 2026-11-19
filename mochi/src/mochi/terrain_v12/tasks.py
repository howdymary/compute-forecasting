"""V12 collision-aware alarm approach; actuator-driven motion throughout."""
from dataclasses import asdict
import math

import mujoco
import numpy as np
from scipy.optimize import least_squares


def alarm_ik(w, target, normal):
    arm=w.arm['right'];tmp=w.viz;tmp.qpos[:]=w.d.qpos;tmp.qvel[:]=0
    limits=arm['limits'];tip=arm['tip'];qs=arm['qs']
    def residual(q):
        tmp.qpos[qs]=q;mujoco.mj_forward(w.m,tmp)
        penalty=np.zeros(w.m.nbody)
        for c in tmp.contact:
            a,b=int(w.m.geom_bodyid[c.geom1]),int(w.m.geom_bodyid[c.geom2])
            if a in w.robot_bodies and b in w.robot_bodies and c.dist<-.0003:
                penalty[a]=max(penalty[a],-float(c.dist)-.0003)
            if (a in w.robot_bodies)!=(b in w.robot_bodies):
                robot,fixture=(int(c.geom1),int(c.geom2)) if a in w.robot_bodies else (int(c.geom2),int(c.geom1))
                body=int(w.m.geom_bodyid[robot]);name=mujoco.mj_id2name(w.m,mujoco.mjtObj.mjOBJ_BODY,body) or ''
                allowed=(fixture in w.support_geoms and name.endswith('ankle_roll_link')) or (fixture==w.object_geoms['alarm'] and robot in w.hand_geoms['right'])
                if not allowed and c.dist<.001:penalty[body]=max(penalty[body],.001-float(c.dist))
        return np.r_[tmp.site_xpos[tip]-target,.008*(tmp.site_xmat[tip].reshape(3,3)[:,0]+normal),8*penalty]
    q0=np.clip(w.d.qpos[qs],limits[:,0]+.00101,limits[:,1]-.00101)
    opt=least_squares(residual,q0,bounds=(limits[:,0]+.001,limits[:,1]-.001),max_nfev=50,
                      ftol=1e-7,xtol=1e-7,gtol=1e-8)
    return opt.x


def press_alarm(w, profile, horizon=12.):
    w.task='alarm';w.approach_side='right';w.phase='approach';w.profile=profile
    w.t0=float(w.d.time);w.hand_contacts=0;w.bad_contacts=0;w.max_force=0.
    arm=w.arm['right'];next_ik=-1.;next_control=-1.;qtarget=w.d.qpos[arm['qs']].copy()
    phase_start=w.t0;stable=0.;desired=None;approach_stage=0
    clearance=np.array([-.335,.065,.205])
    while w.d.time-w.t0<horizon:
        contact,force,bad=w.contacts('alarm');w.hand_contacts+=int(contact);w.bad_contacts+=int(bad);w.max_force=max(w.max_force,force)
        if w.value('alarm')>=w.s['clock_stroke']*.85:
            w.activated=True
            if w.phase=='push':w.phase='hold';phase_start=float(w.d.time)
        if w.phase=='approach' and approach_stage==0 and np.linalg.norm(w.d.site_xpos[arm['tip']]-clearance)<.008:
            approach_stage=1;next_ik=-1.
        if w.phase=='approach' and approach_stage==1 and w.d.time-w.t0>1.8:
            hover,_=w.hand_target('alarm','hover')
            if np.linalg.norm(w.d.site_xpos[arm['tip']]-hover)<.006:
                w.phase='push';next_ik=-1.
        if w.phase=='hold' and w.d.time-phase_start>profile.hold:
            w.phase='release';next_ik=-1.
        desired,normal=w.hand_target('alarm',w.phase)
        if w.phase=='approach' and approach_stage==0:desired=clearance
        if force>profile.force and w.phase in ['push','hold']:
            desired=w.d.site_xpos[arm['tip']]+normal*min(.001,(force-profile.force)*.003)
        if w.d.time>=next_ik:
            qtarget=alarm_ik(w,desired,normal);next_ik=float(w.d.time)+.06
        if w.d.time>=next_control:
            change=qtarget-w.d.ctrl[arm['acts']]
            change*=min(1.,.018/max(np.max(abs(change)),1e-8))
            w.d.ctrl[arm['acts']]=np.clip(w.d.ctrl[arm['acts']]+change,arm['limits'][:,0]+.001,arm['limits'][:,1]-.001)
            next_control=float(w.d.time)+.02
        w.step(standing=True)
        good=w.activated and w.value('alarm')<w.s['clock_stroke']*.2
        stable=stable+w.m.opt.timestep if w.phase=='release' and good else 0.
        if stable>.35 or w.max_force>.8:
            break
    result={'task':'alarm','success':bool(stable>.35 and w.hand_contacts>0 and w.bad_contacts==0 and w.max_force<.8),
            'value':w.value('alarm'),'duration':float(w.d.time)-w.t0,'contacts':w.hand_contacts,
            'non_hand_contact_steps':w.bad_contacts,'max_force_n':w.max_force,'fall':w.fall,
            'profile':asdict(profile),'phase':w.phase,'final_tip':w.d.site_xpos[arm['tip']].tolist(),
            'final_target':desired.tolist(),'controller':'v12 collision-aware staged absolute IK','approach_stage':approach_stage}
    w.results['alarm']=result;w.events.append({'t':float(w.d.time),**result})
    return result
