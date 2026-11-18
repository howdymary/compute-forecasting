import json,math,argparse
from pathlib import Path
from mochi.planning.geometry import ConfigurationSpace
from mochi.planning.route import route_hash,SPEEDS
from mochi.curriculum.world import wrap
parser=argparse.ArgumentParser();parser.add_argument('--laptop-x',type=float,default=.30);parser.add_argument('--output',default='mochi/configs/desk-route-v8.json');parser.add_argument('--lid-sweep',action='store_true');args=parser.parse_args();x=args.laptop_x
s=ConfigurationSpace(clearance=.01);sweep=[]
if args.lid_sweep:
 import mujoco
 joint=mujoco.mj_name2id(s.m,mujoco.mjtObj.mjOBJ_JOINT,'laptop-hinge');q=int(s.m.jnt_qposadr[joint]);initial=float(s.initial[q])
 for degrees in range(0,81,5):
  s.initial[q]=math.pi/2-math.radians(degrees);s.cache.clear();answer=s.check([x,.16,math.pi/2],standing=True);sweep.append({'lid_degrees':degrees,**answer});assert answer['free'],sweep[-1]
 s.initial[q]=initial;s.cache.clear()
r=json.load(open('mochi/configs/desk-route-v1.json'));r['legs']=r['legs'][:2];start=r['legs'][-1]['goal']
for task,steps,final in [('laptop',[([x,.02],0,'forward'),([x,.16],math.pi/2,'forward')],math.pi/2),('globe',[([.35,.16],math.pi/2,'side_right'),([.35,.225],math.pi/2,'forward')],0.)]:
 segs=[];p=list(start[:2]);heading=start[2];duration=0.
 for q,h,command in steps:
  assert s.rotation_free(p,heading,h),(task,'rotation',p,heading,h)
  assert s.segment_free(p,q,h),(task,'segment',p,q,h)
  length=math.dist(p,q);turn=abs(wrap(h-heading))/1.1;travel=length/SPEEDS[command];segs.append({'from':p,'to':q,'heading':h,'command':command,'length_m':length,'nominal_travel_s':travel,'nominal_turn_s':turn});duration+=turn+travel;p=q;heading=h
 assert s.rotation_free(p,heading,final),(task,'finalrotation')
 l={'task':task,'start':start,'goal':[*p,final],'segments':segs,'length_m':sum(x['length_m'] for x in segs),'nominal_motion_s':duration+abs(wrap(final-heading))/1.1,'final_turn_radians':wrap(final-heading)};r['legs'].append(l);start=l['goal'];print(task,'checked',flush=True)
r['sampled_standing_lid_sweep']=sweep;r['planner']='V1 graph-planned alarm/drawer legs; manually specified, swept-clearance-checked laptop/globe corridor';r['global_optimality_claim']=False;r['length_m']=sum(l['length_m'] for l in r['legs']);r['nominal_motion_s']=sum(l['nominal_motion_s'] for l in r['legs']);r['robot_projections']=[{'task':l['task'],**s.projection(l['goal'])} for l in r['legs']];r['version']=route_hash(r);Path(args.output).write_text(json.dumps(r,indent=2)+'\n');print(r['version'])
