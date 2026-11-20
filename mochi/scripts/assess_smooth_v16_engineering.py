"""Summarize completed physical engineering attempts without rerunning them."""
import hashlib,json,math
from pathlib import Path
from statistics import mean

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'artifacts/smooth-v16-engineering'
def read(p):return json.loads(p.read_text())
def describe(name):
    path=OUT/(name+'.json');r=read(path);e=r['episode']
    return {'id':name,'path':str(path.relative_to(ROOT)),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
        'complete_sequence_success':r.get('complete_sequence_success',r.get('success',False)),
        'failure':r.get('failure'),'physical_seconds':e['duration'],'steps':e['steps'],
        'fall':e['fall'],'invalid_contact':e['invalid_contact'],
        'task_outcomes':{k:v['success'] for k,v in e['results'].items()},
        'recovery_joint_travel_rad':sum(x['arm_joint_travel_rad'] for x in e['recoveries']),
        'postit_loaded_contact_samples':len(e.get('postit_crossings',[])),
        'scene_version':e['scene']['version'],'hinge_friction_nm':e['scenario']['laptop_friction'],
        'source_snapshot':str((OUT/'source-snapshots'/name/'src/mochi/smooth_v16').relative_to(ROOT)) if (OUT/'source-snapshots'/name).exists() else None}

def main():
    from mochi.smooth_v16.verification import forward_descent_check
    ledger=read(OUT/'ledger.json');assert all(x['status'] in ['completed','failed'] for x in ledger.values())
    routes={name:read(OUT/(name+'.json')) for name in ['continuous-route-7','continuous-route-8']}
    for name,r in routes.items():
        e=r['episode'];assert r['complete_sequence_success'] and not r['failure'] and not e['fall'] and not e['invalid_contact'],name
        assert e['maximum_applied_base_force']==0
        assert all(e['results'][k]['success'] and e['results'][k]['contacts']>0 and e['results'][k]['max_force_n']<.8 for k in ['alarm','drawer','laptop','globe'])
        assert len(e['recoveries'])==4 and all(x['success'] for x in e['recoveries'])
        assert e['scene']['version']=='richdesk-v16-open-hinge'
        assert e['results']['laptop']['profile']['release_degrees']==42
        assert e['postit_crossings']
        assert forward_descent_check(e['step_events'],e['book_motion_samples'])['verified']
        turn=next(x for x in r['arrivals'] if x['label']=='book-top-turnaround')
        assert turn['success'] and turn['heading_error_degrees']<=10 and turn['book_top']['instant_valid']
    assert routes['continuous-route-7']['episode']['trajectory']['frames'][0]==routes['continuous-route-8']['episode']['trajectory']['frames'][0]
    before=read(OUT/'postit-detour-1.json');after=read(OUT/'postit-direct-0.json')
    assert before['source']==after['source'] and before['success'] and after['success']
    comparison={'scope':'Isolated matched-state approach and paper crossing, same final controlled exit; controller engineering, not training.',
        'source':before['source'],'source_sha256':hashlib.sha256((ROOT/before['source']).read_bytes()).hexdigest(),
        'detour':describe('postit-detour-1'),'direct':describe('postit-direct-0'),
        'step_reduction_fraction':1-after['episode']['steps']['attempts']/before['episode']['steps']['attempts'],
        'time_reduction_fraction':1-after['duration_s']/before['duration_s']}
    evidence={'study':'mochi-smooth-v16-engineering','scope':'Physical controller and route engineering before gradients. Zero new Tinker optimizer updates.',
        'validated_route':describe('continuous-route-7'),
        'matched_full_routes':{k:describe(k) for k in routes},'route_candidate_comparison':comparison,
        'forward_descent':{k:forward_descent_check(r['episode']['step_events'],r['episode']['book_motion_samples']) for k,r in routes.items()},
        'failed_attempts':{k:{'failure':v.get('failure',v.get('error')),'wall_seconds':v['wall_seconds']} for k,v in ledger.items() if not v.get('success',False)},
        'engineering_usage':{'physical_rollouts':len(ledger),'single_worker_hours':sum(v['wall_seconds'] for v in ledger.values())/3600},
        'limits':['One known engineering scenario, not held-out performance.','Scene hinge friction and42-degree laptop release are engineering changes shared by all later weights.','Early exploratory attempts captured source hashes retrospectively; final references ran from immutable complete source snapshots.','Native gait weights remain fixed.']}
    out=ROOT/'evidence/smooth-v16/engineering.json';out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(evidence,indent=2)+'\n')
    print(json.dumps({'continuous_routes_verified':list(routes),'local_rollouts':len(ledger),'route_step_reduction_fraction':comparison['step_reduction_fraction']}))
if __name__=='__main__':main()
