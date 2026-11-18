import json,math
from pathlib import Path
from mochi.planning.geometry import ConfigurationSpace
from mochi.planning.route import route_hash,SPEEDS
from mochi.curriculum.world import wrap
s=ConfigurationSpace(clearance=.01);r=json.load(open('mochi/configs/desk-route-v1.json'));r['legs']=r['legs'][:2];start=r['legs'][-1]['goal']
for task,steps,final in [('laptop',[([.30,.02],0,'forward'),([.30,.16],math.pi/2,'forward')],math.pi/2),('globe',[([.35,.16],math.pi/2,'side_right'),([.35,.225],math.pi/2,'forward')],0.)]:
 segs=[];p=list(start[:2]);heading=start[2];duration=0.
 for q,h,command in steps:
  assert s.rotation_free(p,heading,h),(task,'rotation',p,heading,h)
  assert s.segment_free(p,q,h),(task,'segment',p,q,h)
  length=math.dist(p,q);turn=abs(wrap(h-heading))/1.1;travel=length/SPEEDS[command];segs.append({'from':p,'to':q,'heading':h,'command':command,'length_m':length,'nominal_travel_s':travel,'nominal_turn_s':turn});duration+=turn+travel;p=q;heading=h
 assert s.rotation_free(p,heading,final),(task,'finalrotation')
 l={'task':task,'start':start,'goal':[*p,final],'segments':segs,'length_m':sum(x['length_m'] for x in segs),'nominal_motion_s':duration+abs(wrap(final-heading))/1.1,'final_turn_radians':wrap(final-heading)};r['legs'].append(l);start=l['goal'];print(task,'checked',flush=True)
r['planner']='V1 graph-planned alarm/drawer legs; manually specified, swept-clearance-checked laptop/globe corridor';r['global_optimality_claim']=False;r['length_m']=sum(l['length_m'] for l in r['legs']);r['nominal_motion_s']=sum(l['nominal_motion_s'] for l in r['legs']);r['robot_projections']=[{'task':l['task'],**s.projection(l['goal'])} for l in r['legs']];r['version']=route_hash(r);Path('mochi/configs/desk-route-v8.json').write_text(json.dumps(r,indent=2)+'\n');print(r['version'])
