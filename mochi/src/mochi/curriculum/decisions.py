"""The trained interface: observed navigation state and contact-profile selection."""
import json
from .world import MOVES, PROFILES

def decision(obs):
    from tinker_cookbook.recipes.decisions import Decision
    if obs['domain']=='walk':
        goal='Reach the station position and final heading, without falling. Distances and bearings are relative to the robot. Positive bearings and heading errors mean turn left. Near a station, translate sideways or backwards while aligning the final heading. Stop only when aligned and close enough to manipulate.'
        choices=[(name,f'body velocity forward {v[0]*1000:.0f} mm/s, left {v[1]*1000:.0f} mm/s, yaw left {v[2]:.2f} rad/s') for name,v in MOVES.items()]
    else:
        goal={'alarm':'Depress the alarm button, then release it.', 'drawer':'Push the drawer fully shut, then withdraw.', 'laptop':'Push the open laptop lid toward closed, then withdraw.', 'globe':'Rotate the globe marker to zero, brake, and release.'}[obs['domain']]
        goal+=' Select a contact profile. Require sustained success, hand contact, safe forces, and an upright robot. Exact friction and mass are unknown.'
        choices=[(p.code,f'push speed {p.speed*1000:.0f} mm/s; depth {p.depth*1000:.1f} mm; force backoff {p.force:.3f} N; brake {p.brake*1000:.1f} mm; hold {p.hold:.2f} s') for p in PROFILES]
    return Decision(goal+'\nObserved state: '+json.dumps(obs,sort_keys=True),choices)

async def choose(sampler,renderer,obs):
    from tinker_cookbook.recipes.decisions import sample_decision
    distribution=await sample_decision(sampler,renderer.render(decision(obs)))
    return max(distribution,key=distribution.get),distribution
