"""Measured contact support and an explicitly approximate capture-point check."""
import math
import mujoco
import numpy as np
from scipy.spatial import ConvexHull, QhullError


def support(w):
    points=[];weights=[];scuffs=[]
    for i,c in enumerate(w.d.contact):
        a,b=int(c.geom1),int(c.geom2)
        other=b if a in w.support_geoms else a if b in w.support_geoms else -1
        if other<0:
            continue
        name=mujoco.mj_id2name(w.m,mujoco.mjtObj.mjOBJ_BODY,int(w.m.geom_bodyid[other])) or ''
        if name not in ['left_ankle_roll_link','right_ankle_roll_link']:
            continue
        force=np.zeros(6);mujoco.mj_contactForce(w.m,w.d,i,force)
        if force[0]<=.005:
            continue
        if abs(float(c.frame[2]))<.7:
            scuffs.append({'foot':name,'force_n':float(force[0]),'point':c.pos.tolist()})
        else:
            points.append(c.pos.copy());weights.append(float(force[0]))
    com=w.d.subtree_com[1].copy();jac=np.zeros((3,w.m.nv));mujoco.mj_jacSubtreeCom(w.m,w.d,jac,1)
    velocity=jac@w.d.qvel
    cop=np.average(points,axis=0,weights=weights) if points else np.array([np.nan]*3)
    height=max(.02,float(com[2]-cop[2])) if points else .13
    capture=com[:2]+velocity[:2]/math.sqrt(9.81/height)
    margin=None;com_margin=None;vertices=[]
    try:
        xy=np.unique(np.array(points)[:,:2],axis=0)
        hull=ConvexHull(xy)
        vertices=xy[hull.vertices].tolist()
        margin=float(np.min(-(hull.equations[:,:2]@capture+hull.equations[:,2])))
        com_margin=float(np.min(-(hull.equations[:,:2]@com[:2]+hull.equations[:,2])))
    except (QhullError,IndexError,ValueError):
        pass
    return {'support_polygon_xy':vertices,'cop':cop.tolist() if points else None,
            'com_velocity_m_s':velocity.tolist(),'capture_point_xy':capture.tolist(),
            'capture_margin_m':margin,'com_support_margin_m':com_margin,'riser_contacts':scuffs,
            'scope':'Linear inverted-pendulum approximation from actual loaded contacts and COM velocity; not a full centroidal stability certificate.'}
