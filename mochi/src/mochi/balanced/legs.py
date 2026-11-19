"""Fixed route and actuator interfaces shared by every checkpoint."""
import math

WALKS={
    'W0':{'climb_speed':.055,'descent_speed':.055,'flat_speed':.055},
    'W1':{'climb_speed':.03,'descent_speed':.03,'flat_speed':.055},
    'W2':{'climb_speed':.04,'descent_speed':.02,'flat_speed':.03},
}

def execute_leg(w,task,*,speed=.055,alarm_x=-.365,alarm_y=.045,
                capture_margin=.001,forward_descent=True,descent_speed=.03,climb_speed=None):
    from .sequence import navigate
    arrivals=[]
    def go(goal,**kwargs):
        row=navigate(w,goal,**kwargs);arrivals.append(row);return row
    if task=='alarm':
        go((alarm_x,alarm_y,math.pi/2),book=True,speed=climb_speed or speed,
           label='alarm-book-top',capture_margin=capture_margin)
    elif task=='drawer':
        if forward_descent:
            go((*w.d.qpos[:2],-math.pi/2),capture_margin=.001,label='book-turn-for-forward-descent')
        heading=-math.pi/2 if forward_descent else math.pi/2
        x=float(w.d.qpos[0])
        go((x,-.18,heading),stop=True,speed=descent_speed or speed,capture_margin=.001,
           position_tolerance=.018,label='descend-supported-stop')
        if forward_descent:
            go((*w.d.qpos[:2],math.pi/2),capture_margin=.001,label='desk-turn-to-corridor')
        for point in [(-.19,-.18,math.pi/2),(-.19,-.03,math.pi/2)]:
            go(point,stop=False,speed=speed,label='drawer-corridor')
        go((-.13,.02,math.pi/2),speed=speed,position_tolerance=.012,label='drawer-station')
    elif task=='laptop':
        for point in [(.08,.02,math.pi/2),(.08,-.055,math.pi/2),(.30,-.055,math.pi/2),(.30,.02,math.pi/2)]:
            go(point,stop=False,speed=speed,label='laptop-corridor')
        go((.30,.16,math.pi/2),speed=speed,position_tolerance=.012,label='laptop-station')
    elif task=='globe':
        go((.30,.02,math.pi/2),stop=False,speed=speed,label='leave-laptop')
        go((.35,-.145,0.),speed=speed,position_tolerance=.012,label='globe-station')
    else:
        raise ValueError('Unknown station')
    return arrivals

def execute_selected_leg(w,task,code):
    p=WALKS[code]
    return execute_leg(w,task,speed=p['flat_speed'],climb_speed=p['climb_speed'],descent_speed=p['descent_speed'])
