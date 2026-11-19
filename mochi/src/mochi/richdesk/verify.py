"""Physical success gates; no access to proposed foot or root references."""
import math
import mujoco
import numpy as np


def book_top(w):
    top=next(p for p in w.scene['props'] if p['name']=='book-step-3')
    geom=w.id('geom','book-step-3-contact');loads={'left':0.,'right':0.}
    for i,c in enumerate(w.d.contact):
        a,b=int(c.geom1),int(c.geom2)
        if geom not in [a,b]:continue
        if abs(float(c.frame[2]))<.7:continue
        other=b if a==geom else a;name=mujoco.mj_id2name(w.m,mujoco.mjtObj.mjOBJ_BODY,int(w.m.geom_bodyid[other])) or ''
        for side in loads:
            if name==side+'_ankle_roll_link':
                force=np.zeros(6);mujoco.mj_contactForce(w.m,w.d,i,force);loads[side]+=max(0.,float(force[0]))
    inside=True
    for side in loads:
        body=w.id('body',side+'_ankle_roll_link')
        for g in range(w.m.ngeom):
            if int(w.m.geom_bodyid[g])!=body:continue
            a=w.m.geom_aabb[g];R=w.d.geom_xmat[g].reshape(3,3);center=w.d.geom_xpos[g]+R@a[:3];extent=abs(R)@a[3:]
            if np.any(abs(center[:2]-np.array(top['pos'][:2]))+extent[:2]>np.array(top['size'][:2])/2):inside=False
    tilt=math.degrees(math.acos(float(np.clip(w.d.xmat[1,8],-1,1))))
    valid=not w.fall and inside and all(v>.05 for v in loads.values()) and tilt<5 and w.base_force==0
    return {'instant_valid':bool(valid),'top_book_load_n':loads,'feet_inside_top_book':bool(inside),'tilt_deg':tilt,
            'scope':'Needs 0.4-second continuous dwell before success.'}
