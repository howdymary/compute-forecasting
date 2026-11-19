"""Bounded consequential walking choices; low-level weights remain fixed."""
import math

WALKS={
    'W0':{'width':.024,'shift_seconds':1.8,'swing_scale':1.,'flat_speed':.055},
    'W1':{'width':.024,'shift_seconds':2.1,'swing_scale':1.15,'flat_speed':.045},
    'W2':{'width':.020,'shift_seconds':1.65,'swing_scale':1.,'flat_speed':.065},
}
BASE={'width':.024,'balance_feedback':.5,'descent_lift':.006,'descent_height_fraction':1.,'book_goal':.04}

def execute_selected_leg(w,task,code,parameters=None):
    from .sequence import book_leg,prepare_flat_walking
    from ..balanced.sequence import navigate
    from ..balanced.legs import execute_leg
    p={**BASE,**(parameters or {}),**WALKS[code]};speed=p.pop('flat_speed');arrivals=[]
    if task=='alarm':return [book_leg(w,1,p)]
    if task=='drawer':
        arrivals.extend([book_leg(w,-1,p),prepare_flat_walking(w,p)])
        for point in [(-.19,-.18,math.pi/2),(-.19,-.03,math.pi/2)]:
            arrivals.append(navigate(w,point,stop=False,speed=speed,label='drawer-corridor'))
        arrivals.append(navigate(w,(-.13,.02,math.pi/2),speed=speed,position_tolerance=.012,label='drawer-station'))
        return arrivals
    return execute_leg(w,task,speed=speed)
