import json,math
from pathlib import Path
import numpy as np
from mochi.planning.follower import projection,teacher,PathRunner
from mochi.planning.route import route_hash
ROOT=Path(__file__).resolve().parents[1]

def test_route_is_the_versioned_control_reference():
 r=json.loads((ROOT/'configs/desk-route-v1.json').read_text());assert r['version']==route_hash(r)
 assert [l['task'] for l in r['legs']]==['alarm','drawer','laptop','globe']
 for a,b in zip(r['legs'],r['legs'][1:]):assert a['goal']==b['start']
 assert math.isclose(r['length_m'],sum(s['length_m'] for l in r['legs'] for s in l['segments']))

def test_projection_clamps_and_reports_cross_track():
 p,u,error=projection([.5,.02],[0,0],[1,0]);np.testing.assert_allclose(p,[.5,0]);assert u==.5 and error==.02
 p,u,error=projection([2,0],[0,0],[1,0]);assert u==1 and error==1

def test_final_heading_does_not_override_travel_heading():
 obs={'heading_error_degrees':0,'final_heading_error_degrees':180,'distance_mm':200,'target_forward_mm':80,'target_left_mm':0,'phase':'track'}
 assert teacher(obs)=='forward'
 assert teacher({**obs,'heading_error_degrees':40})=='left'

def test_alignment_is_latched_after_entering_approach():
 r=PathRunner(json.loads((ROOT/'configs/desk-route-v1.json').read_text()));r.reset(19000,False);r.segment=len(r.route['legs'][0]['segments'])-1;goal=np.array(r.route['legs'][0]['goal'][:2]);r.w.d.qpos[:2]=goal-[0,.015]
 assert r.observation()['phase']=='align'
 r.w.d.qpos[:2]=goal-[0,.025]
 assert r.observation()['phase']=='align' # previous implementation switched back

def test_failed_short_route_has_no_efficiency_advantage():
 from mochi.planning.metrics import metrics
 r=json.loads((ROOT/'configs/desk-route-v1.json').read_text())
 ep={'trajectory':{'frames':[]},'decisions':[],'results':{},'fall':True,'duration':1,'maximum_applied_base_force':0,'final_object_states':{},'final_object_speeds':{}}
 m=metrics({'episode':ep,'arrivals':[]},r)
 assert m['excess_path_m_successful_only'] is None and not m['full_sequence_success']
