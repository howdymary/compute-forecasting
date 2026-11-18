"""Small, resolution-bounded SE(2) visibility graph for the unchanged desk.

Translation primitives have a fixed body heading and use the existing command
set. Rotation and translation sweeps are checked separately. This is the best
feasible route on this candidate graph, not a globally optimal continuous path.
"""
import hashlib,heapq,json,math
from pathlib import Path
import numpy as np
from ..curriculum.world import ROUTE,STATIONS,wrap
from .geometry import ConfigurationSpace

APPROACHES={**STATIONS,'alarm':(-.375,.025,math.pi/2)}
SPEEDS={'forward':.065,'back':.025,'side_left':.025,'side_right':.025}
OFFSETS=[('forward',0.),('back',math.pi),('side_left',-math.pi/2),('side_right',math.pi/2)]

def route_hash(data):
 return hashlib.sha256(json.dumps({k:v for k,v in data.items() if k!='version'},sort_keys=True,separators=(',',':')).encode()).hexdigest()[:16]

def plan_leg(space,start,goal):
 # Candidate vertices lie in clear corridors around the fixed fixtures. Sweeps,
 # not the vertex positions alone, decide feasibility. 5 mm candidate spacing.
 candidates=[start[:2],goal[:2],[-.375,-.015],[-.25,.015],[-.20,.015],[-.20,-.035],[-.13,-.015],[-.015,.015],[.30,.025],[.315,.025],[.33,.025],[.315,.295],[.33,.295],[.35,.27],[.35,.225]]
 nodes=[]
 for p in candidates:
  xy=tuple(round(float(x),6) for x in p)
  if xy not in nodes:nodes.append(xy)
 initial=(0,round(wrap(start[2]),6));queue=[(0.,0.,initial)];costs={initial:0.};parent={};best=None;edge_cache={};expanded=0
 def heuristic(i):return math.dist(nodes[i],goal[:2])/.065
 while queue:
  _,cost,state=heapq.heappop(queue)
  if cost>costs[state]+1e-8:continue
  i,heading=state;expanded+=1
  if i==1:
   if space.rotation_free(nodes[i],heading,goal[2]):
    terminal=cost+abs(wrap(goal[2]-heading))/1.1
    if best is None or terminal<best[0]:best=(terminal,state)
   # Other arrivals might have cheaper final alignment.
  if best is not None and cost+heuristic(i)>=best[0]-1e-7:continue
  for j in sorted(range(len(nodes)),key=lambda k:math.dist(nodes[k],goal[:2])):
   if i==j:continue
   distance=math.dist(nodes[i],nodes[j]);bearing=math.atan2(nodes[j][1]-nodes[i][1],nodes[j][0]-nodes[i][0])
   for command,offset in OFFSETS:
    h=round(wrap(bearing+offset),6);turn=abs(wrap(h-heading));new_cost=cost+turn/1.1+distance/SPEEDS[command]
    target=(j,h)
    if new_cost>=costs.get(target,math.inf)-1e-7 or best is not None and new_cost+heuristic(j)>=best[0]-1e-7:continue
    if not space.rotation_free(nodes[i],heading,h):continue
    key=(i,j,h)
    if key not in edge_cache:edge_cache[key]=space.segment_free(nodes[i],nodes[j],h)
    if not edge_cache[key]:continue
    costs[target]=new_cost;parent[target]=(state,{'from':list(nodes[i]),'to':list(nodes[j]),'heading':h,'command':command,'length_m':distance,'nominal_travel_s':distance/SPEEDS[command],'nominal_turn_s':turn/1.1});heapq.heappush(queue,(new_cost+heuristic(j),new_cost,target))
 if best is None:raise RuntimeError(f'No feasible candidate-graph route: {start} -> {goal}')
 segments=[];state=best[1]
 while state!=initial:state,edge=parent[state];segments.append(edge)
 segments.reverse()
 return {'start':list(start),'goal':list(goal),'segments':segments,'length_m':sum(s['length_m'] for s in segments),'nominal_motion_s':best[0],'expanded_states':expanded,'final_turn_radians':wrap(goal[2]-best[1][1])}

def build_route(seed=19000):
 space=ConfigurationSpace(seed,clearance=.010);start=[*space.initial[:2],float(math.atan2(2*(space.initial[3]*space.initial[6]+space.initial[4]*space.initial[5]),1-2*(space.initial[5]**2+space.initial[6]**2)))];legs=[]
 for task,goal in APPROACHES.items():
  leg=plan_leg(space,start,goal);leg['task']=task;legs.append(leg);start=list(goal)
 result={'schema':'mochi.route.v1','calibration_seed':seed,'task_order':list(APPROACHES),'planner':'SE(2) visibility graph, bounded candidate vertices, exact segment headings, shortest nominal time on graph','global_optimality_claim':False,'units':'metres, radians, seconds','desk':{'lo':[-.6,-.4],'hi':[.6,.4]},'clearance':{'total_m':.010,'geometric_m':.002,'tracking_allowance_m':.005,'braking_allowance_m':.003,'note':'Engineering allowances; must be checked against measured tracking. Seven sampled native-gait poses, not a continuous-motion certificate.'},'sweep_resolution':{'translation_m':.0075,'rotation_rad':math.pi/24},'obstacles':space.obstacle_bounds(),'old_route':[{'name':t,'pose':list(p)} for t,p in ROUTE],'initial_pose':legs[0]['start'],'legs':legs,'length_m':sum(l['length_m'] for l in legs),'nominal_motion_s':sum(l['nominal_motion_s'] for l in legs),'nominal_time_caveat':'Command-speed estimate excludes acceleration, settling, task contact and arm recovery; not measured completion time.','geometry_queries':space.calls}
 result['robot_projections']=[{'task':l['task'],**space.projection(l['goal'])} for l in legs];result['version']=route_hash(result);return result

if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser();p.add_argument('--output',default='mochi/configs/desk-route-v1.json');a=p.parse_args();r=build_route();out=Path(a.output);out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({k:r[k] for k in ['version','length_m','nominal_motion_s','geometry_queries']},indent=2))
