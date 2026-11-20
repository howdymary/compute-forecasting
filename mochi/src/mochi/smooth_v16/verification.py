"""V16 support includes the existing paper's top, never its vertical edges."""
import mujoco
import numpy as np
import math


def forward_descent_check(events, samples):
    checked=[]
    for step in events:
        if step['category']!='book_descent' or not step['completed']:
            continue
        delta=np.asarray(step['end_position'])-step['start_position']
        if delta[2]>-.004:
            continue
        nearest=min(samples,key=lambda row:abs(row['t']-step['touchdown_t']))
        heading=math.atan2(delta[1],delta[0])
        wrap=lambda x:(x+math.pi)%(2*math.pi)-math.pi
        body_error=abs(wrap(heading-nearest['yaw']))
        foot_error=abs(wrap(heading-step['end_yaw']))
        checked.append({'side':step['side'],'touchdown_t':step['touchdown_t'],
            'drop_m':-float(delta[2]),'body_error_degrees':math.degrees(body_error),
            'foot_error_degrees':math.degrees(foot_error),
            'forward':body_error<=math.radians(20) and foot_error<=math.radians(20)})
    return {'verified':len(checked)>=6 and all(s['forward'] for s in checked),
        'descending_steps':checked,
        'definition':'Actual descending foot placements, verified loaded touchdown, and body/foot yaw within20 degrees of that footstep direction.'}


def fixture_violation(w):
    allowed={w.id('geom','desk')}|w.book_geoms
    paper=w.id('geom','sticky-notes-contact')
    for index,hit in enumerate(w.d.contact):
        a,b=int(hit.geom1),int(hit.geom2)
        ra=int(w.m.geom_bodyid[a]) in w.robot_bodies
        rb=int(w.m.geom_bodyid[b]) in w.robot_bodies
        if ra==rb:
            continue
        robot,fixture=(a,b) if ra else (b,a)
        body=mujoco.mj_id2name(w.m,mujoco.mjtObj.mjOBJ_BODY,int(w.m.geom_bodyid[robot])) or ''
        foot=body in ['left_ankle_roll_link','right_ankle_roll_link']
        if foot and (fixture in allowed or (fixture==paper and abs(float(hit.frame[2]))>.7)):
            continue
        task=getattr(w,'task',None)
        if w.phase in ['approach','push','hold','release'] and task:
            target=w.object_geoms.get(task)
            hand=w.hand_geoms.get(w.approach_side,set())
            if fixture==target and robot in hand:
                continue
        force=np.zeros(6)
        mujoco.mj_contactForce(w.m,w.d,index,force)
        if force[0]>.05:
            return {'t':float(w.d.time),'body':body,
                'fixture':mujoco.mj_id2name(w.m,mujoco.mjtObj.mjOBJ_GEOM,fixture),
                'force_n':float(force[0]),'phase':w.phase,'normal':hit.frame[:3].tolist()}
    return None
