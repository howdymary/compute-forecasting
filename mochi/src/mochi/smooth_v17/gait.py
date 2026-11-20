"""Bounded globe-leg command candidate; native gait weights are unchanged."""
import math
from ..balanced.sequence import navigate as clearance_move
from ..smooth_v16.navigation import navigate,NavigationParameters

PARAMETERS=NavigationParameters(yaw_gain=2.2,max_yaw_rate=1.,forward_gain=1.4,alignment_gain=1.15)


def globe_leg(w):
    w.efficiency_segment='fixture_clearance'
    arrivals=[clearance_move(w,(.32,.105,math.pi/2),timeout=20.,speed=.035,
        position_tolerance=.012,label='laptop-clearance')]
    w.efficiency_segment='flat_transit'
    for i,point in enumerate([(.32,.02,-math.pi/2),(.32,-.145,-math.pi/2),(.35,-.145,0.)]):
        arrivals.append(navigate(w,point,stop=i==2,speed=.12,
            label='globe-station' if i==2 else 'globe-corridor-'+str(i),parameters=PARAMETERS))
    return arrivals
